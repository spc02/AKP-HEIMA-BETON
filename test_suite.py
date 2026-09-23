import os
import sys
import unittest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
import database
import styles
import export_service
from ui.dashboard_view import DashboardView
from ui.master_data_view import MasterDataView
from ui.stok_view import StokView
from ui.produksi_view import ProduksiView
from ui.keuangan_view import KeuanganView
from ui.laporan_view import LaporanView
from main import MainWindow

database.DB_FILENAME = "test_akp_beton.db"

class AKPBetonTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication(sys.argv)
        database.init_db()

    @classmethod
    def tearDownClass(cls):
        test_db = database.get_db_path()
        if os.path.exists(test_db) and "test_akp_beton.db" in test_db:
            try:
                os.remove(test_db)
            except Exception:
                pass

    def test_01_database_seed_and_materials(self):
        mats = database.get_all_materials()
        self.assertGreaterEqual(len(mats), 5)
        names = [m["nama"] for m in mats]
        self.assertIn("Semen", names)
        self.assertIn("Pasir", names)
        self.assertIn("Split 1.2", names)

    def test_02_recipes_and_mutu(self):
        mutus = database.get_all_mutu_beton()
        self.assertGreaterEqual(len(mutus), 4)
        mortar = next(m for m in mutus if m["kode"] == "mortar")
        resep = database.get_resep_by_mutu_id(mortar["id"])
        self.assertGreaterEqual(len(resep), 1)
        semen_item = next(r for r in resep if "Semen" in r["material_nama"])
        self.assertEqual(semen_item["jumlah_per_m3"], 125.0)

    def test_03_hpp_and_pos_delivery_integration(self):
        """Test HPP calculation, stock auto-deduction, and auto-creation of project invoice"""
        mats = {m["nama"]: m["id"] for m in database.get_all_materials()}
        mutus = {m["kode"]: m["id"] for m in database.get_all_mutu_beton()}
        proyeks = {p["nama"]: p["id"] for p in database.get_all_proyek()}

        # 1. Tambah stok semen 10.000 kg dengan harga beli Rp 1.150 / kg
        semen_id = mats["Semen"]
        init_semen = database.get_material_by_id(semen_id)["stok_saat_ini"]
        stok_id = database.tambah_stok_masuk(
            material_id=semen_id, 
            tanggal="2026-08-01", 
            jumlah=10000.0, 
            no_plat="AB 1234 CD", 
            supplier="PT Semen Gresik", 
            harga_satuan=1150.0,
            keterangan="DO Test Semen Masuk"
        )
        # Belum diklik datang: material belum masuk stok
        self.assertEqual(database.get_material_by_id(semen_id)["stok_saat_ini"], init_semen)

        # Klik Datang: material resmi masuk stok
        ok_dtg, _ = database.set_stok_masuk_tanggal_datang(stok_id, "2026-08-01")
        self.assertTrue(ok_dtg)
        after_in = database.get_material_by_id(semen_id)["stok_saat_ini"]
        self.assertEqual(after_in, init_semen + 10000.0)

        # Verifikasi hutang semen terbentuk otomatis
        semen_orders = database.get_pembayaran_semen_list()
        self.assertGreaterEqual(len(semen_orders), 1)
        latest_semen_order = semen_orders[0]
        self.assertGreater(latest_semen_order["total_harga"], 0)

        # 2. Verifikasi perhitungan HPP Mutu K-250
        k250_id = mutus.get("K-250", list(mutus.values())[0])
        hpp_calc = database.calculate_mutu_hpp(k250_id)
        self.assertGreater(hpp_calc["hpp_per_m3"], 0)
        self.assertGreater(len(hpp_calc["breakdown"]), 0)

        # 3. Pengiriman K-250 volume 3 m3 dengan harga jual Rp 860.000 / m3
        target_proyek_id = list(proyeks.values())[0]
        ok, msg, p_id = database.simpan_pengiriman(
            tanggal="2026-08-01",
            mutu_beton_id=k250_id,
            volume_m3=3.0,
            proyek_id=target_proyek_id,
            tujuan_pengiriman="Lokasi Test Pengecoran",
            harga_jual_kustom=860000.0,
            catatan="Uji Coba Pengiriman POS"
        )
        self.assertTrue(ok)
        self.assertIsNotNone(p_id)

        # 4. Verifikasi piutang proyek terbentuk otomatis
        piutang_list = database.get_piutang_by_proyek(target_proyek_id)
        matched_piutang = next((piu for piu in piutang_list if piu.get("pengiriman_id") == p_id), None)
        self.assertIsNotNone(matched_piutang)
        self.assertEqual(matched_piutang["total_tagihan"], 860000.0 * 3.0)

        # 5. Verifikasi HPP tersimpan di tabel pengiriman
        shipments = database.get_riwayat_pengiriman()
        saved_shipment = next((s for s in shipments if s["id"] == p_id), None)
        self.assertIsNotNone(saved_shipment)
        self.assertGreater(saved_shipment["hpp_per_m3"], 0)
        self.assertEqual(saved_shipment["harga_jual_per_m3"], 860000.0)
        self.assertEqual(saved_shipment["total_pendapatan"], 2580000.0)
        self.assertEqual(saved_shipment["margin_laba_rp"], 2580000.0 - saved_shipment["total_hpp"])

        # 6. Hapus pengiriman -> verifikasi rollback stok dan penghapusan piutang
        ok_del, msg_del = database.hapus_pengiriman(p_id)
        self.assertTrue(ok_del)
        piutang_after_del = database.get_piutang_by_proyek(target_proyek_id)
        self.assertIsNone(next((piu for piu in piutang_after_del if piu.get("pengiriman_id") == p_id), None))

        # Bersihkan stok test
        database.hapus_stok_masuk(stok_id)

    def test_04_keuangan_4_pillars_and_running_balances(self):
        """Test 4 Pillars: Saldo Kas, Hutang Semen, Piutang Proyek, Kas Kantor, Gaji Karyawan"""
        init_ringkasan = database.get_ringkasan_kas()
        init_kantor = init_ringkasan["total_out_kantor"]
        init_gaji = init_ringkasan["total_out_gaji"]
        init_saldo = init_ringkasan["saldo_akhir"]

        # 1. Modal Awal Kas (+ 50.000.000)
        k1 = database.catat_kas("2026-08-01", "Modal Kas Awal Test", 50000000.0, 0.0, "Modal Awal")
        
        # 2. Kas Kantor (BBM Ops) (- 1.500.000)
        kk_id = database.save_kas_kantor("2026-08-02", "NOTA-TEST-01", "BBM / Solar Operasional", 1500000.0, "SPBU Test", "BBM Truk Mixer")
        
        # 3. Gaji Karyawan (- 2.200.000)
        gj_id = database.save_gaji_karyawan("2026-08-03", "Minggu 1", "Supriyanto Test", 2000000.0, "Driver", 200000.0, "Tunai", "Gaji Driver")

        # 4. Verifikasi Ringkasan Kas
        ringkasan = database.get_ringkasan_kas()
        self.assertEqual(ringkasan["total_out_kantor"], init_kantor + 1500000.0)
        self.assertEqual(ringkasan["total_out_gaji"], init_gaji + 2200000.0)
        self.assertEqual(ringkasan["saldo_akhir"], init_saldo + 50000000.0 - 1500000.0 - 2200000.0)

        # Cleanup test entries
        database.delete_kas_kantor(kk_id)
        database.delete_gaji_karyawan(gj_id)
        database.hapus_kas(k1)

    def test_05_views_instantiation(self):
        dash = DashboardView()
        dash.load_data()

        master = MasterDataView()
        master.refresh_all()

        stok = StokView()
        stok.refresh_all()

        prod = ProduksiView()
        prod.refresh_all()

        keu = KeuanganView()
        keu.refresh_all()

        lap = LaporanView()
        lap.refresh_all()

        self.assertIsNotNone(dash)
        self.assertIsNotNone(master)
        self.assertIsNotNone(stok)
        self.assertIsNotNone(prod)
        self.assertIsNotNone(keu)
        self.assertIsNotNone(lap)

    def test_06_export_generation(self):
        os.makedirs("test_output", exist_ok=True)
        xlsx_path_pengiriman = "test_output/rekap_pengiriman_test.xlsx"
        xlsx_path_stok = "test_output/rekap_stok_test.xlsx"
        xlsx_path_keuangan = "test_output/rekap_keuangan_test.xlsx"
        pdf_path_pengiriman = "test_output/rekap_pengiriman_test.pdf"
        pdf_path_stok = "test_output/rekap_stok_test.pdf"
        pdf_path_keuangan = "test_output/rekap_keuangan_test.pdf"

        self.assertTrue(export_service.export_pengiriman_excel(xlsx_path_pengiriman))
        self.assertTrue(export_service.export_stok_excel(xlsx_path_stok))
        self.assertTrue(export_service.export_keuangan_excel(xlsx_path_keuangan))

        self.assertTrue(export_service.export_pengiriman_pdf(pdf_path_pengiriman))
        self.assertTrue(export_service.export_stok_pdf(pdf_path_stok))
        self.assertTrue(export_service.export_keuangan_pdf(pdf_path_keuangan))

        self.assertTrue(os.path.exists(xlsx_path_keuangan))
        self.assertTrue(os.path.exists(pdf_path_keuangan))
        self.assertGreater(os.path.getsize(xlsx_path_keuangan), 1000)
        self.assertGreater(os.path.getsize(pdf_path_keuangan), 1000)

    def test_07_kode_beton_standar_table_values(self):
        """Memverifikasi seluruh nilai material tabel kode beton standar acuan"""
        tabel = database.get_tabel_kode_beton_standar()
        test_volumes = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
        
        for kode, data in tabel.items():
            base = data["resep"]
            for v in test_volumes:
                calc = database.hitung_komposisi_beton(kode, v)["material"]
                for mat_name, base_qty in base.items():
                    self.assertEqual(calc[mat_name], round(base_qty * v, 2))

    def test_08_proportional_interpolation_custom_volume(self):
        """Memverifikasi kalkulasi proporsional untuk volume kustom di luar 1 - 3.5 m3"""
        base_k250 = database.get_tabel_kode_beton_standar()["K-250"]["resep"]
        calc_05 = database.hitung_komposisi_beton("K-250", 0.5)["material"]
        self.assertEqual(calc_05["Semen"], round(base_k250["Semen"] * 0.5, 2))
        self.assertEqual(calc_05["Pasir"], round(base_k250["Pasir"] * 0.5, 2))
    def test_09_material_price_history(self):
        """Memverifikasi pencatatan riwayat harga beli material"""
        mats = database.get_all_materials()
        semen = next(m for m in mats if "Semen" in m["nama"])
        
        database.update_material_price(semen["id"], 1200.0, keterangan="Kenaikan Harga Uji")
        hist = database.get_material_price_history(semen["id"])
        self.assertGreaterEqual(len(hist), 1)
        self.assertEqual(hist[0]["harga_beli"], 1200.0)

    def test_10_collapsible_keuangan_navigation(self):
        """Memverifikasi collapsible submenu menu Keuangan di sidebar dan sub-tab switching"""
        window = MainWindow()
        window.show()
        
        # 1. State Awal: Submenu Keuangan tertutup, Dashboard aktif
        self.assertTrue(window.keuangan_submenu_frame.isHidden())
        self.assertEqual(window.stacked_widget.currentIndex(), 0)
        self.assertEqual(window.lbl_page_title.text(), "Dashboard Operasional")
        self.assertEqual(window.nav_buttons["keuangan"].text(), "Keuangan Plant  ▸")

        # 2. Klik Menu Keuangan -> Submenu terbuka, pindah ke Keuangan sub-tab 0 (Ringkasan)
        window.on_nav_clicked(4)
        self.assertFalse(window.keuangan_submenu_frame.isHidden())
        self.assertEqual(window.stacked_widget.currentIndex(), 4)
        self.assertEqual(window.nav_buttons["keuangan"].text(), "Keuangan Plant  ▾")
        self.assertEqual(window.keuangan_view.get_current_sub_tab(), 0)
        self.assertIn("Ringkasan", window.lbl_page_title.text())

        # 3. Klik Sub-menu 1 (Piutang Material)
        window.on_keuangan_sub_clicked(1)
        self.assertEqual(window.stacked_widget.currentIndex(), 4)
        self.assertEqual(window.keuangan_view.get_current_sub_tab(), 1)
        self.assertIn("Piutang Material", window.lbl_page_title.text())

        # 4. Klik Sub-menu 2 (Piutang Proyek)
        window.on_keuangan_sub_clicked(2)
        self.assertEqual(window.keuangan_view.get_current_sub_tab(), 2)
        self.assertIn("Piutang & Pembayaran Proyek", window.lbl_page_title.text())

        # 5. Klik Sub-menu 5 (Operasional Kendaraan)
        window.on_keuangan_sub_clicked(5)
        self.assertEqual(window.keuangan_view.get_current_sub_tab(), 5)
        self.assertIn("Kendaraan", window.lbl_page_title.text())

        # 6. Klik Menu Utama Lain (Stok Material / Master Data) -> Submenu Keuangan tertutup
        window.on_nav_clicked(2) # Stok Material
        self.assertTrue(window.keuangan_submenu_frame.isHidden())
        self.assertEqual(window.stacked_widget.currentIndex(), 2)
        self.assertEqual(window.nav_buttons["keuangan"].text(), "Keuangan Plant  ▸")
        self.assertIn("Stok Material", window.lbl_page_title.text())

        # 7. Pindah via switch_to_module("keuangan", sub_tab=3)
        window.switch_to_module("keuangan", sub_tab=3) # Kas Kantor
        self.assertFalse(window.keuangan_submenu_frame.isHidden())
        self.assertEqual(window.stacked_widget.currentIndex(), 4)
        self.assertEqual(window.keuangan_view.get_current_sub_tab(), 3)
        self.assertIn("Kas Kantor", window.lbl_page_title.text())

        # 8. Pindah via switch_to_module("kendaraan")
        window.switch_to_module("kendaraan")
        self.assertEqual(window.stacked_widget.currentIndex(), 4)
        self.assertEqual(window.keuangan_view.get_current_sub_tab(), 5)
        self.assertIn("Kendaraan", window.lbl_page_title.text())

        window.close()

    def test_07_license_management(self):
        """Test Machine ID generation, key generation, and verification"""
        import license_manager
        mid = license_manager.get_machine_id()
        self.assertTrue(mid.startswith("AKP-"))

        # Test Permanent Key
        key = license_manager.generate_license_key(mid, "PERM")
        self.assertTrue(key.startswith("AKP-PERM-"))
        valid, msg, meta = license_manager.verify_license_key(mid, key)
        self.assertTrue(valid)
        self.assertTrue(meta["is_permanent"])

        # Test Invalid Key
        invalid_key = "AKP-PERM-0000-0000-0000"
        valid, msg, meta = license_manager.verify_license_key(mid, invalid_key)
        self.assertFalse(valid)

    def test_08_user_authentication(self):
        """Test User auth, password hashing, and user creation"""
        # Test Default Admin
        ok, msg, user = database.authenticate_user("admin", "admin123")
        self.assertTrue(ok)
        self.assertEqual(user["username"], "admin")

        # Test Wrong Password
        ok, msg, user = database.authenticate_user("admin", "wrongpass")
        self.assertFalse(ok)

        # Test Create User
        test_uname = "operator_test"
        ok, msg = database.create_user(test_uname, "pass123", "Operator Uji Coba")
        self.assertTrue(ok)

        # Test Auth New User
        ok, msg, user = database.authenticate_user(test_uname, "pass123")
        self.assertTrue(ok)
        self.assertEqual(user["nama_lengkap"], "Operator Uji Coba")

        # Clean up test user
        del_ok, _ = database.delete_user(user["id"])
        self.assertTrue(del_ok)

    def test_09_reset_data_transaksi(self):
        """Test resetting operational transactions to clean slate"""
        ok, msg = database.reset_data_transaksi()
        self.assertTrue(ok)

        # Pastikan transaksi kosong
        with database.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM pengiriman")
            self.assertEqual(c.fetchone()[0], 0)
            c.execute("SELECT COUNT(*) FROM stok_masuk")
            self.assertEqual(c.fetchone()[0], 0)
            c.execute("SELECT COUNT(*) FROM saldo_kas")
            self.assertEqual(c.fetchone()[0], 0)

        # Muat kembali demo data
        ok_demo, _ = database.seed_demo_data()
        self.assertTrue(ok_demo)


    def test_14_kendaraan_dialog_without_kapasitas(self):
        """Memverifikasi form tambah armada dapat menyimpan kendaraan tanpa input kapasitas dan driver default"""
        from ui.kendaraan_view import KendaraanDialog
        dlg = KendaraanDialog()
        # Pastikan tidak ada widget spin_kapasitas dan txt_driver pada dialog armada
        self.assertFalse(hasattr(dlg, "spin_kapasitas"))
        self.assertFalse(hasattr(dlg, "txt_driver"))
        
        dlg.txt_plat.setText("AB 7777 NO_KAP")
        dlg.txt_nama.setText("Pick Up Operasional")
        dlg.cb_jenis.setEditText("Mobil Operasional")
        dlg.save()
        
        k = database.get_kendaraan_by_plat("AB 7777 NO_KAP")
        self.assertIsNotNone(k)
        self.assertEqual(k["no_plat"], "AB 7777 NO_KAP")
        self.assertEqual(k["kapasitas_m3"], 0.0)
        self.assertEqual(k["driver_default"], "")
        
        # Bersihkan data uji
        database.hapus_kendaraan(k["id"])

    def test_15_stok_masuk_arrival_flow(self):
        """Memverifikasi order material belum masuk stok sebelum diklik Datang, dan masuk setelah diklik Datang"""
        # 1. Tambah material uji
        mat_id = database.save_material(kode="MAT-TST", nama="Batu Uji", satuan="kg", stok_minimum=100.0, harga_beli_terbaru=500.0, stok_awal=0.0)
        init_stok = database.get_material_by_id(mat_id)["stok_saat_ini"]
        self.assertEqual(init_stok, 0.0)

        # 2. Input stok masuk tanpa tanggal datang (status order)
        stok_id = database.tambah_stok_masuk(
            material_id=mat_id,
            tanggal="2026-09-23",
            jumlah=500.0,
            no_plat="AB 1111 ZZ",
            supplier="Supplier Uji",
            harga_satuan=500.0,
            keterangan="Order uji belum datang",
            tanggal_datang=None
        )
        
        # Stok masih harus 0 karena belum diklik Datang
        stok_after_order = database.get_material_by_id(mat_id)["stok_saat_ini"]
        self.assertEqual(stok_after_order, 0.0)

        # Total masuk di rekap kartu stok juga belum menghitung yang belum datang
        rekap = [r for r in database.get_rekap_kartu_stok() if r["id"] == mat_id][0]
        self.assertEqual(rekap["total_masuk"], 0.0)

        # 3. Klik Datang
        ok, msg = database.set_stok_masuk_tanggal_datang(stok_id, "2026-09-23")
        self.assertTrue(ok)

        # Sekarang stok harus bertambah 500.0
        stok_after_datang = database.get_material_by_id(mat_id)["stok_saat_ini"]
        self.assertEqual(stok_after_datang, 500.0)

        rekap2 = [r for r in database.get_rekap_kartu_stok() if r["id"] == mat_id][0]
        self.assertEqual(rekap2["total_masuk"], 500.0)

        # Klik datang lagi tidak boleh dobel tambah stok
        database.set_stok_masuk_tanggal_datang(stok_id, "2026-09-23")
        self.assertEqual(database.get_material_by_id(mat_id)["stok_saat_ini"], 500.0)

        # 4. Hapus stok masuk yang sudah datang -> stok berkurang kembali
        database.hapus_stok_masuk(stok_id)
        self.assertEqual(database.get_material_by_id(mat_id)["stok_saat_ini"], 0.0)

        # Bersihkan material uji
        database.delete_material(mat_id)

    def test_16_kas_kantor_without_vehicle_fields(self):
        """Memverifikasi form kas kantor tidak memiliki input kendaraan & BBM karena sudah ada menu khusus"""
        from ui.keuangan_view import KasKantorDialog
        dlg = KasKantorDialog()
        self.assertFalse(hasattr(dlg, "cb_kendaraan"))
        self.assertFalse(hasattr(dlg, "cb_pengiriman"))
        
        # Pastikan tidak ada kategori BBM atau kendaraan
        items = [dlg.cb_kat.itemText(i) for i in range(dlg.cb_kat.count())]
        self.assertNotIn("BBM / Solar Operasional", items)
        self.assertNotIn("Servis & Maintenance", items)
        self.assertNotIn("Sparepart & Oli Mesin", items)
        self.assertIn("ATK & Perlengkapan Kantor", items)
        self.assertIn("Konsumsi & Dapur", items)

    def test_17_kiriman_proyek_dialog(self):
        """Memverifikasi dialog daftar kiriman produksi per proyek di modul Keuangan"""
        from ui.keuangan_view import KeuanganView, DetailKirimanProyekDialog
        
        # 1. Pastikan KeuanganView memuat rekapitulasi proyek
        kv = KeuanganView()
        kv.load_proyek_keuangan()
        self.assertGreater(kv.table_rekap_proyek.rowCount(), 0)

        # 2. Ambil proyek uji dan buat data pengiriman
        proyeks = database.get_all_proyek()
        p = proyeks[0]
        mutus = database.get_all_mutu_beton()
        m = mutus[0]

        ok, msg, p_id = database.simpan_pengiriman(
            tanggal="2026-09-23",
            mutu_beton_id=m["id"],
            volume_m3=4.0,
            proyek_id=p["id"],
            tujuan_pengiriman="Lokasi Cor Uji",
            no_surat_jalan="SJ-UJI-001",
            no_plat_truk="B 9999 AKP",
            driver="Driver Uji",
            catatan="Uji kiriman",
            harga_jual_kustom=800000.0
        )
        self.assertTrue(ok)

        # 3. Reload rekap dan uji buka dialog kiriman proyek
        kv.load_proyek_keuangan()
        rekap = database.get_rekap_saldo_per_proyek()
        target = next(r for r in rekap if r["id"] == p["id"])
        
        dlg = DetailKirimanProyekDialog(target)
        self.assertIsNotNone(dlg)

        # Pastikan riwayat pengiriman untuk proyek ini terbaca
        riwayat = database.get_riwayat_pengiriman(proyek_id=p["id"])
        self.assertGreaterEqual(len(riwayat), 1)
        self.assertEqual(riwayat[0]["no_surat_jalan"], "SJ-UJI-001")

        # 4. Bersihkan data pengiriman uji
        if p_id:
            database.hapus_pengiriman(p_id)

if __name__ == "__main__":
    unittest.main()



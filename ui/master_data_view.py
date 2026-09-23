"""
Master Data View untuk AKP Beton Desktop Application
Mengelola Master Material & Riwayat Harga Beli, Mutu Beton, Resep Dinamis,
Kalkulasi HPP Otomatis, Penetapan Harga Jual & Margin Laba, serta Master Proyek.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, 
    QLabel, QFrame, QTableWidgetItem, QMessageBox, QDialog,
    QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit, QHeaderView,
    QTableWidget, QAbstractItemView, QGridLayout, QListView, QButtonGroup
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from components import (
    ModernTableWidget, SectionHeader, ModernDialog, confirm_dialog, BadgeLabel,
    PrimaryButton, SecondaryButton, SuccessButton, DangerButton,
    TableEditButton, TableDeleteButton, TableDetailButton
)
import styles
import database

# ==============================================================================
# DIALOG LIHAT RIWAYAT PERUBAHAN HARGA MATERIAL
# ==============================================================================
class RiwayatHargaMaterialDialog(ModernDialog):
    def __init__(self, material_data, parent=None):
        title = f"Riwayat Perubahan Harga Beli: {material_data['nama']} ({material_data['satuan']})"
        super().__init__(title, parent, min_width=780)
        self.material_data = material_data
        self.resize(780, 480)
        self.setMinimumHeight(400)
        self.init_ui()

    def init_ui(self):
        desc = QLabel(
            "Riwayat perubahan harga beli tersimpan secara permanen. Setiap transaksi lama tetap menggunakan HPP pada tanggal transaksinya."
        )
        desc.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 12px; margin-bottom: 4px;")
        desc.setWordWrap(True)
        self.content_layout.addWidget(desc)

        self.table_hist = ModernTableWidget(["No", "Tanggal Berlaku", "Harga Beli per Satuan", "Keterangan / Sumber", "Dicatat Pada"])
        header = self.table_hist.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Fixed)

        self.table_hist.setColumnWidth(0, 50)
        self.table_hist.setColumnWidth(1, 130)
        self.table_hist.setColumnWidth(2, 165)
        self.table_hist.setColumnWidth(4, 160)
        self.content_layout.addWidget(self.table_hist)

        self.load_history()

        self.btn_save.setVisible(False)
        self.btn_cancel.setText("Tutup")

    def load_history(self):
        hist = database.get_material_price_history(self.material_data["id"])
        self.table_hist.setRowCount(len(hist))
        for idx, h in enumerate(hist):
            self.table_hist.setItem(idx, 0, QTableWidgetItem(str(idx + 1)))
            self.table_hist.setItem(idx, 1, QTableWidgetItem(str(h["tanggal"])))
            
            hrg_item = QTableWidgetItem(styles.format_rupiah(h["harga_beli"]))
            hrg_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_hist.setItem(idx, 2, hrg_item)

            self.table_hist.setItem(idx, 3, QTableWidgetItem(str(h["keterangan"] or "-")))
            self.table_hist.setItem(idx, 4, QTableWidgetItem(str(h["created_at"] or "-")))


# ==============================================================================
# DIALOG EDITOR MATERIAL
# ==============================================================================
class MaterialDialog(ModernDialog):
    def __init__(self, material_data=None, parent=None):
        title = "Edit Master Material" if material_data else "Tambah Master Material Baru"
        super().__init__(title, parent, min_width=480)
        self.material_data = material_data
        self.created_mat_id = None
        self.init_form()

    def init_form(self):
        grid = QGridLayout()
        grid.setSpacing(12)

        grid.addWidget(QLabel("Kode Material:*"), 0, 0)
        self.txt_kode = QLineEdit()
        self.txt_kode.setPlaceholderText("Contoh: MAT-SMN")
        grid.addWidget(self.txt_kode, 0, 1)

        grid.addWidget(QLabel("Nama Material:*"), 1, 0)
        self.txt_nama = QLineEdit()
        self.txt_nama.setPlaceholderText("Contoh: Semen Gresik / Split 1.2")
        grid.addWidget(self.txt_nama, 1, 1)

        grid.addWidget(QLabel("Satuan:*"), 2, 0)
        self.txt_satuan = QComboBox()
        self.txt_satuan.setView(QListView())
        self.txt_satuan.setEditable(True)
        self.txt_satuan.addItems(["kg", "m3", "liter", "ton", "sak"])
        grid.addWidget(self.txt_satuan, 2, 1)

        grid.addWidget(QLabel("Harga Beli Satuan (Rp):*"), 3, 0)
        self.spin_harga = QDoubleSpinBox()
        self.spin_harga.setRange(0, 1000000000.0)
        self.spin_harga.setDecimals(2)
        self.spin_harga.setSingleStep(50)
        self.spin_harga.setValue(1000.0)
        grid.addWidget(self.spin_harga, 3, 1)

        # Field Jumlah Stok Awal (atau Stok Saat Ini jika Edit)
        lbl_stok_text = "Jumlah Stok Saat Ini:" if self.material_data else "Jumlah Stok Awal:"
        grid.addWidget(QLabel(lbl_stok_text), 4, 0)
        self.spin_stok_awal = QDoubleSpinBox()
        self.spin_stok_awal.setRange(0, 100000000.0)
        self.spin_stok_awal.setDecimals(2)
        self.spin_stok_awal.setSingleStep(100)
        self.spin_stok_awal.setValue(0.0)
        grid.addWidget(self.spin_stok_awal, 4, 1)

        # Total Nilai Pembelian / Bayar Otomatis
        lbl_total_text = "Total Nilai Stok Saat Ini:" if self.material_data else "Total Nilai Pembelian / Bayar:"
        grid.addWidget(QLabel(lbl_total_text), 5, 0)
        self.lbl_total_nilai = QLabel("Rp 0")
        self.lbl_total_nilai.setStyleSheet(f"font-weight: 800; color: {styles.COLOR_PRIMARY_LIGHT}; font-size: 15px;")
        grid.addWidget(self.lbl_total_nilai, 5, 1)

        grid.addWidget(QLabel("Batas Stok Minimum:"), 6, 0)
        self.spin_min = QDoubleSpinBox()
        self.spin_min.setRange(0, 10000000)
        self.spin_min.setDecimals(2)
        grid.addWidget(self.spin_min, 6, 1)

        def on_satuan_change(sat):
            suffix = f" {sat.strip()}" if sat.strip() else ""
            self.spin_stok_awal.setSuffix(suffix)
            self.spin_min.setSuffix(suffix)

        self.txt_satuan.currentTextChanged.connect(on_satuan_change)
        on_satuan_change(self.txt_satuan.currentText())

        self.spin_harga.valueChanged.connect(self.update_total_nilai)
        self.spin_stok_awal.valueChanged.connect(self.update_total_nilai)

        grid.addWidget(QLabel("Keterangan:"), 7, 0)
        self.txt_ket = QTextEdit()
        self.txt_ket.setPlaceholderText("Catatan spesifikasi / pemasok material (opsional)")
        self.txt_ket.setMaximumHeight(65)
        grid.addWidget(self.txt_ket, 7, 1)

        self.content_layout.addLayout(grid)
        self.btn_save.clicked.connect(self.save)

        if self.material_data:
            self.txt_kode.setText(self.material_data.get("kode") or "")
            self.txt_nama.setText(self.material_data.get("nama") or "")
            self.txt_satuan.setCurrentText(self.material_data.get("satuan") or "kg")
            self.spin_harga.setValue(float(self.material_data.get("harga_beli_terbaru") or 0))
            self.spin_stok_awal.setValue(float(self.material_data.get("stok_saat_ini") or 0))
            self.spin_min.setValue(float(self.material_data.get("stok_minimum") or 0))
            self.txt_ket.setPlainText(self.material_data.get("keterangan") or "")

        self.update_total_nilai()

    def update_total_nilai(self):
        total = self.spin_harga.value() * self.spin_stok_awal.value()
        self.lbl_total_nilai.setText(styles.format_rupiah(total))

    def save(self):
        kode = self.txt_kode.text().strip()
        nama = self.txt_nama.text().strip()
        satuan = self.txt_satuan.currentText().strip()
        harga_beli = self.spin_harga.value()
        stok_awal = self.spin_stok_awal.value()
        stok_min = self.spin_min.value()
        ket = self.txt_ket.toPlainText().strip()

        if not kode or not nama or not satuan:
            QMessageBox.warning(self, "Peringatan", "Kode, Nama, dan Satuan Material wajib diisi!")
            return

        mat_id = self.material_data.get("id") if self.material_data else None
        try:
            self.created_mat_id = database.save_material(kode, nama, satuan, stok_min, harga_beli, ket, mat_id, stok_awal=stok_awal)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", f"Gagal menyimpan data: {str(e)}")


# ==============================================================================
# DIALOG TABEL KODE BETON STANDAR ACUAN
# ==============================================================================
class TabelKodeBetonStandarDialog(ModernDialog):
    def __init__(self, parent=None):
        super().__init__("Tabel Acuan Standar Kode Mutu Beton (K-100 s.d K-400)", parent, min_width=880)
        self.init_table_view()

    def init_table_view(self):
        desc = QLabel(
            "Tabel acuan komposisi campuran material beton standar AKP Batching Plant (Semen, Pasir, Split, Air).\n"
            "Gunakan pemilih volume di bawah untuk melihat kalkulasi proporsional pada volume tertentu atau menguji volume kustom."
        )
        desc.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 12px; margin-bottom: 6px;")
        desc.setWordWrap(True)
        self.content_layout.addWidget(desc)

        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)
        
        lbl_v = QLabel("Pilih / Uji Volume (m³):")
        lbl_v.setStyleSheet("font-weight: 600;")
        filter_bar.addWidget(lbl_v)

        self.cb_vol = QComboBox()
        self.cb_vol.setView(QListView())
        self.cb_vol.addItems(["Semua Volume (Tabel Lengkap 1.0 - 3.5 m³)", "1.0 m³", "1.5 m³", "2.0 m³", "2.5 m³", "3.0 m³", "3.5 m³", "Volume Kustom..."])
        self.cb_vol.currentIndexChanged.connect(self.on_volume_filter_changed)
        filter_bar.addWidget(self.cb_vol)

        self.spin_custom_vol = QDoubleSpinBox()
        self.spin_custom_vol.setRange(0.1, 100.0)
        self.spin_custom_vol.setValue(1.0)
        self.spin_custom_vol.setDecimals(2)
        self.spin_custom_vol.setSuffix(" m³")
        self.spin_custom_vol.setVisible(False)
        self.spin_custom_vol.valueChanged.connect(self.render_table)
        filter_bar.addWidget(self.spin_custom_vol)

        filter_bar.addStretch()
        self.content_layout.addLayout(filter_bar)

        self.table_std = ModernTableWidget(["No", "Mutu Beton", "Volume (m³)", "Semen (kg)", "Pasir (kg)", "Split 1.2 (kg)", "Air (liter)", "Total Berat (kg)"])
        self.table_std.setMinimumHeight(380)
        self.table_std.setColumnWidth(0, 45)
        self.table_std.setColumnWidth(1, 190)
        self.table_std.setColumnWidth(2, 90)
        self.table_std.setColumnWidth(3, 100)
        self.table_std.setColumnWidth(4, 100)
        self.table_std.setColumnWidth(5, 105)
        self.table_std.setColumnWidth(6, 90)
        self.table_std.setColumnWidth(7, 115)
        self.content_layout.addWidget(self.table_std)

        self.btn_save.setVisible(False)
        self.btn_cancel.setText("Tutup")

        self.render_table()

    def on_volume_filter_changed(self):
        idx = self.cb_vol.currentIndex()
        if idx == 7:
            self.spin_custom_vol.setVisible(True)
        else:
            self.spin_custom_vol.setVisible(False)
        self.render_table()

    def render_table(self):
        idx = self.cb_vol.currentIndex()
        tabel_data = database.get_tabel_kode_beton_standar()
        
        if idx == 0:
            volumes = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
        elif idx in (1, 2, 3, 4, 5, 6):
            volumes = [[1.0, 1.5, 2.0, 2.5, 3.0, 3.5][idx - 1]]
        else:
            volumes = [self.spin_custom_vol.value()]

        rows = []
        no = 1
        for kode, m in tabel_data.items():
            for v in volumes:
                calc = database.hitung_komposisi_beton(kode, v)
                smn = calc["material"].get("Semen", 0)
                psr = calc["material"].get("Pasir", 0)
                spt = calc["material"].get("Split 1.2", 0)
                air = calc["material"].get("Air", 0)
                total = smn + psr + spt + air
                rows.append((no, f"{kode} ({m['nama']})", v, smn, psr, spt, air, total))
            no += 1

        self.table_std.setRowCount(len(rows))
        for r_idx, (num, mutu, vol, smn, psr, spt, air, tot) in enumerate(rows):
            item_no = QTableWidgetItem(str(num))
            item_no.setTextAlignment(Qt.AlignCenter)
            self.table_std.setItem(r_idx, 0, item_no)
            self.table_std.setItem(r_idx, 1, QTableWidgetItem(mutu))
            
            item_v = QTableWidgetItem(f"{vol:.2f}" if vol % 1 != 0 else f"{vol:.1f}")
            item_v.setTextAlignment(Qt.AlignCenter)
            self.table_std.setItem(r_idx, 2, item_v)

            for c_idx, val in enumerate([smn, psr, spt, air, tot], start=3):
                item_val = QTableWidgetItem(styles.format_number(val, 2 if val % 1 != 0 else 0))
                item_val.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if c_idx == 7:
                    item_val.setForeground(Qt.darkBlue)
                self.table_std.setItem(r_idx, c_idx, item_val)


# ==============================================================================
# DIALOG EDITOR MUTU BETON, RESEP & HARGA JUAL (HPP & MARGIN LIVE)
# ==============================================================================
class MutuBetonDialog(ModernDialog):
    def __init__(self, mutu_data=None, parent=None):
        title = "Edit Mutu Beton, Resep & Harga Jual" if mutu_data else "Buat Mutu Beton & Resep Baru"
        super().__init__(title, parent, min_width=780)
        self.mutu_data = mutu_data
        self.available_materials = database.get_all_materials()
        self.recipe_rows = []
        self.init_form()

    def init_form(self):
        top_grid = QGridLayout()
        top_grid.setSpacing(10)

        top_grid.addWidget(QLabel("Kode Mutu:*"), 0, 0)
        self.txt_kode = QLineEdit()
        self.txt_kode.setPlaceholderText("Contoh: K-250 / K-300 / mortar")
        top_grid.addWidget(self.txt_kode, 0, 1)

        top_grid.addWidget(QLabel("Nama / Deskripsi Mutu:"), 0, 2)
        self.txt_nama = QLineEdit()
        self.txt_nama.setPlaceholderText("Contoh: Beton K-250 (fc' 21.4 MPa)")
        top_grid.addWidget(self.txt_nama, 0, 3)

        top_grid.addWidget(QLabel("Harga Jual per m³ (Rp):*"), 1, 0)
        self.spin_harga_jual = QDoubleSpinBox()
        self.spin_harga_jual.setRange(0, 100000000.0)
        self.spin_harga_jual.setDecimals(0)
        self.spin_harga_jual.setSingleStep(25000)
        self.spin_harga_jual.setValue(860000.0)
        self.spin_harga_jual.valueChanged.connect(self.calculate_live_hpp)
        top_grid.addWidget(self.spin_harga_jual, 1, 1)

        top_grid.addWidget(QLabel("Biaya Operasional/Alat per m³:"), 1, 2)
        self.spin_biaya_ops = QDoubleSpinBox()
        self.spin_biaya_ops.setRange(0, 10000000.0)
        self.spin_biaya_ops.setDecimals(0)
        self.spin_biaya_ops.setSingleStep(5000)
        self.spin_biaya_ops.setValue(30000.0)
        self.spin_biaya_ops.valueChanged.connect(self.calculate_live_hpp)
        top_grid.addWidget(self.spin_biaya_ops, 1, 3)

        top_grid.addWidget(QLabel("Keterangan Tambahan:"), 2, 0)
        self.txt_ket = QLineEdit()
        self.txt_ket.setPlaceholderText("Catatan slump / spesifikasi struktur (opsional)")
        top_grid.addWidget(self.txt_ket, 2, 1, 1, 3)

        self.content_layout.addLayout(top_grid)

        # Live HPP & Profit Box
        self.hpp_box = QFrame()
        self.hpp_box.setStyleSheet(f"""
            background-color: {styles.COLOR_PRIMARY_DARK};
            border-radius: 8px;
            padding: 10px 14px;
        """)
        hpp_lay = QHBoxLayout(self.hpp_box)
        hpp_lay.setContentsMargins(10, 8, 10, 8)
        
        self.lbl_hpp_val = QLabel("Total HPP: Rp 0 / m³")
        self.lbl_hpp_val.setStyleSheet("color: #93C5FD; font-size: 13px; font-weight: 700;")
        
        self.lbl_jual_val = QLabel("Harga Jual: Rp 0 / m³")
        self.lbl_jual_val.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 700;")

        self.lbl_laba_val = QLabel("Laba: Rp 0 / m³ (0.0%)")
        self.lbl_laba_val.setStyleSheet("color: #34D399; font-size: 14px; font-weight: 800;")

        hpp_lay.addWidget(self.lbl_hpp_val)
        hpp_lay.addWidget(self.lbl_jual_val)
        hpp_lay.addWidget(self.lbl_laba_val)
        self.content_layout.addWidget(self.hpp_box)

        resep_header = QHBoxLayout()
        lbl_resep = QLabel("KOMPOSISI RESEP MATERIAL (Kebutuhan Per 1 m³ Beton):")
        lbl_resep.setStyleSheet(f"font-weight: 700; color: {styles.COLOR_PRIMARY_DARK}; margin-top: 6px;")
        resep_header.addWidget(lbl_resep)
        resep_header.addStretch()

        btn_autofill = SecondaryButton("⚡ Isi dari Standar Tabel")
        btn_autofill.clicked.connect(self.autofill_from_standard)
        resep_header.addWidget(btn_autofill)

        btn_add_mat = SecondaryButton("+ Tambah Baris Material")
        btn_add_mat.clicked.connect(lambda: self.add_recipe_row())
        resep_header.addWidget(btn_add_mat)
        self.content_layout.addLayout(resep_header)

        self.table_resep = ModernTableWidget(["Material", "Satuan", "Kebutuhan per 1 m³", "Harga Beli Terkini", "Subtotal HPP (Rp)", "Aksi"])
        self.table_resep.setMinimumHeight(190)
        self.table_resep.setColumnWidth(0, 180)
        self.table_resep.setColumnWidth(1, 60)
        self.table_resep.setColumnWidth(2, 130)
        self.table_resep.setColumnWidth(3, 120)
        self.table_resep.setColumnWidth(4, 130)
        self.table_resep.setColumnWidth(5, 75)
        self.content_layout.addWidget(self.table_resep)

        self.btn_save.clicked.connect(self.save)

        if self.mutu_data:
            self.txt_kode.setText(self.mutu_data.get("kode") or "")
            self.txt_nama.setText(self.mutu_data.get("nama") or "")
            self.spin_harga_jual.setValue(float(self.mutu_data.get("harga_jual_per_m3") or 850000.0))
            self.spin_biaya_ops.setValue(float(self.mutu_data.get("biaya_operasional_per_m3") or 30000.0))
            self.txt_ket.setText(self.mutu_data.get("keterangan") or "")
            
            resep_items = database.get_resep_by_mutu_id(self.mutu_data["id"])
            for item in resep_items:
                self.add_recipe_row(material_id=item["material_id"], qty=item["jumlah_per_m3"])
        else:
            self.autofill_standard_preset("K-250")

        self.calculate_live_hpp()

    def autofill_from_standard(self):
        kode = self.txt_kode.text().strip().upper()
        if not kode:
            kode = "K-250"
        self.autofill_standard_preset(kode)

    def autofill_standard_preset(self, kode_mutu: str):
        tabel = database.get_tabel_kode_beton_standar()
        target_kode = None
        for k in tabel.keys():
            if k.upper() == kode_mutu.upper():
                target_kode = k
                break
        
        if not target_kode:
            target_kode = "K-250"

        std_data = tabel[target_kode]
        if not self.mutu_data:
            self.txt_kode.setText(target_kode)
            self.txt_nama.setText(std_data["nama"])
            self.spin_harga_jual.setValue(std_data["harga_jual"])
            self.spin_biaya_ops.setValue(std_data["biaya_ops"])
            self.txt_ket.setText(std_data["keterangan"])

        self.table_resep.setRowCount(0)
        mat_map = {m["nama"]: m["id"] for m in self.available_materials}
        for mat_nama, qty in std_data["resep"].items():
            mat_id = mat_map.get(mat_nama)
            if mat_id:
                self.add_recipe_row(material_id=mat_id, qty=qty)

        self.calculate_live_hpp()

    def add_recipe_row(self, material_id=None, qty=0.0):
        row_idx = self.table_resep.rowCount()
        self.table_resep.insertRow(row_idx)

        cb_mat = QComboBox()
        cb_mat.setView(QListView())
        for m in self.available_materials:
            cb_mat.addItem(f"{m['nama']} ({m['satuan']})", m["id"])
        
        if material_id:
            idx = cb_mat.findData(material_id)
            if idx >= 0: cb_mat.setCurrentIndex(idx)
            
        lbl_satuan = QLabel("kg")
        lbl_satuan.setAlignment(Qt.AlignCenter)
        lbl_satuan.setStyleSheet(f"color: {styles.COLOR_TEXT_MAIN}; font-weight: 600;")
        
        lbl_price = QLabel("Rp 0")
        lbl_price.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        lbl_subtotal = QLabel("Rp 0")
        lbl_subtotal.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_subtotal.setStyleSheet("font-weight: 700;")

        spin_qty = QDoubleSpinBox()
        spin_qty.setRange(0.01, 100000.0)
        spin_qty.setDecimals(2)
        spin_qty.setValue(float(qty) if qty > 0 else 100.0)

        def update_row_calc():
            curr_id = cb_mat.currentData()
            mat = next((m for m in self.available_materials if m["id"] == curr_id), None)
            if mat:
                lbl_satuan.setText(mat["satuan"])
                hrg = float(mat.get("harga_beli_terbaru") or 0)
                lbl_price.setText(styles.format_rupiah(hrg))
                sub = spin_qty.value() * hrg
                lbl_subtotal.setText(styles.format_rupiah(sub))
            self.calculate_live_hpp()

        cb_mat.currentIndexChanged.connect(update_row_calc)
        spin_qty.valueChanged.connect(update_row_calc)

        btn_del = TableDeleteButton("Hapus")
        
        def remove_this_row():
            for r in range(self.table_resep.rowCount()):
                if self.table_resep.cellWidget(r, 5) == btn_del:
                    self.table_resep.removeRow(r)
                    break
            self.calculate_live_hpp()

        btn_del.clicked.connect(remove_this_row)

        self.table_resep.setCellWidget(row_idx, 0, cb_mat)
        self.table_resep.setCellWidget(row_idx, 1, lbl_satuan)
        self.table_resep.setCellWidget(row_idx, 2, spin_qty)
        self.table_resep.setCellWidget(row_idx, 3, lbl_price)
        self.table_resep.setCellWidget(row_idx, 4, lbl_subtotal)
        self.table_resep.setCellWidget(row_idx, 5, btn_del)

        update_row_calc()

    def calculate_live_hpp(self):
        tot_material = 0.0
        for r in range(self.table_resep.rowCount()):
            cb_mat = self.table_resep.cellWidget(r, 0)
            spin_qty = self.table_resep.cellWidget(r, 2)
            if cb_mat and spin_qty:
                mat_id = cb_mat.currentData()
                mat = next((m for m in self.available_materials if m["id"] == mat_id), None)
                if mat:
                    tot_material += spin_qty.value() * float(mat.get("harga_beli_terbaru") or 0)

        biaya_ops = self.spin_biaya_ops.value()
        total_hpp = tot_material + biaya_ops
        harga_jual = self.spin_harga_jual.value()
        laba = harga_jual - total_hpp
        margin_pct = (laba / harga_jual * 100.0) if harga_jual > 0 else 0.0

        self.lbl_hpp_val.setText(f"Total HPP: {styles.format_rupiah(total_hpp)} / m³")
        self.lbl_jual_val.setText(f"Harga Jual: {styles.format_rupiah(harga_jual)} / m³")
        self.lbl_laba_val.setText(f"Laba: {styles.format_rupiah(laba)} / m³ ({margin_pct:.1f}%)")
        if laba < 0:
            self.lbl_laba_val.setStyleSheet("color: #F87171; font-size: 14px; font-weight: 800;")
        else:
            self.lbl_laba_val.setStyleSheet("color: #34D399; font-size: 14px; font-weight: 800;")

    def save(self):
        kode = self.txt_kode.text().strip()
        nama = self.txt_nama.text().strip()
        ket = self.txt_ket.text().strip()
        harga_jual = self.spin_harga_jual.value()
        biaya_ops = self.spin_biaya_ops.value()

        if not kode:
            QMessageBox.warning(self, "Peringatan", "Kode Mutu Beton wajib diisi!")
            return

        resep_items = []
        used_mat_ids = set()

        for r in range(self.table_resep.rowCount()):
            cb_mat = self.table_resep.cellWidget(r, 0)
            spin_qty = self.table_resep.cellWidget(r, 2)
            
            if cb_mat and spin_qty:
                mat_id = cb_mat.currentData()
                qty = spin_qty.value()
                if mat_id in used_mat_ids:
                    QMessageBox.warning(self, "Peringatan", f"Material {cb_mat.currentText()} dipilih lebih dari 1 kali dalam resep!")
                    return
                used_mat_ids.add(mat_id)
                resep_items.append({"material_id": mat_id, "jumlah_per_m3": qty})

        if not resep_items:
            QMessageBox.warning(self, "Peringatan", "Resep harus memiliki minimal 1 komposisi material!")
            return

        mutu_id = self.mutu_data.get("id") if self.mutu_data else None
        try:
            database.save_mutu_beton_with_resep(kode, nama, ket, resep_items, harga_jual, biaya_ops, mutu_id)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", f"Gagal menyimpan resep mutu: {str(e)}")


# ==============================================================================
# DIALOG EDITOR PROYEK
# ==============================================================================
class ProyekDialog(ModernDialog):
    def __init__(self, proyek_data=None, parent=None):
        title = "Edit Data Proyek" if proyek_data else "Tambah Proyek Baru"
        super().__init__(title, parent, min_width=460)
        self.proyek_data = proyek_data
        self.init_form()

    def init_form(self):
        grid = QGridLayout()
        grid.setSpacing(12)

        grid.addWidget(QLabel("Nama Proyek:*"), 0, 0)
        self.txt_nama = QLineEdit()
        self.txt_nama.setPlaceholderText("Contoh: Proyek Pelebaran Jembatan / Polres")
        grid.addWidget(self.txt_nama, 0, 1)

        grid.addWidget(QLabel("Lokasi Proyek:"), 1, 0)
        self.txt_lokasi = QLineEdit()
        self.txt_lokasi.setPlaceholderText("Contoh: Windusari / Puring")
        grid.addWidget(self.txt_lokasi, 1, 1)

        grid.addWidget(QLabel("Tipe Proyek:*"), 2, 0, Qt.AlignVCenter)
        tipe_btn_layout = QHBoxLayout()
        tipe_btn_layout.setSpacing(8)
        tipe_btn_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_tipe_luar = QPushButton("🏗️ Proyek Luar (Klien Eksternal)")
        self.btn_tipe_luar.setCheckable(True)
        self.btn_tipe_luar.setChecked(True)
        self.btn_tipe_luar.setCursor(Qt.PointingHandCursor)
        self.btn_tipe_luar.setMinimumHeight(36)

        self.btn_tipe_dalam = QPushButton("🏭 Proyek Dalam (Internal Perusahaan)")
        self.btn_tipe_dalam.setCheckable(True)
        self.btn_tipe_dalam.setCursor(Qt.PointingHandCursor)
        self.btn_tipe_dalam.setMinimumHeight(36)

        self.tipe_group = QButtonGroup(self)
        self.tipe_group.setExclusive(True)
        self.tipe_group.addButton(self.btn_tipe_luar, 0)
        self.tipe_group.addButton(self.btn_tipe_dalam, 1)

        style_luar = f"""
            QPushButton {{
                background-color: #F8FAFC;
                color: #475569;
                border: 1.5px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #EFF6FF;
                border-color: #93C5FD;
                color: #1D4ED8;
            }}
            QPushButton:checked {{
                background-color: {styles.COLOR_PRIMARY_LIGHT};
                color: #FFFFFF;
                border: 1.5px solid {styles.COLOR_PRIMARY_LIGHT};
                font-weight: 700;
            }}
        """
        style_dalam = f"""
            QPushButton {{
                background-color: #F8FAFC;
                color: #475569;
                border: 1.5px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #FFFBEB;
                border-color: #FDE68A;
                color: #B45309;
            }}
            QPushButton:checked {{
                background-color: #D97706;
                color: #FFFFFF;
                border: 1.5px solid #D97706;
                font-weight: 700;
            }}
        """
        self.btn_tipe_luar.setStyleSheet(style_luar)
        self.btn_tipe_dalam.setStyleSheet(style_dalam)

        tipe_btn_layout.addWidget(self.btn_tipe_luar, 1)
        tipe_btn_layout.addWidget(self.btn_tipe_dalam, 1)
        grid.addLayout(tipe_btn_layout, 2, 1)

        grid.addWidget(QLabel("Status Proyek:*"), 3, 0)
        self.cb_status = QComboBox()
        self.cb_status.setView(QListView())
        self.cb_status.addItem("Aktif (Sedang Berjalan)", "aktif")
        self.cb_status.addItem("Selesai (Arsip)", "selesai")
        grid.addWidget(self.cb_status, 3, 1)

        grid.addWidget(QLabel("Keterangan:"), 4, 0)
        self.txt_ket = QTextEdit()
        self.txt_ket.setPlaceholderText("Catatan penanggung jawab lapangan, rute armada, dll (opsional)")
        self.txt_ket.setMaximumHeight(70)
        grid.addWidget(self.txt_ket, 4, 1)

        self.content_layout.addLayout(grid)
        self.btn_save.clicked.connect(self.save)

        if self.proyek_data:
            self.txt_nama.setText(self.proyek_data.get("nama") or "")
            self.txt_lokasi.setText(self.proyek_data.get("lokasi") or "")
            tipe = self.proyek_data.get("tipe_proyek") or "luar"
            if str(tipe).lower() == "dalam":
                self.btn_tipe_dalam.setChecked(True)
            else:
                self.btn_tipe_luar.setChecked(True)
            stat = self.proyek_data.get("status") or "aktif"
            idx = self.cb_status.findData(stat)
            if idx >= 0: self.cb_status.setCurrentIndex(idx)
            self.txt_ket.setPlainText(self.proyek_data.get("keterangan") or "")

    def save(self):
        nama = self.txt_nama.text().strip()
        lokasi = self.txt_lokasi.text().strip()
        tipe = "dalam" if self.btn_tipe_dalam.isChecked() else "luar"
        status = self.cb_status.currentData()
        ket = self.txt_ket.toPlainText().strip()

        if not nama:
            QMessageBox.warning(self, "Peringatan", "Nama Proyek wajib diisi!")
            return

        p_id = self.proyek_data.get("id") if self.proyek_data else None
        try:
            database.save_proyek(nama, lokasi, status, ket, p_id, tipe_proyek=tipe)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", f"Gagal menyimpan data: {str(e)}")


# ==============================================================================
# MAIN MASTER DATA VIEW
# ==============================================================================
class MasterDataView(QWidget):
    data_changed = Signal()

    def __init__(self, user_session: dict = None, parent=None):
        super().__init__(parent)
        self.user_session = user_session or {}
        self.init_ui()

    @property
    def current_user_id(self) -> int:
        """Selalu baca user_id dari session terbaru (dinamis)"""
        uid = self.user_session.get("id")
        return int(uid) if uid else 1

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 16)
        main_layout.setSpacing(12)

        self.tabs = QTabWidget()
        self.tab_material = QWidget()
        self.tab_mutu = QWidget()
        self.tab_proyek = QWidget()

        self.setup_tab_material()
        self.setup_tab_mutu()
        self.setup_tab_proyek()

        self.tabs.addTab(self.tab_material, "Master Material & Harga")
        self.tabs.addTab(self.tab_mutu, "Mutu Beton, HPP & Harga Jual")
        self.tabs.addTab(self.tab_proyek, "Master Proyek")

        main_layout.addWidget(self.tabs)

    # --------------------------------------------------------------------------
    # TAB 1: MASTER MATERIAL
    # --------------------------------------------------------------------------
    def setup_tab_material(self):
        layout = QVBoxLayout(self.tab_material)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        top_bar = QHBoxLayout()
        lbl_info = QLabel("Daftar material batching plant, harga beli terkini, dan riwayat fluktuasi harga")
        lbl_info.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 13px;")
        top_bar.addWidget(lbl_info)
        top_bar.addStretch()

        self.txt_search_mat = QLineEdit()
        self.txt_search_mat.setPlaceholderText("Cari kode / nama material...")
        self.txt_search_mat.setClearButtonEnabled(True)
        self.txt_search_mat.setFixedWidth(240)
        self.txt_search_mat.textChanged.connect(self.load_materials)
        top_bar.addWidget(self.txt_search_mat)

        btn_add = PrimaryButton("+ Tambah Material")
        btn_add.clicked.connect(self.add_material)
        top_bar.addWidget(btn_add)
        layout.addLayout(top_bar)

        self.table_mat = ModernTableWidget([
            "No", "Kode Material", "Nama Material", "Satuan", "Harga Beli Terkini", 
            "Stok Anda", "Total Gudang", "Batas Minimum", "Keterangan", "Aksi"
        ])
        self.table_mat.setColumnWidth(0, 40)
        self.table_mat.setColumnWidth(1, 100)
        self.table_mat.setColumnWidth(2, 145)
        self.table_mat.setColumnWidth(3, 62)
        self.table_mat.setColumnWidth(4, 120)
        self.table_mat.setColumnWidth(5, 110)
        self.table_mat.setColumnWidth(6, 110)
        self.table_mat.setColumnWidth(7, 105)
        self.table_mat.setColumnWidth(9, 210)
        layout.addWidget(self.table_mat)

        self.load_materials()

    def load_materials(self):
        mats = database.get_all_materials()
        # Ambil stok individual user saat ini
        user_stok_map = {}
        try:
            user_stok_list = database.get_all_user_stok(self.current_user_id)
            user_stok_map = {row["material_id"]: float(row["stok_user"] or 0) for row in user_stok_list}
        except Exception:
            pass

        query = self.txt_search_mat.text().strip().lower() if hasattr(self, "txt_search_mat") else ""
        if query:
            mats = [
                m for m in mats
                if query in str(m.get("kode") or "").lower()
                or query in str(m.get("nama") or "").lower()
                or query in str(m.get("keterangan") or "").lower()
                or query in str(m.get("satuan") or "").lower()
            ]
        self.table_mat.setRowCount(len(mats))
        for r_idx, m in enumerate(mats):
            self.table_mat.setItem(r_idx, 0, QTableWidgetItem(str(r_idx + 1)))
            self.table_mat.setItem(r_idx, 1, QTableWidgetItem(str(m["kode"])))
            self.table_mat.setItem(r_idx, 2, QTableWidgetItem(str(m["nama"])))
            self.table_mat.setItem(r_idx, 3, QTableWidgetItem(str(m["satuan"])))
            
            hrg_item = QTableWidgetItem(styles.format_rupiah(m.get("harga_beli_terbaru") or 0))
            hrg_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_mat.setItem(r_idx, 4, hrg_item)

            stok_val = float(m.get("stok_saat_ini") or 0)
            stok_min = float(m.get("stok_minimum") or 0)
            my_stok = user_stok_map.get(m["id"], stok_val)

            # Kolom 5: Stok Anda (Individual Per User)
            my_stok_item = QTableWidgetItem(f"{styles.format_number(my_stok, 2)}")
            my_stok_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            font_my = my_stok_item.font()
            font_my.setBold(True)
            my_stok_item.setFont(font_my)
            if stok_min > 0 and my_stok <= stok_min:
                my_stok_item.setForeground(QColor("#F97316"))  # Orange warning
            elif my_stok > 0:
                my_stok_item.setForeground(QColor("#0EA5E9"))  # Biru sky
            else:
                my_stok_item.setForeground(QColor(styles.COLOR_DANGER))
            self.table_mat.setItem(r_idx, 5, my_stok_item)

            # Kolom 6: Stok Total Gudang (Shared)
            stok_item = QTableWidgetItem(f"{styles.format_number(stok_val, 2)}")
            stok_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            font_stok = stok_item.font()
            font_stok.setBold(True)
            stok_item.setFont(font_stok)
            if stok_min > 0 and stok_val <= stok_min:
                stok_item.setForeground(QColor(styles.COLOR_DANGER))
            else:
                stok_item.setForeground(QColor(styles.COLOR_SUCCESS))
            self.table_mat.setItem(r_idx, 6, stok_item)

            min_item = QTableWidgetItem(f"{styles.format_number(stok_min, 2)}")
            min_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_mat.setItem(r_idx, 7, min_item)
            
            self.table_mat.setItem(r_idx, 8, QTableWidgetItem(str(m["keterangan"] or "-")))

            action_widget = QWidget()
            act_lay = QHBoxLayout(action_widget)
            act_lay.setContentsMargins(4, 2, 4, 2)
            act_lay.setSpacing(6)

            btn_hist = TableDetailButton("Histori")
            btn_hist.clicked.connect(lambda _, data=m: self.view_material_history(data))

            btn_edit = TableEditButton("Edit")
            btn_edit.clicked.connect(lambda _, data=m: self.edit_material(data))

            btn_del = TableDeleteButton("Hapus")
            btn_del.clicked.connect(lambda _, data=m: self.delete_material(data))

            act_lay.addWidget(btn_hist)
            act_lay.addWidget(btn_edit)
            act_lay.addWidget(btn_del)
            self.table_mat.setCellWidget(r_idx, 9, action_widget)

    def view_material_history(self, data):
        dlg = RiwayatHargaMaterialDialog(material_data=data, parent=self)
        dlg.exec()

    def add_material(self):
        dlg = MaterialDialog(parent=self)
        if dlg.exec():
            self.load_materials()
            self.data_changed.emit()

    def edit_material(self, data):
        dlg = MaterialDialog(material_data=data, parent=self)
        if dlg.exec():
            self.load_materials()
            self.data_changed.emit()

    def delete_material(self, data):
        if confirm_dialog(self, "Konfirmasi Hapus", f"Apakah Anda yakin ingin menghapus material '{data['nama']}'?"):
            ok, msg = database.delete_material(data["id"])
            if ok:
                QMessageBox.information(self, "Sukses", msg)
                self.load_materials()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Peringatan", msg)

    # --------------------------------------------------------------------------
    # TAB 2: MUTU BETON, RESEP, HPP & HARGA JUAL
    # --------------------------------------------------------------------------
    def setup_tab_mutu(self):
        layout = QVBoxLayout(self.tab_mutu)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        top_bar = QHBoxLayout()
        lbl_info = QLabel("Kelola mutu beton, racikan resep per 1 m³, kalkulasi HPP real-time, dan margin laba")
        lbl_info.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 13px;")
        top_bar.addWidget(lbl_info)
        top_bar.addStretch()

        btn_view_std = SecondaryButton("📊 Lihat Tabel Acuan SNI/AKP")
        btn_view_std.clicked.connect(self.view_tabel_standar)
        top_bar.addWidget(btn_view_std)

        btn_add = PrimaryButton("+ Tambah Mutu & Resep")
        btn_add.clicked.connect(self.add_mutu)
        top_bar.addWidget(btn_add)
        layout.addLayout(top_bar)

        split_lay = QHBoxLayout()
        split_lay.setSpacing(14)

        # Left: Tabel Mutu Beton Lengkap dengan HPP & Harga Jual
        left_frame = QFrame()
        left_frame.setProperty("class", "CardWidget")
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(12, 12, 12, 12)
        
        lbl_lm_title = QLabel("DAFTAR MUTU BETON & MARGIN LABA (Klik baris untuk lihat rincian resep):")
        lbl_lm_title.setStyleSheet(f"font-weight: 700; color: {styles.COLOR_PRIMARY_DARK}; font-size: 12px;")
        left_layout.addWidget(lbl_lm_title)

        self.table_mutu = ModernTableWidget([
            "Kode Mutu", "HPP per m³", "Harga Jual / m³", "Laba (Rp)", "Margin (%)", "Aksi"
        ])
        self.table_mutu.setColumnWidth(0, 95)
        self.table_mutu.setColumnWidth(1, 115)
        self.table_mutu.setColumnWidth(2, 120)
        self.table_mutu.setColumnWidth(3, 110)
        self.table_mutu.setColumnWidth(4, 85)
        self.table_mutu.setColumnWidth(5, 140)
        self.table_mutu.itemSelectionChanged.connect(self.on_mutu_selected)
        left_layout.addWidget(self.table_mutu)
        split_lay.addWidget(left_frame, 3)

        # Right: Tabel Resep Detail
        right_frame = QFrame()
        right_frame.setProperty("class", "CardWidget")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(12, 12, 12, 12)

        self.lbl_selected_mutu_title = QLabel("RINCIAN RESEP MATERIAL (Per 1 m³):")
        self.lbl_selected_mutu_title.setStyleSheet(f"font-weight: 700; color: {styles.COLOR_PRIMARY_DARK}; font-size: 12px;")
        right_layout.addWidget(self.lbl_selected_mutu_title)

        self.table_detail_resep = ModernTableWidget(["Material", "Takaran / m³", "Satuan", "Biaya Subtotal"])
        self.table_detail_resep.setColumnWidth(0, 130)
        self.table_detail_resep.setColumnWidth(1, 100)
        self.table_detail_resep.setColumnWidth(2, 55)
        self.table_detail_resep.setColumnWidth(3, 110)
        right_layout.addWidget(self.table_detail_resep)
        split_lay.addWidget(right_frame, 2)

        layout.addLayout(split_lay)
        self.load_mutu_beton()

    def load_mutu_beton(self):
        mutus = database.get_all_mutu_beton()
        self.table_mutu.setRowCount(len(mutus))
        for r_idx, m in enumerate(mutus):
            self.table_mutu.setItem(r_idx, 0, QTableWidgetItem(str(m["kode"])))
            
            hpp_item = QTableWidgetItem(styles.format_rupiah(m.get("hpp_per_m3") or 0))
            hpp_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_mutu.setItem(r_idx, 1, hpp_item)

            jual_item = QTableWidgetItem(styles.format_rupiah(m.get("harga_jual_per_m3") or 0))
            jual_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_mutu.setItem(r_idx, 2, jual_item)

            laba = float(m.get("laba_per_m3") or 0)
            laba_item = QTableWidgetItem(styles.format_rupiah(laba))
            laba_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if laba < 0: laba_item.setForeground(Qt.red)
            else: laba_item.setForeground(Qt.darkGreen)
            self.table_mutu.setItem(r_idx, 3, laba_item)

            pct = float(m.get("margin_persen") or 0)
            pct_item = QTableWidgetItem(f"{pct:.1f}%")
            pct_item.setTextAlignment(Qt.AlignCenter)
            self.table_mutu.setItem(r_idx, 4, pct_item)

            action_widget = QWidget()
            act_lay = QHBoxLayout(action_widget)
            act_lay.setContentsMargins(4, 2, 4, 2)
            act_lay.setSpacing(6)

            btn_edit = TableEditButton("Edit")
            btn_edit.clicked.connect(lambda _, data=m: self.edit_mutu(data))

            btn_del = TableDeleteButton("Hapus")
            btn_del.clicked.connect(lambda _, data=m: self.delete_mutu(data))

            act_lay.addWidget(btn_edit)
            act_lay.addWidget(btn_del)
            self.table_mutu.setCellWidget(r_idx, 5, action_widget)

        if mutus:
            self.table_mutu.selectRow(0)

    def on_mutu_selected(self):
        selected_rows = self.table_mutu.selectionModel().selectedRows()
        if not selected_rows:
            self.table_detail_resep.setRowCount(0)
            return

        row_idx = selected_rows[0].row()
        mutus = database.get_all_mutu_beton()
        if row_idx < len(mutus):
            selected_mutu = mutus[row_idx]
            self.lbl_selected_mutu_title.setText(f"RINCIAN RESEP & HPP: {selected_mutu['kode'].upper()} (Per 1 m³)")
            
            resep = database.get_resep_by_mutu_id(selected_mutu["id"])
            self.table_detail_resep.setRowCount(len(resep))
            for r_idx, item in enumerate(resep):
                self.table_detail_resep.setItem(r_idx, 0, QTableWidgetItem(str(item["material_nama"])))
                
                qty_item = QTableWidgetItem(f"{styles.format_number(item['jumlah_per_m3'], 2)}")
                qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table_detail_resep.setItem(r_idx, 1, qty_item)
                
                self.table_detail_resep.setItem(r_idx, 2, QTableWidgetItem(str(item["material_satuan"])))

                sub_item = QTableWidgetItem(styles.format_rupiah(item.get("subtotal_biaya") or 0))
                sub_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table_detail_resep.setItem(r_idx, 3, sub_item)

    def add_mutu(self):
        dlg = MutuBetonDialog(parent=self)
        if dlg.exec():
            self.load_mutu_beton()
            self.data_changed.emit()

    def edit_mutu(self, data):
        dlg = MutuBetonDialog(mutu_data=data, parent=self)
        if dlg.exec():
            self.load_mutu_beton()
            self.data_changed.emit()

    def delete_mutu(self, data):
        if confirm_dialog(self, "Konfirmasi Hapus", f"Apakah Anda yakin ingin menghapus Mutu Beton '{data['kode']}'?"):
            ok, msg = database.delete_mutu_beton(data["id"])
            if ok:
                QMessageBox.information(self, "Sukses", msg)
                self.load_mutu_beton()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Peringatan", msg)

    def view_tabel_standar(self):
        dlg = TabelKodeBetonStandarDialog(parent=self)
        dlg.exec()

    def sync_standar_resep(self):
        if confirm_dialog(
            self, 
            "Konfirmasi Reset Resep Standar", 
            "Apakah Anda yakin ingin menyinkronkan dan mereset resep seluruh mutu beton (K-100 s.d K-400) ke standar Tabel Kode Beton Acuan AKP?"
        ):
            mutu_c, resep_c = database.sinkronkan_kode_beton_standar()
            QMessageBox.information(
                self, 
                "Sukses", 
                f"Berhasil menyinkronkan {mutu_c} mutu beton dan {resep_c} resep material standar."
            )
            self.load_mutu_beton()
            self.data_changed.emit()

    # --------------------------------------------------------------------------
    # TAB 3: MASTER PROYEK
    # --------------------------------------------------------------------------
    def setup_tab_proyek(self):
        layout = QVBoxLayout(self.tab_proyek)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        top_bar = QHBoxLayout()
        lbl_info = QLabel("Daftar proyek pelanggan / lokasi pengecoran batching plant")
        lbl_info.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 13px;")
        top_bar.addWidget(lbl_info)
        top_bar.addStretch()

        btn_add = PrimaryButton("+ Tambah Proyek")
        btn_add.clicked.connect(self.add_proyek)
        top_bar.addWidget(btn_add)
        layout.addLayout(top_bar)

        self.table_proyek = ModernTableWidget(["No", "Nama Proyek", "Tipe", "Lokasi", "Status", "Keterangan", "Aksi"])
        self.table_proyek.setColumnWidth(0, 45)
        self.table_proyek.setColumnWidth(1, 185)
        self.table_proyek.setColumnWidth(2, 110)
        self.table_proyek.setColumnWidth(3, 130)
        self.table_proyek.setColumnWidth(4, 90)
        self.table_proyek.setColumnWidth(6, 150)
        layout.addWidget(self.table_proyek)

        self.load_proyek()

    def load_proyek(self):
        proyeks = database.get_all_proyek()
        self.table_proyek.setRowCount(len(proyeks))
        for r_idx, p in enumerate(proyeks):
            self.table_proyek.setItem(r_idx, 0, QTableWidgetItem(str(r_idx + 1)))
            self.table_proyek.setItem(r_idx, 1, QTableWidgetItem(str(p["nama"])))

            # Kolom Tipe badge
            tipe_val = str(p.get("tipe_proyek") or "luar").lower()
            tipe_badge = BadgeLabel("Proyek Luar" if tipe_val == "luar" else "Proyek Dalam",
                                    "primary" if tipe_val == "luar" else "warning")
            self.table_proyek.setCellWidget(r_idx, 2, tipe_badge)

            self.table_proyek.setItem(r_idx, 3, QTableWidgetItem(str(p["lokasi"] or "-")))
            
            is_active = p["status"] == "aktif"
            badge = BadgeLabel("Aktif" if is_active else "Selesai", "success" if is_active else "info")
            self.table_proyek.setCellWidget(r_idx, 4, badge)

            self.table_proyek.setItem(r_idx, 5, QTableWidgetItem(str(p["keterangan"] or "-")))

            action_widget = QWidget()
            act_lay = QHBoxLayout(action_widget)
            act_lay.setContentsMargins(4, 2, 4, 2)
            act_lay.setSpacing(6)

            btn_edit = TableEditButton("Edit")
            btn_edit.clicked.connect(lambda _, data=p: self.edit_proyek(data))

            btn_del = TableDeleteButton("Hapus")
            btn_del.clicked.connect(lambda _, data=p: self.delete_proyek(data))

            act_lay.addWidget(btn_edit)
            act_lay.addWidget(btn_del)
            self.table_proyek.setCellWidget(r_idx, 6, action_widget)

    def add_proyek(self):
        dlg = ProyekDialog(parent=self)
        if dlg.exec():
            self.load_proyek()
            self.data_changed.emit()

    def edit_proyek(self, data):
        dlg = ProyekDialog(proyek_data=data, parent=self)
        if dlg.exec():
            self.load_proyek()
            self.data_changed.emit()

    def delete_proyek(self, data):
        if confirm_dialog(self, "Konfirmasi Hapus", f"Apakah Anda yakin ingin menghapus proyek '{data['nama']}'?"):
            ok, msg = database.delete_proyek(data["id"])
            if ok:
                QMessageBox.information(self, "Sukses", msg)
                self.load_proyek()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Peringatan", msg)

    def refresh_all(self):
        self.load_materials()
        self.load_mutu_beton()
        self.load_proyek()

"""
Operasional Kendaraan & Manajemen Armada View untuk AKP Beton Desktop Application
Mengelola data armada kendaraan, nomor plat, jenis kendaraan, driver default,
pemantauan status operasional (standby / operasional / maintenance),
serta riwayat pengeluaran operasional (BBM, Servis, Sparepart, Uang Jalan),
rekapitulasi efisiensi armada, dan laporan biaya operasional kendaraan (Export Excel & PDF).
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame,
    QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit, QGridLayout,
    QHeaderView, QTableWidgetItem, QMessageBox, QListView, QSizePolicy,
    QTabWidget, QDateEdit, QScrollArea, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QDate
from components import (
    ModernTableWidget, SectionHeader, ModernDialog, confirm_dialog, BadgeLabel, StatCard,
    PrimaryButton, SecondaryButton, SuccessButton, DangerButton,
    TableEditButton, TableDeleteButton, TableDetailButton
)
import styles
import database
import export_service


# ==============================================================================
# 1. DIALOG FORM TAMBAH / EDIT KENDARAAN
# ==============================================================================
class KendaraanDialog(ModernDialog):
    def __init__(self, kendaraan_data: Optional[Dict[str, Any]] = None, parent=None):
        title = "Edit Data Kendaraan" if kendaraan_data else "Tambah Armada Kendaraan Baru"
        super().__init__(title, parent, min_width=500)
        self.kendaraan_data = kendaraan_data
        self.init_form()

    def init_form(self):
        grid = QGridLayout()
        grid.setSpacing(12)

        # 1. Plat Nomor
        grid.addWidget(QLabel("No. Plat Kendaraan:*"), 0, 0, Qt.AlignVCenter)
        self.txt_plat = QLineEdit()
        self.txt_plat.setPlaceholderText("Contoh: AA 8456 CB")
        grid.addWidget(self.txt_plat, 0, 1)

        # 2. Nama / Kode Unit
        grid.addWidget(QLabel("Nama / Kode Unit:"), 1, 0, Qt.AlignVCenter)
        self.txt_nama = QLineEdit()
        self.txt_nama.setPlaceholderText("Contoh: Truk Mixer TM-01 / Hino 500")
        grid.addWidget(self.txt_nama, 1, 1)

        # 3. Jenis Kendaraan
        grid.addWidget(QLabel("Jenis Kendaraan:*"), 2, 0, Qt.AlignVCenter)
        self.cb_jenis = QComboBox()
        self.cb_jenis.setView(QListView())
        self.cb_jenis.setEditable(True)
        self.cb_jenis.addItems([
            "Truk Mixer",
            "Dump Truck",
            "Wheel Loader",
            "Truk Tronton",
            "Mobil Operasional",
            "Concrete Pump",
            "Lainnya"
        ])
        grid.addWidget(self.cb_jenis, 2, 1)

        # 4. Status Kendaraan
        grid.addWidget(QLabel("Status Armada:*"), 3, 0, Qt.AlignVCenter)
        self.cb_status = QComboBox()
        self.cb_status.setView(QListView())
        self.cb_status.addItem("Tersedia (Standby di Plant)", "tersedia")
        self.cb_status.addItem("Sedang Operasional (Jalan / Kirim)", "operasional")
        self.cb_status.addItem("Perbaikan / Servis (Maintenance)", "maintenance")
        self.cb_status.addItem("Nonaktif (Arsip)", "nonaktif")
        grid.addWidget(self.cb_status, 3, 1)

        # 5. Keterangan Operasional
        grid.addWidget(QLabel("Keterangan Operasional:"), 4, 0, Qt.AlignVCenter)
        self.txt_ket_op = QLineEdit()
        self.txt_ket_op.setPlaceholderText("Contoh: Pengiriman Proyek Jembatan Kali Progo")
        grid.addWidget(self.txt_ket_op, 4, 1)

        # 6. Catatan Tambahan
        grid.addWidget(QLabel("Catatan Tambahan:"), 5, 0, Qt.AlignVCenter)
        self.txt_catatan = QLineEdit()
        self.txt_catatan.toPlainText = self.txt_catatan.text
        self.txt_catatan.setPlaceholderText("Spesifikasi teknis, nomor rangka, tanggal servis, dll (opsional)")
        grid.addWidget(self.txt_catatan, 5, 1)

        self.content_layout.addLayout(grid)
        self.btn_save.setText("Simpan Data")
        self.btn_save.clicked.connect(self.save)

        # Isi data jika mode edit
        if self.kendaraan_data:
            d = self.kendaraan_data
            self.txt_plat.setText(d.get("no_plat") or "")
            self.txt_nama.setText(d.get("nama_kendaraan") or "")
            
            j_idx = self.cb_jenis.findText(d.get("jenis_kendaraan") or "")
            if j_idx >= 0:
                self.cb_jenis.setCurrentIndex(j_idx)
            else:
                self.cb_jenis.setEditText(d.get("jenis_kendaraan") or "")

            s_idx = self.cb_status.findData(d.get("status") or "tersedia")
            if s_idx >= 0:
                self.cb_status.setCurrentIndex(s_idx)

            self.txt_ket_op.setText(d.get("keterangan_operasional") or "")
            self.txt_catatan.setText(d.get("catatan") or "")

    def save(self):
        plat = self.txt_plat.text().strip().upper()
        nama = self.txt_nama.text().strip()
        jenis = self.cb_jenis.currentText().strip()
        kap = float(self.kendaraan_data.get("kapasitas_m3") or 0) if self.kendaraan_data else 0.0
        driver = ""
        status = self.cb_status.currentData() or "tersedia"
        ket_op = self.txt_ket_op.text().strip()
        catatan = self.txt_catatan.text().strip()

        if not plat:
            QMessageBox.warning(self, "Peringatan", "Nomor plat kendaraan wajib diisi!")
            return
        if not jenis:
            QMessageBox.warning(self, "Peringatan", "Jenis kendaraan wajib dipilih/diisi!")
            return

        k_id = self.kendaraan_data["id"] if self.kendaraan_data else None
        try:
            res_id = database.save_kendaraan(
                no_plat=plat, nama_kendaraan=nama, jenis_kendaraan=jenis,
                kapasitas_m3=kap, driver_default=driver, status=status,
                keterangan_operasional=ket_op, catatan=catatan, kendaraan_id=k_id
            )
            if res_id:
                self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Gagal", f"Gagal menyimpan armada: {str(e)}")


# ==============================================================================
# 2. DIALOG FORM UBAH STATUS OPERASIONAL CEPAT
# ==============================================================================
class StatusOperasionalDialog(ModernDialog):
    def __init__(self, kendaraan_data: Dict[str, Any], parent=None):
        plat = kendaraan_data.get("no_plat")
        nama = kendaraan_data.get("nama_kendaraan") or plat
        super().__init__(f"Update Status: {nama} ({plat})", parent, min_width=460)
        self.kendaraan_data = kendaraan_data
        self.init_form()

    def init_form(self):
        d = self.kendaraan_data
        grid = QGridLayout()
        grid.setSpacing(12)

        # Info Ringkas
        lbl_plat = QLabel(f"<b>Armada:</b> {d.get('nama_kendaraan') or '-'} | <b>No. Plat:</b> {d.get('no_plat')}")
        lbl_plat.setStyleSheet(f"font-size: 13px; color: {styles.COLOR_PRIMARY_DARK};")
        grid.addWidget(lbl_plat, 0, 0, 1, 2)

        lbl_jenis = QLabel(f"<b>Jenis Armada:</b> {d.get('jenis_kendaraan') or '-'}")
        lbl_jenis.setStyleSheet("color: #64748B; font-size: 12px; margin-bottom: 6px;")
        grid.addWidget(lbl_jenis, 1, 0, 1, 2)

        # Status Dropdown
        grid.addWidget(QLabel("Status Operasional:*"), 2, 0, Qt.AlignVCenter)
        self.cb_status = QComboBox()
        self.cb_status.setView(QListView())
        self.cb_status.addItem("Siap / Standby (Plant)", "tersedia")
        self.cb_status.addItem("Sedang Operasional (Kirim / Lapangan)", "operasional")
        self.cb_status.addItem("Dalam Perbaikan / Servis (Maintenance)", "maintenance")
        self.cb_status.addItem("Nonaktif", "nonaktif")

        cur_st = d.get("status") or "tersedia"
        st_idx = self.cb_status.findData(cur_st)
        if st_idx >= 0:
            self.cb_status.setCurrentIndex(st_idx)
        grid.addWidget(self.cb_status, 2, 1)

        # Keterangan Operasional
        grid.addWidget(QLabel("Keterangan Penugasan:"), 3, 0, Qt.AlignVCenter)
        self.txt_ket = QLineEdit()
        self.txt_ket.setPlaceholderText("Contoh: Pengiriman ke Proyek Jembatan Kali Progo (SJ: SJ-001)")
        self.txt_ket.setText(d.get("keterangan_operasional") or "")
        grid.addWidget(self.txt_ket, 3, 1)

        # Quick Preset Buttons
        preset_box = QHBoxLayout()
        preset_box.setSpacing(8)

        btn_p_standby = SecondaryButton("Set Standby di Plant")
        btn_p_standby.setFixedHeight(28)
        btn_p_standby.setStyleSheet(btn_p_standby.styleSheet() + "font-size: 11px;")
        btn_p_standby.clicked.connect(self.set_preset_standby)
        preset_box.addWidget(btn_p_standby)

        btn_p_kirim = SecondaryButton("Set Sedang Kirim")
        btn_p_kirim.setFixedHeight(28)
        btn_p_kirim.setStyleSheet(btn_p_kirim.styleSheet() + "font-size: 11px;")
        btn_p_kirim.clicked.connect(self.set_preset_kirim)
        preset_box.addWidget(btn_p_kirim)

        grid.addLayout(preset_box, 4, 1)

        self.content_layout.addLayout(grid)
        self.btn_save.setText("Simpan Status")
        self.btn_save.clicked.connect(self.save)

    def set_preset_standby(self):
        idx = self.cb_status.findData("tersedia")
        if idx >= 0:
            self.cb_status.setCurrentIndex(idx)
        self.txt_ket.setText("Standby di Batching Plant")

    def set_preset_kirim(self):
        idx = self.cb_status.findData("operasional")
        if idx >= 0:
            self.cb_status.setCurrentIndex(idx)
        if not self.txt_ket.text().strip():
            self.txt_ket.setText("Sedang dalam penugasan pengiriman lapangan")

    def save(self):
        k_id = self.kendaraan_data["id"]
        status = self.cb_status.currentData() or "tersedia"
        ket = self.txt_ket.text().strip()

        if status == "tersedia" and not ket:
            ket = ""

        try:
            database.update_status_operasional_kendaraan(k_id, status, ket)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal mengupdate status: {str(e)}")


# ==============================================================================
# 3. DIALOG PENCATATAN BIAYA OPERASIONAL KENDARAAN
# ==============================================================================
class BiayaKendaraanDialog(ModernDialog):
    def __init__(self, biaya_data: Optional[Dict[str, Any]] = None, parent=None):
        title = "Edit Biaya Operasional Mobil" if biaya_data else "Catat Biaya Operasional Kendaraan"
        super().__init__(title, parent, min_width=520)
        self.biaya_data = biaya_data
        self.init_form()

    def init_form(self):
        grid = QGridLayout()
        grid.setSpacing(12)

        # 1. Tanggal
        grid.addWidget(QLabel("Tanggal Nota / Bukti:*"), 0, 0, Qt.AlignVCenter)
        self.dt_tgl = QDateEdit()
        self.dt_tgl.setCalendarPopup(True)
        self.dt_tgl.setDate(QDate.currentDate())
        self.dt_tgl.setDisplayFormat("yyyy-MM-dd")
        grid.addWidget(self.dt_tgl, 0, 1)

        # 2. Pilih Armada Kendaraan
        grid.addWidget(QLabel("Unit Kendaraan:*"), 1, 0, Qt.AlignVCenter)
        self.cb_kendaraan = QComboBox()
        self.cb_kendaraan.setView(QListView())
        
        self.fleet = database.get_all_kendaraan()
        for k in self.fleet:
            np = k.get("no_plat") or ""
            nm = k.get("nama_kendaraan") or ""
            label = f"{np} - {nm}" if nm else np
            self.cb_kendaraan.addItem(label, k["id"])
        grid.addWidget(self.cb_kendaraan, 1, 1)

        # 3. Kategori Biaya
        grid.addWidget(QLabel("Kategori Biaya:*"), 2, 0, Qt.AlignVCenter)
        self.cb_kategori = QComboBox()
        self.cb_kategori.setView(QListView())
        self.cb_kategori.setEditable(True)
        self.cb_kategori.addItems([
            "Servis & Perawatan Bengkel",
            "Sparepart & Oli Mesin",
            "Penggantian Ban",
            "Uang Jalan & Supir",
            "Pajak & Uji KIR",
            "Cuci & Kebersihan Mobil",
            "Retribusi & Tol",
            "Lain-lain Operasional"
        ])
        grid.addWidget(self.cb_kategori, 2, 1)

        # 4. No. Nota / Kuitansi
        grid.addWidget(QLabel("No. Nota / Bukti:"), 3, 0, Qt.AlignVCenter)
        self.txt_nota = QLineEdit()
        self.txt_nota.setPlaceholderText("Contoh: NOTA-BENGKEL-01 / KW-102")
        grid.addWidget(self.txt_nota, 3, 1)

        # 5. SPBU / Bengkel / Penerima
        grid.addWidget(QLabel("Nama Bengkel / Toko:"), 4, 0, Qt.AlignVCenter)
        self.txt_toko = QLineEdit()
        self.txt_toko.setPlaceholderText("Contoh: Bengkel Jaya Motor / Toko Sparepart")
        grid.addWidget(self.txt_toko, 4, 1)

        # 6. Nominal Biaya
        grid.addWidget(QLabel("Nominal Biaya (Rp):*"), 5, 0, Qt.AlignVCenter)
        self.spin_nominal = QDoubleSpinBox()
        self.spin_nominal.setRange(100, 10_000_000_000.0)
        self.spin_nominal.setDecimals(0)
        self.spin_nominal.setSingleStep(50000)
        self.spin_nominal.setValue(250000)
        self.spin_nominal.setGroupSeparatorShown(True)
        grid.addWidget(self.spin_nominal, 5, 1)

        # 7. Keterangan / Rincian
        grid.addWidget(QLabel("Rincian / Keterangan:*"), 6, 0, Qt.AlignVCenter)
        self.txt_ket = QLineEdit()
        self.txt_ket.toPlainText = self.txt_ket.text
        self.txt_ket.setPlaceholderText("Contoh: Servis rutin, ganti oli mesin, perbaikan rem, dll.")
        grid.addWidget(self.txt_ket, 6, 1)

        # Notifikasi integrasi kas plant
        lbl_info = QLabel("<b>Integrasi Kas Plant:</b> Pengeluaran ini otomatis memotong Saldo Kas Plant dan dicatat ke Buku Kas Umum & Kas Kantor.")
        lbl_info.setStyleSheet(f"""
            background-color: {styles.COLOR_INFO_BG};
            color: {styles.COLOR_INFO};
            border: 1px solid #BAE6FD;
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 11px;
        """)
        lbl_info.setWordWrap(True)
        grid.addWidget(lbl_info, 7, 0, 1, 2)

        self.content_layout.addLayout(grid)
        self.btn_save.setText("Simpan Biaya")
        self.btn_save.clicked.connect(self.save)

        # Isi data jika mode edit
        if self.biaya_data:
            d = self.biaya_data
            if d.get("tanggal"):
                self.dt_tgl.setDate(QDate.fromString(str(d["tanggal"])[:10], "yyyy-MM-dd"))
            if d.get("kendaraan_id"):
                idx = self.cb_kendaraan.findData(d["kendaraan_id"])
                if idx >= 0:
                    self.cb_kendaraan.setCurrentIndex(idx)

            k_idx = self.cb_kategori.findText(d.get("kategori") or "")
            if k_idx >= 0:
                self.cb_kategori.setCurrentIndex(k_idx)
            else:
                self.cb_kategori.setEditText(d.get("kategori") or "")

            self.txt_nota.setText(d.get("nomor_nota") or "")
            self.txt_toko.setText(d.get("penerima_toko") or "")
            self.spin_nominal.setValue(float(d.get("nominal") or 0))
            self.txt_ket.setText(d.get("keterangan") or "")

    def save(self):
        tgl = self.dt_tgl.date().toString("yyyy-MM-dd")
        k_id = self.cb_kendaraan.currentData()
        kategori = self.cb_kategori.currentText().strip()
        nota = self.txt_nota.text().strip()
        toko = self.txt_toko.text().strip()
        nominal = self.spin_nominal.value()
        ket = self.txt_ket.text().strip()

        if not k_id:
            QMessageBox.warning(self, "Peringatan", "Silakan pilih armada kendaraan yang dituju!")
            return
        if not kategori:
            QMessageBox.warning(self, "Peringatan", "Kategori biaya wajib ditentukan!")
            return
        if nominal <= 0:
            QMessageBox.warning(self, "Peringatan", "Nominal biaya harus lebih besar dari Rp 0!")
            return
        if not ket:
            QMessageBox.warning(self, "Peringatan", "Rincian / keterangan pengeluaran wajib diisi!")
            return

        try:
            if self.biaya_data:
                database.update_kas_kantor(
                    kas_kantor_id=self.biaya_data["id"],
                    tanggal=tgl, nominal=nominal, kategori=kategori,
                    nomor_nota=nota, penerima_toko=toko, keterangan=ket,
                    kendaraan_id=k_id, driver="", proyek_id=None,
                    pengiriman_id=None
                )
            else:
                database.catat_kas_kantor(
                    tanggal=tgl, nominal=nominal, kategori=kategori,
                    nomor_nota=nota, penerima_toko=toko, keterangan=ket,
                    kendaraan_id=k_id, driver="", proyek_id=None,
                    pengiriman_id=None
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal mencatat biaya kendaraan: {str(e)}")


# ==============================================================================
# 4. DIALOG DETAIL TRANSAKSI BIAYA
# ==============================================================================
class DetailBiayaDialog(ModernDialog):
    """Dialog detail transaksi pengeluaran operasional kendaraan"""
    def __init__(self, biaya_id: int, parent=None):
        super().__init__("Detail Pengeluaran Kendaraan", parent, min_width=520)
        self.biaya_id = biaya_id
        self.init_detail()

    def init_detail(self):
        data = database.get_biaya_kendaraan_by_id(self.biaya_id)
        if not data:
            self.content_layout.addWidget(QLabel("Data transaksi tidak ditemukan."))
            return

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)

        # Header Nominal
        nom = float(data.get("nominal") or 0)
        nom_frame = QFrame()
        nom_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #F8FAFC;
                border: 1.5px solid {styles.COLOR_BORDER};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        nom_lay = QVBoxLayout(nom_frame)
        nom_lay.setContentsMargins(4, 4, 4, 4)
        nom_lay.setSpacing(2)

        lbl_n_title = QLabel("NOMINAL PENGELUARAN")
        lbl_n_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B;")
        nom_lay.addWidget(lbl_n_title)

        lbl_n_val = QLabel(styles.format_rupiah(nom))
        lbl_n_val.setStyleSheet("font-size: 20px; font-weight: 800; color: #1E3A8A;")
        nom_lay.addWidget(lbl_n_val)

        self.content_layout.addWidget(nom_frame)
        self.content_layout.addSpacing(8)

        # Detail Rows
        rows = [
            ("Tanggal Bukti", str(data.get("tanggal") or "-")),
            ("Nomor Nota / SPBU", str(data.get("nomor_nota") or "-")),
            ("Armada / No. Plat", f"{data.get('no_plat') or '-'} ({data.get('nama_kendaraan') or ''})"),
            ("Jenis Kendaraan", str(data.get("jenis_kendaraan") or "-")),
            ("Kategori Biaya", str(data.get("kategori") or "-")),
            ("Bengkel / SPBU / Toko", str(data.get("penerima_toko") or "-")),
            ("Keterangan Rinci", str(data.get("keterangan") or "-"))
        ]

        for idx, (label, val) in enumerate(rows):
            lbl_k = QLabel(f"<b>{label}:</b>")
            lbl_k.setStyleSheet("color: #475569; font-size: 12px;")
            lbl_v = QLabel(val)
            lbl_v.setStyleSheet("color: #0F172A; font-size: 12px; font-weight: 600;")
            lbl_v.setWordWrap(True)
            grid.addWidget(lbl_k, idx, 0, Qt.AlignTop)
            grid.addWidget(lbl_v, idx, 1, Qt.AlignTop)

        grid.setColumnMinimumWidth(0, 140)
        self.content_layout.addLayout(grid)
        self.btn_save.setText("Tutup")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.setVisible(False)


# ==============================================================================
# 5. DIALOG DETAIL ARMADA & RIWAYAT BIAYA UNIT
# ==============================================================================
class DetailKendaraanDialog(ModernDialog):
    """Dialog detail spesifikasi armada serta daftar pengeluaran operasional per unit"""
    def __init__(self, kendaraan_data: Dict[str, Any], parent=None):
        plat = kendaraan_data.get("no_plat") or ""
        nama = kendaraan_data.get("nama_kendaraan") or plat
        super().__init__(f"Detail Armada: {nama} ({plat})", parent, min_width=720)
        self.kendaraan_data = kendaraan_data
        self.init_detail()

    def init_detail(self):
        d = self.kendaraan_data
        k_id = d.get("id") or d.get("kendaraan_id")

        # Info Header Grid
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #F8FAFC;
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        info_lay = QGridLayout(info_frame)
        info_lay.setSpacing(8)

        st = str(d.get("status") or "tersedia")
        badge = BadgeLabel(st.capitalize(), "primary" if st == "operasional" else "success" if st == "tersedia" else "warning")

        info_lay.addWidget(QLabel("<b>No. Plat:</b>"), 0, 0)
        info_lay.addWidget(QLabel(str(d.get("no_plat") or "-")), 0, 1)

        info_lay.addWidget(QLabel("<b>Nama Unit:</b>"), 0, 2)
        info_lay.addWidget(QLabel(str(d.get("nama_kendaraan") or "-")), 0, 3)

        info_lay.addWidget(QLabel("<b>Jenis:</b>"), 1, 0)
        info_lay.addWidget(QLabel(str(d.get("jenis_kendaraan") or "-")), 1, 1)

        info_lay.addWidget(QLabel("<b>Status Armada:</b>"), 1, 2)
        info_lay.addWidget(badge, 1, 3)

        kap_val = float(d.get('kapasitas_m3') or 0)
        kap_display = f"{styles.format_number(kap_val, 1)} m³" if kap_val > 0 else "-"
        info_lay.addWidget(QLabel("<b>Kapasitas:</b>"), 2, 0)
        info_lay.addWidget(QLabel(kap_display), 2, 1)

        self.content_layout.addWidget(info_frame)
        self.content_layout.addSpacing(10)

        # Riwayat Biaya Unit Ini
        lbl_tbl = QLabel("DAFTAR RIWAYAT PENGELUARAN OPERASIONAL UNIT INI:")
        lbl_tbl.setStyleSheet(f"font-weight: 700; color: {styles.COLOR_PRIMARY_DARK}; font-size: 11.5px;")
        self.content_layout.addWidget(lbl_tbl)

        table = ModernTableWidget(["Tanggal", "No. Nota", "Kategori", "Nominal (Rp)", "SPBU / Bengkel", "Driver", "Keterangan"])
        table.setMinimumHeight(240)
        
        trx_list = database.get_biaya_kendaraan_list(kendaraan_id=k_id)
        table.setRowCount(len(trx_list))
        total_unit = 0.0

        for r_idx, r in enumerate(trx_list):
            nom = float(r.get("nominal") or 0)
            total_unit += nom

            table.setItem(r_idx, 0, QTableWidgetItem(str(r.get("tanggal") or "-")))
            table.setItem(r_idx, 1, QTableWidgetItem(str(r.get("nomor_nota") or "-")))
            table.setItem(r_idx, 2, QTableWidgetItem(str(r.get("kategori") or "-")))

            nom_item = QTableWidgetItem(styles.format_rupiah(nom))
            nom_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            nom_item.setForeground(Qt.darkRed)
            table.setItem(r_idx, 3, nom_item)

            table.setItem(r_idx, 4, QTableWidgetItem(str(r.get("penerima_toko") or "-")))
            table.setItem(r_idx, 5, QTableWidgetItem(str(r.get("driver_nama") or "-")))
            table.setItem(r_idx, 6, QTableWidgetItem(str(r.get("keterangan") or "-")))

        self.content_layout.addWidget(table)

        # Footer Total
        lbl_total = QLabel(f"Total Biaya Operasional: <b>{styles.format_rupiah(total_unit)}</b> ({len(trx_list)} transaksi)")
        lbl_total.setStyleSheet("font-size: 13px; color: #1E3A8A; margin-top: 4px;")
        self.content_layout.addWidget(lbl_total)

        self.btn_save.setText("Tutup")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.setVisible(False)


# ==============================================================================
# 6. VIEW UTAMA OPERASIONAL & KEUANGAN KENDARAAN (4 TABS TERPISAH)
# ==============================================================================
class KendaraanView(QWidget):
    data_changed = Signal()

    def __init__(self, user_session: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self.user_session = user_session or {}
        self.init_ui()
        self.load_all()

    def set_active_tab(self, tab_idx: int):
        """Berpindah tab secara terprogram (0: Armada, 1: Riwayat, 2: Rekap, 3: Laporan)"""
        if 0 <= tab_idx < self.tabs.count():
            self.tabs.setCurrentIndex(tab_idx)
            self.on_tab_changed(tab_idx)

    def load_data(self):
        self.load_all()

    def refresh_all(self):
        self.load_all()

    def load_all(self):
        self.load_armada_data()
        self.load_riwayat_data()
        self.load_rekap_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 18)
        main_layout.setSpacing(12)

        # 1. Header Section
        header = SectionHeader(
            "OPERASIONAL & KEUANGAN ARMADA KENDARAAN",
            "Manajemen status armada, pencatatan transaksi pengeluaran operasional (BBM & Servis), rekapitulasi efisiensi biaya, dan laporan resmi"
        )
        main_layout.addWidget(header)

        # 2. Modern Tab Widget
        self.tabs = QTabWidget()
        self.tab_armada = QWidget()
        self.tab_riwayat = QWidget()
        self.tab_rekap = QWidget()

        self.setup_tab_armada()
        self.setup_tab_riwayat()
        self.setup_tab_rekap()

        self.tabs.addTab(self.tab_armada, "Status & Manajemen Armada")
        self.tabs.addTab(self.tab_riwayat, "Riwayat Transaksi Pengeluaran")
        self.tabs.addTab(self.tab_rekap, "Rekapitulasi & Analisis Biaya")
        self.tabs.currentChanged.connect(self.on_tab_changed)

        main_layout.addWidget(self.tabs)

    def on_tab_changed(self, index: int):
        if index == 0:
            self.load_armada_data()
        elif index == 1:
            self.load_riwayat_data()
        elif index == 2:
            self.load_rekap_data()

    # --------------------------------------------------------------------------
    # TAB 1: STATUS & DATA ARMADA
    # --------------------------------------------------------------------------
    def setup_tab_armada(self):
        tab_layout = QVBoxLayout(self.tab_armada)
        tab_layout.setContentsMargins(10, 14, 10, 10)
        tab_layout.setSpacing(12)

        # KPI Stat Cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.card_total = StatCard("Total Armada", "0 Unit", "Seluruh unit kendaraan terdaftar", "#0284C7")
        self.card_operasional = StatCard("Sedang Operasional", "0 Unit", "Armada dalam penugasan lapangan", "#2563EB")
        self.card_tersedia = StatCard("Siap / Standby", "0 Unit", "Standby & siap bertugas di plant", "#059669")
        self.card_maintenance = StatCard("Perbaikan / Servis", "0 Unit", "Unit dalam perawatan bengkel", "#D97706")

        for c in [self.card_total, self.card_operasional, self.card_tersedia, self.card_maintenance]:
            c.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            cards_layout.addWidget(c)

        tab_layout.addLayout(cards_layout)

        # Toolbar Filter & Tambah Armada
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 8px;
                padding: 6px 10px;
            }}
        """)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(4, 4, 4, 4)
        tb_layout.setSpacing(10)

        # Search Bar
        self.txt_search_armada = QLineEdit()
        self.txt_search_armada.setPlaceholderText("Cari No. Plat, Nama Unit, Driver, Keterangan...")
        self.txt_search_armada.setClearButtonEnabled(True)
        self.txt_search_armada.setMinimumWidth(260)
        self.txt_search_armada.textChanged.connect(self.load_armada_data)
        tb_layout.addWidget(self.txt_search_armada, 2)

        # Filter Status
        tb_layout.addWidget(QLabel("Status:"))
        self.cb_filter_status = QComboBox()
        self.cb_filter_status.setView(QListView())
        self.cb_filter_status.addItem("Semua Status", "semua")
        self.cb_filter_status.addItem("Tersedia (Standby)", "tersedia")
        self.cb_filter_status.addItem("Sedang Operasional", "operasional")
        self.cb_filter_status.addItem("Perbaikan / Maintenance", "maintenance")
        self.cb_filter_status.addItem("Nonaktif", "nonaktif")
        self.cb_filter_status.currentIndexChanged.connect(self.load_armada_data)
        tb_layout.addWidget(self.cb_filter_status)

        # Filter Jenis
        tb_layout.addWidget(QLabel("Jenis:"))
        self.cb_filter_jenis = QComboBox()
        self.cb_filter_jenis.setView(QListView())
        self.cb_filter_jenis.addItems([
            "Semua Jenis",
            "Truk Mixer",
            "Dump Truck",
            "Wheel Loader",
            "Truk Tronton",
            "Mobil Operasional",
            "Concrete Pump"
        ])
        self.cb_filter_jenis.currentIndexChanged.connect(self.load_armada_data)
        tb_layout.addWidget(self.cb_filter_jenis)

        # Tombol Tambah Armada Baru
        btn_tambah = PrimaryButton("+ Tambah Armada")
        btn_tambah.clicked.connect(self.tambah_armada_baru)
        tb_layout.addWidget(btn_tambah)

        tab_layout.addWidget(toolbar)

        # Tabel Data Armada (5 Kolom Bersih & Elegan - Terkunci & Tidak Bisa Digeser)
        self.table_armada = ModernTableWidget([
            "No. Plat", "Nama Unit", "Jenis Kendaraan", "Status", "Aksi"
        ])
        h_armada = self.table_armada.horizontalHeader()
        h_armada.setSectionsMovable(False)
        h_armada.setSectionResizeMode(0, QHeaderView.Fixed)
        h_armada.setSectionResizeMode(1, QHeaderView.Stretch)
        h_armada.setSectionResizeMode(2, QHeaderView.Stretch)
        h_armada.setSectionResizeMode(3, QHeaderView.Fixed)
        h_armada.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table_armada.setColumnWidth(0, 115)
        self.table_armada.setColumnWidth(3, 120)
        self.table_armada.setColumnWidth(4, 290)
        self.table_armada.itemDoubleClicked.connect(self.on_armada_row_double_clicked)
        tab_layout.addWidget(self.table_armada)

    def on_armada_row_double_clicked(self, item):
        row = item.row()
        if hasattr(self, "current_armada_list") and 0 <= row < len(self.current_armada_list):
            dlg = DetailKendaraanDialog(self.current_armada_list[row], parent=self)
            dlg.exec()

    def load_armada_data(self):
        rekap = database.get_rekap_status_kendaraan()
        self.card_total.update_value(f"{rekap.get('total', 0)} Unit")
        self.card_operasional.update_value(f"{rekap.get('operasional', 0)} Unit")
        self.card_tersedia.update_value(f"{rekap.get('tersedia', 0)} Unit")
        self.card_maintenance.update_value(f"{rekap.get('maintenance', 0)} Unit")

        st = self.cb_filter_status.currentData()
        status = None if st == "semua" else st

        jn = self.cb_filter_jenis.currentText()
        jenis = None if jn == "Semua Jenis" else jn

        search = self.txt_search_armada.text().strip() or None

        self.current_armada_list = database.get_all_kendaraan(status=status, jenis=jenis, search=search)
        self.table_armada.setRowCount(len(self.current_armada_list))

        for r_idx, k in enumerate(self.current_armada_list):
            # Col 0: No. Plat
            plat_item = QTableWidgetItem(str(k.get("no_plat") or "-"))
            plat_item.setTextAlignment(Qt.AlignCenter)
            font_p = plat_item.font()
            font_p.setBold(True)
            plat_item.setFont(font_p)
            self.table_armada.setItem(r_idx, 0, plat_item)

            # Col 1: Nama Unit
            self.table_armada.setItem(r_idx, 1, QTableWidgetItem(str(k.get("nama_kendaraan") or "-")))

            # Col 2: Jenis Kendaraan
            self.table_armada.setItem(r_idx, 2, QTableWidgetItem(str(k.get("jenis_kendaraan") or "-")))

            # Col 3: Status
            st_val = str(k.get("status") or "tersedia").lower()
            badge = BadgeLabel(st_val.capitalize(), "primary" if st_val == "operasional" else "success" if st_val == "tersedia" else "warning")
            self.table_armada.setCellWidget(r_idx, 3, badge)

            # Col 4: Aksi Buttons
            action_widget = QWidget()
            act_lay = QHBoxLayout(action_widget)
            act_lay.setContentsMargins(4, 2, 10, 2)
            act_lay.setSpacing(5)
            act_lay.setAlignment(Qt.AlignCenter)

            btn_detail = TableDetailButton("Detail")
            btn_detail.clicked.connect(lambda _, row_data=k: self.buka_detail_kendaraan(row_data))
            act_lay.addWidget(btn_detail)

            btn_status = TableEditButton("Status")
            btn_status.clicked.connect(lambda _, row_data=k: self.ubah_status_armada(row_data))
            act_lay.addWidget(btn_status)

            btn_edit = TableEditButton("Edit")
            btn_edit.clicked.connect(lambda _, row_data=k: self.edit_armada(row_data))
            act_lay.addWidget(btn_edit)

            btn_del = TableDeleteButton("Hapus")
            btn_del.clicked.connect(lambda _, row_data=k: self.hapus_armada(row_data))
            act_lay.addWidget(btn_del)

            self.table_armada.setCellWidget(r_idx, 4, action_widget)

    def buka_detail_kendaraan(self, row_data):
        dlg = DetailKendaraanDialog(row_data, parent=self)
        dlg.exec()

    def tambah_armada_baru(self):
        dlg = KendaraanDialog(parent=self)
        if dlg.exec():
            self.load_all()
            self.data_changed.emit()

    def ubah_status_armada(self, row_data):
        dlg = StatusOperasionalDialog(row_data, parent=self)
        if dlg.exec():
            self.load_all()
            self.data_changed.emit()

    def edit_armada(self, row_data):
        dlg = KendaraanDialog(row_data, parent=self)
        if dlg.exec():
            self.load_all()
            self.data_changed.emit()

    def hapus_armada(self, row_data):
        plat = row_data.get("no_plat") or ""
        nama = row_data.get("nama_kendaraan") or plat
        if confirm_dialog(self, "Konfirmasi Hapus Armada", f"Hapus armada '{nama}' ({plat}) dari sistem?"):
            ok, msg = database.hapus_kendaraan(row_data["id"])
            if ok:
                QMessageBox.information(self, "Sukses", msg)
                self.load_all()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Gagal", msg)

    # --------------------------------------------------------------------------
    # TAB 2: RIWAYAT TRANSAKSI PENGELUARAN (FOKUS PADA TRANSAKSI / PENGELUARAN)
    # --------------------------------------------------------------------------
    def setup_tab_riwayat(self):
        tab_layout = QVBoxLayout(self.tab_riwayat)
        tab_layout.setContentsMargins(10, 14, 10, 10)
        tab_layout.setSpacing(12)

        # Filter Toolbar
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        tb_layout = QVBoxLayout(toolbar)
        tb_layout.setContentsMargins(6, 6, 6, 6)
        tb_layout.setSpacing(8)

        # Baris 1: Filter Periode, Armada, dan Kategori
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        row1.addWidget(QLabel("Periode:"))
        self.dt_r_start = QDateEdit()
        self.dt_r_start.setCalendarPopup(True)
        self.dt_r_start.setDate(QDate.currentDate().addMonths(-1))
        self.dt_r_start.setDisplayFormat("yyyy-MM-dd")
        self.dt_r_start.setMinimumWidth(110)
        self.dt_r_start.dateChanged.connect(self.load_riwayat_data)
        row1.addWidget(self.dt_r_start)

        row1.addWidget(QLabel("s/d"))
        self.dt_r_end = QDateEdit()
        self.dt_r_end.setCalendarPopup(True)
        self.dt_r_end.setDate(QDate.currentDate())
        self.dt_r_end.setDisplayFormat("yyyy-MM-dd")
        self.dt_r_end.setMinimumWidth(110)
        self.dt_r_end.dateChanged.connect(self.load_riwayat_data)
        row1.addWidget(self.dt_r_end)

        row1.addWidget(QLabel("Armada:"))
        self.cb_r_armada = QComboBox()
        self.cb_r_armada.setView(QListView())
        self.cb_r_armada.addItem("Semua Armada", -1)
        self.cb_r_armada.setMinimumWidth(180)
        self.cb_r_armada.currentIndexChanged.connect(self.load_riwayat_data)
        row1.addWidget(self.cb_r_armada, 1)

        row1.addWidget(QLabel("Kategori:"))
        self.cb_r_kategori = QComboBox()
        self.cb_r_kategori.setView(QListView())
        self.cb_r_kategori.addItems([
            "Semua Kategori",
            "BBM / Solar Operasional",
            "Servis & Perawatan Bengkel",
            "Sparepart & Oli Mesin",
            "Penggantian Ban",
            "Uang Jalan & Supir",
            "Pajak & Uji KIR",
            "Cuci & Kebersihan Mobil",
            "Retribusi & Tol",
            "Lain-lain Operasional"
        ])
        self.cb_r_kategori.setMinimumWidth(180)
        self.cb_r_kategori.currentIndexChanged.connect(self.load_riwayat_data)
        row1.addWidget(self.cb_r_kategori, 1)

        tb_layout.addLayout(row1)

        # Baris 2: Cari Kata Kunci dan Tombol Aksi
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        row2.addWidget(QLabel("Cari:"))
        self.txt_r_search = QLineEdit()
        self.txt_r_search.setPlaceholderText("Cari nota, SPBU, penerima, proyek, keterangan...")
        self.txt_r_search.setClearButtonEnabled(True)
        self.txt_r_search.textChanged.connect(self.load_riwayat_data)
        row2.addWidget(self.txt_r_search, 2)

        # Action Button: Catat Biaya Baru
        btn_catat = PrimaryButton("+ Catat Biaya")
        btn_catat.setFixedHeight(34)
        btn_catat.clicked.connect(self.tambah_biaya_mobil)
        row2.addWidget(btn_catat)

        # Reset Filter
        btn_reset = SecondaryButton("Reset Filter")
        btn_reset.setFixedHeight(34)
        btn_reset.clicked.connect(self.reset_filter_riwayat)
        row2.addWidget(btn_reset)

        tb_layout.addLayout(row2)

        tab_layout.addWidget(toolbar)

        # Tabel Riwayat Transaksi (5 Kolom Bersih & Elegan - Terkunci & Tidak Bisa Digeser)
        self.table_riwayat = ModernTableWidget([
            "Tanggal", "Armada / Plat", "Kategori Biaya", "Nominal (Rp)", "Aksi"
        ])
        h_riwayat = self.table_riwayat.horizontalHeader()
        h_riwayat.setSectionsMovable(False)
        h_riwayat.setSectionResizeMode(0, QHeaderView.Fixed)
        h_riwayat.setSectionResizeMode(1, QHeaderView.Stretch)
        h_riwayat.setSectionResizeMode(2, QHeaderView.Fixed)
        h_riwayat.setSectionResizeMode(3, QHeaderView.Fixed)
        h_riwayat.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table_riwayat.setColumnWidth(0, 95)
        self.table_riwayat.setColumnWidth(2, 170)
        self.table_riwayat.setColumnWidth(3, 125)
        self.table_riwayat.setColumnWidth(4, 215)
        self.table_riwayat.itemDoubleClicked.connect(self.on_riwayat_row_double_clicked)
        tab_layout.addWidget(self.table_riwayat)

        # Summary Bar di Bawah Tabel
        self.lbl_riwayat_summary = QLabel("Total Transaksi: 0 Nota | Total Pengeluaran: Rp 0")
        self.lbl_riwayat_summary.setStyleSheet("font-size: 12px; font-weight: 700; color: #1E3A8A; padding: 4px;")
        tab_layout.addWidget(self.lbl_riwayat_summary)

    def on_riwayat_row_double_clicked(self, item):
        row = item.row()
        if hasattr(self, "current_biaya_list") and 0 <= row < len(self.current_biaya_list):
            dlg = DetailBiayaDialog(self.current_biaya_list[row]["id"], parent=self)
            dlg.exec()

    def reset_filter_riwayat(self):
        self.dt_r_start.setDate(QDate.currentDate().addMonths(-1))
        self.dt_r_end.setDate(QDate.currentDate())
        self.cb_r_armada.setCurrentIndex(0)
        self.cb_r_kategori.setCurrentIndex(0)
        self.txt_r_search.clear()
        self.load_riwayat_data()

    def populate_combos(self):
        # Update Armada Combos
        fleet = database.get_all_kendaraan()
        
        # Riwayat
        cur_r = self.cb_r_armada.currentData()
        self.cb_r_armada.blockSignals(True)
        self.cb_r_armada.clear()
        self.cb_r_armada.addItem("Semua Armada", -1)
        for k in fleet:
            np = k.get("no_plat") or ""
            nm = k.get("nama_kendaraan") or ""
            lbl = f"{np} - {nm}" if nm else np
            self.cb_r_armada.addItem(lbl, k["id"])
        idx_r = self.cb_r_armada.findData(cur_r)
        self.cb_r_armada.setCurrentIndex(idx_r if idx_r >= 0 else 0)
        self.cb_r_armada.blockSignals(False)

        # Drivers for Laporan
        cb_lap = getattr(self, "cb_lap_driver", None)
        if cb_lap:
            drivers = database.get_all_drivers()
            cur_d = cb_lap.currentText()
            cb_lap.blockSignals(True)
            cb_lap.clear()
            cb_lap.addItem("Semua Driver")
            for d in drivers:
                cb_lap.addItem(d)
            idx_d = cb_lap.findText(cur_d)
            cb_lap.setCurrentIndex(idx_d if idx_d >= 0 else 0)
            cb_lap.blockSignals(False)

    def load_riwayat_data(self):
        self.populate_combos()

        k_id = self.cb_r_armada.currentData()
        kategori = self.cb_r_kategori.currentText()
        s_date = self.dt_r_start.date().toString("yyyy-MM-dd")
        e_date = self.dt_r_end.date().toString("yyyy-MM-dd")
        search = self.txt_r_search.text().strip() or None

        self.current_biaya_list = database.get_biaya_kendaraan_list(
            kendaraan_id=k_id if k_id != -1 else None,
            start_date=s_date,
            end_date=e_date,
            kategori=kategori if kategori != "Semua Kategori" else None,
            search=search
        )

        self.table_riwayat.setRowCount(len(self.current_biaya_list))
        total_nominal = 0.0

        for r_idx, r in enumerate(self.current_biaya_list):
            nom = float(r.get("nominal") or 0)
            total_nominal += nom

            # Col 0: Tanggal
            tgl_item = QTableWidgetItem(str(r.get("tanggal") or "-"))
            tgl_item.setTextAlignment(Qt.AlignCenter)
            self.table_riwayat.setItem(r_idx, 0, tgl_item)

            # Col 1: Armada / Plat
            plat_str = f"{r.get('no_plat') or '-'} ({r.get('nama_kendaraan') or ''})".strip()
            item_arm = QTableWidgetItem(plat_str)
            font_a = item_arm.font()
            font_a.setBold(True)
            item_arm.setFont(font_a)
            self.table_riwayat.setItem(r_idx, 1, item_arm)

            # Col 2: Kategori Biaya
            kat = str(r.get("kategori") or "Operasional")
            if "BBM" in kat or "Solar" in kat:
                badge = BadgeLabel(kat, "warning")
            elif "Servis" in kat or "Bengkel" in kat or "Sparepart" in kat:
                badge = BadgeLabel(kat, "danger")
            elif "Uang Jalan" in kat or "Supir" in kat:
                badge = BadgeLabel(kat, "primary")
            else:
                badge = BadgeLabel(kat, "info")
            self.table_riwayat.setCellWidget(r_idx, 2, badge)

            # Col 3: Nominal (Rp)
            nom_item = QTableWidgetItem(styles.format_rupiah(nom))
            nom_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            nom_item.setForeground(Qt.darkRed)
            font_n = nom_item.font()
            font_n.setBold(True)
            nom_item.setFont(font_n)
            self.table_riwayat.setItem(r_idx, 3, nom_item)

            # Col 4: Aksi Buttons
            action_widget = QWidget()
            act_lay = QHBoxLayout(action_widget)
            act_lay.setContentsMargins(4, 2, 10, 2)
            act_lay.setSpacing(5)
            act_lay.setAlignment(Qt.AlignCenter)

            btn_det = TableDetailButton("Detail")
            btn_det.clicked.connect(lambda _, row_data=r: self.buka_detail_biaya(row_data))
            act_lay.addWidget(btn_det)

            btn_edit = TableEditButton("Edit")
            btn_edit.clicked.connect(lambda _, row_data=r: self.edit_biaya_mobil(row_data))
            act_lay.addWidget(btn_edit)

            btn_del = TableDeleteButton("Hapus")
            btn_del.clicked.connect(lambda _, row_data=r: self.hapus_biaya_mobil(row_data))
            act_lay.addWidget(btn_del)

            self.table_riwayat.setCellWidget(r_idx, 4, action_widget)

        self.lbl_riwayat_summary.setText(
            f"Menampilkan <b>{len(self.current_biaya_list)}</b> transaksi operasional | "
            f"Total Biaya: <b>{styles.format_rupiah(total_nominal)}</b>"
        )

    def buka_detail_biaya(self, row_data):
        dlg = DetailBiayaDialog(row_data["id"], parent=self)
        dlg.exec()

    def tambah_biaya_mobil(self):
        dlg = BiayaKendaraanDialog(parent=self)
        if dlg.exec():
            self.load_all()
            self.data_changed.emit()

    def edit_biaya_mobil(self, row_data):
        dlg = BiayaKendaraanDialog(biaya_data=row_data, parent=self)
        if dlg.exec():
            self.load_all()
            self.data_changed.emit()

    def hapus_biaya_mobil(self, row_data):
        nota = row_data.get("nomor_nota") or f"ID #{row_data.get('id')}"
        nom = styles.format_rupiah(row_data.get("nominal") or 0)
        if confirm_dialog(self, "Konfirmasi Hapus Biaya", f"Hapus transaksi operasional nota '{nota}' sebesar {nom}?\nPengeluaran ini akan dikembalikan ke saldo kas."):
            ok, msg = database.hapus_kas_kantor(row_data["id"])
            if ok:
                QMessageBox.information(self, "Sukses", msg)
                self.load_all()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Gagal", msg)

    # --------------------------------------------------------------------------
    # TAB 3: REKAPITULASI & ANALISIS BIAYA (TOTAL BIAYA, KENDARAAN, FREKUENSI, ANALISIS)
    # --------------------------------------------------------------------------
    def setup_tab_rekap(self):
        tab_layout = QVBoxLayout(self.tab_rekap)
        tab_layout.setContentsMargins(10, 14, 10, 10)
        tab_layout.setSpacing(12)

        # KPI Analisis Biaya Cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.card_rekap_total = StatCard("Total Biaya Armada", "Rp 0", "Pengeluaran operasional periode ini", "#1E3A8A")
        self.card_rekap_bbm = StatCard("Biaya BBM / Solar", "Rp 0", "Konsumsi bahan bakar armada", "#D97706")
        self.card_rekap_servis = StatCard("Biaya Servis & Bengkel", "Rp 0", "Perawatan, ganti oli & sparepart", "#DC2626")
        self.card_rekap_avg = StatCard("Rata-Rata per Kendaraan", "Rp 0", "Rasio pengeluaran per unit mobil", "#059669")
        self.card_rekap_freq = StatCard("Frekuensi Transaksi", "0 Nota", "Total pencatatan kuitansi/SPBU", "#475569")

        for c in [self.card_rekap_total, self.card_rekap_bbm, self.card_rekap_servis, self.card_rekap_avg, self.card_rekap_freq]:
            c.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            cards_layout.addWidget(c)

        tab_layout.addLayout(cards_layout)

        # Toolbar Filter Rekapitulasi
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 8px;
                padding: 6px 10px;
            }}
        """)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(4, 4, 4, 4)
        tb_layout.setSpacing(10)

        tb_layout.addWidget(QLabel("Mulai:"))
        self.dt_rk_start = QDateEdit()
        self.dt_rk_start.setCalendarPopup(True)
        self.dt_rk_start.setDate(QDate.currentDate().addMonths(-1))
        self.dt_rk_start.setDisplayFormat("yyyy-MM-dd")
        self.dt_rk_start.dateChanged.connect(self.load_rekap_data)
        tb_layout.addWidget(self.dt_rk_start)

        tb_layout.addWidget(QLabel("Sampai:"))
        self.dt_rk_end = QDateEdit()
        self.dt_rk_end.setCalendarPopup(True)
        self.dt_rk_end.setDate(QDate.currentDate())
        self.dt_rk_end.setDisplayFormat("yyyy-MM-dd")
        self.dt_rk_end.dateChanged.connect(self.load_rekap_data)
        tb_layout.addWidget(self.dt_rk_end)

        tb_layout.addWidget(QLabel("Jenis:"))
        self.cb_rk_jenis = QComboBox()
        self.cb_rk_jenis.setView(QListView())
        self.cb_rk_jenis.addItems([
            "Semua Jenis",
            "Truk Mixer",
            "Dump Truck",
            "Wheel Loader",
            "Truk Tronton",
            "Mobil Operasional",
            "Concrete Pump"
        ])
        self.cb_rk_jenis.currentIndexChanged.connect(self.load_rekap_data)
        tb_layout.addWidget(self.cb_rk_jenis)

        self.txt_rk_search = QLineEdit()
        self.txt_rk_search.setPlaceholderText("Cari no plat / nama unit...")
        self.txt_rk_search.setMinimumWidth(180)
        self.txt_rk_search.textChanged.connect(self.load_rekap_data)
        tb_layout.addWidget(self.txt_rk_search)

        btn_reset_rk = SecondaryButton("Reset")
        btn_reset_rk.clicked.connect(self.reset_filter_rekap)
        tb_layout.addWidget(btn_reset_rk)

        tab_layout.addWidget(toolbar)

        # Tabel Rekapitulasi Efisiensi per Unit Mobil (5 Kolom Bersih & Elegan - Terkunci & Tidak Bisa Digeser)
        self.table_rekap = ModernTableWidget([
            "No. Plat", "Nama Unit", "Jenis Kendaraan", "TOTAL BIAYA (Rp)", "Aksi"
        ])
        h_rekap = self.table_rekap.horizontalHeader()
        h_rekap.setSectionsMovable(False)
        h_rekap.setSectionResizeMode(0, QHeaderView.Fixed)
        h_rekap.setSectionResizeMode(1, QHeaderView.Stretch)
        h_rekap.setSectionResizeMode(2, QHeaderView.Stretch)
        h_rekap.setSectionResizeMode(3, QHeaderView.Fixed)
        h_rekap.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table_rekap.setColumnWidth(0, 115)
        self.table_rekap.setColumnWidth(3, 150)
        self.table_rekap.setColumnWidth(4, 100)
        self.table_rekap.itemDoubleClicked.connect(self.on_rekap_row_double_clicked)
        tab_layout.addWidget(self.table_rekap)

    def on_rekap_row_double_clicked(self, item):
        row = item.row()
        if hasattr(self, "current_rekap_list") and 0 <= row < len(self.current_rekap_list):
            dlg = DetailKendaraanDialog(self.current_rekap_list[row], parent=self)
            dlg.exec()

    def reset_filter_rekap(self):
        self.dt_rk_start.setDate(QDate.currentDate().addMonths(-1))
        self.dt_rk_end.setDate(QDate.currentDate())
        self.cb_rk_jenis.setCurrentIndex(0)
        self.txt_rk_search.clear()
        self.load_rekap_data()

    def load_rekap_data(self):
        s_date = self.dt_rk_start.date().toString("yyyy-MM-dd")
        e_date = self.dt_rk_end.date().toString("yyyy-MM-dd")
        jenis = self.cb_rk_jenis.currentText()
        search = self.txt_rk_search.text().strip() or None

        self.current_rekap_list = database.get_rekap_biaya_per_kendaraan(
            start_date=s_date,
            end_date=e_date,
            jenis_kendaraan=jenis,
            search=search
        )

        sum_tot = 0.0
        sum_bbm = 0.0
        sum_srv = 0.0
        sum_freq = 0

        self.table_rekap.setRowCount(len(self.current_rekap_list))
        for r_idx, r in enumerate(self.current_rekap_list):
            t_bbm = float(r.get("total_bbm") or 0)
            t_srv = float(r.get("total_servis") or 0)
            t_tot = float(r.get("total_biaya") or 0)
            freq = int(r.get("frekuensi_transaksi") or 0)

            sum_bbm += t_bbm
            sum_srv += t_srv
            sum_tot += t_tot
            sum_freq += freq

            # Col 0: No. Plat
            p_item = QTableWidgetItem(str(r.get("no_plat") or "-"))
            p_item.setTextAlignment(Qt.AlignCenter)
            font_p = p_item.font()
            font_p.setBold(True)
            p_item.setFont(font_p)
            self.table_rekap.setItem(r_idx, 0, p_item)

            # Col 1: Nama Unit
            self.table_rekap.setItem(r_idx, 1, QTableWidgetItem(str(r.get("nama_kendaraan") or "-")))

            # Col 2: Jenis Kendaraan
            self.table_rekap.setItem(r_idx, 2, QTableWidgetItem(str(r.get("jenis_kendaraan") or "-")))

            # Col 3: TOTAL BIAYA (Rp)
            tot_item = QTableWidgetItem(styles.format_rupiah(t_tot))
            tot_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            tot_item.setForeground(Qt.darkRed)
            font_t = tot_item.font()
            font_t.setBold(True)
            tot_item.setFont(font_t)
            self.table_rekap.setItem(r_idx, 3, tot_item)

            # Col 4: Aksi
            act_w = QWidget()
            act_lay = QHBoxLayout(act_w)
            act_lay.setContentsMargins(4, 2, 4, 2)
            act_lay.setAlignment(Qt.AlignCenter)
            btn_det = TableDetailButton("Detail")
            btn_det.clicked.connect(lambda _, row_data=r: self.buka_detail_kendaraan(row_data))
            act_lay.addWidget(btn_det)
            self.table_rekap.setCellWidget(r_idx, 4, act_w)

        # Update Stat Cards Rekap
        self.card_rekap_total.update_value(styles.format_rupiah(sum_tot))
        self.card_rekap_bbm.update_value(styles.format_rupiah(sum_bbm))
        self.card_rekap_servis.update_value(styles.format_rupiah(sum_srv))
        avg_cost = (sum_tot / len(self.current_rekap_list)) if self.current_rekap_list else 0.0
        self.card_rekap_avg.update_value(styles.format_rupiah(avg_cost))
        self.card_rekap_freq.update_value(f"{sum_freq} Nota")

    # --------------------------------------------------------------------------
    # TAB 4: LAPORAN OPERASIONAL KENDARAAN (EXPORT EXCEL & PDF & FILTER LENGKAP)
    # --------------------------------------------------------------------------
    def setup_tab_laporan(self):
        tab_layout = QVBoxLayout(self.tab_laporan)
        tab_layout.setContentsMargins(10, 14, 10, 10)
        tab_layout.setSpacing(12)

        # Card Filter & Export Laporan
        filter_card = QFrame()
        filter_card.setProperty("class", "CardWidget")
        fc_layout = QVBoxLayout(filter_card)
        fc_layout.setContentsMargins(16, 14, 16, 14)
        fc_layout.setSpacing(12)

        lbl_title = QLabel("FILTER & GENERATE LAPORAN OPERASIONAL KENDARAAN")
        lbl_title.setStyleSheet(f"font-weight: 800; color: {styles.COLOR_PRIMARY_DARK}; font-size: 13px;")
        fc_layout.addWidget(lbl_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)

        # Baris 1: Rentang Tanggal
        grid.addWidget(QLabel("Mulai Tanggal:"), 0, 0, Qt.AlignVCenter)
        self.dt_lap_start = QDateEdit()
        self.dt_lap_start.setCalendarPopup(True)
        self.dt_lap_start.setDate(QDate.currentDate().addMonths(-1))
        self.dt_lap_start.setDisplayFormat("yyyy-MM-dd")
        self.dt_lap_start.dateChanged.connect(self.load_laporan_data)
        grid.addWidget(self.dt_lap_start, 0, 1)

        grid.addWidget(QLabel("Sampai Tanggal:"), 0, 2, Qt.AlignVCenter)
        self.dt_lap_end = QDateEdit()
        self.dt_lap_end.setCalendarPopup(True)
        self.dt_lap_end.setDate(QDate.currentDate())
        self.dt_lap_end.setDisplayFormat("yyyy-MM-dd")
        self.dt_lap_end.dateChanged.connect(self.load_laporan_data)
        grid.addWidget(self.dt_lap_end, 0, 3)

        # Baris 2: Kendaraan & Driver
        grid.addWidget(QLabel("Filter Kendaraan:"), 1, 0, Qt.AlignVCenter)
        self.cb_lap_kendaraan = QComboBox()
        self.cb_lap_kendaraan.setView(QListView())
        self.cb_lap_kendaraan.addItem("Semua Kendaraan", -1)
        self.cb_lap_kendaraan.currentIndexChanged.connect(self.load_laporan_data)
        grid.addWidget(self.cb_lap_kendaraan, 1, 1)

        grid.addWidget(QLabel("Filter Driver:"), 1, 2, Qt.AlignVCenter)
        self.cb_lap_driver = QComboBox()
        self.cb_lap_driver.setView(QListView())
        self.cb_lap_driver.addItem("Semua Driver")
        self.cb_lap_driver.currentIndexChanged.connect(self.load_laporan_data)
        grid.addWidget(self.cb_lap_driver, 1, 3)

        # Baris 3: Kategori Biaya & Proyek
        grid.addWidget(QLabel("Kategori Biaya:"), 2, 0, Qt.AlignVCenter)
        self.cb_lap_kategori = QComboBox()
        self.cb_lap_kategori.setView(QListView())
        self.cb_lap_kategori.addItems([
            "Semua Kategori",
            "BBM / Solar Operasional",
            "Servis & Perawatan Bengkel",
            "Sparepart & Oli Mesin",
            "Penggantian Ban",
            "Uang Jalan & Supir",
            "Pajak & Uji KIR",
            "Cuci & Kebersihan Mobil",
            "Retribusi & Tol",
            "Lain-lain Operasional"
        ])
        self.cb_lap_kategori.currentIndexChanged.connect(self.load_laporan_data)
        grid.addWidget(self.cb_lap_kategori, 2, 1)

        grid.addWidget(QLabel("Filter Proyek:"), 2, 2, Qt.AlignVCenter)
        self.cb_lap_proyek = QComboBox()
        self.cb_lap_proyek.setView(QListView())
        self.cb_lap_proyek.addItem("Semua Proyek", -1)
        proyeks = database.get_all_proyek(only_active=False)
        for p in proyeks:
            self.cb_lap_proyek.addItem(p["nama"], p["id"])
        self.cb_lap_proyek.currentIndexChanged.connect(self.load_laporan_data)
        grid.addWidget(self.cb_lap_proyek, 2, 3)

        fc_layout.addLayout(grid)

        # Export Buttons Row
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)

        self.btn_lap_export_excel = SuccessButton("Ekspor ke Microsoft Excel (.xlsx)")
        self.btn_lap_export_excel.setFixedHeight(38)
        self.btn_lap_export_excel.clicked.connect(self.ekspor_laporan_excel)
        btn_box.addWidget(self.btn_lap_export_excel)

        self.btn_lap_export_pdf = PrimaryButton("Ekspor ke Dokumen PDF (.pdf)")
        self.btn_lap_export_pdf.setFixedHeight(38)
        self.btn_lap_export_pdf.clicked.connect(self.ekspor_laporan_pdf)
        btn_box.addWidget(self.btn_lap_export_pdf)

        btn_box.addStretch()
        fc_layout.addLayout(btn_box)

        tab_layout.addWidget(filter_card)

        # Live Preview Header
        lbl_preview = QLabel("LIVE PREVIEW LAPORAN PENGELUARAN KENDARAAN:")
        lbl_preview.setStyleSheet(f"font-weight: 700; color: {styles.COLOR_PRIMARY_DARK}; font-size: 11.5px;")
        tab_layout.addWidget(lbl_preview)

        # Tabel Live Preview Laporan
        self.table_laporan = ModernTableWidget([
            "No", "Tanggal", "No. Nota", "No. Plat", "Nama Unit", "Driver",
            "Kategori Biaya", "Nominal (Rp)", "SPBU / Bengkel", "Proyek Terkait", "Keterangan"
        ])
        self.table_laporan.setColumnWidth(0, 45)
        self.table_laporan.setColumnWidth(1, 95)
        self.table_laporan.setColumnWidth(2, 115)
        self.table_laporan.setColumnWidth(3, 110)
        self.table_laporan.setColumnWidth(4, 140)
        self.table_laporan.setColumnWidth(5, 110)
        self.table_laporan.setColumnWidth(6, 140)
        self.table_laporan.setColumnWidth(7, 120)
        self.table_laporan.setColumnWidth(8, 130)
        self.table_laporan.setColumnWidth(9, 130)
        self.table_laporan.horizontalHeader().setSectionResizeMode(10, QHeaderView.Stretch)
        tab_layout.addWidget(self.table_laporan)

        # Summary Bar
        self.lbl_lap_summary = QLabel("Menampilkan 0 baris transaksi")
        self.lbl_lap_summary.setStyleSheet("font-size: 12px; font-weight: 700; color: #1E3A8A; padding: 4px;")
        tab_layout.addWidget(self.lbl_lap_summary)

    def load_laporan_data(self):
        # Sync Fleet Dropdown on Laporan
        fleet = database.get_all_kendaraan()
        cur_k = self.cb_lap_kendaraan.currentData()
        self.cb_lap_kendaraan.blockSignals(True)
        self.cb_lap_kendaraan.clear()
        self.cb_lap_kendaraan.addItem("Semua Kendaraan", -1)
        for k in fleet:
            np = k.get("no_plat") or ""
            nm = k.get("nama_kendaraan") or ""
            self.cb_lap_kendaraan.addItem(f"{np} - {nm}" if nm else np, k["id"])
        idx_k = self.cb_lap_kendaraan.findData(cur_k)
        self.cb_lap_kendaraan.setCurrentIndex(idx_k if idx_k >= 0 else 0)
        self.cb_lap_kendaraan.blockSignals(False)

        s_date = self.dt_lap_start.date().toString("yyyy-MM-dd")
        e_date = self.dt_lap_end.date().toString("yyyy-MM-dd")
        k_id = self.cb_lap_kendaraan.currentData()
        driver = self.cb_lap_driver.currentText()
        kategori = self.cb_lap_kategori.currentText()
        pr_id = self.cb_lap_proyek.currentData()

        self.current_lap_list = database.get_biaya_kendaraan_list(
            kendaraan_id=k_id if k_id != -1 else None,
            start_date=s_date,
            end_date=e_date,
            kategori=kategori if kategori != "Semua Kategori" else None,
            driver=driver if driver != "Semua Driver" else None,
            proyek_id=pr_id if pr_id != -1 else None
        )

        self.table_laporan.setRowCount(len(self.current_lap_list))
        total_nom = 0.0

        for r_idx, r in enumerate(self.current_lap_list):
            nom = float(r.get("nominal") or 0)
            total_nom += nom

            no_item = QTableWidgetItem(str(r_idx + 1))
            no_item.setTextAlignment(Qt.AlignCenter)
            self.table_laporan.setItem(r_idx, 0, no_item)

            self.table_laporan.setItem(r_idx, 1, QTableWidgetItem(str(r.get("tanggal") or "-")))
            self.table_laporan.setItem(r_idx, 2, QTableWidgetItem(str(r.get("nomor_nota") or "-")))

            p_item = QTableWidgetItem(str(r.get("no_plat") or "-"))
            p_item.setTextAlignment(Qt.AlignCenter)
            font_p = p_item.font()
            font_p.setBold(True)
            p_item.setFont(font_p)
            self.table_laporan.setItem(r_idx, 3, p_item)

            self.table_laporan.setItem(r_idx, 4, QTableWidgetItem(str(r.get("nama_kendaraan") or "-")))
            self.table_laporan.setItem(r_idx, 5, QTableWidgetItem(str(r.get("driver_nama") or "-")))
            self.table_laporan.setItem(r_idx, 6, QTableWidgetItem(str(r.get("kategori") or "-")))

            nom_item = QTableWidgetItem(styles.format_rupiah(nom))
            nom_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            nom_item.setForeground(Qt.darkRed)
            font_n = nom_item.font()
            font_n.setBold(True)
            nom_item.setFont(font_n)
            self.table_laporan.setItem(r_idx, 7, nom_item)

            self.table_laporan.setItem(r_idx, 8, QTableWidgetItem(str(r.get("penerima_toko") or "-")))
            self.table_laporan.setItem(r_idx, 9, QTableWidgetItem(str(r.get("proyek_nama") or "-")))
            self.table_laporan.setItem(r_idx, 10, QTableWidgetItem(str(r.get("keterangan") or "-")))

        self.lbl_lap_summary.setText(
            f"Total Data Terfilter: <b>{len(self.current_lap_list)}</b> baris transaksi | "
            f"Total Pengeluaran: <b>{styles.format_rupiah(total_nom)}</b>"
        )

    def ekspor_laporan_excel(self):
        s_date = self.dt_lap_start.date().toString("yyyy-MM-dd")
        e_date = self.dt_lap_end.date().toString("yyyy-MM-dd")
        k_id = self.cb_lap_kendaraan.currentData()
        driver = self.cb_lap_driver.currentText()
        kategori = self.cb_lap_kategori.currentText()
        pr_id = self.cb_lap_proyek.currentData()

        default_filename = f"Laporan_Operasional_Kendaraan_{s_date}_{e_date}.xlsx"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Simpan Laporan Excel Operasional Kendaraan",
            default_filename, "Excel Files (*.xlsx)"
        )
        if not filepath:
            return

        ok, msg = export_service.export_operasional_kendaraan_excel(
            filepath=filepath,
            start_date=s_date,
            end_date=e_date,
            kendaraan_id=k_id if k_id != -1 else None,
            driver=driver if driver != "Semua Driver" else None,
            kategori=kategori if kategori != "Semua Kategori" else None,
            proyek_id=pr_id if pr_id != -1 else None
        )
        if ok:
            export_service.open_excel_document(filepath)
            QMessageBox.information(self, "Berhasil", f"Laporan operasional kendaraan berhasil diekspor dan dibuka:\n{msg}")
        else:
            QMessageBox.critical(self, "Gagal", msg)

    def ekspor_laporan_pdf(self):
        s_date = self.dt_lap_start.date().toString("yyyy-MM-dd")
        e_date = self.dt_lap_end.date().toString("yyyy-MM-dd")
        k_id = self.cb_lap_kendaraan.currentData()
        driver = self.cb_lap_driver.currentText()
        kategori = self.cb_lap_kategori.currentText()
        pr_id = self.cb_lap_proyek.currentData()

        default_filename = f"Laporan_Operasional_Kendaraan_{s_date}_{e_date}.pdf"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Simpan Laporan PDF Operasional Kendaraan",
            default_filename, "PDF Documents (*.pdf)"
        )
        if not filepath:
            return

        ok, msg = export_service.export_operasional_kendaraan_pdf(
            filepath=filepath,
            start_date=s_date,
            end_date=e_date,
            kendaraan_id=k_id if k_id != -1 else None,
            driver=driver if driver != "Semua Driver" else None,
            kategori=kategori if kategori != "Semua Kategori" else None,
            proyek_id=pr_id if pr_id != -1 else None
        )
        if ok:
            export_service.open_pdf_document(filepath)
            QMessageBox.information(self, "Berhasil", f"Laporan operasional kendaraan PDF siap cetak berhasil dibuat dan langsung dibuka di Chrome:\n{msg}")
        else:
            QMessageBox.critical(self, "Gagal", msg)

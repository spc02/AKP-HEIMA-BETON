"""
Produksi & Pengiriman View untuk AKP Beton Desktop Application
Mengelola formulir pengiriman beton, kalkulasi otomatis kebutuhan material x volume,
kalkulasi live POS HPP & Margin Laba, validasi ketersediaan stok, riwayat pengiriman,
dan cetak Surat Jalan / Tiket Cor.
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, 
    QLabel, QFrame, QTableWidgetItem, QMessageBox, QDialog,
    QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit, QDateEdit,
    QGridLayout, QHeaderView, QFileDialog, QListView, QSizePolicy, QScrollArea,
    QButtonGroup, QCheckBox, QCompleter, QRadioButton
)
from PySide6.QtCore import Qt, QDate, Signal, QStringListModel
from components import (
    ModernTableWidget, SectionHeader, ModernDialog, confirm_dialog, BadgeLabel, StatCard,
    PrimaryButton, SecondaryButton, SuccessButton, DangerButton,
    TableEditButton, TableDeleteButton, TableDetailButton
)
import styles
import database
import export_service

# ==========================================
# DIALOG LIHAT DETAIL PENGIRIMAN & MATERIAL
# ==========================================
class DetailPengirimanDialog(ModernDialog):
    def __init__(self, pengiriman_data, parent=None):
        title = f"Rincian Pengiriman & Pemakaian Material: {pengiriman_data.get('no_surat_jalan') or 'Pengiriman'}"
        super().__init__(title, parent, min_width=680)
        self.pengiriman_data = pengiriman_data
        self.init_details()

    def init_details(self):
        d = self.pengiriman_data
        
        # Grid Info Utama
        info_lay = QGridLayout()
        info_lay.setSpacing(6)
        
        info_lay.addWidget(QLabel("No. Surat Jalan:"), 0, 0)
        info_lay.addWidget(QLabel(f"<b>{d.get('no_surat_jalan') or '-'}</b>"), 0, 1)

        info_lay.addWidget(QLabel("Tanggal Pengiriman:"), 0, 2)
        info_lay.addWidget(QLabel(f"<b>{d.get('tanggal')}</b>"), 0, 3)

        info_lay.addWidget(QLabel("Mutu Beton:"), 1, 0)
        info_lay.addWidget(QLabel(f"<b>{d.get('mutu_kode')}</b> ({d.get('mutu_nama') or '-'})"), 1, 1)

        info_lay.addWidget(QLabel("Volume Cor:"), 1, 2)
        info_lay.addWidget(QLabel(f"<b>{styles.format_number(d.get('volume_m3'), 2)} m³</b>"), 1, 3)

        info_lay.addWidget(QLabel("Proyek Tujuan:"), 2, 0)
        info_lay.addWidget(QLabel(f"<b>{d.get('proyek_nama')}</b>"), 2, 1)

        info_lay.addWidget(QLabel("Lokasi / Segmen:"), 2, 2)
        info_lay.addWidget(QLabel(f"<b>{d.get('tujuan_pengiriman') or '-'}</b>"), 2, 3)

        info_lay.addWidget(QLabel("Truk Mixer & Driver:"), 3, 0)
        info_lay.addWidget(QLabel(f"{d.get('no_plat_truk') or '-'} / {d.get('driver') or '-'}"), 3, 1)

        info_lay.addWidget(QLabel("Status BBM Cor:"), 3, 2)
        st_bbm = str(d.get("status_bbm") or "Belum Diisi")
        bbm_color = "#059669" if st_bbm == "Sudah Diisi" else "#DC2626"
        info_lay.addWidget(QLabel(f"<span style='color: {bbm_color}; font-weight: bold;'>{st_bbm}</span>"), 3, 3)

        info_lay.addWidget(QLabel("Catatan:"), 4, 0)
        info_lay.addWidget(QLabel(f"{d.get('catatan') or '-'}"), 4, 1, 1, 3)

        self.content_layout.addLayout(info_lay)
        self.content_layout.addWidget(QFrame(frameShape=QFrame.HLine))

        # Financial Snapshot (POS / Cashier Integration)
        lbl_fin = QLabel("RINGKASAN KEUANGAN & MARGIN LABA (POS SNAPSHOT):")
        lbl_fin.setStyleSheet(f"font-weight: 700; color: {styles.COLOR_PRIMARY_DARK}; font-size: 12px;")
        self.content_layout.addWidget(lbl_fin)

        fin_grid = QGridLayout()
        fin_grid.setSpacing(8)

        hpp_m3 = float(d.get("hpp_per_m3") or 0)
        tot_hpp = float(d.get("total_hpp") or 0)
        h_jual_m3 = float(d.get("harga_jual_per_m3") or 0)
        tot_pend = float(d.get("total_pendapatan") or 0)
        margin_rp = float(d.get("margin_laba_rp") or 0)
        margin_pct = float(d.get("margin_laba_persen") or 0)

        c1 = StatCard("HPP per m³", styles.format_rupiah(hpp_m3), f"Total HPP: {styles.format_rupiah(tot_hpp)}", "#64748B")
        c2 = StatCard("Harga Jual / m³", styles.format_rupiah(h_jual_m3), f"Total Invoice: {styles.format_rupiah(tot_pend)}", "#2563EB")
        c3 = StatCard("Laba Kotor (Gross)", styles.format_rupiah(margin_rp), f"Margin: {margin_pct:.1f}%", "#059669" if margin_rp >= 0 else "#DC2626")
        
        fin_grid.addWidget(c1, 0, 0)
        fin_grid.addWidget(c2, 0, 1)
        fin_grid.addWidget(c3, 0, 2)
        self.content_layout.addLayout(fin_grid)
        self.content_layout.addWidget(QFrame(frameShape=QFrame.HLine))

        # Rincian Material Terpakai
        lbl_tbl = QLabel("RINCIAN PEMAKAIAN MATERIAL YANG DIPOTONG DARI STOK:")
        lbl_tbl.setStyleSheet(f"font-weight: 700; color: {styles.COLOR_PRIMARY_DARK}; font-size: 12px;")
        self.content_layout.addWidget(lbl_tbl)

        self.table_details = ModernTableWidget(["Kode Material", "Nama Material", "Jumlah Terpakai", "Satuan"])
        self.table_details.setColumnWidth(0, 110)
        self.table_details.setColumnWidth(1, 200)
        self.table_details.setColumnWidth(2, 140)
        self.table_details.setColumnWidth(3, 80)
        self.content_layout.addWidget(self.table_details)

        details = database.get_pengiriman_detail_by_id(d["id"])
        self.table_details.setRowCount(len(details))
        for idx, item in enumerate(details):
            self.table_details.setItem(idx, 0, QTableWidgetItem(str(item["material_kode"])))
            self.table_details.setItem(idx, 1, QTableWidgetItem(str(item["material_nama"])))
            
            qty_item = QTableWidgetItem(f"{styles.format_number(item['jumlah_terpakai'], 2)}")
            qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_details.setItem(idx, 2, qty_item)

            self.table_details.setItem(idx, 3, QTableWidgetItem(str(item["material_satuan"])))

        # Tombol aksi cetak dokumen di bagian footer
        btn_print_lay = QHBoxLayout()
        btn_print_lay.setSpacing(10)

        self.btn_dlg_inv = PrimaryButton("📄 Cetak Invoice (PDF)")
        self.btn_dlg_inv.setFixedHeight(34)
        self.btn_dlg_inv.clicked.connect(self.on_print_invoice)

        self.btn_dlg_sj = SuccessButton("📋 Cetak Surat Jalan (PDF)")
        self.btn_dlg_sj.setFixedHeight(34)
        self.btn_dlg_sj.clicked.connect(self.on_print_sj)

        btn_print_lay.addWidget(self.btn_dlg_inv)
        btn_print_lay.addWidget(self.btn_dlg_sj)
        btn_print_lay.addStretch()

        self.content_layout.addLayout(btn_print_lay)

        self.btn_save.setVisible(False)
        self.btn_cancel.setText("Tutup")

    def on_print_invoice(self):
        parent_obj = self.parent()
        if parent_obj and hasattr(parent_obj, "lihat_invoice"):
            parent_obj.lihat_invoice(self.pengiriman_data["id"])

    def on_print_sj(self):
        parent_obj = self.parent()
        if parent_obj and hasattr(parent_obj, "lihat_surat_jalan"):
            parent_obj.lihat_surat_jalan(self.pengiriman_data["id"])


# ==========================================
# DIALOG CEPAT CATAT BBM SURAT JALAN COR
# ==========================================
class QuickCatatBBMDialog(ModernDialog):
    """Dialog cepat pencatatan BBM/operasional dari baris riwayat pengiriman tertentu"""
    def __init__(self, pengiriman_data: dict, parent=None):
        no_sj = pengiriman_data.get("no_surat_jalan") or f"SJ #{pengiriman_data.get('id')}"
        super().__init__(f"Catat BBM Pengiriman: {no_sj}", parent, min_width=540)
        self.pengiriman_data = pengiriman_data
        self.existing_biaya = database.get_biaya_by_pengiriman_id(pengiriman_data["id"])
        self.init_form()

    def init_form(self):
        d = self.pengiriman_data
        
        # 1. Info Card Terkunci (Auto-Identified dari Pengiriman)
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #F8FAFC;
                border: 1.5px solid {styles.COLOR_BORDER};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        info_lay = QGridLayout(info_frame)
        info_lay.setContentsMargins(4, 4, 4, 4)
        info_lay.setSpacing(6)
        
        info_lay.addWidget(QLabel("No. Surat Jalan:"), 0, 0)
        info_lay.addWidget(QLabel(f"<b>{d.get('no_surat_jalan') or '-'}</b>"), 0, 1)

        info_lay.addWidget(QLabel("Tanggal Kirim:"), 0, 2)
        info_lay.addWidget(QLabel(f"<b>{d.get('tanggal')}</b>"), 0, 3)

        info_lay.addWidget(QLabel("Truk Mixer:"), 1, 0)
        plat = d.get('no_plat_truk') or '-'
        nama_k = d.get('nama_kendaraan') or ''
        plat_str = f"{plat} ({nama_k})" if nama_k else plat
        info_lay.addWidget(QLabel(f"<b>{plat_str}</b>"), 1, 1)

        info_lay.addWidget(QLabel("Driver / Supir:"), 1, 2)
        info_lay.addWidget(QLabel(f"<b>{d.get('driver') or '-'}</b>"), 1, 3)

        info_lay.addWidget(QLabel("Proyek Tujuan:"), 2, 0)
        info_lay.addWidget(QLabel(f"<b>{d.get('proyek_nama') or '-'}</b>"), 2, 1)

        info_lay.addWidget(QLabel("Volume Beton:"), 2, 2)
        info_lay.addWidget(QLabel(f"<b>{styles.format_number(d.get('volume_m3') or 0, 2)} m³</b>"), 2, 3)

        self.content_layout.addWidget(info_frame)
        self.content_layout.addSpacing(6)

        # 2. Pilihan Mode: Isi Solar (Biaya Kas) vs Tangki Cukup (Tanpa Biaya)
        self.rb_isi_bbm = QRadioButton("⛽ Isi Solar / Catat Pengeluaran Kas Operasional")
        self.rb_tangki_cukup = QRadioButton("✅ Tangki Solar Cukup / Gabung Trip Sebelumnya (Tanpa Biaya)")
        
        self.rb_isi_bbm.setChecked(True)
        self.rb_isi_bbm.setCursor(Qt.PointingHandCursor)
        self.rb_tangki_cukup.setCursor(Qt.PointingHandCursor)
        self.rb_isi_bbm.toggled.connect(self.on_mode_changed)

        self.content_layout.addWidget(self.rb_isi_bbm)
        self.content_layout.addWidget(self.rb_tangki_cukup)
        self.content_layout.addSpacing(6)

        # 3. Form Input Biaya BBM
        self.form_frame = QFrame()
        self.form_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        grid = QGridLayout(self.form_frame)
        grid.setSpacing(10)

        # Tanggal Nota
        grid.addWidget(QLabel("Tanggal Nota SPBU:*"), 0, 0, Qt.AlignVCenter)
        self.dt_tgl = QDateEdit()
        self.dt_tgl.setCalendarPopup(True)
        tgl_str = str(d.get("tanggal") or "")[:10]
        self.dt_tgl.setDate(QDate.fromString(tgl_str, "yyyy-MM-dd") if tgl_str else QDate.currentDate())
        self.dt_tgl.setDisplayFormat("yyyy-MM-dd")
        grid.addWidget(self.dt_tgl, 0, 1)

        # Nominal Biaya BBM
        grid.addWidget(QLabel("Nominal Solar (Rp):*"), 1, 0, Qt.AlignVCenter)
        self.spin_nominal = QDoubleSpinBox()
        self.spin_nominal.setRange(100, 10_000_000_000.0)
        self.spin_nominal.setDecimals(0)
        self.spin_nominal.setSingleStep(50000)
        self.spin_nominal.setValue(250000)
        self.spin_nominal.setGroupSeparatorShown(True)
        grid.addWidget(self.spin_nominal, 1, 1)

        # Nama SPBU
        grid.addWidget(QLabel("Nama SPBU / Penjual:"), 2, 0, Qt.AlignVCenter)
        self.txt_spbu = QLineEdit()
        self.txt_spbu.setPlaceholderText("Contoh: SPBU Pertamina Secang")
        grid.addWidget(self.txt_spbu, 2, 1)

        # No Nota
        grid.addWidget(QLabel("No. Nota / Struk:"), 3, 0, Qt.AlignVCenter)
        self.txt_nota = QLineEdit()
        self.txt_nota.setPlaceholderText("Contoh: NOTA-8821 (opsional)")
        grid.addWidget(self.txt_nota, 3, 1)

        # Keterangan / Rincian
        grid.addWidget(QLabel("Rincian / Catatan:*"), 4, 0, Qt.AlignVCenter)
        self.txt_ket = QLineEdit()
        self.txt_ket.setPlaceholderText("Contoh: Solar Dexlite 25 Liter")
        no_sj = d.get('no_surat_jalan') or f"SJ #{d.get('id')}"
        pr_name = d.get('proyek_nama') or ''
        self.txt_ket.setText(f"BBM Pengiriman {no_sj} ({pr_name})")
        grid.addWidget(self.txt_ket, 4, 1)

        self.content_layout.addWidget(self.form_frame)

        # Notice
        self.lbl_notice = QLabel("💡 <b>Otomatis:</b> Biaya ini akan langsung memotong Saldo Kas Plant dan mengubah Status BBM menjadi <b>'Sudah Diisi'</b>.")
        self.lbl_notice.setStyleSheet(f"""
            background-color: {styles.COLOR_INFO_BG};
            color: {styles.COLOR_INFO};
            border: 1px solid #BAE6FD;
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 11px;
        """)
        self.lbl_notice.setWordWrap(True)
        self.content_layout.addWidget(self.lbl_notice)

        self.btn_save.setText("Simpan Biaya BBM")
        self.btn_save.clicked.connect(self.save)

        # Jika sebelumnya sudah ada biaya atau status tangki cukup
        st_bbm = str(d.get("status_bbm") or "")
        if st_bbm == "Tangki Cukup":
            self.rb_tangki_cukup.setChecked(True)
        elif self.existing_biaya:
            eb = self.existing_biaya
            if eb.get("tanggal"):
                self.dt_tgl.setDate(QDate.fromString(str(eb["tanggal"])[:10], "yyyy-MM-dd"))
            self.spin_nominal.setValue(float(eb.get("nominal") or 0))
            self.txt_spbu.setText(str(eb.get("penerima_toko") or ""))
            self.txt_nota.setText(str(eb.get("nomor_nota") or ""))
            self.txt_ket.setText(str(eb.get("keterangan") or ""))

    def on_mode_changed(self):
        is_isi = self.rb_isi_bbm.isChecked()
        self.form_frame.setEnabled(is_isi)
        if is_isi:
            self.lbl_notice.setText("💡 <b>Otomatis:</b> Biaya ini akan langsung memotong Saldo Kas Plant dan mengubah Status BBM menjadi <b>'Sudah Diisi'</b>.")
            self.btn_save.setText("Simpan Biaya BBM")
        else:
            self.lbl_notice.setText("ℹ️ <b>Tangki Cukup:</b> Tidak ada kas yang dipotong. Pengiriman akan ditandai berstatus <b>'Tangki Cukup'</b> dan tidak lagi berstatus tunggakan merah.")
            self.btn_save.setText("Simpan Status BBM")

    def save(self):
        p_id = self.pengiriman_data["id"]
        if self.rb_tangki_cukup.isChecked():
            if self.existing_biaya:
                database.hapus_kas_kantor(self.existing_biaya["id"])
            database.update_status_bbm_pengiriman(p_id, "Tangki Cukup")
            self.accept()
            return

        # Validasi mode Isi BBM
        nom = self.spin_nominal.value()
        if nom <= 0:
            QMessageBox.warning(self, "Peringatan", "Nominal pengeluaran BBM harus lebih besar dari Rp 0!")
            return
        
        tgl = self.dt_tgl.date().toString("yyyy-MM-dd")
        spbu = self.txt_spbu.text().strip()
        nota = self.txt_nota.text().strip()
        ket = self.txt_ket.text().strip()
        if not ket:
            ket = f"BBM Pengiriman {self.pengiriman_data.get('no_surat_jalan') or p_id}"

        k_id = self.pengiriman_data.get("kendaraan_id")
        driver = self.pengiriman_data.get("driver")
        proyek_id = self.pengiriman_data.get("proyek_id")

        try:
            if self.existing_biaya:
                database.update_kas_kantor(
                    kas_kantor_id=self.existing_biaya["id"],
                    tanggal=tgl,
                    nominal=nom,
                    kategori="BBM / Solar Operasional",
                    nomor_nota=nota,
                    penerima_toko=spbu,
                    keterangan=ket,
                    kendaraan_id=k_id,
                    driver=driver,
                    proyek_id=proyek_id,
                    pengiriman_id=p_id
                )
            else:
                database.catat_kas_kantor(
                    tanggal=tgl,
                    nominal=nom,
                    kategori="BBM / Solar Operasional",
                    nomor_nota=nota,
                    penerima_toko=spbu,
                    keterangan=ket,
                    kendaraan_id=k_id,
                    driver=driver,
                    proyek_id=proyek_id,
                    pengiriman_id=p_id
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", f"Gagal menyimpan biaya BBM: {str(e)}")


# ==========================================
# MAIN PRODUKSI & PENGIRIMAN VIEW
# ==========================================
class ProduksiView(QWidget):
    data_changed = Signal()

    def __init__(self, user_session: dict = None, parent=None):
        super().__init__(parent)
        self.user_session = user_session or {}
        self.mutu_list = []
        self.proyek_list = []
        self.init_ui()

    @property
    def current_user_id(self) -> int:
        """Selalu baca user_id dari session terbaru (dinamis, bukan cached)"""
        uid = self.user_session.get("id")
        return int(uid) if uid else 1

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 16)
        main_layout.setSpacing(12)

        self.tabs = QTabWidget()
        self.tab_input = QWidget()
        self.tab_riwayat = QWidget()

        self.setup_tab_input()
        self.setup_tab_riwayat()

        self.tabs.addTab(self.tab_input, "Input Pengiriman / Dispatch (POS)")
        self.tabs.addTab(self.tab_riwayat, "Riwayat Pengiriman Beton")

        main_layout.addWidget(self.tabs)
        self.refresh_all()

    # ------------------------------------------
    # TAB 1: FORM INPUT PENGIRIMAN
    # ------------------------------------------
    def setup_tab_input(self):
        tab_layout = QVBoxLayout(self.tab_input)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content_widget = QWidget()
        content_widget.setObjectName("produksi_scroll_content")
        content_widget.setStyleSheet("#produksi_scroll_content { background: transparent; }")
        layout = QHBoxLayout(content_widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignTop)

        # Left: Form Frame (1-Column Layout identical to Stok Material)
        form_frame = QFrame()
        form_frame.setProperty("class", "CardWidget")
        form_frame.setMinimumWidth(450)
        form_frame.setMaximumWidth(520)
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(18, 18, 18, 18)
        form_layout.setSpacing(14)

        lbl_f_title = QLabel("DATA PENGIRIMAN BETON COR")
        lbl_f_title.setStyleSheet(f"font-weight: 700; color: {styles.COLOR_PRIMARY_DARK}; font-size: 13px;")
        form_layout.addWidget(lbl_f_title)

        grid = QGridLayout()
        grid.setVerticalSpacing(14)
        grid.setHorizontalSpacing(14)
        grid.setContentsMargins(0, 4, 0, 4)
        grid.setColumnMinimumWidth(0, 140)

        # 1. Tanggal
        grid.addWidget(QLabel("Tanggal Pengiriman:*"), 0, 0, Qt.AlignVCenter)
        self.dt_tanggal = QDateEdit()
        self.dt_tanggal.setCalendarPopup(True)
        self.dt_tanggal.setDate(QDate.currentDate())
        self.dt_tanggal.setDisplayFormat("yyyy-MM-dd")
        grid.addWidget(self.dt_tanggal, 0, 1)

        # 2. No Surat Jalan
        grid.addWidget(QLabel("No. Surat Jalan:"), 1, 0, Qt.AlignVCenter)
        self.txt_no_sj = QLineEdit()
        self.txt_no_sj.setPlaceholderText("Auto-generate (mis. SJ-20260911-001)")
        grid.addWidget(self.txt_no_sj, 1, 1)

        # 3. Mutu Beton
        grid.addWidget(QLabel("Mutu Beton:*"), 2, 0, Qt.AlignVCenter)
        self.cb_mutu = QComboBox()
        self.cb_mutu.setView(QListView())
        self.cb_mutu.currentIndexChanged.connect(self.on_mutu_selected)
        grid.addWidget(self.cb_mutu, 2, 1)

        # 4. Volume m3
        grid.addWidget(QLabel("Volume Beton (m³):*"), 3, 0, Qt.AlignVCenter)
        self.spin_vol = QDoubleSpinBox()
        self.spin_vol.setRange(0.1, 1000.0)
        self.spin_vol.setDecimals(2)
        self.spin_vol.setValue(1.0)
        self.spin_vol.valueChanged.connect(self.calculate_live_preview)
        grid.addWidget(self.spin_vol, 3, 1)

        # 5. Harga Jual Satuan per m3
        grid.addWidget(QLabel("Harga Jual / m³ (Rp):*"), 4, 0, Qt.AlignVCenter)
        self.spin_harga_jual = QDoubleSpinBox()
        self.spin_harga_jual.setRange(0, 100_000_000)
        self.spin_harga_jual.setDecimals(0)
        self.spin_harga_jual.setSingleStep(10000)
        self.spin_harga_jual.setValue(850000)
        self.spin_harga_jual.setGroupSeparatorShown(True)
        self.spin_harga_jual.valueChanged.connect(self.calculate_live_preview)
        grid.addWidget(self.spin_harga_jual, 4, 1)

        # 6. Proyek Pelanggan
        grid.addWidget(QLabel("Proyek Tujuan:*"), 5, 0, Qt.AlignVCenter)
        proyek_layout = QHBoxLayout()
        proyek_layout.setSpacing(8)

        self.cb_proyek = QComboBox()
        self.cb_proyek.setView(QListView())
        self.cb_proyek.setEditable(True)
        self.cb_proyek.setInsertPolicy(QComboBox.NoInsert)
        if self.cb_proyek.lineEdit():
            self.cb_proyek.lineEdit().setPlaceholderText("Pilih atau ketik langsung nama proyek...")
        self.cb_proyek.currentIndexChanged.connect(self.on_proyek_selected)
        proyek_layout.addWidget(self.cb_proyek, 1)

        btn_tambah_proyek = SecondaryButton("+ Proyek")
        btn_tambah_proyek.setToolTip("Tambah proyek baru ke master data")
        btn_tambah_proyek.clicked.connect(self.quick_add_proyek)
        proyek_layout.addWidget(btn_tambah_proyek)

        grid.addLayout(proyek_layout, 5, 1)

        # 6b. Tipe Proyek (Button Kiri: Luar, Kanan: Dalam)
        grid.addWidget(QLabel("Tipe Proyek:"), 6, 0, Qt.AlignVCenter)
        tipe_btn_layout = QHBoxLayout()
        tipe_btn_layout.setSpacing(8)
        tipe_btn_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_tipe_luar = QPushButton("🏗️ Proyek Luar")
        self.btn_tipe_luar.setCheckable(True)
        self.btn_tipe_luar.setChecked(True)
        self.btn_tipe_luar.setCursor(Qt.PointingHandCursor)
        self.btn_tipe_luar.setMinimumHeight(34)
        self.btn_tipe_luar.setToolTip("Proyek untuk klien / pemesan eksternal (masuk piutang luar)")

        self.btn_tipe_dalam = QPushButton("🏭 Proyek Dalam")
        self.btn_tipe_dalam.setCheckable(True)
        self.btn_tipe_dalam.setCursor(Qt.PointingHandCursor)
        self.btn_tipe_dalam.setMinimumHeight(34)
        self.btn_tipe_dalam.setToolTip("Proyek milik internal perusahaan sendiri (masuk piutang dalam)")

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
                padding: 4px 8px;
                font-weight: 600;
                font-size: 11.5px;
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
                padding: 4px 8px;
                font-weight: 600;
                font-size: 11.5px;
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
        grid.addLayout(tipe_btn_layout, 6, 1)

        # 7. Detail Lokasi Pengiriman
        grid.addWidget(QLabel("Lokasi / Segment:"), 7, 0, Qt.AlignVCenter)
        self.txt_tujuan = QLineEdit()
        self.txt_tujuan.setPlaceholderText("Contoh: windusari / jembatan pier 1")
        grid.addWidget(self.txt_tujuan, 7, 1)

        # 8. Kendaraan / No Plat Truk Mixer (Dropdown + Tombol Tambah Armada + Status Banner)
        grid.addWidget(QLabel("Kendaraan Mixer:*"), 8, 0, Qt.AlignVCenter)
        mixer_v_layout = QVBoxLayout()
        mixer_v_layout.setSpacing(4)

        mixer_layout = QHBoxLayout()
        mixer_layout.setSpacing(8)

        self.cb_plat_truk = QComboBox()
        self.cb_plat_truk.setView(QListView())
        self.cb_plat_truk.setEditable(True)
        self.cb_plat_truk.setInsertPolicy(QComboBox.NoInsert)
        if self.cb_plat_truk.lineEdit():
            self.cb_plat_truk.lineEdit().setPlaceholderText("Pilih armada mixer atau ketik plat...")
        self.cb_plat_truk.currentIndexChanged.connect(self.on_kendaraan_selected)
        mixer_layout.addWidget(self.cb_plat_truk, 1)

        btn_tambah_armada = SecondaryButton("+ Armada")
        btn_tambah_armada.setToolTip("Tambah armada truk baru ke daftar kendaraan")
        btn_tambah_armada.clicked.connect(self.quick_add_kendaraan)
        mixer_layout.addWidget(btn_tambah_armada)

        mixer_v_layout.addLayout(mixer_layout)

        # Dynamic Status Alert Banner (Tampil saat truk yang dipilih sedang operasional / servis)
        self.frame_truk_status = QFrame()
        self.frame_truk_status.setObjectName("frameTrukStatus")
        self.frame_truk_status.setVisible(False)
        f_lay = QHBoxLayout(self.frame_truk_status)
        f_lay.setContentsMargins(10, 6, 10, 6)
        f_lay.setSpacing(10)

        self.lbl_truk_status_desc = QLabel()
        self.lbl_truk_status_desc.setObjectName("lblTrukStatusDesc")
        self.lbl_truk_status_desc.setWordWrap(True)
        self.lbl_truk_status_desc.setStyleSheet("background: transparent; border: none;")
        f_lay.addWidget(self.lbl_truk_status_desc, 1)

        self.btn_truk_kembali = SecondaryButton("🔄 Set Truk Sudah Kembali")
        self.btn_truk_kembali.setFixedHeight(28)
        self.btn_truk_kembali.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #1E293B;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                padding: 3px 12px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: #F8FAFC;
                border-color: #94A3B8;
            }
        """)
        self.btn_truk_kembali.setToolTip("Klik jika truk sebenarnya sudah kembali ke plant dan siap standby")
        self.btn_truk_kembali.clicked.connect(self.set_truk_terpilih_kembali)
        f_lay.addWidget(self.btn_truk_kembali)

        mixer_v_layout.addWidget(self.frame_truk_status)

        grid.addLayout(mixer_v_layout, 8, 1)

        # 9. Driver
        grid.addWidget(QLabel("Nama Driver:"), 9, 0, Qt.AlignVCenter)
        self.txt_driver = QLineEdit()
        self.txt_driver.setPlaceholderText("Nama pengemudi truk mixer")
        grid.addWidget(self.txt_driver, 9, 1)

        # 10. Catatan
        grid.addWidget(QLabel("Catatan:"), 10, 0, Qt.AlignVCenter)
        self.txt_catatan = QLineEdit()
        self.txt_catatan.toPlainText = self.txt_catatan.text
        self.txt_catatan.setPlaceholderText("Slump tes, instruksi lapangan, dsb (opsional)")
        grid.addWidget(self.txt_catatan, 10, 1)

        # 11. Opsi Surat Jalan (Hide Harga)
        grid.addWidget(QLabel("Surat Jalan:"), 11, 0, Qt.AlignVCenter)
        self.chk_hide_harga_sj = QCheckBox("Sembunyikan Harga & Jumlah di Surat Jalan (Format Non-Harga)")
        self.chk_hide_harga_sj.setChecked(False)
        self.chk_hide_harga_sj.setCursor(Qt.PointingHandCursor)
        self.chk_hide_harga_sj.setToolTip("Jika dicentang, kolom HARGA dan JUMLAH akan disembunyikan pada cetakan Surat Jalan fisik (Invoice tetap menampilkan harga lengkap)")
        self.chk_hide_harga_sj.setStyleSheet(f"""
            QCheckBox {{
                font-weight: 600;
                color: {styles.COLOR_TEXT_MAIN};
                font-size: 12px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1.5px solid {styles.COLOR_BORDER};
                background-color: #FFFFFF;
            }}
            QCheckBox::indicator:hover {{
                border-color: {styles.COLOR_PRIMARY_LIGHT};
            }}
            QCheckBox::indicator:checked {{
                background-color: {styles.COLOR_PRIMARY_LIGHT};
                border-color: {styles.COLOR_PRIMARY_LIGHT};
            }}
        """)
        grid.addWidget(self.chk_hide_harga_sj, 11, 1)

        form_layout.addLayout(grid)

        # POS Automation Notification Banner (Compact)
        lbl_pos_notice = QLabel("💡 <b>Otomasi:</b> Simpan pengiriman otomatis <b>memotong stok</b> & mencatat <b>piutang proyek</b> di Keuangan.")
        lbl_pos_notice.setStyleSheet(f"""
            background-color: {styles.COLOR_INFO_BG};
            color: {styles.COLOR_INFO};
            border: 1px solid #BAE6FD;
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 11px;
        """)
        lbl_pos_notice.setWordWrap(True)
        form_layout.addWidget(lbl_pos_notice)

        # BBM Reminder Notice
        lbl_bbm_notice = QLabel("⛽ <b>Status BBM:</b> Pengiriman yang baru disimpan berstatus <b>'Belum Diisi'</b>. Biaya BBM dapat dicatat & ditautkan langsung melalui menu <b>Operasional Kendaraan</b>.")
        lbl_bbm_notice.setStyleSheet("""
            background-color: #FFFBEB;
            color: #92400E;
            border: 1px solid #FDE68A;
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 11px;
        """)
        lbl_bbm_notice.setWordWrap(True)
        form_layout.addWidget(lbl_bbm_notice)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_reset = SecondaryButton("Reset Form")
        btn_reset.clicked.connect(self.reset_form)

        btn_simpan = PrimaryButton("Simpan & Potong Stok")
        btn_simpan.clicked.connect(self.simpan_pengiriman)

        btn_layout.addWidget(btn_reset)
        btn_layout.addWidget(btn_simpan)
        form_layout.addLayout(btn_layout)
        form_layout.addStretch()

        layout.addWidget(form_frame, 6)

        # Right: Live POS Financial Preview & Recipe Calculation
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # Card 1: Live POS Margin & Revenue Calculation
        fin_frame = QFrame()
        fin_frame.setProperty("class", "CardWidget")
        fin_layout = QVBoxLayout(fin_frame)
        fin_layout.setContentsMargins(14, 12, 14, 12)
        fin_layout.setSpacing(8)

        lbl_fin_title = QLabel("KALKULASI HPP, HARGA JUAL & MARGIN LABA (POS LIVE)")
        lbl_fin_title.setStyleSheet(f"font-weight: 700; color: {styles.COLOR_PRIMARY_DARK}; font-size: 12px;")
        fin_layout.addWidget(lbl_fin_title)

        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(8)

        self.card_prev_hpp = StatCard("HPP / m³", "Rp 0", "HPP Material + Ops", "#64748B")
        self.card_prev_tot_hpp = StatCard("Total HPP Batch", "Rp 0", "HPP × Volume", "#475569")
        self.card_prev_rev = StatCard("Total Tagihan", "Rp 0", "Harga Jual × Volume", "#2563EB")
        self.card_prev_margin = StatCard("Estimasi Laba Kotor", "Rp 0", "Margin: 0.0%", "#059669")

        for c in [self.card_prev_hpp, self.card_prev_tot_hpp, self.card_prev_rev, self.card_prev_margin]:
            c.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        kpi_grid.addWidget(self.card_prev_hpp, 0, 0)
        kpi_grid.addWidget(self.card_prev_tot_hpp, 0, 1)
        kpi_grid.addWidget(self.card_prev_rev, 1, 0)
        kpi_grid.addWidget(self.card_prev_margin, 1, 1)

        fin_layout.addLayout(kpi_grid)
        right_layout.addWidget(fin_frame)

        # Card 2: Live Material Recipe & Stock Check Preview
        preview_frame = QFrame()
        preview_frame.setProperty("class", "CardWidget")
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(14, 12, 14, 12)
        preview_layout.setSpacing(8)

        lbl_p_title = QLabel("PENGECEKAN KETERSEDIAAN STOK MATERIAL")
        lbl_p_title.setStyleSheet(f"font-weight: 700; color: {styles.COLOR_PRIMARY_DARK}; font-size: 12px;")
        preview_layout.addWidget(lbl_p_title)

        self.lbl_calc_desc = QLabel("Kebutuhan material berdasarkan resep mutu × volume pengiriman:")
        self.lbl_calc_desc.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11.5px;")
        preview_layout.addWidget(self.lbl_calc_desc)

        self.table_preview = ModernTableWidget(["Material", "Resep", "Butuh", "Stok Anda", "Status"])
        self.table_preview.verticalHeader().setDefaultSectionSize(32)
        self.table_preview.setMinimumHeight(150)
        
        header = self.table_preview.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table_preview.setColumnWidth(1, 65)
        self.table_preview.setColumnWidth(2, 75)
        self.table_preview.setColumnWidth(3, 75)
        self.table_preview.setColumnWidth(4, 70)
        
        preview_layout.addWidget(self.table_preview)

        self.lbl_stock_status_box = QLabel("Status Ketersediaan: Stok Aman")
        self.lbl_stock_status_box.setStyleSheet(f"""
            background-color: {styles.COLOR_SUCCESS_BG};
            color: {styles.COLOR_SUCCESS};
            border: 1px solid #A7F3D0;
            border-radius: 6px;
            padding: 7px 10px;
            font-weight: 700;
            font-size: 11.5px;
        """)
        preview_layout.addWidget(self.lbl_stock_status_box)

        right_layout.addWidget(preview_frame)
        layout.addWidget(right_container, 5)

        scroll.setWidget(content_widget)
        tab_layout.addWidget(scroll)

    def on_mutu_selected(self):
        mutu_id = self.cb_mutu.currentData()
        if not mutu_id:
            return
        # Ambil harga jual standar mutu dari list
        matched = next((m for m in self.mutu_list if m["id"] == mutu_id), None)
        if matched and float(matched.get("harga_jual_per_m3") or 0) > 0:
            self.spin_harga_jual.setValue(float(matched["harga_jual_per_m3"]))
        self.calculate_live_preview()

    def calculate_live_preview(self):
        mutu_id = self.cb_mutu.currentData()
        vol = self.spin_vol.value()
        h_jual = self.spin_harga_jual.value()

        if not mutu_id or vol <= 0:
            self.table_preview.setRowCount(0)
            self.card_prev_hpp.update_value("Rp 0")
            self.card_prev_tot_hpp.update_value("Rp 0")
            self.card_prev_rev.update_value("Rp 0")
            self.card_prev_margin.update_value("Rp 0")
            return

        # 1. Hitung Kebutuhan Material & Cek Stok Individual User
        preview_items = database.preview_kebutuhan_material(mutu_id, vol, user_id=self.current_user_id)
        self.table_preview.setRowCount(len(preview_items))

        all_sufficient = True
        insufficient_materials = []

        for r_idx, item in enumerate(preview_items):
            self.table_preview.setItem(r_idx, 0, QTableWidgetItem(f"{item['material_nama']} ({item['material_satuan']})"))
            
            resep_item = QTableWidgetItem(f"{styles.format_number(item['jumlah_per_m3'], 2)}")
            resep_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_preview.setItem(r_idx, 1, resep_item)

            butuh_item = QTableWidgetItem(f"{styles.format_number(item['kebutuhan'], 2)}")
            butuh_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            butuh_item.setForeground(Qt.darkBlue)
            self.table_preview.setItem(r_idx, 2, butuh_item)

            stk_item = QTableWidgetItem(f"{styles.format_number(item['stok_saat_ini'], 2)}")
            stk_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_preview.setItem(r_idx, 3, stk_item)

            cukup = bool(item["cukup"])
            if not cukup:
                all_sufficient = False
                insufficient_materials.append(item["material_nama"])

            badge = BadgeLabel("Cukup" if cukup else "Kurang", "success" if cukup else "danger")
            self.table_preview.setCellWidget(r_idx, 4, badge)

        if all_sufficient:
            self.lbl_stock_status_box.setText("Seluruh material mencukupi untuk volume pengiriman ini.")
            self.lbl_stock_status_box.setStyleSheet(f"""
                background-color: {styles.COLOR_SUCCESS_BG};
                color: {styles.COLOR_SUCCESS};
                border: 1px solid #A7F3D0;
                border-radius: 6px;
                padding: 7px 10px;
                font-weight: 700;
                font-size: 11.5px;
            """)
        else:
            stok_nol_items = [item["material_nama"] for item in preview_items if float(item.get("stok_saat_ini") or 0) <= 0]
            if stok_nol_items:
                nol_str = ", ".join(stok_nol_items)
                self.lbl_stock_status_box.setText(f"⛔ PERINGATAN: Stok material habis / 0 ({nol_str})! Pengiriman tidak dapat diproses.")
            else:
                kurang_str = ", ".join(insufficient_materials)
                self.lbl_stock_status_box.setText(f"PERINGATAN: Stok material tidak mencukupi ({kurang_str})!")
            self.lbl_stock_status_box.setStyleSheet(f"""
                background-color: {styles.COLOR_DANGER_BG};
                color: {styles.COLOR_DANGER};
                border: 1px solid #FECACA;
                border-radius: 6px;
                padding: 7px 10px;
                font-weight: 700;
                font-size: 11.5px;
            """)

        # 2. Hitung HPP, Total Tagihan & Margin Laba
        calc_hpp = database.calculate_mutu_hpp(mutu_id)
        hpp_m3 = calc_hpp["hpp_per_m3"]
        tot_hpp = hpp_m3 * vol
        tot_pendapatan = h_jual * vol
        laba_rp = tot_pendapatan - tot_hpp
        margin_pct = (laba_rp / tot_pendapatan * 100.0) if tot_pendapatan > 0 else 0.0

        self.card_prev_hpp.update_value(styles.format_rupiah(hpp_m3))
        self.card_prev_tot_hpp.update_value(styles.format_rupiah(tot_hpp))
        self.card_prev_rev.update_value(styles.format_rupiah(tot_pendapatan))
        self.card_prev_margin.update_value(styles.format_rupiah(laba_rp), f"Margin: {margin_pct:.1f}%")

    def get_tipe_proyek(self):
        """Mendapatkan tipe proyek yang dipilih (luar / dalam)"""
        if hasattr(self, "btn_tipe_dalam") and self.btn_tipe_dalam.isChecked():
            return "dalam"
        return "luar"

    def set_tipe_proyek(self, tipe):
        """Mengatur pilihan tipe proyek pada toggle button"""
        if str(tipe).lower() == "dalam":
            if hasattr(self, "btn_tipe_dalam"):
                self.btn_tipe_dalam.setChecked(True)
        else:
            if hasattr(self, "btn_tipe_luar"):
                self.btn_tipe_luar.setChecked(True)

    def on_proyek_selected(self):
        """Auto-sinkronkan Tipe Proyek saat memilih proyek dari dropdown"""
        proyek_id = self.cb_proyek.currentData()
        if proyek_id:
            matched = next((p for p in self.proyek_list if p["id"] == proyek_id), None)
            if matched:
                tipe = matched.get("tipe_proyek") or "luar"
                self.set_tipe_proyek(tipe)

    def get_plat_truk(self) -> str:
        """Mendapatkan nomor plat dari pilihan combobox atau teks yang diketik"""
        if not hasattr(self, "cb_plat_truk"):
            return ""
        data = self.cb_plat_truk.currentData()
        if data:
            return str(data).strip()
        text = self.cb_plat_truk.currentText().strip()
        if not text:
            return ""
        # Ambil bagian plat sebelum separator dash atau kurung jika ada
        return text.split(" - ")[0].split(" (")[0].strip()

    def get_kendaraan_id(self) -> Optional[int]:
        """Mendapatkan ID kendaraan dari plat truk yang dipilih"""
        plat = self.get_plat_truk()
        if not plat:
            return None
        kend = database.get_kendaraan_by_plat(plat)
        return kend["id"] if kend else None

    def on_kendaraan_selected(self):
        """Saat armada dipilih dari dropdown, isi driver default dan periksa status kesiapan armada"""
        plat = self.get_plat_truk()
        if not plat:
            if hasattr(self, "frame_truk_status"):
                self.frame_truk_status.setVisible(False)
            return

        kend = database.get_kendaraan_by_plat(plat)
        if kend:
            if kend.get("driver_default") and not self.txt_driver.text().strip():
                self.txt_driver.setText(kend["driver_default"])

            st = str(kend.get("status") or "tersedia").lower()
            if hasattr(self, "frame_truk_status"):
                if st == "operasional":
                    ket = kend.get("keterangan_operasional") or "Sedang bertugas pengiriman lapangan"
                    self.lbl_truk_status_desc.setText(
                        f"⛔ <b>ARMADA SEDANG DIGUNAKAN:</b> {ket}"
                    )
                    self.lbl_truk_status_desc.setStyleSheet("color: #B91C1C; font-size: 11.5px; background: transparent; border: none;")
                    self.frame_truk_status.setStyleSheet("""
                        QFrame#frameTrukStatus {
                            background-color: #FEF2F2;
                            border: 1px solid #FECACA;
                            border-radius: 6px;
                        }
                    """)
                    self.btn_truk_kembali.setVisible(True)
                    self.frame_truk_status.setVisible(True)
                elif st == "maintenance":
                    self.lbl_truk_status_desc.setText(
                        "🟠 <b>ARMADA DALAM PERBAIKAN:</b> Sedang dalam perawatan / servis bengkel."
                    )
                    self.lbl_truk_status_desc.setStyleSheet("color: #B45309; font-size: 11.5px; background: transparent; border: none;")
                    self.frame_truk_status.setStyleSheet("""
                        QFrame#frameTrukStatus {
                            background-color: #FFFBEB;
                            border: 1px solid #FDE68A;
                            border-radius: 6px;
                        }
                    """)
                    self.btn_truk_kembali.setVisible(False)
                    self.frame_truk_status.setVisible(True)
                else:
                    self.frame_truk_status.setVisible(False)
        else:
            if hasattr(self, "frame_truk_status"):
                self.frame_truk_status.setVisible(False)

    def set_truk_terpilih_kembali(self):
        """Mengubah status truk yang sedang digunakan menjadi Siap / Standby di Plant"""
        plat = self.get_plat_truk()
        if plat:
            database.update_status_operasional_kendaraan(plat, "tersedia", "Standby di Batching Plant")
            QMessageBox.information(
                self,
                "Truk Kembali ke Plant",
                f"Status armada '{plat}' berhasil diubah menjadi Siap / Standby di Plant."
            )
            self.refresh_all()
            self.data_changed.emit()

    def quick_add_kendaraan(self):
        """Membuka dialog tambah armada cepat dari layar POS pengiriman"""
        from ui.kendaraan_view import KendaraanDialog
        dlg = KendaraanDialog(parent=self)
        if dlg.exec():
            self.refresh_all()
            self.data_changed.emit()
            k_list = database.get_all_kendaraan()
            if k_list:
                last_k = k_list[-1]
                idx = self.cb_plat_truk.findData(last_k["no_plat"])
                if idx >= 0:
                    self.cb_plat_truk.setCurrentIndex(idx)

    def reset_form(self):
        self.spin_vol.setValue(1.0)
        self.txt_no_sj.clear()
        self.txt_tujuan.clear()
        if hasattr(self, "cb_plat_truk"):
            if self.cb_plat_truk.count() > 0:
                self.cb_plat_truk.setCurrentIndex(0)
            elif self.cb_plat_truk.lineEdit():
                self.cb_plat_truk.lineEdit().clear()
        self.txt_driver.clear()
        self.txt_catatan.clear()
        self.dt_tanggal.setDate(QDate.currentDate())
        self.set_tipe_proyek("luar")
        if hasattr(self, "chk_hide_harga_sj"):
            self.chk_hide_harga_sj.setChecked(False)
        self.on_mutu_selected()
        self.on_kendaraan_selected()  # Auto-fill driver default dari armada index 0
        self.calculate_live_preview()

    def quick_add_proyek(self):
        from ui.master_data_view import ProyekDialog
        dlg = ProyekDialog(parent=self)
        if dlg.exec():
            self.refresh_all()
            self.data_changed.emit()
            proyeks = database.get_all_proyek(only_active=True)
            if proyeks:
                last_pr = proyeks[-1]
                idx = self.cb_proyek.findData(last_pr["id"])
                if idx >= 0:
                    self.cb_proyek.setCurrentIndex(idx)

    def simpan_pengiriman(self):
        mutu_id = self.cb_mutu.currentData()
        vol = self.spin_vol.value()
        harga_jual = self.spin_harga_jual.value()
        tanggal = self.dt_tanggal.date().toString("yyyy-MM-dd")
        no_sj = self.txt_no_sj.text().strip()
        tujuan = self.txt_tujuan.text().strip()
        plat = self.get_plat_truk()
        driver = self.txt_driver.text().strip()
        catatan = self.txt_catatan.toPlainText().strip()
        tipe_proyek = self.get_tipe_proyek()

        # Validasi Input Proyek
        typed_proyek_text = self.cb_proyek.currentText().strip()
        if not typed_proyek_text:
            QMessageBox.warning(self, "Peringatan", "Silakan pilih atau ketik Proyek Tujuan!")
            return

        proyek_id = self.cb_proyek.currentData()
        matched_pr = next(
            (p for p in self.proyek_list if p["nama"].lower() == typed_proyek_text.lower() or f"{p['nama']} ({p['lokasi'] or '-'})".lower() == typed_proyek_text.lower()), 
            None
        )
        if matched_pr:
            proyek_id = matched_pr["id"]
            # Sinkronkan tipe_proyek jika berbeda dengan pilihan user
            if matched_pr.get("tipe_proyek") != tipe_proyek:
                database.save_proyek(
                    nama=matched_pr["nama"],
                    lokasi=matched_pr.get("lokasi") or "",
                    status=matched_pr.get("status") or "aktif",
                    keterangan=matched_pr.get("keterangan") or "",
                    proyek_id=proyek_id,
                    tipe_proyek=tipe_proyek
                )
        elif not proyek_id or (self.cb_proyek.currentIndex() >= 0 and self.cb_proyek.itemText(self.cb_proyek.currentIndex()) != typed_proyek_text):
            try:
                proyek_id = database.save_proyek(
                    nama=typed_proyek_text,
                    lokasi=tujuan if tujuan else "Lokasi Proyek",
                    status="aktif",
                    keterangan="Dibuat otomatis dari input pengiriman cor",
                    tipe_proyek=tipe_proyek
                )
                self.refresh_all()
                self.data_changed.emit()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal membuat proyek baru: {str(e)}")
                return

        if not mutu_id:
            QMessageBox.warning(self, "Peringatan", "Silakan pilih Mutu Beton!")
            return
        if not proyek_id:
            QMessageBox.warning(self, "Peringatan", "Silakan tentukan Proyek Pelanggan!")
            return
        if vol <= 0:
            QMessageBox.warning(self, "Peringatan", "Volume pengiriman harus lebih dari 0 m³!")
            return
        if harga_jual <= 0:
            QMessageBox.warning(self, "Peringatan", "Harga jual per m³ harus lebih dari Rp 0!")
            return

        # Validasi Armada: Cek Status Sedang Digunakan (Operasional), Servis, Nonaktif & Overload
        if plat:
            kend = database.get_kendaraan_by_plat(plat)
            if kend:
                k_nama = kend.get("nama_kendaraan") or plat
                k_status = str(kend.get("status") or "tersedia").lower()

                # BLOKIR JIKA TRUK SEDANG DIGUNAKAN / OPERASIONAL
                if k_status == "operasional":
                    ket_tugas = kend.get("keterangan_operasional") or "Pengiriman cor lapangan"
                    msg_op = (
                        f"⛔ TRUK SEDANG DIGUNAKAN!\n\n"
                        f"Armada '{k_nama}' ({plat}) saat ini tercatat masih bertugas di lapangan.\n\n"
                        f"Rincian Tugas Saat Ini:\n"
                        f"• {ket_tugas}\n\n"
                        f"Truk yang sedang jalan TIDAK DAPAT DITUGASKAN untuk pengiriman baru sebelum kembali ke plant.\n\n"
                        f"Apakah armada ini sebenarnya SUDAH KEMBALI ke Batching Plant dan siap berangkat lagi?"
                    )
                    if confirm_dialog(self, "Konfirmasi Kepulangan Truk", msg_op):
                        database.update_status_operasional_kendaraan(plat, "tersedia", "Standby di Batching Plant")
                    else:
                        QMessageBox.warning(
                            self,
                            "Pengiriman Dibatalkan",
                            f"Transaksi pengiriman DIBATALKAN.\n\nSilakan pilih armada lain yang berstatus Siap / Standby, atau tunggu armada '{k_nama}' kembali ke Batching Plant."
                        )
                        return

                elif k_status == "maintenance":
                    if not confirm_dialog(
                        self,
                        "Peringatan Armada Servis",
                        f"⚠️ PERINGATAN KENDARAAN DALAM PERBAIKAN!\n\n"
                        f"Armada '{k_nama}' ({plat}) saat ini berstatus DALAM PERBAIKAN / SERVIS BENGKEL.\n\n"
                        f"Apakah Anda yakin tetap ingin menugaskan unit ini untuk pengiriman?"
                    ):
                        return
                elif k_status == "nonaktif":
                    if not confirm_dialog(
                        self,
                        "Peringatan Armada Nonaktif",
                        f"⚠️ PERINGATAN KENDARAAN NONAKTIF!\n\n"
                        f"Armada '{k_nama}' ({plat}) berstatus NONAKTIF / ARSIP.\n\n"
                        f"Apakah Anda yakin ingin mengaktifkan dan menugaskan unit ini?"
                    ):
                        return

        preview_items = database.preview_kebutuhan_material(mutu_id, vol, user_id=self.current_user_id)
        if not preview_items:
            QMessageBox.warning(self, "Peringatan", "Mutu beton ini belum memiliki komposisi resep material! Silakan atur di Master Data.")
            return

        kurang = [item for item in preview_items if not item["cukup"]]
        if kurang:
            # 1. Jika ada material yang stoknya 0 atau minus, BLOKIR TOTAL (tidak bisa lanjut sama sekali)
            stok_nol = [k for k in kurang if float(k.get("stok_saat_ini") or 0) <= 0]
            if stok_nol:
                nol_msg = "\n".join([
                    f"• {k['material_nama']}: Butuh {styles.format_number(k['kebutuhan'], 2)} {k['material_satuan']} (Sisa stok: 0 {k['material_satuan']})"
                    for k in stok_nol
                ])
                QMessageBox.critical(
                    self,
                    "Stok Material 0 - Tidak Bisa Lanjut",
                    f"Transaksi TIDAK DAPAT DILANJUTKAN!\n\n"
                    f"Stok material berikut bernilai 0 (habis):\n\n"
                    f"{nol_msg}\n\n"
                    f"Silakan lakukan pengadaan / input stok masuk material terlebih dahulu sebelum membuat pengiriman."
                )
                return

            # 2. Jika stok masih ada tetapi kurang dari kebutuhan volume penuh
            kurang_msg = "\n".join([
                f"• {k['material_nama']}: Butuh {styles.format_number(k['kebutuhan'], 2)} {k['material_satuan']}, sisa stok hanya {styles.format_number(k['stok_saat_ini'], 2)} {k['material_satuan']}" 
                for k in kurang
            ])
            if not confirm_dialog(
                self, 
                "Konfirmasi Stok Kurang", 
                f"PERINGATAN: Sisa stok material berikut tidak mencukupi untuk volume penuh:\n\n"
                f"{kurang_msg}\n\n"
                f"Apakah Anda tetap ingin melanjutkan simpan (stok akan bernilai minus)?"
            ):
                return

        hide_harga_sj = 1 if hasattr(self, "chk_hide_harga_sj") and self.chk_hide_harga_sj.isChecked() else 0

        try:
            ok, msg, p_id = database.simpan_pengiriman(
                tanggal=tanggal, mutu_beton_id=mutu_id, volume_m3=vol,
                proyek_id=proyek_id, tujuan_pengiriman=tujuan, no_surat_jalan=no_sj,
                no_plat_truk=plat, driver=driver, catatan=catatan,
                harga_jual_kustom=harga_jual,
                user_id=self.current_user_id,
                hide_harga_sj=hide_harga_sj,
                kendaraan_id=self.get_kendaraan_id()
            )
            if ok:
                self.reset_form()
                self.load_riwayat()
                self.data_changed.emit()
                if p_id:
                    self.prompt_cetak_dokumen(p_id, msg)
            else:
                QMessageBox.warning(self, "Gagal", msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Terjadi kesalahan: {str(e)}")

    # ------------------------------------------
    # TAB 2: RIWAYAT PENGIRIMAN
    # ------------------------------------------
    def setup_tab_riwayat(self):
        layout = QVBoxLayout(self.tab_riwayat)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        filter_frame = QFrame()
        filter_frame.setProperty("class", "CardWidget")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(10, 8, 10, 8)
        filter_layout.setSpacing(8)

        filter_layout.addWidget(QLabel("Proyek:"))
        self.cb_filter_proyek = QComboBox()
        self.cb_filter_proyek.setView(QListView())
        filter_layout.addWidget(self.cb_filter_proyek)

        filter_layout.addWidget(QLabel("Mutu:"))
        self.cb_filter_mutu = QComboBox()
        self.cb_filter_mutu.setView(QListView())
        filter_layout.addWidget(self.cb_filter_mutu)

        filter_layout.addWidget(QLabel("BBM:"))
        self.cb_filter_bbm = QComboBox()
        self.cb_filter_bbm.setView(QListView())
        self.cb_filter_bbm.addItem("Semua Status BBM", "all")
        self.cb_filter_bbm.addItem("⚠️ Belum Diisi", "Belum Diisi")
        self.cb_filter_bbm.addItem("✅ Sudah Diisi", "Sudah Diisi")
        self.cb_filter_bbm.addItem("⛽ Tangki Cukup", "Tangki Cukup")
        self.cb_filter_bbm.currentIndexChanged.connect(self.load_riwayat)
        filter_layout.addWidget(self.cb_filter_bbm)

        filter_layout.addWidget(QLabel("Mulai:"))
        self.dt_f_start = QDateEdit()
        self.dt_f_start.setCalendarPopup(True)
        self.dt_f_start.setDate(QDate.currentDate().addMonths(-3))
        self.dt_f_start.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self.dt_f_start)

        filter_layout.addWidget(QLabel("Sampai:"))
        self.dt_f_end = QDateEdit()
        self.dt_f_end.setCalendarPopup(True)
        self.dt_f_end.setDate(QDate.currentDate())
        self.dt_f_end.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self.dt_f_end)

        self.txt_f_search = QLineEdit()
        self.txt_f_search.setPlaceholderText("Cari No SJ / Lokasi / Driver...")
        filter_layout.addWidget(self.txt_f_search)

        btn_apply = PrimaryButton("Filter")
        btn_apply.clicked.connect(self.load_riwayat)
        filter_layout.addWidget(btn_apply)

        btn_reset = SecondaryButton("Reset")
        btn_reset.clicked.connect(self.reset_filter_riwayat)
        filter_layout.addWidget(btn_reset)

        layout.addWidget(filter_frame)

        # Table Riwayat Pengiriman
        self.table_riwayat = ModernTableWidget([
            "No", "No Surat Jalan", "Proyek", "Mutu", "Vol (m³)", "Driver", "Status BBM", "Aksi"
        ])
        self.table_riwayat.setColumnWidth(0, 40)
        self.table_riwayat.setColumnWidth(1, 135)
        self.table_riwayat.setColumnWidth(3, 70)
        self.table_riwayat.setColumnWidth(4, 65)
        self.table_riwayat.setColumnWidth(5, 100)
        self.table_riwayat.setColumnWidth(6, 95)
        self.table_riwayat.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_riwayat.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.table_riwayat.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
        self.table_riwayat.setColumnWidth(7, 285)
        layout.addWidget(self.table_riwayat)

    def load_riwayat(self):
        pr_id = self.cb_filter_proyek.currentData()
        mt_id = self.cb_filter_mutu.currentData()
        bbm_status = self.cb_filter_bbm.currentData() if hasattr(self, "cb_filter_bbm") else None
        s_date = self.dt_f_start.date().toString("yyyy-MM-dd")
        e_date = self.dt_f_end.date().toString("yyyy-MM-dd")
        search = self.txt_f_search.text().strip()

        data = database.get_riwayat_pengiriman(
            start_date=s_date, end_date=e_date,
            proyek_id=pr_id if pr_id != -1 else None,
            mutu_id=mt_id if mt_id != -1 else None,
            search=search if search else None,
            status_bbm=bbm_status
        )

        self.table_riwayat.setRowCount(len(data))
        for r_idx, r in enumerate(data):
            # Col 0: No
            no_item = QTableWidgetItem(str(r_idx + 1))
            no_item.setTextAlignment(Qt.AlignCenter)
            self.table_riwayat.setItem(r_idx, 0, no_item)

            # Col 1: No Surat Jalan
            self.table_riwayat.setItem(r_idx, 1, QTableWidgetItem(str(r["no_surat_jalan"] or "-")))

            # Col 2: Proyek
            self.table_riwayat.setItem(r_idx, 2, QTableWidgetItem(str(r["proyek_nama"])))

            # Col 3: Mutu
            mutu_item = QTableWidgetItem(str(r["mutu_kode"]))
            mutu_item.setTextAlignment(Qt.AlignCenter)
            self.table_riwayat.setItem(r_idx, 3, mutu_item)

            # Col 4: Vol (m³)
            vol_item = QTableWidgetItem(f"{styles.format_number(r['volume_m3'], 2)}")
            vol_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_riwayat.setItem(r_idx, 4, vol_item)

            # Col 5: Driver
            self.table_riwayat.setItem(r_idx, 5, QTableWidgetItem(str(r["driver"] or "-")))

            # Col 6: Status BBM Interactive Button
            st_bbm = str(r.get("status_bbm") or "Belum Diisi")
            btn_bbm = QPushButton()
            btn_bbm.setCursor(Qt.PointingHandCursor)
            btn_bbm.setFixedHeight(24)
            
            if st_bbm == "Sudah Diisi":
                btn_bbm.setText("✅ Diisi")
                btn_bbm.setToolTip("BBM telah tercatat di kas operasional. Klik untuk melihat / mengedit biaya BBM.")
                btn_bbm.setStyleSheet("""
                    QPushButton {
                        background-color: #F0FDF4;
                        color: #16A34A;
                        border: 1px solid #BBF7D0;
                        border-radius: 12px;
                        padding: 2px 6px;
                        font-weight: 700;
                        font-size: 10.5px;
                    }
                    QPushButton:hover {
                        background-color: #DCFCE7;
                        border-color: #86EFAC;
                    }
                """)
            elif st_bbm == "Tangki Cukup":
                btn_bbm.setText("⛽ Cukup")
                btn_bbm.setToolTip("Armada menggunakan solar sisa trip sebelumnya / gabungan. Klik untuk ubah.")
                btn_bbm.setStyleSheet("""
                    QPushButton {
                        background-color: #EFF6FF;
                        color: #2563EB;
                        border: 1px solid #BFDBFE;
                        border-radius: 12px;
                        padding: 2px 6px;
                        font-weight: 700;
                        font-size: 10.5px;
                    }
                    QPushButton:hover {
                        background-color: #DBEAFE;
                        border-color: #93C5FD;
                    }
                """)
            else:
                btn_bbm.setText("⚠️ Catat")
                btn_bbm.setToolTip("BBM belum dicatat. Klik untuk mencatat pengeluaran BBM langsung untuk surat jalan ini.")
                btn_bbm.setStyleSheet("""
                    QPushButton {
                        background-color: #FEF2F2;
                        color: #DC2626;
                        border: 1px solid #FECACA;
                        border-radius: 12px;
                        padding: 2px 6px;
                        font-weight: 700;
                        font-size: 10.5px;
                    }
                    QPushButton:hover {
                        background-color: #FEE2E2;
                        border-color: #F87171;
                    }
                """)
            
            btn_bbm.clicked.connect(lambda _, row_data=r: self.buka_catat_bbm_cepat(row_data))
            
            bbm_cell = QWidget()
            bbm_lay = QHBoxLayout(bbm_cell)
            bbm_lay.setContentsMargins(2, 2, 2, 2)
            bbm_lay.setAlignment(Qt.AlignCenter)
            bbm_lay.addWidget(btn_bbm)
            self.table_riwayat.setCellWidget(r_idx, 6, bbm_cell)

            # Col 7: Aksi Buttons
            act_widget = QWidget()
            act_lay = QHBoxLayout(act_widget)
            act_lay.setContentsMargins(3, 2, 3, 2)
            act_lay.setSpacing(4)

            btn_detail = TableDetailButton("Detail")
            btn_detail.setFixedHeight(24)
            btn_detail.setToolTip("Lihat rincian lengkap material terpakai, HPP, dan Margin Laba")
            btn_detail.clicked.connect(lambda _, row_data=r: self.show_detail(row_data))

            btn_cetak = QPushButton("Cetak SJ")
            btn_cetak.setCursor(Qt.PointingHandCursor)
            btn_cetak.setFixedHeight(24)
            btn_cetak.setStyleSheet("""
                QPushButton {
                    background-color: #F0FDF4;
                    color: #16A34A;
                    border: 1px solid #86EFAC;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 11px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #DCFCE7;
                    color: #15803D;
                    border-color: #4ADE80;
                }
            """)
            btn_cetak.setToolTip("Buka & Cetak Dokumen Surat Jalan di Google Chrome")
            btn_cetak.clicked.connect(lambda _, row_data=r: self.lihat_surat_jalan(row_data["id"]))

            btn_invoice = QPushButton("Invoice")
            btn_invoice.setCursor(Qt.PointingHandCursor)
            btn_invoice.setFixedHeight(24)
            btn_invoice.setStyleSheet("""
                QPushButton {
                    background-color: #F5F3FF;
                    color: #4F46E5;
                    border: 1px solid #C7D2FE;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 11px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #EEF2FF;
                    color: #3730A3;
                    border-color: #A5B4FC;
                }
            """)
            btn_invoice.setToolTip("Buka & Cetak Dokumen Invoice di Google Chrome")
            btn_invoice.clicked.connect(lambda _, row_data=r: self.lihat_invoice(row_data["id"]))

            btn_del = TableDeleteButton("Hapus")
            btn_del.setFixedHeight(24)
            btn_del.setToolTip("Batalkan / Hapus data pengiriman ini")
            btn_del.clicked.connect(lambda _, row_data=r: self.hapus_pengiriman(row_data))

            act_lay.addWidget(btn_detail)
            act_lay.addWidget(btn_cetak)
            act_lay.addWidget(btn_invoice)
            act_lay.addWidget(btn_del)
            self.table_riwayat.setCellWidget(r_idx, 7, act_widget)

    def reset_filter_riwayat(self):
        self.cb_filter_proyek.setCurrentIndex(0)
        self.cb_filter_mutu.setCurrentIndex(0)
        if hasattr(self, "cb_filter_bbm"):
            self.cb_filter_bbm.setCurrentIndex(0)
        self.txt_f_search.clear()
        self.dt_f_start.setDate(QDate.currentDate().addMonths(-3))
        self.dt_f_end.setDate(QDate.currentDate())
        self.load_riwayat()

    def buka_catat_bbm_cepat(self, row_data: dict):
        dlg = QuickCatatBBMDialog(row_data, parent=self)
        if dlg.exec():
            self.load_riwayat()
            self.data_changed.emit()

    def show_detail(self, row_data):
        dlg = DetailPengirimanDialog(row_data, parent=self)
        dlg.exec()

    def hapus_pengiriman(self, row_data):
        msg = (
            f"Apakah Anda yakin ingin membatalkan/menghapus pengiriman ini:\n\n"
            f"No Surat Jalan: {row_data['no_surat_jalan']}\n"
            f"Proyek: {row_data['proyek_nama']}\n"
            f"Volume: {styles.format_number(row_data['volume_m3'], 2)} m³\n"
            f"Total Tagihan: {styles.format_rupiah(row_data.get('total_pendapatan') or 0)}\n\n"
            f"Stok material fisik akan DIKEMBALIKAN ke gudang dan tagihan piutang proyek di Modul Keuangan akan DIHAPUS."
        )
        if confirm_dialog(self, "Konfirmasi Pembatalan Pengiriman", msg):
            ok, res_msg = database.hapus_pengiriman(row_data["id"], user_id=self.current_user_id)
            if ok:
                QMessageBox.information(self, "Sukses", res_msg)
                self.load_riwayat()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Gagal", res_msg)

    def refresh_all(self):
        self.mutu_list = database.get_all_mutu_beton()
        self.proyek_list = database.get_all_proyek(only_active=True)
        all_proyeks = database.get_all_proyek()

        cur_mutu = self.cb_mutu.currentData()
        self.cb_mutu.blockSignals(True)
        self.cb_mutu.clear()
        for m in self.mutu_list:
            self.cb_mutu.addItem(f"{m['kode']} ({m['nama'] or '-'})", m["id"])
        if cur_mutu:
            idx = self.cb_mutu.findData(cur_mutu)
            if idx >= 0: self.cb_mutu.setCurrentIndex(idx)
        self.cb_mutu.blockSignals(False)

        cur_pr = self.cb_proyek.currentData()
        cur_text = self.cb_proyek.currentText()
        self.cb_proyek.clear()
        for p in self.proyek_list:
            self.cb_proyek.addItem(f"{p['nama']} ({p['lokasi'] or '-'})", p["id"])
        if cur_pr:
            idx = self.cb_proyek.findData(cur_pr)
            if idx >= 0: 
                self.cb_proyek.setCurrentIndex(idx)
            elif cur_text:
                self.cb_proyek.setEditText(cur_text)
        elif cur_text:
            self.cb_proyek.setEditText(cur_text)

        self.cb_filter_proyek.clear()
        self.cb_filter_proyek.addItem("Semua Proyek", -1)
        for p in all_proyeks:
            self.cb_filter_proyek.addItem(p["nama"], p["id"])

        self.cb_filter_mutu.clear()
        self.cb_filter_mutu.addItem("Semua Mutu", -1)
        for m in self.mutu_list:
            self.cb_filter_mutu.addItem(m["kode"], m["id"])

        # Update dropdown armada kendaraan mixer
        try:
            kendaraan_list = database.get_all_kendaraan()
            cur_plat = self.get_plat_truk()
            if hasattr(self, "cb_plat_truk"):
                self.cb_plat_truk.blockSignals(True)
                self.cb_plat_truk.clear()
                for k in kendaraan_list:
                    np = k.get("no_plat") or ""
                    nm = k.get("nama_kendaraan") or ""
                    st = str(k.get("status") or "tersedia").lower()
                    label = f"{np} - {nm}" if nm else np
                    if st == "operasional":
                        label += "  [SEDANG DIGUNAKAN]"
                    elif st == "maintenance":
                        label += "  [SEDANG SERVIS]"
                    elif st == "nonaktif":
                        label += "  [NONAKTIF]"
                    self.cb_plat_truk.addItem(label, np)
                if cur_plat:
                    idx = self.cb_plat_truk.findData(cur_plat)
                    if idx >= 0:
                        self.cb_plat_truk.setCurrentIndex(idx)
                    elif self.cb_plat_truk.lineEdit():
                        self.cb_plat_truk.lineEdit().setText(cur_plat)
                self.cb_plat_truk.blockSignals(False)
        except Exception:
            pass

        self.on_mutu_selected()
        self.on_kendaraan_selected()
        self.load_riwayat()

    # ------------------------------------------
    # LIHAT / CETAK SURAT JALAN PDF (CHROME)
    # ------------------------------------------
    def lihat_surat_jalan(self, pengiriman_id: int):
        """Mencetak Surat Jalan ke file PDF dan membukanya langsung di Google Chrome untuk dilihat dan diunduh."""
        import os
        import re
        import tempfile
        import subprocess
        import webbrowser
        from datetime import datetime as dt

        # Dapatkan no_surat_jalan untuk nama file yang rapi jika ada
        no_sj = ""
        try:
            riwayat = database.get_riwayat_pengiriman()
            p_data = next((x for x in riwayat if x["id"] == pengiriman_id), None)
            if p_data and p_data.get("no_surat_jalan"):
                no_sj = re.sub(r'[\\/*?:"<>| ]', '_', str(p_data["no_surat_jalan"]))
        except Exception:
            pass

        base_name = f"Surat_Jalan_{no_sj}" if no_sj else f"Surat_Jalan_{pengiriman_id}"
        temp_dir = os.path.join(tempfile.gettempdir(), "akp_surat_jalan")
        os.makedirs(temp_dir, exist_ok=True)

        filepath = os.path.join(temp_dir, f"{base_name}.pdf")
        # Jika file sedang dibuka/dikunci oleh browser, gunakan nama ber-timestamp
        try:
            if os.path.exists(filepath):
                with open(filepath, "a"):
                    pass
        except (PermissionError, OSError):
            filepath = os.path.join(temp_dir, f"{base_name}_{dt.now().strftime('%H%M%S')}.pdf")

        ok, result = export_service.cetak_surat_jalan_pdf(filepath, pengiriman_id)

        if ok:
            opened, msg = export_service.open_pdf_document(filepath)
            if not opened:
                QMessageBox.warning(self, "Peringatan", f"PDF berhasil dibuat tetapi gagal dibuka secara otomatis: {msg}")
        else:
            QMessageBox.critical(
                self,
                "Gagal Menampilkan Surat Jalan",
                f"❌ {result}"
            )

    # Alias untuk kompatibilitas
    cetak_surat_jalan = lihat_surat_jalan

    # ------------------------------------------
    # LIHAT / CETAK INVOICE PDF (CHROME)
    # ------------------------------------------
    def lihat_invoice(self, pengiriman_id: int):
        """Mencetak Invoice ke file PDF dan membukanya langsung di Google Chrome untuk dilihat dan dicetak."""
        import os
        import re
        import tempfile
        from datetime import datetime as dt

        no_sj = ""
        try:
            riwayat = database.get_riwayat_pengiriman()
            p_data = next((x for x in riwayat if x["id"] == pengiriman_id), None)
            if p_data and p_data.get("no_surat_jalan"):
                no_sj = re.sub(r'[\\/*?:"<>| ]', '_', str(p_data["no_surat_jalan"]))
        except Exception:
            pass

        base_name = f"Invoice_{no_sj}" if no_sj else f"Invoice_{pengiriman_id}"
        temp_dir = os.path.join(tempfile.gettempdir(), "akp_invoice")
        os.makedirs(temp_dir, exist_ok=True)

        filepath = os.path.join(temp_dir, f"{base_name}.pdf")
        try:
            if os.path.exists(filepath):
                with open(filepath, "a"):
                    pass
        except (PermissionError, OSError):
            filepath = os.path.join(temp_dir, f"{base_name}_{dt.now().strftime('%H%M%S')}.pdf")

        ok, result = export_service.cetak_invoice_pdf(filepath, pengiriman_id)

        if ok:
            opened, msg = export_service.open_pdf_document(filepath)
            if not opened:
                QMessageBox.warning(self, "Peringatan", f"PDF Invoice berhasil dibuat tetapi gagal dibuka secara otomatis: {msg}")
        else:
            QMessageBox.critical(
                self,
                "Gagal Menampilkan Invoice",
                f"❌ {result}"
            )

    cetak_invoice = lihat_invoice

    # ------------------------------------------
    # PROMPT PILIHAN CETAK PASCA SIMPAN
    # ------------------------------------------
    def prompt_cetak_dokumen(self, pengiriman_id: int, info_msg: str):
        """Dialog interaktif untuk memilih cetak Invoice, Surat Jalan, atau Keduanya setelah simpan."""
        dlg = ModernDialog("Pengiriman Berhasil Disimpan", self, min_width=490)

        lbl_icon = QLabel("📋")
        lbl_icon.setStyleSheet("font-size: 36px;")
        lbl_icon.setAlignment(Qt.AlignCenter)

        lbl_title = QLabel("TRANSAKSI PENGIRIMAN BERHASIL TERCATAT")
        lbl_title.setStyleSheet("font-weight: 800; font-size: 14px; color: #0F172A;")
        lbl_title.setAlignment(Qt.AlignCenter)

        lbl_desc = QLabel(
            f"ID Transaksi: #{pengiriman_id}\n\n"
            f"{info_msg}\n\n"
            "Silakan pilih dokumen faktur/tiket yang ingin Anda buka langsung di Google Chrome:"
        )
        lbl_desc.setStyleSheet("font-size: 12px; color: #334155; line-height: 1.4;")
        lbl_desc.setAlignment(Qt.AlignCenter)
        lbl_desc.setWordWrap(True)

        dlg.content_layout.addWidget(lbl_icon)
        dlg.content_layout.addWidget(lbl_title)
        dlg.content_layout.addWidget(lbl_desc)

        btn_box = QVBoxLayout()
        btn_box.setSpacing(8)

        btn_inv = PrimaryButton("📄 Buka & Cetak INVOICE (PDF)")
        btn_inv.setFixedHeight(38)
        btn_inv.setStyleSheet(btn_inv.styleSheet() + "font-size: 12.5px; font-weight: 700;")

        btn_sj = SuccessButton("📋 Buka & Cetak SURAT JALAN (PDF)")
        btn_sj.setFixedHeight(38)
        btn_sj.setStyleSheet(btn_sj.styleSheet() + "font-size: 12.5px; font-weight: 700;")

        btn_both = SecondaryButton("🖨️ Buka KEDUA DOKUMEN Sekaligus (Invoice + SJ)")
        btn_both.setFixedHeight(36)

        def on_open_invoice():
            dlg.accept()
            self.lihat_invoice(pengiriman_id)

        def on_open_sj():
            dlg.accept()
            self.lihat_surat_jalan(pengiriman_id)

        def on_open_both():
            dlg.accept()
            self.lihat_invoice(pengiriman_id)
            self.lihat_surat_jalan(pengiriman_id)

        btn_inv.clicked.connect(on_open_invoice)
        btn_sj.clicked.connect(on_open_sj)
        btn_both.clicked.connect(on_open_both)

        btn_box.addWidget(btn_inv)
        btn_box.addWidget(btn_sj)
        btn_box.addWidget(btn_both)

        dlg.content_layout.addLayout(btn_box)

        dlg.btn_save.setVisible(False)
        dlg.btn_cancel.setText("Selesai (Tutup)")
        dlg.exec()

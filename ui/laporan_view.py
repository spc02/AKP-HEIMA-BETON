"""
AKP Beton Management System - Laporan View
Pusat generate & ekspor laporan bisnis resmi ke format Microsoft Excel (.xlsx) dan Dokumen PDF (.pdf),
dilengkapi ringkasan struktur laporan dan pengaturan Kop Surat Perusahaan.
"""

import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QFrame, QPushButton, QComboBox, QDateEdit, QLineEdit,
    QMessageBox, QFileDialog, QScrollArea, QListView
)
from PySide6.QtCore import Qt, QDate
from components import (
    PrimaryButton, SecondaryButton, SuccessButton
)
import styles
import database
import export_service

class LaporanView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.proyek_list = []
        self.init_ui()

    def init_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background-color: transparent;")

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(16, 14, 16, 16)
        main_layout.setSpacing(14)

        # 1. Card Utama: Filter & Generate Ekspor Laporan
        export_frame = QFrame()
        export_frame.setProperty("class", "CardWidget")
        export_layout = QVBoxLayout(export_frame)
        export_layout.setContentsMargins(18, 16, 18, 18)
        export_layout.setSpacing(14)

        lbl_exp_title = QLabel("GENERATE & EKSPOR LAPORAN PERUSAHAAN")
        lbl_exp_title.setStyleSheet(f"font-weight: 800; color: {styles.COLOR_PRIMARY_DARK}; font-size: 13.5px; letter-spacing: 0.5px;")
        export_layout.addWidget(lbl_exp_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)

        # Pilihan Jenis Laporan
        grid.addWidget(QLabel("Jenis Laporan:*"), 0, 0)
        self.cb_jenis_lap = QComboBox()
        self.cb_jenis_lap.setView(QListView())
        self.cb_jenis_lap.addItem("1. Laporan Rekapitulasi Pengiriman & Penjualan Beton Cor", "pengiriman")
        self.cb_jenis_lap.addItem("2. Laporan Kartu Kontrol & Sisa Stok Material (Valuasi)", "stok")
        self.cb_jenis_lap.addItem("3. Laporan Keuangan Plant (Buku Kas, Hutang Semen, Piutang, Kas Kantor & Gaji)", "keuangan")
        self.cb_jenis_lap.addItem("4. Laporan Biaya & Operasional Kendaraan", "kendaraan")
        self.cb_jenis_lap.currentIndexChanged.connect(self.on_jenis_laporan_changed)
        grid.addWidget(self.cb_jenis_lap, 0, 1, 1, 3)

        # Filter Proyek
        self.lbl_filter_pr = QLabel("Filter Proyek:")
        grid.addWidget(self.lbl_filter_pr, 1, 0)
        self.cb_filter_pr = QComboBox()
        self.cb_filter_pr.setView(QListView())
        grid.addWidget(self.cb_filter_pr, 1, 1, 1, 3)

        # Rentang Tanggal
        self.lbl_dt_start = QLabel("Mulai Tanggal:")
        grid.addWidget(self.lbl_dt_start, 2, 0)
        self.dt_start = QDateEdit()
        self.dt_start.setCalendarPopup(True)
        self.dt_start.setDate(QDate.currentDate().addMonths(-1))
        self.dt_start.setDisplayFormat("yyyy-MM-dd")
        grid.addWidget(self.dt_start, 2, 1)

        self.lbl_dt_end = QLabel("Sampai Tanggal:")
        grid.addWidget(self.lbl_dt_end, 2, 2)
        self.dt_end = QDateEdit()
        self.dt_end.setCalendarPopup(True)
        self.dt_end.setDate(QDate.currentDate())
        self.dt_end.setDisplayFormat("yyyy-MM-dd")
        grid.addWidget(self.dt_end, 2, 3)

        export_layout.addLayout(grid)

        # Action Buttons: Export Excel & Export PDF
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        btn_excel = SuccessButton("Ekspor ke Microsoft Excel (.xlsx)")
        btn_excel.setFixedHeight(40)
        btn_excel.clicked.connect(self.export_excel)

        btn_pdf = PrimaryButton("Ekspor ke Dokumen PDF (.pdf)")
        btn_pdf.setFixedHeight(40)
        btn_pdf.clicked.connect(self.export_pdf)

        btn_layout.addWidget(btn_excel)
        btn_layout.addWidget(btn_pdf)
        btn_layout.addStretch()
        export_layout.addLayout(btn_layout)

        main_layout.addWidget(export_frame)

        # 2. Dua Kartu Sejajar: Ringkasan Format Laporan & Pengaturan Kop Laporan
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(14)

        # Kolom Kiri: Informasi & Cakupan Dokumen Laporan
        info_frame = QFrame()
        info_frame.setProperty("class", "CardWidget")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(18, 16, 18, 18)
        info_layout.setSpacing(12)

        lbl_info_title = QLabel("INFORMASI STRUKTUR & CAKUPAN LAPORAN")
        lbl_info_title.setStyleSheet(f"font-weight: 800; color: {styles.COLOR_PRIMARY_DARK}; font-size: 13px;")
        info_layout.addWidget(lbl_info_title)

        info_box = QFrame()
        info_box.setObjectName("infoBoxReport")
        info_box.setStyleSheet(f"""
            QFrame#infoBoxReport {{
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
            }}
        """)
        box_lay = QVBoxLayout(info_box)
        box_lay.setContentsMargins(14, 12, 14, 12)
        box_lay.setSpacing(10)

        item1 = QLabel(
            "<b>1. Rekapitulasi Pengiriman & Penjualan Beton Cor:</b><br>"
            "<span style='color: #64748B; font-size: 11.5px;'>"
            "Mencakup nomor surat jalan (SJ), tanggal cor, nama pelanggan, proyek, mutu beton (K/Fc), volume cor (m³), "
            "harga per m³, total nilai penjualan, serta status pembayaran (Lunas / Tempo / DP)."
            "</span>"
        )
        item1.setWordWrap(True)
        item1.setStyleSheet("border: none; background: transparent;")
        box_lay.addWidget(item1)

        item2 = QLabel(
            "<b>2. Kartu Kontrol & Sisa Stok Material (Valuasi):</b><br>"
            "<span style='color: #64748B; font-size: 11.5px;'>"
            "Mencakup seluruh daftar material produksi (semen, pasir, split, abu batu, solar, additive), total masuk, "
            "total pemakaian produksi otomatis, sisa stok saat ini, dan estimasi valuasi aset."
            "</span>"
        )
        item2.setWordWrap(True)
        item2.setStyleSheet("border: none; background: transparent;")
        box_lay.addWidget(item2)

        item3 = QLabel(
            "<b>3. Laporan Keuangan Plant (4 Pilar & Buku Kas):</b><br>"
            "<span style='color: #64748B; font-size: 11.5px;'>"
            "Mencakup ringkasan buku kas riil, tagihan hutang supplier semen, daftar piutang proyek, "
            "pengeluaran kas operasional kantor harian, serta beban penggajian karyawan."
            "</span>"
        )
        item3.setWordWrap(True)
        item3.setStyleSheet("border: none; background: transparent;")
        box_lay.addWidget(item3)

        item4 = QLabel(
            "<b>4. Laporan Biaya & Operasional Kendaraan:</b><br>"
            "<span style='color: #64748B; font-size: 11.5px;'>"
            "Mencakup rincian nota pengeluaran armada (BBM, servis, oli, supir), rekapitulasi efisiensi per kendaraan, "
            "dan frekuensi operasional mobil di lapangan."
            "</span>"
        )
        item4.setWordWrap(True)
        item4.setStyleSheet("border: none; background: transparent;")
        box_lay.addWidget(item4)

        info_layout.addWidget(info_box)
        info_layout.addStretch()
        bottom_layout.addWidget(info_frame, 1)

        # Kolom Kanan: Pengaturan Kop Surat Laporan (PDF / Excel)
        profile_frame = QFrame()
        profile_frame.setProperty("class", "CardWidget")
        profile_layout = QVBoxLayout(profile_frame)
        profile_layout.setContentsMargins(18, 16, 18, 18)
        profile_layout.setSpacing(10)

        lbl_pf_title = QLabel("KOP SURAT LAPORAN RESMI (KOP PDF / EXCEL)")
        lbl_pf_title.setStyleSheet(f"font-weight: 800; color: {styles.COLOR_PRIMARY_DARK}; font-size: 13px;")
        profile_layout.addWidget(lbl_pf_title)

        lbl_pf_desc = QLabel("Informasi ini otomatis dicetak di bagian kepala (header) dokumen PDF dan Excel:")
        lbl_pf_desc.setStyleSheet("color: #64748B; font-size: 11.5px;")
        lbl_pf_desc.setWordWrap(True)
        profile_layout.addWidget(lbl_pf_desc)

        p_grid = QGridLayout()
        p_grid.setHorizontalSpacing(10)
        p_grid.setVerticalSpacing(8)

        p_grid.addWidget(QLabel("Nama Perusahaan:"), 0, 0)
        self.txt_set_nama = QLineEdit()
        p_grid.addWidget(self.txt_set_nama, 0, 1)

        p_grid.addWidget(QLabel("Alamat Operasional:"), 1, 0)
        self.txt_set_alamat = QLineEdit()
        p_grid.addWidget(self.txt_set_alamat, 1, 1)

        p_grid.addWidget(QLabel("No. Telepon / Kontak:"), 2, 0)
        self.txt_set_telp = QLineEdit()
        p_grid.addWidget(self.txt_set_telp, 2, 1)

        p_grid.addWidget(QLabel("Penanggung Jawab:"), 3, 0)
        self.txt_set_pj = QLineEdit()
        p_grid.addWidget(self.txt_set_pj, 3, 1)

        profile_layout.addLayout(p_grid)

        btn_save_settings = SecondaryButton("Simpan Identitas Kop Laporan")
        btn_save_settings.setFixedHeight(38)
        btn_save_settings.clicked.connect(self.save_settings)
        profile_layout.addWidget(btn_save_settings)
        profile_layout.addStretch()

        bottom_layout.addWidget(profile_frame, 1)
        main_layout.addLayout(bottom_layout)

        scroll.setWidget(container)
        layout_outer = QVBoxLayout(self)
        layout_outer.setContentsMargins(0, 0, 0, 0)
        layout_outer.addWidget(scroll)

        self.refresh_all()

    def on_jenis_laporan_changed(self, idx: int):
        jenis = self.cb_jenis_lap.currentData()
        # Filter proyek relevan untuk laporan pengiriman dan operasional kendaraan
        has_proyek = (jenis in ["pengiriman", "kendaraan"])
        self.lbl_filter_pr.setEnabled(has_proyek)
        self.cb_filter_pr.setEnabled(has_proyek)

    def export_excel(self):
        jenis = self.cb_jenis_lap.currentData()
        pr_id = self.cb_filter_pr.currentData()
        start_d = self.dt_start.date().toString("yyyy-MM-dd")
        end_d = self.dt_end.date().toString("yyyy-MM-dd")
        
        proyek_id = pr_id if (pr_id != -1 and jenis in ["pengiriman", "kendaraan"]) else None
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"Laporan_{jenis}_{now_str}.xlsx"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Simpan File Excel", default_name, "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            if jenis == "pengiriman":
                export_service.export_pengiriman_excel(file_path, start_d, end_d, proyek_id)
            elif jenis == "stok":
                export_service.export_stok_excel(file_path)
            elif jenis == "keuangan":
                export_service.export_keuangan_excel(file_path, start_d, end_d)
            elif jenis == "kendaraan":
                export_service.export_operasional_kendaraan_excel(file_path, start_date=start_d, end_date=end_d, proyek_id=proyek_id)

            # Langsung buka file Excel secara otomatis
            export_service.open_excel_document(file_path)
            QMessageBox.information(self, "Berhasil", f"Laporan Excel berhasil disimpan dan langsung dibuka:\n\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Gagal Ekspor", f"Terjadi kesalahan saat ekspor Excel: {str(e)}")

    def export_pdf(self):
        jenis = self.cb_jenis_lap.currentData()
        pr_id = self.cb_filter_pr.currentData()
        start_d = self.dt_start.date().toString("yyyy-MM-dd")
        end_d = self.dt_end.date().toString("yyyy-MM-dd")
        
        proyek_id = pr_id if (pr_id != -1 and jenis in ["pengiriman", "kendaraan"]) else None
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"Laporan_{jenis}_{now_str}.pdf"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Simpan File PDF", default_name, "PDF Files (*.pdf)"
        )
        if not file_path:
            return

        try:
            if jenis == "pengiriman":
                export_service.export_pengiriman_pdf(file_path, start_d, end_d, proyek_id)
            elif jenis == "stok":
                export_service.export_stok_pdf(file_path)
            elif jenis == "keuangan":
                export_service.export_keuangan_pdf(file_path, start_d, end_d)
            elif jenis == "kendaraan":
                export_service.export_operasional_kendaraan_pdf(file_path, start_date=start_d, end_date=end_d, proyek_id=proyek_id)

            # Langsung buka file PDF di Chrome / default viewer secara otomatis
            export_service.open_pdf_document(file_path)
            QMessageBox.information(self, "Berhasil", f"Laporan PDF berhasil disimpan dan langsung dibuka di Chrome:\n\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Gagal Ekspor", f"Terjadi kesalahan saat ekspor PDF: {str(e)}")

    def save_settings(self):
        database.save_setting("nama_perusahaan", self.txt_set_nama.text().strip())
        database.save_setting("alamat_perusahaan", self.txt_set_alamat.text().strip())
        database.save_setting("telepon_perusahaan", self.txt_set_telp.text().strip())
        database.save_setting("pj_lapangan", self.txt_set_pj.text().strip())
        QMessageBox.information(self, "Disimpan", "Pengaturan identitas kop laporan berhasil disimpan.")

    def refresh_all(self):
        all_p = database.get_all_proyek()
        curr_p = self.cb_filter_pr.currentData()
        self.cb_filter_pr.clear()
        self.cb_filter_pr.addItem("Semua Proyek", -1)
        for p in all_p:
            self.cb_filter_pr.addItem(p["nama"], p["id"])
        if curr_p:
            idx = self.cb_filter_pr.findData(curr_p)
            if idx >= 0: self.cb_filter_pr.setCurrentIndex(idx)

        settings = database.get_settings()
        self.txt_set_nama.setText(settings.get("nama_perusahaan", "AKP BATCHING PLANT"))
        self.txt_set_alamat.setText(settings.get("alamat_perusahaan", "Jl. Raya Magelang - Secang KM 7, Jawa Tengah"))
        self.txt_set_telp.setText(settings.get("telepon_perusahaan", "0812-3456-7890 / (0293) 362819"))
        self.txt_set_pj.setText(settings.get("pj_lapangan", "Ir. H. Sudirman (Plant Manager)"))

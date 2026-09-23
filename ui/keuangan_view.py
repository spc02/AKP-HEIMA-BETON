"""
Keuangan View untuk AKP Beton Desktop Application
Sistem Keuangan Terpadu 4 Pilar (Hutang Semen, Piutang Proyek, Kas Kantor, Gaji Karyawan)
dan Buku Kas Umum dengan Saldo Otomatis Anti-Selisih (Single Source of Truth).
"""

import os
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, 
    QLabel, QFrame, QTableWidgetItem, QMessageBox, QDialog,
    QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit, QDateEdit,
    QGridLayout, QHeaderView, QListView, QFileDialog, QStackedWidget, QButtonGroup
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QFont
from components import (
    StatCard, ModernTableWidget, SectionHeader, ModernDialog, confirm_dialog, BadgeLabel,
    PrimaryButton, SecondaryButton, SuccessButton, DangerButton,
    TableEditButton, TableDeleteButton, TableDetailButton, TablePayButton
)
import styles
import database
from ui.kendaraan_view import KendaraanView

# ==============================================================================
# 1. DIALOG INPUT MODAL AWAL / KAS KHUSUS
# ==============================================================================
class ModalKasDialog(ModernDialog):
    def __init__(self, parent=None):
        super().__init__("Catat Modal Awal / Penerimaan Kas Khusus", parent, min_width=460)
        self.init_form()

    def init_form(self):
        grid = QGridLayout()
        grid.setSpacing(12)

        grid.addWidget(QLabel("Tanggal Transaksi:*"), 0, 0)
        self.dt_tgl = QDateEdit()
        self.dt_tgl.setCalendarPopup(True)
        self.dt_tgl.setDate(QDate.currentDate())
        self.dt_tgl.setDisplayFormat("yyyy-MM-dd")
        grid.addWidget(self.dt_tgl, 0, 1)

        grid.addWidget(QLabel("Kategori Kas:*"), 1, 0)
        self.cb_kat = QComboBox()
        self.cb_kat.setView(QListView())
        self.cb_kat.addItems(["Modal Awal", "Kas Masuk Lain", "Setoran Pemilik / Investor"])
        grid.addWidget(self.cb_kat, 1, 1)

        grid.addWidget(QLabel("Nominal (Rp):*"), 2, 0)
        self.spin_nominal = QDoubleSpinBox()
        self.spin_nominal.setRange(1000, 100000000000.0)
        self.spin_nominal.setDecimals(0)
        self.spin_nominal.setSingleStep(1000000)
        self.spin_nominal.setValue(10000000)
        grid.addWidget(self.spin_nominal, 2, 1)

        grid.addWidget(QLabel("Keterangan:*"), 3, 0)
        self.txt_ket = QTextEdit()
        self.txt_ket.setPlaceholderText("Uraian setoran modal / sumber dana masuk")
        self.txt_ket.setMaximumHeight(70)
        grid.addWidget(self.txt_ket, 3, 1)

        self.content_layout.addLayout(grid)
        self.btn_save.clicked.connect(self.save)

    def save(self):
        tgl = self.dt_tgl.date().toString("yyyy-MM-dd")
        kat = self.cb_kat.currentText().strip()
        nominal = self.spin_nominal.value()
        ket = self.txt_ket.toPlainText().strip()

        if nominal <= 0:
            QMessageBox.warning(self, "Peringatan", "Nominal transaksi harus lebih dari Rp 0!")
            return
        if not ket:
            QMessageBox.warning(self, "Peringatan", "Keterangan transaksi wajib diisi!")
            return

        try:
            database.catat_kas_manual(tgl, ket, masuk=nominal, keluar=0.0, kategori=kat)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", f"Gagal menyimpan transaksi modal kas: {str(e)}")


# ==============================================================================
# 2. DIALOG PEMBAYARAN / CICILAN SEMEN
# ==============================================================================
class CicilanSemenDialog(ModernDialog):
    def __init__(self, parent=None, target_order: dict = None):
        title = "Catat Pembayaran / Cicilan Piutang Material"
        if target_order:
            no_do = target_order.get("no_order") or f"ID #{target_order.get('id')}"
            title = f"Catat Pembayaran Piutang Material - {no_do}"
        super().__init__(title, parent, min_width=500)
        self.target_order = target_order
        self.order_list = database.get_pembayaran_semen_list()
        self.init_form()

    def init_form(self):
        grid = QGridLayout()
        grid.setSpacing(12)

        row_offset = 0
        if not self.target_order:
            grid.addWidget(QLabel("Pilih Faktur / DO Material:"), 0, 0)
            self.cb_order = QComboBox()
            self.cb_order.setView(QListView())
            self.cb_order.addItem("Pembayaran Umum / Tanpa Alokasi Faktur Tertentu", None)
            
            pending_count = 0
            for o in self.order_list:
                sisa = o['sisa_hutang']
                if sisa > 0:
                    pending_count += 1
                    lbl = f"DO #{o['id']} ({o['tanggal_order']}) - {o['no_order'] or 'DO'} - Sisa Hutang: {styles.format_rupiah(sisa)}"
                    self.cb_order.addItem(lbl, o["id"])
                else:
                    lbl = f"DO #{o['id']} ({o['tanggal_order']}) - {o['no_order'] or 'DO'} [LUNAS]"
                    self.cb_order.addItem(lbl, o["id"])

            self.cb_order.currentIndexChanged.connect(self.on_order_selected)
            grid.addWidget(self.cb_order, 0, 1)
            row_offset = 1

        # 1. Tanggal Pembayaran
        grid.addWidget(QLabel("Tanggal Pembayaran:*"), row_offset + 0, 0)
        self.dt_tgl = QDateEdit()
        self.dt_tgl.setCalendarPopup(True)
        self.dt_tgl.setDate(QDate.currentDate())
        self.dt_tgl.setDisplayFormat("yyyy-MM-dd")
        grid.addWidget(self.dt_tgl, row_offset + 0, 1)

        # 2. Nominal Bayar
        grid.addWidget(QLabel("Nominal Bayar (Rp):*"), row_offset + 1, 0)
        self.spin_nominal = QDoubleSpinBox()
        self.spin_nominal.setRange(1, 100000000000.0)
        self.spin_nominal.setDecimals(0)
        self.spin_nominal.setSingleStep(1000000)

        if self.target_order:
            sisa_nominal = float(self.target_order.get("sisa_hutang") or 0)
            self.spin_nominal.setValue(sisa_nominal if sisa_nominal > 0 else 0)

        grid.addWidget(self.spin_nominal, row_offset + 1, 1)

        # 3. Metode Bayar
        grid.addWidget(QLabel("Metode Bayar:"), row_offset + 2, 0)
        self.cb_metode = QComboBox()
        self.cb_metode.setView(QListView())
        self.cb_metode.addItems(["Transfer Mandiri", "Transfer BCA", "Transfer BRI", "Transfer BNI", "Tunai / Cash", "Giro / Cek"])
        grid.addWidget(self.cb_metode, row_offset + 2, 1)

        # 4. Keterangan / Bukti
        grid.addWidget(QLabel("Keterangan / Bukti:"), row_offset + 3, 0)
        self.txt_ket = QLineEdit()
        self.txt_ket.setPlaceholderText("No. referensi transfer, nama rekening supplier, dll")
        grid.addWidget(self.txt_ket, row_offset + 3, 1)

        # Info otomatis potong kas
        lbl_info = QLabel("Catatan: Pembayaran hutang semen ini akan otomatis mengurangi Saldo Kas Plant.")
        lbl_info.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px; font-style: italic;")
        grid.addWidget(lbl_info, row_offset + 4, 0, 1, 2)

        self.content_layout.addLayout(grid)
        self.btn_save.clicked.connect(self.save)

        if not self.target_order and pending_count > 0:
            self.cb_order.setCurrentIndex(1)
            self.on_order_selected()

    def on_order_selected(self):
        if hasattr(self, "cb_order"):
            order_id = self.cb_order.currentData()
            if order_id:
                target = next((o for o in self.order_list if o["id"] == order_id), None)
                if target and target["sisa_hutang"] > 0:
                    self.spin_nominal.setValue(target["sisa_hutang"])

    def save(self):
        if self.target_order:
            order_id = self.target_order.get("id")
        else:
            order_id = self.cb_order.currentData()

        tgl = self.dt_tgl.date().toString("yyyy-MM-dd")
        nominal = self.spin_nominal.value()
        metode = self.cb_metode.currentText()
        ket = self.txt_ket.text().strip()

        if nominal <= 0:
            QMessageBox.warning(self, "Peringatan", "Nominal pembayaran harus lebih dari Rp 0!")
            return

        try:
            database.catat_cicilan_semen(order_id, tgl, nominal, metode, ket)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", f"Gagal menyimpan pembayaran semen: {str(e)}")


# ==============================================================================
# 2B. WIDGET BADGE JATUH TEMPO & HITUNGAN MUNDUR (COUNTDOWN)
# ==============================================================================
class JatuhTempoBadgeWidget(QWidget):
    """Widget khusus untuk menampilkan Tanggal Jatuh Tempo beserta badge Countdown berwarna cerdas"""
    def __init__(self, tgl_str: str, delta_days: int, is_lunas: bool, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)

        # 1. Tanggal Text
        lbl_date = QLabel(tgl_str)
        lbl_date.setAlignment(Qt.AlignCenter)
        lbl_date.setStyleSheet("font-weight: 700; font-size: 11px; color: #1E293B;")
        layout.addWidget(lbl_date)

        # 2. Countdown Badge with Dynamic Color
        lbl_badge = QLabel()
        lbl_badge.setAlignment(Qt.AlignCenter)
        
        if is_lunas:
            lbl_badge.setText("✅ Lunas")
            lbl_badge.setStyleSheet("""
                background-color: #ECFDF5;
                color: #059669;
                border: 1px solid #A7F3D0;
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 10px;
                font-weight: 700;
            """)
        elif delta_days < 0:
            lbl_badge.setText(f"⚠️ Lewat {abs(delta_days)} Hari")
            lbl_badge.setStyleSheet("""
                background-color: #FEF2F2;
                color: #DC2626;
                border: 1px solid #FCA5A5;
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 10px;
                font-weight: 800;
            """)
        elif delta_days == 0:
            lbl_badge.setText("🔥 Hari Ini!")
            lbl_badge.setStyleSheet("""
                background-color: #FEF2F2;
                color: #B91C1C;
                border: 1px solid #EF4444;
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 10px;
                font-weight: 800;
            """)
        elif delta_days <= 3:
            lbl_badge.setText(f"⏳ Sisa {delta_days} Hari")
            lbl_badge.setStyleSheet("""
                background-color: #FFF7ED;
                color: #EA580C;
                border: 1px solid #FDBA74;
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 10px;
                font-weight: 700;
            """)
        elif delta_days <= 7:
            lbl_badge.setText(f"⏱️ Sisa {delta_days} Hari")
            lbl_badge.setStyleSheet("""
                background-color: #FEFCE8;
                color: #D97706;
                border: 1px solid #FDE047;
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 10px;
                font-weight: 700;
            """)
        else:
            lbl_badge.setText(f"📅 Sisa {delta_days} Hari")
            lbl_badge.setStyleSheet("""
                background-color: #EFF6FF;
                color: #2563EB;
                border: 1px solid #BFDBFE;
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 10px;
                font-weight: 600;
            """)

        layout.addWidget(lbl_badge)


# ==============================================================================
# 2B. DIALOG DETAIL FAKTUR / DO MATERIAL SUPPLIER
# ==============================================================================
class DetailMaterialDODialog(ModernDialog):
    """Dialog rincian lengkap DO / Faktur Material beserta riwayat cicilan kas"""
    def __init__(self, order_data: dict, parent=None):
        no_order = order_data.get("no_order") or f"ID #{order_data.get('id')}"
        super().__init__(f"Rincian DO / Faktur: {no_order}", parent, min_width=680)
        self.order_data = order_data
        self.parent_view = parent
        self.init_details()

    def init_details(self):
        o = self.order_data

        # 1. Header Card: Status, Kategori & Sisa Tagihan
        sisa = float(o.get("sisa_hutang") or 0)
        is_lunas = sisa <= 0

        top_card = QFrame()
        top_card.setStyleSheet(f"""
            QFrame {{
                background-color: {styles.COLOR_BG_APP};
                border: 1.5px solid {styles.COLOR_BORDER};
                border-radius: 8px;
            }}
        """)
        top_lay = QHBoxLayout(top_card)
        top_lay.setContentsMargins(14, 10, 14, 10)

        badge_status = BadgeLabel("LUNAS" if is_lunas else "BELUM LUNAS", "success" if is_lunas else "danger")
        kat_val = str(o.get("kategori_piutang") or "kantor").lower()
        badge_kat = BadgeLabel("🏭 Piutang Perusahaan" if kat_val == "perusahaan" else "🏢 Piutang Kantor", 
                               "warning" if kat_val == "perusahaan" else "primary")

        top_lay.addWidget(QLabel("<b>Status:</b>"))
        top_lay.addWidget(badge_status)
        top_lay.addSpacing(12)
        top_lay.addWidget(QLabel("<b>Kategori:</b>"))
        top_lay.addWidget(badge_kat)
        top_lay.addStretch()

        sisa_color = "#059669" if is_lunas else "#DC2626"
        lbl_sisa = QLabel(f"Sisa Tagihan: <span style='color: {sisa_color}; font-size: 15px; font-weight: 800;'>{styles.format_rupiah(sisa)}</span>")
        top_lay.addWidget(lbl_sisa)

        self.content_layout.addWidget(top_card)
        self.content_layout.addSpacing(4)

        # 2. Grid Rincian DO & Material
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)

        # Baris 0: No DO & Supplier
        grid.addWidget(QLabel("No. DO / Faktur:"), 0, 0)
        grid.addWidget(QLabel(f"<b>{o.get('no_order') or '-'}</b>"), 0, 1)
        grid.addWidget(QLabel("Supplier / Asal:"), 0, 2)
        lbl_supp = QLabel(f"<b>{o.get('supplier') or '-'}</b>")
        lbl_supp.setWordWrap(True)
        grid.addWidget(lbl_supp, 0, 3)

        # Baris 1: Material & Satuan
        mat_nama = o.get("material_nama") or o.get("material_kode") or "Semen"
        satuan = o.get("material_satuan") or "Ton"
        grid.addWidget(QLabel("Material:"), 1, 0)
        grid.addWidget(QLabel(f"<b>{mat_nama}</b>"), 1, 1)
        grid.addWidget(QLabel("Volume / Qty:"), 1, 2)
        grid.addWidget(QLabel(f"<b>{styles.format_number(o.get('jumlah_ton') or 0, 2)} {satuan}</b>"), 1, 3)

        # Baris 2: Tanggal Datang & Jatuh Tempo
        tgl_dtg_raw = o.get("tanggal_datang")
        if tgl_dtg_raw and str(tgl_dtg_raw).strip() not in ("-", "None", ""):
            tgl_dtg = f"Sudah Datang ({fmt_tgl(tgl_dtg_raw)})"
        else:
            tgl_dtg = "Belum Datang"
        jt_str = str(o.get("jatuh_tempo") or "-")
        grid.addWidget(QLabel("Tanggal Datang / DO:"), 2, 0)
        grid.addWidget(QLabel(f"<b>{tgl_dtg}</b>"), 2, 1)
        grid.addWidget(QLabel("Jatuh Tempo:"), 2, 2)
        grid.addWidget(QLabel(f"<b>{jt_str}</b>"), 2, 3)

        # Baris 3: Harga Satuan & Total Tagihan
        grid.addWidget(QLabel("Harga Satuan:"), 3, 0)
        grid.addWidget(QLabel(f"<b>{styles.format_rupiah(o.get('harga_per_ton') or 0)}</b> / {satuan}"), 3, 1)
        grid.addWidget(QLabel("Total Tagihan:"), 3, 2)
        grid.addWidget(QLabel(f"<b style='font-size: 13px; color: {styles.COLOR_PRIMARY_DARK};'>{styles.format_rupiah(o.get('total_harga') or 0)}</b>"), 3, 3)

        # Baris 4: Sudah Dibayar & Catatan
        grid.addWidget(QLabel("Sudah Dibayar:"), 4, 0)
        grid.addWidget(QLabel(f"<b style='color: #059669;'>{styles.format_rupiah(o.get('total_dibayar') or 0)}</b>"), 4, 1)
        grid.addWidget(QLabel("Catatan / Keterangan:"), 4, 2)
        lbl_ket = QLabel(str(o.get("keterangan") or "-"))
        lbl_ket.setWordWrap(True)
        grid.addWidget(lbl_ket, 4, 3)

        for c_idx in range(4):
            grid.setColumnMinimumWidth(c_idx, 95)

        self.content_layout.addLayout(grid)
        self.content_layout.addWidget(QFrame(frameShape=QFrame.HLine))

        # 3. Riwayat Pembayaran / Cicilan Kas
        lbl_cicil_title = QLabel("RIWAYAT PEMBAYARAN / CICILAN UNTUK FAKTUR INI:")
        lbl_cicil_title.setStyleSheet(f"font-weight: 700; color: {styles.COLOR_PRIMARY_DARK}; font-size: 11px;")
        self.content_layout.addWidget(lbl_cicil_title)

        cicilan_list = database.get_cicilan_semen_list(order_id=o.get("id"))
        if cicilan_list:
            tbl = ModernTableWidget(["No", "Tanggal Bayar", "Nominal Dibayar (Rp)", "Metode Bayar", "Keterangan / Bukti"])
            tbl.setColumnWidth(0, 35)
            tbl.setColumnWidth(1, 95)
            tbl.setColumnWidth(2, 140)
            tbl.setColumnWidth(3, 120)
            tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
            tbl.setMaximumHeight(160)
            tbl.setRowCount(len(cicilan_list))
            for idx, c in enumerate(cicilan_list):
                tbl.setItem(idx, 0, QTableWidgetItem(str(idx + 1)))
                tbl.setItem(idx, 1, QTableWidgetItem(str(c["tanggal"])))
                nom_item = QTableWidgetItem(styles.format_rupiah(c["nominal"]))
                nom_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                tbl.setItem(idx, 2, nom_item)
                tbl.setItem(idx, 3, QTableWidgetItem(str(c["metode"] or "-")))
                tbl.setItem(idx, 4, QTableWidgetItem(str(c["keterangan"] or "-")))
            self.content_layout.addWidget(tbl)
        else:
            lbl_empty = QLabel("Belum ada riwayat pembayaran / cicilan tercatat untuk DO ini.")
            lbl_empty.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-style: italic; padding: 6px 0;")
            self.content_layout.addWidget(lbl_empty)

        # 4. Tombol Footer
        self.btn_save.setText("Tutup")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.setVisible(False)

        if not is_lunas:
            btn_bayar = SuccessButton("💳 Catat Cicilan / Bayar Tagihan Ini")
            btn_bayar.clicked.connect(self.on_bayar_clicked)
            footer_lay = self.main_layout.itemAt(self.main_layout.count() - 1).layout()
            if footer_lay:
                footer_lay.insertWidget(0, btn_bayar)

    def on_bayar_clicked(self):
        self.accept()
        if self.parent_view and hasattr(self.parent_view, "bayar_order_semen_langsung"):
            self.parent_view.bayar_order_semen_langsung(self.order_data)


# ==============================================================================
# 3. DIALOG INPUT ORDER / DO SEMEN MANUAL
# ==============================================================================
class OrderSemenDialog(ModernDialog):
    def __init__(self, parent=None):
        super().__init__("Catat DO / Tagihan Material Baru", parent, min_width=540)
        self.materials = database.get_all_materials()
        self.init_form()

    def init_form(self):
        grid = QGridLayout()
        grid.setSpacing(12)

        # 0. Kategori Piutang (Segmented Card Selection)
        grid.addWidget(QLabel("Kategori Piutang:*"), 0, 0)
        kat_frame = QFrame()
        kat_frame.setStyleSheet("background-color: transparent;")
        kat_lay = QHBoxLayout(kat_frame)
        kat_lay.setContentsMargins(0, 0, 0, 0)
        kat_lay.setSpacing(10)

        self.btn_kat_kantor = QPushButton("🏢 Piutang Kantor")
        self.btn_kat_kantor.setCheckable(True)
        self.btn_kat_kantor.setChecked(True)
        self.btn_kat_kantor.setCursor(Qt.PointingHandCursor)
        self.btn_kat_kantor.setFixedHeight(36)

        self.btn_kat_perusahaan = QPushButton("🏭 Piutang Perusahaan")
        self.btn_kat_perusahaan.setCheckable(True)
        self.btn_kat_perusahaan.setCursor(Qt.PointingHandCursor)
        self.btn_kat_perusahaan.setFixedHeight(36)

        self.grp_kat = QButtonGroup(self)
        self.grp_kat.setExclusive(True)
        self.grp_kat.addButton(self.btn_kat_kantor, 0)
        self.grp_kat.addButton(self.btn_kat_perusahaan, 1)

        btn_k_style = """
            QPushButton {
                background-color: #F8FAFC; color: #334155; border: 1.5px solid #CBD5E1;
                border-radius: 6px; padding: 4px 14px; font-weight: 600; font-size: 12px;
            }
            QPushButton:hover { background-color: #EFF6FF; border-color: #3B82F6; color: #1D4ED8; }
            QPushButton:checked { background-color: #1E3A8A; color: #FFFFFF; border: 2px solid #1D4ED8; font-weight: 700; }
        """
        btn_p_style = """
            QPushButton {
                background-color: #F8FAFC; color: #334155; border: 1.5px solid #CBD5E1;
                border-radius: 6px; padding: 4px 14px; font-weight: 600; font-size: 12px;
            }
            QPushButton:hover { background-color: #FFFBEB; border-color: #F59E0B; color: #B45309; }
            QPushButton:checked { background-color: #D97706; color: #FFFFFF; border: 2px solid #B45309; font-weight: 700; }
        """
        self.btn_kat_kantor.setStyleSheet(btn_k_style)
        self.btn_kat_perusahaan.setStyleSheet(btn_p_style)

        kat_lay.addWidget(self.btn_kat_kantor)
        kat_lay.addWidget(self.btn_kat_perusahaan)
        kat_lay.addStretch()
        grid.addWidget(kat_frame, 0, 1)

        # 1. Jenis Material
        grid.addWidget(QLabel("Jenis Material:*"), 1, 0)
        self.cb_mat = QComboBox()
        self.cb_mat.setView(QListView())
        for m in self.materials:
            self.cb_mat.addItem(f"{m['nama']} ({m['kode']})", m["id"])
        self.cb_mat.currentIndexChanged.connect(self.on_mat_changed)
        grid.addWidget(self.cb_mat, 1, 1)

        # 2. No. DO / Order
        grid.addWidget(QLabel("No. DO / Order:*"), 2, 0)
        self.txt_no_order = QLineEdit()
        self.txt_no_order.setPlaceholderText("Contoh: DO-MAT-2026-09-01")
        grid.addWidget(self.txt_no_order, 2, 1)

        # 3. Supplier
        grid.addWidget(QLabel("Supplier / Asal:*"), 3, 0)
        self.txt_supplier = QLineEdit()
        self.txt_supplier.setText("PT Semen Indonesia (Gresik)")
        grid.addWidget(self.txt_supplier, 3, 1)

        # 4. Tanggal Order
        grid.addWidget(QLabel("Tanggal Order:*"), 4, 0)
        self.dt_order = QDateEdit()
        self.dt_order.setCalendarPopup(True)
        self.dt_order.setDate(QDate.currentDate())
        self.dt_order.setDisplayFormat("yyyy-MM-dd")
        grid.addWidget(self.dt_order, 4, 1)

        # 5. Tanggal Datang
        grid.addWidget(QLabel("Tanggal Datang:*"), 5, 0)
        self.dt_datang = QDateEdit()
        self.dt_datang.setCalendarPopup(True)
        self.dt_datang.setDate(QDate.currentDate())
        self.dt_datang.setDisplayFormat("yyyy-MM-dd")
        self.dt_datang.dateChanged.connect(self.on_datang_changed)
        grid.addWidget(self.dt_datang, 5, 1)

        # 6. Tanggal Jatuh Tempo
        grid.addWidget(QLabel("Jatuh Tempo:*"), 6, 0)
        jt_box = QFrame()
        jt_box.setStyleSheet("background-color: transparent;")
        jt_lay = QHBoxLayout(jt_box)
        jt_lay.setContentsMargins(0, 0, 0, 0)
        jt_lay.setSpacing(6)

        self.dt_jatuh_tempo = QDateEdit()
        self.dt_jatuh_tempo.setCalendarPopup(True)
        self.dt_jatuh_tempo.setDate(QDate.currentDate().addDays(14))
        self.dt_jatuh_tempo.setDisplayFormat("yyyy-MM-dd")
        self.dt_jatuh_tempo.setFixedWidth(120)
        jt_lay.addWidget(self.dt_jatuh_tempo)

        btn_p7 = QPushButton("+7 Hari")
        btn_p14 = QPushButton("+14 Hari")
        btn_p30 = QPushButton("+30 Hari")
        btn_p40 = QPushButton("+40 Hari")
        p_style = "QPushButton { background-color: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 4px; padding: 3px 8px; font-size: 11px; font-weight: 600; } QPushButton:hover { background-color: #E2E8F0; }"
        for b in (btn_p7, btn_p14, btn_p30, btn_p40):
            b.setStyleSheet(p_style)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(28)
        btn_p7.clicked.connect(lambda: self.dt_jatuh_tempo.setDate(self.dt_datang.date().addDays(7)))
        btn_p14.clicked.connect(lambda: self.dt_jatuh_tempo.setDate(self.dt_datang.date().addDays(14)))
        btn_p30.clicked.connect(lambda: self.dt_jatuh_tempo.setDate(self.dt_datang.date().addDays(30)))
        btn_p40.clicked.connect(lambda: self.dt_jatuh_tempo.setDate(self.dt_datang.date().addDays(40)))
        jt_lay.addWidget(btn_p7)
        jt_lay.addWidget(btn_p14)
        jt_lay.addWidget(btn_p30)
        jt_lay.addWidget(btn_p40)
        jt_lay.addStretch()
        grid.addWidget(jt_box, 6, 1)

        # 7. Jumlah
        self.lbl_jumlah_title = QLabel("Jumlah (Ton):*")
        grid.addWidget(self.lbl_jumlah_title, 7, 0)
        self.spin_ton = QDoubleSpinBox()
        self.spin_ton.setRange(0.01, 1000000.0)
        self.spin_ton.setDecimals(2)
        self.spin_ton.setValue(30.0)
        self.spin_ton.valueChanged.connect(self.calculate_total)
        grid.addWidget(self.spin_ton, 7, 1)

        # 8. Harga per Satuan
        self.lbl_harga_title = QLabel("Harga per Satuan (Rp):*")
        grid.addWidget(self.lbl_harga_title, 8, 0)
        self.spin_harga = QDoubleSpinBox()
        self.spin_harga.setRange(0, 100000000.0)
        self.spin_harga.setDecimals(0)
        self.spin_harga.setSingleStep(50000)
        self.spin_harga.setValue(1150000)
        self.spin_harga.valueChanged.connect(self.calculate_total)
        grid.addWidget(self.spin_harga, 8, 1)

        # 9. Total Tagihan
        grid.addWidget(QLabel("Total Tagihan:"), 9, 0)
        self.lbl_total = QLabel("Rp 0")
        self.lbl_total.setStyleSheet(f"font-weight: 800; color: {styles.COLOR_PRIMARY_LIGHT}; font-size: 15px;")
        grid.addWidget(self.lbl_total, 9, 1)

        # 10. Keterangan
        grid.addWidget(QLabel("Keterangan:"), 10, 0)
        self.txt_ket = QLineEdit()
        self.txt_ket.setPlaceholderText("Jenis material, spesifikasi, dll")
        grid.addWidget(self.txt_ket, 10, 1)

        self.content_layout.addLayout(grid)
        self.btn_save.clicked.connect(self.save)
        self.on_mat_changed()
        self.calculate_total()

    def on_datang_changed(self):
        self.dt_jatuh_tempo.setDate(self.dt_datang.date().addDays(14))

    def on_mat_changed(self):
        mat_id = self.cb_mat.currentData()
        mat = next((m for m in self.materials if m["id"] == mat_id), None)
        if mat:
            sat = mat.get("satuan") or "Unit"
            self.lbl_jumlah_title.setText(f"Jumlah ({sat}):*")
            self.lbl_harga_title.setText(f"Harga per {sat} (Rp):*")
            h = float(mat.get("harga_beli_terbaru") or 0)
            if h > 0:
                self.spin_harga.setValue(h)

    def calculate_total(self):
        tot = self.spin_ton.value() * self.spin_harga.value()
        self.lbl_total.setText(styles.format_rupiah(tot))

    def save(self):
        mat_id = self.cb_mat.currentData()
        kat = "perusahaan" if self.btn_kat_perusahaan.isChecked() else "kantor"
        no_order = self.txt_no_order.text().strip()
        supplier = self.txt_supplier.text().strip()
        tgl_order = self.dt_order.date().toString("yyyy-MM-dd")
        tgl_datang = self.dt_datang.date().toString("yyyy-MM-dd")
        jatuh_tempo = self.dt_jatuh_tempo.date().toString("yyyy-MM-dd")
        ton = self.spin_ton.value()
        harga = self.spin_harga.value()
        ket = self.txt_ket.text().strip()

        if ton <= 0 or harga <= 0:
            QMessageBox.warning(self, "Peringatan", "Jumlah dan Harga per Satuan harus lebih dari 0!")
            return

        try:
            database.catat_order_semen(
                tgl_order, tgl_datang, ton, harga, supplier, no_order, ket,
                kategori_piutang=kat, material_id=mat_id, jatuh_tempo=jatuh_tempo
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", f"Gagal menyimpan order material: {str(e)}")


# ==============================================================================
# 4. DIALOG TERIMA PEMBAYARAN PROYEK KLIEN
# ==============================================================================
class PembayaranProyekDialog(ModernDialog):
    def __init__(self, parent=None, target_proyek: dict = None):
        title = "Catat Penerimaan Pembayaran / Termin Proyek"
        if target_proyek:
            nama_pr = target_proyek.get("nama") or f"Proyek #{target_proyek.get('id')}"
            title = f"Terima Pembayaran Proyek - {nama_pr}"
        super().__init__(title, parent, min_width=520)
        self.target_proyek = target_proyek
        self.proyek_list = database.get_all_proyek()
        self.init_form()

    def init_form(self):
        grid = QGridLayout()
        grid.setSpacing(12)

        row_offset = 0
        if not self.target_proyek:
            grid.addWidget(QLabel("Pilih Proyek:*"), 0, 0)
            self.cb_proyek = QComboBox()
            self.cb_proyek.setView(QListView())
            
            rekap_pr = database.get_rekap_saldo_per_proyek()
            rekap_map = {r["id"]: r for r in rekap_pr}

            for p in self.proyek_list:
                r = rekap_map.get(p["id"])
                sisa = r["sisa_saldo_piutang"] if r else 0.0
                lbl = f"{p['nama']} (Sisa Piutang: {styles.format_rupiah(sisa)})"
                self.cb_proyek.addItem(lbl, p["id"])
            grid.addWidget(self.cb_proyek, 0, 1)
            row_offset = 1

        grid.addWidget(QLabel("Tanggal Terima Bayar:*"), row_offset + 0, 0)
        self.dt_tgl = QDateEdit()
        self.dt_tgl.setCalendarPopup(True)
        self.dt_tgl.setDate(QDate.currentDate())
        self.dt_tgl.setDisplayFormat("yyyy-MM-dd")
        grid.addWidget(self.dt_tgl, row_offset + 0, 1)

        grid.addWidget(QLabel("Nominal Masuk (Rp):*"), row_offset + 1, 0)
        self.spin_bayar = QDoubleSpinBox()
        self.spin_bayar.setRange(1000, 100000000000.0)
        self.spin_bayar.setDecimals(0)
        self.spin_bayar.setSingleStep(1000000)
        
        if self.target_proyek:
            sisa_piutang = float(self.target_proyek.get("sisa_saldo_piutang") or 0)
            self.spin_bayar.setValue(sisa_piutang if sisa_piutang > 0 else 0)
        else:
            self.spin_bayar.setValue(10000000)
        grid.addWidget(self.spin_bayar, row_offset + 1, 1)

        grid.addWidget(QLabel("Metode Penerimaan:"), row_offset + 2, 0)
        self.cb_metode = QComboBox()
        self.cb_metode.setView(QListView())
        self.cb_metode.addItems(["Transfer Bank (BNI)", "Transfer Bank (Mandiri)", "Transfer Bank (BCA)", "Transfer Bank (Bank Jateng / BRI)", "Tunai / Cash", "Giro / Cek"])
        grid.addWidget(self.cb_metode, row_offset + 2, 1)

        grid.addWidget(QLabel("No. Bukti / Kuitansi:"), row_offset + 3, 0)
        self.txt_bukti = QLineEdit()
        self.txt_bukti.setPlaceholderText("Contoh: KW-2026/09/001 / Ref Bank")
        grid.addWidget(self.txt_bukti, row_offset + 3, 1)

        grid.addWidget(QLabel("Keterangan / Termin:"), row_offset + 4, 0)
        self.txt_ket = QTextEdit()
        self.txt_ket.setPlaceholderText("Contoh: Pembayaran Termin 1 Pengecoran Jalan Segmen STA 0-500")
        self.txt_ket.setMaximumHeight(65)
        grid.addWidget(self.txt_ket, row_offset + 4, 1)

        # Info otomatis tambah kas
        lbl_info = QLabel("Catatan: Penerimaan pembayaran ini akan otomatis menambah Saldo Kas Plant.")
        lbl_info.setStyleSheet(f"color: {styles.COLOR_SUCCESS}; font-size: 11px; font-weight: 600;")
        grid.addWidget(lbl_info, row_offset + 5, 0, 1, 2)

        self.content_layout.addLayout(grid)
        self.btn_save.clicked.connect(self.save)

    def save(self):
        if self.target_proyek:
            pr_id = self.target_proyek.get("id")
        else:
            pr_id = self.cb_proyek.currentData()

        tgl = self.dt_tgl.date().toString("yyyy-MM-dd")
        nominal = self.spin_bayar.value()
        metode = self.cb_metode.currentText()
        bukti = self.txt_bukti.text().strip()
        ket = self.txt_ket.toPlainText().strip()

        if not pr_id:
            QMessageBox.warning(self, "Peringatan", "Pilih proyek terlebih dahulu!")
            return
        if nominal <= 0:
            QMessageBox.warning(self, "Peringatan", "Nominal pembayaran harus lebih besar dari 0!")
            return

        try:
            database.catat_pembayaran_proyek(pr_id, tgl, nominal, metode, bukti, ket)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", f"Gagal mencatat pembayaran proyek: {str(e)}")


# ==============================================================================
# 5. DIALOG PENGELUARAN KAS KANTOR (NOTA NON-SEMEN)
# ==============================================================================
class KasKantorDialog(ModernDialog):
    def __init__(self, parent=None):
        super().__init__("Catat Pengeluaran Kas Kantor / Harian", parent, min_width=500)
        self.init_form()

    def init_form(self):
        grid = QGridLayout()
        grid.setSpacing(12)

        grid.addWidget(QLabel("Tanggal Nota / Bukti:*"), 0, 0)
        self.dt_tgl = QDateEdit()
        self.dt_tgl.setCalendarPopup(True)
        self.dt_tgl.setDate(QDate.currentDate())
        self.dt_tgl.setDisplayFormat("yyyy-MM-dd")
        grid.addWidget(self.dt_tgl, 0, 1)

        grid.addWidget(QLabel("Kategori Pengeluaran:*"), 1, 0)
        self.cb_kat = QComboBox()
        self.cb_kat.setView(QListView())
        self.cb_kat.setEditable(True)
        self.cb_kat.addItems([
            "Konsumsi & Dapur",
            "ATK & Perlengkapan Kantor",
            "Listrik, Air & Komunikasi",
            "Retribusi, Parkir & Keamanan",
            "Kebersihan & Perlengkapan Plant",
            "Lain-lain (Operasional Kantor)"
        ])
        grid.addWidget(self.cb_kat, 1, 1)

        grid.addWidget(QLabel("No. Nota / Kuitansi:"), 2, 0)
        self.txt_nota = QLineEdit()
        self.txt_nota.setPlaceholderText("Contoh: NOTA-092 / Toko-881")
        grid.addWidget(self.txt_nota, 2, 1)

        grid.addWidget(QLabel("Nama Toko / Penerima:"), 3, 0)
        self.txt_toko = QLineEdit()
        self.txt_toko.setPlaceholderText("Contoh: Toko Bangunan Berkah / PLN / PDAM")
        grid.addWidget(self.txt_toko, 3, 1)

        grid.addWidget(QLabel("Nominal Pengeluaran (Rp):*"), 4, 0)
        self.spin_nominal = QDoubleSpinBox()
        self.spin_nominal.setRange(100, 10000000000.0)
        self.spin_nominal.setDecimals(0)
        self.spin_nominal.setSingleStep(50000)
        self.spin_nominal.setValue(100000)
        grid.addWidget(self.spin_nominal, 4, 1)

        grid.addWidget(QLabel("Rincian / Keterangan:*"), 5, 0)
        self.txt_ket = QTextEdit()
        self.txt_ket.setPlaceholderText("Uraian pengeluaran operasional kantor...")
        self.txt_ket.setMaximumHeight(65)
        grid.addWidget(self.txt_ket, 5, 1)

        # Info otomatis potong kas
        lbl_info = QLabel("Catatan: Pengeluaran ini memotong Saldo Kas Plant. Untuk operasional kendaraan, BBM cor & servis, gunakan menu khusus Operasional Kendaraan.")
        lbl_info.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px; font-style: italic;")
        grid.addWidget(lbl_info, 6, 0, 1, 2)

        self.content_layout.addLayout(grid)
        self.btn_save.clicked.connect(self.save)

    def save(self):
        tgl = self.dt_tgl.date().toString("yyyy-MM-dd")
        kat = self.cb_kat.currentText().strip()
        nota = self.txt_nota.text().strip()
        toko = self.txt_toko.text().strip()
        nominal = self.spin_nominal.value()
        ket = self.txt_ket.toPlainText().strip()

        if nominal <= 0:
            QMessageBox.warning(self, "Peringatan", "Nominal pengeluaran harus lebih besar dari Rp 0!")
            return
        if not ket:
            QMessageBox.warning(self, "Peringatan", "Rincian keterangan pengeluaran wajib diisi!")
            return

        try:
            database.catat_kas_kantor(tgl, nominal, kat, nota, toko, ket, "", kendaraan_id=None, pengiriman_id=None)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", f"Gagal mencatat kas kantor: {str(e)}")


# ==============================================================================
# 6. DIALOG PEMBAYARAN GAJI KARYAWAN
# ==============================================================================
class GajiKaryawanDialog(ModernDialog):
    def __init__(self, parent=None):
        super().__init__("Catat Pembayaran Gaji Karyawan", parent, min_width=500)
        self.init_form()

    def init_form(self):
        grid = QGridLayout()
        grid.setSpacing(12)

        grid.addWidget(QLabel("Tanggal Pembayaran:*"), 0, 0)
        self.dt_tgl = QDateEdit()
        self.dt_tgl.setCalendarPopup(True)
        self.dt_tgl.setDate(QDate.currentDate())
        self.dt_tgl.setDisplayFormat("yyyy-MM-dd")
        grid.addWidget(self.dt_tgl, 0, 1)

        grid.addWidget(QLabel("Periode Gaji:*"), 1, 0)
        self.txt_periode = QLineEdit()
        self.txt_periode.setPlaceholderText("Contoh: Minggu 1 Sept 2026 / Bulan Agustus 2026")
        self.txt_periode.setText(f"Minggu {QDate.currentDate().weekNumber()[0]} {datetime.now().strftime('%B %Y')}")
        grid.addWidget(self.txt_periode, 1, 1)

        grid.addWidget(QLabel("Nama Karyawan:*"), 2, 0)
        self.txt_nama = QLineEdit()
        self.txt_nama.setPlaceholderText("Contoh: Supriyanto / Bambang / Slamet")
        grid.addWidget(self.txt_nama, 2, 1)

        grid.addWidget(QLabel("Jabatan / Posisi:"), 3, 0)
        self.cb_jabatan = QComboBox()
        self.cb_jabatan.setView(QListView())
        self.cb_jabatan.setEditable(True)
        self.cb_jabatan.addItems([
            "Supir Truk Mixer",
            "Operator Batching Plant",
            "Operator Wheel Loader",
            "Mekanik / Maintenance",
            "Helper Lapangan / Lab",
            "Admin / Staf Keuangan",
            "Satpam / Keamanan",
            "Lain-lain"
        ])
        grid.addWidget(self.cb_jabatan, 3, 1)

        grid.addWidget(QLabel("Gaji Pokok / Upah (Rp):*"), 4, 0)
        self.spin_gaji = QDoubleSpinBox()
        self.spin_gaji.setRange(0, 1000000000.0)
        self.spin_gaji.setDecimals(0)
        self.spin_gaji.setSingleStep(250000)
        self.spin_gaji.setValue(2000000)
        self.spin_gaji.valueChanged.connect(self.calculate_total)
        grid.addWidget(self.spin_gaji, 4, 1)

        grid.addWidget(QLabel("Tunjangan / Bonus / Ritase (Rp):"), 5, 0)
        self.spin_tunjangan = QDoubleSpinBox()
        self.spin_tunjangan.setRange(-100000000.0, 1000000000.0)
        self.spin_tunjangan.setDecimals(0)
        self.spin_tunjangan.setSingleStep(50000)
        self.spin_tunjangan.setValue(250000)
        self.spin_tunjangan.valueChanged.connect(self.calculate_total)
        grid.addWidget(self.spin_tunjangan, 5, 1)

        grid.addWidget(QLabel("Total Gaji Dibayarkan:"), 6, 0)
        self.lbl_total = QLabel("Rp 0")
        self.lbl_total.setStyleSheet(f"font-weight: 800; color: {styles.COLOR_PRIMARY_LIGHT}; font-size: 15px;")
        grid.addWidget(self.lbl_total, 6, 1)

        grid.addWidget(QLabel("Metode Pembayaran:"), 7, 0)
        self.cb_metode = QComboBox()
        self.cb_metode.setView(QListView())
        self.cb_metode.addItems(["Tunai / Cash", "Transfer Bank Mandiri", "Transfer Bank BCA", "Transfer Bank BNI", "Transfer Bank BRI"])
        grid.addWidget(self.cb_metode, 7, 1)

        grid.addWidget(QLabel("Keterangan Tambahan:"), 8, 0)
        self.txt_ket = QLineEdit()
        self.txt_ket.setPlaceholderText("Uang ritase, lembur pengecoran, dsb")
        grid.addWidget(self.txt_ket, 8, 1)

        self.content_layout.addLayout(grid)
        self.btn_save.clicked.connect(self.save)
        self.calculate_total()

    def calculate_total(self):
        tot = self.spin_gaji.value() + self.spin_tunjangan.value()
        self.lbl_total.setText(styles.format_rupiah(tot))

    def save(self):
        tgl = self.dt_tgl.date().toString("yyyy-MM-dd")
        periode = self.txt_periode.text().strip()
        nama = self.txt_nama.text().strip()
        jabatan = self.cb_jabatan.currentText().strip()
        gaji = self.spin_gaji.value()
        tunjangan = self.spin_tunjangan.value()
        metode = self.cb_metode.currentText()
        ket = self.txt_ket.text().strip()

        if not nama or not periode:
            QMessageBox.warning(self, "Peringatan", "Nama Karyawan dan Periode Gaji wajib diisi!")
            return
        if (gaji + tunjangan) <= 0:
            QMessageBox.warning(self, "Peringatan", "Total gaji yang dibayarkan harus lebih besar dari Rp 0!")
            return

        try:
            database.catat_gaji_karyawan(tgl, periode, nama, gaji, jabatan, tunjangan, metode, ket)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", f"Gagal mencatat gaji karyawan: {str(e)}")


# ==============================================================================
# 7. DIALOG DETAIL PEMBAYARAN GAJI KARYAWAN
# ==============================================================================
class DetailGajiDialog(ModernDialog):
    """Dialog detail rincian pembayaran gaji karyawan"""
    def __init__(self, gaji_data: dict, parent=None):
        nama = gaji_data.get("nama_karyawan") or "Karyawan"
        super().__init__(f"Rincian Gaji: {nama}", parent, min_width=500)
        self.gaji_data = gaji_data
        self.init_detail()

    def init_detail(self):
        d = self.gaji_data
        if not d:
            self.content_layout.addWidget(QLabel("Data gaji tidak ditemukan."))
            return

        tot = float(d.get("total_dibayar") or 0)
        gp = float(d.get("nominal_gaji") or 0)
        tj = float(d.get("potongan_tunjangan") or 0)
        metode = str(d.get("metode_bayar") or "Tunai / Cash")

        # 1. Header Banner Total Gaji Diterima (Take Home Pay)
        banner = QFrame()
        banner.setStyleSheet("""
            QFrame {
                background-color: #ECFDF5;
                border: 1.5px solid #A7F3D0;
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        b_lay = QVBoxLayout(banner)
        b_lay.setContentsMargins(6, 6, 6, 6)
        b_lay.setSpacing(2)

        lbl_b_title = QLabel("TOTAL GAJI DITERIMA (TAKE HOME PAY)")
        lbl_b_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #065F46; letter-spacing: 0.5px;")
        b_lay.addWidget(lbl_b_title)

        lbl_b_val = QLabel(styles.format_rupiah(tot))
        lbl_b_val.setStyleSheet("font-size: 22px; font-weight: 800; color: #059669;")
        b_lay.addWidget(lbl_b_val)

        self.content_layout.addWidget(banner)
        self.content_layout.addSpacing(8)

        # 2. Grid Rincian Informasi
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)

        rows = [
            ("Nama Karyawan", str(d.get("nama_karyawan") or "-")),
            ("Jabatan / Posisi", str(d.get("jabatan") or "-")),
            ("Tanggal Pembayaran", str(d.get("tanggal_bayar") or "-")),
            ("Periode Gaji", str(d.get("periode_gaji") or "-")),
            ("Gaji Pokok / Upah", styles.format_rupiah(gp)),
            ("Tunjangan / Bonus / Ritase", styles.format_rupiah(tj)),
            ("Total Dibayar", styles.format_rupiah(tot)),
            ("Metode Pembayaran", metode),
            ("Catatan / Keterangan", str(d.get("keterangan") or "-")),
            ("Waktu Pencatatan", str(d.get("created_at") or "-"))
        ]

        for idx, (label, val) in enumerate(rows):
            lbl_k = QLabel(f"<b>{label}:</b>")
            lbl_k.setStyleSheet("color: #475569; font-size: 12px;")

            if label == "Metode Pembayaran":
                val_w = QWidget()
                v_lay = QHBoxLayout(val_w)
                v_lay.setContentsMargins(0, 0, 0, 0)
                badge_m = BadgeLabel(val, "success" if "tunai" in val.lower() else "primary")
                v_lay.addWidget(badge_m)
                v_lay.addStretch()
                grid.addWidget(lbl_k, idx, 0, Qt.AlignTop)
                grid.addWidget(val_w, idx, 1, Qt.AlignVCenter)
            elif label == "Total Dibayar":
                lbl_v = QLabel(val)
                lbl_v.setStyleSheet("color: #059669; font-size: 13px; font-weight: 800;")
                grid.addWidget(lbl_k, idx, 0, Qt.AlignTop)
                grid.addWidget(lbl_v, idx, 1, Qt.AlignTop)
            else:
                lbl_v = QLabel(val)
                lbl_v.setStyleSheet("color: #0F172A; font-size: 12px; font-weight: 600;")
                lbl_v.setWordWrap(True)
                grid.addWidget(lbl_k, idx, 0, Qt.AlignTop)
                grid.addWidget(lbl_v, idx, 1, Qt.AlignTop)

        grid.setColumnMinimumWidth(0, 160)
        self.content_layout.addLayout(grid)

        self.btn_save.setText("Tutup")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.setVisible(False)


# ==============================================================================
# MAIN KEUANGAN VIEW (5 TAB TERINTEGRASI)
# ==============================================================================
class KeuanganView(QWidget):
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 12)
        main_layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("CleanTabWidget")
        self.tabs.setProperty("class", "CleanTabWidget")
        
        self.tab_ringkasan = QWidget()
        self.tab_semen = QWidget()
        self.tab_proyek = QWidget()
        self.tab_kantor = QWidget()
        self.tab_gaji = QWidget()
        self.tab_kendaraan = KendaraanView(parent=self)
        self.tab_kendaraan.data_changed.connect(self.refresh_all)

        self.setup_tab_ringkasan()
        self.setup_tab_semen()
        self.setup_tab_proyek()
        self.setup_tab_kantor()
        self.setup_tab_gaji()

        self.tabs.addTab(self.tab_ringkasan, "Ringkasan & Saldo Kas")
        self.tabs.addTab(self.tab_semen, "Piutang Material")
        self.tabs.addTab(self.tab_proyek, "Piutang & Pembayaran Proyek")
        self.tabs.addTab(self.tab_kantor, "Kas Kantor (Harian)")
        self.tabs.addTab(self.tab_gaji, "Gaji Karyawan")
        self.tabs.addTab(self.tab_kendaraan, "Operasional Kendaraan")

        # Sembunyikan tab bar bawaan agar tampilan bersih & lapang (dikendalikan via collapsible submenu sidebar)
        self.tabs.tabBar().hide()

        main_layout.addWidget(self.tabs)
        self.refresh_all()

    # --------------------------------------------------------------------------
    # TAB 1: RINGKASAN & SALDO KAS BUKU BESAR
    # --------------------------------------------------------------------------
    def setup_tab_ringkasan(self):
        layout = QVBoxLayout(self.tab_ringkasan)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 6 KPI Cards Grid
        kpi_lay = QGridLayout()
        kpi_lay.setSpacing(10)

        self.card_saldo_utama = StatCard("Saldo Kas Plant Tersedia", "Rp 0", "Kas Riil Bebas Selisih", "#1E3A8A")
        self.card_in_proyek = StatCard("(+) Pembayaran Proyek", "Rp 0", "Penerimaan Dari Klien", "#059669")
        self.card_out_semen = StatCard("(-) Pembayaran Semen", "Rp 0", "Hutang Supplier Semen", "#DC2626")
        self.card_out_kendaraan = StatCard("(-) Operasional Kendaraan", "Rp 0", "BBM, Servis, Supir", "#EA580C")
        self.card_out_kantor = StatCard("(-) Kas Kantor Harian", "Rp 0", "ATK, Listrik, Operasional", "#D97706")
        self.card_out_gaji = StatCard("(-) Gaji Karyawan", "Rp 0", "Payroll Supir & Operator", "#7C3AED")

        kpi_lay.addWidget(self.card_saldo_utama, 0, 0)
        kpi_lay.addWidget(self.card_in_proyek, 0, 1)
        kpi_lay.addWidget(self.card_out_semen, 0, 2)
        kpi_lay.addWidget(self.card_out_kendaraan, 0, 3)
        kpi_lay.addWidget(self.card_out_kantor, 0, 4)
        kpi_lay.addWidget(self.card_out_gaji, 0, 5)
        layout.addLayout(kpi_lay)

        # Filter & Action Bar
        filter_frame = QFrame()
        filter_frame.setProperty("class", "CardWidget")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(10, 8, 10, 8)
        filter_layout.setSpacing(10)

        filter_layout.addWidget(QLabel("Filter:"))
        self.cb_filter_kat_kas = QComboBox()
        self.cb_filter_kat_kas.setView(QListView())
        self.cb_filter_kat_kas.addItems([
            "Semua Kategori",
            "Pembayaran Proyek",
            "Pembayaran Semen",
            "Operasional Kendaraan",
            "Kas Kantor",
            "Gaji Karyawan",
            "Modal Awal"
        ])
        self.cb_filter_kat_kas.currentIndexChanged.connect(self.load_ringkasan_kas)
        self.cb_filter_kat_kas.setMinimumWidth(170)
        filter_layout.addWidget(self.cb_filter_kat_kas)

        filter_layout.addWidget(QLabel("Mulai:"))
        self.dt_kas_start = QDateEdit()
        self.dt_kas_start.setCalendarPopup(True)
        self.dt_kas_start.setDate(QDate.currentDate().addMonths(-1))
        self.dt_kas_start.setDisplayFormat("yyyy-MM-dd")
        self.dt_kas_start.setFixedWidth(105)
        filter_layout.addWidget(self.dt_kas_start)

        filter_layout.addWidget(QLabel("s/d:"))
        self.dt_kas_end = QDateEdit()
        self.dt_kas_end.setCalendarPopup(True)
        self.dt_kas_end.setDate(QDate.currentDate())
        self.dt_kas_end.setDisplayFormat("yyyy-MM-dd")
        self.dt_kas_end.setFixedWidth(105)
        filter_layout.addWidget(self.dt_kas_end)

        btn_filter = PrimaryButton("Filter")
        btn_filter.clicked.connect(self.load_ringkasan_kas)
        filter_layout.addWidget(btn_filter)

        btn_all = SecondaryButton("Semua")
        btn_all.clicked.connect(self.reset_filter_kas)
        filter_layout.addWidget(btn_all)

        filter_layout.addStretch()

        btn_modal = SuccessButton("+ Modal")
        btn_modal.setToolTip("Catat Modal Awal atau Setoran Kas Baru")
        btn_modal.clicked.connect(self.add_modal_kas)
        filter_layout.addWidget(btn_modal)

        layout.addWidget(filter_frame)

        lbl_tbl = QLabel("BUKU KAS UMUM BATCHING PLANT (ARUS KAS OTOMATIS BERJALAN):")
        lbl_tbl.setStyleSheet(f"font-weight: 700; color: {styles.COLOR_PRIMARY_DARK}; margin-top: 4px;")
        layout.addWidget(lbl_tbl)

        self.table_kas = ModernTableWidget([
            "No", "Tanggal", "Kategori Modul", "Kas Masuk (Rp)", "Kas Keluar (Rp)", "Total Saldo (Rp)", "Aksi"
        ])
        self.table_kas.setColumnWidth(0, 50)
        self.table_kas.setColumnWidth(1, 110)
        self.table_kas.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_kas.horizontalHeader().setSectionResizeMode(5, QHeaderView.Interactive)
        self.table_kas.setColumnWidth(3, 150)
        self.table_kas.setColumnWidth(4, 150)
        self.table_kas.setColumnWidth(5, 160)
        self.table_kas.setColumnWidth(6, 90)
        layout.addWidget(self.table_kas)

    def reset_filter_kas(self):
        self.dt_kas_start.setDate(QDate(2020, 1, 1))
        self.dt_kas_end.setDate(QDate.currentDate().addYears(1))
        self.cb_filter_kat_kas.setCurrentIndex(0)
        self.load_ringkasan_kas()

    def load_ringkasan_kas(self):
        start_d = self.dt_kas_start.date().toString("yyyy-MM-dd")
        end_d = self.dt_kas_end.date().toString("yyyy-MM-dd")
        kat = self.cb_filter_kat_kas.currentText()

        # Update KPI cards
        summary = database.get_ringkasan_kas()
        self.card_saldo_utama.update_value(styles.format_rupiah(summary["saldo_akhir"]))
        self.card_in_proyek.update_value(styles.format_rupiah(summary["total_in_proyek"]))
        self.card_out_semen.update_value(styles.format_rupiah(summary["total_out_semen"]))
        if hasattr(self, "card_out_kendaraan"):
            self.card_out_kendaraan.update_value(styles.format_rupiah(summary.get("total_out_kendaraan") or 0))
            self.card_out_kantor.update_value(styles.format_rupiah(summary.get("total_out_kantor_murni") or 0))
        else:
            self.card_out_kantor.update_value(styles.format_rupiah(summary["total_out_kantor"]))
        self.card_out_gaji.update_value(styles.format_rupiah(summary["total_out_gaji"]))

        data = database.get_saldo_kas(start_date=start_d, end_date=end_d, kategori=kat)
        self.table_kas.setRowCount(len(data))

        for r_idx, r in enumerate(data):
            self.table_kas.setItem(r_idx, 0, QTableWidgetItem(str(r_idx + 1)))
            self.table_kas.setItem(r_idx, 1, QTableWidgetItem(str(r["tanggal"])))
            
            kat_item = QTableWidgetItem(str(r["kategori"] or "-"))
            if r.get("keterangan"):
                kat_item.setToolTip(str(r["keterangan"]))
            self.table_kas.setItem(r_idx, 2, kat_item)

            m_val = float(r["saldo_masuk"] or 0)
            m_item = QTableWidgetItem(styles.format_rupiah(m_val) if m_val > 0 else "-")
            m_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if m_val > 0: m_item.setForeground(Qt.darkGreen)
            self.table_kas.setItem(r_idx, 3, m_item)

            k_val = float(r["saldo_keluar"] or 0)
            k_item = QTableWidgetItem(styles.format_rupiah(k_val) if k_val > 0 else "-")
            k_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if k_val > 0: k_item.setForeground(Qt.red)
            self.table_kas.setItem(r_idx, 4, k_item)

            bal_item = QTableWidgetItem(styles.format_rupiah(r["total_saldo"]))
            bal_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            font = bal_item.font()
            font.setBold(True)
            bal_item.setFont(font)
            self.table_kas.setItem(r_idx, 5, bal_item)

            btn_del = TableDeleteButton("Hapus")
            btn_del.clicked.connect(lambda _, row_data=r: self.hapus_transaksi_kas(row_data))
            self.table_kas.setCellWidget(r_idx, 6, btn_del)

    def add_modal_kas(self):
        dlg = ModalKasDialog(parent=self)
        if dlg.exec():
            self.refresh_all()
            self.data_changed.emit()

    def hapus_transaksi_kas(self, row_data):
        if confirm_dialog(self, "Konfirmasi Hapus Transaksi Kas", 
                          f"Hapus transaksi kas '{row_data['keterangan']}'?\nSeluruh buku kas dan saldo akan dihitung ulang secara otomatis."):
            ok, msg = database.hapus_kas(row_data["id"])
            if ok:
                QMessageBox.information(self, "Sukses", msg)
                self.refresh_all()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Gagal", msg)

    # --------------------------------------------------------------------------
    # TAB 2: PIUTANG MATERIAL (KANTOR & PERUSAHAAN)
    # --------------------------------------------------------------------------
    def setup_tab_semen(self):
        layout = QVBoxLayout(self.tab_semen)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 1. TOP SEGMENTED SLIDE / TAB SWITCHER
        top_switch_frame = QFrame()
        top_switch_frame.setStyleSheet("background-color: transparent;")
        top_switch_layout = QHBoxLayout(top_switch_frame)
        top_switch_layout.setContentsMargins(0, 0, 0, 0)
        top_switch_layout.setSpacing(8)

        self.btn_semen_sub_faktur = QPushButton("Daftar Tagihan Material")
        self.btn_semen_sub_faktur.setCheckable(True)
        self.btn_semen_sub_faktur.setChecked(True)

        self.btn_semen_sub_riwayat = QPushButton("Riwayat Pembayaran Material")
        self.btn_semen_sub_riwayat.setCheckable(True)

        self.semen_sub_group = QButtonGroup(self)
        self.semen_sub_group.setExclusive(True)
        self.semen_sub_group.addButton(self.btn_semen_sub_faktur, 0)
        self.semen_sub_group.addButton(self.btn_semen_sub_riwayat, 1)

        seg_style = f"""
            QPushButton {{
                background-color: #F1F5F9;
                color: {styles.COLOR_TEXT_MUTED};
                border: 1.5px solid {styles.COLOR_BORDER};
                border-radius: 6px;
                padding: 7px 18px;
                font-weight: 600;
                font-size: 12.5px;
            }}
            QPushButton:hover {{
                background-color: #E2E8F0;
                color: {styles.COLOR_TEXT_MAIN};
            }}
            QPushButton:checked {{
                background-color: {styles.COLOR_PRIMARY_LIGHT};
                color: #FFFFFF;
                border-color: {styles.COLOR_PRIMARY_LIGHT};
                font-weight: 700;
            }}
        """
        self.btn_semen_sub_faktur.setStyleSheet(seg_style)
        self.btn_semen_sub_riwayat.setStyleSheet(seg_style)

        top_switch_layout.addWidget(self.btn_semen_sub_faktur)
        top_switch_layout.addWidget(self.btn_semen_sub_riwayat)
        top_switch_layout.addStretch()
        layout.addWidget(top_switch_frame)

        # 2. KPI / SALDO CARDS (Dibawah Switcher)
        kpi_lay = QHBoxLayout()
        kpi_lay.setSpacing(10)
        self.card_semen_tagihan = StatCard("Total Tagihan Material", "Rp 0", "Pembelian Material Masuk", "#1E3A8A")
        self.card_semen_bayar = StatCard("Total Pembayaran Material", "Rp 0", "Sudah Ditransfer/Dibayar", "#059669")
        self.card_semen_hutang = StatCard("Sisa Piutang Material Aktif", "Rp 0", "Kewajiban Supplier Material", "#DC2626")
        kpi_lay.addWidget(self.card_semen_tagihan)
        kpi_lay.addWidget(self.card_semen_bayar)
        kpi_lay.addWidget(self.card_semen_hutang)
        layout.addLayout(kpi_lay)

        # 3. STACKED SLIDES CONTAINER
        self.stack_semen = QStackedWidget()

        # Slide 0: Daftar Faktur / DO Material
        page_faktur = QWidget()
        lay_faktur = QVBoxLayout(page_faktur)
        lay_faktur.setContentsMargins(0, 4, 0, 0)
        lay_faktur.setSpacing(8)

        act_faktur = QHBoxLayout()
        btn_order = PrimaryButton("+ Catat DO / Tagihan Material Manual")
        btn_order.clicked.connect(self.add_order_semen)
        act_faktur.addWidget(btn_order)

        act_faktur.addSpacing(14)
        act_faktur.addWidget(QLabel("Filter Kategori:"))
        self.cb_filter_piutang_kat = QComboBox()
        self.cb_filter_piutang_kat.setView(QListView())
        self.cb_filter_piutang_kat.addItem("Semua Kategori", "all")
        self.cb_filter_piutang_kat.addItem("🏢 Piutang Kantor", "kantor")
        self.cb_filter_piutang_kat.addItem("🏭 Piutang Perusahaan", "perusahaan")
        self.cb_filter_piutang_kat.currentIndexChanged.connect(self.load_semen)
        act_faktur.addWidget(self.cb_filter_piutang_kat)

        self.txt_search_material = QLineEdit()
        self.txt_search_material.setPlaceholderText("Cari No DO / Supplier / Material...")
        self.txt_search_material.textChanged.connect(self.load_semen)
        act_faktur.addWidget(self.txt_search_material)

        act_faktur.addStretch()
        lay_faktur.addLayout(act_faktur)

        lbl_tbl = QLabel("DAFTAR FAKTUR / DO PEMBELIAN MATERIAL SUPPLIER:")
        lbl_tbl.setStyleSheet(f"font-weight: 700; color: {styles.COLOR_PRIMARY_DARK};")
        lay_faktur.addWidget(lbl_tbl)

        self.table_semen_order = ModernTableWidget([
            "No", "No DO/Faktur", "Supplier / Asal", "Material", "Jatuh Tempo", "Total Tagihan", "Sisa Tagihan", "Status", "Aksi"
        ])
        hdr = self.table_semen_order.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        self.table_semen_order.setColumnWidth(0, 38)
        self.table_semen_order.setColumnWidth(1, 160)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_semen_order.setColumnWidth(3, 105)
        self.table_semen_order.setColumnWidth(4, 135)
        self.table_semen_order.setColumnWidth(5, 115)
        self.table_semen_order.setColumnWidth(6, 115)
        self.table_semen_order.setColumnWidth(7, 100)
        hdr.setSectionResizeMode(8, QHeaderView.Fixed)
        self.table_semen_order.setColumnWidth(8, 175)
        self.table_semen_order.cellClicked.connect(self.on_semen_order_cell_clicked)
        self.table_semen_order.cellDoubleClicked.connect(self.on_semen_order_cell_clicked)
        lay_faktur.addWidget(self.table_semen_order)

        self.stack_semen.addWidget(page_faktur)

        # Slide 1: Riwayat Pembayaran / Cicilan Material
        page_riwayat = QWidget()
        lay_riwayat = QVBoxLayout(page_riwayat)
        lay_riwayat.setContentsMargins(0, 4, 0, 0)
        lay_riwayat.setSpacing(8)

        lbl_cicil = QLabel("RIWAYAT PEMBAYARAN / CICILAN MATERIAL KE SUPPLIER (MEMOTONG KAS):")
        lbl_cicil.setStyleSheet(f"font-weight: 700; color: {styles.COLOR_PRIMARY_DARK};")
        lay_riwayat.addWidget(lbl_cicil)

        self.table_cicilan = ModernTableWidget([
            "No", "Tanggal Bayar", "Alokasi DO", "Supplier", "Nominal Dibayar (Rp)", "Metode Bayar", "Keterangan", "Aksi"
        ])
        self.table_cicilan.setColumnWidth(0, 45)
        self.table_cicilan.setColumnWidth(1, 95)
        self.table_cicilan.setColumnWidth(2, 110)
        self.table_cicilan.setColumnWidth(3, 140)
        self.table_cicilan.setColumnWidth(4, 130)
        self.table_cicilan.setColumnWidth(5, 110)
        self.table_cicilan.setColumnWidth(7, 80)
        lay_riwayat.addWidget(self.table_cicilan)

        self.stack_semen.addWidget(page_riwayat)

        layout.addWidget(self.stack_semen)
        self.semen_sub_group.idClicked.connect(self.stack_semen.setCurrentIndex)

    def load_semen(self):
        kat_filter = None
        if hasattr(self, "cb_filter_piutang_kat"):
            val = self.cb_filter_piutang_kat.currentData()
            if val in ("kantor", "perusahaan"):
                kat_filter = val

        search_text = None
        if hasattr(self, "txt_search_material"):
            st = self.txt_search_material.text().strip()
            if st:
                search_text = st

        summary = database.get_ringkasan_hutang_semen(kategori_piutang=kat_filter)
        self.card_semen_tagihan.update_value(styles.format_rupiah(summary["total_tagihan_semen"]))
        self.card_semen_bayar.update_value(styles.format_rupiah(summary["total_dibayar"]))
        self.card_semen_hutang.update_value(styles.format_rupiah(summary["sisa_hutang_semen"]))

        orders = database.get_pembayaran_semen_list(kategori_piutang=kat_filter, search=search_text)
        self._cached_semen_orders = orders
        self.table_semen_order.setRowCount(len(orders))
        today = datetime.now().date()
        for r_idx, o in enumerate(orders):
            self.table_semen_order.setItem(r_idx, 0, QTableWidgetItem(str(r_idx + 1)))
            self.table_semen_order.setItem(r_idx, 1, QTableWidgetItem(str(o["no_order"] or "-")))
            self.table_semen_order.setItem(r_idx, 2, QTableWidgetItem(str(o["supplier"] or "Supplier")))
            
            # 3. Material
            mat_nama = o.get("material_nama") or o.get("material_kode") or "Semen"
            self.table_semen_order.setItem(r_idx, 3, QTableWidgetItem(str(mat_nama)))

            # 4. Jatuh Tempo & Hitungan Mundur (Countdown + Warna Dinamis)
            tgl_dtg_str = str(o.get("tanggal_datang") or o.get("tanggal_order") or "-")
            jt_str = str(o.get("jatuh_tempo") or "").strip()
            if not jt_str:
                try:
                    base_d = datetime.strptime(tgl_dtg_str, "%Y-%m-%d")
                    jt_str = (base_d + timedelta(days=14)).strftime("%Y-%m-%d")
                except Exception:
                    jt_str = tgl_dtg_str
            
            try:
                jt_date = datetime.strptime(jt_str, "%Y-%m-%d").date()
                delta = (jt_date - today).days
            except Exception:
                delta = 999

            sisa = o["sisa_hutang"]
            is_lunas = sisa <= 0
            jt_widget = JatuhTempoBadgeWidget(jt_str, delta, is_lunas)
            self.table_semen_order.setCellWidget(r_idx, 4, jt_widget)

            # 5. Total Tagihan
            tot_item = QTableWidgetItem(styles.format_rupiah(o["total_harga"]))
            tot_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_semen_order.setItem(r_idx, 5, tot_item)

            # 6. Sisa Tagihan
            sisa_item = QTableWidgetItem(styles.format_rupiah(sisa))
            sisa_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_semen_order.setItem(r_idx, 6, sisa_item)

            # 7. Status Lunas
            badge = BadgeLabel("LUNAS" if is_lunas else "BELUM LUNAS", "success" if is_lunas else "danger")
            if not is_lunas:
                badge.setCursor(Qt.PointingHandCursor)
                badge.setToolTip("Klik untuk langsung bayar tagihan ini")
                badge.mousePressEvent = lambda event, row_data=o: self.bayar_order_semen_langsung(row_data)
            self.table_semen_order.setCellWidget(r_idx, 7, badge)

            # 8. Aksi (Detail, Bayar, Hapus)
            act_w = QWidget()
            act_lay = QHBoxLayout(act_w)
            act_lay.setContentsMargins(4, 2, 4, 2)
            act_lay.setSpacing(6)
            act_lay.setAlignment(Qt.AlignCenter)

            btn_detail = TableDetailButton("Detail")
            btn_detail.setToolTip("Lihat rincian lengkap DO & pembelian material")
            btn_detail.clicked.connect(lambda _, row_data=o: self.show_detail_order_semen(row_data))
            act_lay.addWidget(btn_detail)

            if not is_lunas:
                btn_bayar = TablePayButton("Bayar")
                btn_bayar.setToolTip("Bayar tagihan DO ini sekarang")
                btn_bayar.clicked.connect(lambda _, row_data=o: self.bayar_order_semen_langsung(row_data))
                act_lay.addWidget(btn_bayar)

            btn_del = TableDeleteButton("Hapus")
            btn_del.setToolTip("Hapus data order/DO ini")
            btn_del.clicked.connect(lambda _, row_data=o: self.hapus_order_semen(row_data))
            act_lay.addWidget(btn_del)

            self.table_semen_order.setCellWidget(r_idx, 8, act_w)

        cicilan_list = database.get_cicilan_semen_list()
        self.table_cicilan.setRowCount(len(cicilan_list))
        for r_idx, c in enumerate(cicilan_list):
            self.table_cicilan.setItem(r_idx, 0, QTableWidgetItem(str(r_idx + 1)))
            self.table_cicilan.setItem(r_idx, 1, QTableWidgetItem(str(c["tanggal"])))
            self.table_cicilan.setItem(r_idx, 2, QTableWidgetItem(f"DO #{c['pembayaran_semen_id']}" if c['pembayaran_semen_id'] else "Umum"))
            self.table_cicilan.setItem(r_idx, 3, QTableWidgetItem(str(c["supplier"] or "-")))
            
            nom_item = QTableWidgetItem(styles.format_rupiah(c["nominal"]))
            nom_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_cicilan.setItem(r_idx, 4, nom_item)

            self.table_cicilan.setItem(r_idx, 5, QTableWidgetItem(str(c["metode"] or "-")))
            self.table_cicilan.setItem(r_idx, 6, QTableWidgetItem(str(c["keterangan"] or "-")))

            btn_del_c = TableDeleteButton("Hapus")
            btn_del_c.clicked.connect(lambda _, row_data=c: self.hapus_cicilan_semen(row_data))
            self.table_cicilan.setCellWidget(r_idx, 7, btn_del_c)

    def add_order_semen(self):
        dlg = OrderSemenDialog(parent=self)
        if dlg.exec():
            self.refresh_all()
            self.data_changed.emit()

    def add_cicilan_semen(self):
        dlg = CicilanSemenDialog(parent=self)
        if dlg.exec():
            self.refresh_all()
            self.data_changed.emit()

    def on_semen_order_cell_clicked(self, row: int, col: int):
        # Abaikan klik pada kolom Aksi (8) karena tombol di dalamnya sudah menangani aksinya sendiri
        if col == 8:
            return
        if hasattr(self, "_cached_semen_orders") and 0 <= row < len(self._cached_semen_orders):
            order = self._cached_semen_orders[row]
            self.show_detail_order_semen(order)

    def show_detail_order_semen(self, order_data: dict):
        if not order_data:
            return
        dlg = DetailMaterialDODialog(order_data, parent=self)
        dlg.exec()

    def bayar_order_semen_langsung(self, order_data: dict):
        if not order_data:
            return
        if order_data.get("sisa_hutang", 0) <= 0:
            QMessageBox.information(
                self, "Sudah Lunas",
                f"Faktur/DO '{order_data.get('no_order') or 'Semen'}' sudah lunas, tidak ada sisa hutang."
            )
            return
        dlg = CicilanSemenDialog(parent=self, target_order=order_data)
        if dlg.exec():
            self.refresh_all()
            self.data_changed.emit()

    def hapus_order_semen(self, row_data):
        if confirm_dialog(self, "Konfirmasi Hapus Order Semen", f"Hapus faktur semen '{row_data['no_order'] or 'DO'}' ({row_data['jumlah_ton']} Ton)?"):
            ok, msg = database.hapus_order_semen(row_data["id"])
            if ok:
                QMessageBox.information(self, "Sukses", msg)
                self.refresh_all()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Gagal", msg)

    def hapus_cicilan_semen(self, row_data):
        if confirm_dialog(self, "Konfirmasi Hapus Pembayaran Semen", f"Hapus catatan pembayaran semen tanggal {row_data['tanggal']} senilai {styles.format_rupiah(row_data['nominal'])}?"):
            ok, msg = database.hapus_cicilan_semen(row_data["id"])
            if ok:
                QMessageBox.information(self, "Sukses", msg)
                self.refresh_all()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Gagal", msg)

    # --------------------------------------------------------------------------
    # TAB 3: PIUTANG & PEMBAYARAN PROYEK KLIEN
    # --------------------------------------------------------------------------
    def setup_tab_proyek(self):
        layout = QVBoxLayout(self.tab_proyek)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 1. TOP SEGMENTED SLIDE / TAB SWITCHER (Diletakkan di bagian atas saldo)
        top_switch_frame = QFrame()
        top_switch_frame.setStyleSheet("background-color: transparent;")
        top_switch_layout = QHBoxLayout(top_switch_frame)
        top_switch_layout.setContentsMargins(0, 0, 0, 0)
        top_switch_layout.setSpacing(8)

        self.btn_proyek_sub_rekap = QPushButton("Rekapitulasi Piutang per Proyek")
        self.btn_proyek_sub_rekap.setCheckable(True)
        self.btn_proyek_sub_rekap.setChecked(True)

        self.btn_proyek_sub_riwayat = QPushButton("Riwayat Pembayaran / Termin Klien")
        self.btn_proyek_sub_riwayat.setCheckable(True)

        self.proyek_sub_group = QButtonGroup(self)
        self.proyek_sub_group.setExclusive(True)
        self.proyek_sub_group.addButton(self.btn_proyek_sub_rekap, 0)
        self.proyek_sub_group.addButton(self.btn_proyek_sub_riwayat, 1)

        seg_style = f"""
            QPushButton {{
                background-color: #F1F5F9;
                color: {styles.COLOR_TEXT_MUTED};
                border: 1.5px solid {styles.COLOR_BORDER};
                border-radius: 6px;
                padding: 7px 18px;
                font-weight: 600;
                font-size: 12.5px;
            }}
            QPushButton:hover {{
                background-color: #E2E8F0;
                color: {styles.COLOR_TEXT_MAIN};
            }}
            QPushButton:checked {{
                background-color: {styles.COLOR_PRIMARY_LIGHT};
                color: #FFFFFF;
                border-color: {styles.COLOR_PRIMARY_LIGHT};
                font-weight: 700;
            }}
        """
        self.btn_proyek_sub_rekap.setStyleSheet(seg_style)
        self.btn_proyek_sub_riwayat.setStyleSheet(seg_style)

        top_switch_layout.addWidget(self.btn_proyek_sub_rekap)
        top_switch_layout.addWidget(self.btn_proyek_sub_riwayat)
        top_switch_layout.addStretch()
        layout.addWidget(top_switch_frame)

        # 2. KPI / SALDO CARDS (Dibawah Switcher)
        kpi_lay = QHBoxLayout()
        kpi_lay.setSpacing(10)
        self.card_proyek_tagihan = StatCard("Total Nilai Cor Terkirim", "Rp 0", "Total Piutang Dibentuk", "#1E3A8A")
        self.card_proyek_bayar = StatCard("Total Pembayaran Masuk", "Rp 0", "Diterima Dari Klien Proyek", "#059669")
        self.card_proyek_piutang = StatCard("Total Sisa Piutang Klien", "Rp 0", "Tagihan Belum Lunas", "#EA580C")
        kpi_lay.addWidget(self.card_proyek_tagihan)
        kpi_lay.addWidget(self.card_proyek_bayar)
        kpi_lay.addWidget(self.card_proyek_piutang)
        layout.addLayout(kpi_lay)

        # 3. STACKED SLIDES CONTAINER
        self.stack_proyek = QStackedWidget()

        # Slide 0: Rekapitulasi Piutang per Proyek
        page_rekap = QWidget()
        lay_rekap = QVBoxLayout(page_rekap)
        lay_rekap.setContentsMargins(0, 4, 0, 0)
        lay_rekap.setSpacing(8)

        # Filter bar tipe proyek
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)
        filter_bar.addWidget(QLabel("Filter Tipe Proyek:"))
        self.cb_filter_tipe_proyek = QComboBox()
        self.cb_filter_tipe_proyek.setView(QListView())
        self.cb_filter_tipe_proyek.addItem("Semua Proyek", "all")
        self.cb_filter_tipe_proyek.addItem("🏗️ Proyek Luar (Klien Eksternal)", "luar")
        self.cb_filter_tipe_proyek.addItem("🏭 Proyek Dalam (Internal)", "dalam")
        self.cb_filter_tipe_proyek.setFixedWidth(230)
        self.cb_filter_tipe_proyek.currentIndexChanged.connect(self.load_proyek_keuangan)
        filter_bar.addWidget(self.cb_filter_tipe_proyek)
        filter_bar.addStretch()
        lay_rekap.addLayout(filter_bar)

        lbl_rekap_pr = QLabel("REKAPITULASI PIUTANG PER PROYEK:")
        lbl_rekap_pr.setStyleSheet(f"font-weight: 700; color: {styles.COLOR_PRIMARY_DARK};")
        lay_rekap.addWidget(lbl_rekap_pr)

        self.table_rekap_proyek = ModernTableWidget([
            "No", "Nama Proyek", "Tipe", "Lokasi", "Total Volume (m³)", "Total Tagihan (Rp)", "Total Diterima (Rp)", "Sisa Piutang (Rp)", "Status", "Aksi"
        ])
        self.table_rekap_proyek.setColumnWidth(0, 40)
        self.table_rekap_proyek.setColumnWidth(1, 170)
        self.table_rekap_proyek.setColumnWidth(2, 100)
        self.table_rekap_proyek.setColumnWidth(3, 110)
        self.table_rekap_proyek.setColumnWidth(4, 90)
        self.table_rekap_proyek.setColumnWidth(5, 120)
        self.table_rekap_proyek.setColumnWidth(6, 120)
        self.table_rekap_proyek.setColumnWidth(7, 120)
        self.table_rekap_proyek.setColumnWidth(8, 80)
        self.table_rekap_proyek.setColumnWidth(9, 90)
        self.table_rekap_proyek.cellClicked.connect(self.on_proyek_rekap_cell_clicked)
        self.table_rekap_proyek.cellDoubleClicked.connect(self.on_proyek_rekap_cell_clicked)
        lay_rekap.addWidget(self.table_rekap_proyek)

        self.stack_proyek.addWidget(page_rekap)

        # Slide 1: Riwayat Penerimaan Pembayaran Klien
        page_riwayat_pr = QWidget()
        lay_riwayat_pr = QVBoxLayout(page_riwayat_pr)
        lay_riwayat_pr.setContentsMargins(0, 4, 0, 0)
        lay_riwayat_pr.setSpacing(8)

        lbl_det_pr = QLabel("RIWAYAT PENERIMAAN PEMBAYARAN DARI KLIEN (MENAMBAH KAS):")
        lbl_det_pr.setStyleSheet(f"font-weight: 700; color: {styles.COLOR_PRIMARY_DARK};")
        lay_riwayat_pr.addWidget(lbl_det_pr)

        self.table_detail_pembayaran = ModernTableWidget([
            "No", "Tanggal", "Proyek", "Nominal Terima (Rp)", "Metode Penerimaan", "No Bukti", "Keterangan", "Aksi"
        ])
        self.table_detail_pembayaran.setColumnWidth(0, 45)
        self.table_detail_pembayaran.setColumnWidth(1, 95)
        self.table_detail_pembayaran.setColumnWidth(2, 180)
        self.table_detail_pembayaran.setColumnWidth(3, 130)
        self.table_detail_pembayaran.setColumnWidth(4, 120)
        self.table_detail_pembayaran.setColumnWidth(5, 110)
        self.table_detail_pembayaran.setColumnWidth(7, 80)
        lay_riwayat_pr.addWidget(self.table_detail_pembayaran)

        self.stack_proyek.addWidget(page_riwayat_pr)

        layout.addWidget(self.stack_proyek)
        self.proyek_sub_group.idClicked.connect(self.stack_proyek.setCurrentIndex)

    def load_proyek_keuangan(self):
        summary = database.get_ringkasan_piutang_proyek()
        self.card_proyek_tagihan.update_value(styles.format_rupiah(summary["total_tagihan_proyek"]))
        self.card_proyek_bayar.update_value(styles.format_rupiah(summary["total_terbayar"]))
        self.card_proyek_piutang.update_value(styles.format_rupiah(summary["sisa_piutang_proyek"]))

        # Ambil filter tipe proyek
        tipe_filter = None
        if hasattr(self, "cb_filter_tipe_proyek"):
            val = self.cb_filter_tipe_proyek.currentData()
            if val in ("dalam", "luar"):
                tipe_filter = val

        rekap = database.get_rekap_saldo_per_proyek(tipe_proyek=tipe_filter)
        self._cached_proyek_rekap = rekap
        self.table_rekap_proyek.setRowCount(len(rekap))
        for r_idx, r in enumerate(rekap):
            self.table_rekap_proyek.setItem(r_idx, 0, QTableWidgetItem(str(r_idx + 1)))
            self.table_rekap_proyek.setItem(r_idx, 1, QTableWidgetItem(str(r["nama"])))

            # Kolom Tipe Proyek (badge)
            tipe_val = str(r.get("tipe_proyek") or "luar").lower()
            if tipe_val == "dalam":
                tipe_badge = BadgeLabel("Proyek Dalam", "warning")
            else:
                tipe_badge = BadgeLabel("Proyek Luar", "primary")
            self.table_rekap_proyek.setCellWidget(r_idx, 2, tipe_badge)

            self.table_rekap_proyek.setItem(r_idx, 3, QTableWidgetItem(str(r["lokasi"] or "-")))

            vol_item = QTableWidgetItem(f"{styles.format_number(r['total_volume_m3'], 2)}")
            vol_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_rekap_proyek.setItem(r_idx, 4, vol_item)

            tag_item = QTableWidgetItem(styles.format_rupiah(r["total_tagihan"]))
            tag_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_rekap_proyek.setItem(r_idx, 5, tag_item)

            byr_item = QTableWidgetItem(styles.format_rupiah(r["total_bayar"]))
            byr_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_rekap_proyek.setItem(r_idx, 6, byr_item)

            sisa = r["sisa_saldo_piutang"]
            sisa_item = QTableWidgetItem(styles.format_rupiah(sisa))
            sisa_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_rekap_proyek.setItem(r_idx, 7, sisa_item)

            is_lunas = sisa <= 0
            badge = BadgeLabel("Lunas" if is_lunas else "Piutang", "success" if is_lunas else "warning")
            if not is_lunas:
                badge.setCursor(Qt.PointingHandCursor)
                badge.setToolTip("Klik untuk terima pembayaran piutang proyek ini")
                badge.mousePressEvent = lambda event, row_data=r: self.bayar_proyek_langsung(row_data)
            self.table_rekap_proyek.setCellWidget(r_idx, 8, badge)

            if not is_lunas:
                btn_bayar = TablePayButton("Bayar")
                btn_bayar.setToolTip("Terima pembayaran piutang proyek ini sekarang")
                btn_bayar.clicked.connect(lambda _, row_data=r: self.bayar_proyek_langsung(row_data))
                self.table_rekap_proyek.setCellWidget(r_idx, 9, btn_bayar)
            else:
                lbl_lunas = QLabel("-")
                lbl_lunas.setAlignment(Qt.AlignCenter)
                lbl_lunas.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px;")
                self.table_rekap_proyek.setCellWidget(r_idx, 9, lbl_lunas)

        txs = database.get_proyek_pembayaran_list()
        self.table_detail_pembayaran.setRowCount(len(txs))
        for r_idx, t in enumerate(txs):
            self.table_detail_pembayaran.setItem(r_idx, 0, QTableWidgetItem(str(r_idx + 1)))
            self.table_detail_pembayaran.setItem(r_idx, 1, QTableWidgetItem(str(t["tanggal"])))
            self.table_detail_pembayaran.setItem(r_idx, 2, QTableWidgetItem(str(t["proyek_nama"])))

            pm_item = QTableWidgetItem(styles.format_rupiah(t["nominal"]))
            pm_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_detail_pembayaran.setItem(r_idx, 3, pm_item)

            self.table_detail_pembayaran.setItem(r_idx, 4, QTableWidgetItem(str(t["metode"] or "-")))
            self.table_detail_pembayaran.setItem(r_idx, 5, QTableWidgetItem(str(t["nomor_bukti"] or "-")))
            self.table_detail_pembayaran.setItem(r_idx, 6, QTableWidgetItem(str(t["keterangan"] or "-")))

            btn_del_t = TableDeleteButton("Hapus")
            btn_del_t.clicked.connect(lambda _, row_data=t: self.hapus_pembayaran_proyek(row_data))
            self.table_detail_pembayaran.setCellWidget(r_idx, 7, btn_del_t)

    def add_pembayaran_proyek(self):
        dlg = PembayaranProyekDialog(parent=self)
        if dlg.exec():
            self.refresh_all()
            self.data_changed.emit()

    def on_proyek_rekap_cell_clicked(self, row: int, col: int):
        if col == 9:  # Kolom Aksi (sudah bergeser karena kolom Tipe ditambahkan)
            return
        if hasattr(self, "_cached_proyek_rekap") and 0 <= row < len(self._cached_proyek_rekap):
            proyek = self._cached_proyek_rekap[row]
            if proyek.get("sisa_saldo_piutang", 0) > 0:
                self.bayar_proyek_langsung(proyek)

    def bayar_proyek_langsung(self, proyek_data: dict):
        if not proyek_data:
            return
        if proyek_data.get("sisa_saldo_piutang", 0) <= 0:
            QMessageBox.information(
                self, "Sudah Lunas",
                f"Proyek '{proyek_data.get('nama')}' sudah lunas, tidak ada sisa piutang."
            )
            return
        dlg = PembayaranProyekDialog(parent=self, target_proyek=proyek_data)
        if dlg.exec():
            self.refresh_all()
            self.data_changed.emit()

    def hapus_pembayaran_proyek(self, row_data):
        if confirm_dialog(self, "Konfirmasi Hapus Pembayaran Proyek", 
                          f"Hapus pembayaran dari '{row_data['proyek_nama']}' tanggal {row_data['tanggal']} senilai {styles.format_rupiah(row_data['nominal'])}?"):
            ok, msg = database.hapus_pembayaran_proyek(row_data["id"])
            if ok:
                QMessageBox.information(self, "Sukses", msg)
                self.refresh_all()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Gagal", msg)

    # --------------------------------------------------------------------------
    # TAB 4: KAS KANTOR (PENGELUARAN HARIAN NON-SEMEN)
    # --------------------------------------------------------------------------
    def setup_tab_kantor(self):
        layout = QVBoxLayout(self.tab_kantor)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        kpi_lay = QHBoxLayout()
        kpi_lay.setSpacing(10)
        self.card_kantor_total = StatCard("Total Pengeluaran Kas Kantor", "Rp 0", "Seluruh Pengeluaran Harian", "#D97706")
        self.card_kantor_bulan = StatCard("Pengeluaran Bulan Berjalan", "Rp 0", "Konsumsi, ATK, Listrik Bulan Ini", "#EA580C")
        kpi_lay.addWidget(self.card_kantor_total)
        kpi_lay.addWidget(self.card_kantor_bulan)
        layout.addLayout(kpi_lay)

        act_bar = QHBoxLayout()
        btn_kantor = PrimaryButton("+ Catat Nota Pengeluaran Kas Kantor")
        btn_kantor.clicked.connect(self.add_kas_kantor)
        act_bar.addWidget(btn_kantor)
        act_bar.addStretch()
        layout.addLayout(act_bar)

        lbl_tbl = QLabel("DAFTAR NOTA PENGELUARAN HARIAN PLANT (MEMOTONG KAS):")
        lbl_tbl.setStyleSheet(f"font-weight: 700; color: {styles.COLOR_PRIMARY_DARK};")
        layout.addWidget(lbl_tbl)

        self.table_kantor = ModernTableWidget([
            "No", "Tanggal", "No Nota", "Kategori Biaya", "Toko / Penerima", "Unit Armada", "Nominal (Rp)", "Rincian Keterangan", "Aksi"
        ])
        self.table_kantor.setColumnWidth(0, 45)
        self.table_kantor.setColumnWidth(1, 95)
        self.table_kantor.setColumnWidth(2, 110)
        self.table_kantor.setColumnWidth(3, 140)
        self.table_kantor.setColumnWidth(4, 140)
        self.table_kantor.setColumnWidth(5, 130)
        self.table_kantor.setColumnWidth(6, 125)
        self.table_kantor.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch)
        self.table_kantor.setColumnWidth(8, 80)
        layout.addWidget(self.table_kantor)

    def load_kas_kantor(self):
        summary = database.get_ringkasan_kas_kantor()
        self.card_kantor_total.update_value(styles.format_rupiah(summary["total_kas_kantor"]))
        self.card_kantor_bulan.update_value(styles.format_rupiah(summary["total_kas_kantor_bulan_ini"]))

        data = database.get_kas_kantor_list()
        self.table_kantor.setRowCount(len(data))
        for r_idx, r in enumerate(data):
            self.table_kantor.setItem(r_idx, 0, QTableWidgetItem(str(r_idx + 1)))
            self.table_kantor.setItem(r_idx, 1, QTableWidgetItem(str(r["tanggal"])))
            self.table_kantor.setItem(r_idx, 2, QTableWidgetItem(str(r["nomor_nota"] or "-")))
            self.table_kantor.setItem(r_idx, 3, QTableWidgetItem(str(r["kategori"] or "-")))
            self.table_kantor.setItem(r_idx, 4, QTableWidgetItem(str(r["penerima_toko"] or "-")))

            # Unit Armada
            plat_str = f"{r.get('no_plat')} ({r.get('nama_kendaraan') or ''})".strip() if r.get("no_plat") else "-"
            self.table_kantor.setItem(r_idx, 5, QTableWidgetItem(plat_str))

            nom_item = QTableWidgetItem(styles.format_rupiah(r["nominal"]))
            nom_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_kantor.setItem(r_idx, 6, nom_item)

            self.table_kantor.setItem(r_idx, 7, QTableWidgetItem(str(r["keterangan"] or "-")))

            btn_del = TableDeleteButton("Hapus")
            btn_del.clicked.connect(lambda _, row_data=r: self.hapus_kas_kantor(row_data))
            self.table_kantor.setCellWidget(r_idx, 8, btn_del)

    def add_kas_kantor(self):
        dlg = KasKantorDialog(parent=self)
        if dlg.exec():
            self.refresh_all()
            self.data_changed.emit()

    def hapus_kas_kantor(self, row_data):
        if confirm_dialog(self, "Konfirmasi Hapus Pengeluaran", f"Hapus nota pengeluaran '{row_data['keterangan']}' senilai {styles.format_rupiah(row_data['nominal'])}?"):
            ok, msg = database.hapus_kas_kantor(row_data["id"])
            if ok:
                QMessageBox.information(self, "Sukses", msg)
                self.refresh_all()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Gagal", msg)

    # --------------------------------------------------------------------------
    # TAB 5: GAJI KARYAWAN (PAYROLL PEKERJA)
    # --------------------------------------------------------------------------
    def setup_tab_gaji(self):
        layout = QVBoxLayout(self.tab_gaji)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        kpi_lay = QHBoxLayout()
        kpi_lay.setSpacing(10)
        self.card_gaji_total = StatCard("Total Gaji Terbayar", "Rp 0", "Seluruh Penggajian Karyawan", "#7C3AED")
        self.card_gaji_bulan = StatCard("Gaji Bulan Berjalan", "Rp 0", "Upah Supir & Operator Bulan Ini", "#4F46E5")
        kpi_lay.addWidget(self.card_gaji_total)
        kpi_lay.addWidget(self.card_gaji_bulan)
        layout.addLayout(kpi_lay)

        act_bar = QHBoxLayout()
        btn_gaji = PrimaryButton("+ Catat Pembayaran Gaji Karyawan")
        btn_gaji.clicked.connect(self.add_gaji_karyawan)
        act_bar.addWidget(btn_gaji)
        act_bar.addStretch()
        layout.addLayout(act_bar)

        lbl_tbl = QLabel("RIWAYAT PENGGAJIAN KARYAWAN & SUPIR (MEMOTONG KAS):")
        lbl_tbl.setStyleSheet(f"font-weight: 700; color: {styles.COLOR_PRIMARY_DARK};")
        layout.addWidget(lbl_tbl)

        self.table_gaji = ModernTableWidget([
            "No", "Tgl Bayar", "Periode Gaji", "Nama Karyawan", "Jabatan", "Total Dibayar (Rp)", "Metode", "Aksi"
        ])
        hg = self.table_gaji.horizontalHeader()
        hg.setSectionsMovable(False)
        hg.setSectionResizeMode(0, QHeaderView.Fixed)
        hg.setSectionResizeMode(1, QHeaderView.Fixed)
        hg.setSectionResizeMode(2, QHeaderView.Stretch)
        hg.setSectionResizeMode(3, QHeaderView.Fixed)
        hg.setSectionResizeMode(4, QHeaderView.Stretch)
        hg.setSectionResizeMode(5, QHeaderView.Fixed)
        hg.setSectionResizeMode(6, QHeaderView.Fixed)
        hg.setSectionResizeMode(7, QHeaderView.Fixed)

        self.table_gaji.setColumnWidth(0, 40)
        self.table_gaji.setColumnWidth(1, 95)
        self.table_gaji.setColumnWidth(3, 140)
        self.table_gaji.setColumnWidth(5, 135)
        self.table_gaji.setColumnWidth(6, 105)
        self.table_gaji.setColumnWidth(7, 140)

        self.table_gaji.itemDoubleClicked.connect(self.on_table_gaji_double_click)
        layout.addWidget(self.table_gaji)

    def load_gaji(self):
        summary = database.get_ringkasan_gaji_karyawan()
        self.card_gaji_total.update_value(styles.format_rupiah(summary["total_gaji"]))
        self.card_gaji_bulan.update_value(styles.format_rupiah(summary["total_gaji_bulan_ini"]))

        data = database.get_gaji_karyawan_list()
        self.gaji_data_cache = data
        self.table_gaji.setRowCount(len(data))
        for r_idx, r in enumerate(data):
            # 0. No
            it_no = QTableWidgetItem(str(r_idx + 1))
            it_no.setTextAlignment(Qt.AlignCenter)
            self.table_gaji.setItem(r_idx, 0, it_no)

            # 1. Tgl Bayar
            it_tgl = QTableWidgetItem(str(r["tanggal_bayar"]))
            it_tgl.setTextAlignment(Qt.AlignCenter)
            self.table_gaji.setItem(r_idx, 1, it_tgl)

            # 2. Periode Gaji
            it_per = QTableWidgetItem(str(r["periode_gaji"]))
            it_per.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table_gaji.setItem(r_idx, 2, it_per)

            # 3. Nama Karyawan (bold font)
            it_nama = QTableWidgetItem(str(r["nama_karyawan"]))
            f_nama = it_nama.font()
            f_nama.setBold(True)
            it_nama.setFont(f_nama)
            it_nama.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table_gaji.setItem(r_idx, 3, it_nama)

            # 4. Jabatan
            it_jab = QTableWidgetItem(str(r["jabatan"] or "-"))
            it_jab.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table_gaji.setItem(r_idx, 4, it_jab)

            # 5. Total Dibayar (Rp)
            tot_item = QTableWidgetItem(styles.format_rupiah(r["total_dibayar"]))
            f_tot = tot_item.font()
            f_tot.setBold(True)
            tot_item.setFont(f_tot)
            tot_item.setForeground(Qt.darkGreen)
            tot_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_gaji.setItem(r_idx, 5, tot_item)

            # 6. Metode (BadgeLabel centered)
            metode = str(r["metode_bayar"] or "Tunai")
            met_type = "success" if "tunai" in metode.lower() else "primary"
            met_w = QWidget()
            met_lay = QHBoxLayout(met_w)
            met_lay.setContentsMargins(4, 2, 4, 2)
            met_lay.setAlignment(Qt.AlignCenter)
            badge_metode = BadgeLabel(metode, met_type)
            met_lay.addWidget(badge_metode)
            self.table_gaji.setCellWidget(r_idx, 6, met_w)

            # 7. Aksi (Detail & Hapus)
            act_w = QWidget()
            act_lay = QHBoxLayout(act_w)
            act_lay.setContentsMargins(4, 2, 4, 2)
            act_lay.setSpacing(6)
            act_lay.setAlignment(Qt.AlignCenter)

            btn_detail = TableDetailButton("Detail")
            btn_detail.setToolTip("Lihat rincian lengkap slip gaji")
            btn_detail.clicked.connect(lambda _, row_data=r: self.buka_detail_gaji(row_data))
            act_lay.addWidget(btn_detail)

            btn_del = TableDeleteButton("Hapus")
            btn_del.setToolTip("Hapus data penggajian ini")
            btn_del.clicked.connect(lambda _, row_data=r: self.hapus_gaji_karyawan(row_data))
            act_lay.addWidget(btn_del)

            self.table_gaji.setCellWidget(r_idx, 7, act_w)

    def on_table_gaji_double_click(self, item):
        row = item.row()
        if hasattr(self, "gaji_data_cache") and 0 <= row < len(self.gaji_data_cache):
            self.buka_detail_gaji(self.gaji_data_cache[row])

    def buka_detail_gaji(self, row_data):
        if not row_data:
            return
        dlg = DetailGajiDialog(row_data, parent=self)
        dlg.exec()

    def add_gaji_karyawan(self):
        dlg = GajiKaryawanDialog(parent=self)
        if dlg.exec():
            self.refresh_all()
            self.data_changed.emit()

    def hapus_gaji_karyawan(self, row_data):
        if confirm_dialog(self, "Konfirmasi Hapus Gaji", f"Hapus data gaji '{row_data['nama_karyawan']}' periode {row_data['periode_gaji']}?"):
            ok, msg = database.hapus_gaji_karyawan(row_data["id"])
            if ok:
                QMessageBox.information(self, "Sukses", msg)
                self.refresh_all()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Gagal", msg)

    # --------------------------------------------------------------------------
    # REFRESH ALL TABS & SUB-TAB CONTROL
    # --------------------------------------------------------------------------
    def set_current_sub_tab(self, index: int):
        if index >= 5:
            self.tabs.setCurrentIndex(5)
            if hasattr(self, 'tab_kendaraan'):
                k_tab_idx = index - 5
                self.tab_kendaraan.set_active_tab(k_tab_idx)
                self.tab_kendaraan.load_all()
        elif 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)
            if index == 0:
                self.load_ringkasan_kas()
            elif index == 1:
                self.load_semen()
            elif index == 2:
                self.load_proyek_keuangan()
            elif index == 3:
                self.load_kas_kantor()
            elif index == 4:
                self.load_gaji()

    def get_current_sub_tab(self) -> int:
        return self.tabs.currentIndex()

    def refresh_all(self):
        self.load_ringkasan_kas()
        self.load_semen()
        self.load_proyek_keuangan()
        self.load_kas_kantor()
        self.load_gaji()
        if hasattr(self, 'tab_kendaraan'):
            self.tab_kendaraan.load_all()

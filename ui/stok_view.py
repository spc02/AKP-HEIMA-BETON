"""
Stok Material View untuk AKP Beton Desktop Application
Mengelola input stok masuk dengan harga beli satuan, riwayat penerimaan material,
otomatisasi hutang semen supplier, dan rekapitulasi kartu stok & nilai aset persediaan.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, 
    QLabel, QFrame, QTableWidgetItem, QMessageBox, QDialog,
    QLineEdit, QComboBox, QDoubleSpinBox, QAbstractSpinBox, QTextEdit, QDateEdit,
    QGridLayout, QScrollArea, QListView, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor
from components import (
    ModernTableWidget, SectionHeader, ModernDialog, confirm_dialog, BadgeLabel, StatCard,
    PrimaryButton, SecondaryButton, SuccessButton, DangerButton,
    TableEditButton, TableDeleteButton, TableDetailButton
)
import styles
import database
from export_service import fmt_tgl


class KonfirmasiDatangDialog(ModernDialog):
    """Dialog untuk mencatat tanggal kedatangan aktual material ke pabrik"""
    def __init__(self, row_data: dict, parent=None):
        super().__init__("Konfirmasi Material Sudah Datang", parent, min_width=440)
        self.row_data = row_data
        self.init_dialog()

    def init_dialog(self):
        hdr = SectionHeader("📦 Konfirmasi Kedatangan", "Catat tanggal kedatangan material agar otomatis masuk ke stok fisik")
        self.content_layout.addWidget(hdr)

        # Info Box
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        info_lay = QGridLayout(info_frame)
        info_lay.setVerticalSpacing(8)
        info_lay.setHorizontalSpacing(12)

        mat_nama = self.row_data.get("material_nama") or "-"
        satuan = self.row_data.get("material_satuan") or ""
        jml = styles.format_number(self.row_data.get("jumlah") or 0, 2)
        supp = self.row_data.get("supplier") or "-"
        plat = self.row_data.get("no_plat") or "-"
        tgl_order = fmt_tgl(self.row_data.get("tanggal"))

        info_lay.addWidget(QLabel("Material:"), 0, 0)
        info_lay.addWidget(QLabel(f"<b>{mat_nama}</b> ({jml} {satuan})"), 0, 1)

        info_lay.addWidget(QLabel("Supplier / Truk:"), 1, 0)
        info_lay.addWidget(QLabel(f"{supp} / {plat}"), 1, 1)

        info_lay.addWidget(QLabel("Tanggal Order:"), 2, 0)
        info_lay.addWidget(QLabel(f"<b>{tgl_order}</b>"), 2, 1)

        self.content_layout.addWidget(info_frame)

        # Input Tanggal Datang
        input_box = QFrame()
        input_lay = QHBoxLayout(input_box)
        input_lay.setContentsMargins(0, 0, 0, 0)
        input_lay.setSpacing(10)

        lbl_tgl = QLabel("Tanggal Datang:*")
        lbl_tgl.setStyleSheet("font-weight: 700; color: #0F172A; font-size: 13px;")
        input_lay.addWidget(lbl_tgl)

        self.dt_datang = QDateEdit()
        self.dt_datang.setCalendarPopup(True)
        self.dt_datang.setDisplayFormat("yyyy-MM-dd")

        existing_dtg = self.row_data.get("tanggal_datang")
        if existing_dtg and str(existing_dtg).strip() not in ("", "None", "-"):
            try:
                qd = QDate.fromString(str(existing_dtg)[:10], "yyyy-MM-dd")
                if qd.isValid():
                    self.dt_datang.setDate(qd)
                else:
                    self.dt_datang.setDate(QDate.currentDate())
            except Exception:
                self.dt_datang.setDate(QDate.currentDate())
        else:
            self.dt_datang.setDate(QDate.currentDate())

        self.dt_datang.setFixedHeight(34)
        input_lay.addWidget(self.dt_datang, 1)
        self.content_layout.addWidget(input_box)

        lbl_hint = QLabel("💡 Saat dikonfirmasi datang, kuantitas material otomatis MASUK KE STOK FISIK dan laporan keuangan diperbarui menjadi 'Sudah Datang'.")
        lbl_hint.setWordWrap(True)
        lbl_hint.setStyleSheet("font-size: 11px; color: #16A34A; font-weight: 600;")
        self.content_layout.addWidget(lbl_hint)

        self.btn_save.setText("✓ Konfirmasi Sudah Datang & Masuk Stok")
        self.btn_save.clicked.connect(self.save_tanggal_datang)

    def save_tanggal_datang(self):
        tgl_str = self.dt_datang.date().toString("yyyy-MM-dd")
        stok_id = self.row_data.get("id")
        ok, msg = database.set_stok_masuk_tanggal_datang(stok_id, tgl_str)
        if ok:
            self.accept()
        else:
            QMessageBox.critical(self, "Gagal", f"Gagal menyimpan tanggal datang: {msg}")


class StokView(QWidget):
    data_changed = Signal()

    def __init__(self, user_session: dict = None, parent=None):
        super().__init__(parent)
        self.user_session = user_session or {}
        self.materials_list = []
        self.init_ui()

    @property
    def current_user_id(self) -> int:
        """Selalu baca user_id dari session terbaru (dinamis)"""
        uid = self.user_session.get("id")
        return int(uid) if uid else 1

    @property
    def current_user_name(self) -> str:
        """Baca nama user dari session terbaru"""
        return (self.user_session.get("nama_lengkap")
                or self.user_session.get("username")
                or "Anda")

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 16)
        main_layout.setSpacing(12)

        self.tabs = QTabWidget()
        self.tab_input = QWidget()
        self.tab_riwayat = QWidget()
        self.tab_rekap = QWidget()

        self.setup_tab_input()
        self.setup_tab_riwayat()
        self.setup_tab_rekap()

        self.tabs.addTab(self.tab_input, "Input Stok Masuk")
        self.tabs.addTab(self.tab_riwayat, "Riwayat Penerimaan")
        self.tabs.addTab(self.tab_rekap, "Rekap Kartu Stok & Nilai Aset")

        main_layout.addWidget(self.tabs)
        self.refresh_all()

    # --------------------------------------------------------------------------
    # TAB 1: FORM INPUT STOK MASUK
    # --------------------------------------------------------------------------
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
        content_widget.setObjectName("stok_scroll_content")
        content_widget.setStyleSheet("#stok_scroll_content { background: transparent; }")
        layout = QHBoxLayout(content_widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignTop)

        # Left: Form Frame
        form_frame = QFrame()
        form_frame.setProperty("class", "CardWidget")
        form_frame.setMinimumWidth(450)
        form_frame.setMaximumWidth(520)
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(18, 18, 18, 18)
        form_layout.setSpacing(14)

        lbl_f_title = QLabel("FORM PENERIMAAN MATERIAL MASUK (POINT OF SALE)")
        lbl_f_title.setStyleSheet(f"font-weight: 700; color: {styles.COLOR_PRIMARY_DARK}; font-size: 13px;")
        form_layout.addWidget(lbl_f_title)

        grid = QGridLayout()
        grid.setVerticalSpacing(14)
        grid.setHorizontalSpacing(14)
        grid.setContentsMargins(0, 4, 0, 4)
        grid.setColumnMinimumWidth(0, 130)

        # 1. Pilih Material
        grid.addWidget(QLabel("Jenis Material:*"), 0, 0, Qt.AlignVCenter)
        mat_select_layout = QHBoxLayout()
        mat_select_layout.setSpacing(8)
        self.cb_material = QComboBox()
        self.cb_material.setView(QListView())
        self.cb_material.currentIndexChanged.connect(self.on_material_selected)
        mat_select_layout.addWidget(self.cb_material, 1)

        btn_tambah_mat = SecondaryButton("+ Material Baru")
        btn_tambah_mat.setToolTip("Tambah jenis material baru ke database master")
        btn_tambah_mat.clicked.connect(self.buka_dialog_tambah_material)
        mat_select_layout.addWidget(btn_tambah_mat)
        grid.addLayout(mat_select_layout, 0, 1)

        # 2. Tanggal Order
        grid.addWidget(QLabel("Tanggal Order:*"), 1, 0, Qt.AlignVCenter)
        self.dt_tanggal = QDateEdit()
        self.dt_tanggal.setCalendarPopup(True)
        self.dt_tanggal.setDate(QDate.currentDate())
        self.dt_tanggal.setDisplayFormat("yyyy-MM-dd")
        self.dt_tanggal.dateChanged.connect(self.on_tanggal_order_changed)
        grid.addWidget(self.dt_tanggal, 1, 1)

        # 3. Tanggal Jatuh Tempo (Baru & Cepat)
        grid.addWidget(QLabel("Jatuh Tempo:*"), 2, 0, Qt.AlignTop)
        jt_frame = QWidget()
        jt_lay = QVBoxLayout(jt_frame)
        jt_lay.setContentsMargins(0, 0, 0, 0)
        jt_lay.setSpacing(6)

        row_jt_date = QHBoxLayout()
        row_jt_date.setContentsMargins(0, 0, 0, 0)
        row_jt_date.setSpacing(8)

        self.dt_jatuh_tempo = QDateEdit()
        self.dt_jatuh_tempo.setCalendarPopup(True)
        self.dt_jatuh_tempo.setDate(QDate.currentDate().addDays(14))
        self.dt_jatuh_tempo.setDisplayFormat("yyyy-MM-dd")
        self.dt_jatuh_tempo.setFixedWidth(140)
        self.dt_jatuh_tempo.dateChanged.connect(self.update_jatuh_tempo_preview)
        row_jt_date.addWidget(self.dt_jatuh_tempo)

        self.lbl_jt_countdown_hint = QLabel("⏳ 14 hari dari tgl order")
        self.lbl_jt_countdown_hint.setStyleSheet("font-size: 11.5px; font-weight: 600; color: #2563EB; margin-left: 2px;")
        row_jt_date.addWidget(self.lbl_jt_countdown_hint)
        row_jt_date.addStretch()
        jt_lay.addLayout(row_jt_date)

        row_jt_presets = QHBoxLayout()
        row_jt_presets.setContentsMargins(0, 0, 0, 0)
        row_jt_presets.setSpacing(6)

        preset_style = """
            QPushButton {
                background-color: #F1F5F9;
                color: #334155;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
                color: #0F172A;
                border-color: #94A3B8;
            }
            QPushButton:pressed {
                background-color: #CBD5E1;
            }
        """
        btn_jt7 = QPushButton("+7 Hari")
        btn_jt14 = QPushButton("+14 Hari")
        btn_jt30 = QPushButton("+30 Hari")
        btn_jt40 = QPushButton("+40 Hari")
        for b in (btn_jt7, btn_jt14, btn_jt30, btn_jt40):
            b.setStyleSheet(preset_style)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(28)

        btn_jt7.clicked.connect(lambda: self.set_jatuh_tempo_offset(7))
        btn_jt14.clicked.connect(lambda: self.set_jatuh_tempo_offset(14))
        btn_jt30.clicked.connect(lambda: self.set_jatuh_tempo_offset(30))
        btn_jt40.clicked.connect(lambda: self.set_jatuh_tempo_offset(40))

        row_jt_presets.addWidget(btn_jt7)
        row_jt_presets.addWidget(btn_jt14)
        row_jt_presets.addWidget(btn_jt30)
        row_jt_presets.addWidget(btn_jt40)
        row_jt_presets.addStretch()
        jt_lay.addLayout(row_jt_presets)

        grid.addWidget(jt_frame, 2, 1)

        # 4. Jumlah Masuk / Berat Timbang
        self.lbl_jumlah_unit = QLabel("Jumlah Masuk (kg):*")
        grid.addWidget(self.lbl_jumlah_unit, 3, 0, Qt.AlignVCenter)
        self.spin_jumlah = QDoubleSpinBox()
        self.spin_jumlah.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.spin_jumlah.setRange(0.01, 10000000.0)
        self.spin_jumlah.setDecimals(2)
        self.spin_jumlah.valueChanged.connect(self.update_stock_preview)
        grid.addWidget(self.spin_jumlah, 3, 1)

        # 5. Harga Beli Satuan (Rp)
        self.lbl_harga_unit = QLabel("Harga Beli per Satuan (Rp):*")
        grid.addWidget(self.lbl_harga_unit, 4, 0, Qt.AlignVCenter)
        self.spin_harga = QDoubleSpinBox()
        self.spin_harga.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.spin_harga.setRange(0, 1000000000.0)
        self.spin_harga.setDecimals(2)
        self.spin_harga.setSingleStep(50)
        self.spin_harga.valueChanged.connect(self.update_stock_preview)
        grid.addWidget(self.spin_harga, 4, 1)

        # 6. Total Biaya Pembelian
        grid.addWidget(QLabel("Total Nilai Pembelian:"), 5, 0, Qt.AlignVCenter)
        self.lbl_total_biaya = QLabel("Rp 0")
        self.lbl_total_biaya.setStyleSheet(f"font-weight: 800; color: {styles.COLOR_PRIMARY_LIGHT}; font-size: 15px;")
        grid.addWidget(self.lbl_total_biaya, 5, 1)

        # 7. Kategori Piutang Material (Modern Segmented Choice Cards)
        grid.addWidget(QLabel("Kategori Piutang:*"), 6, 0, Qt.AlignVCenter)
        kat_frame = QWidget()
        kat_lay = QHBoxLayout(kat_frame)
        kat_lay.setContentsMargins(0, 0, 0, 0)
        kat_lay.setSpacing(12)

        self.btn_piutang_kantor = QPushButton("🏢  Piutang Kantor")
        self.btn_piutang_kantor.setCheckable(True)
        self.btn_piutang_kantor.setChecked(True)
        self.btn_piutang_kantor.setCursor(Qt.PointingHandCursor)
        self.btn_piutang_kantor.setFixedHeight(40)

        self.btn_piutang_perusahaan = QPushButton("🏭  Piutang Perusahaan")
        self.btn_piutang_perusahaan.setCheckable(True)
        self.btn_piutang_perusahaan.setCursor(Qt.PointingHandCursor)
        self.btn_piutang_perusahaan.setFixedHeight(40)

        self.grp_piutang = QButtonGroup(self)
        self.grp_piutang.setExclusive(True)
        self.grp_piutang.addButton(self.btn_piutang_kantor, 0)
        self.grp_piutang.addButton(self.btn_piutang_perusahaan, 1)

        btn_kantor_style = """
            QPushButton {
                background-color: #F8FAFC;
                color: #334155;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                padding: 4px 10px;
                font-weight: 600;
                font-size: 12px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #EFF6FF;
                border-color: #3B82F6;
                color: #1D4ED8;
            }
            QPushButton:checked {
                background-color: #1E3A8A;
                color: #FFFFFF;
                border: 2px solid #1D4ED8;
                font-weight: 700;
            }
        """
        btn_perusahaan_style = """
            QPushButton {
                background-color: #F8FAFC;
                color: #334155;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                padding: 4px 10px;
                font-weight: 600;
                font-size: 12px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #FFFBEB;
                border-color: #F59E0B;
                color: #B45309;
            }
            QPushButton:checked {
                background-color: #D97706;
                color: #FFFFFF;
                border: 2px solid #B45309;
                font-weight: 700;
            }
        """
        self.btn_piutang_kantor.setStyleSheet(btn_kantor_style)
        self.btn_piutang_perusahaan.setStyleSheet(btn_perusahaan_style)

        kat_lay.addWidget(self.btn_piutang_kantor)
        kat_lay.addWidget(self.btn_piutang_perusahaan)
        kat_lay.addStretch()
        grid.addWidget(kat_frame, 6, 1)

        # 8. Nomor Plat Truk
        grid.addWidget(QLabel("No. Plat Truk:"), 7, 0, Qt.AlignVCenter)
        self.txt_plat = QLineEdit()
        self.txt_plat.setPlaceholderText("Contoh: AA 1234 XY")
        grid.addWidget(self.txt_plat, 7, 1)

        # 9. Supplier / Asal
        grid.addWidget(QLabel("Supplier / Asal:"), 8, 0, Qt.AlignVCenter)
        self.txt_supplier = QLineEdit()
        self.txt_supplier.setPlaceholderText("Contoh: Semen Gresik / Tambang Pasir Progo")
        grid.addWidget(self.txt_supplier, 8, 1)

        # 10. Keterangan
        grid.addWidget(QLabel("Keterangan / DO:"), 9, 0, Qt.AlignVCenter)
        self.txt_keterangan = QLineEdit()
        self.txt_keterangan.toPlainText = self.txt_keterangan.text
        self.txt_keterangan.setPlaceholderText("Catatan pengiriman, nomor surat jalan supplier, dll (opsional)")
        grid.addWidget(self.txt_keterangan, 9, 1)

        form_layout.addLayout(grid)

        # Banner Otomasi Piutang Material
        self.lbl_semen_notice = QLabel("⭐ Otomasi Kasir: Seluruh penerimaan material masuk otomatis dicatat ke menu Piutang Material di Keuangan.")
        self.lbl_semen_notice.setStyleSheet(f"""
            background-color: {styles.COLOR_INFO_BG};
            color: {styles.COLOR_INFO};
            border: 1px solid #BAE6FD;
            border-radius: 6px;
            padding: 8px 10px;
            font-size: 11px;
            font-weight: 600;
        """)
        self.lbl_semen_notice.setVisible(True)
        form_layout.addWidget(self.lbl_semen_notice)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        btn_reset = SecondaryButton("Bersihkan Form")
        btn_reset.clicked.connect(self.reset_form)
        
        btn_simpan = PrimaryButton("Simpan Stok Masuk")
        btn_simpan.clicked.connect(self.simpan_stok_masuk)

        btn_layout.addWidget(btn_reset)
        btn_layout.addWidget(btn_simpan)
        form_layout.addLayout(btn_layout)
        form_layout.addStretch()

        layout.addWidget(form_frame, 3)

        # Right: Info & Live Stock Preview Card
        info_frame = QFrame()
        info_frame.setProperty("class", "CardWidget")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(16, 16, 16, 16)
        info_layout.setSpacing(10)

        lbl_i_title = QLabel("SIMULASI PERUBAHAN STOK & NILAI")
        lbl_i_title.setStyleSheet(f"font-weight: 700; color: {styles.COLOR_PRIMARY_DARK}; font-size: 13px;")
        info_layout.addWidget(lbl_i_title)

        self.lbl_mat_name = QLabel("Material: -")
        self.lbl_mat_name.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {styles.COLOR_TEXT_MAIN};")
        info_layout.addWidget(self.lbl_mat_name)

        self.lbl_cur_stock = QLabel("Stok Saat Ini: 0 kg")
        self.lbl_cur_stock.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 13px;")
        info_layout.addWidget(self.lbl_cur_stock)

        self.lbl_add_stock = QLabel("Penambahan: +0 kg")
        self.lbl_add_stock.setStyleSheet(f"color: {styles.COLOR_SUCCESS}; font-weight: 600; font-size: 13px;")
        info_layout.addWidget(self.lbl_add_stock)

        info_layout.addWidget(QFrame(frameShape=QFrame.HLine))

        self.lbl_after_stock = QLabel("Estimasi Stok Baru: 0 kg")
        self.lbl_after_stock.setStyleSheet(f"color: {styles.COLOR_PRIMARY_LIGHT}; font-weight: 800; font-size: 15px;")
        info_layout.addWidget(self.lbl_after_stock)

        self.lbl_asset_val = QLabel("Nilai Aset Masuk: Rp 0")
        self.lbl_asset_val.setStyleSheet(f"color: {styles.COLOR_SUCCESS}; font-weight: 700; font-size: 13px; margin-top: 6px;")
        info_layout.addWidget(self.lbl_asset_val)

        info_layout.addStretch()
        layout.addWidget(info_frame, 2)

        scroll.setWidget(content_widget)
        tab_layout.addWidget(scroll)

    def on_material_selected(self):
        mat_id = self.cb_material.currentData()
        if not mat_id:
            return
        mat = next((m for m in self.materials_list if m["id"] == mat_id), None)
        if not mat:
            return

        satuan = mat["satuan"]
        self.lbl_jumlah_unit.setText(f"Jumlah Masuk ({satuan}):*")
        self.lbl_harga_unit.setText(f"Harga Beli per {satuan} (Rp):*")
        
        # Set default harga beli dari data master material
        hrg_terbaru = float(mat.get("harga_beli_terbaru") or 0)
        self.spin_harga.setValue(hrg_terbaru)

        # Check apakah Semen
        is_semen = (mat.get("kode") == "MAT-SMN" or "semen" in mat.get("nama", "").lower())
        self.lbl_semen_notice.setVisible(True)
        self.lbl_semen_notice.setText(f"⭐ Otomasi Keuangan: Tagihan pembelian {mat['nama']} otomatis dicatat ke menu Piutang Material.")
        if is_semen and not self.txt_supplier.text():
            self.txt_supplier.setText("PT Semen Indonesia (Gresik)")

        self.update_stock_preview()

    def update_stock_preview(self):
        mat_id = self.cb_material.currentData()
        if not mat_id:
            return
        mat = next((m for m in self.materials_list if m["id"] == mat_id), None)
        if not mat:
            return

        satuan = mat["satuan"]
        cur = database.get_user_stok(self.current_user_id, mat_id)
        add = self.spin_jumlah.value()
        hrg = self.spin_harga.value()
        after = cur + add
        tot_biaya = add * hrg

        self.lbl_total_biaya.setText(styles.format_rupiah(tot_biaya))
        self.lbl_mat_name.setText(f"Material: {mat['nama']} ({mat['kode']})")
        self.lbl_cur_stock.setText(f"Stok Anda Saat Ini: {styles.format_number(cur, 2)} {satuan}")
        self.lbl_add_stock.setText(f"Penambahan: +{styles.format_number(add, 2)} {satuan} (Shared)")
        self.lbl_after_stock.setText(f"Estimasi Stok Anda Baru: {styles.format_number(after, 2)} {satuan}")
        self.lbl_asset_val.setText(f"Nilai Aset Masuk: {styles.format_rupiah(tot_biaya)}")

    def set_jatuh_tempo_offset(self, days: int):
        base_date = self.dt_tanggal.date()
        self.dt_jatuh_tempo.setDate(base_date.addDays(days))
        self.update_jatuh_tempo_preview()

    def on_tanggal_order_changed(self):
        # Otomatis sinkronkan jatuh tempo default +14 hari dari tanggal order
        self.dt_jatuh_tempo.setDate(self.dt_tanggal.date().addDays(14))
        self.update_jatuh_tempo_preview()

    def update_jatuh_tempo_preview(self):
        tgl_ord = self.dt_tanggal.date()
        tgl_jt = self.dt_jatuh_tempo.date()
        days_diff = tgl_ord.daysTo(tgl_jt)
        if days_diff < 0:
            self.lbl_jt_countdown_hint.setText(f"⚠️ Sebelum tgl order ({abs(days_diff)} hari)")
            self.lbl_jt_countdown_hint.setStyleSheet("font-size: 11px; font-weight: 700; color: #DC2626; margin-left: 4px;")
        elif days_diff == 0:
            self.lbl_jt_countdown_hint.setText("⚡ Jatuh tempo hari H order")
            self.lbl_jt_countdown_hint.setStyleSheet("font-size: 11px; font-weight: 700; color: #EA580C; margin-left: 4px;")
        else:
            self.lbl_jt_countdown_hint.setText(f"⏳ {days_diff} hari dari tgl order")
            self.lbl_jt_countdown_hint.setStyleSheet("font-size: 11px; font-weight: 600; color: #2563EB; margin-left: 4px;")

    def reset_form(self):
        self.spin_jumlah.setValue(0.0)
        self.txt_plat.clear()
        self.txt_supplier.clear()
        self.txt_keterangan.clear()
        self.btn_piutang_kantor.setChecked(True)
        self.dt_tanggal.setDate(QDate.currentDate())
        self.dt_jatuh_tempo.setDate(QDate.currentDate().addDays(14))
        self.update_jatuh_tempo_preview()
        self.on_material_selected()

    def simpan_stok_masuk(self):
        mat_id = self.cb_material.currentData()
        tanggal = self.dt_tanggal.date().toString("yyyy-MM-dd")
        jatuh_tempo = self.dt_jatuh_tempo.date().toString("yyyy-MM-dd")
        jumlah = self.spin_jumlah.value()
        harga = self.spin_harga.value()
        plat = self.txt_plat.text().strip()
        supplier = self.txt_supplier.text().strip()
        ket = self.txt_keterangan.toPlainText().strip()
        kat_piutang = "perusahaan" if self.btn_piutang_perusahaan.isChecked() else "kantor"
        kat_label = "Piutang Perusahaan" if kat_piutang == "perusahaan" else "Piutang Kantor"

        if not mat_id:
            QMessageBox.warning(self, "Peringatan", "Silakan pilih jenis material!")
            return
        if jumlah <= 0:
            QMessageBox.warning(self, "Peringatan", "Jumlah masuk harus lebih besar dari 0!")
            return

        try:
            database.tambah_stok_masuk(
                mat_id, tanggal, jumlah, plat, supplier, ket, 
                harga_satuan=harga, kategori_piutang=kat_piutang,
                jatuh_tempo=jatuh_tempo
            )
            
            msg = (
                f"Data stok masuk berhasil disimpan dan stok material bertambah!\n\n"
                f"Tagihan otomatis dicatat sebagai {kat_label} (Jatuh Tempo: {jatuh_tempo}) pada menu Piutang Material di Keuangan Plant."
            )
            
            QMessageBox.information(self, "Berhasil", msg)
            self.reset_form()
            self.refresh_all()
            self.data_changed.emit()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", f"Gagal menyimpan transaksi stok: {str(e)}")

    def buka_dialog_tambah_material(self):
        from ui.master_data_view import MaterialDialog
        dlg = MaterialDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            new_id = getattr(dlg, "created_mat_id", None)
            self.refresh_all()
            if new_id:
                idx = self.cb_material.findData(new_id)
                if idx >= 0:
                    self.cb_material.setCurrentIndex(idx)
            self.data_changed.emit()
            QMessageBox.information(self, "Berhasil", "Jenis material baru berhasil ditambahkan dan langsung dipilih.")

    # --------------------------------------------------------------------------
    # TAB 2: RIWAYAT STOK MASUK
    # --------------------------------------------------------------------------
    def setup_tab_riwayat(self):
        layout = QVBoxLayout(self.tab_riwayat)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Filter Bar
        filter_frame = QFrame()
        filter_frame.setProperty("class", "CardWidget")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(10, 8, 10, 8)
        filter_layout.setSpacing(8)

        filter_layout.addWidget(QLabel("Filter Material:"))
        self.cb_filter_mat = QComboBox()
        self.cb_filter_mat.setView(QListView())
        filter_layout.addWidget(self.cb_filter_mat)

        filter_layout.addWidget(QLabel("Mulai:"))
        self.dt_filter_start = QDateEdit()
        self.dt_filter_start.setCalendarPopup(True)
        self.dt_filter_start.setDate(QDate.currentDate().addMonths(-3))
        self.dt_filter_start.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self.dt_filter_start)

        filter_layout.addWidget(QLabel("Sampai:"))
        self.dt_filter_end = QDateEdit()
        self.dt_filter_end.setCalendarPopup(True)
        self.dt_filter_end.setDate(QDate.currentDate())
        self.dt_filter_end.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self.dt_filter_end)

        btn_apply = PrimaryButton("Filter")
        btn_apply.clicked.connect(self.load_riwayat)
        filter_layout.addWidget(btn_apply)

        btn_reset_f = SecondaryButton("Reset")
        btn_reset_f.clicked.connect(self.reset_filter_riwayat)
        filter_layout.addWidget(btn_reset_f)
        filter_layout.addStretch()

        layout.addWidget(filter_frame)

        self.table_riwayat = ModernTableWidget([
            "No", "Tgl Order", "Tgl Datang", "Material", "Jumlah Masuk", "Satuan", "Harga Satuan", "Total Biaya (Rp)", "No Plat", "Supplier", "Keterangan", "Aksi"
        ])
        self.table_riwayat.setColumnWidth(0, 45)
        self.table_riwayat.setColumnWidth(1, 95)
        self.table_riwayat.setColumnWidth(2, 105)
        self.table_riwayat.setColumnWidth(3, 130)
        self.table_riwayat.setColumnWidth(4, 95)
        self.table_riwayat.setColumnWidth(5, 55)
        self.table_riwayat.setColumnWidth(6, 110)
        self.table_riwayat.setColumnWidth(7, 120)
        self.table_riwayat.setColumnWidth(8, 95)
        self.table_riwayat.setColumnWidth(9, 130)
        # Kolom 10 (Keterangan) = stretch, Kolom 11 (Aksi) = fixed 260 — dihandle ModernTableWidget
        layout.addWidget(self.table_riwayat)

    def load_riwayat(self):
        mat_id = self.cb_filter_mat.currentData()
        start_d = self.dt_filter_start.date().toString("yyyy-MM-dd")
        end_d = self.dt_filter_end.date().toString("yyyy-MM-dd")

        data = database.get_riwayat_stok_masuk(material_id=mat_id if mat_id != -1 else None, 
                                               start_date=start_d, end_date=end_d)
        
        self.table_riwayat.setRowCount(len(data))
        for r_idx, r in enumerate(data):
            self.table_riwayat.setItem(r_idx, 0, QTableWidgetItem(str(r_idx + 1)))
            
            # 1. Tgl Order
            tgl_order_str = fmt_tgl(r.get("tanggal"))
            item_order = QTableWidgetItem(tgl_order_str)
            item_order.setTextAlignment(Qt.AlignCenter)
            self.table_riwayat.setItem(r_idx, 1, item_order)

            # 2. Tgl Datang
            tgl_dtg = r.get("tanggal_datang")
            has_arrived = bool(tgl_dtg and str(tgl_dtg).strip() not in ("", "None", "-"))
            if has_arrived:
                item_dtg = QTableWidgetItem(f"✓ Sudah Datang\n({fmt_tgl(tgl_dtg)})")
                item_dtg.setForeground(QColor("#059669"))
                item_dtg.setToolTip(f"Material telah tiba pada tanggal {fmt_tgl(tgl_dtg)} dan telah masuk ke stok fisik.")
            else:
                item_dtg = QTableWidgetItem("Belum Datang")
                item_dtg.setForeground(QColor("#D97706"))
                item_dtg.setToolTip("Material masih dalam status order (belum tiba di plant)")
            item_dtg.setTextAlignment(Qt.AlignCenter)
            self.table_riwayat.setItem(r_idx, 2, item_dtg)

            # 3. Material
            self.table_riwayat.setItem(r_idx, 3, QTableWidgetItem(str(r["material_nama"])))
            
            # 4. Qty
            qty_item = QTableWidgetItem(f"{styles.format_number(r['jumlah'], 2)}")
            qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_riwayat.setItem(r_idx, 4, qty_item)
            
            # 5. Satuan
            self.table_riwayat.setItem(r_idx, 5, QTableWidgetItem(str(r["material_satuan"])))

            # 6. Harga Satuan
            hrg_item = QTableWidgetItem(styles.format_rupiah(r.get("harga_satuan") or 0))
            hrg_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_riwayat.setItem(r_idx, 6, hrg_item)

            # 7. Total Biaya
            tot_item = QTableWidgetItem(styles.format_rupiah(r.get("total_biaya") or 0))
            tot_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_riwayat.setItem(r_idx, 7, tot_item)

            # 8. No Plat
            self.table_riwayat.setItem(r_idx, 8, QTableWidgetItem(str(r["no_plat"] or "-")))

            # 9. Supplier
            self.table_riwayat.setItem(r_idx, 9, QTableWidgetItem(str(r["supplier"] or "-")))

            # 10. Keterangan
            self.table_riwayat.setItem(r_idx, 10, QTableWidgetItem(str(r["keterangan"] or "-")))

            # 11. Aksi (Datang & Hapus)
            act_w = QWidget()
            act_lay = QHBoxLayout(act_w)
            act_lay.setContentsMargins(4, 2, 4, 2)
            act_lay.setSpacing(6)
            act_lay.setAlignment(Qt.AlignCenter)

            btn_datang = QPushButton("✓ Sudah Datang" if has_arrived else "📦 Datang")
            if has_arrived:
                btn_datang.setStyleSheet("""
                    QPushButton {
                        background-color: #F0FDF4;
                        color: #16A34A;
                        border: 1.5px solid #86EFAC;
                        border-radius: 4px;
                        padding: 4px 8px;
                        font-size: 11px;
                        font-weight: 700;
                        min-width: 90px;
                    }
                    QPushButton:hover {
                        background-color: #DCFCE7;
                        color: #15803D;
                        border-color: #4ADE80;
                    }
                """)
                btn_datang.setToolTip(f"Sudah datang ({fmt_tgl(tgl_dtg)}). Klik jika ingin mengubah tanggal kedatangan.")
            else:
                btn_datang.setStyleSheet("""
                    QPushButton {
                        background-color: #ECFDF5;
                        color: #059669;
                        border: 1.5px solid #10B981;
                        border-radius: 4px;
                        padding: 4px 10px;
                        font-size: 11px;
                        font-weight: 700;
                        min-width: 75px;
                    }
                    QPushButton:hover {
                        background-color: #D1FAE5;
                        color: #047857;
                        border-color: #059669;
                    }
                """)
                btn_datang.setToolTip("Klik jika material ini sudah tiba di plant (akan langsung menambah stok & update laporan)")

            btn_datang.clicked.connect(lambda _, row_data=r: self.buka_dialog_konfirmasi_datang(row_data))
            act_lay.addWidget(btn_datang)

            btn_del = TableDeleteButton("Hapus")
            btn_del.setToolTip("Hapus transaksi stok ini")
            btn_del.clicked.connect(lambda _, row_data=r: self.hapus_stok_masuk(row_data))
            act_lay.addWidget(btn_del)

            self.table_riwayat.setCellWidget(r_idx, 11, act_w)

    def buka_dialog_konfirmasi_datang(self, row_data):
        dlg = KonfirmasiDatangDialog(row_data, parent=self)
        if dlg.exec() == QDialog.Accepted:
            tgl_str = dlg.dt_datang.date().toString("yyyy-MM-dd")
            QMessageBox.information(
                self, "Material Sudah Datang", 
                f"Status material berhasil diubah menjadi SUDAH DATANG ({fmt_tgl(tgl_str)})!\nMaterial resmi masuk ke stok fisik dan laporan telah diperbarui."
            )
            self.refresh_all()
            self.data_changed.emit()

    def reset_filter_riwayat(self):
        self.cb_filter_mat.setCurrentIndex(0)
        self.dt_filter_start.setDate(QDate.currentDate().addMonths(-3))
        self.dt_filter_end.setDate(QDate.currentDate())
        self.load_riwayat()

    def hapus_stok_masuk(self, row_data):
        msg = f"Apakah Anda yakin ingin menghapus catatan stok masuk {row_data['material_nama']} sebanyak {styles.format_number(row_data['jumlah'], 2)} {row_data['material_satuan']}?\n\nStok material dan tagihan hutang terkait (jika semen) akan otomatis disesuaikan kembali."
        if confirm_dialog(self, "Konfirmasi Hapus Stok", msg):
            ok, res_msg = database.hapus_stok_masuk(row_data["id"])
            if ok:
                QMessageBox.information(self, "Sukses", res_msg)
                self.refresh_all()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "Peringatan", res_msg)

    # --------------------------------------------------------------------------
    # TAB 3: REKAP KARTU STOK & NILAI ASET
    # --------------------------------------------------------------------------
    def setup_tab_rekap(self):
        layout = QVBoxLayout(self.tab_rekap)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.card_asset_total = StatCard("Total Nilai Aset Stok Material", "Rp 0", "Valuasi Persediaan Gudang", "#059669")
        layout.addWidget(self.card_asset_total)

        # Banner info sistem stok individual
        banner_info = QLabel(
            "ℹ️  Sistem Stok Individual: Stok masuk (penerimaan) ditambahkan ke SEMUA user secara bersamaan. "
            "Stok keluar (produksi cor) hanya mengurangi stok milik user yang melakukan pengiriman."
        )
        banner_info.setStyleSheet(f"""
            background-color: #EFF6FF;
            color: #1D4ED8;
            border: 1px solid #BFDBFE;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 11.5px;
            font-weight: 500;
        """)
        banner_info.setWordWrap(True)
        layout.addWidget(banner_info)

        lbl_info = QLabel("Rekapitulasi pergerakan fisik material (Total Masuk vs Total Terpakai Cor) dan valuasi nilai aset persediaan:")
        lbl_info.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 12px;")
        layout.addWidget(lbl_info)

        self.lbl_rekap_user = QLabel(f"👤 Stok Anda = stok individual untuk: {self.current_user_name}")
        self.lbl_rekap_user.setStyleSheet(f"color: #0EA5E9; font-size: 12px; font-weight: 600;")
        layout.addWidget(self.lbl_rekap_user)

        self.table_rekap = ModernTableWidget([
            "No", "Kode", "Nama Material", "Satuan", "Total Masuk", "Total Terpakai", 
            "Stok Gudang (Global)", "Stok Anda", "Harga Beli", "Nilai Aset (Rp)", "Status"
        ])
        self.table_rekap.setColumnWidth(0, 40)
        self.table_rekap.setColumnWidth(1, 85)
        self.table_rekap.setColumnWidth(2, 145)
        self.table_rekap.setColumnWidth(3, 58)
        self.table_rekap.setColumnWidth(4, 100)
        self.table_rekap.setColumnWidth(5, 100)
        self.table_rekap.setColumnWidth(6, 120)
        self.table_rekap.setColumnWidth(7, 105)
        self.table_rekap.setColumnWidth(8, 105)
        self.table_rekap.setColumnWidth(9, 120)
        self.table_rekap.setColumnWidth(10, 85)
        layout.addWidget(self.table_rekap)

    def load_rekap(self):
        # Update label nama user
        if hasattr(self, "lbl_rekap_user"):
            self.lbl_rekap_user.setText(f"\U0001f464 Stok Anda = stok individual untuk: {self.current_user_name}")

        data = database.get_rekap_kartu_stok()
        # Ambil stok individual user
        user_stok_map = {}
        try:
            user_stok_list = database.get_all_user_stok(self.current_user_id)
            user_stok_map = {row["material_id"]: float(row["stok_user"] or 0) for row in user_stok_list}
        except Exception:
            pass

        total_val = sum(float(r.get("nilai_aset_stok") or 0) for r in data if float(r.get("stok_saat_ini") or 0) > 0)
        self.card_asset_total.update_value(styles.format_rupiah(total_val))

        self.table_rekap.setRowCount(len(data))
        for r_idx, r in enumerate(data):
            self.table_rekap.setItem(r_idx, 0, QTableWidgetItem(str(r_idx + 1)))
            self.table_rekap.setItem(r_idx, 1, QTableWidgetItem(str(r["kode"])))
            self.table_rekap.setItem(r_idx, 2, QTableWidgetItem(str(r["nama"])))
            self.table_rekap.setItem(r_idx, 3, QTableWidgetItem(str(r["satuan"])))
            
            in_item = QTableWidgetItem(f"{styles.format_number(r['total_masuk'], 2)}")
            in_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_rekap.setItem(r_idx, 4, in_item)

            use_item = QTableWidgetItem(f"{styles.format_number(r['total_terpakai'], 2)}")
            use_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_rekap.setItem(r_idx, 5, use_item)

            # Kolom 6: Stok Global
            stk = float(r["stok_saat_ini"] or 0)
            stk_item = QTableWidgetItem(f"{styles.format_number(stk, 2)}")
            stk_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if stk < 0:
                stk_item.setForeground(Qt.red)
            self.table_rekap.setItem(r_idx, 6, stk_item)

            # Kolom 7: Stok Anda (Individual)
            my_stok = user_stok_map.get(r["id"], stk)
            my_item = QTableWidgetItem(f"{styles.format_number(my_stok, 2)}")
            my_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            font_my = my_item.font()
            font_my.setBold(True)
            my_item.setFont(font_my)
            if my_stok > 0:
                my_item.setForeground(QColor("#0EA5E9"))
            elif my_stok < 0:
                my_item.setForeground(Qt.red)
            self.table_rekap.setItem(r_idx, 7, my_item)

            hrg_item = QTableWidgetItem(styles.format_rupiah(r.get("harga_beli_terbaru") or 0))
            hrg_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_rekap.setItem(r_idx, 8, hrg_item)

            val_item = QTableWidgetItem(styles.format_rupiah(r.get("nilai_aset_stok") or 0))
            val_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            font = val_item.font()
            font.setBold(True)
            val_item.setFont(font)
            self.table_rekap.setItem(r_idx, 9, val_item)

            min_stk = float(r["stok_minimum"] or 0)
            is_crit = stk <= min_stk or stk < 0
            badge = BadgeLabel("KRITIS / MINUS" if is_crit else "AMAN", "danger" if is_crit else "success")
            self.table_rekap.setCellWidget(r_idx, 10, badge)

    def refresh_all(self):
        self.materials_list = database.get_all_materials()
        
        curr_input_mat = self.cb_material.currentData()
        self.cb_material.clear()
        for m in self.materials_list:
            self.cb_material.addItem(f"{m['nama']} ({m['satuan']})", m["id"])
        if curr_input_mat:
            idx = self.cb_material.findData(curr_input_mat)
            if idx >= 0: self.cb_material.setCurrentIndex(idx)

        curr_filter_mat = self.cb_filter_mat.currentData()
        self.cb_filter_mat.clear()
        self.cb_filter_mat.addItem("Semua Material", -1)
        for m in self.materials_list:
            self.cb_filter_mat.addItem(m["nama"], m["id"])
        if curr_filter_mat:
            idx = self.cb_filter_mat.findData(curr_filter_mat)
            if idx >= 0: self.cb_filter_mat.setCurrentIndex(idx)

        self.on_material_selected()
        self.load_riwayat()
        self.load_rekap()

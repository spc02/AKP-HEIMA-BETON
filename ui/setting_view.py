"""
AKP Beton Management System - Setting View
Tampilan Pengaturan Sistem Terpadu (Sub-menu: Akun Pengguna & Manajemen Data)
"""

import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame, QStackedWidget, QFileDialog,
    QInputDialog, QScrollArea, QCheckBox, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QHeaderView, QComboBox, QMenu, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

import styles
import database
import license_manager
from components import (
    PrimaryButton, SecondaryButton, DangerButton, confirm_dialog,
    ModernDialog, ModernTableWidget, BadgeLabel
)


# =============================================================================
# 1. TOMBOL AKSI TABEL (ICON BUTTONS)
# =============================================================================
class TableActionIconButton(QPushButton):
    """Tombol icon kompak elegan untuk aksi baris tabel (Key, Edit, More)"""
    def __init__(self, icon_text: str, tooltip: str = "", parent=None):
        super().__init__(icon_text, parent)
        self.setToolTip(tooltip)
        self.setFixedSize(32, 30)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                font-family: 'Segoe UI Emoji', 'Segoe UI Symbol', sans-serif;
                font-size: 13px;
                color: #475569;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                border-color: #94A3B8;
                color: #0F172A;
            }
            QPushButton:pressed {
                background-color: #E2E8F0;
            }
        """)


# =============================================================================
# 2. DIALOG TAMBAH PENGGUNA BARU
# =============================================================================
class TambahPenggunaDialog(ModernDialog):
    """Dialog pendaftaran pengguna baru dengan pemilihan hak akses (role)"""
    def __init__(self, parent=None):
        super().__init__("Tambah Pengguna Baru", parent, min_width=440)
        self.init_form()

    def init_form(self):
        grid = QGridLayout()
        grid.setSpacing(12)

        grid.addWidget(QLabel("Username:*"), 0, 0)
        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("Contoh: operator1, gudang, kasir")
        grid.addWidget(self.txt_username, 0, 1)

        grid.addWidget(QLabel("Nama Lengkap:*"), 1, 0)
        self.txt_nama = QLineEdit()
        self.txt_nama.setPlaceholderText("Contoh: Budi Santoso")
        grid.addWidget(self.txt_nama, 1, 1)

        grid.addWidget(QLabel("Peran (Role):*"), 2, 0)
        self.cb_role = QComboBox()
        self.cb_role.addItems(["Operator", "Administrator", "Gudang", "Keuangan", "Produksi"])
        grid.addWidget(self.cb_role, 2, 1)

        grid.addWidget(QLabel("Kata Sandi:*"), 3, 0)
        self.txt_pwd = QLineEdit()
        self.txt_pwd.setEchoMode(QLineEdit.Password)
        self.txt_pwd.setPlaceholderText("Minimal 4 karakter")
        grid.addWidget(self.txt_pwd, 3, 1)

        grid.addWidget(QLabel("Konfirmasi Sandi:*"), 4, 0)
        self.txt_pwd2 = QLineEdit()
        self.txt_pwd2.setEchoMode(QLineEdit.Password)
        self.txt_pwd2.setPlaceholderText("Ulangi kata sandi")
        grid.addWidget(self.txt_pwd2, 4, 1)

        grid.addWidget(QLabel("Status Akun:"), 5, 0)
        self.cb_status = QComboBox()
        self.cb_status.addItems(["Aktif", "Nonaktif"])
        grid.addWidget(self.cb_status, 5, 1)

        self.content_layout.addLayout(grid)
        self.btn_save.setText("Simpan Pengguna")
        self.btn_save.clicked.connect(self.save)

    def save(self):
        u = self.txt_username.text().strip()
        n = self.txt_nama.text().strip()
        r = self.cb_role.currentText()
        p = self.txt_pwd.text()
        p2 = self.txt_pwd2.text()
        is_act = 1 if self.cb_status.currentText() == "Aktif" else 0

        if not u or not n or not p:
            QMessageBox.warning(self, "Peringatan", "Username, Nama Lengkap, dan Kata Sandi wajib diisi.")
            return
        if len(p) < 4:
            QMessageBox.warning(self, "Peringatan", "Kata sandi minimal 4 karakter.")
            return
        if p != p2:
            QMessageBox.warning(self, "Peringatan", "Konfirmasi kata sandi tidak cocok.")
            return

        ok, msg = database.create_user(u, p, n, role=r, is_active=is_act)
        if ok:
            QMessageBox.information(self, "Sukses", f"Pengguna '{u}' ({n}) berhasil ditambahkan.")
            self.accept()
        else:
            QMessageBox.critical(self, "Gagal", msg)


# =============================================================================
# 3. DIALOG UBAH KATA SANDI PENGGUNA
# =============================================================================
class UbahPasswordDialog(ModernDialog):
    """Dialog ubah kata sandi pengguna terpilih"""
    def __init__(self, user: dict, parent=None):
        super().__init__(f"Ubah Kata Sandi: {user.get('username')}", parent, min_width=420)
        self.user = user
        self.init_form()

    def init_form(self):
        grid = QGridLayout()
        grid.setSpacing(12)

        grid.addWidget(QLabel("Pengguna:"), 0, 0)
        lbl_info = QLabel(f"<b>{self.user.get('nama_lengkap')}</b> ({self.user.get('username')})")
        lbl_info.setStyleSheet("color: #1E293B; font-size: 13px;")
        grid.addWidget(lbl_info, 0, 1)

        grid.addWidget(QLabel("Kata Sandi Baru:*"), 1, 0)
        self.txt_new_pwd = QLineEdit()
        self.txt_new_pwd.setEchoMode(QLineEdit.Password)
        self.txt_new_pwd.setPlaceholderText("Minimal 4 karakter")
        grid.addWidget(self.txt_new_pwd, 1, 1)

        grid.addWidget(QLabel("Konfirmasi Sandi:*"), 2, 0)
        self.txt_confirm_pwd = QLineEdit()
        self.txt_confirm_pwd.setEchoMode(QLineEdit.Password)
        self.txt_confirm_pwd.setPlaceholderText("Ulangi kata sandi baru")
        grid.addWidget(self.txt_confirm_pwd, 2, 1)

        self.content_layout.addLayout(grid)
        self.btn_save.setText("Simpan Kata Sandi")
        self.btn_save.clicked.connect(self.save)

    def save(self):
        p1 = self.txt_new_pwd.text()
        p2 = self.txt_confirm_pwd.text()

        if len(p1) < 4:
            QMessageBox.warning(self, "Peringatan", "Kata sandi baru minimal 4 karakter.")
            return
        if p1 != p2:
            QMessageBox.warning(self, "Peringatan", "Konfirmasi kata sandi tidak cocok.")
            return

        ok, msg = database.change_user_password(self.user["id"], p1)
        if ok:
            QMessageBox.information(self, "Sukses", f"Kata sandi untuk pengguna '{self.user['username']}' berhasil diperbarui.")
            self.accept()
        else:
            QMessageBox.critical(self, "Gagal", msg)


# =============================================================================
# 4. DIALOG EDIT DATA PENGGUNA
# =============================================================================
class EditPenggunaDialog(ModernDialog):
    """Dialog edit data profil dan hak akses pengguna"""
    def __init__(self, user: dict, parent=None):
        super().__init__(f"Edit Pengguna: {user.get('username')}", parent, min_width=420)
        self.user = user
        self.init_form()

    def init_form(self):
        grid = QGridLayout()
        grid.setSpacing(12)

        grid.addWidget(QLabel("Username:"), 0, 0)
        txt_u = QLineEdit(self.user.get("username", ""))
        txt_u.setReadOnly(True)
        txt_u.setStyleSheet("background-color: #F1F5F9; color: #64748B; font-weight: 600;")
        grid.addWidget(txt_u, 0, 1)

        grid.addWidget(QLabel("Nama Lengkap:*"), 1, 0)
        self.txt_nama = QLineEdit(self.user.get("nama_lengkap", ""))
        grid.addWidget(self.txt_nama, 1, 1)

        grid.addWidget(QLabel("Peran (Role):"), 2, 0)
        self.cb_role = QComboBox()
        self.cb_role.addItems(["Administrator", "Operator", "Gudang", "Keuangan", "Produksi"])
        curr_role = self.user.get("role") or "Operator"
        idx = self.cb_role.findText(curr_role)
        if idx >= 0:
            self.cb_role.setCurrentIndex(idx)
        grid.addWidget(self.cb_role, 2, 1)

        grid.addWidget(QLabel("Status Akun:"), 3, 0)
        self.cb_status = QComboBox()
        self.cb_status.addItems(["Aktif", "Nonaktif"])
        self.cb_status.setCurrentIndex(0 if self.user.get("is_active", 1) else 1)
        grid.addWidget(self.cb_status, 3, 1)

        self.content_layout.addLayout(grid)
        self.btn_save.setText("Simpan Perubahan")
        self.btn_save.clicked.connect(self.save)

    def save(self):
        nama = self.txt_nama.text().strip()
        role = self.cb_role.currentText()
        is_act = 1 if self.cb_status.currentText() == "Aktif" else 0

        if not nama:
            QMessageBox.warning(self, "Peringatan", "Nama lengkap tidak boleh kosong.")
            return

        ok, msg = database.update_user(self.user["id"], nama, is_act, role)
        if ok:
            QMessageBox.information(self, "Sukses", "Data pengguna berhasil diperbarui.")
            self.accept()
        else:
            QMessageBox.critical(self, "Gagal", msg)


# =============================================================================
# 5. SETTING VIEW UTAMA (AKUN PENGGUNA & MANAJEMEN DATA)
# =============================================================================
class SettingView(QWidget):
    data_changed = Signal()
    logout_requested = Signal()

    def __init__(self, user_session: dict = None, parent=None):
        super().__init__(parent)
        self.user_session = user_session or {"username": "admin", "nama_lengkap": "Administrator AKP"}
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # Header Title (Untuk sub-halaman selain Akun Pengguna, misal Data Management)
        self.header_row_widget = QWidget()
        header_row = QHBoxLayout(self.header_row_widget)
        header_row.setContentsMargins(0, 0, 0, 0)
        header_text = QVBoxLayout()
        header_text.setSpacing(2)

        self.lbl_title = QLabel("Pengaturan Sistem")
        self.lbl_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #0F172A;")

        self.lbl_subtitle = QLabel("Kelola akun pengguna, cadangan database, profil usaha, dan lisensi mesin.")
        self.lbl_subtitle.setStyleSheet("font-size: 12.5px; color: #64748B;")

        header_text.addWidget(self.lbl_title)
        header_text.addWidget(self.lbl_subtitle)
        header_row.addLayout(header_text)
        header_row.addStretch()

        main_layout.addWidget(self.header_row_widget)

        # Stacked Widget untuk 2 Sub-halaman: 0 = Akun Pengguna, 1 = Manajemen Data
        self.stacked = QStackedWidget()
        self.user_page = self.create_user_page()
        self.data_page = self.create_data_page()

        self.stacked.addWidget(self.user_page) # Index 0
        self.stacked.addWidget(self.data_page) # Index 1

        main_layout.addWidget(self.stacked, 1)

    def set_sub_tab(self, sub_idx: int):
        """Berpindah sub-halaman: 0 untuk User (Akun Pengguna), 1 untuk Data"""
        if sub_idx in (0, 1):
            self.stacked.setCurrentIndex(sub_idx)
            if sub_idx == 0:
                self.header_row_widget.setVisible(False)
                self.load_users_table()
            else:
                self.header_row_widget.setVisible(True)
                self.lbl_title.setText("Pengaturan & Manajemen Data")
                self.lbl_subtitle.setText("Cadangan data, restore database, profil perusahaan, dan lisensi perangkat.")
                self.load_company_profile()
                self.update_db_info()

    def get_current_sub_tab(self) -> int:
        return self.stacked.currentIndex()

    def refresh_all(self):
        if self.stacked.currentIndex() == 0:
            self.load_users_table()
        else:
            self.load_company_profile()
            self.update_db_info()

    # =========================================================================
    # SUB-HALAMAN 1: AKUN PENGGUNA (SIMPLE, MODERN, TABULAR)
    # =========================================================================
    def create_user_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # 1. Header Section (Sesuai Mockup)
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        icon_box = QLabel("👥")
        icon_box.setStyleSheet("font-size: 26px; padding-right: 2px;")
        header_row.addWidget(icon_box)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        lbl_u_title = QLabel("Akun Pengguna")
        lbl_u_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #0F172A;")
        title_col.addWidget(lbl_u_title)

        lbl_u_desc = QLabel("Kelola akun yang dapat mengakses sistem. Setiap pengguna memiliki hak akses sesuai peran (role).")
        lbl_u_desc.setStyleSheet("font-size: 13px; color: #64748B;")
        title_col.addWidget(lbl_u_desc)

        header_row.addLayout(title_col)
        header_row.addStretch()

        btn_add = PrimaryButton("+ Tambah Pengguna")
        btn_add.setFixedHeight(38)
        btn_add.clicked.connect(self.show_add_user_dialog)
        header_row.addWidget(btn_add)

        layout.addLayout(header_row)

        # 2. Filter Bar (Search + Dropdown Role & Status)
        filter_card = QFrame()
        filter_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        f_lay = QHBoxLayout(filter_card)
        f_lay.setContentsMargins(12, 10, 12, 10)
        f_lay.setSpacing(12)

        self.txt_search_user = QLineEdit()
        self.txt_search_user.setPlaceholderText("🔍  Cari username atau nama pengguna...")
        self.txt_search_user.setClearButtonEnabled(True)
        self.txt_search_user.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 6px;
                padding: 7px 12px;
                font-size: 13px;
                color: #0F172A;
            }
            QLineEdit:focus {
                border-color: #2563EB;
            }
        """)
        self.txt_search_user.textChanged.connect(self.load_users_table)
        f_lay.addWidget(self.txt_search_user, 2)

        self.cb_filter_role = QComboBox()
        self.cb_filter_role.addItems(["Semua Role", "Administrator", "Operator", "Gudang", "Keuangan", "Produksi"])
        self.cb_filter_role.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 6px;
                padding: 7px 14px;
                font-size: 13px;
                color: #0F172A;
                min-width: 135px;
            }
            QComboBox:focus {
                border-color: #2563EB;
            }
        """)
        self.cb_filter_role.currentIndexChanged.connect(self.load_users_table)
        f_lay.addWidget(self.cb_filter_role, 1)

        self.cb_filter_status = QComboBox()
        self.cb_filter_status.addItems(["Semua Status", "Aktif", "Nonaktif"])
        self.cb_filter_status.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 6px;
                padding: 7px 14px;
                font-size: 13px;
                color: #0F172A;
                min-width: 125px;
            }
            QComboBox:focus {
                border-color: #2563EB;
            }
        """)
        self.cb_filter_status.currentIndexChanged.connect(self.load_users_table)
        f_lay.addWidget(self.cb_filter_status, 1)

        layout.addWidget(filter_card)

        # 3. Modern Table Widget (7 Kolom Sesuai Mockup)
        self.table_users = ModernTableWidget([
            "No", "Username", "Nama Lengkap", "Role", "Status", "Terakhir Masuk", "Aksi"
        ])
        hg = self.table_users.horizontalHeader()
        hg.setSectionsMovable(False)
        hg.setSectionResizeMode(0, QHeaderView.Fixed)
        hg.setSectionResizeMode(1, QHeaderView.Fixed)
        hg.setSectionResizeMode(2, QHeaderView.Stretch)
        hg.setSectionResizeMode(3, QHeaderView.Fixed)
        hg.setSectionResizeMode(4, QHeaderView.Fixed)
        hg.setSectionResizeMode(5, QHeaderView.Fixed)
        hg.setSectionResizeMode(6, QHeaderView.Fixed)

        self.table_users.setColumnWidth(0, 50)
        self.table_users.setColumnWidth(1, 130)
        self.table_users.setColumnWidth(3, 135)
        self.table_users.setColumnWidth(4, 125)
        self.table_users.setColumnWidth(5, 165)
        self.table_users.setColumnWidth(6, 145)

        layout.addWidget(self.table_users, 1)

        # 4. Pagination / Info Row
        pag_row = QHBoxLayout()
        self.lbl_count_user = QLabel("Menampilkan 0 pengguna")
        self.lbl_count_user.setStyleSheet("font-size: 12.5px; color: #64748B; font-weight: 500;")
        pag_row.addWidget(self.lbl_count_user)
        pag_row.addStretch()

        btn_prev = QPushButton("<")
        btn_prev.setFixedSize(28, 28)
        btn_prev.setEnabled(False)
        btn_prev.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 4px; color: #64748B; font-weight: 700; font-size: 12px; padding: 0px; margin: 0px;")
        pag_row.addWidget(btn_prev)

        btn_p1 = QPushButton("1")
        btn_p1.setFixedSize(28, 28)
        btn_p1.setStyleSheet("background-color: #2563EB; border: 1px solid #2563EB; border-radius: 4px; color: #FFFFFF; font-weight: 700; font-size: 12px; padding: 0px; margin: 0px;")
        pag_row.addWidget(btn_p1)

        btn_next = QPushButton(">")
        btn_next.setFixedSize(28, 28)
        btn_next.setEnabled(False)
        btn_next.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 4px; color: #64748B; font-weight: 700; font-size: 12px; padding: 0px; margin: 0px;")
        pag_row.addWidget(btn_next)

        layout.addLayout(pag_row)

        # 5. Keterangan Aksi Legend Card (Sesuai Mockup)
        legend_frame = QFrame()
        legend_frame.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        leg_lay = QHBoxLayout(legend_frame)
        leg_lay.setContentsMargins(16, 10, 16, 10)
        leg_lay.setSpacing(26)

        lbl_leg_h = QLabel("<b>ℹ️  Keterangan Aksi:</b>")
        lbl_leg_h.setStyleSheet("color: #0F172A; font-size: 12.5px;")
        leg_lay.addWidget(lbl_leg_h)

        lbl_k1 = QLabel("🔑  Ubah Kata Sandi")
        lbl_k1.setStyleSheet("color: #475569; font-size: 12px; font-weight: 600;")
        leg_lay.addWidget(lbl_k1)

        lbl_k2 = QLabel("✏️  Edit Data")
        lbl_k2.setStyleSheet("color: #475569; font-size: 12px; font-weight: 600;")
        leg_lay.addWidget(lbl_k2)

        lbl_k3 = QLabel("⋮  Menu Lainnya (Nonaktifkan / Hapus)")
        lbl_k3.setStyleSheet("color: #475569; font-size: 12px; font-weight: 600;")
        leg_lay.addWidget(lbl_k3)

        leg_lay.addStretch()
        layout.addWidget(legend_frame)

        return page

    def create_role_badge(self, role: str) -> QWidget:
        """Membuat pill badge peran (role) sesuai palet warna profesional"""
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setAlignment(Qt.AlignCenter)

        r_lower = (role or "Operator").lower()
        if "admin" in r_lower:
            bg, fg, border = "#EFF6FF", "#2563EB", "#BFDBFE"
        elif "gudang" in r_lower:
            bg, fg, border = "#ECFDF5", "#059669", "#A7F3D0"
        elif "keuangan" in r_lower:
            bg, fg, border = "#F5F3FF", "#7C3AED", "#DDD6FE"
        elif "produksi" in r_lower:
            bg, fg, border = "#FFFBEB", "#D97706", "#FDE68A"
        else: # Operator
            bg, fg, border = "#F1F5F9", "#475569", "#CBD5E1"

        lbl = QLabel(role or "Operator")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFixedHeight(24)
        lbl.setStyleSheet(f"""
            background-color: {bg};
            color: {fg};
            border: 1px solid {border};
            border-radius: 12px;
            padding: 2px 14px;
            font-size: 11.5px;
            font-weight: 700;
        """)
        lay.addWidget(lbl)
        return w

    def create_status_badge(self, is_active: int) -> QWidget:
        """Membuat pill badge status aktif/nonaktif dengan indikator bulatan"""
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setAlignment(Qt.AlignCenter)

        if is_active:
            bg, fg, border, text = "#ECFDF5", "#059669", "#A7F3D0", "●  Aktif"
        else:
            bg, fg, border, text = "#FEF2F2", "#DC2626", "#FECACA", "●  Nonaktif"

        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFixedHeight(24)
        lbl.setStyleSheet(f"""
            background-color: {bg};
            color: {fg};
            border: 1px solid {border};
            border-radius: 12px;
            padding: 2px 14px;
            font-size: 11.5px;
            font-weight: 700;
        """)
        lay.addWidget(lbl)
        return w

    def load_users_table(self):
        """Muat daftar pengguna ke tabel dengan filter pencarian, role, dan status."""
        try:
            users = database.get_all_users()
            query = self.txt_search_user.text().strip().lower() if hasattr(self, "txt_search_user") else ""
            f_role = self.cb_filter_role.currentText() if hasattr(self, "cb_filter_role") else "Semua Role"
            f_status = self.cb_filter_status.currentText() if hasattr(self, "cb_filter_status") else "Semua Status"

            filtered = []
            for u in users:
                u_name = str(u.get("username") or "").lower()
                n_lengkap = str(u.get("nama_lengkap") or "").lower()
                r = str(u.get("role") or "Operator")
                act = u.get("is_active", 1)

                if query and (query not in u_name and query not in n_lengkap):
                    continue
                if f_role != "Semua Role" and r.lower() != f_role.lower():
                    continue
                if f_status == "Aktif" and not act:
                    continue
                if f_status == "Nonaktif" and act:
                    continue

                filtered.append(u)

            self.table_users.setRowCount(len(filtered))
            for idx, u in enumerate(filtered):
                # 0. No
                it_no = QTableWidgetItem(str(idx + 1))
                it_no.setTextAlignment(Qt.AlignCenter)
                self.table_users.setItem(idx, 0, it_no)

                # 1. Username
                it_un = QTableWidgetItem(str(u.get("username", "")))
                it_un.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.table_users.setItem(idx, 1, it_un)

                # 2. Nama Lengkap
                it_nl = QTableWidgetItem(str(u.get("nama_lengkap", "")))
                it_nl.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.table_users.setItem(idx, 2, it_nl)

                # 3. Role Badge
                self.table_users.setCellWidget(idx, 3, self.create_role_badge(u.get("role") or "Operator"))

                # 4. Status Badge
                self.table_users.setCellWidget(idx, 4, self.create_status_badge(u.get("is_active", 1)))

                # 5. Terakhir Masuk
                last_l = str(u.get("last_login") or "-")
                if len(last_l) >= 16:
                    try:
                        dt = datetime.strptime(last_l[:19], "%Y-%m-%d %H:%M:%S")
                        last_l = dt.strftime("%d-%m-%Y %H:%M")
                    except Exception:
                        pass
                it_ll = QTableWidgetItem(last_l)
                it_ll.setTextAlignment(Qt.AlignCenter)
                self.table_users.setItem(idx, 5, it_ll)

                # 6. Aksi (3 Icon Buttons)
                act_w = QWidget()
                act_lay = QHBoxLayout(act_w)
                act_lay.setContentsMargins(4, 2, 4, 2)
                act_lay.setSpacing(6)
                act_lay.setAlignment(Qt.AlignCenter)

                btn_pwd = TableActionIconButton("🔑", "Ubah Kata Sandi")
                btn_pwd.clicked.connect(lambda _, user=u: self.show_change_pwd_dialog(user))
                act_lay.addWidget(btn_pwd)

                btn_edit = TableActionIconButton("✏", "Edit Data Pengguna")
                btn_edit.clicked.connect(lambda _, user=u: self.show_edit_user_dialog(user))
                act_lay.addWidget(btn_edit)

                btn_more = TableActionIconButton("⋮", "Menu Lainnya (Nonaktifkan / Hapus)")
                btn_more.clicked.connect(lambda _, b=btn_more, user=u: self.show_user_context_menu(b, user))
                act_lay.addWidget(btn_more)

                self.table_users.setCellWidget(idx, 6, act_w)

            if hasattr(self, "lbl_count_user"):
                total_all = len(users)
                cur_len = len(filtered)
                self.lbl_count_user.setText(f"Menampilkan 1 - {cur_len} dari {total_all} pengguna" if cur_len > 0 else "Tidak ada pengguna yang cocok")

        except Exception as e:
            print("Error loading users table:", e)

    def show_add_user_dialog(self):
        """Buka dialog pendaftaran pengguna baru"""
        dlg = TambahPenggunaDialog(parent=self)
        if dlg.exec():
            self.load_users_table()
            self.data_changed.emit()

    def show_change_pwd_dialog(self, user: dict):
        """Buka dialog ganti password pengguna"""
        dlg = UbahPasswordDialog(user, parent=self)
        if dlg.exec():
            self.load_users_table()

    def show_edit_user_dialog(self, user: dict):
        """Buka dialog edit profil pengguna"""
        dlg = EditPenggunaDialog(user, parent=self)
        if dlg.exec():
            self.load_users_table()
            self.data_changed.emit()

    def show_user_context_menu(self, btn: QPushButton, user: dict):
        """Tampilkan dropdown menu lainnya untuk user terpilih"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 4px;
                font-size: 12.5px;
            }
            QMenu::item {
                padding: 6px 18px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #EFF6FF;
                color: #1E3A8A;
            }
        """)
        is_active = user.get("is_active", 1)
        toggle_text = "Nonaktifkan Akun" if is_active else "Aktifkan Akun"
        action_toggle = menu.addAction(toggle_text)
        action_del = menu.addAction("Hapus Akun Pengguna")

        action = menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))
        if action == action_toggle:
            new_status = 0 if is_active else 1
            ok, msg = database.update_user(user["id"], user["nama_lengkap"], new_status, user.get("role", "Operator"))
            if ok:
                self.load_users_table()
            else:
                QMessageBox.warning(self, "Peringatan", msg)
        elif action == action_del:
            self.delete_user_by_dict(user)

    def delete_user_by_dict(self, user: dict):
        """Hapus user yang dipilih"""
        if user["id"] == self.user_session.get("id"):
            QMessageBox.warning(self, "Tidak Diizinkan", "Anda tidak dapat menghapus akun yang sedang Anda gunakan.")
            return

        confirm = QMessageBox.question(
            self, "Konfirmasi Hapus Pengguna",
            f"Apakah Anda yakin ingin menghapus akun:\n\n"
            f"Username: {user['username']}\nNama: {user['nama_lengkap']}\n\n"
            f"⚠️  Data stok individual user ini juga akan ikut terhapus.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            ok, msg = database.delete_user(user["id"])
            if ok:
                QMessageBox.information(self, "Sukses", msg)
                self.load_users_table()
            else:
                QMessageBox.warning(self, "Gagal", msg)


    # =========================================================================
    # SUB-HALAMAN 2: DATA (BACKUP, PROFIL, LISENSI)
    # =========================================================================
    def create_data_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 1. Card Backup & Restore Database
        db_card = QFrame()
        db_card.setProperty("class", "CardWidget")
        db_layout = QVBoxLayout(db_card)
        db_layout.setContentsMargins(20, 18, 20, 18)
        db_layout.setSpacing(12)

        lbl_db_h = QLabel("CADANGAN & PEMULIHAN DATABASE (BACKUP & RESTORE)")
        lbl_db_h.setStyleSheet("font-size: 13.5px; font-weight: 800; color: #1E293B;")
        db_layout.addWidget(lbl_db_h)

        self.lbl_db_file = QLabel("Memuat info database...")
        self.lbl_db_file.setStyleSheet("font-size: 12px; color: #64748B; font-family: monospace;")
        db_layout.addWidget(self.lbl_db_file)

        btn_db_row = QHBoxLayout()
        btn_db_row.setSpacing(10)

        btn_backup = PrimaryButton("Backup Database Sekarang (.db)")
        btn_backup.setFixedHeight(38)
        btn_backup.clicked.connect(self.do_backup)
        btn_db_row.addWidget(btn_backup)

        btn_restore = SecondaryButton("Pulihkan Database (Restore .db)")
        btn_restore.setFixedHeight(38)
        btn_restore.clicked.connect(self.do_restore)
        btn_db_row.addWidget(btn_restore)

        btn_db_row.addStretch()
        db_layout.addLayout(btn_db_row)
        layout.addWidget(db_card)

        # 2. Card Reset Data Aplikasi
        reset_card = QFrame()
        reset_card.setProperty("class", "CardWidget")
        reset_layout = QVBoxLayout(reset_card)
        reset_layout.setContentsMargins(20, 18, 20, 18)
        reset_layout.setSpacing(12)

        lbl_reset_h = QLabel("RESET DATA APLIKASI")
        lbl_reset_h.setStyleSheet("font-size: 13.5px; font-weight: 800; color: #DC2626;")
        reset_layout.addWidget(lbl_reset_h)

        lbl_reset_desc = QLabel(
            "Pilih opsi reset data sesuai kebutuhan Anda. "
            "Sistem akan secara otomatis membuat file cadangan (backup) sebelum tindakan reset dijalankan "
            "sehingga data lama tetap tersimpan aman."
        )
        lbl_reset_desc.setWordWrap(True)
        lbl_reset_desc.setStyleSheet("font-size: 12px; color: #64748B; line-height: 1.4;")
        reset_layout.addWidget(lbl_reset_desc)

        btn_row_reset = QHBoxLayout()
        btn_row_reset.setSpacing(10)

        btn_reset_transaksi = DangerButton("⚠️ Kosongkan Riwayat Transaksi (Stok & Kas 0)")
        btn_reset_transaksi.setFixedHeight(38)
        btn_reset_transaksi.clicked.connect(self.do_reset_transaksi)
        btn_row_reset.addWidget(btn_reset_transaksi)

        btn_reset_factory = DangerButton("🔄 Reset Total Database (Kondisi Awal Pabrik)")
        btn_reset_factory.setFixedHeight(38)
        btn_reset_factory.clicked.connect(self.do_reset_database_factory)
        btn_row_reset.addWidget(btn_reset_factory)

        btn_seed_ringkas = SecondaryButton("📥 Muat Data Sampel Ringkas (Sedikit Saja)")
        btn_seed_ringkas.setFixedHeight(38)
        btn_seed_ringkas.clicked.connect(self.do_seed_data_ringkas)
        btn_row_reset.addWidget(btn_seed_ringkas)

        btn_row_reset.addStretch()
        reset_layout.addLayout(btn_row_reset)

        layout.addWidget(reset_card)

        # 3. Card Profil Perusahaan
        corp_card = QFrame()
        corp_card.setProperty("class", "CardWidget")
        corp_layout = QVBoxLayout(corp_card)
        corp_layout.setContentsMargins(20, 18, 20, 18)
        corp_layout.setSpacing(10)

        lbl_corp_h = QLabel("PROFIL USAHA & BATCHING PLANT")
        lbl_corp_h.setStyleSheet("font-size: 13.5px; font-weight: 800; color: #1E293B;")
        corp_layout.addWidget(lbl_corp_h)

        corp_layout.addWidget(QLabel("Nama Perusahaan / Plant:"))
        self.txt_corp_name = QLineEdit()
        corp_layout.addWidget(self.txt_corp_name)

        corp_layout.addWidget(QLabel("Alamat Operasional:"))
        self.txt_corp_address = QLineEdit()
        corp_layout.addWidget(self.txt_corp_address)

        row_c2 = QHBoxLayout()
        col_phone = QVBoxLayout()
        col_phone.addWidget(QLabel("Telepon / Kontak:"))
        self.txt_corp_phone = QLineEdit()
        col_phone.addWidget(self.txt_corp_phone)
        row_c2.addLayout(col_phone)

        col_pj = QVBoxLayout()
        col_pj.addWidget(QLabel("Penanggung Jawab Lapangan:"))
        self.txt_corp_pj = QLineEdit()
        col_pj.addWidget(self.txt_corp_pj)
        row_c2.addLayout(col_pj)
        corp_layout.addLayout(row_c2)

        # Row Bank Details untuk Invoice
        row_bank = QHBoxLayout()
        col_b_name = QVBoxLayout()
        col_b_name.addWidget(QLabel("Nama Bank (Invoice):"))
        self.txt_bank_name = QLineEdit()
        col_b_name.addWidget(self.txt_bank_name)
        row_bank.addLayout(col_b_name)

        col_b_acc = QVBoxLayout()
        col_b_acc.addWidget(QLabel("Nomor Rekening (Invoice):"))
        self.txt_bank_acc = QLineEdit()
        col_b_acc.addWidget(self.txt_bank_acc)
        row_bank.addLayout(col_b_acc)

        col_b_holder = QVBoxLayout()
        col_b_holder.addWidget(QLabel("Atas Nama Rekening:"))
        self.txt_bank_holder = QLineEdit()
        col_b_holder.addWidget(self.txt_bank_holder)
        row_bank.addLayout(col_b_holder)
        corp_layout.addLayout(row_bank)

        # Row Penandatangan & Kota Invoice
        row_sig = QHBoxLayout()
        col_city = QVBoxLayout()
        col_city.addWidget(QLabel("Kota Dokumen (Invoice):"))
        self.txt_inv_city = QLineEdit()
        col_city.addWidget(self.txt_inv_city)
        row_sig.addLayout(col_city)

        col_signer = QVBoxLayout()
        col_signer.addWidget(QLabel("Nama Penandatangan (Invoice):"))
        self.txt_inv_signer = QLineEdit()
        col_signer.addWidget(self.txt_inv_signer)
        row_sig.addLayout(col_signer)
        corp_layout.addLayout(row_sig)

        btn_save_corp = PrimaryButton("Simpan Profil Perusahaan & Bank")
        btn_save_corp.setFixedHeight(36)
        btn_save_corp.clicked.connect(self.save_company_profile)
        corp_layout.addWidget(btn_save_corp)
        layout.addWidget(corp_card)

        # 3. Card Lisensi Mesin & Reset
        lic_card = QFrame()
        lic_card.setProperty("class", "CardWidget")
        lic_layout = QVBoxLayout(lic_card)
        lic_layout.setContentsMargins(20, 18, 20, 18)
        lic_layout.setSpacing(10)

        lbl_lic_h = QLabel("STATUS LISENSI PERANGKAT KERAS (HARDWARE LOCK)")
        lbl_lic_h.setStyleSheet("font-size: 13.5px; font-weight: 800; color: #1E293B;")
        lic_layout.addWidget(lbl_lic_h)

        mid = license_manager.get_machine_id()
        lbl_mid_desc = QLabel(f"Machine ID Komputer: <b>{mid}</b>")
        lbl_mid_desc.setStyleSheet("font-size: 12.5px; color: #334155; font-family: monospace;")
        lic_layout.addWidget(lbl_mid_desc)

        is_act, lic_msg, lic_meta = license_manager.is_activated()
        lbl_lic_stat = QLabel(f"Status Lisensi: <span style='color: #059669; font-weight: bold;'>{lic_msg}</span>")
        lbl_lic_stat.setStyleSheet("font-size: 12.5px;")
        lic_layout.addWidget(lbl_lic_stat)

        lic_btn_row = QHBoxLayout()
        lic_btn_row.setSpacing(10)

        btn_copy_mid = SecondaryButton("Salin Machine ID")
        btn_copy_mid.setFixedHeight(34)
        btn_copy_mid.clicked.connect(lambda: QMessageBox.information(self, "Disalin", f"Machine ID disalin:\n{mid}"))
        lic_btn_row.addWidget(btn_copy_mid)

        btn_reset_lic = DangerButton("Reset Lisensi Komputer")
        btn_reset_lic.setFixedHeight(34)
        btn_reset_lic.clicked.connect(self.do_reset_license)
        lic_btn_row.addWidget(btn_reset_lic)

        lic_btn_row.addStretch()
        lic_layout.addLayout(lic_btn_row)
        layout.addWidget(lic_card)

        layout.addStretch()
        scroll.setWidget(page)
        return scroll

    def update_db_info(self):
        db_path = database.get_db_path()
        if os.path.exists(db_path):
            sz = os.path.getsize(db_path) / 1024
            self.lbl_db_file.setText(f"File: {db_path} ({sz:.1f} KB)")
        else:
            self.lbl_db_file.setText(f"File: {db_path} (Belum ada)")

    def do_backup(self):
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"akp_beton_backup_{now_str}.db"
        dest_path, _ = QFileDialog.getSaveFileName(
            self, "Pilih Lokasi Backup Database", default_name, "SQLite Database (*.db)"
        )
        if dest_path:
            ok, msg = database.backup_db(dest_path)
            if ok:
                QMessageBox.information(self, "Backup Berhasil", msg)
            else:
                QMessageBox.critical(self, "Backup Gagal", msg)

    def do_restore(self):
        src_path, _ = QFileDialog.getOpenFileName(
            self, "Pilih File Cadangan Database (.db)", "", "SQLite Database (*.db)"
        )
        if not src_path:
            return

        msg = (
            "PERINGATAN:\n\n"
            "Memulihkan database akan menimpa seluruh data transaksi saat ini dengan file cadangan.\n\n"
            "Apakah Anda yakin ingin melanjutkan pemulihan database?"
        )
        if confirm_dialog(self, "Konfirmasi Pemulihan Database", msg):
            ok, msg = database.restore_db(src_path)
            if ok:
                QMessageBox.information(self, "Pemulihan Berhasil", msg + "\nSistem akan memuat ulang data terbaru.")
                self.data_changed.emit()
            else:
                QMessageBox.critical(self, "Gagal", msg)

    def load_company_profile(self):
        self.txt_corp_name.setText(database.get_pengaturan("nama_perusahaan", "AKP BATCHING PLANT"))
        self.txt_corp_address.setText(database.get_pengaturan("alamat_perusahaan", "Jl. Raya Magelang - Secang KM 7, Jawa Tengah"))
        self.txt_corp_phone.setText(database.get_pengaturan("telepon_perusahaan", "0812-3456-7890 / (0293) 362819"))
        self.txt_corp_pj.setText(database.get_pengaturan("pj_lapangan", "Ir. H. Sudirman (Plant Manager)"))
        self.txt_bank_name.setText(database.get_pengaturan("bank_nama", "Bank Central Asia (BCA)."))
        self.txt_bank_acc.setText(database.get_pengaturan("bank_rekening", "1222218475"))
        self.txt_bank_holder.setText(database.get_pengaturan("bank_atas_nama", "ADHE KURNIA PRADANA"))
        self.txt_inv_city.setText(database.get_pengaturan("invoice_kota", "Magelang"))
        self.txt_inv_signer.setText(database.get_pengaturan("invoice_penandatangan", "ADHE KURNIA PRADANA"))

    def save_company_profile(self):
        database.set_pengaturan("nama_perusahaan", self.txt_corp_name.text().strip())
        database.set_pengaturan("alamat_perusahaan", self.txt_corp_address.text().strip())
        database.set_pengaturan("telepon_perusahaan", self.txt_corp_phone.text().strip())
        database.set_pengaturan("pj_lapangan", self.txt_corp_pj.text().strip())
        database.set_pengaturan("bank_nama", self.txt_bank_name.text().strip())
        database.set_pengaturan("bank_rekening", self.txt_bank_acc.text().strip())
        database.set_pengaturan("bank_atas_nama", self.txt_bank_holder.text().strip())
        database.set_pengaturan("invoice_kota", self.txt_inv_city.text().strip())
        database.set_pengaturan("invoice_penandatangan", self.txt_inv_signer.text().strip())
        QMessageBox.information(self, "Tersimpan", "Profil perusahaan dan informasi invoice berhasil diperbarui.")
        self.data_changed.emit()

    def do_reset_transaksi(self):
        msg = (
            "PERINGATAN KRUSIAL:\n\n"
            "Tindakan ini akan MENGHAPUS SEMUA CATATAN TRANSAKSI:\n"
            "• Seluruh riwayat pengiriman & surat jalan\n"
            "• Seluruh riwayat penerimaan stok material\n"
            "• Seluruh catatan tagihan & pembayaran semen\n"
            "• Seluruh piutang & termin masuk proyek\n"
            "• Seluruh kas kantor & pengeluaran gaji\n"
            "• Seluruh stok material dikembalikan ke 0\n\n"
            "(Master data material, resep beton standar, dan akun login tetap aman)\n\n"
            "Sistem akan secara otomatis membuat file cadangan (backup) sebelum reset.\n\n"
            "Apakah Anda benar-benar yakin ingin melanjutkan reset data transaksi?"
        )
        if not confirm_dialog(self, "Konfirmasi Reset Data Transaksi", msg):
            return

        # Simpan backup otomatis sebelum reset demi keamanan
        db_path = database.get_db_path()
        db_dir = os.path.dirname(db_path)
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        auto_bak = os.path.join(db_dir, f"auto_backup_sebelum_reset_{now_str}.db")
        database.backup_db(auto_bak)

        ok, msg = database.reset_data_transaksi()
        if ok:
            QMessageBox.information(
                self,
                "Reset Berhasil",
                f"{msg}\n\n"
                f"File cadangan otomatis sebelum reset telah disimpan di:\n{auto_bak}"
            )
            self.update_db_info()
            self.data_changed.emit()
        else:
            QMessageBox.critical(self, "Gagal Reset", msg)

    def do_reset_database_factory(self):
        msg = (
            "PERINGATAN KRUSIAL:\n\n"
            "Tindakan ini akan MERESET DATABASE KE KONDISI AWAL PABRIK:\n"
            "• Seluruh data transaksi, pengiriman, stok, dan kas dikosongkan\n"
            "• Seluruh stok material dikembalikan ke 0\n"
            "• Master proyek dan resep dikembalikan ke standar awal pabrik\n\n"
            "Sistem akan secara otomatis membuat file cadangan (backup) sebelum reset.\n\n"
            "Apakah Anda benar-benar yakin ingin melakukan Reset Total Pabrik?"
        )
        if not confirm_dialog(self, "Konfirmasi Reset Total Database", msg):
            return

        db_path = database.get_db_path()
        db_dir = os.path.dirname(db_path)
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        auto_bak = os.path.join(db_dir, f"auto_backup_sebelum_factory_reset_{now_str}.db")
        database.backup_db(auto_bak)

        ok, msg = database.reset_database_factory()
        if ok:
            QMessageBox.information(
                self,
                "Reset Total Berhasil",
                f"{msg}\n\n"
                f"File cadangan otomatis telah disimpan di:\n{auto_bak}"
            )
            self.update_db_info()
            self.data_changed.emit()
        else:
            QMessageBox.critical(self, "Gagal Reset", msg)

    def do_seed_data_ringkas(self):
        msg = (
            "Apakah Anda ingin memuat data contoh transaksi ringkas (sedikit saja)?\n\n"
            "Data yang akan dimuat mencakup:\n"
            "• 1 Saldo Modal Awal Kas Operasional (Rp 50.000.000)\n"
            "• 6 Penerimaan Stok Material (Semen, Pasir, Split, Air, Solar, Admixture)\n"
            "• 1 Pembayaran Cicilan Semen ke Supplier\n"
            "• 3 Pengiriman Cor Beton (Surat Jalan)\n"
            "• 1 Penerimaan Pembayaran Termin Proyek\n"
            "• 1 Pengeluaran Kas Kantor (BBM)\n"
            "• 1 Pembayaran Gaji Supir Mixer\n\n"
            "Sistem akan mencadangkan database Anda secara otomatis sebelum memuat data ini."
        )
        if not confirm_dialog(self, "Konfirmasi Muat Data Contoh Ringkas", msg):
            return

        db_path = database.get_db_path()
        db_dir = os.path.dirname(db_path)
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        auto_bak = os.path.join(db_dir, f"auto_backup_sebelum_muat_data_ringkas_{now_str}.db")
        database.backup_db(auto_bak)

        ok, res_msg = database.seed_data_ringkas()
        if ok:
            QMessageBox.information(
                self,
                "Berhasil Memuat Data",
                f"{res_msg}\n\n"
                f"File cadangan otomatis telah disimpan di:\n{auto_bak}"
            )
            self.update_db_info()
            self.data_changed.emit()
        else:
            QMessageBox.critical(self, "Gagal", res_msg)

    def do_reset_license(self):
        msg = (
            "Apakah Anda yakin ingin me-reset lisensi pada komputer ini?\n\n"
            "Setelah di-reset, aplikasi akan memerlukan Kunci Lisensi baru saat dibuka berikutnya."
        )
        if confirm_dialog(self, "Konfirmasi Reset Lisensi", msg):
            if license_manager.reset_license():
                QMessageBox.information(
                    self,
                    "Lisensi Di-reset",
                    "Lisensi berhasil di-reset. Aplikasi akan ditutup sekarang untuk menerapkan status aktivasi awal."
                )
                import sys
                sys.exit(0)
            else:
                QMessageBox.critical(self, "Gagal", "Gagal me-reset lisensi.")

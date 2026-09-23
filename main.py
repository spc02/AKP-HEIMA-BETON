"""
AKP Beton Management System - Main Desktop Application
Sistem Manajemen Operasional & Keuangan Batching Plant
"""

import sys
import os
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QFrame, QStatusBar,
    QMessageBox, QButtonGroup, QDialog, QSpinBox, QDoubleSpinBox, QAbstractSpinBox,
    QDateEdit, QCalendarWidget, QTableView, QComboBox, QListView
)
from PySide6.QtCore import Qt, QTimer, QObject, QEvent
from PySide6.QtGui import QFont, QIcon

# Explicit AppUserModelID agar Windows mengenali identitas icon taskbar aplikasi secara mandiri
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("akpbeton.plantbase.management.1.0")
except Exception:
    pass

import styles
import database
import license_manager
from ui.activation_dialog import ActivationDialog
from ui.login_dialog import LoginDialog
from ui.user_management_dialog import UserManagementDialog
from ui.dashboard_view import DashboardView
from ui.master_data_view import MasterDataView
from ui.stok_view import StokView
from ui.produksi_view import ProduksiView
from ui.kendaraan_view import KendaraanView
from ui.keuangan_view import KeuanganView
from ui.laporan_view import LaporanView
from ui.setting_view import SettingView
from components import confirm_dialog

def get_app_icon() -> QIcon:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    ico_path = os.path.join(base_dir, "assets", "app_logo.ico")
    if os.path.exists(ico_path):
        return QIcon(ico_path)
    png_path = os.path.join(base_dir, "assets", "app_logo.png")
    if os.path.exists(png_path):
        return QIcon(png_path)
    return QIcon()

class MainWindow(QMainWindow):
    def __init__(self, user_session: dict = None):
        super().__init__()
        self.setWindowTitle("AKP CONTRUCTION BUILDING - Sistem Manajemen Batching Plant")
        self.setWindowIcon(get_app_icon())
        self.resize(1180, 720)
        self.setMinimumSize(960, 580)
        
        # Pastikan user_session selalu punya 'id' (fallback ke 1 = admin)
        self.user_session = user_session or {"id": 1, "username": "admin", "nama_lengkap": "Administrator AKP"}
        if not self.user_session.get("id"):
            self.user_session["id"] = 1
        self.logout_requested = False

        # Inisialisasi Database
        database.init_db()

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        app_layout = QHBoxLayout(central_widget)
        app_layout.setContentsMargins(0, 0, 0, 0)
        app_layout.setSpacing(0)

        # 1. SIDEBAR NAVIGATION (Navy Blue Industrial)
        sidebar = QFrame()
        sidebar.setFixedWidth(215) # Lebar efisien untuk teks & sub-menu
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {styles.COLOR_PRIMARY_DARK};
                border-right: 1px solid #1E293B;
            }}
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 16, 10, 14)
        sidebar_layout.setSpacing(4)

        # Brand Header
        brand_frame = QFrame()
        brand_frame.setStyleSheet("background-color: transparent;")
        brand_layout = QVBoxLayout(brand_frame)
        brand_layout.setContentsMargins(6, 0, 6, 12)
        brand_layout.setSpacing(2)

        lbl_logo = QLabel("AKP CONTRUCTION")
        lbl_logo.setStyleSheet("color: #FFFFFF; font-size: 15.5px; font-weight: 900; letter-spacing: 0.8px;")
        
        lbl_sub = QLabel("BUILDING & BATCHING PLANT")
        lbl_sub.setStyleSheet("color: #94A3B8; font-size: 8.5px; font-weight: 700; letter-spacing: 0.6px;")

        brand_layout.addWidget(lbl_logo)
        brand_layout.addWidget(lbl_sub)
        sidebar_layout.addWidget(brand_frame)

        # Navigation Buttons Group
        self.nav_btn_group = QButtonGroup(self)
        self.nav_btn_group.setExclusive(True)

        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "Dashboard"),
            ("master_data", "Master Data"),
            ("stok", "Stok Material"),
            ("produksi", "Produksi & Kirim"),
            ("keuangan", "Keuangan Plant  ▸"),
            ("laporan", "Laporan"),
            ("setting", "Setting  ▸")
        ]

        # Definisi Submenu Keuangan (Termasuk Operasional Kendaraan)
        self.keuangan_sub_items = [
            ("ringkasan", "Ringkasan & Saldo Kas"),
            ("semen", "Piutang Material"),
            ("proyek", "Piutang Proyek"),
            ("kantor", "Kas Kantor (Harian)"),
            ("gaji", "Gaji Karyawan"),
            ("kendaraan", "Operasional Kendaraan")
        ]

        # Definisi Submenu Setting
        self.setting_sub_items = [
            ("user", "User"),
            ("data", "Data")
        ]

        for index, (key, label) in enumerate(nav_items):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty("class", "SidebarNavBtn")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: #CBD5E1;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 12px;
                    font-size: 13px;
                    font-weight: 600;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.10);
                    color: #FFFFFF;
                }}
                QPushButton:checked {{
                    background-color: {styles.COLOR_PRIMARY_LIGHT};
                    color: #FFFFFF;
                    font-weight: 700;
                }}
            """)
            self.nav_btn_group.addButton(btn, index)
            self.nav_buttons[key] = btn
            sidebar_layout.addWidget(btn)

            # Jika ini menu Keuangan, tambahkan collapsible submenu container
            if key == "keuangan":
                self.keuangan_submenu_frame = QFrame()
                self.keuangan_submenu_frame.setObjectName("SidebarSubmenu")
                self.keuangan_submenu_frame.setProperty("class", "SidebarSubmenu")
                submenu_layout = QVBoxLayout(self.keuangan_submenu_frame)
                submenu_layout.setContentsMargins(6, 4, 6, 4)
                submenu_layout.setSpacing(2)

                self.keuangan_sub_buttons = {}
                self.keuangan_sub_btn_group = QButtonGroup(self)
                self.keuangan_sub_btn_group.setExclusive(True)

                for sub_idx, (sub_key, sub_label) in enumerate(self.keuangan_sub_items):
                    sub_btn = QPushButton(f"• {sub_label}")
                    sub_btn.setCheckable(True)
                    sub_btn.setProperty("class", "SidebarSubNavBtn")
                    sub_btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: transparent;
                            color: #94A3B8;
                            border: none;
                            border-radius: 4px;
                            padding: 7px 10px 7px 10px;
                            font-size: 11.5px;
                            font-weight: 500;
                            text-align: left;
                        }}
                        QPushButton:hover {{
                            background-color: rgba(255, 255, 255, 0.12);
                            color: #FFFFFF;
                            font-weight: 600;
                        }}
                        QPushButton:checked {{
                            background-color: {styles.COLOR_PRIMARY_LIGHT};
                            color: #FFFFFF;
                            font-weight: 700;
                        }}
                    """)
                    self.keuangan_sub_btn_group.addButton(sub_btn, sub_idx)
                    self.keuangan_sub_buttons[sub_key] = sub_btn
                    submenu_layout.addWidget(sub_btn)

                self.keuangan_sub_btn_group.idClicked.connect(self.on_keuangan_sub_clicked)
                self.keuangan_submenu_frame.setVisible(False)
                sidebar_layout.addWidget(self.keuangan_submenu_frame)

            # Jika ini menu Setting, tambahkan collapsible submenu container
            if key == "setting":
                self.setting_submenu_frame = QFrame()
                self.setting_submenu_frame.setObjectName("SidebarSubmenu")
                self.setting_submenu_frame.setProperty("class", "SidebarSubmenu")
                setting_sub_layout = QVBoxLayout(self.setting_submenu_frame)
                setting_sub_layout.setContentsMargins(6, 4, 6, 4)
                setting_sub_layout.setSpacing(2)

                self.setting_sub_buttons = {}
                self.setting_sub_btn_group = QButtonGroup(self)
                self.setting_sub_btn_group.setExclusive(True)

                for sub_idx, (sub_key, sub_label) in enumerate(self.setting_sub_items):
                    sub_btn = QPushButton(f"• {sub_label}")
                    sub_btn.setCheckable(True)
                    sub_btn.setProperty("class", "SidebarSubNavBtn")
                    sub_btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: transparent;
                            color: #94A3B8;
                            border: none;
                            border-radius: 4px;
                            padding: 7px 10px 7px 10px;
                            font-size: 11.5px;
                            font-weight: 500;
                            text-align: left;
                        }}
                        QPushButton:hover {{
                            background-color: rgba(255, 255, 255, 0.12);
                            color: #FFFFFF;
                            font-weight: 600;
                        }}
                        QPushButton:checked {{
                            background-color: {styles.COLOR_PRIMARY_LIGHT};
                            color: #FFFFFF;
                            font-weight: 700;
                        }}
                    """)
                    self.setting_sub_btn_group.addButton(sub_btn, sub_idx)
                    self.setting_sub_buttons[sub_key] = sub_btn
                    setting_sub_layout.addWidget(sub_btn)

                self.setting_sub_btn_group.idClicked.connect(self.on_setting_sub_clicked)
                self.setting_submenu_frame.setVisible(False)
                sidebar_layout.addWidget(self.setting_submenu_frame)

        sidebar_layout.addStretch()

        # Sidebar Footer
        lbl_ver = QLabel("v1.0.0 • Lisensi Aktif")
        lbl_ver.setStyleSheet("color: #64748B; font-size: 10px; padding-left: 8px; padding-bottom: 6px;")
        sidebar_layout.addWidget(lbl_ver)

        app_layout.addWidget(sidebar)

        # 2. MAIN CONTENT AREA (Header + Stacked Pages)
        content_area = QWidget()
        content_area.setStyleSheet(f"background-color: {styles.COLOR_BG_APP};")
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Top Header Bar
        top_bar = QFrame()
        top_bar.setFixedHeight(50)
        top_bar.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border-bottom: 1px solid {styles.COLOR_BORDER_LIGHT};
            }}
        """)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 0, 20, 0)

        self.lbl_page_title = QLabel("Dashboard Operasional")
        self.lbl_page_title.setStyleSheet(f"color: {styles.COLOR_TEXT_MAIN}; font-size: 15px; font-weight: 700;")
        top_layout.addWidget(self.lbl_page_title)
        top_layout.addStretch()

        self.lbl_datetime = QLabel()
        self.lbl_datetime.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 12px; margin-right: 14px;")
        top_layout.addWidget(self.lbl_datetime)
        self.update_datetime()

        # Tombol Logout di Header Kanan Atas
        btn_top_logout = QPushButton("Logout")
        btn_top_logout.setCursor(Qt.PointingHandCursor)
        btn_top_logout.setFixedHeight(30)
        btn_top_logout.setStyleSheet(f"""
            QPushButton {{
                background-color: #FEF2F2;
                color: #DC2626;
                border: 1px solid #FECACA;
                border-radius: 6px;
                padding: 4px 14px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: #DC2626;
                color: #FFFFFF;
                border-color: #DC2626;
            }}
            QPushButton:pressed {{
                background-color: #B91C1C;
                color: #FFFFFF;
            }}
        """)
        btn_top_logout.clicked.connect(self.handle_logout)
        top_layout.addWidget(btn_top_logout)

        content_layout.addWidget(top_bar)

        # 3. Stacked Pages
        self.stacked_widget = QStackedWidget()
        self.dashboard_view = DashboardView(user_session=self.user_session)
        self.master_data_view = MasterDataView(user_session=self.user_session)
        self.stok_view = StokView(user_session=self.user_session)
        self.produksi_view = ProduksiView(user_session=self.user_session)
        self.keuangan_view = KeuanganView()
        self.kendaraan_view = self.keuangan_view.tab_kendaraan
        self.laporan_view = LaporanView()
        self.setting_view = SettingView(self.user_session)

        self.stacked_widget.addWidget(self.dashboard_view)    # Index 0
        self.stacked_widget.addWidget(self.master_data_view)  # Index 1
        self.stacked_widget.addWidget(self.stok_view)         # Index 2
        self.stacked_widget.addWidget(self.produksi_view)     # Index 3
        self.stacked_widget.addWidget(self.keuangan_view)     # Index 4
        self.stacked_widget.addWidget(self.laporan_view)      # Index 5
        self.stacked_widget.addWidget(self.setting_view)      # Index 6

        content_layout.addWidget(self.stacked_widget)
        app_layout.addWidget(content_area)

        # Set default active page: Dashboard
        self.nav_buttons["dashboard"].setChecked(True)
        self.nav_btn_group.idClicked.connect(self.on_nav_clicked)

        # Timer untuk jam header
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_datetime)
        self.timer.start(1000)

    def update_datetime(self):
        now = datetime.now()
        days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        day_name = days[now.weekday()]
        self.lbl_datetime.setText(f"{day_name}, {now.strftime('%d/%m/%Y %H:%M:%S')}")

    def on_nav_clicked(self, index: int):
        # Penanganan khusus Menu Keuangan (Index 4)
        if index == 4:
            self.setting_submenu_frame.setVisible(False)
            self.nav_buttons["setting"].setText("Setting  ▸")

            is_open = self.keuangan_submenu_frame.isVisible()
            if not is_open or self.stacked_widget.currentIndex() != 4:
                self.keuangan_submenu_frame.setVisible(True)
                self.nav_buttons["keuangan"].setText("Keuangan Plant  ▾")
                self.nav_buttons["keuangan"].setChecked(True)
                self.stacked_widget.setCurrentIndex(4)

                curr_sub = self.keuangan_sub_btn_group.checkedId()
                if curr_sub < 0:
                    curr_sub = 0
                    if self.keuangan_sub_btn_group.button(0):
                        self.keuangan_sub_btn_group.button(0).setChecked(True)
                self.on_keuangan_sub_clicked(curr_sub)
            else:
                self.keuangan_submenu_frame.setVisible(False)
                self.nav_buttons["keuangan"].setText("Keuangan Plant  ▸")
            return

        # Penanganan khusus Menu Setting (Index 6)
        if index == 6:
            self.keuangan_submenu_frame.setVisible(False)
            self.nav_buttons["keuangan"].setText("Keuangan Plant  ▸")

            is_open = self.setting_submenu_frame.isVisible()
            if not is_open or self.stacked_widget.currentIndex() != 6:
                self.setting_submenu_frame.setVisible(True)
                self.nav_buttons["setting"].setText("Setting  ▾")
                self.nav_buttons["setting"].setChecked(True)
                self.stacked_widget.setCurrentIndex(6)

                curr_sub = self.setting_sub_btn_group.checkedId()
                if curr_sub < 0:
                    curr_sub = 0
                    if self.setting_sub_btn_group.button(0):
                        self.setting_sub_btn_group.button(0).setChecked(True)
                self.on_setting_sub_clicked(curr_sub)
            else:
                self.setting_submenu_frame.setVisible(False)
                self.nav_buttons["setting"].setText("Setting  ▸")
            return

        # Jika menu utama lain diklik: tutup submenu Keuangan & Setting
        self.keuangan_submenu_frame.setVisible(False)
        self.nav_buttons["keuangan"].setText("Keuangan Plant  ▸")
        self.setting_submenu_frame.setVisible(False)
        self.nav_buttons["setting"].setText("Setting  ▸")

        checked_sub_k = self.keuangan_sub_btn_group.checkedButton()
        if checked_sub_k:
            self.keuangan_sub_btn_group.setExclusive(False)
            checked_sub_k.setChecked(False)
            self.keuangan_sub_btn_group.setExclusive(True)

        checked_sub_s = self.setting_sub_btn_group.checkedButton()
        if checked_sub_s:
            self.setting_sub_btn_group.setExclusive(False)
            checked_sub_s.setChecked(False)
            self.setting_sub_btn_group.setExclusive(True)

        self.stacked_widget.setCurrentIndex(index)
        titles = [
            "Dashboard Operasional",
            "Master Data (Material, Resep, Proyek)",
            "Manajemen Stok Material",
            "Produksi & Pengiriman Beton",
            "Keuangan & Akuntansi Batching Plant",
            "Pusat Laporan & Ekspor Dokumen",
            "Pengaturan Sistem (Setting)"
        ]
        if index < len(titles):
            self.lbl_page_title.setText(titles[index])

        self.refresh_current_view(index)

    def on_keuangan_sub_clicked(self, sub_idx: int):
        self.stacked_widget.setCurrentIndex(4)
        self.nav_buttons["keuangan"].setChecked(True)
        self.nav_buttons["keuangan"].setText("Keuangan Plant  ▾")
        if not self.keuangan_submenu_frame.isVisible():
            self.keuangan_submenu_frame.setVisible(True)

        btn = self.keuangan_sub_btn_group.button(sub_idx)
        if btn and not btn.isChecked():
            btn.setChecked(True)

        self.keuangan_view.set_current_sub_tab(sub_idx)

        sub_titles = [
            "Keuangan Plant - Ringkasan & Saldo Kas",
            "Keuangan Plant - Piutang Material",
            "Keuangan Plant - Piutang & Pembayaran Proyek",
            "Keuangan Plant - Kas Kantor (Harian)",
            "Keuangan Plant - Gaji Karyawan",
            "Keuangan Plant - Operasional Kendaraan"
        ]
        if 0 <= sub_idx < len(sub_titles):
            self.lbl_page_title.setText(sub_titles[sub_idx])

    def on_setting_sub_clicked(self, sub_idx: int):
        self.stacked_widget.setCurrentIndex(6)
        self.nav_buttons["setting"].setChecked(True)
        self.nav_buttons["setting"].setText("Setting  ▾")
        if not self.setting_submenu_frame.isVisible():
            self.setting_submenu_frame.setVisible(True)

        btn = self.setting_sub_btn_group.button(sub_idx)
        if btn and not btn.isChecked():
            btn.setChecked(True)

        self.setting_view.set_sub_tab(sub_idx)

        sub_titles = [
            "Pengaturan - Akun Pengguna (User)",
            "Pengaturan - Manajemen Data (Backup, Profil & Lisensi)"
        ]
        if 0 <= sub_idx < len(sub_titles):
            self.lbl_page_title.setText(sub_titles[sub_idx])

    def switch_to_module(self, module_name: str, sub_tab: int = 0):
        if module_name == "kendaraan":
            self.switch_to_module("keuangan", sub_tab=5)
            return

        if module_name == "keuangan":
            self.nav_buttons["keuangan"].setChecked(True)
            self.keuangan_submenu_frame.setVisible(True)
            self.nav_buttons["keuangan"].setText("Keuangan Plant  ▾")
            target_sub = sub_tab if (0 <= sub_tab < len(self.keuangan_sub_items)) else 0
            btn = self.keuangan_sub_btn_group.button(target_sub)
            if btn:
                btn.setChecked(True)
            self.on_keuangan_sub_clicked(target_sub)
            return

        if module_name == "setting":
            self.nav_buttons["setting"].setChecked(True)
            self.setting_submenu_frame.setVisible(True)
            self.nav_buttons["setting"].setText("Setting  ▾")
            target_sub = sub_tab if (0 <= sub_tab < len(self.setting_sub_items)) else 0
            btn = self.setting_sub_btn_group.button(target_sub)
            if btn:
                btn.setChecked(True)
            self.on_setting_sub_clicked(target_sub)
            return

        mapping = {
            "dashboard": 0,
            "master_data": 1,
            "stok": 2,
            "produksi": 3,
            "keuangan": 4,
            "laporan": 5,
            "setting": 6
        }
        if module_name in mapping:
            idx = mapping[module_name]
            btn = self.nav_btn_group.button(idx)
            if btn:
                btn.setChecked(True)
                self.on_nav_clicked(idx)

    def refresh_current_view(self, index: int):
        if index == 0:
            self.dashboard_view.load_data()
        elif index == 1:
            self.master_data_view.refresh_all()
        elif index == 2:
            self.stok_view.refresh_all()
        elif index == 3:
            self.produksi_view.refresh_all()
        elif index == 4:
            self.keuangan_view.refresh_all()
        elif index == 5:
            self.laporan_view.refresh_all()
        elif index == 6:
            self.setting_view.refresh_all()

    def sync_all_data(self):
        """Memperbarui seluruh view ketika terjadi perubahan transaksi di salah satu view"""
        self.dashboard_view.load_data()
        self.stok_view.refresh_all()
        self.produksi_view.refresh_all()
        self.kendaraan_view.load_data()
        self.keuangan_view.refresh_all()
        self.master_data_view.refresh_all()
        self.laporan_view.refresh_all()
        self.setting_view.refresh_all()

    def connect_signals(self):
        self.dashboard_view.nav_to_module.connect(self.switch_to_module)
        self.master_data_view.data_changed.connect(self.sync_all_data)
        self.stok_view.data_changed.connect(self.sync_all_data)
        self.produksi_view.data_changed.connect(self.sync_all_data)
        self.kendaraan_view.data_changed.connect(self.sync_all_data)
        self.keuangan_view.data_changed.connect(self.sync_all_data)
        self.setting_view.data_changed.connect(self.sync_all_data)
        self.setting_view.logout_requested.connect(self.handle_logout)

    def handle_logout(self):
        uname = self.user_session.get("username", "admin")
        if confirm_dialog(self, "Konfirmasi Keluar Akun", f"Apakah Anda yakin ingin logout dari akun '{uname}'?"):
            self.logout_requested = True
            self.close()


class NoScrollWheelFilter(QObject):
    """Mencegah perubahan angka/pilihan pada input saat kursor scroll mouse di form atau halaman"""
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            if isinstance(obj, (QSpinBox, QDoubleSpinBox, QAbstractSpinBox, QComboBox, QDateEdit)):
                event.ignore()
                return True
        elif event.type() == QEvent.Show:
            if isinstance(obj, (QSpinBox, QDoubleSpinBox)):
                obj.setButtonSymbols(QAbstractSpinBox.NoButtons)
            elif isinstance(obj, QComboBox):
                if not isinstance(obj.view(), QListView):
                    obj.setView(QListView())
            elif isinstance(obj, QDateEdit):
                cal = obj.calendarWidget()
                if cal:
                    cal.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
                    tv = cal.findChild(QTableView)
                    if tv:
                        tv.setStyleSheet("background-color: #FFFFFF; color: #0F172A; selection-background-color: #0F172A; selection-color: #FFFFFF;")
            elif isinstance(obj, QCalendarWidget):
                obj.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
                tv = obj.findChild(QTableView)
                if tv:
                    tv.setStyleSheet("background-color: #FFFFFF; color: #0F172A; selection-background-color: #0F172A; selection-color: #FFFFFF;")
        return super().eventFilter(obj, event)


def main():
    app = QApplication(sys.argv)
    wheel_filter = NoScrollWheelFilter(app)
    app.installEventFilter(wheel_filter)
    app.setWindowIcon(get_app_icon())
    app.setStyleSheet(styles.GLOBAL_STYLESHEET)
    
    # 1. Inisialisasi Database
    database.init_db()

    # 2. Periksa Aktivasi Lisensi Perangkat Keras
    is_act, lic_msg, lic_data = license_manager.is_activated()
    if not is_act:
        act_dialog = ActivationDialog()
        if act_dialog.exec() != QDialog.Accepted:
            sys.exit(0)

    # 3. Loop Sesi Login Pengguna
    while True:
        login_dialog = LoginDialog()
        if login_dialog.exec() != QDialog.Accepted:
            sys.exit(0)

        user_session = login_dialog.user_session
        if not user_session:
            sys.exit(0)

        window = MainWindow(user_session=user_session)
        window.show()

        app.exec()

        if not getattr(window, 'logout_requested', False):
            sys.exit(0)

if __name__ == "__main__":
    main()

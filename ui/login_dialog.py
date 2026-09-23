"""
AKP Beton Management System - Login Dialog
Halaman Masuk Pengguna dengan Desain Industrial Modern & Kartu Login Melayang
Sesuai rancangan visual Sistem Manajemen Batching Plant
"""

import os
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame, QCheckBox, QApplication
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QPainter, QFont, QIcon, QColor

import styles
import database
import license_manager

class LoginDialog(QDialog):
    login_succeeded = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sistem Manajemen Batching Plant - Masuk")
        self.setFixedSize(1024, 682)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.user_session = None

        # Resolusi path aset visual
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self.bg_path = os.path.join(base_dir, "assets", "login_bg.jpg")
        self.silo_badge_path = os.path.join(base_dir, "assets", "login_silo_badge.png")
        self.icon_user_path = os.path.join(base_dir, "assets", "icon_user.png")
        self.icon_lock_path = os.path.join(base_dir, "assets", "icon_lock.png")
        self.icon_eye_path = os.path.join(base_dir, "assets", "icon_eye.png")

        # Muat icon aplikasi
        self.app_icon_path = os.path.join(base_dir, "assets", "app_logo.ico")
        if os.path.exists(self.app_icon_path):
            self.setWindowIcon(QIcon(self.app_icon_path))

        # Muat pixmap latar belakang
        if os.path.exists(self.bg_path):
            self.bg_pixmap = QPixmap(self.bg_path).scaled(1024, 682, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        else:
            self.bg_pixmap = None

        self.init_ui()
        self.center_on_screen()
        self.load_remembered_username()

    def center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            x = (geom.width() - 1024) // 2
            y = (geom.height() - 682) // 2
            self.move(max(0, x), max(0, y))

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.bg_pixmap and not self.bg_pixmap.isNull():
            painter.drawPixmap(0, 0, self.bg_pixmap)
        else:
            painter.fillRect(self.rect(), QColor("#0A192F"))

    def init_ui(self):
        # 1. Kartu Login Putih Melayang (Floating Card di sebelah kanan)
        self.card = QFrame(self)
        self.card.setGeometry(614, 64, 380, 526)
        self.card.setObjectName("loginCard")
        self.card.setStyleSheet("""
            QFrame#loginCard {
                background-color: #FFFFFF;
                border-radius: 20px;
                border: 1px solid #E2E8F0;
            }
        """)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(28, 22, 28, 22)
        card_layout.setSpacing(10)

        # A. Badge Logo Silo Batching Plant
        lbl_badge = QLabel()
        lbl_badge.setAlignment(Qt.AlignCenter)
        if os.path.exists(self.silo_badge_path):
            silo_pix = QPixmap(self.silo_badge_path).scaled(78, 78, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl_badge.setPixmap(silo_pix)
        card_layout.addWidget(lbl_badge)

        # B. Judul "Selamat Datang"
        lbl_title = QLabel("Selamat Datang")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("font-size: 21px; font-weight: 800; color: #0F172A;")
        card_layout.addWidget(lbl_title)

        # C. Subtitle
        lbl_sub = QLabel("Silakan masuk untuk melanjutkan\nke sistem manajemen batching plant")
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setStyleSheet("font-size: 11.5px; color: #64748B; line-height: 1.3;")
        card_layout.addWidget(lbl_sub)

        card_layout.addSpacing(4)

        # D. Input Username (Floating Box)
        self.user_box = QFrame()
        self.user_box.setObjectName("userBox")
        self.user_box.setStyleSheet("""
            QFrame#userBox {
                background-color: #FFFFFF;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
            }
        """)
        user_lay = QHBoxLayout(self.user_box)
        user_lay.setContentsMargins(10, 6, 12, 6)
        user_lay.setSpacing(8)

        lbl_u_icon = QLabel()
        if os.path.exists(self.icon_user_path):
            lbl_u_icon.setPixmap(QPixmap(self.icon_user_path).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lbl_u_icon.setStyleSheet("border: none; background: transparent;")
        user_lay.addWidget(lbl_u_icon)

        u_col = QVBoxLayout()
        u_col.setSpacing(0)
        u_lbl_tag = QLabel("Nama Pengguna (Username)")
        u_lbl_tag.setStyleSheet("font-size: 10px; color: #64748B; font-weight: 600; border: none; background: transparent;")
        u_col.addWidget(u_lbl_tag)

        self.input_username = QLineEdit("admin")
        self.input_username.setStyleSheet("font-size: 13.5px; font-weight: 700; color: #0F172A; border: none; background: transparent; padding: 0px;")
        self.input_username.returnPressed.connect(self.focus_password)
        u_col.addWidget(self.input_username)
        user_lay.addLayout(u_col)
        card_layout.addWidget(self.user_box)

        # E. Input Password
        lbl_p_tag = QLabel("Kata Sandi (Password)")
        lbl_p_tag.setStyleSheet("font-size: 11.5px; color: #1E293B; font-weight: 700;")
        card_layout.addWidget(lbl_p_tag)

        self.pwd_box = QFrame()
        self.pwd_box.setObjectName("pwdBox")
        self.pwd_box.setStyleSheet("""
            QFrame#pwdBox {
                background-color: #FFFFFF;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
            }
        """)
        pwd_lay = QHBoxLayout(self.pwd_box)
        pwd_lay.setContentsMargins(10, 8, 10, 8)
        pwd_lay.setSpacing(8)

        lbl_p_icon = QLabel()
        if os.path.exists(self.icon_lock_path):
            lbl_p_icon.setPixmap(QPixmap(self.icon_lock_path).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lbl_p_icon.setStyleSheet("border: none; background: transparent;")
        pwd_lay.addWidget(lbl_p_icon)

        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.Password)
        self.input_password.setPlaceholderText("Masukkan kata sandi")
        self.input_password.setStyleSheet("font-size: 13px; color: #0F172A; border: none; background: transparent;")
        self.input_password.returnPressed.connect(self.handle_login)
        pwd_lay.addWidget(self.input_password)

        self.btn_eye = QPushButton()
        if os.path.exists(self.icon_eye_path):
            self.btn_eye.setIcon(QIcon(self.icon_eye_path))
            self.btn_eye.setIconSize(QSize(18, 18))
        else:
            self.btn_eye.setText("👁")
        self.btn_eye.setCheckable(True)
        self.btn_eye.setCursor(Qt.PointingHandCursor)
        self.btn_eye.setStyleSheet("border: none; background: transparent; padding: 2px;")
        self.btn_eye.toggled.connect(self.toggle_password_visibility)
        pwd_lay.addWidget(self.btn_eye)
        card_layout.addWidget(self.pwd_box)

        # F. Checkbox "Ingat username"
        self.chk_remember = QCheckBox("Ingat username di komputer ini")
        self.chk_remember.setChecked(True)
        self.chk_remember.setStyleSheet("""
            QCheckBox {
                font-size: 11.5px;
                color: #1E293B;
                font-weight: 600;
                margin-top: 2px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1.5px solid #0B2545;
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                background-color: #0B2545;
                border-color: #0B2545;
            }
        """)
        card_layout.addWidget(self.chk_remember)

        card_layout.addSpacing(4)

        # G. Tombol Utama Masuk (Navy Solid)
        self.btn_login = QPushButton("Masuk ke Sistem   →")
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.setFixedHeight(44)
        self.btn_login.setStyleSheet("""
            QPushButton {
                background-color: #0B2545;
                color: #FFFFFF;
                font-size: 13.5px;
                font-weight: 700;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1A365D;
            }
            QPushButton:pressed {
                background-color: #07172C;
            }
        """)
        self.btn_login.clicked.connect(self.handle_login)
        card_layout.addWidget(self.btn_login)

        # H. Tombol Batal / Keluar
        btn_cancel = QPushButton("Batal / Keluar")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setFixedHeight(38)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #1E293B;
                font-size: 12.5px;
                font-weight: 700;
                border-radius: 8px;
                border: 1.5px solid #CBD5E1;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
                border-color: #94A3B8;
            }
            QPushButton:pressed {
                background-color: #CBD5E1;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        card_layout.addWidget(btn_cancel)

    def focus_password(self):
        self.input_password.setFocus()

    def toggle_password_visibility(self, checked: bool):
        if checked:
            self.input_password.setEchoMode(QLineEdit.Normal)
        else:
            self.input_password.setEchoMode(QLineEdit.Password)

    def load_remembered_username(self):
        rem = database.get_pengaturan("remembered_username")
        if rem:
            self.input_username.setText(rem)
            self.input_password.setFocus()
        else:
            self.input_username.setText("admin")
            self.input_password.setFocus()

    def handle_login(self):
        username = self.input_username.text().strip()
        password = self.input_password.text()

        if not username:
            QMessageBox.warning(self, "Peringatan", "Silakan masukkan username.")
            self.input_username.setFocus()
            return
        if not password:
            QMessageBox.warning(self, "Peringatan", "Silakan masukkan kata sandi.")
            self.input_password.setFocus()
            return

        ok, msg, user_data = database.authenticate_user(username, password)
        if not ok:
            QMessageBox.critical(self, "Gagal Masuk", msg)
            self.input_password.clear()
            self.input_password.setFocus()
            return

        # Simpan preferensi username jika dicentang
        if self.chk_remember.isChecked():
            database.set_pengaturan("remembered_username", username)
        else:
            database.set_pengaturan("remembered_username", "")

        self.user_session = user_data
        self.login_succeeded.emit(user_data)
        self.accept()

"""
AKP Beton Management System - Activation Dialog
Dialog Aktivasi Aplikasi Berbasis Penguncian Perangkat Keras (Machine ID)
"""

import os
import sys

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon

import styles
import license_manager

class ActivationDialog(QDialog):
    activation_succeeded = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Aktivasi Lisensi - AKP Contruction Building")
        self.setFixedSize(560, 480)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.machine_id = license_manager.get_machine_id()
        self.license_info = None

        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        ico_path = os.path.join(base_dir, "assets", "app_logo.ico")
        if os.path.exists(ico_path):
            self.setWindowIcon(QIcon(ico_path))

        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {styles.COLOR_BG_APP};
                font-family: 'Segoe UI', sans-serif;
            }}
            QFrame#headerFrame {{
                background-color: {styles.COLOR_PRIMARY_DARK};
                border-bottom: 2px solid {styles.COLOR_PRIMARY};
                border-radius: 0px;
            }}
            QFrame#cardFrame {{
                background-color: #FFFFFF;
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 8px;
            }}
            QLabel {{
                color: {styles.COLOR_TEXT_MAIN};
            }}
            QLineEdit {{
                background-color: #FFFFFF;
                border: 1.5px solid {styles.COLOR_BORDER};
                border-radius: 6px;
                padding: 10px 14px;
                font-size: 13px;
                color: {styles.COLOR_TEXT_MAIN};
            }}
            QLineEdit:focus {{
                border-color: {styles.COLOR_PRIMARY_LIGHT};
                background-color: #F8FAFC;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Header Banner
        header = QFrame()
        header.setObjectName("headerFrame")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(28, 22, 28, 22)
        header_layout.setSpacing(4)

        lbl_brand = QLabel("AKP CONTRUCTION BUILDING")
        lbl_brand.setStyleSheet("color: #FFFFFF; font-size: 17px; font-weight: 900; letter-spacing: 0.8px;")
        
        lbl_subtitle = QLabel("Aktivasi Lisensi Resmi & Penguncian Perangkat Keras")
        lbl_subtitle.setStyleSheet("color: #94A3B8; font-size: 11.5px; font-weight: 500;")

        header_layout.addWidget(lbl_brand)
        header_layout.addWidget(lbl_subtitle)
        layout.addWidget(header)

        # 2. Main Body Container
        body_widget = QFrame()
        body_layout = QVBoxLayout(body_widget)
        body_layout.setContentsMargins(28, 20, 28, 20)
        body_layout.setSpacing(16)

        # Info Box
        info_box = QFrame()
        info_box.setObjectName("infoBox")
        info_box.setStyleSheet(f"""
            QFrame#infoBox {{
                background-color: {styles.COLOR_INFO_BG};
                border: 1px solid #BAE6FD;
                border-radius: 8px;
            }}
        """)
        info_box_layout = QVBoxLayout(info_box)
        info_box_layout.setContentsMargins(14, 12, 14, 12)
        info_box_layout.setSpacing(4)

        lbl_info_title = QLabel("Perangkat Belum Teraktivasi")
        lbl_info_title.setStyleSheet(f"color: {styles.COLOR_INFO}; font-weight: 700; font-size: 12.5px; border: none; background: transparent;")
        
        lbl_info_desc = QLabel(
            "Aplikasi ini dilindungi lisensi khusus per perangkat komputer. "
            "Kirimkan Machine ID berikut kepada administrator / pemilik sistem untuk mendapatkan Kunci Lisensi resmi."
        )
        lbl_info_desc.setWordWrap(True)
        lbl_info_desc.setStyleSheet("color: #0369A1; font-size: 11.5px; line-height: 1.4; border: none; background: transparent;")

        info_box_layout.addWidget(lbl_info_title)
        info_box_layout.addWidget(lbl_info_desc)
        body_layout.addWidget(info_box)

        # Machine ID Box
        mid_label = QLabel("Machine ID Komputer Anda:")
        mid_label.setStyleSheet("font-weight: 700; font-size: 12.5px; color: #334155;")
        body_layout.addWidget(mid_label)

        mid_row = QHBoxLayout()
        mid_row.setSpacing(8)
        self.input_mid = QLineEdit(self.machine_id)
        self.input_mid.setReadOnly(True)
        self.input_mid.setStyleSheet(f"""
            background-color: #F1F5F9;
            color: {styles.COLOR_PRIMARY};
            font-family: 'Consolas', monospace;
            font-size: 13.5px;
            font-weight: 700;
            border: 1px solid #CBD5E1;
            padding: 8px 12px;
        """)
        mid_row.addWidget(self.input_mid)

        btn_copy = QPushButton("Salin ID")
        btn_copy.setCursor(Qt.PointingHandCursor)
        btn_copy.setFixedHeight(38)
        btn_copy.setStyleSheet(f"""
            QPushButton {{
                background-color: #475569;
                color: #FFFFFF;
                font-weight: 600;
                border-radius: 6px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: #334155;
            }}
        """)
        btn_copy.clicked.connect(self.copy_machine_id)
        mid_row.addWidget(btn_copy)
        body_layout.addLayout(mid_row)

        # License Key Input
        key_label = QLabel("Masukkan Kunci Lisensi (Serial Key):")
        key_label.setStyleSheet("font-weight: 700; font-size: 12.5px; color: #334155; margin-top: 4px;")
        body_layout.addWidget(key_label)

        self.input_key = QLineEdit()
        self.input_key.setPlaceholderText("AKP-PERM-XXXX-XXXX-XXXX")
        self.input_key.setStyleSheet(f"""
            font-family: 'Consolas', monospace;
            font-size: 13.5px;
            font-weight: 600;
            letter-spacing: 0.5px;
        """)
        self.input_key.textChanged.connect(self.on_key_text_changed)
        self.input_key.returnPressed.connect(self.handle_activate)
        body_layout.addWidget(self.input_key)

        body_layout.addStretch()

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_exit = QPushButton("Keluar Aplikasi")
        btn_exit.setCursor(Qt.PointingHandCursor)
        btn_exit.setFixedHeight(42)
        btn_exit.setStyleSheet("""
            QPushButton {{
                background-color: #E2E8F0;
                color: #334155;
                font-weight: 600;
                border-radius: 6px;
                padding: 0 20px;
                border: 1px solid #CBD5E1;
            }}
            QPushButton:hover {{
                background-color: #CBD5E1;
            }}
        """)
        btn_exit.clicked.connect(self.reject)
        btn_row.addWidget(btn_exit)

        self.btn_activate = QPushButton("Aktivasi Sekarang")
        self.btn_activate.setCursor(Qt.PointingHandCursor)
        self.btn_activate.setFixedHeight(42)
        self.btn_activate.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.COLOR_PRIMARY};
                color: #FFFFFF;
                font-weight: 700;
                font-size: 13.5px;
                border-radius: 6px;
                padding: 0 24px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {styles.COLOR_PRIMARY_LIGHT};
            }}
        """)
        self.btn_activate.clicked.connect(self.handle_activate)
        btn_row.addWidget(self.btn_activate)

        body_layout.addLayout(btn_row)
        layout.addWidget(body_widget)

    def on_key_text_changed(self, text: str):
        # Auto uppercase
        upper = text.upper()
        if text != upper:
            cursor_pos = self.input_key.cursorPosition()
            self.input_key.setText(upper)
            self.input_key.setCursorPosition(cursor_pos)

    def copy_machine_id(self):
        QApplication.clipboard().setText(self.machine_id)
        QMessageBox.information(
            self,
            "Tersalin ke Clipboard",
            f"Machine ID berhasil disalin:\n\n{self.machine_id}\n\nSilakan kirimkan ke administrator untuk mendapatkan Serial Key aktivasi."
        )

    def handle_activate(self):
        key = self.input_key.text().strip().upper()
        if not key:
            QMessageBox.warning(self, "Validasi Lisensi", "Silakan masukkan Kunci Lisensi (Serial Key) terlebih dahulu.")
            self.input_key.setFocus()
            return

        is_valid, msg, meta = license_manager.verify_license_key(self.machine_id, key)
        if not is_valid:
            QMessageBox.critical(
                self,
                "Aktivasi Gagal",
                f"Kunci Lisensi tidak valid:\n\n{msg}\n\nPastikan Kunci Lisensi sesuai persis dengan Machine ID komputer ini."
            )
            return

        # Simpan lisensi
        saved = license_manager.save_license(self.machine_id, key, meta)
        if not saved:
            QMessageBox.critical(
                self,
                "Error Penyimpanan",
                "Terjadi kesalahan saat menyimpan file lisensi di komputer lokal. Periksa izin akses folder."
            )
            return

        self.license_info = meta
        QMessageBox.information(
            self,
            "Aktivasi Berhasil",
            f"Selamat! Aplikasi AKP CONTRUCTION BUILDING telah berhasil diaktivasi pada komputer ini.\n\n"
            f"Jenis Lisensi: {'Permanen (Lifetime)' if meta.get('is_permanent') else 'Berlaku s.d ' + str(meta.get('expiry_date'))}\n"
            f"Machine ID: {self.machine_id}"
        )
        self.activation_succeeded.emit(meta)
        self.accept()

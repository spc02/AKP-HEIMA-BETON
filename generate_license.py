"""
AKP Beton Management System - License Key Generator
Alat Pembuat Kunci Lisensi untuk Pemilik / Developer AKP Contruction Building.

Cara Penggunaan:
1. Mode GUI (Mudah):
   Jalankan: python generate_license.py (atau double click)
2. Mode CLI:
   python generate_license.py <MACHINE_ID> [PERM|YYYYMMDD]
   Contoh:
   python generate_license.py AKP-6DCA-0E64-ECAC-605C PERM
"""

import sys
import os
from datetime import datetime

import license_manager

def run_cli(args):
    if len(args) < 2:
        print("Penggunaan CLI: python generate_license.py <MACHINE_ID> [PERM|YYYYMMDD]")
        print("Contoh: python generate_license.py AKP-6DCA-0E64-ECAC-605C PERM")
        return

    mid = args[1].strip()
    l_type = args[2].strip() if len(args) > 2 else "PERM"
    key = license_manager.generate_license_key(mid, l_type)
    print("=" * 60)
    print(f"AKP CONTRUCTION BUILDING - LICENSE KEY GENERATOR")
    print("=" * 60)
    print(f"Machine ID   : {mid}")
    print(f"Tipe Lisensi : {'Permanen (Lifetime)' if l_type == 'PERM' else 'Berjangka hingga ' + l_type}")
    print(f"License Key  : {key}")
    print("=" * 60)
    print("Kirimkan License Key di atas kepada klien untuk diinput di aplikasi.")


def run_gui():
    try:
        from PySide6.QtWidgets import (
            QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
            QLineEdit, QPushButton, QComboBox, QMessageBox, QFrame
        )
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFont, QClipboard
    except ImportError:
        print("PySide6 tidak tersedia, beralih ke mode CLI.")
        return

    app = QApplication.instance() or QApplication(sys.argv)

    class KeygenWindow(QDialog):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("AKP License Generator (Admin Tool)")
            self.setFixedSize(540, 360)
            self.setStyleSheet("""
                QDialog {
                    background-color: #0F172A;
                    color: #F8FAFC;
                    font-family: 'Segoe UI', sans-serif;
                }
                QLabel {
                    color: #E2E8F0;
                    font-size: 13px;
                }
                QLineEdit, QComboBox {
                    background-color: #1E293B;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 8px 12px;
                    color: #FFFFFF;
                    font-size: 13px;
                }
                QLineEdit:focus, QComboBox:focus {
                    border: 1px solid #3B82F6;
                }
                QPushButton {
                    background-color: #2563EB;
                    color: white;
                    font-weight: bold;
                    border-radius: 6px;
                    padding: 10px 16px;
                    font-size: 13px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #1D4ED8;
                }
            """)
            self.init_ui()

        def init_ui(self):
            layout = QVBoxLayout(self)
            layout.setContentsMargins(28, 24, 28, 24)
            layout.setSpacing(14)

            # Header
            header = QLabel("AKP LICENSE GENERATOR")
            header.setStyleSheet("font-size: 18px; font-weight: 800; color: #60A5FA; letter-spacing: 0.8px;")
            sub_header = QLabel("Buat Kunci Lisensi Resmi Berdasarkan Machine ID Klien")
            sub_header.setStyleSheet("font-size: 12px; color: #94A3B8;")
            layout.addWidget(header)
            layout.addWidget(sub_header)

            layout.addSpacing(6)

            # Machine ID Input
            lbl_mid = QLabel("Machine ID Klien:")
            lbl_mid.setStyleSheet("font-weight: 600;")
            self.input_mid = QLineEdit()
            self.input_mid.setPlaceholderText("Contoh: AKP-6DCA-0E64-ECAC-605C")
            layout.addWidget(lbl_mid)
            layout.addWidget(self.input_mid)

            # License Type
            lbl_type = QLabel("Masa Berlaku Lisensi:")
            lbl_type.setStyleSheet("font-weight: 600;")
            self.combo_type = QComboBox()
            self.combo_type.addItem("Permanen (Lifetime)", "PERM")
            self.combo_type.addItem("1 Bulan", "1M")
            self.combo_type.addItem("3 Bulan", "3M")
            self.combo_type.addItem("6 Bulan", "6M")
            self.combo_type.addItem("1 Tahun", "1Y")
            layout.addWidget(lbl_type)
            layout.addWidget(self.combo_type)

            # Generate Button
            btn_gen = QPushButton("Generate Kunci Lisensi")
            btn_gen.setCursor(Qt.PointingHandCursor)
            btn_gen.clicked.connect(self.generate_key)
            layout.addWidget(btn_gen)

            # Output Key
            lbl_res = QLabel("License Key Yang Dihasilkan:")
            lbl_res.setStyleSheet("font-weight: 600;")
            layout.addWidget(lbl_res)

            row_res = QHBoxLayout()
            self.input_result = QLineEdit()
            self.input_result.setReadOnly(True)
            self.input_result.setStyleSheet("background-color: #111827; color: #34D399; font-family: monospace; font-weight: bold; font-size: 14px; border: 1px solid #059669;")
            row_res.addWidget(self.input_result)

            btn_copy = QPushButton("Salin")
            btn_copy.setFixedWidth(80)
            btn_copy.setStyleSheet("background-color: #059669; color: white;")
            btn_copy.setCursor(Qt.PointingHandCursor)
            btn_copy.clicked.connect(self.copy_key)
            row_res.addWidget(btn_copy)
            layout.addLayout(row_res)

        def generate_key(self):
            mid = self.input_mid.text().strip().upper()
            if not mid:
                QMessageBox.warning(self, "Peringatan", "Silakan masukkan Machine ID klien terlebih dahulu.")
                return

            choice = self.combo_type.currentData()
            lic_type = "PERM"
            if choice != "PERM":
                # Hitung expiry
                now = datetime.now()
                if choice == "1M":
                    import calendar
                    month = now.month + 1
                    year = now.year + (month - 1) // 12
                    month = ((month - 1) % 12) + 1
                    exp_dt = now.replace(year=year, month=month)
                elif choice == "3M":
                    month = now.month + 3
                    year = now.year + (month - 1) // 12
                    month = ((month - 1) % 12) + 1
                    exp_dt = now.replace(year=year, month=month)
                elif choice == "6M":
                    month = now.month + 6
                    year = now.year + (month - 1) // 12
                    month = ((month - 1) % 12) + 1
                    exp_dt = now.replace(year=year, month=month)
                elif choice == "1Y":
                    exp_dt = now.replace(year=now.year + 1)
                lic_type = exp_dt.strftime("%Y%m%d")

            key = license_manager.generate_license_key(mid, lic_type)
            self.input_result.setText(key)

        def copy_key(self):
            text = self.input_result.text().strip()
            if text:
                QApplication.clipboard().setText(text)
                QMessageBox.information(self, "Disalin", "Kunci lisensi berhasil disalin ke clipboard!")

    win = KeygenWindow()
    win.exec()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_cli(sys.argv)
    else:
        run_gui()

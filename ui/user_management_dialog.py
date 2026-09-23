"""
AKP Beton Management System - User Management Dialog
Dialog Pengelolaan Pengguna Aplikasi (Tambah User, Ganti Password, Status Akun)
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QInputDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

import styles
import database

class UserManagementDialog(QDialog):
    user_data_changed = Signal()

    def __init__(self, current_user: dict, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.setWindowTitle("Kelola Pengguna Aplikasi - AKP Contruction Building")
        self.resize(750, 480)
        self.setMinimumSize(680, 420)

        self.init_ui()
        self.load_users()

    def init_ui(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {styles.COLOR_BG_APP};
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }}
            QTableWidget {{
                background-color: #FFFFFF;
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 6px;
                gridline-color: #F1F5F9;
                font-size: 13px;
            }}
            QHeaderView::section {{
                background-color: #F1F5F9;
                color: #334155;
                font-weight: 700;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #CBD5E1;
            }}
            QPushButton {{
                background-color: {styles.COLOR_PRIMARY};
                color: #FFFFFF;
                font-weight: 600;
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 12.5px;
            }}
            QPushButton:hover {{
                background-color: {styles.COLOR_PRIMARY_LIGHT};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # Header Info
        header_row = QHBoxLayout()
        header_left = QVBoxLayout()
        header_left.setSpacing(2)

        lbl_title = QLabel("Daftar Pengguna Sistem")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #0F172A;")

        lbl_desc = QLabel("Kelola akun yang memiliki hak akses untuk mengoperasikan aplikasi ini.")
        lbl_desc.setStyleSheet("font-size: 12px; color: #64748B;")

        header_left.addWidget(lbl_title)
        header_left.addWidget(lbl_desc)
        header_row.addLayout(header_left)
        header_row.addStretch()

        # Tombol Tambah User Baru
        btn_add = QPushButton("+ Tambah Pengguna Baru")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setFixedHeight(36)
        btn_add.clicked.connect(self.show_add_user_dialog)
        header_row.addWidget(btn_add)

        layout.addLayout(header_row)

        # Tabel Pengguna
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "ID", "Username", "Nama Lengkap", "Status Akun", "Terakhir Masuk"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)

        layout.addWidget(self.table)

        # Action Buttons Row
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.btn_reset_pwd = QPushButton("Ganti Password")
        self.btn_reset_pwd.setCursor(Qt.PointingHandCursor)
        self.btn_reset_pwd.setStyleSheet(f"background-color: #0284C7; color: white;")
        self.btn_reset_pwd.clicked.connect(self.change_password_selected)
        action_row.addWidget(self.btn_reset_pwd)

        self.btn_toggle_active = QPushButton("Aktifkan / Nonaktifkan")
        self.btn_toggle_active.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_active.setStyleSheet("background-color: #D97706; color: white;")
        self.btn_toggle_active.clicked.connect(self.toggle_active_selected)
        action_row.addWidget(self.btn_toggle_active)

        self.btn_delete = QPushButton("Hapus Pengguna")
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setStyleSheet("background-color: #DC2626; color: white;")
        self.btn_delete.clicked.connect(self.delete_user_selected)
        action_row.addWidget(self.btn_delete)

        action_row.addStretch()

        btn_close = QPushButton("Tutup")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #E2E8F0;
                color: #334155;
                font-weight: 600;
                border: 1px solid #CBD5E1;
            }
            QPushButton:hover {
                background-color: #CBD5E1;
            }
        """)
        btn_close.clicked.connect(self.accept)
        action_row.addWidget(btn_close)

        layout.addLayout(action_row)

    def load_users(self):
        self.table.setRowCount(0)
        users = database.get_all_users()

        for row_idx, u in enumerate(users):
            self.table.insertRow(row_idx)

            # ID
            item_id = QTableWidgetItem(str(u["id"]))
            item_id.setTextAlignment(Qt.AlignCenter)
            item_id.setData(Qt.UserRole, u)
            self.table.setItem(row_idx, 0, item_id)

            # Username
            item_u = QTableWidgetItem(u["username"])
            item_u.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.table.setItem(row_idx, 1, item_u)

            # Nama Lengkap
            item_name = QTableWidgetItem(u.get("nama_lengkap", "-"))
            self.table.setItem(row_idx, 2, item_name)

            # Status
            is_act = bool(u.get("is_active", 1))
            status_text = "Aktif" if is_act else "Nonaktif"
            item_status = QTableWidgetItem(status_text)
            item_status.setTextAlignment(Qt.AlignCenter)
            if is_act:
                item_status.setForeground(Qt.darkGreen)
            else:
                item_status.setForeground(Qt.red)
            self.table.setItem(row_idx, 3, item_status)

            # Terakhir Masuk
            last_l = u.get("last_login") or "Belum pernah"
            item_ll = QTableWidgetItem(str(last_l))
            item_ll.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 4, item_ll)

    def get_selected_user(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Peringatan", "Pilih salah satu pengguna pada tabel terlebih dahulu.")
            return None
        row = selected_rows[0].row()
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def show_add_user_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Tambah Pengguna Baru")
        dlg.setFixedSize(380, 310)
        dlg.setStyleSheet(f"""
            QDialog {{
                background-color: #FFFFFF;
                font-family: 'Segoe UI', sans-serif;
            }}
            QLineEdit {{
                border: 1.5px solid {styles.COLOR_BORDER};
                border-radius: 6px;
                padding: 8px 10px;
                font-size: 13px;
            }}
            QPushButton {{
                background-color: {styles.COLOR_PRIMARY};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 16px;
            }}
        """)

        layout = QVBoxLayout(dlg)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl_head = QLabel("Pendaftaran Akun Pengguna Baru")
        lbl_head.setStyleSheet("font-size: 14px; font-weight: bold; color: #1E3A8A;")
        layout.addWidget(lbl_head)

        layout.addWidget(QLabel("Username (untuk login):"))
        in_user = QLineEdit()
        in_user.setPlaceholderText("contoh: operator1")
        layout.addWidget(in_user)

        layout.addWidget(QLabel("Nama Lengkap:"))
        in_nama = QLineEdit()
        in_nama.setPlaceholderText("contoh: Budi Santoso")
        layout.addWidget(in_nama)

        layout.addWidget(QLabel("Password (minimal 4 karakter):"))
        in_pwd = QLineEdit()
        in_pwd.setEchoMode(QLineEdit.Password)
        in_pwd.setPlaceholderText("Masukkan password")
        layout.addWidget(in_pwd)

        layout.addSpacing(10)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Batal")
        btn_cancel.setStyleSheet("background-color: #E2E8F0; color: #334155;")
        btn_cancel.clicked.connect(dlg.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("Simpan Pengguna")
        def save():
            u = in_user.text().strip()
            n = in_nama.text().strip()
            p = in_pwd.text()
            if not u or not n or not p:
                QMessageBox.warning(dlg, "Validasi", "Semua kolom wajib diisi.")
                return
            if len(p) < 4:
                QMessageBox.warning(dlg, "Validasi", "Password minimal 4 karakter.")
                return

            ok, msg = database.create_user(u, p, n)
            if ok:
                QMessageBox.information(dlg, "Sukses", msg)
                dlg.accept()
                self.load_users()
                self.user_data_changed.emit()
            else:
                QMessageBox.critical(dlg, "Gagal", msg)

        btn_save.clicked.connect(save)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

        dlg.exec()

    def change_password_selected(self):
        user = self.get_selected_user()
        if not user:
            return

        new_pwd, ok = QInputDialog.getText(
            self,
            "Ganti Password",
            f"Masukkan password baru untuk '{user['username']}':",
            QLineEdit.Password
        )
        if ok and new_pwd:
            if len(new_pwd) < 4:
                QMessageBox.warning(self, "Peringatan", "Password baru minimal 4 karakter.")
                return
            succeed, msg = database.change_user_password(user["id"], new_pwd)
            if succeed:
                QMessageBox.information(self, "Sukses", f"Password untuk akun '{user['username']}' berhasil diubah.")
                self.load_users()
                self.user_data_changed.emit()
            else:
                QMessageBox.critical(self, "Gagal", msg)

    def toggle_active_selected(self):
        user = self.get_selected_user()
        if not user:
            return

        current_active = bool(user.get("is_active", 1))
        new_active = 0 if current_active else 1
        act_text = "menonaktifkan" if current_active else "mengaktifkan"

        confirm = QMessageBox.question(
            self,
            "Konfirmasi",
            f"Apakah Anda yakin ingin {act_text} akun '{user['username']}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            ok, msg = database.update_user(user["id"], user["nama_lengkap"], new_active)
            if ok:
                QMessageBox.information(self, "Sukses", f"Status akun '{user['username']}' berhasil diperbarui.")
                self.load_users()
                self.user_data_changed.emit()
            else:
                QMessageBox.critical(self, "Gagal", msg)

    def delete_user_selected(self):
        user = self.get_selected_user()
        if not user:
            return

        if user["id"] == self.current_user.get("id"):
            QMessageBox.warning(self, "Peringatan", "Anda tidak dapat menghapus akun yang sedang Anda gunakan saat ini.")
            return

        confirm = QMessageBox.question(
            self,
            "Konfirmasi Hapus Akun",
            f"Apakah Anda yakin ingin MENGHAPUS akun pengguna '{user['username']}' ({user.get('nama_lengkap')})?\n\nTindakan ini tidak dapat dibatalkan.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            ok, msg = database.delete_user(user["id"])
            if ok:
                QMessageBox.information(self, "Sukses", msg)
                self.load_users()
                self.user_data_changed.emit()
            else:
                QMessageBox.critical(self, "Gagal", msg)

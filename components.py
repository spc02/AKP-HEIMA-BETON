"""
Custom Reusable UI Components untuk AKP Beton Desktop Application
Didesain dengan nuansa industrial modern, kontras tinggi, dan tanpa ikon emoji.
Setiap tombol memiliki styling langsung (self-contained) sehingga 100% terjamin warnanya.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QHeaderView, QAbstractItemView, QDialog,
    QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
import styles

# ==========================================
# 1. DEDICATED BUTTON COMPONENTS (100% RELIABLE)
# ==========================================
class PrimaryButton(QPushButton):
    """Tombol utama berwarna Biru Navy solid dengan teks putih kontras tinggi"""
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.COLOR_PRIMARY};
                color: #FFFFFF;
                border: 1px solid {styles.COLOR_PRIMARY_DARK};
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {styles.COLOR_PRIMARY_LIGHT};
                border-color: {styles.COLOR_PRIMARY_LIGHT};
                color: #FFFFFF;
            }}
            QPushButton:pressed {{
                background-color: {styles.COLOR_PRIMARY_DARK};
                color: #FFFFFF;
            }}
            QPushButton:disabled {{
                background-color: #94A3B8;
                color: #F1F5F9;
                border-color: #94A3B8;
            }}
        """)


class SecondaryButton(QPushButton):
    """Tombol sekunder berwarna abu terang dengan border slate dan teks gelap"""
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #F1F5F9;
                color: {styles.COLOR_TEXT_MAIN};
                border: 1.5px solid {styles.COLOR_BORDER};
                border-radius: 6px;
                padding: 7px 16px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #E2E8F0;
                border-color: {styles.COLOR_SECONDARY};
                color: {styles.COLOR_TEXT_MAIN};
            }}
            QPushButton:pressed {{
                background-color: #CBD5E1;
            }}
        """)


class SuccessButton(QPushButton):
    """Tombol aksi sukses / simpan / ekspor excel berwarna Hijau Emerald solid"""
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.COLOR_SUCCESS};
                color: #FFFFFF;
                border: 1px solid #047857;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #10B981;
                border-color: #10B981;
                color: #FFFFFF;
            }}
            QPushButton:pressed {{
                background-color: #047857;
                color: #FFFFFF;
            }}
        """)


class DangerButton(QPushButton):
    """Tombol bahaya / hapus permanen berwarna Merah solid"""
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.COLOR_DANGER};
                color: #FFFFFF;
                border: 1px solid #B91C1C;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #EF4444;
                color: #FFFFFF;
            }}
            QPushButton:pressed {{
                background-color: #B91C1C;
                color: #FFFFFF;
            }}
        """)


class TableDetailButton(QPushButton):
    """Tombol Lihat Detail pada baris tabel (Clean, Corporate)"""
    def __init__(self, text: str = "Detail", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #EFF6FF;
                color: #1D4ED8;
                border: 1.5px solid #93C5FD;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
                min-width: 52px;
            }}
            QPushButton:hover {{
                background-color: #DBEAFE;
                color: #1E40AF;
                border-color: #3B82F6;
            }}
            QPushButton:pressed {{
                background-color: #BFDBFE;
                color: #1E3A8A;
            }}
        """)


class TableEditButton(QPushButton):
    """Tombol Edit di dalam sel tabel"""
    def __init__(self, text: str = "Edit", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #F1F5F9;
                color: #0F172A;
                border: 1.5px solid #94A3B8;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
                min-width: 52px;
            }}
            QPushButton:hover {{
                background-color: #E2E8F0;
                color: #0F172A;
                border-color: #475569;
            }}
            QPushButton:pressed {{
                background-color: #CBD5E1;
            }}
        """)


class TableDeleteButton(QPushButton):
    """Tombol Hapus di dalam sel tabel"""
    def __init__(self, text: str = "Hapus", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #FEF2F2;
                color: #DC2626;
                border: 1.5px solid #FCA5A5;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
                min-width: 52px;
            }}
            QPushButton:hover {{
                background-color: #FEE2E2;
                color: #B91C1C;
                border-color: #EF4444;
            }}
            QPushButton:pressed {{
                background-color: #FECACA;
                color: #991B1B;
            }}
        """)


class TablePayButton(QPushButton):
    """Tombol Bayar / Pelunasan di dalam sel tabel"""
    def __init__(self, text: str = "Bayar", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #ECFDF5;
                color: #047857;
                border: 1.5px solid #6EE7B7;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
                min-width: 52px;
            }}
            QPushButton:hover {{
                background-color: #D1FAE5;
                color: #065F46;
                border-color: #34D399;
            }}
            QPushButton:pressed {{
                background-color: #A7F3D0;
            }}
        """)


class TableDetailButton(QPushButton):
    """Tombol Detail di dalam sel tabel"""
    def __init__(self, text: str = "Detail", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #F0F9FF;
                color: #0284C7;
                border: 1.5px solid #7DD3FC;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
                min-width: 52px;
            }}
            QPushButton:hover {{
                background-color: #E0F2FE;
                color: #0369A1;
                border-color: #0284C7;
            }}
        """)


# ==========================================
# 2. KARTU STATISTIK (STAT CARD)
# ==========================================
class StatCard(QFrame):
    """Kartu metrik ringkasan KPI untuk Dashboard dan Keuangan"""
    def __init__(self, title: str, value: str, subtitle: str = "", accent_color: str = styles.COLOR_PRIMARY_LIGHT, parent=None):
        super().__init__(parent)
        self.setProperty("class", "CardWidget")
        self.accent_color = accent_color
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        # Judul Metrik
        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 700;
            color: {styles.COLOR_TEXT_MUTED};
            letter-spacing: 0.5px;
        """)
        layout.addWidget(self.lbl_title)

        # Nilai Utama
        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 800;
            color: {styles.COLOR_TEXT_MAIN};
        """)
        layout.addWidget(self.lbl_value)

        # Subtitle / Keterangan Tambahan
        self.lbl_subtitle = QLabel(subtitle or "")
        self.lbl_subtitle.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 500;
            color: {styles.COLOR_TEXT_LIGHT};
        """)
        layout.addWidget(self.lbl_subtitle)

    def update_value(self, new_value: str, new_subtitle: str = None):
        self.lbl_value.setText(new_value)
        if new_subtitle is not None:
            self.lbl_subtitle.setText(new_subtitle)


# ==========================================
# 3. STATUS BADGE LABEL
# ==========================================
class BadgeLabel(QLabel):
    """Pill badge status (mis. Lunas, Hutang, Aktif, Selesai, dsb)"""
    def __init__(self, text: str, variant: str = "info", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(24)
        
        variants = {
            "success": (styles.COLOR_SUCCESS_BG, styles.COLOR_SUCCESS, "#A7F3D0"),
            "danger": (styles.COLOR_DANGER_BG, styles.COLOR_DANGER, "#FECACA"),
            "warning": (styles.COLOR_WARNING_BG, styles.COLOR_WARNING, "#FDE68A"),
            "info": (styles.COLOR_INFO_BG, styles.COLOR_INFO, "#BAE6FD"),
            "neutral": ("#F1F5F9", styles.COLOR_TEXT_MUTED, styles.COLOR_BORDER)
        }
        
        bg, fg, border = variants.get(variant, variants["neutral"])
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 12px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 700;
            }}
        """)


# ==========================================
# 4. MODERN TABLE WIDGET
# ==========================================
class ModernTableWidget(QTableWidget):
    """Tabel data serbaguna dengan header ber-kontras tinggi dan spasi baris yang lega"""
    def __init__(self, headers: list, parent=None):
        super().__init__(0, len(headers), parent)
        self.setHorizontalHeaderLabels(headers)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(42) # Tinggi baris lega agar tombol aksi tidak terpotong
        self.setShowGrid(False)

        # Header Configuration
        header = self.horizontalHeader()
        # Jika kolom terakhir adalah "Aksi", beri lebar fixed agar tidak berubah-ubah.
        # Kolom utama (sebelum terakhir) yang akan stretch mengisi sisa ruang.
        _last_col = len(headers) - 1
        if headers and headers[-1] == "Aksi":
            header.setStretchLastSection(False)
            # Stretch kolom sebelum Aksi (kolom konten terlebar)
            if _last_col > 0:
                header.setSectionResizeMode(_last_col - 1, QHeaderView.Stretch)
            # Fix lebar kolom Aksi
            header.setSectionResizeMode(_last_col, QHeaderView.Fixed)
            self.setColumnWidth(_last_col, 260)
        else:
            header.setStretchLastSection(True)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setHighlightSections(False)

    def clear_cell_widgets(self):
        """Mencegah bug Qt di mana widget sel lama menjadi orphan di viewport (0, 0)"""
        for r in range(self.rowCount()):
            for c in range(self.columnCount()):
                w = self.cellWidget(r, c)
                if w is not None:
                    self.removeCellWidget(r, c)
                    w.setParent(None)
                    w.deleteLater()

    def setRowCount(self, rows: int):
        self.clear_cell_widgets()
        super().setRowCount(rows)

    def clearContents(self):
        self.clear_cell_widgets()
        super().clearContents()

    def setCellWidget(self, row: int, column: int, widget):
        old_w = self.cellWidget(row, column)
        if old_w is not None and old_w is not widget:
            self.removeCellWidget(row, column)
            old_w.setParent(None)
            old_w.deleteLater()
        super().setCellWidget(row, column, widget)

        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: #FFFFFF;
                alternate-background-color: #F8FAFC;
                color: {styles.COLOR_TEXT_MAIN};
                border: 1px solid {styles.COLOR_BORDER_LIGHT};
                border-radius: 8px;
                gridline-color: #F1F5F9;
                selection-background-color: #DBEAFE;
                selection-color: {styles.COLOR_PRIMARY_DARK};
                font-size: 13px;
            }}
            QHeaderView::section {{
                background-color: #F1F5F9;
                color: #0F172A;
                padding: 6px 8px;
                border: none;
                border-bottom: 2px solid {styles.COLOR_BORDER};
                font-weight: 700;
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 4px 8px;
                color: {styles.COLOR_TEXT_MAIN};
            }}
            QTableWidget::item:selected {{
                background-color: #DBEAFE;
                color: {styles.COLOR_PRIMARY_DARK};
                font-weight: 600;
            }}
        """)


# ==========================================
# 5. SECTION HEADER
# ==========================================
class SectionHeader(QWidget):
    """Header judul modul dengan deskripsi dan area tombol aksi"""
    def __init__(self, title: str, description: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)

        text_container = QVBoxLayout()
        text_container.setSpacing(2)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 800;
            color: {styles.COLOR_TEXT_MAIN};
        """)
        text_container.addWidget(self.lbl_title)

        if description:
            self.lbl_desc = QLabel(description)
            self.lbl_desc.setStyleSheet(f"""
                font-size: 12px;
                color: {styles.COLOR_TEXT_MUTED};
            """)
            text_container.addWidget(self.lbl_desc)

        layout.addLayout(text_container)
        layout.addStretch()

        self.action_layout = QHBoxLayout()
        self.action_layout.setSpacing(8)
        layout.addLayout(self.action_layout)

    def add_action_button(self, button: QPushButton):
        self.action_layout.addWidget(button)


# ==========================================
# 6. MODERN MODAL DIALOG
# ==========================================
class ModernDialog(QDialog):
    """Modal dialog standar dengan layout bersih, tombol ber-kontras tinggi dan tanpa duplikasi judul"""
    def __init__(self, title: str, parent=None, min_width: int = 480):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(min_width)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(16)

        # Content Area
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(12)
        self.main_layout.addLayout(self.content_layout)

        # Footer Actions (Batal & Simpan)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = SecondaryButton("Batal")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = PrimaryButton("Simpan")
        self.btn_save.setDefault(True)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        self.main_layout.addLayout(btn_layout)


# ==========================================
# 7. CONFIRMATION & NOTIFICATION DIALOG HELPERS
# ==========================================
def confirm_dialog(parent, title: str, message: str) -> bool:
    """Kotak dialog konfirmasi aksi (hapus, batal) dengan tombol Ya/Tidak jelas"""
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(QMessageBox.Question)
    msg_box.setStyleSheet("""
        QMessageBox {
            background-color: #FFFFFF;
        }
        QLabel {
            color: #0F172A;
            font-size: 13px;
            font-weight: 500;
        }
    """)
    
    btn_yes = DangerButton("Ya, Lanjutkan")
    btn_no = SecondaryButton("Batal")
    
    msg_box.addButton(btn_yes, QMessageBox.YesRole)
    msg_box.addButton(btn_no, QMessageBox.NoRole)
    
    msg_box.exec()
    return msg_box.clickedButton() == btn_yes


def show_info_dialog(parent, title: str, message: str):
    """Kotak dialog informasi dengan tombol OK Biru Navy solid yang 100% jelas terlihat"""
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setStyleSheet("""
        QMessageBox {
            background-color: #FFFFFF;
        }
        QLabel {
            color: #0F172A;
            font-size: 13px;
            font-weight: 500;
        }
    """)
    btn_ok = PrimaryButton("  OK  ")
    btn_ok.setMinimumWidth(80)
    btn_ok.clicked.connect(msg_box.accept)
    msg_box.addButton(btn_ok, QMessageBox.AcceptRole)
    msg_box.exec()
    return QMessageBox.Ok


def show_warning_dialog(parent, title: str, message: str, buttons=QMessageBox.Ok, *args, **kwargs):
    """Kotak dialog peringatan dengan tombol yang 100% jelas terlihat"""
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(QMessageBox.Warning)
    msg_box.setStyleSheet("""
        QMessageBox {
            background-color: #FFFFFF;
        }
        QLabel {
            color: #0F172A;
            font-size: 13px;
            font-weight: 500;
        }
    """)
    if buttons == QMessageBox.Ok or buttons == 0:
        btn_ok = PrimaryButton("  OK  ")
        btn_ok.setMinimumWidth(80)
        btn_ok.clicked.connect(msg_box.accept)
        msg_box.addButton(btn_ok, QMessageBox.AcceptRole)
        msg_box.exec()
        return QMessageBox.Ok
    else:
        btn_yes = None
        btn_no = None
        if int(buttons) & int(QMessageBox.Yes):
            btn_yes = DangerButton("Ya, Lanjutkan")
            msg_box.addButton(btn_yes, QMessageBox.YesRole)
        if int(buttons) & int(QMessageBox.No):
            btn_no = SecondaryButton("Batal")
            msg_box.addButton(btn_no, QMessageBox.NoRole)
        if int(buttons) & int(QMessageBox.Cancel):
            btn_cancel = SecondaryButton("Batal")
            msg_box.addButton(btn_cancel, QMessageBox.RejectRole)
        msg_box.exec()
        if msg_box.clickedButton() == btn_yes:
            return QMessageBox.Yes
        return QMessageBox.No


def show_error_dialog(parent, title: str, message: str):
    """Kotak dialog error dengan tombol OK yang 100% jelas terlihat"""
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setStyleSheet("""
        QMessageBox {
            background-color: #FFFFFF;
        }
        QLabel {
            color: #0F172A;
            font-size: 13px;
            font-weight: 500;
        }
    """)
    btn_ok = DangerButton("  OK  ")
    btn_ok.setMinimumWidth(80)
    btn_ok.clicked.connect(msg_box.accept)
    msg_box.addButton(btn_ok, QMessageBox.AcceptRole)
    msg_box.exec()
    return QMessageBox.Ok


def show_question_dialog(parent, title: str, message: str, buttons=QMessageBox.Yes | QMessageBox.No, default_button=QMessageBox.Yes, *args, **kwargs):
    """Kotak dialog pertanyaan/konfirmasi dengan tombol ber-kontras tinggi yang 100% jelas terlihat"""
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(QMessageBox.Question)
    msg_box.setStyleSheet("""
        QMessageBox {
            background-color: #FFFFFF;
        }
        QLabel {
            color: #0F172A;
            font-size: 13px;
            font-weight: 500;
        }
    """)

    btn_yes = None
    btn_no = None
    btn_ok = None
    btn_cancel = None

    b_val = int(buttons) if buttons is not None else int(QMessageBox.Yes | QMessageBox.No)

    if b_val & int(QMessageBox.Yes):
        btn_yes = PrimaryButton("  Ya  ")
        btn_yes.setMinimumWidth(80)
        msg_box.addButton(btn_yes, QMessageBox.YesRole)

    if b_val & int(QMessageBox.No):
        btn_no = SecondaryButton("  Tidak  ")
        btn_no.setMinimumWidth(80)
        msg_box.addButton(btn_no, QMessageBox.NoRole)

    if (b_val & int(QMessageBox.Ok)) and not btn_yes:
        btn_ok = PrimaryButton("  OK  ")
        btn_ok.setMinimumWidth(80)
        msg_box.addButton(btn_ok, QMessageBox.AcceptRole)

    if b_val & int(QMessageBox.Cancel):
        btn_cancel = SecondaryButton("  Batal  ")
        btn_cancel.setMinimumWidth(80)
        msg_box.addButton(btn_cancel, QMessageBox.RejectRole)

    def_val = int(default_button) if default_button is not None else int(QMessageBox.Yes)
    if (def_val & int(QMessageBox.Yes)) and btn_yes:
        btn_yes.setDefault(True)
    elif (def_val & int(QMessageBox.No)) and btn_no:
        btn_no.setDefault(True)
    elif (def_val & int(QMessageBox.Ok)) and btn_ok:
        btn_ok.setDefault(True)

    msg_box.exec()
    clicked = msg_box.clickedButton()
    if clicked == btn_yes:
        return QMessageBox.Yes
    elif clicked == btn_no:
        return QMessageBox.No
    elif clicked == btn_ok:
        return QMessageBox.Ok
    elif clicked == btn_cancel:
        return QMessageBox.Cancel
    return QMessageBox.No


# Otomatis redirect static method QMessageBox agar seluruh sistem menggunakan tombol kontras tinggi
QMessageBox.information = staticmethod(show_info_dialog)
QMessageBox.warning = staticmethod(show_warning_dialog)
QMessageBox.critical = staticmethod(show_error_dialog)
QMessageBox.question = staticmethod(show_question_dialog)


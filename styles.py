"""
Styling System dan QSS Stylesheet untuk AKP Beton Desktop Application.
Menyediakan tema industrial modern bernuansa profesional, bersih, kontras tinggi, dan tanpa ikon emoji.
"""

# Palet Warna Utama
COLOR_PRIMARY = "#1E3A8A"       # Navy Blue AKP
COLOR_PRIMARY_LIGHT = "#2563EB" # Bright Blue
COLOR_PRIMARY_DARK = "#172554"  # Deep Navy
COLOR_SECONDARY = "#475569"     # Slate 600
COLOR_BG_APP = "#F8FAFC"        # Slate 50
COLOR_SURFACE = "#FFFFFF"       # Pure White
COLOR_BORDER = "#CBD5E1"        # Slate 300
COLOR_BORDER_LIGHT = "#E2E8F0"  # Slate 200

COLOR_SUCCESS = "#059669"       # Emerald 600
COLOR_SUCCESS_BG = "#ECFDF5"    # Emerald 50
COLOR_WARNING = "#D97706"       # Amber 600
COLOR_WARNING_BG = "#FFFBEB"    # Amber 50
COLOR_DANGER = "#DC2626"        # Red 600
COLOR_DANGER_BG = "#FEF2F2"     # Red 50
COLOR_INFO = "#0284C7"          # Sky 600
COLOR_INFO_BG = "#F0F9FF"       # Sky 50

COLOR_TEXT_MAIN = "#0F172A"     # Slate 900 (Sangat Jelas / Kontras Tinggi)
COLOR_TEXT_MUTED = "#475569"    # Slate 600
COLOR_TEXT_LIGHT = "#64748B"    # Slate 500

# Stylesheet Global QSS
GLOBAL_STYLESHEET = f"""
/* Global Reset & Base */
QWidget {{
    font-family: 'Segoe UI', 'SF Pro Display', -apple-system, 'Roboto', sans-serif;
    font-size: 13px;
    color: {COLOR_TEXT_MAIN};
    background-color: transparent;
}}

QMainWindow, QDialog {{
    background-color: {COLOR_BG_APP};
    color: {COLOR_TEXT_MAIN};
}}

/* ScrollBar Styling */
QScrollBar:vertical {{
    border: none;
    background: #F1F5F9;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: #CBD5E1;
    min-height: 25px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: #94A3B8;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    border: none;
    background: #F1F5F9;
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: #CBD5E1;
    min-width: 25px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #94A3B8;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Card Container */
QFrame.CardWidget, QFrame[class="CardWidget"] {{
    background-color: {COLOR_SURFACE};
    border-radius: 8px;
    border: 1px solid {COLOR_BORDER_LIGHT};
}}

/* Form Input Controls - Single Line (Consistent 32px Height) */
QLineEdit, QDoubleSpinBox, QSpinBox {{
    background-color: #FFFFFF;
    border: 1.5px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 4px 10px;
    margin: 2px 0px;
    color: {COLOR_TEXT_MAIN};
    font-size: 13px;
    min-height: 32px;
    max-height: 32px;
    selection-background-color: {COLOR_PRIMARY_LIGHT};
    selection-color: #FFFFFF;
}}

/* Form Input Controls - Multi Line */
QTextEdit, QPlainTextEdit {{
    background-color: #FFFFFF;
    border: 1.5px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    margin: 2px 0px;
    color: {COLOR_TEXT_MAIN};
    font-size: 13px;
    min-height: 60px;
    selection-background-color: {COLOR_PRIMARY_LIGHT};
    selection-color: #FFFFFF;
}}

QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1.5px solid {COLOR_PRIMARY_LIGHT};
    background-color: #FFFFFF;
    color: {COLOR_TEXT_MAIN};
}}

QLineEdit:disabled, QDateEdit:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled, QComboBox:disabled {{
    background-color: #F1F5F9;
    color: #94A3B8;
    border-color: #CBD5E1;
}}

/* ========================================================================= */
/* QDateEdit Controls - Teks Tanggal Hitam/Dark, Bebas Warna Biru            */
/* ========================================================================= */
QDateEdit {{
    background-color: #FFFFFF;
    border: 1.5px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 4px 10px;
    margin: 2px 0px;
    color: #0F172A;
    font-size: 13px;
    font-weight: 600;
    min-height: 32px;
    max-height: 32px;
    selection-background-color: #E2E8F0;
    selection-color: #0F172A;
}}

QDateEdit:focus {{
    border: 1.5px solid {COLOR_PRIMARY_LIGHT};
    background-color: #FFFFFF;
    color: #0F172A;
    selection-background-color: #E2E8F0;
    selection-color: #0F172A;
}}

QDateEdit QLineEdit {{
    color: #0F172A;
    background-color: transparent;
    selection-background-color: #E2E8F0;
    selection-color: #0F172A;
}}

QDateEdit::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid {COLOR_BORDER_LIGHT};
    background-color: #F8FAFC;
    border-top-right-radius: 5px;
    border-bottom-right-radius: 5px;
}}

QDateEdit::drop-down:hover {{
    background-color: #E2E8F0;
}}

QDateEdit::down-arrow {{
    width: 0px;
    height: 0px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #334155;
    margin-right: 1px;
}}

/* ========================================================================= */
/* QCalendarWidget - Tampilan Bersih, Terang, Modern & Sangat Mudah Dibaca   */
/* ========================================================================= */
QCalendarWidget {{
    background-color: #FFFFFF;
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
}}

QCalendarWidget QWidget {{
    alternate-background-color: #FFFFFF;
    background-color: #FFFFFF;
}}

/* Navigation Bar (Bulan dan Tahun) */
QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background-color: #F8FAFC;
    border-bottom: 1px solid #E2E8F0;
    min-height: 38px;
}}

/* Tombol Prev & Next Month */
QCalendarWidget QToolButton#qt_calendar_prevmonth {{
    qproperty-icon: none;
    qproperty-text: "<";
    color: #0F172A;
    font-size: 14px;
    font-weight: 800;
    background-color: transparent;
    border: none;
    border-radius: 4px;
    min-width: 30px;
    min-height: 28px;
}}

QCalendarWidget QToolButton#qt_calendar_nextmonth {{
    qproperty-icon: none;
    qproperty-text: ">";
    color: #0F172A;
    font-size: 14px;
    font-weight: 800;
    background-color: transparent;
    border: none;
    border-radius: 4px;
    min-width: 30px;
    min-height: 28px;
}}

QCalendarWidget QToolButton#qt_calendar_prevmonth:hover,
QCalendarWidget QToolButton#qt_calendar_nextmonth:hover {{
    background-color: #E2E8F0;
    color: #0F172A;
}}

/* Tombol Bulan & Tahun */
QCalendarWidget QToolButton#qt_calendar_monthbutton,
QCalendarWidget QToolButton#qt_calendar_yearbutton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    color: #0F172A;
    font-size: 13px;
    font-weight: 700;
    padding: 3px 8px;
}}

QCalendarWidget QToolButton#qt_calendar_monthbutton:hover,
QCalendarWidget QToolButton#qt_calendar_yearbutton:hover {{
    background-color: #E2E8F0;
    border: 1px solid #CBD5E1;
    color: #0F172A;
}}

/* Spinbox Tahun jika diklik */
QCalendarWidget QSpinBox {{
    background-color: #FFFFFF;
    color: #0F172A;
    font-size: 13px;
    font-weight: 700;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    selection-background-color: #E2E8F0;
    selection-color: #0F172A;
}}

/* Dropdown Menu Pilih Bulan */
QCalendarWidget QMenu {{
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 4px;
}}

QCalendarWidget QMenu::item {{
    padding: 5px 16px;
    border-radius: 4px;
    color: #0F172A;
}}

QCalendarWidget QMenu::item:selected {{
    background-color: #F1F5F9;
    color: #0F172A;
    font-weight: 700;
}}

/* Grid Tanggal Hari - Background Putih Bersih, Teks Hitam/Dark */
QCalendarWidget QAbstractItemView:enabled,
QCalendarWidget QTableView,
QCalendarWidget #qt_calendar_calendarview {{
    background-color: #FFFFFF;
    alternate-background-color: #FFFFFF;
    color: #0F172A;
    font-size: 13px;
    font-weight: 600;
    selection-background-color: #0F172A;
    selection-color: #FFFFFF;
    gridline-color: transparent;
    border: none;
    outline: none;
}}

QCalendarWidget QAbstractItemView:disabled {{
    color: #94A3B8;
}}

QCalendarWidget QAbstractItemView:item:hover,
QCalendarWidget QTableView:item:hover {{
    background-color: #F1F5F9;
    color: #0F172A;
    border-radius: 6px;
}}

QCalendarWidget QAbstractItemView:item:selected,
QCalendarWidget QTableView:item:selected {{
    background-color: #0F172A;
    color: #FFFFFF;
    border-radius: 6px;
    font-weight: 700;
}}

/* Header Nama Hari (Sen, Sel, Rab, dst.) */
QCalendarWidget QHeaderView {{
    background-color: #FFFFFF;
    border: none;
}}

QCalendarWidget QHeaderView::section {{
    background-color: #FFFFFF;
    color: #475569;
    font-size: 11.5px;
    font-weight: 700;
    border: none;
    padding: 5px 0px;
}}

/* QDoubleSpinBox & QSpinBox - Clean Numeric Input (Tanpa tombol panah atas/bawah agar tidak salah klik/scroll) */
QDoubleSpinBox, QSpinBox {{
    padding-right: 8px;
}}

QDoubleSpinBox::up-button, QSpinBox::up-button,
QDoubleSpinBox::down-button, QSpinBox::down-button {{
    width: 0px;
    height: 0px;
    border: none;
    background: transparent;
}}

QDoubleSpinBox::up-arrow, QSpinBox::up-arrow,
QDoubleSpinBox::down-arrow, QSpinBox::down-arrow {{
    width: 0px;
    height: 0px;
    border: none;
    background: transparent;
}}

/* QComboBox Super Explicit Styling */
QComboBox {{
    background-color: #FFFFFF;
    border: 1.5px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 4px 10px;
    margin: 2px 0px;
    color: {COLOR_TEXT_MAIN};
    font-size: 13px;
    min-height: 32px;
    max-height: 32px;
}}

QComboBox:focus, QComboBox:hover {{
    border: 1.5px solid {COLOR_PRIMARY_LIGHT};
    color: {COLOR_TEXT_MAIN};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid {COLOR_BORDER_LIGHT};
    background-color: #F8FAFC;
    border-top-right-radius: 5px;
    border-bottom-right-radius: 5px;
}}

QComboBox::drop-down:hover {{
    background-color: #E2E8F0;
}}

QComboBox::down-arrow {{
    width: 0px;
    height: 0px;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #334155;
    margin-right: 1px;
}}

QComboBox QAbstractItemView, QComboBox QListView {{
    background-color: #FFFFFF;
    color: {COLOR_TEXT_MAIN};
    border: 1.5px solid #CBD5E1;
    border-radius: 8px;
    padding: 4px;
    outline: none;
    selection-background-color: #EFF6FF;
    selection-color: #1D4ED8;
}}

QComboBox QAbstractItemView::item, QComboBox QListView::item {{
    background-color: #FFFFFF;
    color: #0F172A;
    padding: 6px 12px;
    min-height: 28px;
    border-radius: 4px;
}}

QComboBox QAbstractItemView::item:selected, QComboBox QAbstractItemView::item:hover,
QComboBox QListView::item:selected, QComboBox QListView::item:hover {{
    background-color: #EFF6FF;
    color: #1D4ED8;
    font-weight: 600;
}}

/* Base QPushButton Styling (Default Safety: Dark Navy with White Text) */
QPushButton {{
    background-color: {COLOR_PRIMARY};
    color: #FFFFFF;
    border: 1px solid {COLOR_PRIMARY_DARK};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 700;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {COLOR_PRIMARY_LIGHT};
    border-color: {COLOR_PRIMARY_LIGHT};
}}
QPushButton:pressed {{
    background-color: {COLOR_PRIMARY_DARK};
}}
QPushButton:disabled {{
    background-color: #94A3B8;
    color: #F1F5F9;
    border-color: #94A3B8;
}}

/* Tombol Utama (Primary Button) - Mendukung class property */
QPushButton[class="PrimaryBtn"], QPushButton.PrimaryBtn {{
    background-color: {COLOR_PRIMARY};
    color: #FFFFFF;
    border: 1px solid {COLOR_PRIMARY_DARK};
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 700;
    font-size: 13px;
}}
QPushButton[class="PrimaryBtn"]:hover, QPushButton.PrimaryBtn:hover {{
    background-color: {COLOR_PRIMARY_LIGHT};
    border-color: {COLOR_PRIMARY_LIGHT};
}}
QPushButton[class="PrimaryBtn"]:pressed, QPushButton.PrimaryBtn:pressed {{
    background-color: {COLOR_PRIMARY_DARK};
}}

/* Tombol Sukses (Success Button) */
QPushButton[class="SuccessBtn"], QPushButton.SuccessBtn {{
    background-color: {COLOR_SUCCESS};
    color: #FFFFFF;
    border: 1px solid #047857;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 700;
    font-size: 13px;
}}
QPushButton[class="SuccessBtn"]:hover, QPushButton.SuccessBtn:hover {{
    background-color: #10B981;
    border-color: #10B981;
}}
QPushButton[class="SuccessBtn"]:pressed, QPushButton.SuccessBtn:pressed {{
    background-color: #047857;
}}

/* Tombol Bahaya / Hapus (Danger Button) */
QPushButton[class="DangerBtn"], QPushButton.DangerBtn {{
    background-color: {COLOR_DANGER};
    color: #FFFFFF;
    border: 1px solid #B91C1C;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 700;
    font-size: 13px;
}}
QPushButton[class="DangerBtn"]:hover, QPushButton.DangerBtn:hover {{
    background-color: #EF4444;
}}
QPushButton[class="DangerBtn"]:pressed, QPushButton.DangerBtn:pressed {{
    background-color: #B91C1C;
}}

/* Tombol Sekunder / Outline (Secondary Button) */
QPushButton[class="SecondaryBtn"], QPushButton.SecondaryBtn {{
    background-color: #F1F5F9;
    color: {COLOR_TEXT_MAIN};
    border: 1.5px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 700;
    font-size: 13px;
}}
QPushButton[class="SecondaryBtn"]:hover, QPushButton.SecondaryBtn:hover {{
    background-color: #E2E8F0;
    border-color: {COLOR_SECONDARY};
    color: {COLOR_TEXT_MAIN};
}}
QPushButton[class="SecondaryBtn"]:pressed, QPushButton.SecondaryBtn:pressed {{
    background-color: #CBD5E1;
}}

/* Tombol Aksi Tabel Ringkas & Jelas */
QPushButton[class="TableActionEdit"], QPushButton.TableActionEdit {{
    background-color: #F1F5F9;
    color: #0F172A;
    border: 1.5px solid #94A3B8;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 700;
    min-width: 52px;
}}
QPushButton[class="TableActionEdit"]:hover, QPushButton.TableActionEdit:hover {{
    background-color: #E2E8F0;
    color: #0F172A;
    border-color: #475569;
}}

QPushButton[class="TableActionDelete"], QPushButton.TableActionDelete {{
    background-color: #FEF2F2;
    color: #DC2626;
    border: 1.5px solid #FCA5A5;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 700;
    min-width: 52px;
}}
QPushButton[class="TableActionDelete"]:hover, QPushButton.TableActionDelete:hover {{
    background-color: #FEE2E2;
    color: #B91C1C;
    border-color: #EF4444;
}}

QPushButton[class="TableActionDetail"], QPushButton.TableActionDetail {{
    background-color: #F0F9FF;
    color: #0284C7;
    border: 1.5px solid #7DD3FC;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 700;
    min-width: 52px;
}}
QPushButton[class="TableActionDetail"]:hover, QPushButton.TableActionDetail:hover {{
    background-color: #E0F2FE;
    color: #0369A1;
    border-color: #0284C7;
}}

/* Modern Table Widget */
QTableWidget, QTableView {{
    background-color: #FFFFFF;
    color: {COLOR_TEXT_MAIN};
    border: 1px solid {COLOR_BORDER_LIGHT};
    border-radius: 8px;
    gridline-color: #F1F5F9;
    selection-background-color: #DBEAFE;
    selection-color: {COLOR_PRIMARY_DARK};
    font-size: 13px;
}}

QHeaderView::section {{
    background-color: #F1F5F9;
    color: #1E293B;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid {COLOR_BORDER};
    font-weight: 700;
    font-size: 12px;
}}

QTableWidget::item {{
    padding: 6px 8px;
    color: {COLOR_TEXT_MAIN};
    border-bottom: 1px solid #F1F5F9;
}}

QTableWidget::item:selected {{
    background-color: #DBEAFE;
    color: {COLOR_PRIMARY_DARK};
    font-weight: 600;
}}

/* Tab Widget Styling */
QTabWidget::pane {{
    border: 1px solid {COLOR_BORDER_LIGHT};
    background-color: #FFFFFF;
    border-radius: 8px;
    top: -1px;
}}

QTabWidget[class="CleanTabWidget"]::pane, QTabWidget#CleanTabWidget::pane {{
    border: none;
    background-color: transparent;
    border-radius: 0px;
    top: 0px;
}}

QTabBar::tab {{
    background-color: #F1F5F9;
    color: {COLOR_TEXT_MUTED};
    padding: 9px 18px;
    font-weight: 600;
    font-size: 13px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
    border: 1px solid {COLOR_BORDER_LIGHT};
    border-bottom: none;
}}

QTabBar::tab:selected {{
    background-color: #FFFFFF;
    color: {COLOR_PRIMARY};
    font-weight: 700;
    border: 1px solid {COLOR_BORDER};
    border-bottom: 2px solid #FFFFFF;
}}

QTabBar::tab:hover:!selected {{
    background-color: #E2E8F0;
    color: {COLOR_TEXT_MAIN};
}}

/* Sidebar Menu Button */
QPushButton[class="SidebarNavBtn"], QPushButton.SidebarNavBtn {{
    background-color: transparent;
    color: #CBD5E1;
    border: none;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 600;
    text-align: left;
}}

QPushButton[class="SidebarNavBtn"]:hover, QPushButton.SidebarNavBtn:hover {{
    background-color: rgba(255, 255, 255, 0.10);
    color: #FFFFFF;
}}

QPushButton[class="SidebarNavBtn"]:checked, QPushButton.SidebarNavBtn:checked {{
    background-color: {COLOR_PRIMARY_LIGHT};
    color: #FFFFFF;
    font-weight: 700;
}}

/* Sidebar Submenu Container & Sub-items */
QFrame#SidebarSubmenu, QFrame[class="SidebarSubmenu"] {{
    background-color: rgba(15, 23, 42, 0.45);
    border-left: 2.5px solid {COLOR_PRIMARY_LIGHT};
    border-radius: 4px;
    margin-left: 8px;
    margin-right: 2px;
    margin-top: 2px;
    margin-bottom: 4px;
}}

QPushButton[class="SidebarSubNavBtn"], QPushButton.SidebarSubNavBtn {{
    background-color: transparent;
    color: #94A3B8;
    border: none;
    border-radius: 4px;
    padding: 7px 10px 7px 12px;
    font-size: 12px;
    font-weight: 500;
    text-align: left;
}}

QPushButton[class="SidebarSubNavBtn"]:hover, QPushButton.SidebarSubNavBtn:hover {{
    background-color: rgba(255, 255, 255, 0.12);
    color: #FFFFFF;
    font-weight: 600;
}}

QPushButton[class="SidebarSubNavBtn"]:checked, QPushButton.SidebarSubNavBtn:checked {{
    background-color: {COLOR_PRIMARY_LIGHT};
    color: #FFFFFF;
    font-weight: 700;
}}

/* Group Box */
QGroupBox {{
    font-weight: 700;
    font-size: 13px;
    color: {COLOR_PRIMARY_DARK};
    border: 1.5px solid {COLOR_BORDER_LIGHT};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 14px;
    background-color: #FFFFFF;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #FFFFFF;
}}

/* Dialog Specific Box */
QDialog QFrame#DialogHeader {{
    background-color: #F8FAFC;
    border-bottom: 1px solid {COLOR_BORDER_LIGHT};
}}

QDialog QLabel {{
    color: {COLOR_TEXT_MAIN};
}}

/* ========================================================================= */
/* POPUP DIALOGS (QMessageBox, QDialogButtonBox, QInputDialog) */
/* ========================================================================= */
QMessageBox {{
    background-color: #FFFFFF;
    color: {COLOR_TEXT_MAIN};
}}

QMessageBox QLabel {{
    color: {COLOR_TEXT_MAIN};
    font-size: 13px;
    font-weight: 500;
    background-color: transparent;
    padding: 6px;
}}

QMessageBox QPushButton, QDialogButtonBox QPushButton, QInputDialog QPushButton {{
    background-color: {COLOR_PRIMARY};
    color: #FFFFFF;
    border: 1.5px solid {COLOR_PRIMARY_DARK};
    border-radius: 6px;
    padding: 7px 22px;
    font-weight: 700;
    font-size: 13px;
    min-width: 80px;
    min-height: 24px;
}}

QMessageBox QPushButton:hover, QDialogButtonBox QPushButton:hover, QInputDialog QPushButton:hover {{
    background-color: {COLOR_PRIMARY_LIGHT};
    border-color: {COLOR_PRIMARY_LIGHT};
    color: #FFFFFF;
}}

QMessageBox QPushButton:pressed, QDialogButtonBox QPushButton:pressed, QInputDialog QPushButton:pressed {{
    background-color: {COLOR_PRIMARY_DARK};
    border-color: {COLOR_PRIMARY_DARK};
    color: #FFFFFF;
}}

QMessageBox QPushButton:focus, QDialogButtonBox QPushButton:focus, QInputDialog QPushButton:focus {{
    outline: none;
    border: 2px solid {COLOR_PRIMARY_LIGHT};
    background-color: {COLOR_PRIMARY};
    color: #FFFFFF;
}}
"""

def format_rupiah(amount: float) -> str:
    """Format angka ke format Rupiah standar Indonesia: Rp 1.250.000"""
    if amount is None:
        return "Rp 0"
    is_neg = amount < 0
    val = abs(amount)
    formatted = f"{val:,.0f}".replace(",", ".")
    return f"-Rp {formatted}" if is_neg else f"Rp {formatted}"

def format_number(val: float, decimal_places: int = 2) -> str:
    """Format angka ribuan: 1.250,50"""
    if val is None:
        return "0"
    if decimal_places == 0 or val == int(val):
        return f"{int(val):,}".replace(",", ".")
    formatted = f"{val:,.{decimal_places}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted

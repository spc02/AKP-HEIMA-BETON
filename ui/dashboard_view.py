"""
Dashboard View untuk AKP Beton Desktop Application
Desain Dashboard Operasional Modern, Presisi & Terintegrasi Real-Time
Menggunakan Vector SVG Icons yang tajam, profesional, bersih, dan tanpa emoji sticker.
"""

import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QFrame, QPushButton, QTableWidgetItem, QHeaderView, QScrollArea,
    QProgressBar, QMessageBox, QSizePolicy, QDialog, QComboBox, QListView
)
from PySide6.QtCore import Qt, Signal, QByteArray
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtSvg import QSvgRenderer

from components import ModernTableWidget, SecondaryButton, PrimaryButton
import styles
import database


# ==============================================================================
# VECTOR SVG ASSETS (MODERN, CLEAN, INDUSTRIAL LINE-ART)
# ==============================================================================
SVG_CUBE_BLUE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
  <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
  <line x1="12" y1="22.08" x2="12" y2="12"/>
</svg>"""

SVG_CHART_GREEN = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#059669">
  <rect x="3" y="13" width="4.5" height="8" rx="1.5"/>
  <rect x="9.75" y="8" width="4.5" height="13" rx="1.5"/>
  <rect x="16.5" y="3" width="4.5" height="18" rx="1.5"/>
</svg>"""

SVG_TRUCK_PURPLE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#7C3AED" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="1" y="3" width="15" height="13" rx="2"/>
  <polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/>
  <circle cx="5.5" cy="18.5" r="2.5"/>
  <circle cx="18.5" cy="18.5" r="2.5"/>
</svg>"""

SVG_USERS_ORANGE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#EA580C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
  <circle cx="9" cy="7" r="4"/>
  <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
  <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
</svg>"""

SVG_WARNING_RED = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#DC2626" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
  <line x1="12" y1="9" x2="12" y2="13"/>
  <line x1="12" y1="17" x2="12.01" y2="17"/>
</svg>"""

SVG_BOX_NAVY = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#0F172A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
  <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
  <line x1="12" y1="22.08" x2="12" y2="12"/>
</svg>"""

SVG_CHART_NAVY = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#0F172A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <line x1="18" y1="20" x2="18" y2="10"/>
  <line x1="12" y1="20" x2="12" y2="4"/>
  <line x1="6" y1="20" x2="6" y2="14"/>
</svg>"""

SVG_TRUCK_NAVY = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#0F172A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <rect x="1" y="3" width="15" height="13" rx="2"/>
  <polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/>
  <circle cx="5.5" cy="18.5" r="2.5"/>
  <circle cx="18.5" cy="18.5" r="2.5"/>
</svg>"""


# ==============================================================================
# REUSABLE VECTOR SVG WIDGET
# ==============================================================================
class SvgIconWidget(QWidget):
    """Widget ringan untuk merender vector SVG secara tajam, presisi & anti-aliased"""
    def __init__(self, svg_xml: str, width: int = 24, height: int = 24, parent=None):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.renderer = QSvgRenderer(QByteArray(svg_xml.strip().encode("utf-8")))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.renderer.isValid():
            self.renderer.render(painter)


# ==============================================================================
# 1. KOMPONEN KARTU KPI METRIK UTAMA (4 KARTU ATAS DENGAN VECTOR ICON)
# ==============================================================================
class KPICardWidget(QFrame):
    def __init__(self, svg_xml: str, icon_bg: str, 
                 title: str, value: str, subtext: str, 
                 progress_val: int = -1, parent=None):
        super().__init__(parent)
        self.progress_val = progress_val
        self.setStyleSheet(f"""
            KPICardWidget {{
                background-color: #FFFFFF;
                border: 1px solid {styles.COLOR_BORDER_LIGHT};
                border-radius: 12px;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMinimumHeight(105)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        # Icon Frame (Rounded Square berlatar pastel lembut dengan vector SVG tajam)
        self.icon_frame = QFrame()
        self.icon_frame.setFixedSize(46, 46)
        self.icon_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {icon_bg};
                border-radius: 10px;
                border: 1px solid rgba(0, 0, 0, 0.04);
            }}
        """)
        icon_lay = QVBoxLayout(self.icon_frame)
        icon_lay.setContentsMargins(0, 0, 0, 0)
        icon_lay.setAlignment(Qt.AlignCenter)
        
        self.svg_icon = SvgIconWidget(svg_xml, width=22, height=22)
        icon_lay.addWidget(self.svg_icon)
        layout.addWidget(self.icon_frame, 0, Qt.AlignTop)

        # Content Box
        content_box = QVBoxLayout()
        content_box.setContentsMargins(0, 0, 0, 0)
        content_box.setSpacing(2)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569; background: transparent;")
        content_box.addWidget(self.lbl_title)

        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet("font-size: 22px; font-weight: 800; color: #0F172A; background: transparent; margin-top: 1px;")
        content_box.addWidget(self.lbl_value)

        # Subtext / Progress layout
        if progress_val >= 0:
            sub_row = QHBoxLayout()
            sub_row.setSpacing(8)
            self.lbl_subtext = QLabel(subtext)
            self.lbl_subtext.setStyleSheet("font-size: 11px; font-weight: 500; color: #64748B; background: transparent;")
            sub_row.addWidget(self.lbl_subtext)
            sub_row.addStretch()
            content_box.addLayout(sub_row)

            # Baris Progress Bar + Persen
            bar_row = QHBoxLayout()
            bar_row.setSpacing(6)
            self.pbar = QProgressBar()
            self.pbar.setRange(0, 100)
            self.pbar.setValue(min(100, max(0, progress_val)))
            self.pbar.setTextVisible(False)
            self.pbar.setFixedHeight(7)
            self.pbar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: #E2E8F0;
                    border-radius: 3.5px;
                    border: none;
                }}
                QProgressBar::chunk {{
                    background-color: {styles.COLOR_PRIMARY_LIGHT};
                    border-radius: 3.5px;
                }}
            """)
            bar_row.addWidget(self.pbar, 1)

            self.lbl_pct = QLabel(f"{progress_val}%")
            self.lbl_pct.setStyleSheet("font-size: 11px; font-weight: 700; color: #475569; background: transparent;")
            bar_row.addWidget(self.lbl_pct)
            content_box.addLayout(bar_row)
        else:
            self.lbl_subtext = QLabel(subtext)
            self.lbl_subtext.setStyleSheet("font-size: 11.5px; font-weight: 500; color: #64748B; background: transparent;")
            self.lbl_subtext.setWordWrap(True)
            content_box.addWidget(self.lbl_subtext)

        layout.addLayout(content_box, 1)

    def update_data(self, value: str, subtext: str, progress_val: int = -1):
        self.lbl_value.setText(value)
        self.lbl_subtext.setText(subtext)
        if hasattr(self, "pbar") and progress_val >= 0:
            self.pbar.setValue(min(100, max(0, progress_val)))
            if hasattr(self, "lbl_pct"):
                self.lbl_pct.setText(f"{progress_val}%")


# ==============================================================================
# 2. KOMPONEN BARIS STOK MATERIAL (PROGRESS + STATUS BADGE)
# ==============================================================================
class MaterialStockRow(QWidget):
    def __init__(self, mat_data: dict, parent=None):
        super().__init__(parent)
        self.init_row(mat_data)

    def init_row(self, mat: dict):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(10)

        nama = mat.get("nama") or "-"
        satuan = mat.get("satuan") or "kg"
        stok = float(mat.get("stok_saat_ini") or 0.0)
        kapasitas = float(mat.get("kapasitas") or 0.0)
        pct = int(mat.get("persentase", 100))
        status_kat = mat.get("status_kategori", "Aman")

        # 1. Nama Material
        lbl_nama = QLabel(nama)
        lbl_nama.setFixedWidth(85)
        lbl_nama.setStyleSheet("font-size: 12.5px; font-weight: 700; color: #0F172A; background: transparent; border: none;")
        layout.addWidget(lbl_nama)

        # 2. Nilai Stok / Kapasitas Satuan
        stk_str = styles.format_number(stok, 0)
        kap_str = styles.format_number(kapasitas, 0)
        lbl_qty = QLabel(f"{stk_str} / {kap_str} {satuan}")
        lbl_qty.setFixedWidth(135)
        lbl_qty.setStyleSheet("font-size: 12px; font-weight: 500; color: #334155; background: transparent; border: none;")
        layout.addWidget(lbl_qty)

        # 3. Horizontal Progress Bar
        pbar = QProgressBar()
        pbar.setRange(0, 100)
        pbar.setValue(pct)
        pbar.setTextVisible(False)
        pbar.setFixedHeight(9)

        # Warna bar: Merah/Oranye jika Kritis, Hijau jika Aman
        if status_kat == "Kritis":
            if pct <= 75:
                bar_color = "#EF4444" # Red
            else:
                bar_color = "#F97316" # Orange
        else:
            bar_color = "#10B981" # Emerald Green

        pbar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #E2E8F0;
                border-radius: 4.5px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 4.5px;
            }}
        """)
        layout.addWidget(pbar, 1)

        # 4. Persentase Teks
        lbl_pct = QLabel(f"{pct}%")
        lbl_pct.setFixedWidth(40)
        lbl_pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_pct.setStyleSheet("font-size: 11.5px; font-weight: 600; color: #475569; background: transparent; border: none;")
        layout.addWidget(lbl_pct)

        # 5. Badge Status Pill
        lbl_badge = QLabel(status_kat)
        lbl_badge.setAlignment(Qt.AlignCenter)
        lbl_badge.setFixedWidth(64)
        lbl_badge.setFixedHeight(22)
        if status_kat == "Kritis":
            lbl_badge.setStyleSheet("""
                background-color: #FEE2E2;
                color: #DC2626;
                font-size: 11px;
                font-weight: 700;
                border-radius: 11px;
                border: 1px solid #FECACA;
            """)
        else:
            lbl_badge.setStyleSheet("""
                background-color: #D1FAE5;
                color: #059669;
                font-size: 11px;
                font-weight: 700;
                border-radius: 11px;
                border: 1px solid #A7F3D0;
            """)
        layout.addWidget(lbl_badge)


# ==============================================================================
# 3. VIEW UTAMA DASHBOARD OPERASIONAL
# ==============================================================================
class DashboardView(QWidget):
    nav_to_module = Signal(str)

    def __init__(self, user_session: dict = None, parent=None):
        super().__init__(parent)
        self.user_session = user_session or {}
        self.filter_proyek_waktu = "semua"
        self.init_ui()
        self.load_data()

    @property
    def current_user_id(self) -> int:
        uid = self.user_session.get("id")
        return int(uid) if uid else 1

    @property
    def current_user_name(self) -> str:
        return (self.user_session.get("nama_lengkap")
                or self.user_session.get("username")
                or "Administrator")

    def init_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background-color: transparent;")

        container = QWidget()
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setContentsMargins(18, 16, 18, 20)
        self.main_layout.setSpacing(14)

        # ======================================================================
        # 1. ALERT BANNER STOK KRITIS
        # ======================================================================
        self.alert_frame = QFrame()
        self.alert_frame.setObjectName("AlertStockBanner")
        self.alert_frame.setStyleSheet("""
            QFrame#AlertStockBanner {
                background-color: #FEF2F2;
                border: 1.5px solid #FECACA;
                border-radius: 10px;
                padding: 8px 14px;
            }
        """)
        alert_layout = QHBoxLayout(self.alert_frame)
        alert_layout.setContentsMargins(10, 8, 10, 8)
        alert_layout.setSpacing(12)

        # Vector Icon Triangle Warning dalam circle merah
        warn_icon_box = QFrame()
        warn_icon_box.setFixedSize(36, 36)
        warn_icon_box.setStyleSheet("""
            background-color: #FEE2E2;
            border-radius: 18px;
            border: 1px solid #FECACA;
        """)
        w_box_lay = QVBoxLayout(warn_icon_box)
        w_box_lay.setContentsMargins(0, 0, 0, 0)
        w_box_lay.setAlignment(Qt.AlignCenter)
        w_box_lay.addWidget(SvgIconWidget(SVG_WARNING_RED, width=18, height=18))
        alert_layout.addWidget(warn_icon_box)

        # Text Kritis
        alert_text = QVBoxLayout()
        alert_text.setSpacing(2)
        lbl_alert_head = QLabel("Stok material berikut mencapai batas kritis")
        lbl_alert_head.setStyleSheet("color: #991B1B; font-weight: 800; font-size: 13px; background: transparent;")
        self.lbl_alert_items = QLabel("Semen, Pasir, Split 1.2")
        self.lbl_alert_items.setStyleSheet("color: #B91C1C; font-weight: 500; font-size: 12px; background: transparent;")
        alert_text.addWidget(lbl_alert_head)
        alert_text.addWidget(self.lbl_alert_items)
        alert_layout.addLayout(alert_text, 1)

        # Tombol Aksi Kanan: Lihat Detail Stok >
        btn_view_stok = QPushButton("Lihat Detail Stok  >")
        btn_view_stok.setCursor(Qt.PointingHandCursor)
        btn_view_stok.setFixedHeight(34)
        btn_view_stok.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #DC2626;
                border: 1px solid #FECACA;
                border-radius: 6px;
                padding: 4px 14px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #DC2626;
                color: #FFFFFF;
                border-color: #DC2626;
            }
        """)
        btn_view_stok.clicked.connect(lambda: self.nav_to_module.emit("stok"))
        alert_layout.addWidget(btn_view_stok)

        self.main_layout.addWidget(self.alert_frame)

        # ======================================================================
        # 2. 4 KARTU KPI UTAMA (Vector Icons: Cube, Chart, Truck, Users)
        # ======================================================================
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)

        # Card 1: Produksi Hari Ini (Cube Biru)
        self.kpi_today = KPICardWidget(
            svg_xml=SVG_CUBE_BLUE, icon_bg="#EFF6FF",
            title="Produksi Hari Ini", value="0 m³", subtext="Target 10 m³",
            progress_val=0
        )
        kpi_row.addWidget(self.kpi_today)

        # Card 2: Produksi Bulan Ini (Chart Hijau)
        self.kpi_month = KPICardWidget(
            svg_xml=SVG_CHART_GREEN, icon_bg="#ECFDF5",
            title="Produksi Bulan Ini", value="0 m³", subtext="↑ +12%\ndari bulan lalu"
        )
        kpi_row.addWidget(self.kpi_month)

        # Card 3: Pengiriman Hari Ini (Truck Ungu)
        self.kpi_delivery = KPICardWidget(
            svg_xml=SVG_TRUCK_PURPLE, icon_bg="#F5F3FF",
            title="Pengiriman Hari Ini", value="0 truk", subtext="0 selesai   0 dalam proses"
        )
        kpi_row.addWidget(self.kpi_delivery)

        # Card 4: Kendaraan Aktif (Fleet Oranye)
        self.kpi_fleet = KPICardWidget(
            svg_xml=SVG_USERS_ORANGE, icon_bg="#FFF7ED",
            title="Kendaraan Aktif", value="0 unit", subtext="0 perjalanan   0 standby"
        )
        kpi_row.addWidget(self.kpi_fleet)

        self.main_layout.addLayout(kpi_row)

        # ======================================================================
        # 3. ROW TENGAH: STATUS STOK MATERIAL (Kiri) + DISTRIBUSI PROYEK (Kanan)
        # ======================================================================
        mid_row = QHBoxLayout()
        mid_row.setSpacing(14)

        # --- A. Card Kiri: Status Stok Material ---
        card_stok = QFrame()
        card_stok.setObjectName("cardStok")
        card_stok.setStyleSheet(f"""
            QFrame#cardStok {{
                background-color: #FFFFFF;
                border: 1px solid {styles.COLOR_BORDER_LIGHT};
                border-radius: 12px;
            }}
        """)
        stok_layout = QVBoxLayout(card_stok)
        stok_layout.setContentsMargins(16, 14, 16, 14)
        stok_layout.setSpacing(10)

        # Header Stok dengan Vector Icon Box
        stok_head = QHBoxLayout()
        stok_head.setSpacing(8)
        stok_head.addWidget(SvgIconWidget(SVG_BOX_NAVY, width=17, height=17))
        lbl_stok_title = QLabel("Status Stok Material")
        lbl_stok_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #0F172A; background: transparent; border: none;")
        stok_head.addWidget(lbl_stok_title)
        stok_head.addStretch()

        btn_all_stok = QPushButton("Lihat Semua")
        btn_all_stok.setCursor(Qt.PointingHandCursor)
        btn_all_stok.setStyleSheet("""
            QPushButton {
                color: #2563EB;
                font-size: 12px;
                font-weight: 700;
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                color: #1D4ED8;
                text-decoration: underline;
            }
        """)
        btn_all_stok.clicked.connect(lambda: self.nav_to_module.emit("stok"))
        stok_head.addWidget(btn_all_stok)
        stok_layout.addLayout(stok_head)

        # Container List Baris Material
        self.stok_rows_container = QVBoxLayout()
        self.stok_rows_container.setSpacing(8)
        stok_layout.addLayout(self.stok_rows_container)
        stok_layout.addStretch()

        mid_row.addWidget(card_stok, 52) # 52% width

        # --- B. Card Kanan: Distribusi Volume Beton per Proyek ---
        card_proyek = QFrame()
        card_proyek.setObjectName("cardProyek")
        card_proyek.setStyleSheet(f"""
            QFrame#cardProyek {{
                background-color: #FFFFFF;
                border: 1px solid {styles.COLOR_BORDER_LIGHT};
                border-radius: 12px;
            }}
        """)
        proyek_layout = QVBoxLayout(card_proyek)
        proyek_layout.setContentsMargins(16, 14, 16, 14)
        proyek_layout.setSpacing(10)

        # Header Proyek + Dropdown Filter
        proyek_head = QHBoxLayout()
        proyek_head.setSpacing(8)
        proyek_head.addWidget(SvgIconWidget(SVG_CHART_NAVY, width=17, height=17))
        lbl_proyek_title = QLabel("Distribusi Volume Beton per Proyek")
        lbl_proyek_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #0F172A; background: transparent; border: none;")
        proyek_head.addWidget(lbl_proyek_title)
        proyek_head.addStretch()

        self.cb_filter_proyek = QComboBox()
        self.cb_filter_proyek.setView(QListView())
        self.cb_filter_proyek.addItem("Semua", "semua")
        self.cb_filter_proyek.addItem("Hari Ini", "hari_ini")
        self.cb_filter_proyek.addItem("Bulan Ini", "bulan_ini")
        self.cb_filter_proyek.setStyleSheet("""
            QComboBox {
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 3px 24px 3px 10px;
                font-size: 12px;
                font-weight: 600;
                color: #334155;
                background-color: #FFFFFF;
                min-width: 75px;
            }
            QComboBox:hover {
                border-color: #2563EB;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: none;
            }
        """)
        self.cb_filter_proyek.currentIndexChanged.connect(self.on_filter_proyek_changed)
        proyek_head.addWidget(self.cb_filter_proyek)
        proyek_layout.addLayout(proyek_head)

        # Split Body Proyek: Kiri (Bars) + Kanan (Summary Box Total Volume)
        proyek_body = QHBoxLayout()
        proyek_body.setSpacing(16)

        self.proyek_bars_layout = QVBoxLayout()
        self.proyek_bars_layout.setSpacing(8)
        proyek_body.addLayout(self.proyek_bars_layout, 1)

        # Summary Box Kanan
        self.summary_box = QFrame()
        self.summary_box.setObjectName("summaryBox")
        self.summary_box.setFixedSize(130, 130)
        self.summary_box.setStyleSheet("""
            QFrame#summaryBox {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
        s_lay = QVBoxLayout(self.summary_box)
        s_lay.setContentsMargins(10, 12, 10, 12)
        s_lay.setSpacing(2)
        s_lay.setAlignment(Qt.AlignCenter)

        s_box_ico_container = QVBoxLayout()
        s_box_ico_container.setAlignment(Qt.AlignCenter)
        s_box_ico_container.addWidget(SvgIconWidget(SVG_BOX_NAVY, width=28, height=28))
        s_lay.addLayout(s_box_ico_container)

        lbl_s_lbl = QLabel("Total Volume")
        lbl_s_lbl.setAlignment(Qt.AlignCenter)
        lbl_s_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B; background: transparent; border: none; margin-top: 4px;")
        s_lay.addWidget(lbl_s_lbl)

        self.lbl_s_vol = QLabel("0 m³")
        self.lbl_s_vol.setAlignment(Qt.AlignCenter)
        self.lbl_s_vol.setStyleSheet("font-size: 20px; font-weight: 900; color: #0F172A; background: transparent; border: none;")
        s_lay.addWidget(self.lbl_s_vol)

        self.lbl_s_proyek = QLabel("dari 0 proyek")
        self.lbl_s_proyek.setAlignment(Qt.AlignCenter)
        self.lbl_s_proyek.setStyleSheet("font-size: 10.5px; font-weight: 500; color: #64748B; background: transparent; border: none;")
        s_lay.addWidget(self.lbl_s_proyek)

        proyek_body.addWidget(self.summary_box, 0, Qt.AlignTop)
        proyek_layout.addLayout(proyek_body)
        proyek_layout.addStretch()

        mid_row.addWidget(card_proyek, 48) # 48% width

        self.main_layout.addLayout(mid_row)

        # ======================================================================
        # 4. BOTTOM SECTION: PENGIRIMAN TERBARU (TABEL MODERN DENGAN VECTOR ICON)
        # ======================================================================
        card_recent = QFrame()
        card_recent.setObjectName("cardRecent")
        card_recent.setStyleSheet(f"""
            QFrame#cardRecent {{
                background-color: #FFFFFF;
                border: 1px solid {styles.COLOR_BORDER_LIGHT};
                border-radius: 12px;
            }}
        """)
        recent_layout = QVBoxLayout(card_recent)
        recent_layout.setContentsMargins(16, 14, 16, 16)
        recent_layout.setSpacing(12)

        # Header Pengiriman Terbaru
        rec_head = QHBoxLayout()
        rec_head.setSpacing(8)
        rec_head.addWidget(SvgIconWidget(SVG_TRUCK_NAVY, width=18, height=18))
        lbl_rec_title = QLabel("Pengiriman Terbaru")
        lbl_rec_title.setStyleSheet("font-size: 14.5px; font-weight: 800; color: #0F172A; background: transparent; border: none;")
        rec_head.addWidget(lbl_rec_title)
        rec_head.addStretch()

        btn_all_rec = QPushButton("Lihat Semua Pengiriman  ➔")
        btn_all_rec.setCursor(Qt.PointingHandCursor)
        btn_all_rec.setStyleSheet("""
            QPushButton {
                color: #2563EB;
                font-size: 12px;
                font-weight: 700;
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                color: #1D4ED8;
                text-decoration: underline;
            }
        """)
        btn_all_rec.clicked.connect(lambda: self.nav_to_module.emit("produksi"))
        rec_head.addWidget(btn_all_rec)
        recent_layout.addLayout(rec_head)

        # Tabel Pengiriman Terbaru Sesuai Mockup
        self.table_recent = ModernTableWidget([
            "No", "Waktu", "No Surat Jalan", "Proyek", "Mutu", 
            "Volume", "Tujuan / Lokasi", "Driver", "No Plat", "Status"
        ])
        self.table_recent.setMinimumHeight(240)

        # Setting lebar kolom
        self.table_recent.setColumnWidth(0, 38)   # No
        self.table_recent.setColumnWidth(1, 125)  # Waktu
        self.table_recent.setColumnWidth(2, 135)  # No Surat Jalan
        self.table_recent.setColumnWidth(3, 160)  # Proyek
        self.table_recent.setColumnWidth(4, 70)   # Mutu
        self.table_recent.setColumnWidth(5, 75)   # Volume
        self.table_recent.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch) # Tujuan / Lokasi
        self.table_recent.setColumnWidth(7, 120)  # Driver
        self.table_recent.setColumnWidth(8, 100)  # No Plat
        self.table_recent.setColumnWidth(9, 115)  # Status

        recent_layout.addWidget(self.table_recent)
        self.main_layout.addWidget(card_recent)

        scroll.setWidget(container)

        outer_lay = QVBoxLayout(self)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.addWidget(scroll)

    def on_filter_proyek_changed(self):
        self.filter_proyek_waktu = self.cb_filter_proyek.currentData() or "semua"
        self.update_proyek_distribution()

    def update_proyek_distribution(self):
        # Bersihkan container lama
        while self.proyek_bars_layout.count():
            item = self.proyek_bars_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        res = database.get_proyek_volume_distribution(self.filter_proyek_waktu)
        items = res.get("items", [])
        tot_vol = res.get("total_vol", 0.0)
        p_count = res.get("proyek_count", 0)

        self.lbl_s_vol.setText(f"{styles.format_number(tot_vol, 0)} m³")
        self.lbl_s_proyek.setText(f"dari {p_count} proyek")

        if not items:
            lbl_empty = QLabel("Belum ada data pengiriman beton pada periode ini.")
            lbl_empty.setStyleSheet("color: #64748B; font-style: italic; font-size: 12px; padding: 10px 0; background: transparent; border: none;")
            self.proyek_bars_layout.addWidget(lbl_empty)
            self.proyek_bars_layout.addStretch()
            return

        max_v = max((p["total_vol"] for p in items), default=1.0)
        if max_v <= 0: max_v = 1.0

        for p in items:
            row_w = QWidget()
            row_w.setFixedHeight(32)
            row_lay = QHBoxLayout(row_w)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(12)

            # Nama Proyek (Rapi, rata kanan menghadap bar, clean font)
            lbl_p_name = QLabel(p["nama"])
            lbl_p_name.setFixedWidth(145)
            lbl_p_name.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl_p_name.setStyleSheet("font-size: 12px; font-weight: 600; color: #1E293B; background: transparent; border: none;")
            lbl_p_name.setToolTip(p["nama"])
            row_lay.addWidget(lbl_p_name)

            # Bar Horizontal Biru
            vol_val = float(p["total_vol"] or 0)
            pct = int(round((vol_val / max_v) * 100))
            pbar = QProgressBar()
            pbar.setRange(0, 100)
            pbar.setValue(pct)
            pbar.setTextVisible(False)
            pbar.setFixedHeight(18)
            pbar.setStyleSheet("""
                QProgressBar {
                    background-color: #EFF6FF;
                    border-radius: 5px;
                    border: none;
                }
                QProgressBar::chunk {
                    background-color: #3B82F6;
                    border-radius: 5px;
                }
            """)
            row_lay.addWidget(pbar, 1)

            # Nilai Volume m³
            lbl_v_text = QLabel(f"{styles.format_number(vol_val, 0)} m³")
            lbl_v_text.setFixedWidth(50)
            lbl_v_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            lbl_v_text.setStyleSheet("font-size: 12px; font-weight: 700; color: #0F172A; background: transparent; border: none;")
            row_lay.addWidget(lbl_v_text)

            self.proyek_bars_layout.addWidget(row_w)

        self.proyek_bars_layout.addStretch()

    def load_data(self):
        """Memuat seluruh data dashboard terbaru secara terintegrasi"""
        data = database.get_dashboard_data(user_id=self.current_user_id)

        # 1. Update 4 Kartu KPI
        vol_today = data.get("vol_today", 0.0)
        target_today = data.get("target_today", 10.0)
        target_pct = data.get("target_pct", 0)
        self.kpi_today.update_data(
            value=f"{styles.format_number(vol_today, 0)} m³",
            subtext=f"Target {styles.format_number(target_today, 0)} m³",
            progress_val=target_pct
        )

        vol_month = data.get("vol_month", 0.0)
        growth_pct = data.get("vol_growth_pct", 0.0)
        growth_sign = "↑ +" if growth_pct >= 0 else "↓ "
        self.kpi_month.update_data(
            value=f"{styles.format_number(vol_month, 0)} m³",
            subtext=f"{growth_sign}{growth_pct:.0f}%\ndari bulan lalu"
        )

        count_ships = data.get("count_ships_today", 0)
        ships_selesai = data.get("ships_selesai", 0)
        ships_proses = data.get("ships_proses", 0)
        self.kpi_delivery.update_data(
            value=f"{count_ships} truk",
            subtext=f"{ships_selesai} selesai    {ships_proses} dalam proses"
        )

        kend_aktif = data.get("kend_aktif", 0)
        kend_perjalanan = data.get("kend_perjalanan", 0)
        kend_standby = data.get("kend_standby", 0)
        self.kpi_fleet.update_data(
            value=f"{kend_aktif} unit",
            subtext=f"{kend_perjalanan} perjalanan    {kend_standby} standby"
        )

        # 2. Update Alert Banner Stok Kritis
        critical = data.get("critical_materials", [])
        if critical:
            items_str = ", ".join([f"{m['nama']} ({styles.format_number(m['stok_saat_ini'], 0)} {m['satuan']})" for m in critical[:4]])
            self.lbl_alert_items.setText(items_str)
            self.alert_frame.setVisible(True)
        else:
            self.alert_frame.setVisible(False)

        # 3. Update List Baris Stok Material
        while self.stok_rows_container.count():
            item = self.stok_rows_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        mats = data.get("stok_materials", [])
        if not mats:
            lbl_empty_mat = QLabel("Belum ada data stok material yang terdaftar.")
            lbl_empty_mat.setStyleSheet("color: #64748B; font-style: italic; padding: 10px 0;")
            self.stok_rows_container.addWidget(lbl_empty_mat)
        else:
            for m in mats:
                row_widget = MaterialStockRow(m)
                self.stok_rows_container.addWidget(row_widget)

        # 4. Update Distribusi Proyek
        self.update_proyek_distribution()

        # 5. Update Tabel Pengiriman Terbaru
        recent = data.get("recent_shipments", [])
        self.table_recent.setRowCount(len(recent))
        for r_idx, r in enumerate(recent):
            # No
            it_no = QTableWidgetItem(str(r_idx + 1))
            it_no.setTextAlignment(Qt.AlignCenter)
            self.table_recent.setItem(r_idx, 0, it_no)

            # Waktu
            it_waktu = QTableWidgetItem(str(r.get("waktu_str") or r.get("tanggal") or "-"))
            it_waktu.setTextAlignment(Qt.AlignCenter)
            self.table_recent.setItem(r_idx, 1, it_waktu)

            # No Surat Jalan
            it_sj = QTableWidgetItem(str(r.get("no_surat_jalan") or "-"))
            it_sj.setForeground(QColor("#1E293B"))
            self.table_recent.setItem(r_idx, 2, it_sj)

            # Proyek
            self.table_recent.setItem(r_idx, 3, QTableWidgetItem(str(r.get("proyek_nama") or "-")))

            # Mutu
            it_mutu = QTableWidgetItem(str(r.get("mutu_kode") or "-"))
            it_mutu.setTextAlignment(Qt.AlignCenter)
            self.table_recent.setItem(r_idx, 4, it_mutu)

            # Volume
            vol_val = float(r.get("volume_m3") or 0)
            it_vol = QTableWidgetItem(f"{styles.format_number(vol_val, 0)} m³")
            it_vol.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_recent.setItem(r_idx, 5, it_vol)

            # Tujuan / Lokasi
            self.table_recent.setItem(r_idx, 6, QTableWidgetItem(str(r.get("tujuan_pengiriman") or "-")))

            # Driver
            drv = str(r.get("driver") or "-").upper()
            self.table_recent.setItem(r_idx, 7, QTableWidgetItem(drv))

            # No Plat
            it_plat = QTableWidgetItem(str(r.get("no_plat_truk") or "-"))
            it_plat.setTextAlignment(Qt.AlignCenter)
            self.table_recent.setItem(r_idx, 8, it_plat)

            # Status Badge Widget
            status_str = r.get("status_kirim", "Selesai")
            status_container = QWidget()
            status_lay = QHBoxLayout(status_container)
            status_lay.setContentsMargins(0, 0, 0, 0)
            status_lay.setAlignment(Qt.AlignCenter)

            lbl_st = QLabel(f"✓ {status_str}" if status_str == "Selesai" else f"• {status_str}")
            lbl_st.setAlignment(Qt.AlignCenter)
            lbl_st.setFixedSize(98, 24)
            if status_str == "Selesai":
                lbl_st.setStyleSheet("""
                    background-color: #ECFDF5;
                    color: #059669;
                    font-size: 11px;
                    font-weight: 700;
                    border-radius: 12px;
                    border: 1px solid #A7F3D0;
                """)
            else:
                lbl_st.setStyleSheet("""
                    background-color: #EFF6FF;
                    color: #2563EB;
                    font-size: 11px;
                    font-weight: 700;
                    border-radius: 12px;
                    border: 1px solid #BFDBFE;
                """)
            status_lay.addWidget(lbl_st)
            self.table_recent.setCellWidget(r_idx, 9, status_container)

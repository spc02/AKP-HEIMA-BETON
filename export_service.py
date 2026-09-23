"""
Export Service untuk AKP Beton Desktop Application
Menyediakan export laporan ke format Excel (.xlsx) menggunakan openpyxl
dan PDF (.pdf) siap cetak menggunakan reportlab untuk Operasional & 4 Pilar Keuangan.
Termasuk cetak Surat Jalan (Tiket Cor) PDF siap cetak per transaksi pengiriman.
"""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# OpenPyXL Imports
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

# ReportLab Imports
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, Image as RLImage, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm

import database

def get_company_header_info() -> Dict[str, str]:
    get_settings_fn = getattr(database, "get_settings", lambda: {})
    settings = get_settings_fn()
    return {
        "nama": settings.get("nama_perusahaan", "AKP CONTRUCTION BUILDING"),
        "alamat": settings.get("alamat_perusahaan", "Jl. Raya Batching Plant & Construction, Jawa Tengah"),
        "telepon": settings.get("telepon_perusahaan", "0812-3456-7890"),
        "pj": settings.get("pj_lapangan", "Penanggung Jawab Operasional")
    }

def fmt_tgl(tgl_str: Any, fmt: str = "%d/%m/%Y") -> str:
    """Konversi string tanggal dari format database (YYYY-MM-DD) ke format tampilan (DD/MM/YYYY).
    Mengembalikan string kosong jika nilai None/-/kosong."""
    if not tgl_str or str(tgl_str).strip() in ("-", "None", ""):
        return "-"
    s = str(tgl_str).strip()[:10]  # ambil hanya bagian YYYY-MM-DD
    try:
        return datetime.strptime(s, "%Y-%m-%d").strftime(fmt)
    except ValueError:
        return s  # kembalikan apa adanya jika sudah dalam format lain

def fmt_periode(start_date: Optional[str], end_date: Optional[str]) -> str:
    """Buat string periode laporan dengan tanggal yang sudah diformat DD/MM/YYYY."""
    if start_date and end_date:
        return f"Periode: {fmt_tgl(start_date)} s/d {fmt_tgl(end_date)}"
    elif start_date:
        return f"Mulai Tanggal: {fmt_tgl(start_date)}"
    return "Semua Periode"



# ==========================================
# EXCEL EXPORT ENGINE (OPENPYXL)
# ==========================================

def style_excel_header(ws, row_idx: int, num_cols: int, title: str, subtitle: str = ""):
    """Menambahkan Kop Judul Laporan Excel dengan styling formal"""
    company = get_company_header_info()
    
    # Baris 1: Nama Perusahaan
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
    cell1 = ws.cell(row=1, column=1, value=company["nama"].upper())
    cell1.font = Font(name="Calibri", size=15, bold=True, color="1E3A8A")
    cell1.alignment = Alignment(horizontal="center", vertical="center")
    
    # Baris 2: Alamat & Kontak
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=num_cols)
    cell2 = ws.cell(row=2, column=1, value=f"{company['alamat']} | Telp: {company['telepon']}")
    cell2.font = Font(name="Calibri", size=10, italic=True, color="64748B")
    cell2.alignment = Alignment(horizontal="center", vertical="center")
    
    # Baris 3: Judul Laporan
    ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=num_cols)
    cell3 = ws.cell(row=4, column=1, value=title.upper())
    cell3.font = Font(name="Calibri", size=13, bold=True, color="0F172A")
    cell3.alignment = Alignment(horizontal="center", vertical="center")
    
    if subtitle:
        ws.merge_cells(start_row=5, start_column=1, end_row=5, end_column=num_cols)
        cell4 = ws.cell(row=5, column=1, value=subtitle)
        cell4.font = Font(name="Calibri", size=10, color="334155")
        cell4.alignment = Alignment(horizontal="center", vertical="center")

def autofit_columns(ws, max_col_width: int = 50):
    """Menyesuaikan lebar kolom Excel secara otomatis berdasarkan isi sel"""
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row <= 5:
                continue
            val_str = str(cell.value or "")
            max_len = max(max_len, len(val_str))
        ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), max_col_width)

def get_standard_borders():
    header_fill = PatternFill(start_color="FFDBEAFE", end_color="FFDBEAFE", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FF0F172A")
    border_header = Border(
        left=Side(style='thin', color='FF94A3B8'),
        right=Side(style='thin', color='FF94A3B8'),
        top=Side(style='medium', color='FF1E3A8A'),
        bottom=Side(style='medium', color='FF1E3A8A')
    )
    border_thin = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )
    return header_fill, header_font, border_header, border_thin

def export_pengiriman_excel(filepath: str, start_date: Optional[str] = None, end_date: Optional[str] = None, proyek_id: Optional[int] = None):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rekap Pengiriman"
    
    data = database.get_riwayat_pengiriman(start_date=start_date, end_date=end_date, proyek_id=proyek_id)
    
    periode_str = fmt_periode(start_date, end_date)
        
    headers = [
        "No", "Tanggal", "No Surat Jalan", "Mutu Beton", "Volume (m3)", "Proyek", "Tujuan / Lokasi", 
        "HPP / m3 (Rp)", "Total HPP (Rp)", "Harga Jual / m3 (Rp)", "Total Pendapatan (Rp)", "Laba Kotor (Rp)", 
        "Semen Terpakai (kg)", "No Plat", "Driver", "Catatan"
    ]
    style_excel_header(ws, 1, len(headers), "Laporan Rekapitulasi Pengiriman Beton & POS Dispatch", periode_str)
    
    header_fill, header_font, border_header, border_thin = get_standard_borders()
    
    start_row = 7
    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=start_row, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border_header
    
    current_row = start_row + 1
    total_vol = 0.0
    total_hpp = 0.0
    total_rev = 0.0
    total_laba = 0.0
    total_semen = 0.0
    
    for idx, row in enumerate(data, start=1):
        vol = float(row.get("volume_m3") or 0)
        hpp_m3 = float(row.get("hpp_per_m3") or 0)
        t_hpp = float(row.get("total_hpp") or 0)
        h_jual = float(row.get("harga_jual_per_m3") or 0)
        t_pend = float(row.get("total_pendapatan") or 0)
        laba = float(row.get("margin_laba_rp") or 0)
        smn = float(row.get("semen_terpakai") or 0)

        total_vol += vol
        total_hpp += t_hpp
        total_rev += t_pend
        total_laba += laba
        total_semen += smn
        
        vals = [
            idx, fmt_tgl(row.get("tanggal")), row.get("no_surat_jalan"), row.get("mutu_kode"),
            vol, row.get("proyek_nama"), row.get("tujuan_pengiriman") or "-",
            hpp_m3, t_hpp, h_jual, t_pend, laba,
            smn, row.get("no_plat_truk") or "-", row.get("driver") or "-", row.get("catatan") or "-"
        ]
        
        for col_idx, val in enumerate(vals, start=1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.border = border_thin
            if col_idx in (1, 2, 4, 14, 15):
                cell.alignment = Alignment(horizontal="center", vertical="top")
            elif col_idx in (5, 8, 9, 10, 11, 12, 13):
                cell.alignment = Alignment(horizontal="right", vertical="top")
                cell.number_format = "#,##0.00" if col_idx == 5 else "#,##0"
            elif col_idx in (7, 16):  # Tujuan & Catatan — wrap text
                cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            else:
                cell.alignment = Alignment(horizontal="left", vertical="top")
        current_row += 1
        
    # Total Row
    ws.cell(row=current_row, column=1, value="TOTAL")
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=4)
    total_lbl = ws.cell(row=current_row, column=1)
    total_lbl.font = Font(name="Calibri", bold=True, color="FF0F172A")
    total_lbl.alignment = Alignment(horizontal="center")
    
    ws.cell(row=current_row, column=5, value=total_vol).number_format = "#,##0.00"
    ws.cell(row=current_row, column=9, value=total_hpp).number_format = "#,##0"
    ws.cell(row=current_row, column=11, value=total_rev).number_format = "#,##0"
    ws.cell(row=current_row, column=12, value=total_laba).number_format = "#,##0"
    ws.cell(row=current_row, column=13, value=total_semen).number_format = "#,##0"
    
    for c in range(1, len(headers)+1):
        cell = ws.cell(row=current_row, column=c)
        cell.border = border_thin
        cell.font = Font(name="Calibri", bold=True, color="FF0F172A")
        cell.fill = PatternFill(start_color="FFF1F5F9", end_color="FFF1F5F9", fill_type="solid")
        
    autofit_columns(ws)
    wb.save(filepath)
    return True

def export_stok_excel(filepath: str):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rekap Stok Material"
    
    data = database.get_rekap_kartu_stok()
    headers = [
        "No", "Kode Material", "Nama Material", "Satuan", "Harga Beli Terbaru (Rp)", 
        "Total Masuk", "Total Terpakai Cor", "Sisa Stok Saat Ini", "Nilai Aset Stok (Rp)", "Stok Minimum", "Status"
    ]
    style_excel_header(ws, 1, len(headers), "Laporan Rekapitulasi Stok Material & Valuasi Aset", f"Per Tanggal: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    header_fill, header_font, border_header, border_thin = get_standard_borders()
    
    start_row = 7
    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=start_row, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border_header
        
    current_row = start_row + 1
    total_aset = 0.0
    for idx, row in enumerate(data, start=1):
        stok = float(row.get("stok_saat_ini") or 0)
        min_stok = float(row.get("stok_minimum") or 0)
        hrg_beli = float(row.get("harga_beli_terbaru") or 0)
        nilai_aset = float(row.get("nilai_aset_stok") or 0)
        total_aset += nilai_aset
        status_str = "KRITIS / MINUS" if stok <= min_stok else "AMAN"
        
        vals = [
            idx, row.get("kode"), row.get("nama"), row.get("satuan"), hrg_beli,
            row.get("total_masuk"), row.get("total_terpakai"), stok, nilai_aset, min_stok, status_str
        ]
        
        for col_idx, val in enumerate(vals, start=1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.border = border_thin
            if col_idx in (1, 2, 4, 11):
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if col_idx == 11:
                    cell.font = Font(name="Calibri", bold=True, color="DC2626" if status_str != "AMAN" else "059669")
            elif col_idx in (5, 6, 7, 8, 9, 10):
                cell.alignment = Alignment(horizontal="right", vertical="center")
                cell.number_format = "#,##0.00" if col_idx in (6, 7, 8, 10) else "#,##0"
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
        current_row += 1

    # Total Row Valuasi Aset
    ws.cell(row=current_row, column=1, value="TOTAL NILAI ASET STOK")
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=8)
    ws.cell(row=current_row, column=1).alignment = Alignment(horizontal="center")
    ws.cell(row=current_row, column=9, value=total_aset).number_format = "#,##0"
    for c in range(1, len(headers)+1):
        cell = ws.cell(row=current_row, column=c)
        cell.border = border_thin
        cell.font = Font(name="Calibri", bold=True, color="FF0F172A")
        cell.fill = PatternFill(start_color="FFF1F5F9", end_color="FFF1F5F9", fill_type="solid")
        
    autofit_columns(ws)
    wb.save(filepath)
    return True

def export_keuangan_excel(filepath: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Ekspor komprehensif 5 Sheet Excel untuk Modul Keuangan Plant"""
    wb = openpyxl.Workbook()
    header_fill, header_font, border_header, border_thin = get_standard_borders()
    start_row = 7

    periode_str = fmt_periode(start_date, end_date)

    # -------------------------------------------------------------
    # Sheet 1: Buku Kas Umum (Ledger Saldo Kas)
    # -------------------------------------------------------------
    ws_kas = wb.active
    ws_kas.title = "Buku Kas Umum"
    kas_data = database.get_saldo_kas(start_date=start_date, end_date=end_date)
    headers_kas = ["No", "Tanggal", "Kategori", "Keterangan", "Kas Masuk (Rp)", "Kas Keluar (Rp)", "Saldo Berjalan (Rp)"]
    style_excel_header(ws_kas, 1, len(headers_kas), "Laporan Buku Kas Umum Batching Plant", periode_str)
    
    for col_idx, h in enumerate(headers_kas, start=1):
        c = ws_kas.cell(row=start_row, column=col_idx, value=h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = border_header
        
    r_idx = start_row + 1
    t_in, t_out = 0.0, 0.0
    for idx, row in enumerate(kas_data, start=1):
        m = float(row.get("saldo_masuk") or 0)
        k = float(row.get("saldo_keluar") or 0)
        t_in += m
        t_out += k
        vals = [idx, fmt_tgl(row.get("tanggal")), row.get("kategori"), row.get("keterangan"), m, k, row.get("total_saldo")]
        for c_idx, v in enumerate(vals, start=1):
            cell = ws_kas.cell(row=r_idx, column=c_idx, value=v)
            cell.border = border_thin
            if c_idx in (1, 2, 3):
                cell.alignment = Alignment(horizontal="center", vertical="top")
            elif c_idx in (5, 6, 7):
                cell.alignment = Alignment(horizontal="right", vertical="top")
                cell.number_format = "#,##0"
            elif c_idx == 4:  # Keterangan — wrap text
                cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            else:
                cell.alignment = Alignment(horizontal="left", vertical="top")
        ws_kas.row_dimensions[r_idx].height = None  # auto-height
        r_idx += 1
        
    ws_kas.cell(row=r_idx, column=1, value="TOTAL")
    ws_kas.merge_cells(start_row=r_idx, start_column=1, end_row=r_idx, end_column=4)
    ws_kas.cell(row=r_idx, column=5, value=t_in).number_format = "#,##0"
    ws_kas.cell(row=r_idx, column=6, value=t_out).number_format = "#,##0"
    ws_kas.cell(row=r_idx, column=7, value=t_in - t_out).number_format = "#,##0"
    for c in range(1, len(headers_kas)+1):
        ws_kas.cell(row=r_idx, column=c).border = border_thin
        ws_kas.cell(row=r_idx, column=c).font = Font(name="Calibri", bold=True, color="FF0F172A")
        ws_kas.cell(row=r_idx, column=c).fill = PatternFill(start_color="FFF1F5F9", end_color="FFF1F5F9", fill_type="solid")
    autofit_columns(ws_kas)
    
    # Helper untuk mengisi sheet Piutang Material Supplier (Kantor / Perusahaan)
    def render_piutang_semen_sheet(ws, title_text: str, kat_piutang: str):
        data = database.get_pembayaran_semen_list(kategori_piutang=kat_piutang)
        headers = ["No", "No DO / Order", "Supplier", "Tgl Order", "Tgl Datang", "Jumlah (Ton)", "Harga/Ton (Rp)", "Total Tagihan (Rp)", "Terbayar (Rp)", "Sisa Hutang (Rp)", "Status"]
        style_excel_header(ws, 1, len(headers), title_text, "")
        for col_idx, h in enumerate(headers, start=1):
            c = ws.cell(row=start_row, column=col_idx, value=h)
            c.fill = header_fill
            c.font = header_font
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = border_header
        r_idx = start_row + 1
        tot_tag, tot_byr, tot_sisa = 0.0, 0.0, 0.0
        for idx, row in enumerate(data, start=1):
            t_hrg = float(row.get("total_harga") or 0)
            t_byr = float(row.get("total_dibayar") or 0)
            t_sisa = float(row.get("sisa_hutang") or 0)
            tot_tag += t_hrg
            tot_byr += t_byr
            tot_sisa += t_sisa
            stat_str = "LUNAS" if t_sisa <= 0 else ("CICILAN" if t_byr > 0 else "BELUM BAYAR")

            vals = [
                idx, row.get("no_order") or "-", row.get("supplier") or "-", fmt_tgl(row.get("tanggal_order")), fmt_tgl(row.get("tanggal_datang")),
                row.get("jumlah_ton"), row.get("harga_per_ton"), t_hrg, t_byr, t_sisa, stat_str
            ]
            for c_idx, v in enumerate(vals, start=1):
                cell = ws.cell(row=r_idx, column=c_idx, value=v)
                cell.border = border_thin
                if c_idx in (1, 2, 4, 5, 11):
                    cell.alignment = Alignment(horizontal="center")
                elif c_idx in (6, 7, 8, 9, 10):
                    cell.alignment = Alignment(horizontal="right")
                    cell.number_format = "#,##0.00" if c_idx == 6 else "#,##0"
                else:
                    cell.alignment = Alignment(horizontal="left")
            r_idx += 1
        
        ws.cell(row=r_idx, column=1, value="TOTAL")
        ws.merge_cells(start_row=r_idx, start_column=1, end_row=r_idx, end_column=7)
        ws.cell(row=r_idx, column=8, value=tot_tag).number_format = "#,##0"
        ws.cell(row=r_idx, column=9, value=tot_byr).number_format = "#,##0"
        ws.cell(row=r_idx, column=10, value=tot_sisa).number_format = "#,##0"
        for c in range(1, len(headers)+1):
            ws.cell(row=r_idx, column=c).border = border_thin
            ws.cell(row=r_idx, column=c).font = Font(name="Calibri", bold=True, color="FF0F172A")
            ws.cell(row=r_idx, column=c).fill = PatternFill(start_color="FFF1F5F9", end_color="FFF1F5F9", fill_type="solid")
        autofit_columns(ws)

    # -------------------------------------------------------------
    # Sheet 2: Tagihan & Piutang Kantor (Material Supplier)
    # -------------------------------------------------------------
    ws_kantor_piu = wb.create_sheet(title="Piutang Kantor")
    render_piutang_semen_sheet(ws_kantor_piu, "Rekapitulasi Tagihan & Hutang Supplier (Piutang Kantor)", "kantor")

    # -------------------------------------------------------------
    # Sheet 3: Tagihan & Piutang Perusahaan (Material Supplier)
    # -------------------------------------------------------------
    ws_perush_piu = wb.create_sheet(title="Piutang Perusahaan")
    render_piutang_semen_sheet(ws_perush_piu, "Rekapitulasi Tagihan & Hutang Supplier (Piutang Perusahaan)", "perusahaan")

    # -------------------------------------------------------------
    # Sheet 3: Piutang Tiap Proyek
    # -------------------------------------------------------------
    ws_proyek = wb.create_sheet(title="Piutang Proyek")
    proyek_rekap = database.get_rekap_saldo_per_proyek()
    headers_pr = ["No", "Nama Proyek", "Lokasi", "Status", "Total Volume Cor (m3)", "Total Tagihan (Rp)", "Pembayaran Diterima (Rp)", "Sisa Piutang (Rp)"]
    style_excel_header(ws_proyek, 1, len(headers_pr), "Rekapitulasi Tagihan & Piutang Per Proyek", "")
    for col_idx, h in enumerate(headers_pr, start=1):
        c = ws_proyek.cell(row=start_row, column=col_idx, value=h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = border_header
    r_idx = start_row + 1
    tot_vol_pr, tot_tag_pr, tot_byr_pr, tot_piu_pr = 0.0, 0.0, 0.0, 0.0
    for idx, row in enumerate(proyek_rekap, start=1):
        vol_p = float(row.get("total_volume_m3") or 0)
        tag_p = float(row.get("total_tagihan") or 0)
        byr_p = float(row.get("total_bayar") or 0)
        piu_p = float(row.get("sisa_saldo_piutang") or 0)

        tot_vol_pr += vol_p
        tot_tag_pr += tag_p
        tot_byr_pr += byr_p
        tot_piu_pr += piu_p

        vals = [
            idx, row.get("nama"), row.get("lokasi"), row.get("status").upper(),
            vol_p, tag_p, byr_p, piu_p
        ]
        for c_idx, v in enumerate(vals, start=1):
            cell = ws_proyek.cell(row=r_idx, column=c_idx, value=v)
            cell.border = border_thin
            if c_idx in (1, 3, 4):
                cell.alignment = Alignment(horizontal="center")
            elif c_idx in (5, 6, 7, 8):
                cell.alignment = Alignment(horizontal="right")
                cell.number_format = "#,##0.00" if c_idx == 5 else "#,##0"
            else:
                cell.alignment = Alignment(horizontal="left")
        r_idx += 1
    
    ws_proyek.cell(row=r_idx, column=1, value="TOTAL")
    ws_proyek.merge_cells(start_row=r_idx, start_column=1, end_row=r_idx, end_column=4)
    ws_proyek.cell(row=r_idx, column=5, value=tot_vol_pr).number_format = "#,##0.00"
    ws_proyek.cell(row=r_idx, column=6, value=tot_tag_pr).number_format = "#,##0"
    ws_proyek.cell(row=r_idx, column=7, value=tot_byr_pr).number_format = "#,##0"
    ws_proyek.cell(row=r_idx, column=8, value=tot_piu_pr).number_format = "#,##0"
    for c in range(1, len(headers_pr)+1):
        ws_proyek.cell(row=r_idx, column=c).border = border_thin
        ws_proyek.cell(row=r_idx, column=c).font = Font(name="Calibri", bold=True, color="FF0F172A")
        ws_proyek.cell(row=r_idx, column=c).fill = PatternFill(start_color="FFF1F5F9", end_color="FFF1F5F9", fill_type="solid")
    autofit_columns(ws_proyek)

    # -------------------------------------------------------------
    # Sheet 4: Pengeluaran Kas Kantor (Non-Semen)
    # -------------------------------------------------------------
    ws_kantor = wb.create_sheet(title="Kas Kantor Non-Semen")
    kantor_data = database.get_kas_kantor_list()
    headers_ktr = ["No", "Tanggal", "Nomor Nota", "Kategori", "Nominal (Rp)", "Penerima / Toko", "Keterangan"]
    style_excel_header(ws_kantor, 1, len(headers_ktr), "Laporan Pengeluaran Operasional Kas Kantor", "")
    for col_idx, h in enumerate(headers_ktr, start=1):
        c = ws_kantor.cell(row=start_row, column=col_idx, value=h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = border_header
    r_idx = start_row + 1
    tot_ktr = 0.0
    for idx, row in enumerate(kantor_data, start=1):
        nom_k = float(row.get("nominal") or 0)
        tot_ktr += nom_k
        vals = [idx, fmt_tgl(row.get("tanggal")), row.get("nomor_nota") or "-", row.get("kategori"), nom_k, row.get("penerima_toko") or "-", row.get("keterangan") or "-"]
        for c_idx, v in enumerate(vals, start=1):
            cell = ws_kantor.cell(row=r_idx, column=c_idx, value=v)
            cell.border = border_thin
            if c_idx in (1, 2, 3, 4):
                cell.alignment = Alignment(horizontal="center")
            elif c_idx == 5:
                cell.alignment = Alignment(horizontal="right")
                cell.number_format = "#,##0"
            else:
                cell.alignment = Alignment(horizontal="left")
        r_idx += 1
    ws_kantor.cell(row=r_idx, column=1, value="TOTAL")
    ws_kantor.merge_cells(start_row=r_idx, start_column=1, end_row=r_idx, end_column=4)
    ws_kantor.cell(row=r_idx, column=5, value=tot_ktr).number_format = "#,##0"
    for c in range(1, len(headers_ktr)+1):
        ws_kantor.cell(row=r_idx, column=c).border = border_thin
        ws_kantor.cell(row=r_idx, column=c).font = Font(name="Calibri", bold=True, color="FF0F172A")
        ws_kantor.cell(row=r_idx, column=c).fill = PatternFill(start_color="FFF1F5F9", end_color="FFF1F5F9", fill_type="solid")
    autofit_columns(ws_kantor)

    # -------------------------------------------------------------
    # Sheet 5: Gaji Karyawan
    # -------------------------------------------------------------
    ws_gaji = wb.create_sheet(title="Gaji Karyawan")
    gaji_data = database.get_gaji_karyawan_list()
    headers_gj = ["No", "Tanggal Bayar", "Periode", "Nama Karyawan", "Jabatan", "Gaji Pokok (Rp)", "Pot/Tunjangan (Rp)", "Total Dibayar (Rp)", "Metode", "Keterangan"]
    style_excel_header(ws_gaji, 1, len(headers_gj), "Rekapitulasi Pembayaran Gaji Karyawan", "")
    for col_idx, h in enumerate(headers_gj, start=1):
        c = ws_gaji.cell(row=start_row, column=col_idx, value=h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = border_header
    r_idx = start_row + 1
    tot_gj = 0.0
    for idx, row in enumerate(gaji_data, start=1):
        t_dibayar = float(row.get("total_dibayar") or 0)
        tot_gj += t_dibayar
        vals = [
            idx, fmt_tgl(row.get("tanggal_bayar")), row.get("periode_gaji"), row.get("nama_karyawan"),
            row.get("jabatan") or "-", row.get("nominal_gaji"), row.get("potongan_tunjangan"),
            t_dibayar, row.get("metode_bayar"), row.get("keterangan") or "-"
        ]
        for c_idx, v in enumerate(vals, start=1):
            cell = ws_gaji.cell(row=r_idx, column=c_idx, value=v)
            cell.border = border_thin
            if c_idx in (1, 2, 3, 9):
                cell.alignment = Alignment(horizontal="center")
            elif c_idx in (6, 7, 8):
                cell.alignment = Alignment(horizontal="right")
                cell.number_format = "#,##0"
            else:
                cell.alignment = Alignment(horizontal="left")
        r_idx += 1
    ws_gaji.cell(row=r_idx, column=1, value="TOTAL GAJI DIBAYARKAN")
    ws_gaji.merge_cells(start_row=r_idx, start_column=1, end_row=r_idx, end_column=7)
    ws_gaji.cell(row=r_idx, column=8, value=tot_gj).number_format = "#,##0"
    for c in range(1, len(headers_gj)+1):
        ws_gaji.cell(row=r_idx, column=c).border = border_thin
        ws_gaji.cell(row=r_idx, column=c).font = Font(name="Calibri", bold=True, color="FF0F172A")
        ws_gaji.cell(row=r_idx, column=c).fill = PatternFill(start_color="FFF1F5F9", end_color="FFF1F5F9", fill_type="solid")
    autofit_columns(ws_gaji)
    
    wb.save(filepath)
    return True


# ==========================================
# PDF EXPORT ENGINE (REPORTLAB)
# ==========================================

# -- Helper: Paragraph yang wrap otomatis untuk sel tabel PDF --
_PDF_CELL_STYLE_NORMAL = ParagraphStyle(
    'CellNormal', fontName='Helvetica', fontSize=8, leading=10,
    wordWrap='CJK', leftIndent=0, rightIndent=0
)
_PDF_CELL_STYLE_BOLD = ParagraphStyle(
    'CellBold', fontName='Helvetica-Bold', fontSize=8, leading=10,
    wordWrap='CJK', leftIndent=0, rightIndent=0
)
_PDF_CELL_STYLE_CENTER = ParagraphStyle(
    'CellCenter', fontName='Helvetica', fontSize=8, leading=10,
    wordWrap='CJK', alignment=1, leftIndent=0, rightIndent=0
)
_PDF_CELL_STYLE_RIGHT = ParagraphStyle(
    'CellRight', fontName='Helvetica', fontSize=8, leading=10,
    wordWrap='CJK', alignment=2, leftIndent=0, rightIndent=0
)
_PDF_CELL_STYLE_SMALL = ParagraphStyle(
    'CellSmall', fontName='Helvetica', fontSize=7.5, leading=10,
    wordWrap='CJK', leftIndent=0, rightIndent=0
)

def _p(text: Any, style: ParagraphStyle = None) -> Paragraph:
    """Buat sel tabel PDF yang wrap otomatis ke baris bawah (tidak menabrak kolom sebelah)."""
    if style is None:
        style = _PDF_CELL_STYLE_NORMAL
    return Paragraph(str(text) if text is not None else "-", style)

def _pc(text: Any) -> Paragraph:
    """Paragraph rata tengah (untuk kolom tanggal, no, dll)."""
    return _p(text, _PDF_CELL_STYLE_CENTER)

def _pr(text: Any) -> Paragraph:
    """Paragraph rata kanan (untuk kolom angka Rp)."""
    return _p(text, _PDF_CELL_STYLE_RIGHT)

def _pb(text: Any) -> Paragraph:
    """Paragraph bold (untuk baris total)."""
    return _p(text, _PDF_CELL_STYLE_BOLD)

def _ps(text: Any) -> Paragraph:
    """Paragraph ukuran kecil (untuk laporan kendaraan padat)."""
    return _p(text, _PDF_CELL_STYLE_SMALL)


def create_pdf_header_elements(title: str, subtitle: str = "") -> List[Any]:
    elements = []
    company = get_company_header_info()
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CompanyTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#1E3A8A'),
        alignment=1
    )
    
    sub_style = ParagraphStyle(
        'CompanySub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748B'),
        alignment=1
    )
    
    doc_title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0F172A'),
        alignment=1
    )
    
    elements.append(Paragraph(company["nama"].upper(), title_style))
    elements.append(Paragraph(f"{company['alamat']} | Telp: {company['telepon']}", sub_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(title.upper(), doc_title_style))
    if subtitle:
        elements.append(Paragraph(subtitle, sub_style))
    elements.append(Spacer(1, 14))
    return elements

def create_pdf_signature_block() -> Table:
    company = get_company_header_info()
    date_now = datetime.now().strftime("%d %B %Y")
    
    data = [
        [f"Jawa Tengah, {date_now}", ""],
        ["Dibuat Oleh,", "Mengetahui / Menyetujui,"],
        ["", ""],
        ["", ""],
        ["( .................................... )", f"( {company['pj']} )"],
        ["Staff Administrasi & Keuangan", "Plant Manager AKP Contruction Building"]
    ]
    
    t = Table(data, colWidths=[240, 240])
    t.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    return t

def export_pengiriman_pdf(filepath: str, start_date: Optional[str] = None, end_date: Optional[str] = None, proyek_id: Optional[int] = None):
    doc = SimpleDocTemplate(filepath, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    
    periode_str = fmt_periode(start_date, end_date)
        
    elements.extend(create_pdf_header_elements("Laporan Rekapitulasi Pengiriman Beton", periode_str))
    
    data = database.get_riwayat_pengiriman(start_date=start_date, end_date=end_date, proyek_id=proyek_id)
    
    table_data = [
        [_pc("No"), _pc("Tanggal"), _pc("No Surat Jalan"), _pc("Mutu"), _pc("Vol (m3)"), _pc("Proyek"), _pc("Tujuan"), _pc("Total Tagihan (Rp)"), _pc("No Plat"), _pc("Driver")]
    ]
    
    total_vol = 0.0
    total_rev = 0.0
    
    for idx, r in enumerate(data, start=1):
        vol = float(r.get("volume_m3") or 0)
        t_pend = float(r.get("total_pendapatan") or 0)
        total_vol += vol
        total_rev += t_pend
        
        table_data.append([
            _pc(str(idx)),
            _pc(fmt_tgl(r.get("tanggal"))),
            _pc(str(r.get("no_surat_jalan") or "-")),
            _pc(str(r.get("mutu_kode") or "-")),
            _pr(f"{vol:,.2f}"),
            _p(str(r.get("proyek_nama") or "-")),
            _p(str(r.get("tujuan_pengiriman") or "-")),
            _pr(f"{t_pend:,.0f}"),
            _pc(str(r.get("no_plat_truk") or "-")),
            _pc(str(r.get("driver") or "-"))
        ])
        
    table_data.append([
        _pb("TOTAL"), "", "", "", _pr(f"{total_vol:,.2f}"), "", "", _pr(f"{total_rev:,.0f}"), "", ""
    ])
    
    col_widths = [25, 65, 85, 50, 55, 140, 130, 95, 70, 65]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8.5),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#F8FAFC')]),
        ('SPAN', (0,-1), (3,-1)),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F1F5F9')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('ALIGN', (0,-1), (3,-1), 'CENTER'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))
    elements.append(KeepTogether(create_pdf_signature_block()))
    
    doc.build(elements)
    return True

def export_stok_pdf(filepath: str):
    doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    
    elements.extend(create_pdf_header_elements("Laporan Rekapitulasi Stok Material & Valuasi", f"Dicetak pada: {datetime.now().strftime('%d/%m/%Y %H:%M')}"))
    
    data = database.get_rekap_kartu_stok()
    table_data = [
        ["No", "Kode", "Nama Material", "Satuan", "Harga (Rp)", "Total Masuk", "Terpakai", "Sisa Stok", "Aset (Rp)", "Status"]
    ]
    
    total_aset = 0.0
    for idx, r in enumerate(data, start=1):
        stk = float(r.get("stok_saat_ini") or 0)
        min_stk = float(r.get("stok_minimum") or 0)
        hrg = float(r.get("harga_beli_terbaru") or 0)
        aset = float(r.get("nilai_aset_stok") or 0)
        total_aset += aset
        stat = "KRITIS" if stk <= min_stk else "AMAN"
        table_data.append([
            str(idx),
            str(r.get("kode")),
            str(r.get("nama")),
            str(r.get("satuan")),
            f"{hrg:,.0f}",
            f"{float(r.get('total_masuk') or 0):,.2f}",
            f"{float(r.get('total_terpakai') or 0):,.2f}",
            f"{stk:,.2f}",
            f"{aset:,.0f}",
            stat
        ])
        
    table_data.append([
        "TOTAL VALUASI ASET", "", "", "", "", "", "", "", f"{total_aset:,.0f}", ""
    ])

    col_widths = [20, 50, 95, 40, 55, 60, 60, 60, 65, 35]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('ALIGN', (0,1), (3,-1), 'CENTER'),
        ('ALIGN', (4,1), (8,-1), 'RIGHT'),
        ('ALIGN', (9,1), (9,-1), 'CENTER'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 7.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('SPAN', (0,-1), (7,-1)),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F1F5F9')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('ALIGN', (0,-1), (7,-1), 'CENTER'),
    ]))
    
    elements.append(t)
    elements.append(Spacer(1, 20))
    elements.append(KeepTogether(create_pdf_signature_block()))
    doc.build(elements)
    return True

def export_keuangan_pdf(filepath: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Ekspor Dokumen PDF Buku Kas Umum & Ringkasan 4 Pilar Keuangan"""
    doc = SimpleDocTemplate(filepath, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    periode_str = fmt_periode(start_date, end_date)
        
    elements.extend(create_pdf_header_elements("Laporan Arus Kas Umum (Buku Besar)", periode_str))

    # Ringkasan Saldo 4 Pilar Card Table
    summary = database.get_ringkasan_kas()
    p_sum = database.get_ringkasan_piutang_proyek()
    s_sum = database.get_ringkasan_hutang_semen()

    sum_table_data = [
        ["Saldo Kas Plant (Aktif)", "Total Piutang Proyek", "Total Hutang Semen", "Pengeluaran Kas Kantor", "Total Gaji Terbayar"],
        [
            f"Rp {summary['saldo_akhir']:,.0f}",
            f"Rp {p_sum['sisa_piutang_proyek']:,.0f}",
            f"Rp {s_sum['sisa_hutang_semen']:,.0f}",
            f"Rp {summary['total_out_kantor']:,.0f}",
            f"Rp {summary['total_out_gaji']:,.0f}"
        ]
    ]
    t_sum = Table(sum_table_data, colWidths=[150, 150, 150, 150, 180])
    t_sum.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8.5),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#F8FAFC')),
        ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,1), (-1,1), 10),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_sum)
    elements.append(Spacer(1, 14))

    # Ledger Table
    kas_data = database.get_saldo_kas(start_date=start_date, end_date=end_date)
    table_data = [
        ["No", "Tanggal", "Kategori", "Keterangan", "Kas Masuk (Rp)", "Kas Keluar (Rp)", "Saldo Berjalan (Rp)"]
    ]

    t_in, t_out = 0.0, 0.0
    for idx, r in enumerate(kas_data, start=1):
        m = float(r.get("saldo_masuk") or 0)
        k = float(r.get("saldo_keluar") or 0)
        t_in += m
        t_out += k
        table_data.append([
            _pc(str(idx)),
            _pc(fmt_tgl(r.get("tanggal"))),
            _pc(str(r.get("kategori") or "-")),
            _p(str(r.get("keterangan") or "-")),
            _pr(f"{m:,.0f}") if m > 0 else _pc("-"),
            _pr(f"{k:,.0f}") if k > 0 else _pc("-"),
            _pr(f"{float(r.get('total_saldo') or 0):,.0f}")
        ])

    table_data.append([
        _pb("TOTAL MUTASI KAS"), "", "", "", _pr(f"{t_in:,.0f}"), _pr(f"{t_out:,.0f}"), _pr(f"{(t_in - t_out):,.0f}")
    ])

    col_widths = [25, 65, 110, 260, 100, 100, 120]
    t_ledger = Table(table_data, colWidths=col_widths, repeatRows=1)
    t_ledger.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8.5),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('SPAN', (0,-1), (3,-1)),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F1F5F9')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('ALIGN', (0,-1), (3,-1), 'CENTER'),
    ]))

    elements.append(t_ledger)
    elements.append(Spacer(1, 20))
    elements.append(KeepTogether(create_pdf_signature_block()))

    doc.build(elements)
    return True


# ==========================================
# SURAT JALAN (TIKET COR) PDF - PER TRANSAKSI
# ==========================================

def _terbilang(n: int) -> str:
    """Mengubah angka integer ke teks terbilang Bahasa Indonesia"""
    if n < 0:
        return "minus " + _terbilang(-n)
    if n == 0:
        return ""

    satuan = ["", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan",
              "sepuluh", "sebelas", "dua belas", "tiga belas", "empat belas", "lima belas",
              "enam belas", "tujuh belas", "delapan belas", "sembilan belas"]
    puluhan = ["", "", "dua puluh", "tiga puluh", "empat puluh", "lima puluh",
               "enam puluh", "tujuh puluh", "delapan puluh", "sembilan puluh"]

    if n < 20:
        return satuan[n]
    elif n < 100:
        rest = _terbilang(n % 10)
        return puluhan[n // 10] + (" " + rest if rest else "")
    elif n < 200:
        rest = _terbilang(n - 100)
        return "seratus" + (" " + rest if rest else "")
    elif n < 1000:
        rest = _terbilang(n % 100)
        return satuan[n // 100] + " ratus" + (" " + rest if rest else "")
    elif n < 2000:
        rest = _terbilang(n - 1000)
        return "seribu" + (" " + rest if rest else "")
    elif n < 1_000_000:
        rest = _terbilang(n % 1000)
        return _terbilang(n // 1000) + " ribu" + (" " + rest if rest else "")
    elif n < 1_000_000_000:
        rest = _terbilang(n % 1_000_000)
        return _terbilang(n // 1_000_000) + " juta" + (" " + rest if rest else "")
    elif n < 1_000_000_000_000:
        rest = _terbilang(n % 1_000_000_000)
        return _terbilang(n // 1_000_000_000) + " miliar" + (" " + rest if rest else "")
    else:
        rest = _terbilang(n % 1_000_000_000_000)
        return _terbilang(n // 1_000_000_000_000) + " triliun" + (" " + rest if rest else "")


def terbilang_rupiah(amount: float) -> str:
    """Mengubah nominal Rupiah ke teks terbilang, misal: 'Empat Juta Lima Ratus Ribu Rupiah'"""
    if amount is None or amount == 0:
        return "Nol Rupiah"
    n = int(round(abs(amount)))
    result = _terbilang(n).strip()
    if not result:
        return "Nol Rupiah"
    # Kapitalisasi setiap kata
    result = " ".join(w.capitalize() for w in result.split())
    return result + " Rupiah"


def format_rupiah_invoice(amount: float) -> str:
    """Format nominal angka ke format faktur/invoice: Rp.5.940.000,-"""
    val = int(round(amount or 0))
    formatted = f"{val:,}".replace(",", ".")
    return f"Rp.{formatted},-"


def cetak_surat_jalan_pdf(filepath: str, pengiriman_id: int, hide_harga: Optional[bool] = None) -> tuple:
    """
    Mencetak Surat Jalan PDF identik dengan template PT. ARCO KURNIA PRADANA:
    - A5 Landscape (210 x 148 mm)
    - Kop: Logo AKP (kiri) | Nama PT. + Alamat (kanan)
    - Dua garis horizontal tebal sebagai pemisah
    - Nomor SJ besar di kiri, Tanggal/Kepada/No Kendaraan di kanan
    - Tabel: NO | JENIS MATERIAL | VOLUME | Sat | (HARGA & JUMLAH jika hide_harga=False)
    - Baris total
    - Baris Terbilang (atau Catatan jika harga di-hide)
    - Tanda tangan: Pengirim | Sopir | Penerima
    """
    try:
        # ── Data ──────────────────────────────────────────────────────────────
        data_list = database.get_riwayat_pengiriman()
        pengiriman = next((r for r in data_list if r["id"] == pengiriman_id), None)
        if not pengiriman:
            return False, f"Pengiriman dengan ID #{pengiriman_id} tidak ditemukan."

        if hide_harga is None:
            hide_harga = bool(pengiriman.get("hide_harga_sj", 0))

        company = get_company_header_info()

        # ── Page setup: A5 Landscape ──────────────────────────────────────────
        from reportlab.lib.pagesizes import A5, landscape as rl_landscape
        PAGE_W, PAGE_H = rl_landscape(A5)   # ~595 x 421 points
        ML = 10 * mm   # left margin
        MR = 8  * mm   # right margin
        MT = 6  * mm   # top margin
        MB = 6  * mm   # bottom margin
        USABLE_W = PAGE_W - ML - MR

        doc = SimpleDocTemplate(
            filepath,
            pagesize=rl_landscape(A5),
            leftMargin=ML,
            rightMargin=MR,
            topMargin=MT,
            bottomMargin=MB
        )

        elems = []
        sty   = getSampleStyleSheet()

        # ── Colours (match logo: black text, orange accent, gray address) ────
        C_BLACK  = colors.HexColor("#0A0A0A")
        C_ORANGE = colors.HexColor("#E05A00")   # AKP orange accent
        C_GRAY   = colors.HexColor("#444444")
        C_LTGRAY = colors.HexColor("#888888")
        C_WHITE  = colors.white
        C_TBLBG  = colors.HexColor("#F5F5F5")   # light row alternate

        # ── Paragraph styles ──────────────────────────────────────────────────
        def ps(name, font="Helvetica", size=9, leading=None, color=None, align=0, bold=False):
            fn = ("Helvetica-Bold" if bold else font)
            return ParagraphStyle(
                name, parent=sty["Normal"],
                fontName=fn, fontSize=size,
                leading=leading or (size * 1.25),
                textColor=color or C_BLACK,
                alignment=align
            )

        sty_co_name  = ps("CoName",  bold=True,  size=15, color=C_BLACK,  align=0)
        sty_co_sub   = ps("CoSub",   bold=True,  size=9,  color=C_BLACK,  align=0)
        sty_co_addr  = ps("CoAddr",  size=7.5,   color=C_GRAY,  align=0)
        sty_sj_num   = ps("SJNum",   bold=True,  size=16, color=C_BLACK)
        sty_lbl      = ps("Lbl",     bold=True,  size=9,  color=C_BLACK)
        sty_val      = ps("Val",     size=9,      color=C_BLACK)
        sty_th       = ps("TH",      bold=True,  size=8.5, color=C_BLACK, align=1)
        sty_td_c     = ps("TDC",     size=9,      color=C_BLACK, align=1)
        sty_td_l     = ps("TDL",     size=9,      color=C_BLACK, align=0)
        sty_td_r     = ps("TDR",     size=9,      color=C_BLACK, align=2)
        sty_td_bold  = ps("TDBold",  bold=True,  size=9,  color=C_BLACK, align=2)
        sty_terb_lbl = ps("TerbLbl", font="Helvetica-Oblique", size=9,  color=C_BLACK)
        sty_ttd_lbl  = ps("TtdLbl",  bold=True,  size=9,  color=C_BLACK, align=1)
        sty_dots     = ps("Dots",    size=9,      color=C_BLACK, align=1)

        # ── 1. HEADER KOP ─────────────────────────────────────────────────────
        logo_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "assets", "akp_logo.png"
        )
        if not os.path.exists(logo_path):
            # fallback
            logo_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "assets", "app_logo.png"
            )

        LOGO_H = 16 * mm
        LOGO_W = 28 * mm
        LOGO_COL = LOGO_W + 4 * mm
        INFO_COL = USABLE_W - LOGO_COL

        # Company right block
        nama_perusahaan = "PT. ARCO KURNIA PRADANA"
        sub_baris       = "CONTRUCTION BUILDING"
        addr_baris      = "KARANG TENGAH RT 01 RW 02 KARANGKAJEN SECANG MAGELANG"

        co_block = [
            Paragraph(nama_perusahaan, sty_co_name),
            Paragraph(sub_baris,       sty_co_sub),
            Paragraph(addr_baris,      sty_co_addr),
        ]

        if os.path.exists(logo_path):
            logo_img = RLImage(logo_path, width=LOGO_W, height=LOGO_H)
            hdr_data  = [[logo_img, co_block]]
            hdr_table = Table(hdr_data, colWidths=[LOGO_COL, INFO_COL])
            hdr_table.setStyle(TableStyle([
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING",   (0, 0), (-1, -1), 0),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
                ("TOPPADDING",    (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]))
        else:
            hdr_data  = [["", co_block]]
            hdr_table = Table(hdr_data, colWidths=[LOGO_COL, INFO_COL])
            hdr_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING",   (0, 0), (-1, -1), 0),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
                ("TOPPADDING",    (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]))

        elems.append(hdr_table)

        # ── 2. DOUBLE THICK LINE ──────────────────────────────────────────────
        from reportlab.platypus import HRFlowable
        elems.append(Spacer(1, 1 * mm))
        elems.append(HRFlowable(width="100%", thickness=2.5, color=C_BLACK, spaceAfter=0.8))
        elems.append(HRFlowable(width="100%", thickness=0.8, color=C_BLACK, spaceAfter=1.5 * mm))

        # ── 3. SJ NUMBER (kiri besar) + INFO BLOCK (kanan) ───────────────────
        no_sj        = str(pengiriman.get("no_surat_jalan") or "-")
        tanggal_raw  = str(pengiriman.get("tanggal") or "")
        try:
            tanggal_fmt = datetime.strptime(tanggal_raw, "%Y-%m-%d").strftime("%d %B %Y")
        except Exception:
            tanggal_fmt = tanggal_raw

        proyek_nama  = str(pengiriman.get("proyek_nama")    or "")
        no_kendaraan = str(pengiriman.get("no_plat_truk")   or "")
        driver_name  = str(pengiriman.get("driver")          or "")
        mutu_kode    = str(pengiriman.get("mutu_kode")       or "")
        tujuan       = str(pengiriman.get("tujuan_pengiriman") or "")
        volume_m3    = float(pengiriman.get("volume_m3")    or 0)
        h_jual       = float(pengiriman.get("harga_jual_per_m3") or 0)
        total_tag    = float(pengiriman.get("total_pendapatan")  or 0)
        catatan      = str(pengiriman.get("catatan")         or "")

        # Gabung no kendaraan + sopir
        kend_str = no_kendaraan
        if driver_name:
            kend_str = f"{no_kendaraan}  /  {driver_name}" if no_kendaraan else driver_name

        # Info block (kanan): tabel label-nilai
        COLON_W = 10 * mm
        LABEL_W = 26 * mm
        VAL_W   = USABLE_W * 0.44 - LABEL_W - COLON_W

        info_rows = [
            [Paragraph("Tanggal",      sty_lbl), Paragraph(":", sty_lbl), Paragraph(tanggal_fmt,  sty_val)],
            [Paragraph("Kepada",       sty_lbl), Paragraph(":", sty_lbl), Paragraph(proyek_nama,  sty_val)],
            [Paragraph("No Kendaraan", sty_lbl), Paragraph(":", sty_lbl), Paragraph(kend_str,     sty_val)],
        ]
        info_tbl = Table(info_rows, colWidths=[LABEL_W, COLON_W, VAL_W])
        info_tbl.setStyle(TableStyle([
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]))

        SJ_COL   = USABLE_W * 0.56
        INFO_COL2 = USABLE_W - SJ_COL

        sj_info = Table(
            [[Paragraph(no_sj, sty_sj_num), info_tbl]],
            colWidths=[SJ_COL, INFO_COL2]
        )
        sj_info.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        elems.append(sj_info)
        elems.append(Spacer(1, 1.5 * mm))

        # ── 4. TABEL UTAMA ────────────────────────────────────────────────────
        jenis_str = f"Beton {mutu_kode}"
        if tujuan and tujuan != "-":
            jenis_str += f"  –  {tujuan}"

        vol_str  = f"{volume_m3:,.2f}".replace(",", ".")
        EMPTY_ROWS = 3
        ROW_H   = 9  * mm
        EMPTY_H = 7  * mm
        row_heights = [7 * mm] + [ROW_H] + [EMPTY_H] * EMPTY_ROWS + [7 * mm]

        if hide_harga:
            # FORMAT NON-HARGA (HARGA & JUMLAH DISEMBUNYIKAN)
            CW_NO   = 12 * mm
            CW_VOL  = 28 * mm
            CW_SAT  = 18 * mm
            CW_MAT  = USABLE_W - CW_NO - CW_VOL - CW_SAT

            col_widths = [CW_NO, CW_MAT, CW_VOL, CW_SAT]

            # Header row
            mat_table_data = [[
                Paragraph("NO",             sty_th),
                Paragraph("JENIS MATERIAL", sty_th),
                Paragraph("VOLUME",         sty_th),
                Paragraph("Sat",            sty_th),
            ]]

            # Baris 1: Produk beton cor
            mat_table_data.append([
                Paragraph("1",       sty_td_c),
                Paragraph(jenis_str, sty_td_l),
                Paragraph(vol_str,   sty_td_c),
                Paragraph("m³",      sty_td_c),
            ])

            # Baris kosong
            for _ in range(EMPTY_ROWS):
                mat_table_data.append(["", "", "", ""])

            # Baris total volume
            mat_table_data.append([
                "", Paragraph("TOTAL VOLUME", sty_td_bold),
                Paragraph(vol_str, sty_td_bold),
                Paragraph("m³", sty_td_bold),
            ])

        else:
            # FORMAT LENGKAP DENGAN HARGA
            CW_NO   = 10 * mm
            CW_MAT  = 68 * mm
            CW_VOL  = 22 * mm
            CW_SAT  = 14 * mm
            CW_HRG  = 30 * mm
            CW_JML  = USABLE_W - CW_NO - CW_MAT - CW_VOL - CW_SAT - CW_HRG

            col_widths = [CW_NO, CW_MAT, CW_VOL, CW_SAT, CW_HRG, CW_JML]
            hrg_str  = f"{h_jual:,.0f}".replace(",", ".")
            jml_str  = f"{total_tag:,.0f}".replace(",", ".")

            # Header row
            mat_table_data = [[
                Paragraph("NO",             sty_th),
                Paragraph("JENIS MATERIAL", sty_th),
                Paragraph("VOLUME",         sty_th),
                Paragraph("Sat",            sty_th),
                Paragraph("HARGA (Rp)",     sty_th),
                Paragraph("JUMLAH (Rp)",    sty_th),
            ]]

            # Baris 1: Produk beton cor
            mat_table_data.append([
                Paragraph("1",       sty_td_c),
                Paragraph(jenis_str, sty_td_l),
                Paragraph(vol_str,   sty_td_c),
                Paragraph("m³",      sty_td_c),
                Paragraph(hrg_str,   sty_td_r),
                Paragraph(jml_str,   sty_td_r),
            ])

            # Baris kosong
            for _ in range(EMPTY_ROWS):
                mat_table_data.append(["", "", "", "", "", ""])

            # Baris total
            mat_table_data.append([
                "", "", "", "",
                Paragraph("Rp.", sty_td_bold),
                Paragraph(jml_str, sty_td_bold),
            ])

        mat_table = Table(
            mat_table_data,
            colWidths=col_widths,
            rowHeights=row_heights,
            repeatRows=1
        )
        mat_table.setStyle(TableStyle([
            # Header
            ("BACKGROUND",    (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 8),
            ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
            ("VALIGN",        (0, 0), (-1, 0), "MIDDLE"),

            # Data
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 1), (-1, -1), 8.5),
            ("VALIGN",        (0, 1), (-1, -2), "TOP"),
            ("VALIGN",        (0, -1), (-1, -1), "MIDDLE"),

            # Full grid (black thin border, identik template)
            ("GRID",          (0, 0), (-1, -1), 0.8, C_BLACK),

            # Baris total: top border sedikit lebih tebal
            ("LINEABOVE",     (0, -1), (-1, -1), 0.8, C_BLACK),

            # Padding
            ("TOPPADDING",    (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING",   (0, 0), (-1, -1), 3),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
        ]))
        elems.append(mat_table)
        elems.append(Spacer(1, 1.5 * mm))

        # ── 5. TERBILANG / CATATAN ──────────────────────────────────────────
        terb_lbl_w  = 24 * mm
        terb_box_w  = USABLE_W - terb_lbl_w

        if hide_harga:
            # Jika harga di-hide, tampilkan Catatan / Keterangan di kotak agar tidak membocorkan nominal
            terb_data = [[
                Paragraph("<i>Catatan :</i>", sty_terb_lbl),
                Paragraph(catatan if catatan else "-", sty_val),
            ]]
        else:
            terb_str = terbilang_rupiah(total_tag)
            terb_data = [[
                Paragraph("<i>Terbilang :</i>", sty_terb_lbl),
                Paragraph(terb_str, sty_val),
            ]]

        terb_table = Table(
            terb_data,
            colWidths=[terb_lbl_w, terb_box_w],
            rowHeights=[7 * mm]
        )
        terb_table.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
            ("TOPPADDING",    (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            # Kotak hanya pada sel terbilang (kolom kanan)
            ("BOX",           (1, 0), (1, 0), 0.8, C_BLACK),
            # Garis bawah label kiri
            ("LINEBELOW",     (0, 0), (0, 0), 0, C_WHITE),
        ]))
        elems.append(terb_table)
        elems.append(Spacer(1, 2.5 * mm))

        # ── 6. TANDA TANGAN ──────────────────────────────────────────────────
        COL3 = USABLE_W / 3.0
        DOTS = "……………………"

        ttd_data = [
            # Label
            [Paragraph("Pengirim", sty_ttd_lbl),
             Paragraph("Sopir",    sty_ttd_lbl),
             Paragraph("Penerima", sty_ttd_lbl)],
            # Ruang kosong baris 1
            ["", "", ""],
            # Ruang kosong baris 2
            ["", "", ""],
            # Titik-titik
            [Paragraph(DOTS, sty_dots),
             Paragraph(DOTS, sty_dots),
             Paragraph(DOTS, sty_dots)],
        ]
        TTD_ROW_H = [5 * mm, 4 * mm, 4 * mm, 5 * mm]

        ttd_table = Table(
            ttd_data,
            colWidths=[COL3, COL3, COL3],
            rowHeights=TTD_ROW_H
        )
        ttd_table.setStyle(TableStyle([
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 0), (-1, -1), 9),
            ("TOPPADDING",    (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        elems.append(ttd_table)

        # ── 7. Catatan (opsional) ─────────────────────────────────────────────
        if catatan and catatan != "-":
            elems.append(Spacer(1, 2 * mm))
            elems.append(Paragraph(
                f"<i>Catatan: {catatan}</i>",
                ps("FootNote", font="Helvetica-Oblique", size=7.5, color=C_LTGRAY)
            ))

        doc.build(elems)
        return True, filepath

    except Exception as exc:
        import traceback
        return False, f"Gagal mencetak Surat Jalan: {exc}\n{traceback.format_exc()}"


def cetak_invoice_pdf(filepath: str, pengiriman_id: int) -> tuple:
    """
    Mencetak Invoice PDF identik dengan template PT. ARCO KURNIA PRADANA:
    - Kertas A4 Portrait
    - Header banner AKP CONSTRUCTION BUILDING + Karangtengah Secang Magelang
    - Judul INVOICE
    - Nama Customer & Nama Pekerjaan
    - Garis pemisah tipis
    - Tagihan (Beton K300 / 6 m3) & Besar Tagihan (Rp.5.940.000,-)
    - Garis pemisah tebal
    - TOTAL (Rp.5.940.000,-)
    - Garis pemisah tebal
    - Terbilang (# lima juta sembilan ratus empat puluh ribu rupiah #)
    - Garis pemisah tebal
    - Transfer Bank Account BCA di kiri bawah
    - Tanggal Magelang, Tanda Tangan Basah & Nama Adhe Kurnia Pradana di kanan bawah
    """
    try:
        data_list = database.get_riwayat_pengiriman()
        pengiriman = next((r for r in data_list if r["id"] == pengiriman_id), None)
        if not pengiriman:
            return False, f"Pengiriman dengan ID #{pengiriman_id} tidak ditemukan."

        settings = getattr(database, "get_settings", lambda: {})()
        bank_nama = settings.get("bank_nama", "Bank Central Asia (BCA).")
        bank_rekening = settings.get("bank_rekening", "1222218475")
        bank_atas_nama = settings.get("bank_atas_nama", "ADHE KURNIA PRADANA")
        invoice_kota = settings.get("invoice_kota", "Magelang")
        invoice_penandatangan = settings.get("invoice_penandatangan", "ADHE KURNIA PRADANA")

        # Parsing data
        proyek_nama = str(pengiriman.get("proyek_nama") or "Customer")
        mutu_raw = str(pengiriman.get("mutu_kode") or "K300")
        mutu_clean = mutu_raw.replace("-", "")
        pekerjaan_str = mutu_clean if mutu_clean.lower().startswith("beton") else f"Beton {mutu_clean}"

        volume_m3 = float(pengiriman.get("volume_m3") or 0)
        vol_str = f"{volume_m3:g}" if volume_m3 == int(volume_m3) else f"{volume_m3:.2f}".rstrip("0").rstrip(".")
        tagihan_str = f"{pekerjaan_str} / {vol_str} m³"

        total_tag = float(pengiriman.get("total_pendapatan") or 0)
        besar_tagihan_str = format_rupiah_invoice(total_tag)

        terb_txt = _terbilang(int(round(total_tag))).strip().lower()
        if not terb_txt:
            terb_txt = "nol"
        terbilang_str = f"# {terb_txt} rupiah #"

        # Tanggal Indonesia
        BULAN_INDO = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        tanggal_raw = str(pengiriman.get("tanggal") or "")
        try:
            t_dt = datetime.strptime(tanggal_raw, "%Y-%m-%d")
            tanggal_fmt = f"{t_dt.day} {BULAN_INDO[t_dt.month]} {t_dt.year}"
        except Exception:
            tanggal_fmt = tanggal_raw

        # Setup Document A4 Portrait
        ML = 18 * mm
        MR = 18 * mm
        MT = 16 * mm
        MB = 16 * mm
        PAGE_W, PAGE_H = A4
        USABLE_W = PAGE_W - ML - MR

        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            leftMargin=ML,
            rightMargin=MR,
            topMargin=MT,
            bottomMargin=MB
        )

        elems = []
        base_styles = getSampleStyleSheet()

        C_BLACK = colors.HexColor("#000000")
        C_TITLE = colors.HexColor("#0F172A")
        C_TEXT = colors.HexColor("#0F172A")

        p_title = ParagraphStyle('InvTitle', parent=base_styles['Normal'], fontName='Helvetica-Bold', fontSize=24, leading=28, textColor=C_TITLE)
        p_bold = ParagraphStyle('InvBold', parent=base_styles['Normal'], fontName='Helvetica-Bold', fontSize=10.5, leading=14, textColor=C_TEXT)
        p_reg = ParagraphStyle('InvReg', parent=base_styles['Normal'], fontName='Helvetica', fontSize=10.5, leading=14, textColor=C_TEXT)
        p_tot_lbl = ParagraphStyle('InvTotLbl', parent=base_styles['Normal'], fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=C_TEXT)
        p_tot_val = ParagraphStyle('InvTotVal', parent=base_styles['Normal'], fontName='Helvetica-Bold', fontSize=16, leading=20, alignment=2, textColor=C_TEXT)
        p_terb = ParagraphStyle('InvTerb', parent=base_styles['Normal'], fontName='Helvetica-Oblique', fontSize=10.5, leading=14, textColor=C_TEXT)

        # 1. Header Banner
        hdr_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "invoice_header.png")
        if os.path.exists(hdr_path):
            img_w = USABLE_W
            img_h = USABLE_W * (87.0 / 874.0)
            elems.append(RLImage(hdr_path, width=img_w, height=img_h))
        else:
            # Fallback jika gambar header tidak ditemukan
            company = get_company_header_info()
            elems.append(Paragraph(f"<b>{company['nama']}</b>", p_title))
            elems.append(Paragraph(f"{company['alamat']} | Telp: {company['telepon']}", p_reg))
            elems.append(HRFlowable(width="100%", thickness=2, color=C_BLACK, spaceBefore=4, spaceAfter=2))

        elems.append(Spacer(1, 10 * mm))

        # 2. Judul INVOICE
        elems.append(Paragraph("INVOICE", p_title))
        elems.append(Spacer(1, 6 * mm))

        # 3. Customer & Pekerjaan
        col1_w = 38 * mm
        col2_w = 6 * mm
        col3_w = USABLE_W - col1_w - col2_w

        t1_data = [
            [Paragraph("Nama Customer", p_reg), Paragraph(":", p_reg), Paragraph(f"<b>{proyek_nama}</b>", p_reg)],
            [Paragraph("Nama Pekerjaan", p_reg), Paragraph(":", p_reg), Paragraph(f"<b>{pekerjaan_str}</b>", p_reg)]
        ]
        t1 = Table(t1_data, colWidths=[col1_w, col2_w, col3_w])
        t1.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        elems.append(t1)
        elems.append(Spacer(1, 2 * mm))

        # Garis pemisah tipis
        elems.append(HRFlowable(width="100%", thickness=1.0, color=C_BLACK, spaceBefore=2, spaceAfter=4))
        elems.append(Spacer(1, 1 * mm))

        # 4. Tagihan & Besar Tagihan
        t2_data = [
            [Paragraph("Tagihan", p_reg), Paragraph(":", p_reg), Paragraph(f"<b>{tagihan_str}</b>", p_reg)],
            [Paragraph("Besar Tagihan", p_reg), Paragraph(":", p_reg), Paragraph(f"<b>{besar_tagihan_str}</b>", p_reg)]
        ]
        t2 = Table(t2_data, colWidths=[col1_w, col2_w, col3_w])
        t2.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        elems.append(t2)
        elems.append(Spacer(1, 2 * mm))

        # Garis pemisah tebal
        elems.append(HRFlowable(width="100%", thickness=2.2, color=C_BLACK, spaceBefore=2, spaceAfter=4))

        # 5. TOTAL
        tot_tbl = Table([
            [Paragraph("TOTAL", p_tot_lbl), Paragraph(besar_tagihan_str, p_tot_val)]
        ], colWidths=[USABLE_W * 0.4, USABLE_W * 0.6])
        tot_tbl.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elems.append(tot_tbl)

        # Garis pemisah tebal
        elems.append(HRFlowable(width="100%", thickness=2.2, color=C_BLACK, spaceBefore=3, spaceAfter=4))

        # 6. Terbilang
        elems.append(Paragraph(f"<b>Terbilang:</b> <i>{terbilang_str}</i>", p_terb))

        # Garis pemisah tebal
        elems.append(HRFlowable(width="100%", thickness=2.2, color=C_BLACK, spaceBefore=4, spaceAfter=8))
        elems.append(Spacer(1, 3 * mm))

        # 7. Informasi Rekening Bank Transfer (Sisi Kiri) & Tanda Tangan (Sisi Kanan)
        b_col1 = 28 * mm
        b_col2 = 5 * mm
        b_col3 = 55 * mm
        bank_data = [
            [Paragraph("<b>Transfer Bank Account:</b>", p_bold), "", ""],
            [Paragraph("Nama", p_reg), Paragraph(":", p_reg), Paragraph(f"<b>{bank_atas_nama}</b>", p_reg)],
            [Paragraph("Bank", p_reg), Paragraph(":", p_reg), Paragraph(f"<b>{bank_nama}</b>", p_reg)],
            [Paragraph("Account No", p_reg), Paragraph(":", p_reg), Paragraph(f"<b>{bank_rekening}</b>", p_reg)],
        ]
        tbl_bank = Table(bank_data, colWidths=[b_col1, b_col2, b_col3])
        tbl_bank.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('SPAN', (0, 0), (2, 0)),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))

        # Blok tanda tangan sisi kanan
        sig_w = USABLE_W - (b_col1 + b_col2 + b_col3)
        p_sig_city = ParagraphStyle('SigCity', parent=p_bold, alignment=1)
        p_sig_name = ParagraphStyle('SigName', parent=p_bold, alignment=1)

        sig_img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "invoice_signature.png")
        sig_elements = [
            Paragraph(f"{invoice_kota}, {tanggal_fmt}", p_sig_city)
        ]
        if os.path.exists(sig_img_path):
            sig_elements.append(RLImage(sig_img_path, width=20 * mm, height=26 * mm))
        else:
            sig_elements.append(Spacer(1, 26 * mm))
        sig_elements.append(Paragraph(f"<u><b>{invoice_penandatangan}</b></u>", p_sig_name))

        tbl_sig = Table([[sig_elements[0]], [sig_elements[1]], [sig_elements[2]]], colWidths=[sig_w])
        tbl_sig.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))

        bottom_table = Table([[tbl_bank, tbl_sig]], colWidths=[b_col1 + b_col2 + b_col3, sig_w])
        bottom_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        elems.append(bottom_table)

        doc.build(elems)
        return True, filepath

    except Exception as exc:
        import traceback
        return False, f"Gagal mencetak Invoice: {exc}\n{traceback.format_exc()}"


# ==============================================================================
# 5. EXPORT OPERASIONAL KENDARAAN (EXCEL & PDF)
# ==============================================================================

def export_operasional_kendaraan_excel(filepath: str,
                                       start_date: Optional[str] = None,
                                       end_date: Optional[str] = None,
                                       kendaraan_id: Optional[int] = None,
                                       driver: Optional[str] = None,
                                       kategori: Optional[str] = None,
                                       proyek_id: Optional[int] = None) -> Tuple[bool, str]:
    """Ekspor Laporan Biaya Operasional Kendaraan ke Microsoft Excel (.xlsx) dengan 2 Sheet resmi"""
    try:
        wb = openpyxl.Workbook()
        
        # -------------------------------------------------------------
        # SHEET 1: RIWAYAT TRANSAKSI OPERASIONAL
        # -------------------------------------------------------------
        ws_trx = wb.active
        ws_trx.title = "Riwayat Biaya Operasional"
        ws_trx.views.sheetView[0].showGridLines = True
        
        headers_trx = [
            "No", "Tanggal", "No. Nota", "No. Plat", "Nama Unit", "Jenis Kendaraan",
            "Driver / Supir", "Kategori Biaya", "Nominal (Rp)", "SPBU / Bengkel",
            "Proyek Terkait", "Keterangan"
        ]
        
        periode_str = fmt_periode(start_date, end_date)
            
        style_excel_header(ws_trx, 1, len(headers_trx), "Laporan Riwayat Biaya Operasional Kendaraan", periode_str)
        
        # Info Parameter Filter
        filter_row = 5
        filter_texts = []
        if kendaraan_id and kendaraan_id != -1:
            k_obj = database.get_kendaraan_by_id(kendaraan_id) if hasattr(database, "get_kendaraan_by_id") else None
            filter_texts.append(f"Kendaraan: {k_obj.get('no_plat') if k_obj else kendaraan_id}")
        if driver and driver != "Semua Driver":
            filter_texts.append(f"Driver: {driver}")
        if kategori and kategori != "Semua Kategori":
            filter_texts.append(f"Kategori: {kategori}")
        if proyek_id and proyek_id != -1:
            pr_obj = database.get_proyek_by_id(proyek_id) if hasattr(database, "get_proyek_by_id") else None
            filter_texts.append(f"Proyek: {pr_obj.get('nama') if pr_obj else proyek_id}")
            
        if filter_texts:
            ws_trx.cell(row=filter_row, column=1, value="Filter Terpasang: " + " | ".join(filter_texts))
            ws_trx.cell(row=filter_row, column=1).font = Font(name="Calibri", size=10, italic=True, color="475569")
            start_table_row = 7
        else:
            start_table_row = 6

        # Header Kolom Tabel Transaksi
        fill_navy = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )
        double_bottom_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='double', color='0F172A')
        )

        for col_idx, col_name in enumerate(headers_trx, start=1):
            c = ws_trx.cell(row=start_table_row, column=col_idx, value=col_name)
            c.fill = fill_navy
            c.font = font_header
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            c.border = thin_border
        ws_trx.row_dimensions[start_table_row].height = 26

        # Isi Data Transaksi
        biaya_data = database.get_biaya_kendaraan_list(
            kendaraan_id=kendaraan_id,
            start_date=start_date,
            end_date=end_date,
            kategori=kategori,
            driver=driver,
            proyek_id=proyek_id
        )

        current_row = start_table_row + 1
        total_nominal = 0.0

        for idx, row in enumerate(biaya_data, start=1):
            nom = float(row.get("nominal") or 0)
            total_nominal += nom
            
            fill_row = PatternFill(start_color="F8FAFC" if idx % 2 == 0 else "FFFFFF", fill_type="solid")
            
            row_vals = [
                idx,
                fmt_tgl(row.get("tanggal")),
                str(row.get("nomor_nota") or "-"),
                str(row.get("no_plat") or "-"),
                str(row.get("nama_kendaraan") or "-"),
                str(row.get("jenis_kendaraan") or "-"),
                str(row.get("driver_nama") or "-"),
                str(row.get("kategori") or "-"),
                nom,
                str(row.get("penerima_toko") or "-"),
                str(row.get("proyek_nama") or "-"),
                str(row.get("keterangan") or "-")
            ]

            for c_idx, val in enumerate(row_vals, start=1):
                cell = ws_trx.cell(row=current_row, column=c_idx, value=val)
                cell.fill = fill_row
                cell.border = thin_border
                cell.font = Font(name="Calibri", size=10)
                
                # Alignments & Numbers
                if c_idx in (1, 2, 3, 4):
                    cell.alignment = Alignment(horizontal="center", vertical="top")
                elif c_idx == 9:  # Nominal (Rp)
                    cell.alignment = Alignment(horizontal="right", vertical="top")
                    cell.number_format = "#,##0"
                    cell.font = Font(name="Calibri", size=10, bold=True)
                elif c_idx in (11, 12):  # Proyek & Keterangan — wrap text
                    cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="top")

            current_row += 1

        # Total Row
        ws_trx.cell(row=current_row, column=1, value="TOTAL PENGELUARAN BIAYA OPERASIONAL")
        ws_trx.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=8)
        tot_label = ws_trx.cell(row=current_row, column=1)
        tot_label.font = Font(name="Calibri", size=11, bold=True, color="0F172A")
        tot_label.alignment = Alignment(horizontal="right", vertical="center")

        tot_val = ws_trx.cell(row=current_row, column=9, value=total_nominal)
        tot_val.font = Font(name="Calibri", size=11, bold=True, color="1E3A8A")
        tot_val.number_format = "#,##0"
        tot_val.alignment = Alignment(horizontal="right", vertical="center")

        for c_idx in range(1, len(headers_trx) + 1):
            ws_trx.cell(row=current_row, column=c_idx).border = double_bottom_border

        # -------------------------------------------------------------
        # SHEET 2: REKAPITULASI TOTAL BIAYA PER KENDARAAN
        # -------------------------------------------------------------
        ws_rekap = wb.create_sheet(title="Rekapitulasi per Kendaraan")
        ws_rekap.views.sheetView[0].showGridLines = True
        
        headers_rekap = [
            "No", "No. Plat", "Nama Unit", "Jenis Kendaraan", "Driver Default", "Status Unit",
            "Total BBM (Rp)", "Total Servis (Rp)", "Lain-lain (Rp)", "TOTAL BIAYA (Rp)", "Frekuensi"
        ]
        style_excel_header(ws_rekap, 1, len(headers_rekap), "Rekapitulasi Biaya Operasional per Kendaraan", periode_str)
        
        r_start_row = 6
        for col_idx, col_name in enumerate(headers_rekap, start=1):
            c = ws_rekap.cell(row=r_start_row, column=col_idx, value=col_name)
            c.fill = fill_navy
            c.font = font_header
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            c.border = thin_border
        ws_rekap.row_dimensions[r_start_row].height = 26

        rekap_data = database.get_rekap_biaya_per_kendaraan(start_date=start_date, end_date=end_date)
        r_cur_row = r_start_row + 1
        
        sum_bbm = 0.0
        sum_servis = 0.0
        sum_lain = 0.0
        sum_grand_total = 0.0
        sum_freq = 0

        for idx, r in enumerate(rekap_data, start=1):
            t_bbm = float(r.get("total_bbm") or 0)
            t_srv = float(r.get("total_servis") or 0)
            t_oth = float(r.get("total_lainnya") or 0)
            t_tot = float(r.get("total_biaya") or 0)
            freq = int(r.get("frekuensi_transaksi") or 0)

            sum_bbm += t_bbm
            sum_servis += t_srv
            sum_lain += t_oth
            sum_grand_total += t_tot
            sum_freq += freq

            fill_row = PatternFill(start_color="F8FAFC" if idx % 2 == 0 else "FFFFFF", fill_type="solid")
            
            r_vals = [
                idx,
                str(r.get("no_plat") or "-"),
                str(r.get("nama_kendaraan") or "-"),
                str(r.get("jenis_kendaraan") or "-"),
                str(r.get("driver_default") or "-"),
                str(r.get("status") or "tersedia").capitalize(),
                t_bbm,
                t_srv,
                t_oth,
                t_tot,
                f"{freq} Nota"
            ]

            for c_idx, val in enumerate(r_vals, start=1):
                cell = ws_rekap.cell(row=r_cur_row, column=c_idx, value=val)
                cell.fill = fill_row
                cell.border = thin_border
                cell.font = Font(name="Calibri", size=10)
                
                if c_idx in (1, 2, 6, 11):
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                elif c_idx in (7, 8, 9, 10):
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                    cell.number_format = "#,##0"
                    if c_idx == 10:
                        cell.font = Font(name="Calibri", size=10, bold=True, color="1E3A8A")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center")

            r_cur_row += 1

        # Grand Total Rekap
        ws_rekap.cell(row=r_cur_row, column=1, value="TOTAL KESELURUHAN ARMADA")
        ws_rekap.merge_cells(start_row=r_cur_row, start_column=1, end_row=r_cur_row, end_column=6)
        tot_r_lbl = ws_rekap.cell(row=r_cur_row, column=1)
        tot_r_lbl.font = Font(name="Calibri", size=11, bold=True, color="0F172A")
        tot_r_lbl.alignment = Alignment(horizontal="right", vertical="center")

        ws_rekap.cell(row=r_cur_row, column=7, value=sum_bbm).number_format = "#,##0"
        ws_rekap.cell(row=r_cur_row, column=8, value=sum_servis).number_format = "#,##0"
        ws_rekap.cell(row=r_cur_row, column=9, value=sum_lain).number_format = "#,##0"
        
        cell_g_tot = ws_rekap.cell(row=r_cur_row, column=10, value=sum_grand_total)
        cell_g_tot.number_format = "#,##0"
        cell_g_tot.font = Font(name="Calibri", size=11, bold=True, color="1E3A8A")
        
        cell_f_tot = ws_rekap.cell(row=r_cur_row, column=11, value=f"{sum_freq} Nota")
        cell_f_tot.alignment = Alignment(horizontal="center", vertical="center")
        cell_f_tot.font = Font(name="Calibri", size=10, bold=True)

        for c_idx in range(1, len(headers_rekap) + 1):
            ws_rekap.cell(row=r_cur_row, column=c_idx).border = double_bottom_border
            if c_idx in (7, 8, 9, 10):
                ws_rekap.cell(row=r_cur_row, column=c_idx).font = Font(name="Calibri", size=10, bold=True)

        # Auto-fit Column Widths
        for sheet in (ws_trx, ws_rekap):
            for col in sheet.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.row > 4 and cell.value:
                        val_str = str(cell.value)
                        if len(val_str) > max_len and len(val_str) < 50:
                            max_len = len(val_str)
                sheet.column_dimensions[col_letter].width = max(max_len + 4, 12)

        wb.save(filepath)
        return True, filepath

    except Exception as exc:
        import traceback
        return False, f"Gagal mengekspor Laporan Operasional Kendaraan Excel: {exc}\n{traceback.format_exc()}"


def export_operasional_kendaraan_pdf(filepath: str,
                                      start_date: Optional[str] = None,
                                      end_date: Optional[str] = None,
                                      kendaraan_id: Optional[int] = None,
                                      driver: Optional[str] = None,
                                      kategori: Optional[str] = None,
                                      proyek_id: Optional[int] = None) -> Tuple[bool, str]:
    """Ekspor Laporan Biaya Operasional Kendaraan ke format PDF dokumen siap cetak"""
    try:
        doc = SimpleDocTemplate(filepath, pagesize=landscape(A4), rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=24)
        elements = []

        periode_str = fmt_periode(start_date, end_date)

        elements.extend(create_pdf_header_elements("Laporan Biaya & Operasional Kendaraan", periode_str))

        # Query Data
        biaya_data = database.get_biaya_kendaraan_list(
            kendaraan_id=kendaraan_id,
            start_date=start_date,
            end_date=end_date,
            kategori=kategori,
            driver=driver,
            proyek_id=proyek_id
        )

        styles_ss = getSampleStyleSheet()
        p_bold = ParagraphStyle('BoldText', parent=styles_ss['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=11)
        p_normal = ParagraphStyle('NormText', parent=styles_ss['Normal'], fontName='Helvetica', fontSize=8, leading=10)
        p_title_sec = ParagraphStyle('SecTitle', parent=styles_ss['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#1E3A8A'))

        # Summary Ringkasan Biaya
        total_biaya = sum(float(r.get("nominal") or 0) for r in biaya_data)
        total_bbm = sum(float(r.get("nominal") or 0) for r in biaya_data if "BBM" in str(r.get("kategori") or "") or "Solar" in str(r.get("kategori") or ""))
        total_servis = sum(float(r.get("nominal") or 0) for r in biaya_data if any(k in str(r.get("kategori") or "") for k in ("Servis", "Bengkel", "Sparepart", "Oli")))
        total_lain = total_biaya - (total_bbm + total_servis)

        summary_box_data = [
            [
                Paragraph(f"<b>Total Pengeluaran:</b><br/>Rp {total_biaya:,.0f}", p_bold),
                Paragraph(f"<b>Total BBM / Solar:</b><br/>Rp {total_bbm:,.0f}", p_bold),
                Paragraph(f"<b>Total Servis & Bengkel:</b><br/>Rp {total_servis:,.0f}", p_bold),
                Paragraph(f"<b>Biaya Lain-lain:</b><br/>Rp {total_lain:,.0f}", p_bold),
                Paragraph(f"<b>Frekuensi Transaksi:</b><br/>{len(biaya_data)} Nota", p_bold),
            ]
        ]
        sum_table = Table(summary_box_data, colWidths=[155, 155, 155, 155, 130])
        sum_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(sum_table)
        elements.append(Spacer(1, 12))

        # Tabel Transaksi
        elements.append(Paragraph("RINCIAN RIWAYAT TRANSAKSI OPERASIONAL KENDARAAN", p_title_sec))
        elements.append(Spacer(1, 4))

        headers = [_pc("No"), _pc("Tanggal"), _pc("No. Nota"), _pc("Armada / Plat"), _pc("Driver"), _pc("Kategori Biaya"), _pc("Nominal (Rp)"), _pc("SPBU / Bengkel"), _pc("Proyek"), _pc("Keterangan")]
        col_widths = [22, 58, 68, 78, 72, 90, 72, 88, 82, 120]  # total ~750

        table_rows = [headers]
        for idx, r in enumerate(biaya_data, start=1):
            nom = float(r.get("nominal") or 0)
            plat_str = str(r.get("no_plat") or "-")
            if r.get("nama_kendaraan"):
                plat_str += f"\n({r['nama_kendaraan']})"
            table_rows.append([
                _pc(str(idx)),
                _pc(fmt_tgl(r.get("tanggal"))),
                _ps(str(r.get("nomor_nota") or "-")),
                _ps(plat_str),
                _ps(str(r.get("driver_nama") or "-")),
                _ps(str(r.get("kategori") or "-")),
                _pr(f"{nom:,.0f}"),
                _ps(str(r.get("penerima_toko") or "-")),
                _ps(str(r.get("proyek_nama") or "-")),
                _ps(str(r.get("keterangan") or "-"))
            ])

        # Baris Total
        table_rows.append([_pb("TOTAL"), "", "", "", "", "", _pr(f"{total_biaya:,.0f}"), "", "", ""])

        t_biaya = Table(table_rows, colWidths=col_widths, repeatRows=1)
        t_biaya.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F8FAFC')]),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            # Baris Total
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 8),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E2E8F0')),
            ('ALIGN', (0, -1), (0, -1), 'CENTER'),
        ]))
        elements.append(t_biaya)
        elements.append(Spacer(1, 16))

        # Tanda Tangan
        elements.append(KeepTogether([create_pdf_signature_block()]))

        doc.build(elements)
        return True, filepath

    except Exception as exc:
        import traceback
        return False, f"Gagal mengekspor Laporan Operasional Kendaraan PDF: {exc}\n{traceback.format_exc()}"


# ==========================================
# FILE OPENING UTILITIES (CHROME & EXCEL)
# ==========================================

def open_pdf_document(filepath: str) -> Tuple[bool, str]:
    """
    Membuka file PDF di Google Chrome (prioritas utama) atau PDF viewer default sistem.
    Mengembalikan (success: bool, message: str).
    """
    import subprocess
    import webbrowser

    if not filepath or not os.path.exists(filepath):
        return False, "File PDF tidak ditemukan."

    abs_path = os.path.abspath(filepath)
    opened = False

    # Daftar lokasi executable Google Chrome pada Windows
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
    ]

    for cp in chrome_paths:
        if os.path.exists(cp):
            try:
                subprocess.Popen([cp, abs_path])
                opened = True
                break
            except Exception:
                pass

    if not opened:
        try:
            file_url = f"file:///{abs_path.replace(os.sep, '/')}"
            webbrowser.open(file_url)
            opened = True
        except Exception:
            pass

    if not opened:
        try:
            os.startfile(abs_path)
            opened = True
        except Exception:
            try:
                from PySide6.QtGui import QDesktopServices
                from PySide6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl.fromLocalFile(abs_path))
                opened = True
            except Exception as e:
                return False, f"Gagal membuka PDF secara otomatis: {str(e)}"

    return True, "File PDF berhasil dibuka."


def open_excel_document(filepath: str) -> Tuple[bool, str]:
    """
    Membuka file Excel (.xlsx) dengan Microsoft Excel atau spreadsheet viewer default.
    Mengembalikan (success: bool, message: str).
    """
    import subprocess

    if not filepath or not os.path.exists(filepath):
        return False, "File Excel tidak ditemukan."

    abs_path = os.path.abspath(filepath)
    opened = False

    try:
        os.startfile(abs_path)
        opened = True
    except Exception:
        try:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(abs_path))
            opened = True
        except Exception:
            try:
                subprocess.Popen(['start', '', abs_path], shell=True)
                opened = True
            except Exception as e:
                return False, f"Gagal membuka Excel secara otomatis: {str(e)}"

    return True, "File Excel berhasil dibuka."





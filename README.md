# AKP-HEIMA-BETON

Sistem Manajemen Operasional & Keuangan Batching Plant - AKP Contruction Building.

## Fitur Utama
1. **Dashboard Operasional Modern**: KPI Produksi harian/bulanan, monitoring stok material, distribusi proyek, dan armada.
2. **Master Data**: Material, Mutu Beton Standar Acuan & Resep Campuran, Proyek, dan Akun Pengguna.
3. **Manajemen Stok Material**: Penerimaan stok masuk (Semen, Pasir, Split, Air, Solar, Admixture), audit mutasi stok individual & gudang.
4. **Produksi & Pengiriman (Surat Jalan)**: Pembuatan surat jalan cetak PDF, penugasan armada mixer, driver, dan mutu beton.
5. **Keuangan & Akuntansi Plant**: 
   - Saldo Kas & Buku Kas Umum
   - Piutang Material & Pembayaran Semen
   - Piutang Proyek & Penerimaan Pembayaran Termin
   - Kas Kantor Harian
   - Penggajian Karyawan
   - Biaya Operasional Kendaraan (Servis, Sparepart, KIR, dll.)
6. **Laporan & Ekspor**: Ekspor dokumen resmi PDF & Microsoft Excel (.xlsx) dengan auto word-wrap rapi.
7. **Keamanan & Lisensi Hardware**: Hardware Lock (Machine ID) dan manajemen lisensi perangkat.

---

## Persyaratan Sistem
- Windows 10 / 11 (64-bit)
- Python 3.10+ (jika menjalankan dari source code)

## Cara Menjalankan Aplikasi (Source Code)
1. Install dependensi:
   ```bash
   pip install -r requirements.txt
   ```
2. Jalankan aplikasi:
   ```bash
   python main.py
   ```

## Cara Membuat File Executable (.exe)
Jalankan file batch:
```cmd
build.bat
```
Hasil file `.exe` dan paket `.zip` siap pakai akan otomatis berada di folder `dist/AKP Contruction Building/`.

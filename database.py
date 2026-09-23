import sqlite3
import sys
import os
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

DB_FILENAME = "akp_beton.db"

def get_secure_appdata_dir() -> str:
    """Direktori penyimpanan data tersembunyi & terproteksi di komputer client"""
    appdata = os.getenv('LOCALAPPDATA') or os.getenv('APPDATA')
    if not appdata:
        appdata = os.path.expanduser('~')
    secure_dir = os.path.join(appdata, 'AKPBetonData')
    os.makedirs(secure_dir, exist_ok=True)
    return secure_dir

def get_db_path() -> str:
    """
    Mengembalikan path file database.
    - Saat aplikasi berjalan sebagai executable di client (frozen):
      Database disimpan di direktori sistem AppData yang aman (%LOCALAPPDATA%\\AKPBetonData\\akp_storage.dat)
      dan disamarkan agar tidak dapat diakses / diedit langsung oleh pengguna dari folder aplikasi.
    - Saat mode pengembangan / unit test (non-frozen):
      Menggunakan path lokal proyek agar mudah dites dan dikembangkan.
    """
    if getattr(sys, 'frozen', False):
        secure_dir = get_secure_appdata_dir()
        target_path = os.path.join(secure_dir, "akp_storage.dat")
        
        # Inisialisasi awal jika database belum ada di AppData client
        if not os.path.exists(target_path):
            exe_dir = os.path.dirname(sys.executable)
            candidates = [
                os.path.join(exe_dir, "_internal", "akp_init.dat"),
                os.path.join(exe_dir, "akp_init.dat"),
                os.path.join(exe_dir, DB_FILENAME),
            ]
            for c in candidates:
                if os.path.exists(c):
                    try:
                        import shutil
                        shutil.copy2(c, target_path)
                        try:
                            import ctypes
                            # Set atribut file hidden di Windows (FILE_ATTRIBUTE_HIDDEN = 0x02)
                            ctypes.windll.kernel32.SetFileAttributesW(target_path, 0x02)
                        except Exception:
                            pass
                        break
                    except Exception:
                        pass
        return target_path
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, DB_FILENAME)


@contextmanager
def get_connection():
    """Context manager koneksi SQLite dengan foreign keys aktif dan auto-close"""
    conn = sqlite3.connect(get_db_path())
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def run_schema_migration(conn):
    """Menambahkan kolom dan tabel baru ke database yang sudah ada tanpa menghapus data lama"""
    cursor = conn.cursor()

    # Helper untuk cek keberadaan kolom
    def get_column_names(table_name: str) -> List[str]:
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]

    # 1. Migrasi Material
    mat_cols = get_column_names("material")
    if "harga_beli_terbaru" not in mat_cols:
        cursor.execute("ALTER TABLE material ADD COLUMN harga_beli_terbaru REAL DEFAULT 0")

    # 2. Migrasi Mutu Beton
    mutu_cols = get_column_names("mutu_beton")
    if "harga_jual_per_m3" not in mutu_cols:
        cursor.execute("ALTER TABLE mutu_beton ADD COLUMN harga_jual_per_m3 REAL DEFAULT 0")
    if "biaya_operasional_per_m3" not in mutu_cols:
        cursor.execute("ALTER TABLE mutu_beton ADD COLUMN biaya_operasional_per_m3 REAL DEFAULT 0")

    # 3. Migrasi Stok Masuk
    stok_cols = get_column_names("stok_masuk")
    if "harga_satuan" not in stok_cols:
        cursor.execute("ALTER TABLE stok_masuk ADD COLUMN harga_satuan REAL DEFAULT 0")
    if "total_biaya" not in stok_cols:
        cursor.execute("ALTER TABLE stok_masuk ADD COLUMN total_biaya REAL DEFAULT 0")
    if "pembayaran_semen_id" not in stok_cols:
        cursor.execute("ALTER TABLE stok_masuk ADD COLUMN pembayaran_semen_id INTEGER")

    # 4. Migrasi Pengiriman
    pengiriman_cols = get_column_names("pengiriman")
    if "hpp_per_m3" not in pengiriman_cols:
        cursor.execute("ALTER TABLE pengiriman ADD COLUMN hpp_per_m3 REAL DEFAULT 0")
    if "total_hpp" not in pengiriman_cols:
        cursor.execute("ALTER TABLE pengiriman ADD COLUMN total_hpp REAL DEFAULT 0")
    if "harga_jual_per_m3" not in pengiriman_cols:
        cursor.execute("ALTER TABLE pengiriman ADD COLUMN harga_jual_per_m3 REAL DEFAULT 0")
    if "total_pendapatan" not in pengiriman_cols:
        cursor.execute("ALTER TABLE pengiriman ADD COLUMN total_pendapatan REAL DEFAULT 0")
    if "margin_laba_rp" not in pengiriman_cols:
        cursor.execute("ALTER TABLE pengiriman ADD COLUMN margin_laba_rp REAL DEFAULT 0")
    if "margin_laba_persen" not in pengiriman_cols:
        cursor.execute("ALTER TABLE pengiriman ADD COLUMN margin_laba_persen REAL DEFAULT 0")
    if "hide_harga_sj" not in pengiriman_cols:
        cursor.execute("ALTER TABLE pengiriman ADD COLUMN hide_harga_sj INTEGER DEFAULT 0")
    if "status_bbm" not in pengiriman_cols:
        cursor.execute("ALTER TABLE pengiriman ADD COLUMN status_bbm TEXT DEFAULT 'Belum Diisi'")

    # 5. Migrasi Pembayaran Semen & Material
    semen_cols = get_column_names("pembayaran_semen")
    if "stok_masuk_id" not in semen_cols:
        cursor.execute("ALTER TABLE pembayaran_semen ADD COLUMN stok_masuk_id INTEGER")
    if "supplier" not in semen_cols:
        cursor.execute("ALTER TABLE pembayaran_semen ADD COLUMN supplier TEXT")
    if "kategori_piutang" not in semen_cols:
        cursor.execute("ALTER TABLE pembayaran_semen ADD COLUMN kategori_piutang TEXT DEFAULT 'kantor'")
    if "material_id" not in semen_cols:
        cursor.execute("ALTER TABLE pembayaran_semen ADD COLUMN material_id INTEGER")
    if "jatuh_tempo" not in semen_cols:
        cursor.execute("ALTER TABLE pembayaran_semen ADD COLUMN jatuh_tempo TEXT")

    stok_cols = get_column_names("stok_masuk")
    if "kategori_piutang" not in stok_cols:
        cursor.execute("ALTER TABLE stok_masuk ADD COLUMN kategori_piutang TEXT DEFAULT 'kantor'")
    if "jatuh_tempo" not in stok_cols:
        cursor.execute("ALTER TABLE stok_masuk ADD COLUMN jatuh_tempo TEXT")
    if "tanggal_datang" not in stok_cols:
        cursor.execute("ALTER TABLE stok_masuk ADD COLUMN tanggal_datang TEXT")
        cursor.execute("""
            UPDATE stok_masuk 
            SET tanggal_datang = (SELECT tanggal_datang FROM pembayaran_semen WHERE pembayaran_semen.id = stok_masuk.pembayaran_semen_id)
            WHERE tanggal_datang IS NULL AND pembayaran_semen_id IS NOT NULL
        """)

    # 6. Migrasi Saldo Kas
    kas_cols = get_column_names("saldo_kas")
    if "referensi_tipe" not in kas_cols:
        cursor.execute("ALTER TABLE saldo_kas ADD COLUMN referensi_tipe TEXT")
    if "referensi_id" not in kas_cols:
        cursor.execute("ALTER TABLE saldo_kas ADD COLUMN referensi_id INTEGER")

    # 11. Migrasi Tipe Proyek (Proyek Dalam / Proyek Luar)
    proyek_cols = get_column_names("proyek")
    if "tipe_proyek" not in proyek_cols:
        cursor.execute("ALTER TABLE proyek ADD COLUMN tipe_proyek TEXT DEFAULT 'luar'")

    # 12. Migrasi Tabel Kendaraan & Armada Operasional
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS kendaraan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        no_plat TEXT UNIQUE NOT NULL,
        nama_kendaraan TEXT,
        jenis_kendaraan TEXT NOT NULL DEFAULT 'Truk Mixer',
        kapasitas_m3 REAL DEFAULT 0,
        driver_default TEXT,
        status TEXT DEFAULT 'tersedia',
        keterangan_operasional TEXT,
        catatan TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_kendaraan_plat ON kendaraan(no_plat)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_kendaraan_status ON kendaraan(status)")

    # 13. Migrasi Kolom kendaraan_id, driver, proyek_id di kas_kantor
    kas_kantor_cols = get_column_names("kas_kantor")
    if "kendaraan_id" not in kas_kantor_cols:
        cursor.execute("ALTER TABLE kas_kantor ADD COLUMN kendaraan_id INTEGER REFERENCES kendaraan(id)")
    if "driver" not in kas_kantor_cols:
        cursor.execute("ALTER TABLE kas_kantor ADD COLUMN driver TEXT")
    if "proyek_id" not in kas_kantor_cols:
        cursor.execute("ALTER TABLE kas_kantor ADD COLUMN proyek_id INTEGER REFERENCES proyek(id)")
    if "pengiriman_id" not in kas_kantor_cols:
        cursor.execute("ALTER TABLE kas_kantor ADD COLUMN pengiriman_id INTEGER REFERENCES pengiriman(id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_kas_kantor_kendaraan ON kas_kantor(kendaraan_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_kas_kantor_proyek ON kas_kantor(proyek_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_kas_kantor_pengiriman ON kas_kantor(pengiriman_id)")

    # Backfill driver di data kas_kantor yang sudah ada dari kendaraan.driver_default jika masih kosong
    cursor.execute("""
    UPDATE kas_kantor 
    SET driver = (
        SELECT k.driver_default FROM kendaraan k WHERE k.id = kas_kantor.kendaraan_id LIMIT 1
    )
    WHERE (driver IS NULL OR TRIM(driver) = '') AND kendaraan_id IS NOT NULL
    """)

    # 14. Migrasi Kolom kendaraan_id di pengiriman
    pengiriman_cols = get_column_names("pengiriman")
    if "kendaraan_id" not in pengiriman_cols:
        cursor.execute("ALTER TABLE pengiriman ADD COLUMN kendaraan_id INTEGER REFERENCES kendaraan(id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pengiriman_kendaraan ON pengiriman(kendaraan_id)")

    # Backfill kendaraan_id di data pengiriman yang sudah ada berdasarkan no_plat_truk
    cursor.execute("""
    UPDATE pengiriman 
    SET kendaraan_id = (
        SELECT k.id FROM kendaraan k WHERE UPPER(k.no_plat) = UPPER(pengiriman.no_plat_truk) LIMIT 1
    )
    WHERE kendaraan_id IS NULL AND no_plat_truk IS NOT NULL AND TRIM(no_plat_truk) != ''
    """)

    # 7. Sinkronisasi Data Lama Tagihan Proyek ke Proyek Piutang & Pembayaran jika tabel baru masih kosong
    cursor.execute("SELECT COUNT(*) FROM proyek_piutang")
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT COUNT(*) FROM tagihan_proyek")
        if cursor.fetchone()[0] > 0:
            cursor.execute("SELECT * FROM tagihan_proyek ORDER BY tanggal ASC, id ASC")
            old_tags = cursor.fetchall()
            for row in old_tags:
                p_id = row["proyek_id"]
                tgl = row["tanggal"]
                t_masuk = float(row["tagihan_masuk"] or 0)
                p_bayar = float(row["pembayaran_material"] or 0)
                ket = row["keterangan"] or ""

                if t_masuk > 0:
                    cursor.execute("""
                    INSERT INTO proyek_piutang (proyek_id, tanggal, total_tagihan, keterangan)
                    VALUES (?, ?, ?, ?)
                    """, (p_id, tgl, t_masuk, ket if ket else "Tagihan Proyek (Migrasi)"))
                if p_bayar > 0:
                    cursor.execute("""
                    INSERT INTO proyek_pembayaran (proyek_id, tanggal, nominal, keterangan)
                    VALUES (?, ?, ?, ?)
                    """, (p_id, tgl, p_bayar, ket if ket else "Pembayaran Proyek (Migrasi)"))

    # 8. Sinkronisasi Pengiriman Lama yang belum ada HPP / Harga Jual
    cursor.execute("SELECT id, mutu_beton_id, volume_m3, proyek_id, tanggal FROM pengiriman WHERE total_pendapatan = 0 OR total_pendapatan IS NULL")
    old_shipments = cursor.fetchall()
    for sh in old_shipments:
        p_id = sh["id"]
        m_id = sh["mutu_beton_id"]
        vol = float(sh["volume_m3"] or 1.0)
        pr_id = sh["proyek_id"]
        tgl = sh["tanggal"]

        cursor.execute("SELECT kode, harga_jual_per_m3, biaya_operasional_per_m3 FROM mutu_beton WHERE id = ?", (m_id,))
        m_row = cursor.fetchone()
        if m_row:
            h_jual = float(m_row["harga_jual_per_m3"] or 850000.0)
            b_ops = float(m_row["biaya_operasional_per_m3"] or 30000.0)
            
            # Hitung HPP dari resep
            cursor.execute("""
            SELECT r.jumlah_per_m3, m.harga_beli_terbaru
            FROM mutu_beton_resep r
            JOIN material m ON r.material_id = m.id
            WHERE r.mutu_beton_id = ?
            """, (m_id,))
            resep_rows = cursor.fetchall()
            hpp_unit = b_ops
            for rr in resep_rows:
                hpp_unit += (float(rr["jumlah_per_m3"] or 0) * float(rr["harga_beli_terbaru"] or 0))
            if hpp_unit <= b_ops:
                hpp_unit = 700000.0 # Fallback wajar jika harga material belum terset

            tot_hpp = hpp_unit * vol
            tot_pendapatan = h_jual * vol
            laba_rp = tot_pendapatan - tot_hpp
            laba_pct = (laba_rp / tot_pendapatan * 100.0) if tot_pendapatan > 0 else 0.0

            cursor.execute("""
            UPDATE pengiriman 
            SET hpp_per_m3 = ?, total_hpp = ?, harga_jual_per_m3 = ?, total_pendapatan = ?, margin_laba_rp = ?, margin_laba_persen = ?
            WHERE id = ?
            """, (hpp_unit, tot_hpp, h_jual, tot_pendapatan, laba_rp, laba_pct, p_id))

            # Buat entri piutang jika belum ada
            cursor.execute("SELECT COUNT(*) FROM proyek_piutang WHERE pengiriman_id = ?", (p_id,))
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                INSERT INTO proyek_piutang (proyek_id, pengiriman_id, tanggal, mutu_beton_kode, volume_m3, harga_satuan_m3, total_tagihan, keterangan)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (pr_id, p_id, tgl, m_row["kode"], vol, h_jual, tot_pendapatan, f"Pengiriman Beton {m_row['kode']} ({vol} m³)"))

    # 9. Migrasi Tabel Users & Inisialisasi Akun Admin
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nama_lengkap TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        last_login TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    
    # Pastikan default user admin dibuat jika tabel masih kosong
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', 'admin123'.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
        stored_hash = f"{salt}${pwd_hash}"
        cursor.execute("""
        INSERT INTO users (username, password_hash, nama_lengkap, is_active)
        VALUES (?, ?, ?, 1)
        """, ('admin', stored_hash, 'Administrator AKP'))

    # Migrasi kolom role di tabel users jika belum ada
    cursor.execute("PRAGMA table_info(users)")
    u_cols = [col[1] for col in cursor.fetchall()]
    if "role" not in u_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'Operator'")
        cursor.execute("UPDATE users SET role = 'Administrator' WHERE username = 'admin'")

    # Seed akun awal sesuai standar sistem jika akun masih sangat sedikit (<= 2)
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] <= 2:
        seed_users = [
            ("operator1", "Budi Santoso", "Operator", 1, "2026-09-19 14:21:00"),
            ("operator2", "Andi Pratama", "Operator", 0, "2026-09-12 09:10:00"),
            ("gudang", "Siti Nurhayati", "Gudang", 1, "2026-09-18 16:40:00"),
            ("keuangan", "Rizky Alif", "Keuangan", 1, "2026-09-17 11:03:00"),
            ("produksi", "Dodi Kurniawan", "Produksi", 1, "2026-09-16 13:55:00")
        ]
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', '123456'.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
        std_hash = f"{salt}${pwd_hash}"
        for s_u, s_nama, s_role, s_act, s_last in seed_users:
            cursor.execute("SELECT id FROM users WHERE username = ?", (s_u,))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO users (username, password_hash, nama_lengkap, role, is_active, last_login)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (s_u, std_hash, s_nama, s_role, s_act, s_last))

    # 10. Migrasi Tabel Individual Stok Per User
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_material_stok (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        material_id INTEGER NOT NULL,
        stok_saat_ini REAL DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (material_id) REFERENCES material(id) ON DELETE CASCADE,
        UNIQUE (user_id, material_id)
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ums_user ON user_material_stok(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ums_material ON user_material_stok(material_id)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_stok_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        material_id INTEGER NOT NULL,
        tipe TEXT NOT NULL,
        jumlah REAL NOT NULL,
        referensi_id INTEGER,
        keterangan TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_usl_user ON user_stok_log(user_id)")

    # Inisialisasi user_material_stok untuk semua user & material yang sudah ada (jika tabel baru saja dibuat)
    cursor.execute("SELECT id FROM users WHERE is_active = 1")
    all_users = cursor.fetchall()
    cursor.execute("SELECT id, stok_saat_ini FROM material")
    all_mats = cursor.fetchall()
    for u in all_users:
        for m in all_mats:
            cursor.execute("""
            INSERT OR IGNORE INTO user_material_stok (user_id, material_id, stok_saat_ini)
            VALUES (?, ?, ?)
            """, (u["id"], m["id"], float(m["stok_saat_ini"] or 0)))

    conn.commit()


def init_db():
    """Inisialisasi semua tabel database jika belum ada"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Tabel Material
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS material (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode TEXT UNIQUE,
            nama TEXT NOT NULL,
            satuan TEXT NOT NULL,
            stok_saat_ini REAL DEFAULT 0,
            stok_minimum REAL DEFAULT 0,
            harga_beli_terbaru REAL DEFAULT 0,
            keterangan TEXT
        )
        """)

        # 2. Tabel Histori Harga Beli Material
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS material_harga_histori (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER NOT NULL,
            tanggal TEXT NOT NULL,
            harga_beli REAL NOT NULL,
            keterangan TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (material_id) REFERENCES material(id) ON DELETE CASCADE
        )
        """)

        # 3. Tabel Proyek
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS proyek (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL UNIQUE,
            lokasi TEXT,
            status TEXT DEFAULT 'aktif', -- 'aktif' atau 'selesai'
            keterangan TEXT
        )
        """)

        # 4. Tabel Mutu Beton
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS mutu_beton (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode TEXT NOT NULL UNIQUE,
            nama TEXT,
            harga_jual_per_m3 REAL DEFAULT 0,
            biaya_operasional_per_m3 REAL DEFAULT 0,
            keterangan TEXT
        )
        """)

        # 5. Tabel Resep Mutu Beton (Many-to-Many: Mutu Beton x Material)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS mutu_beton_resep (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mutu_beton_id INTEGER NOT NULL,
            material_id INTEGER NOT NULL,
            jumlah_per_m3 REAL NOT NULL,
            FOREIGN KEY (mutu_beton_id) REFERENCES mutu_beton(id) ON DELETE CASCADE,
            FOREIGN KEY (material_id) REFERENCES material(id) ON DELETE RESTRICT,
            UNIQUE (mutu_beton_id, material_id)
        )
        """)

        # 6. Tabel Pembayaran / Hutang Semen Supplier
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pembayaran_semen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stok_masuk_id INTEGER,
            no_order TEXT,
            supplier TEXT,
            tanggal_order TEXT,
            tanggal_datang TEXT,
            jatuh_tempo TEXT,
            jumlah_ton REAL NOT NULL,
            harga_per_ton REAL NOT NULL,
            total_harga REAL NOT NULL,
            keterangan TEXT,
            kategori_piutang TEXT DEFAULT 'kantor',
            material_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 7. Tabel Cicilan / Pembayaran Semen ke Supplier
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pembayaran_semen_cicilan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pembayaran_semen_id INTEGER,
            tanggal TEXT NOT NULL,
            nominal REAL NOT NULL,
            metode TEXT DEFAULT 'Transfer',
            keterangan TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pembayaran_semen_id) REFERENCES pembayaran_semen(id) ON DELETE SET NULL
        )
        """)

        # 8. Tabel Stok Masuk
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stok_masuk (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER NOT NULL,
            tanggal TEXT NOT NULL,
            jumlah REAL NOT NULL,
            no_plat TEXT,
            supplier TEXT,
            harga_satuan REAL DEFAULT 0,
            total_biaya REAL DEFAULT 0,
            pembayaran_semen_id INTEGER,
            keterangan TEXT,
            kategori_piutang TEXT DEFAULT 'kantor',
            jatuh_tempo TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (material_id) REFERENCES material(id) ON DELETE RESTRICT,
            FOREIGN KEY (pembayaran_semen_id) REFERENCES pembayaran_semen(id) ON DELETE SET NULL
        )
        """)

        # 9. Tabel Pengiriman (Produksi & Delivery)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pengiriman (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            no_surat_jalan TEXT,
            tanggal TEXT NOT NULL,
            mutu_beton_id INTEGER NOT NULL,
            volume_m3 REAL NOT NULL,
            proyek_id INTEGER NOT NULL,
            tujuan_pengiriman TEXT,
            no_plat_truk TEXT,
            driver TEXT,
            hpp_per_m3 REAL DEFAULT 0,
            total_hpp REAL DEFAULT 0,
            harga_jual_per_m3 REAL DEFAULT 0,
            total_pendapatan REAL DEFAULT 0,
            margin_laba_rp REAL DEFAULT 0,
            margin_laba_persen REAL DEFAULT 0,
            catatan TEXT,
            hide_harga_sj INTEGER DEFAULT 0,
            kendaraan_id INTEGER,
            status_bbm TEXT DEFAULT 'Belum Diisi',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mutu_beton_id) REFERENCES mutu_beton(id) ON DELETE RESTRICT,
            FOREIGN KEY (proyek_id) REFERENCES proyek(id) ON DELETE RESTRICT,
            FOREIGN KEY (kendaraan_id) REFERENCES kendaraan(id) ON DELETE SET NULL
        )
        """)

        # 10. Tabel Detail Pengiriman (Material terpakai dari Resep x Volume)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pengiriman_detail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pengiriman_id INTEGER NOT NULL,
            material_id INTEGER NOT NULL,
            jumlah_terpakai REAL NOT NULL,
            FOREIGN KEY (pengiriman_id) REFERENCES pengiriman(id) ON DELETE CASCADE,
            FOREIGN KEY (material_id) REFERENCES material(id) ON DELETE RESTRICT
        )
        """)

        # 11. Tabel Tagihan / Piutang Proyek Terintegrasi
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS proyek_piutang (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proyek_id INTEGER NOT NULL,
            pengiriman_id INTEGER,
            tanggal TEXT NOT NULL,
            no_surat_jalan TEXT,
            mutu_beton_kode TEXT,
            volume_m3 REAL DEFAULT 0,
            harga_satuan_m3 REAL DEFAULT 0,
            total_tagihan REAL NOT NULL,
            keterangan TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (proyek_id) REFERENCES proyek(id) ON DELETE CASCADE,
            FOREIGN KEY (pengiriman_id) REFERENCES pengiriman(id) ON DELETE SET NULL
        )
        """)

        # 12. Tabel Pembayaran / Termin Masuk dari Proyek Klien
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS proyek_pembayaran (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proyek_id INTEGER NOT NULL,
            tanggal TEXT NOT NULL,
            nominal REAL NOT NULL,
            metode TEXT DEFAULT 'Transfer Bank',
            nomor_bukti TEXT,
            keterangan TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (proyek_id) REFERENCES proyek(id) ON DELETE CASCADE
        )
        """)

        # 13. Tabel Tagihan Proyek Lama (Backward compatibility)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tagihan_proyek (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proyek_id INTEGER NOT NULL,
            tanggal TEXT NOT NULL,
            tagihan_masuk REAL DEFAULT 0,
            pembayaran_material REAL DEFAULT 0,
            saldo_akhir REAL DEFAULT 0,
            keterangan TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (proyek_id) REFERENCES proyek(id) ON DELETE RESTRICT
        )
        """)

        # 14. Tabel Kas Kantor (Pengeluaran Harian Non-Semen)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS kas_kantor (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal TEXT NOT NULL,
            nomor_nota TEXT,
            kategori TEXT NOT NULL,
            nominal REAL NOT NULL,
            penerima_toko TEXT,
            keterangan TEXT,
            lampiran_foto TEXT,
            kendaraan_id INTEGER,
            proyek_id INTEGER,
            pengiriman_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kendaraan_id) REFERENCES kendaraan(id) ON DELETE SET NULL,
            FOREIGN KEY (proyek_id) REFERENCES proyek(id) ON DELETE SET NULL,
            FOREIGN KEY (pengiriman_id) REFERENCES pengiriman(id) ON DELETE SET NULL
        )
        """)

        # 15. Tabel Gaji Karyawan
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS gaji_karyawan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal_bayar TEXT NOT NULL,
            periode_gaji TEXT NOT NULL,
            nama_karyawan TEXT NOT NULL,
            jabatan TEXT,
            nominal_gaji REAL NOT NULL,
            potongan_tunjangan REAL DEFAULT 0,
            total_dibayar REAL NOT NULL,
            metode_bayar TEXT DEFAULT 'Tunai',
            keterangan TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 16. Tabel Saldo Kas Batching Plant Terpadu
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS saldo_kas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal TEXT NOT NULL,
            keterangan TEXT,
            saldo_masuk REAL DEFAULT 0,
            saldo_keluar REAL DEFAULT 0,
            total_saldo REAL DEFAULT 0,
            kategori TEXT DEFAULT 'Operasional',
            referensi_tipe TEXT,
            referensi_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 17. Tabel Pengaturan / Profil
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pengaturan (
            kunci TEXT PRIMARY KEY,
            nilai TEXT
        )
        """)

        # 18. Tabel Individual Stok Per User
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_material_stok (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            material_id INTEGER NOT NULL,
            stok_saat_ini REAL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (material_id) REFERENCES material(id) ON DELETE CASCADE,
            UNIQUE (user_id, material_id)
        )
        """)

        # 19. Tabel Log Mutasi Stok Individual Per User (Audit Trail)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_stok_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            material_id INTEGER NOT NULL,
            tipe TEXT NOT NULL,
            jumlah REAL NOT NULL,
            referensi_id INTEGER,
            keterangan TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 20. Tabel Kendaraan & Armada Operasional
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS kendaraan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            no_plat TEXT UNIQUE NOT NULL,
            nama_kendaraan TEXT,
            jenis_kendaraan TEXT NOT NULL DEFAULT 'Truk Mixer',
            kapasitas_m3 REAL DEFAULT 0,
            driver_default TEXT,
            status TEXT DEFAULT 'tersedia',
            keterangan_operasional TEXT,
            catatan TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Indexing untuk kecepatan pencarian
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pengiriman_tgl ON pengiriman(tanggal)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pengiriman_proyek ON pengiriman(proyek_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stok_masuk_tgl ON stok_masuk(tanggal)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_saldo_kas_tgl ON saldo_kas(tanggal)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_proyek_piutang_pr ON proyek_piutang(proyek_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_proyek_bayar_pr ON proyek_pembayaran(proyek_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kas_kantor_tgl ON kas_kantor(tanggal)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gaji_tgl ON gaji_karyawan(tanggal_bayar)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ums_user ON user_material_stok(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ums_material ON user_material_stok(material_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usl_user ON user_stok_log(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kendaraan_plat ON kendaraan(no_plat)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kendaraan_status ON kendaraan(status)")

        conn.commit()

        # Jalankan schema migration untuk database yang sudah ada
        run_schema_migration(conn)

    # Seed data default dan sinkronkan kode beton standar acuan
    seed_default_data()
    sinkronkan_kode_beton_standar()


# ==============================================================================
# TABEL KODE MUTU BETON STANDAR ACUAN (K-100 s.d K-400 & MORTAR)
# ==============================================================================
TABEL_KODE_BETON_STANDAR = {
    "K-100": {
        "nama": "Beton K-100 (fc' 7.4 MPa)",
        "keterangan": "Lantai kerja, rabat beton non-struktural",
        "harga_jual": 720000.0,
        "biaya_ops": 30000.0,
        "urutan": 1,
        "resep": {
            "Semen": 160.0,
            "Pasir": 893.0,
            "Split 1.2": 1027.0,
            "Air": 200.0,
        }
    },
    "K-175": {
        "nama": "Beton K-175 (fc' 14.5 MPa)",
        "keterangan": "Konstruksi ringan, jalan lingkungan, rabat beton",
        "harga_jual": 780000.0,
        "biaya_ops": 30000.0,
        "urutan": 2,
        "resep": {
            "Semen": 266.0,
            "Pasir": 760.0,
            "Split 1.2": 1029.0,
            "Air": 215.0,
        }
    },
    "K-200": {
        "nama": "Beton K-200 (fc' 16.9 MPa)",
        "keterangan": "Konstruksi ringan s.d sedang, jalan desa, plat lantai",
        "harga_jual": 800000.0,
        "biaya_ops": 30000.0,
        "urutan": 3,
        "resep": {
            "Semen": 292.0,
            "Pasir": 731.0,
            "Split 1.2": 1031.0,
            "Air": 215.0,
        }
    },
    "K-225": {
        "nama": "Beton K-225 (fc' 19.3 MPa)",
        "keterangan": "Struktural rumah bertingkat, kolom praktis, plat lantai",
        "harga_jual": 830000.0,
        "biaya_ops": 30000.0,
        "urutan": 4,
        "resep": {
            "Semen": 311.0,
            "Pasir": 698.0,
            "Split 1.2": 1047.0,
            "Air": 215.0,
        }
    },
    "K-250": {
        "nama": "Beton K-250 (fc' 21.4 MPa)",
        "keterangan": "Struktur standar SNI gedung & balok, jalan beton cor",
        "harga_jual": 860000.0,
        "biaya_ops": 30000.0,
        "urutan": 5,
        "resep": {
            "Semen": 360.0,
            "Pasir": 674.0,
            "Split 1.2": 1023.0,
            "Air": 215.0,
        }
    },
    "K-275": {
        "nama": "Beton K-275 (fc' 23.5 MPa)",
        "keterangan": "Struktur beban sedang-berat, jalan beton provinsi",
        "harga_jual": 890000.0,
        "biaya_ops": 30000.0,
        "urutan": 6,
        "resep": {
            "Semen": 371.0,
            "Pasir": 667.0,
            "Split 1.2": 1012.0,
            "Air": 215.0,
        }
    },
    "K-300": {
        "nama": "Beton K-300 (fc' 25.6 MPa)",
        "keterangan": "Konstruksi jembatan, jalan raya utama, lantai gudang heavy duty",
        "harga_jual": 930000.0,
        "biaya_ops": 30000.0,
        "urutan": 7,
        "resep": {
            "Semen": 381.0,
            "Pasir": 659.0,
            "Split 1.2": 1001.0,
            "Air": 215.0,
        }
    },
    "K-350": {
        "nama": "Beton K-350 (fc' 29.8 MPa)",
        "keterangan": "Pondasi tiang pancang, gelagar jembatan, bendungan",
        "harga_jual": 990000.0,
        "biaya_ops": 30000.0,
        "urutan": 8,
        "resep": {
            "Semen": 395.0,
            "Pasir": 650.0,
            "Split 1.2": 995.0,
            "Air": 215.0,
        }
    },
    "K-400": {
        "nama": "Beton K-400",
        "keterangan": "Struktur mutu tinggi khusus / precast heavy duty",
        "harga_jual": 1050000.0,
        "biaya_ops": 30000.0,
        "urutan": 9,
        "resep": {
            "Semen": 400.0,
            "Pasir": 645.0,
            "Split 1.2": 990.0,
            "Air": 215.0,
        }
    },
    "mortar": {
        "nama": "Mortar / Semen Pasir",
        "keterangan": "Campuran standar mortar pengikat",
        "harga_jual": 650000.0,
        "biaya_ops": 25000.0,
        "urutan": 10,
        "resep": {
            "Semen": 125.0,
            "Pasir": 1150.0,
            "Air": 200.0,
        }
    }
}

def get_tabel_kode_beton_standar() -> Dict[str, Any]:
    """Mengembalikan data master tabel kode beton standar acuan"""
    return TABEL_KODE_BETON_STANDAR

def sinkronkan_kode_beton_standar(force: bool = False) -> Tuple[int, int]:
    """
    Sinkronisasi database dengan Tabel Kode Beton Standar Acuan (K-100 s.d K-400 & mortar).
    Membuat atau memperbarui mutu beton beserta takaran resep per 1 m3 untuk Semen, Pasir, Split 1.2, dan Air.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Pastikan seluruh material standar sudah terdaftar beserta harga beli awal wajar
        default_materials = [
            ("MAT-SMN", "Semen", "kg", 0, 5000, 1150.0, "Semen Portland / PCC"),
            ("MAT-PSR", "Pasir", "kg", 0, 10000, 150.0, "Pasir cor"),
            ("MAT-SP12", "Split 1.2", "kg", 0, 10000, 160.0, "Agregat kasar ukuran 10-20mm"),
            ("MAT-SP11", "Split 1.1", "kg", 0, 5000, 170.0, "Agregat kasar ukuran 5-10mm"),
            ("MAT-SLR", "Solar", "liter", 0, 500, 14500.0, "Bahan bakar operasional genset/loader"),
            ("MAT-AIR", "Air", "liter", 0, 0, 10.0, "Air campuran beton"),
            ("MAT-ADMIX", "Admixture", "liter", 0, 50, 22000.0, "Cairan aditif pengeras / retarder")
        ]
        for kode, nama, satuan, stok_awal, stok_min, hrg_beli, ket in default_materials:
            cursor.execute("SELECT id, harga_beli_terbaru FROM material WHERE nama = ? OR kode = ?", (nama, kode))
            row = cursor.fetchone()
            if not row:
                cursor.execute("""
                INSERT INTO material (kode, nama, satuan, stok_saat_ini, stok_minimum, harga_beli_terbaru, keterangan)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (kode, nama, satuan, stok_awal, stok_min, hrg_beli, ket))
                mat_id = cursor.lastrowid
                # Tambah ke histori
                cursor.execute("""
                INSERT INTO material_harga_histori (material_id, tanggal, harga_beli, keterangan)
                VALUES (?, ?, ?, ?)
                """, (mat_id, datetime.now().strftime("%Y-%m-%d"), hrg_beli, "Harga Standar Awal"))
            elif row["harga_beli_terbaru"] is None or row["harga_beli_terbaru"] <= 0:
                cursor.execute("UPDATE material SET harga_beli_terbaru = ? WHERE id = ?", (hrg_beli, row["id"]))

        # 2. Ambil peta ID material
        cursor.execute("SELECT id, nama FROM material")
        mat_map = {row["nama"]: row["id"] for row in cursor.fetchall()}
        
        mutu_count = 0
        resep_count = 0

        # 3. Sinkronkan Mutu Beton & Resep
        for kode, data in TABEL_KODE_BETON_STANDAR.items():
            cursor.execute("SELECT id, harga_jual_per_m3 FROM mutu_beton WHERE kode = ?", (kode,))
            row = cursor.fetchone()
            if row:
                mutu_id = row["id"]
                # Pertahankan harga jual kustom jika sudah ada
                h_jual = row["harga_jual_per_m3"] if (row["harga_jual_per_m3"] and row["harga_jual_per_m3"] > 0) else data["harga_jual"]
                cursor.execute("""
                UPDATE mutu_beton 
                SET nama = ?, keterangan = ?, harga_jual_per_m3 = ?, biaya_operasional_per_m3 = ? 
                WHERE id = ?
                """, (data["nama"], data["keterangan"], h_jual, data["biaya_ops"], mutu_id))
            else:
                cursor.execute("""
                INSERT INTO mutu_beton (kode, nama, keterangan, harga_jual_per_m3, biaya_operasional_per_m3) 
                VALUES (?, ?, ?, ?, ?)
                """, (kode, data["nama"], data["keterangan"], data["harga_jual"], data["biaya_ops"]))
                mutu_id = cursor.lastrowid
            
            mutu_count += 1

            # Update atau refresh resep standar jika resep kosong
            cursor.execute("SELECT COUNT(*) FROM mutu_beton_resep WHERE mutu_beton_id = ?", (mutu_id,))
            if cursor.fetchone()[0] == 0 or force:
                cursor.execute("DELETE FROM mutu_beton_resep WHERE mutu_beton_id = ?", (mutu_id,))
                for mat_nama, qty in data["resep"].items():
                    if mat_nama in mat_map:
                        mat_id = mat_map[mat_nama]
                        cursor.execute("""
                        INSERT INTO mutu_beton_resep (mutu_beton_id, material_id, jumlah_per_m3)
                        VALUES (?, ?, ?)
                        """, (mutu_id, mat_id, float(qty)))
                        resep_count += 1

        conn.commit()
        return mutu_count, resep_count

def hitung_komposisi_beton(kode_mutu: str, volume_m3: float) -> Dict[str, Any]:
    """
    Menghitung komposisi campuran beton secara proporsional berdasarkan Tabel Kode Beton Acuan.
    Formula: Kebutuhan Material = Resep Dasar per 1 m3 x Volume
    """
    if volume_m3 <= 0:
        raise ValueError("Volume beton harus lebih besar dari 0.")

    if kode_mutu in TABEL_KODE_BETON_STANDAR:
        base = TABEL_KODE_BETON_STANDAR[kode_mutu]
        mat_calc = {}
        for mat_name, base_qty in base["resep"].items():
            mat_calc[mat_name] = round(base_qty * volume_m3, 2)
            
        return {
            "kode": kode_mutu,
            "nama": base["nama"],
            "volume_m3": volume_m3,
            "material": mat_calc
        }
    else:
        # Fallback cari mutu beton kustom di database
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, kode, nama FROM mutu_beton WHERE kode = ?", (kode_mutu,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Mutu beton '{kode_mutu}' tidak ditemukan dalam sistem.")
            mutu_id = row["id"]
            preview = preview_kebutuhan_material(mutu_id, volume_m3)
            return {
                "kode": kode_mutu,
                "nama": row["nama"],
                "volume_m3": volume_m3,
                "material": {item["material_nama"]: round(item["kebutuhan"], 2) for item in preview}
            }

def seed_default_data():
    """Mengisi data awal standar proyek dan pengaturan jika database baru dibuat"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Cek apakah proyek sudah ada
        cursor.execute("SELECT COUNT(*) FROM proyek")
        if cursor.fetchone()[0] == 0:
            default_proyek = [
                ("Proyek Pelebaran Jembatan", "Jembatan", "aktif", "Pekerjaan pelebaran jembatan utama"),
                ("Proyek Pelebaran Windusari", "Windusari", "aktif", "Pekerjaan jalan & saluran Windusari"),
                ("Proyek Pelebaran Puring", "Puring", "aktif", "Pelebaran jalan area Puring"),
                ("Proyek Pelebaran Polres", "Polres", "aktif", "Pembangunan & pengecoran area Polres")
            ]
            cursor.executemany("""
            INSERT INTO proyek (nama, lokasi, status, keterangan)
            VALUES (?, ?, ?, ?)
            """, default_proyek)

        # Inisialisasi Pengaturan Aplikasi
        default_settings = [
            ("nama_perusahaan", "AKP BATCHING PLANT"),
            ("alamat_perusahaan", "Jl. Raya Batching Plant AKP, Jawa Tengah"),
            ("telepon_perusahaan", "0812-3456-7890"),
            ("pj_lapangan", "Operator / Penanggung Jawab Batching Plant")
        ]
        cursor.executemany("""
        INSERT OR IGNORE INTO pengaturan (kunci, nilai) VALUES (?, ?)
        """, default_settings)

        # Inisialisasi Armada Kendaraan Default
        cursor.execute("SELECT COUNT(*) FROM kendaraan")
        if cursor.fetchone()[0] == 0:
            default_kendaraan = [
                ("AA 8456 CB", "Truk Mixer TM-01", "Truk Mixer", 7.0, "Slamet Riyadi", "tersedia", "", "Kapasitas 7 m³ Hino 500"),
                ("AA 8990 BB", "Truk Mixer TM-02", "Truk Mixer", 7.0, "Joko Susilo", "tersedia", "", "Kapasitas 7 m³ Isuzu Giga"),
                ("AA 8123 AB", "Dump Truck DT-01", "Dump Truck", 10.0, "Supriyanto", "tersedia", "", "Dump truck pengangkut agregat pasir & split"),
                ("AA 9012 CB", "Wheel Loader L-01", "Wheel Loader", 1.8, "Agus Prasetyo", "tersedia", "", "Alat muat pasir & split ke batching plant")
            ]
            cursor.executemany("""
            INSERT INTO kendaraan (no_plat, nama_kendaraan, jenis_kendaraan, kapasitas_m3, driver_default, status, keterangan_operasional, catatan)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, default_kendaraan)

        conn.commit()


# ==============================================================================
# MATERIAL & HARGA CRUD & SERVICES
# ==============================================================================

def get_all_materials() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM material ORDER BY nama ASC")
        return [dict(row) for row in cursor.fetchall()]

def get_material_by_id(mat_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM material WHERE id = ?", (mat_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def save_material(kode: str, nama: str, satuan: str, stok_minimum: float = 0, 
                  harga_beli_terbaru: float = 0, keterangan: str = "", mat_id: Optional[int] = None,
                  stok_awal: float = 0.0) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        if mat_id:
            cursor.execute("SELECT harga_beli_terbaru, stok_saat_ini FROM material WHERE id = ?", (mat_id,))
            old_row = cursor.fetchone()
            old_price = float(old_row["harga_beli_terbaru"] or 0) if old_row else 0.0

            cursor.execute("""
            UPDATE material 
            SET kode = ?, nama = ?, satuan = ?, stok_saat_ini = ?, stok_minimum = ?, harga_beli_terbaru = ?, keterangan = ?
            WHERE id = ?
            """, (kode.strip(), nama.strip(), satuan.strip(), stok_awal, stok_minimum, harga_beli_terbaru, keterangan.strip(), mat_id))
            
            # Jika harga berubah, simpan ke histori
            if abs(old_price - harga_beli_terbaru) > 0.001 and harga_beli_terbaru > 0:
                cursor.execute("""
                INSERT INTO material_harga_histori (material_id, tanggal, harga_beli, keterangan)
                VALUES (?, ?, ?, ?)
                """, (mat_id, today, harga_beli_terbaru, "Penyesuaian di Master Data Material"))

            conn.commit()
            return mat_id
        else:
            cursor.execute("""
            INSERT INTO material (kode, nama, satuan, stok_saat_ini, stok_minimum, harga_beli_terbaru, keterangan)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (kode.strip(), nama.strip(), satuan.strip(), stok_awal, stok_minimum, harga_beli_terbaru, keterangan.strip()))
            new_id = cursor.lastrowid
            
            if harga_beli_terbaru > 0:
                cursor.execute("""
                INSERT INTO material_harga_histori (material_id, tanggal, harga_beli, keterangan)
                VALUES (?, ?, ?, ?)
                """, (new_id, today, harga_beli_terbaru, "Harga Awal Material"))

            # Jika ada stok awal > 0, catat juga ke stok_masuk sebagai Saldo Awal agar terlacak di mutasi stok
            if stok_awal > 0:
                tot_biaya = stok_awal * harga_beli_terbaru
                cursor.execute("""
                INSERT INTO stok_masuk (material_id, tanggal, jumlah, supplier, harga_satuan, total_biaya, keterangan)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (new_id, today, stok_awal, "Saldo Awal", harga_beli_terbaru, tot_biaya, "Stok Awal Master Material"))

            # Inisialisasi user_material_stok untuk semua user aktif
            cursor.execute("SELECT id FROM users WHERE is_active = 1")
            all_users = cursor.fetchall()
            for u in all_users:
                cursor.execute("""
                INSERT OR IGNORE INTO user_material_stok (user_id, material_id, stok_saat_ini)
                VALUES (?, ?, ?)
                """, (u["id"], new_id, stok_awal))

            conn.commit()
            return new_id

def delete_material(mat_id: int) -> Tuple[bool, str]:
    """Hapus material jika belum terpakai di resep, stok, atau pengiriman"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM mutu_beton_resep WHERE material_id = ?", (mat_id,))
        if cursor.fetchone()[0] > 0:
            return False, "Material tidak dapat dihapus karena terdaftar dalam Resep Mutu Beton."
        cursor.execute("SELECT COUNT(*) FROM stok_masuk WHERE material_id = ?", (mat_id,))
        if cursor.fetchone()[0] > 0:
            return False, "Material tidak dapat dihapus karena memiliki riwayat stok masuk."
        cursor.execute("SELECT COUNT(*) FROM pengiriman_detail WHERE material_id = ?", (mat_id,))
        if cursor.fetchone()[0] > 0:
            return False, "Material tidak dapat dihapus karena memiliki riwayat pengiriman cor."
        
        cursor.execute("DELETE FROM material WHERE id = ?", (mat_id,))
        conn.commit()
        return True, "Material berhasil dihapus."

def update_material_price(material_id: int, harga_beli: float, tanggal: Optional[str] = None, keterangan: str = "") -> bool:
    """Mengupdate harga beli terbaru material dan mencatat ke histori tanpa menimpa data lama"""
    if harga_beli <= 0:
        return False
    tgl = tanggal or datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE material SET harga_beli_terbaru = ? WHERE id = ?", (harga_beli, material_id))
        cursor.execute("""
        INSERT INTO material_harga_histori (material_id, tanggal, harga_beli, keterangan)
        VALUES (?, ?, ?, ?)
        """, (material_id, tgl, harga_beli, keterangan.strip()))
        conn.commit()
        return True

def get_material_price_history(material_id: int) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT h.*, m.nama AS material_nama, m.satuan AS material_satuan, m.kode AS material_kode
        FROM material_harga_histori h
        JOIN material m ON h.material_id = m.id
        WHERE h.material_id = ?
        ORDER BY h.tanggal DESC, h.id DESC
        """, (material_id,))
        return [dict(row) for row in cursor.fetchall()]


# ==============================================================================
# PROYEK CRUD & SERVICES
# ==============================================================================

def get_all_proyek(only_active: bool = False, tipe_proyek: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        params = []
        conds = []
        if only_active:
            conds.append("status = 'aktif'")
        if tipe_proyek and tipe_proyek in ("dalam", "luar"):
            conds.append("tipe_proyek = ?")
            params.append(tipe_proyek)
        where = ("WHERE " + " AND ".join(conds)) if conds else ""
        cursor.execute(f"SELECT * FROM proyek {where} ORDER BY status ASC, nama ASC", params)
        return [dict(row) for row in cursor.fetchall()]

def save_proyek(nama: str, lokasi: str, status: str = "aktif", keterangan: str = "", proyek_id: Optional[int] = None, tipe_proyek: str = "luar") -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        tipe = tipe_proyek if tipe_proyek in ("dalam", "luar") else "luar"
        if proyek_id:
            cursor.execute("""
            UPDATE proyek SET nama = ?, lokasi = ?, status = ?, keterangan = ?, tipe_proyek = ? WHERE id = ?
            """, (nama.strip(), lokasi.strip(), status, keterangan.strip(), tipe, proyek_id))
            conn.commit()
            return proyek_id
        else:
            cursor.execute("""
            INSERT INTO proyek (nama, lokasi, status, keterangan, tipe_proyek) VALUES (?, ?, ?, ?, ?)
            """, (nama.strip(), lokasi.strip(), status, keterangan.strip(), tipe))
            conn.commit()
            return cursor.lastrowid

def delete_proyek(proyek_id: int) -> Tuple[bool, str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pengiriman WHERE proyek_id = ?", (proyek_id,))
        if cursor.fetchone()[0] > 0:
            return False, "Proyek tidak dapat dihapus karena memiliki riwayat pengiriman cor. Anda dapat mengubah statusnya menjadi 'selesai'."
        cursor.execute("SELECT COUNT(*) FROM proyek_piutang WHERE proyek_id = ?", (proyek_id,))
        if cursor.fetchone()[0] > 0:
            return False, "Proyek tidak dapat dihapus karena memiliki riwayat tagihan/piutang proyek."
        cursor.execute("DELETE FROM proyek WHERE id = ?", (proyek_id,))
        conn.commit()
        return True, "Proyek berhasil dihapus."


# ==============================================================================
# KENDARAAN & ARMADA OPERASIONAL CRUD & SERVICES
# ==============================================================================

def get_all_kendaraan(status: Optional[str] = None, search: Optional[str] = None, 
                      jenis: Optional[str] = None) -> List[Dict[str, Any]]:
    """Mengambil daftar seluruh armada kendaraan dengan opsi filter status, jenis, dan pencarian"""
    with get_connection() as conn:
        cursor = conn.cursor()
        conds = []
        params = []
        if status and status.lower() != "semua":
            conds.append("status = ?")
            params.append(status.lower())
        if jenis and jenis.lower() != "semua":
            conds.append("jenis_kendaraan = ?")
            params.append(jenis)
        if search:
            conds.append("(no_plat LIKE ? OR nama_kendaraan LIKE ? OR driver_default LIKE ? OR keterangan_operasional LIKE ?)")
            s = f"%{search.strip()}%"
            params.extend([s, s, s, s])
        
        where = ("WHERE " + " AND ".join(conds)) if conds else ""
        cursor.execute(f"SELECT * FROM kendaraan {where} ORDER BY CASE status WHEN 'operasional' THEN 1 WHEN 'tersedia' THEN 2 WHEN 'maintenance' THEN 3 ELSE 4 END, no_plat ASC", params)
        return [dict(row) for row in cursor.fetchall()]

def get_kendaraan_by_id(kendaraan_id: int) -> Optional[Dict[str, Any]]:
    """Mengambil data 1 kendaraan berdasarkan ID"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM kendaraan WHERE id = ?", (kendaraan_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_kendaraan_by_plat(no_plat: str) -> Optional[Dict[str, Any]]:
    """Mengambil data 1 kendaraan berdasarkan Nomor Plat"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM kendaraan WHERE UPPER(no_plat) = ?", (no_plat.strip().upper(),))
        row = cursor.fetchone()
        return dict(row) if row else None

def save_kendaraan(no_plat: str, nama_kendaraan: str = "", jenis_kendaraan: str = "Truk Mixer",
                   kapasitas_m3: float = 0.0, driver_default: str = "", status: str = "tersedia",
                   keterangan_operasional: str = "", catatan: str = "", 
                   kendaraan_id: Optional[int] = None) -> int:
    """Menyimpan atau memperbarui data armada kendaraan"""
    with get_connection() as conn:
        cursor = conn.cursor()
        no_plat_clean = no_plat.strip().upper()
        if kendaraan_id:
            cursor.execute("""
            UPDATE kendaraan 
            SET no_plat = ?, nama_kendaraan = ?, jenis_kendaraan = ?, kapasitas_m3 = ?,
                driver_default = ?, status = ?, keterangan_operasional = ?, catatan = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (no_plat_clean, nama_kendaraan.strip(), jenis_kendaraan.strip(),
                  float(kapasitas_m3 or 0), driver_default.strip(), status,
                  keterangan_operasional.strip(), catatan.strip(), kendaraan_id))
            conn.commit()
            return kendaraan_id
        else:
            cursor.execute("""
            INSERT INTO kendaraan (no_plat, nama_kendaraan, jenis_kendaraan, kapasitas_m3,
                                   driver_default, status, keterangan_operasional, catatan)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (no_plat_clean, nama_kendaraan.strip(), jenis_kendaraan.strip(),
                  float(kapasitas_m3 or 0), driver_default.strip(), status,
                  keterangan_operasional.strip(), catatan.strip()))
            conn.commit()
            return cursor.lastrowid

def hapus_kendaraan(kendaraan_id: int) -> Tuple[bool, str]:
    """Menghapus data kendaraan dengan proteksi integritas data historis"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT no_plat, nama_kendaraan FROM kendaraan WHERE id = ?", (kendaraan_id,))
        row = cursor.fetchone()
        if not row:
            return False, "Data armada tidak ditemukan."
            
        plat = row["no_plat"]
        
        # Cek apakah ada riwayat pengeluaran kas kantor
        cursor.execute("SELECT COUNT(*) FROM kas_kantor WHERE kendaraan_id = ?", (kendaraan_id,))
        cnt_kas = cursor.fetchone()[0]
        
        # Cek apakah ada riwayat pengiriman cor
        cursor.execute("SELECT COUNT(*) FROM pengiriman WHERE kendaraan_id = ? OR UPPER(no_plat_truk) = ?", (kendaraan_id, plat.upper()))
        cnt_kirim = cursor.fetchone()[0]
        
        if cnt_kas > 0 or cnt_kirim > 0:
            return False, (
                f"Armada '{plat}' tidak dapat dihapus permanen karena memiliki data historis transaksi "
                f"({cnt_kas} nota biaya kas, {cnt_kirim} pengiriman cor).\n\n"
                f"Silakan ubah status armada menjadi 'Nonaktif' untuk mengarsipkannya agar pembukuan tetap konsisten."
            )
            
        cursor.execute("DELETE FROM kendaraan WHERE id = ?", (kendaraan_id,))
        conn.commit()
        return True, f"Armada {plat} berhasil dihapus."

def update_status_operasional_kendaraan(kendaraan_id_or_plat, status: str, 
                                       keterangan_operasional: str = "") -> bool:
    """Mengupdate status operasional dan keterangan jalan/standby kendaraan"""
    with get_connection() as conn:
        cursor = conn.cursor()
        if isinstance(kendaraan_id_or_plat, int) or (isinstance(kendaraan_id_or_plat, str) and kendaraan_id_or_plat.isdigit()):
            cursor.execute("""
            UPDATE kendaraan 
            SET status = ?, keterangan_operasional = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (status, keterangan_operasional.strip(), int(kendaraan_id_or_plat)))
        else:
            plat_clean = str(kendaraan_id_or_plat).strip().upper()
            cursor.execute("""
            UPDATE kendaraan 
            SET status = ?, keterangan_operasional = ?, updated_at = CURRENT_TIMESTAMP
            WHERE UPPER(no_plat) = ?
            """, (status, keterangan_operasional.strip(), plat_clean))
        conn.commit()
        return cursor.rowcount > 0

def get_rekap_status_kendaraan() -> Dict[str, int]:
    """Menghitung ringkasan jumlah armada berdasarkan status operasional"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM kendaraan")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM kendaraan WHERE status = 'operasional'")
        operasional = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM kendaraan WHERE status = 'tersedia'")
        tersedia = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM kendaraan WHERE status = 'maintenance'")
        maintenance = cursor.fetchone()[0]
        return {
            "total": total,
            "operasional": operasional,
            "tersedia": tersedia,
            "maintenance": maintenance
        }


# ==============================================================================
# MUTU BETON, RESEP, HPP & HARGA JUAL SERVICES
# ==============================================================================

def get_all_mutu_beton() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mutu_beton")
        rows = [dict(row) for row in cursor.fetchall()]
        
        # Tambahkan kalkulasi HPP dan Margin untuk setiap mutu beton
        for item in rows:
            calc = calculate_mutu_hpp_from_cursor(cursor, item["id"], float(item.get("biaya_operasional_per_m3") or 0))
            item["hpp_per_m3"] = calc["hpp_per_m3"]
            h_jual = float(item.get("harga_jual_per_m3") or 0)
            item["laba_per_m3"] = h_jual - calc["hpp_per_m3"]
            item["margin_persen"] = ((item["laba_per_m3"] / h_jual) * 100.0) if h_jual > 0 else 0.0

        def sort_key(item):
            code = item.get("kode", "")
            if code in TABEL_KODE_BETON_STANDAR:
                return (0, TABEL_KODE_BETON_STANDAR[code]["urutan"])
            if code.upper().startswith("K-"):
                try:
                    num = int(code.upper().replace("K-", "").strip())
                    return (1, num)
                except Exception:
                    pass
            return (2, code.lower())
            
        rows.sort(key=sort_key)
        return rows

def get_resep_by_mutu_id(mutu_id: int) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT r.id, r.mutu_beton_id, r.material_id, r.jumlah_per_m3,
               m.kode AS material_kode, m.nama AS material_nama, m.satuan AS material_satuan,
               m.harga_beli_terbaru
        FROM mutu_beton_resep r
        JOIN material m ON r.material_id = m.id
        WHERE r.mutu_beton_id = ?
        ORDER BY m.nama ASC
        """, (mutu_id,))
        rows = [dict(row) for row in cursor.fetchall()]
        for r in rows:
            r["subtotal_biaya"] = (float(r["jumlah_per_m3"] or 0) * float(r["harga_beli_terbaru"] or 0))
        return rows

def calculate_mutu_hpp_from_cursor(cursor, mutu_id: int, biaya_ops: float = 0.0) -> Dict[str, Any]:
    cursor.execute("""
    SELECT r.jumlah_per_m3, m.nama AS material_nama, m.satuan AS material_satuan, m.harga_beli_terbaru
    FROM mutu_beton_resep r
    JOIN material m ON r.material_id = m.id
    WHERE r.mutu_beton_id = ?
    """, (mutu_id,))
    rows = cursor.fetchall()
    
    breakdown = []
    total_material_cost = 0.0
    for r in rows:
        qty = float(r["jumlah_per_m3"] or 0)
        price = float(r["harga_beli_terbaru"] or 0)
        sub = qty * price
        total_material_cost += sub
        breakdown.append({
            "material": r["material_nama"],
            "satuan": r["material_satuan"],
            "qty_per_m3": qty,
            "harga_beli": price,
            "subtotal": sub
        })
    
    total_hpp = total_material_cost + biaya_ops
    return {
        "total_material_cost": total_material_cost,
        "biaya_operasional": biaya_ops,
        "hpp_per_m3": total_hpp,
        "breakdown": breakdown,
        "items": breakdown
    }

def calculate_mutu_hpp(mutu_id: int) -> Dict[str, Any]:
    """Menghitung rincian HPP 1 m3 mutu beton berdasarkan harga beli material terkini"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT biaya_operasional_per_m3, harga_jual_per_m3 FROM mutu_beton WHERE id = ?", (mutu_id,))
        m_row = cursor.fetchone()
        biaya_ops = float(m_row["biaya_operasional_per_m3"] or 0) if m_row else 0.0
        harga_jual = float(m_row["harga_jual_per_m3"] or 0) if m_row else 0.0

        calc = calculate_mutu_hpp_from_cursor(cursor, mutu_id, biaya_ops)
        calc["harga_jual_per_m3"] = harga_jual
        calc["laba_per_m3"] = harga_jual - calc["hpp_per_m3"]
        calc["margin_persen"] = ((calc["laba_per_m3"] / harga_jual) * 100.0) if harga_jual > 0 else 0.0
        return calc

def save_mutu_beton_with_resep(kode: str, nama: str, keterangan: str, 
                               resep_items: List[Dict[str, Any]], 
                               harga_jual_per_m3: float = 0, 
                               biaya_operasional_per_m3: float = 0,
                               mutu_id: Optional[int] = None) -> int:
    """Menyimpan atau mengupdate mutu beton beserta resep, harga jual, dan biaya operasional"""
    with get_connection() as conn:
        cursor = conn.cursor()
        if mutu_id:
            cursor.execute("""
            UPDATE mutu_beton 
            SET kode = ?, nama = ?, keterangan = ?, harga_jual_per_m3 = ?, biaya_operasional_per_m3 = ?
            WHERE id = ?
            """, (kode.strip(), nama.strip(), keterangan.strip(), harga_jual_per_m3, biaya_operasional_per_m3, mutu_id))
            target_mutu_id = mutu_id
            cursor.execute("DELETE FROM mutu_beton_resep WHERE mutu_beton_id = ?", (target_mutu_id,))
        else:
            cursor.execute("""
            INSERT INTO mutu_beton (kode, nama, keterangan, harga_jual_per_m3, biaya_operasional_per_m3) 
            VALUES (?, ?, ?, ?, ?)
            """, (kode.strip(), nama.strip(), keterangan.strip(), harga_jual_per_m3, biaya_operasional_per_m3))
            target_mutu_id = cursor.lastrowid

        # Insert resep items
        for item in resep_items:
            mat_id = item['material_id']
            qty = float(item['jumlah_per_m3'])
            if qty > 0:
                cursor.execute("""
                INSERT INTO mutu_beton_resep (mutu_beton_id, material_id, jumlah_per_m3)
                VALUES (?, ?, ?)
                """, (target_mutu_id, mat_id, qty))
        
        conn.commit()
        return target_mutu_id

def delete_mutu_beton(mutu_id: int) -> Tuple[bool, str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pengiriman WHERE mutu_beton_id = ?", (mutu_id,))
        if cursor.fetchone()[0] > 0:
            return False, "Mutu beton tidak dapat dihapus karena sudah ada riwayat pengiriman yang menggunakannya."
        cursor.execute("DELETE FROM mutu_beton WHERE id = ?", (mutu_id,))
        conn.commit()
        return True, "Mutu beton berhasil dihapus."


# ==============================================================================
# INDIVIDUAL STOCK PER USER SERVICES
# ==============================================================================

def init_user_stok_for_material(user_id: int, material_id: int, stok_awal: float = 0.0):
    """Inisialisasi record stok individual untuk user tertentu pada material tertentu.
    Jika record sudah ada, tidak ada perubahan (INSERT OR IGNORE)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR IGNORE INTO user_material_stok (user_id, material_id, stok_saat_ini)
        VALUES (?, ?, ?)
        """, (user_id, material_id, stok_awal))
        conn.commit()


def init_user_stok_for_all_materials(user_id: int):
    """Inisialisasi stok individual untuk semua material yang ada, berdasarkan stok global saat ini.
    Dipanggil saat user baru dibuat."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, stok_saat_ini FROM material")
        materials = cursor.fetchall()
        for mat in materials:
            cursor.execute("""
            INSERT OR IGNORE INTO user_material_stok (user_id, material_id, stok_saat_ini)
            VALUES (?, ?, ?)
            """, (user_id, mat["id"], float(mat["stok_saat_ini"] or 0)))
        conn.commit()


def get_user_stok(user_id: int, material_id: int) -> float:
    """Ambil stok saat ini milik user tertentu untuk satu material. Return 0 jika belum ada."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT stok_saat_ini FROM user_material_stok WHERE user_id = ? AND material_id = ?
        """, (user_id, material_id))
        row = cursor.fetchone()
        return float(row["stok_saat_ini"]) if row else 0.0


def get_all_user_stok(user_id: int) -> List[Dict[str, Any]]:
    """Ambil semua stok material milik user tertentu, lengkap dengan info material."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT 
            ums.material_id,
            ums.stok_saat_ini AS stok_user,
            ums.updated_at,
            m.kode, m.nama, m.satuan, m.stok_minimum, m.harga_beli_terbaru,
            m.stok_saat_ini AS stok_global
        FROM user_material_stok ums
        JOIN material m ON ums.material_id = m.id
        WHERE ums.user_id = ?
        ORDER BY m.nama ASC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]


def _sync_shared_stok_masuk_to_all_users(cursor, material_id: int, jumlah: float, stok_masuk_id: int, tanggal: str):
    """Internal helper: tambahkan jumlah stok masuk ke SEMUA user aktif (stok masuk bersifat shared)."""
    cursor.execute("SELECT id FROM users WHERE is_active = 1")
    all_users = cursor.fetchall()
    for u in all_users:
        uid = u["id"]
        # Upsert: tambah jika sudah ada, insert jika belum
        cursor.execute("""
        INSERT INTO user_material_stok (user_id, material_id, stok_saat_ini, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, material_id) DO UPDATE SET
            stok_saat_ini = stok_saat_ini + ?,
            updated_at = CURRENT_TIMESTAMP
        """, (uid, material_id, jumlah, jumlah))
        # Log mutasi
        cursor.execute("""
        INSERT INTO user_stok_log (user_id, material_id, tipe, jumlah, referensi_id, keterangan)
        VALUES (?, ?, 'masuk_shared', ?, ?, ?)
        """, (uid, material_id, jumlah, stok_masuk_id, f"Stok masuk bersama tgl {tanggal}"))


def _rollback_shared_stok_masuk_from_all_users(cursor, material_id: int, jumlah: float, stok_masuk_id: int):
    """Internal helper: kurangi kembali stok semua user saat stok_masuk dihapus."""
    cursor.execute("SELECT id FROM users WHERE is_active = 1")
    all_users = cursor.fetchall()
    for u in all_users:
        uid = u["id"]
        cursor.execute("""
        UPDATE user_material_stok 
        SET stok_saat_ini = MAX(0, stok_saat_ini - ?), updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ? AND material_id = ?
        """, (jumlah, uid, material_id))
        cursor.execute("""
        INSERT INTO user_stok_log (user_id, material_id, tipe, jumlah, referensi_id, keterangan)
        VALUES (?, ?, 'masuk_shared_rollback', ?, ?, 'Rollback: hapus stok masuk')
        """, (uid, material_id, jumlah, stok_masuk_id))


def reduce_user_stok(user_id: int, material_id: int, jumlah: float, referensi_id: int = None, keterangan: str = ""):
    """Kurangi stok individual milik user tertentu. Dipanggil saat pengiriman/produksi."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE user_material_stok 
        SET stok_saat_ini = MAX(0, stok_saat_ini - ?), updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ? AND material_id = ?
        """, (jumlah, user_id, material_id))
        cursor.execute("""
        INSERT INTO user_stok_log (user_id, material_id, tipe, jumlah, referensi_id, keterangan)
        VALUES (?, ?, 'keluar_individual', ?, ?, ?)
        """, (user_id, material_id, jumlah, referensi_id, keterangan or "Pemakaian pengiriman"))
        conn.commit()


def restore_user_stok(user_id: int, material_id: int, jumlah: float, referensi_id: int = None, keterangan: str = ""):
    """Kembalikan stok individual milik user tertentu. Dipanggil saat pengiriman dibatalkan."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE user_material_stok 
        SET stok_saat_ini = stok_saat_ini + ?, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ? AND material_id = ?
        """, (jumlah, user_id, material_id))
        cursor.execute("""
        INSERT INTO user_stok_log (user_id, material_id, tipe, jumlah, referensi_id, keterangan)
        VALUES (?, ?, 'keluar_individual_rollback', ?, ?, ?)
        """, (user_id, material_id, jumlah, referensi_id, keterangan or "Rollback pembatalan pengiriman"))
        conn.commit()


def get_user_stok_log(user_id: int, material_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Ambil log mutasi stok individual user, opsional filter per material."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
        SELECT usl.*, m.nama AS material_nama, m.satuan
        FROM user_stok_log usl
        JOIN material m ON usl.material_id = m.id
        WHERE usl.user_id = ?
        """
        params = [user_id]
        if material_id:
            query += " AND usl.material_id = ?"
            params.append(material_id)
        query += " ORDER BY usl.created_at DESC LIMIT 500"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


# ==============================================================================
# STOK MATERIAL & PENERIMAAN BARANG SERVICES (POS FLOW)
# ==============================================================================

def tambah_stok_masuk(material_id: int, tanggal: str, jumlah: float, 
                      no_plat: str = "", supplier: str = "", keterangan: str = "", 
                      harga_satuan: float = 0.0, kategori_piutang: str = "kantor",
                      jatuh_tempo: str = "", tanggal_datang: Optional[str] = None) -> int:
    """
    1. Mencatat transaksi stok masuk (order) dan menambah stok_saat_ini.
    2. Jika ada input harga_satuan > 0, update harga beli terbaru & catat riwayat harga.
    3. Otomatis mencatat faktur Piutang/Tagihan Material Supplier (Kategori: Kantor / Perusahaan) + Jatuh Tempo.
    4. Menyimpan tanggal_datang jika sudah datang, atau None jika masih status order.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Ambil info material
        cursor.execute("SELECT kode, nama, satuan, harga_beli_terbaru FROM material WHERE id = ?", (material_id,))
        mat_row = cursor.fetchone()
        if not mat_row:
            raise ValueError("Material tidak ditemukan.")

        # Gunakan harga terbaru jika harga_satuan 0
        if harga_satuan <= 0:
            harga_satuan = float(mat_row["harga_beli_terbaru"] or 0)
            
        total_biaya = jumlah * harga_satuan
        pembayaran_semen_id = None
        clean_kat = "perusahaan" if str(kategori_piutang).strip().lower() == "perusahaan" else "kantor"
        kat_label = "Perusahaan" if clean_kat == "perusahaan" else "Kantor"
        clean_tgl_dtg = str(tanggal_datang).strip() if tanggal_datang and str(tanggal_datang).strip() not in ("", "None", "-") else None

        actual_jt = str(jatuh_tempo or "").strip()
        if not actual_jt:
            try:
                base_dt = datetime.strptime(tanggal, "%Y-%m-%d")
                actual_jt = (base_dt + timedelta(days=14)).strftime("%Y-%m-%d")
            except Exception:
                actual_jt = tanggal

        # Otomatis catat faktur Tagihan / Piutang Material Supplier untuk seluruh material
        if total_biaya > 0:
            is_semen = (mat_row["kode"] == "MAT-SMN" or "semen" in mat_row["nama"].lower())
            if is_semen and mat_row["satuan"].lower() == "kg":
                jumlah_ton = (jumlah / 1000.0)
                harga_per_ton = (harga_satuan * 1000.0)
            else:
                jumlah_ton = jumlah
                harga_per_ton = harga_satuan
            
            no_do = f"DO-{mat_row['kode']}-{tanggal.replace('-', '')}-{int(jumlah_ton)}"
            supp_str = supplier.strip() or f"Supplier {mat_row['nama']}"
            ket_str = keterangan.strip() or f"Penerimaan {mat_row['nama']} (Piutang {kat_label})"

            cursor.execute("""
            INSERT INTO pembayaran_semen (no_order, supplier, tanggal_order, tanggal_datang, jumlah_ton, harga_per_ton, total_harga, keterangan, kategori_piutang, material_id, jatuh_tempo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (no_do, supp_str, tanggal, clean_tgl_dtg, jumlah_ton, harga_per_ton, total_biaya, ket_str, clean_kat, material_id, actual_jt))
            pembayaran_semen_id = cursor.lastrowid

        # Insert Stok Masuk (dengan tanggal_datang)
        cursor.execute("""
        INSERT INTO stok_masuk (material_id, tanggal, jumlah, no_plat, supplier, harga_satuan, total_biaya, pembayaran_semen_id, keterangan, kategori_piutang, jatuh_tempo, tanggal_datang)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (material_id, tanggal, jumlah, no_plat.strip(), supplier.strip(), harga_satuan, total_biaya, pembayaran_semen_id, keterangan.strip(), clean_kat, actual_jt, clean_tgl_dtg))
        stok_id = cursor.lastrowid

        # Update link stok_masuk_id di pembayaran_semen
        if pembayaran_semen_id:
            cursor.execute("UPDATE pembayaran_semen SET stok_masuk_id = ? WHERE id = ?", (stok_id, pembayaran_semen_id))

        # Update stok saat ini & harga terbaru material (GLOBAL)
        if harga_satuan > 0:
            cursor.execute("""
            UPDATE material 
            SET stok_saat_ini = stok_saat_ini + ?, harga_beli_terbaru = ? 
            WHERE id = ?
            """, (jumlah, harga_satuan, material_id))
            
            # Catat histori perubahan harga
            cursor.execute("""
            INSERT INTO material_harga_histori (material_id, tanggal, harga_beli, keterangan)
            VALUES (?, ?, ?, ?)
            """, (material_id, tanggal, harga_satuan, f"Penerimaan Stok ({supplier.strip() or 'Supplier'})"))
        else:
            cursor.execute("UPDATE material SET stok_saat_ini = stok_saat_ini + ? WHERE id = ?", (jumlah, material_id))

        # === INDIVIDUAL STOCK: Tambah ke SEMUA user aktif (stok masuk = shared) ===
        _sync_shared_stok_masuk_to_all_users(cursor, material_id, jumlah, stok_id, tanggal)

        conn.commit()
        return stok_id

def hapus_stok_masuk(stok_id: int) -> Tuple[bool, str]:
    """Menghapus transaksi stok masuk, mengurangi stok kembali, dan menghapus hutang semen terkait"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT material_id, jumlah, pembayaran_semen_id FROM stok_masuk WHERE id = ?", (stok_id,))
        row = cursor.fetchone()
        if not row:
            return False, "Data stok masuk tidak ditemukan."
        
        mat_id = row["material_id"]
        qty = row["jumlah"]
        semen_id = row["pembayaran_semen_id"]
        
        if semen_id:
            # Hapus cicilan semen dan order semen
            cursor.execute("DELETE FROM pembayaran_semen_cicilan WHERE pembayaran_semen_id = ?", (semen_id,))
            cursor.execute("DELETE FROM pembayaran_semen WHERE id = ?", (semen_id,))
            
        cursor.execute("DELETE FROM stok_masuk WHERE id = ?", (stok_id,))
        cursor.execute("UPDATE material SET stok_saat_ini = stok_saat_ini - ? WHERE id = ?", (qty, mat_id))

        # === INDIVIDUAL STOCK: Rollback dari SEMUA user aktif ===
        _rollback_shared_stok_masuk_from_all_users(cursor, mat_id, qty, stok_id)
        
        # Hitung ulang kas jika ada cicilan terhapus
        recalculate_master_kas_balances(cursor)
        conn.commit()
        return True, "Data stok masuk berhasil dihapus dan stok material telah disesuaikan."

def set_stok_masuk_tanggal_datang(stok_masuk_id: int, tanggal_datang: str) -> Tuple[bool, str]:
    """
    Update tanggal datang aktual untuk catatan stok masuk dan pembayaran semen/material terkait.
    """
    try:
        clean_dtg = str(tanggal_datang or "").strip()
        if not clean_dtg:
            return False, "Tanggal datang tidak boleh kosong."
            
        with get_connection() as conn:
            cursor = conn.cursor()
            # 1. Update stok_masuk
            cursor.execute("UPDATE stok_masuk SET tanggal_datang = ? WHERE id = ?", (clean_dtg, stok_masuk_id))
            
            # 2. Update pembayaran_semen terkait (bisa via stok_masuk_id atau via foreign key pembayaran_semen_id)
            cursor.execute("""
            UPDATE pembayaran_semen 
            SET tanggal_datang = ? 
            WHERE stok_masuk_id = ? OR id = (SELECT pembayaran_semen_id FROM stok_masuk WHERE id = ?)
            """, (clean_dtg, stok_masuk_id, stok_masuk_id))
            
            conn.commit()
            return True, "Tanggal datang berhasil disimpan."
    except Exception as e:
        return False, str(e)

def get_riwayat_stok_masuk(material_id: Optional[int] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
        SELECT s.*, m.nama AS material_nama, m.satuan AS material_satuan, m.kode AS material_kode
        FROM stok_masuk s
        JOIN material m ON s.material_id = m.id
        WHERE 1=1
        """
        params = []
        if material_id:
            query += " AND s.material_id = ?"
            params.append(material_id)
        if start_date:
            query += " AND s.tanggal >= ?"
            params.append(start_date)
        if end_date:
            query += " AND s.tanggal <= ?"
            params.append(end_date)
            
        query += " ORDER BY s.tanggal DESC, s.id DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def get_rekap_kartu_stok() -> List[Dict[str, Any]]:
    """Rekap pergerakan stok: total masuk, total terpakai pengiriman, stok saat ini & nilai aset stok"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT 
            m.id, m.kode, m.nama, m.satuan, m.stok_saat_ini, m.stok_minimum, m.harga_beli_terbaru,
            COALESCE((SELECT SUM(s.jumlah) FROM stok_masuk s WHERE s.material_id = m.id), 0) AS total_masuk,
            COALESCE((SELECT SUM(d.jumlah_terpakai) FROM pengiriman_detail d WHERE d.material_id = m.id), 0) AS total_terpakai,
            (m.stok_saat_ini * m.harga_beli_terbaru) AS nilai_aset_stok
        FROM material m
        ORDER BY m.nama ASC
        """)
        return [dict(row) for row in cursor.fetchall()]


# ==============================================================================
# PRODUKSI & PENGIRIMAN SERVICES (INTEGRASI HPP & PIUTANG PROYEK OTOMATIS)
# ==============================================================================

def preview_kebutuhan_material(mutu_beton_id: int, volume_m3: float, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Menghitung kebutuhan material berdasarkan resep x volume,
    serta membandingkannya dengan sisa stok saat ini (stok milik user jika user_id diberikan).
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("""
            SELECT 
                r.material_id, m.nama AS material_nama, m.satuan AS material_satuan,
                COALESCE(ums.stok_saat_ini, m.stok_saat_ini) AS stok_saat_ini, 
                r.jumlah_per_m3, m.harga_beli_terbaru,
                (r.jumlah_per_m3 * ?) AS kebutuhan,
                ((COALESCE(ums.stok_saat_ini, m.stok_saat_ini) - (r.jumlah_per_m3 * ?)) >= 0) AS cukup,
                (r.jumlah_per_m3 * ? * m.harga_beli_terbaru) AS subtotal_hpp
            FROM mutu_beton_resep r
            JOIN material m ON r.material_id = m.id
            LEFT JOIN user_material_stok ums ON (ums.material_id = m.id AND ums.user_id = ?)
            WHERE r.mutu_beton_id = ?
            ORDER BY m.nama ASC
            """, (volume_m3, volume_m3, volume_m3, user_id, mutu_beton_id))
        else:
            cursor.execute("""
            SELECT 
                r.material_id, m.nama AS material_nama, m.satuan AS material_satuan,
                m.stok_saat_ini, r.jumlah_per_m3, m.harga_beli_terbaru,
                (r.jumlah_per_m3 * ?) AS kebutuhan,
                ((m.stok_saat_ini - (r.jumlah_per_m3 * ?)) >= 0) AS cukup,
                (r.jumlah_per_m3 * ? * m.harga_beli_terbaru) AS subtotal_hpp
            FROM mutu_beton_resep r
            JOIN material m ON r.material_id = m.id
            WHERE r.mutu_beton_id = ?
            ORDER BY m.nama ASC
            """, (volume_m3, volume_m3, volume_m3, mutu_beton_id))
        return [dict(row) for row in cursor.fetchall()]


def simpan_pengiriman(tanggal: str, mutu_beton_id: int, volume_m3: float, proyek_id: int, 
                      tujuan_pengiriman: str = "", no_surat_jalan: str = "", no_plat_truk: str = "",
                      driver: str = "", catatan: str = "", harga_jual_kustom: Optional[float] = None,
                      user_id: Optional[int] = None, hide_harga_sj: int = 0,
                      kendaraan_id: Optional[int] = None) -> Tuple[bool, str, Optional[int]]:
    """
    1. Hitung kebutuhan material = resep * volume
    2. Hitung Snapshot HPP per m3 dari harga beli material saat ini + biaya operasional
    3. Ambil Harga Jual per m3 dan hitung Laba (Rp & %)
    4. Simpan ke tabel pengiriman & pengiriman_detail (termasuk relasi foreign key kendaraan_id)
    5. Kurangi stok fisik masing-masing material
    6. OTOMATIS mencatat tagihan piutang proyek di Keuangan (proyek_piutang)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Ambil info mutu beton & resep
        cursor.execute("SELECT kode, nama, harga_jual_per_m3, biaya_operasional_per_m3 FROM mutu_beton WHERE id = ?", (mutu_beton_id,))
        mutu_row = cursor.fetchone()
        if not mutu_row:
            return False, "Mutu beton tidak ditemukan.", None

        cursor.execute("""
        SELECT r.material_id, r.jumlah_per_m3, m.nama, m.satuan, m.stok_saat_ini, m.harga_beli_terbaru
        FROM mutu_beton_resep r
        JOIN material m ON r.material_id = m.id
        WHERE r.mutu_beton_id = ?
        """, (mutu_beton_id,))
        resep_list = cursor.fetchall()
        
        if not resep_list:
            return False, "Mutu beton ini belum memiliki komposisi resep material! Silakan atur di Master Data -> Mutu Beton.", None

        # Hitung HPP
        biaya_ops = float(mutu_row["biaya_operasional_per_m3"] or 0)
        hpp_material_unit = 0.0
        for r in resep_list:
            hpp_material_unit += (float(r["jumlah_per_m3"] or 0) * float(r["harga_beli_terbaru"] or 0))
        
        hpp_per_m3 = hpp_material_unit + biaya_ops
        total_hpp = hpp_per_m3 * volume_m3

        # Harga Jual
        harga_jual = float(harga_jual_kustom) if (harga_jual_kustom and harga_jual_kustom > 0) else float(mutu_row["harga_jual_per_m3"] or 850000.0)
        total_pendapatan = harga_jual * volume_m3
        margin_laba_rp = total_pendapatan - total_hpp
        margin_laba_persen = (margin_laba_rp / total_pendapatan * 100.0) if total_pendapatan > 0 else 0.0

        # Generate No Surat Jalan jika belum diisi manual
        if not no_surat_jalan or not no_surat_jalan.strip():
            today_str = tanggal.replace("-", "")
            cursor.execute("SELECT COUNT(*) FROM pengiriman WHERE tanggal = ?", (tanggal,))
            count_today = cursor.fetchone()[0] + 1
            no_surat_jalan = f"SJ-{today_str}-{count_today:03d}"

        # Otomatis cari kendaraan_id jika belum diisi tapi nomor plat ada
        if not kendaraan_id and no_plat_truk and no_plat_truk.strip():
            cursor.execute("SELECT id FROM kendaraan WHERE UPPER(no_plat) = ?", (no_plat_truk.strip().upper(),))
            k_row = cursor.fetchone()
            if k_row:
                kendaraan_id = k_row[0]

        # 1. Insert Pengiriman
        cursor.execute("""
        INSERT INTO pengiriman (
            no_surat_jalan, tanggal, mutu_beton_id, volume_m3, proyek_id, tujuan_pengiriman, 
            no_plat_truk, driver, hpp_per_m3, total_hpp, harga_jual_per_m3, total_pendapatan, 
            margin_laba_rp, margin_laba_persen, catatan, hide_harga_sj, kendaraan_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (no_surat_jalan, tanggal, mutu_beton_id, volume_m3, proyek_id, tujuan_pengiriman.strip(), 
              no_plat_truk.strip(), driver.strip(), hpp_per_m3, total_hpp, harga_jual, total_pendapatan, 
              margin_laba_rp, margin_laba_persen, catatan.strip(), int(hide_harga_sj or 0), kendaraan_id))
        pengiriman_id = cursor.lastrowid

        # 2. Insert Pengiriman Detail & Potong Stok Material
        for item in resep_list:
            mat_id = item["material_id"]
            qty_terpakai = float(item["jumlah_per_m3"]) * volume_m3
            
            cursor.execute("""
            INSERT INTO pengiriman_detail (pengiriman_id, material_id, jumlah_terpakai)
            VALUES (?, ?, ?)
            """, (pengiriman_id, mat_id, qty_terpakai))
            
            # Potong stok GLOBAL
            cursor.execute("""
            UPDATE material SET stok_saat_ini = stok_saat_ini - ? WHERE id = ?
            """, (qty_terpakai, mat_id))

            # === INDIVIDUAL STOCK: Potong stok hanya milik user yang aktif ===
            if user_id:
                cursor.execute("""
                UPDATE user_material_stok 
                SET stok_saat_ini = MAX(0, stok_saat_ini - ?), updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND material_id = ?
                """, (qty_terpakai, user_id, mat_id))
                cursor.execute("""
                INSERT INTO user_stok_log (user_id, material_id, tipe, jumlah, referensi_id, keterangan)
                VALUES (?, ?, 'keluar_individual', ?, ?, ?)
                """, (user_id, mat_id, qty_terpakai, pengiriman_id,
                      f"Pengiriman {no_surat_jalan} - {mutu_row['kode']} {volume_m3}m³"))

        # 3. Otomatis Catat Piutang Proyek di Modul Keuangan (POS Automation)
        cursor.execute("""
        INSERT INTO proyek_piutang (
            proyek_id, pengiriman_id, tanggal, no_surat_jalan, mutu_beton_kode, volume_m3, 
            harga_satuan_m3, total_tagihan, keterangan
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (proyek_id, pengiriman_id, tanggal, no_surat_jalan, mutu_row["kode"], volume_m3, 
              harga_jual, total_pendapatan, f"Pengecoran {mutu_row['kode']} ({volume_m3} m³) - {tujuan_pengiriman.strip() or 'Site'}"))

        # 4. Otomatis Sinkronkan Status Armada Kendaraan ke 'operasional'
        if kendaraan_id or (no_plat_truk and no_plat_truk.strip()):
            try:
                cursor.execute("SELECT nama FROM proyek WHERE id = ?", (proyek_id,))
                pr_row = cursor.fetchone()
                pr_nama = pr_row["nama"] if pr_row else "Proyek"
                ket_op = f"Kirim {mutu_row['kode']} ({volume_m3} m³) ke {pr_nama} - Driver: {driver.strip() if driver else '-'} (SJ: {no_surat_jalan})"
                
                if kendaraan_id:
                    cursor.execute("""
                    UPDATE kendaraan 
                    SET status = 'operasional', keterangan_operasional = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """, (ket_op, kendaraan_id))
                elif no_plat_truk and no_plat_truk.strip():
                    plat_clean = no_plat_truk.strip().upper()
                    cursor.execute("""
                    UPDATE kendaraan 
                    SET status = 'operasional', keterangan_operasional = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE UPPER(no_plat) = ?
                    """, (ket_op, plat_clean))
            except Exception:
                pass

        conn.commit()
        return True, "Pengiriman berhasil disimpan! Stok material terpotong & tagihan piutang proyek otomatis tercatat di Keuangan.", pengiriman_id

def hapus_pengiriman(pengiriman_id: int, user_id: Optional[int] = None) -> Tuple[bool, str]:
    """Batalkan pengiriman: kembalikan stok material (global & individual) dan hapus tagihan piutang terkait"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Ambil detail material terpakai
        cursor.execute("SELECT material_id, jumlah_terpakai FROM pengiriman_detail WHERE pengiriman_id = ?", (pengiriman_id,))
        details = cursor.fetchall()
        
        if not details:
            return False, "Data pengiriman tidak ditemukan."

        # Ambil user_id dari log jika tidak diberikan (untuk rollback yang benar)
        if not user_id:
            cursor.execute("""
            SELECT DISTINCT user_id FROM user_stok_log 
            WHERE referensi_id = ? AND tipe = 'keluar_individual'
            """, (pengiriman_id,))
            log_users = cursor.fetchall()
        else:
            log_users = [type('obj', (object,), {'__getitem__': lambda self, key: user_id if key == 'user_id' else None})()]
            # Buat list sederhana dengan dict
            log_users = [{'user_id': user_id}]
            
        # Kembalikan stok GLOBAL
        for row in details:
            cursor.execute("UPDATE material SET stok_saat_ini = stok_saat_ini + ? WHERE id = ?", (row["jumlah_terpakai"], row["material_id"]))

        # === INDIVIDUAL STOCK: Kembalikan stok ke user yang melakukan pengiriman ===
        for log_user in log_users:
            lu_id = log_user["user_id"] if hasattr(log_user, '__getitem__') else log_user["user_id"]
            for row in details:
                cursor.execute("""
                UPDATE user_material_stok 
                SET stok_saat_ini = stok_saat_ini + ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND material_id = ?
                """, (row["jumlah_terpakai"], lu_id, row["material_id"]))
                cursor.execute("""
                INSERT INTO user_stok_log (user_id, material_id, tipe, jumlah, referensi_id, keterangan)
                VALUES (?, ?, 'keluar_individual_rollback', ?, ?, 'Rollback: pembatalan pengiriman')
                """, (lu_id, row["material_id"], row["jumlah_terpakai"], pengiriman_id))
            
        # Ambil info no_plat_truk & kendaraan_id sebelum pengiriman dihapus
        cursor.execute("SELECT no_plat_truk, kendaraan_id FROM pengiriman WHERE id = ?", (pengiriman_id,))
        p_ship = cursor.fetchone()
        plat_to_standby = p_ship["no_plat_truk"] if (p_ship and p_ship["no_plat_truk"]) else None
        k_id_to_standby = p_ship["kendaraan_id"] if (p_ship and p_ship["kendaraan_id"]) else None

        # Hapus piutang proyek terkait
        cursor.execute("DELETE FROM proyek_piutang WHERE pengiriman_id = ?", (pengiriman_id,))
        cursor.execute("UPDATE kas_kantor SET pengiriman_id = NULL WHERE pengiriman_id = ?", (pengiriman_id,))
        cursor.execute("DELETE FROM pengiriman WHERE id = ?", (pengiriman_id,))
        
        # Kembalikan status armada terkait ke 'tersedia' jika saat ini berstatus operasional
        try:
            if k_id_to_standby:
                cursor.execute("""
                UPDATE kendaraan 
                SET status = 'tersedia', keterangan_operasional = 'Standby di Batching Plant', updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'operasional'
                """, (k_id_to_standby,))
            elif plat_to_standby and plat_to_standby.strip():
                cursor.execute("""
                UPDATE kendaraan 
                SET status = 'tersedia', keterangan_operasional = 'Standby di Batching Plant', updated_at = CURRENT_TIMESTAMP
                WHERE UPPER(no_plat) = ? AND status = 'operasional'
                """, (plat_to_standby.strip().upper(),))
        except Exception:
            pass

        conn.commit()
        return True, "Pengiriman berhasil dibatalkan, stok dikembalikan, dan tagihan piutang disesuaikan."

def get_riwayat_pengiriman(start_date: Optional[str] = None, end_date: Optional[str] = None, 
                           proyek_id: Optional[int] = None, mutu_id: Optional[int] = None,
                           search: Optional[str] = None,
                           status_bbm: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
        SELECT 
            p.*, 
            m.kode AS mutu_kode, m.nama AS mutu_nama,
            pr.nama AS proyek_nama, pr.lokasi AS proyek_lokasi,
            k.nama_kendaraan, k.jenis_kendaraan,
            (SELECT COALESCE(SUM(d.jumlah_terpakai), 0) 
             FROM pengiriman_detail d 
             JOIN material mat ON d.material_id = mat.id 
             WHERE d.pengiriman_id = p.id AND (mat.kode = 'MAT-SMN' OR LOWER(mat.nama) LIKE '%semen%')) AS semen_terpakai
        FROM pengiriman p
        JOIN mutu_beton m ON p.mutu_beton_id = m.id
        JOIN proyek pr ON p.proyek_id = pr.id
        LEFT JOIN kendaraan k ON p.kendaraan_id = k.id
        WHERE 1=1
        """
        params = []
        if start_date:
            query += " AND p.tanggal >= ?"
            params.append(start_date)
        if end_date:
            query += " AND p.tanggal <= ?"
            params.append(end_date)
        if proyek_id:
            query += " AND p.proyek_id = ?"
            params.append(proyek_id)
        if mutu_id:
            query += " AND p.mutu_beton_id = ?"
            params.append(mutu_id)
        if status_bbm and status_bbm != "all":
            if status_bbm == "Belum Diisi":
                query += " AND (p.status_bbm IS NULL OR p.status_bbm = 'Belum Diisi')"
            else:
                query += " AND p.status_bbm = ?"
                params.append(status_bbm)
        if search:
            query += " AND (p.no_surat_jalan LIKE ? OR p.tujuan_pengiriman LIKE ? OR p.driver LIKE ? OR p.catatan LIKE ? OR p.no_plat_truk LIKE ? OR k.nama_kendaraan LIKE ?)"
            s = f"%{search.strip()}%"
            params.extend([s, s, s, s, s, s])
            
        query += " ORDER BY p.tanggal DESC, p.id DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def get_pengiriman_detail_by_id(pengiriman_id: int) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT d.*, m.nama AS material_nama, m.satuan AS material_satuan, m.kode AS material_kode
        FROM pengiriman_detail d
        JOIN material m ON d.material_id = m.id
        WHERE d.pengiriman_id = ?
        ORDER BY m.nama ASC
        """, (pengiriman_id,))
        return [dict(row) for row in cursor.fetchall()]


# ==============================================================================
# PILAR 1: KEUANGAN - HUTANG & PEMBAYARAN SEMEN SUPPLIER
# ==============================================================================

def catat_order_semen(tanggal_order: str, tanggal_datang: str, jumlah_ton: float, 
                      harga_per_ton: float, supplier: str = "", no_order: str = "", 
                      keterangan: str = "", kategori_piutang: str = "kantor", material_id: Optional[int] = None,
                      jatuh_tempo: str = "") -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        total_harga = jumlah_ton * harga_per_ton
        clean_kat = "perusahaan" if str(kategori_piutang).strip().lower() == "perusahaan" else "kantor"
        
        actual_jt = str(jatuh_tempo or "").strip()
        if not actual_jt:
            try:
                base_dt = datetime.strptime(tanggal_datang or tanggal_order, "%Y-%m-%d")
                actual_jt = (base_dt + timedelta(days=14)).strftime("%Y-%m-%d")
            except Exception:
                actual_jt = tanggal_datang or tanggal_order

        cursor.execute("""
        INSERT INTO pembayaran_semen (no_order, supplier, tanggal_order, tanggal_datang, jumlah_ton, harga_per_ton, total_harga, keterangan, kategori_piutang, material_id, jatuh_tempo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (no_order.strip(), supplier.strip() or "Supplier Material", tanggal_order, tanggal_datang, jumlah_ton, harga_per_ton, total_harga, keterangan.strip(), clean_kat, material_id, actual_jt))
        conn.commit()
        return cursor.lastrowid

def catat_cicilan_semen(pembayaran_semen_id: Optional[int], tanggal: str, nominal: float, 
                        metode: str = "Transfer", keterangan: str = "") -> int:
    """Mencatat pembayaran semen ke supplier dan otomatis memotong Saldo Kas Plant"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO pembayaran_semen_cicilan (pembayaran_semen_id, tanggal, nominal, metode, keterangan)
        VALUES (?, ?, ?, ?, ?)
        """, (pembayaran_semen_id, tanggal, nominal, metode.strip(), keterangan.strip()))
        cicilan_id = cursor.lastrowid

        # Re-sync saldo kas
        recalculate_master_kas_balances(cursor)
        conn.commit()
        return cicilan_id

def hapus_order_semen(order_id: int) -> Tuple[bool, str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pembayaran_semen_cicilan WHERE pembayaran_semen_id = ?", (order_id,))
        cursor.execute("DELETE FROM pembayaran_semen WHERE id = ?", (order_id,))
        recalculate_master_kas_balances(cursor)
        conn.commit()
        return True, "Data order semen berhasil dihapus."

def hapus_cicilan_semen(cicilan_id: int) -> Tuple[bool, str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pembayaran_semen_cicilan WHERE id = ?", (cicilan_id,))
        recalculate_master_kas_balances(cursor)
        conn.commit()
        return True, "Data pembayaran semen berhasil dihapus dan saldo kas telah disesuaikan."

def get_pembayaran_semen_list(kategori_piutang: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
        SELECT 
            p.*,
            m.nama AS material_nama,
            m.kode AS material_kode,
            m.satuan AS material_satuan,
            COALESCE((SELECT SUM(c.nominal) FROM pembayaran_semen_cicilan c WHERE c.pembayaran_semen_id = p.id), 0) AS total_dibayar,
            (p.total_harga - COALESCE((SELECT SUM(c.nominal) FROM pembayaran_semen_cicilan c WHERE c.pembayaran_semen_id = p.id), 0)) AS sisa_hutang
        FROM pembayaran_semen p
        LEFT JOIN material m ON p.material_id = m.id
        WHERE 1=1
        """
        params = []
        if kategori_piutang and kategori_piutang.lower() in ("kantor", "perusahaan"):
            query += " AND LOWER(COALESCE(p.kategori_piutang, 'kantor')) = ?"
            params.append(kategori_piutang.lower())
        if search:
            query += " AND (p.no_order LIKE ? OR p.supplier LIKE ? OR p.keterangan LIKE ? OR m.nama LIKE ?)"
            s_term = f"%{search}%"
            params.extend([s_term, s_term, s_term, s_term])
        query += " ORDER BY p.tanggal_order DESC, p.id DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def get_cicilan_semen_list(order_id: Optional[int] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
        SELECT c.*, p.no_order, p.supplier, p.tanggal_order, p.jumlah_ton, p.kategori_piutang
        FROM pembayaran_semen_cicilan c
        LEFT JOIN pembayaran_semen p ON c.pembayaran_semen_id = p.id
        WHERE 1=1
        """
        params = []
        if order_id:
            query += " AND c.pembayaran_semen_id = ?"
            params.append(order_id)
        query += " ORDER BY c.tanggal DESC, c.id DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def get_ringkasan_hutang_semen(kategori_piutang: Optional[str] = None) -> Dict[str, float]:
    with get_connection() as conn:
        cursor = conn.cursor()
        where_clause = ""
        params = []
        if kategori_piutang and kategori_piutang.lower() in ("kantor", "perusahaan"):
            where_clause = " WHERE LOWER(COALESCE(kategori_piutang, 'kantor')) = ?"
            params.append(kategori_piutang.lower())

        cursor.execute(f"SELECT COALESCE(SUM(total_harga), 0) FROM pembayaran_semen{where_clause}", params)
        total_tagihan = cursor.fetchone()[0]

        if kategori_piutang and kategori_piutang.lower() in ("kantor", "perusahaan"):
            cursor.execute("""
            SELECT COALESCE(SUM(c.nominal), 0) 
            FROM pembayaran_semen_cicilan c
            JOIN pembayaran_semen p ON c.pembayaran_semen_id = p.id
            WHERE LOWER(COALESCE(p.kategori_piutang, 'kantor')) = ?
            """, params)
        else:
            cursor.execute("SELECT COALESCE(SUM(nominal), 0) FROM pembayaran_semen_cicilan")
        total_dibayar = cursor.fetchone()[0]

        return {
            "total_tagihan_semen": total_tagihan,
            "total_dibayar": total_dibayar,
            "sisa_hutang_semen": total_tagihan - total_dibayar
        }


# ==============================================================================
# PILAR 2: KEUANGAN - PIUTANG & PEMBAYARAN PROYEK KLIEN
# ==============================================================================

def catat_piutang_proyek_manual(proyek_id: int, tanggal: str, total_tagihan: float, 
                                no_surat_jalan: str = "", mutu_beton_kode: str = "", 
                                volume_m3: float = 0.0, harga_satuan_m3: float = 0.0, keterangan: str = "") -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO proyek_piutang (proyek_id, tanggal, no_surat_jalan, mutu_beton_kode, volume_m3, harga_satuan_m3, total_tagihan, keterangan)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (proyek_id, tanggal, no_surat_jalan.strip(), mutu_beton_kode.strip(), volume_m3, harga_satuan_m3, total_tagihan, keterangan.strip()))
        piutang_id = cursor.lastrowid
        conn.commit()
        return piutang_id

def catat_pembayaran_proyek(proyek_id: int, tanggal: str, nominal: float, 
                            metode: str = "Transfer Bank", nomor_bukti: str = "", keterangan: str = "") -> int:
    """Mencatat penerimaan pembayaran dari klien proyek dan otomatis menambah Saldo Kas Plant"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO proyek_pembayaran (proyek_id, tanggal, nominal, metode, nomor_bukti, keterangan)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (proyek_id, tanggal, nominal, metode.strip(), nomor_bukti.strip(), keterangan.strip()))
        bayar_id = cursor.lastrowid

        # Re-sync saldo kas
        recalculate_master_kas_balances(cursor)
        conn.commit()
        return bayar_id

def hapus_piutang_proyek(piutang_id: int) -> Tuple[bool, str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM proyek_piutang WHERE id = ?", (piutang_id,))
        conn.commit()
        return True, "Tagihan piutang proyek berhasil dihapus."

def hapus_pembayaran_proyek(pembayaran_id: int) -> Tuple[bool, str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM proyek_pembayaran WHERE id = ?", (pembayaran_id,))
        recalculate_master_kas_balances(cursor)
        conn.commit()
        return True, "Catatan pembayaran proyek berhasil dihapus dan saldo kas telah disesuaikan."

def get_proyek_piutang_list(proyek_id: Optional[int] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
        SELECT pi.*, p.nama AS proyek_nama, p.lokasi AS proyek_lokasi
        FROM proyek_piutang pi
        JOIN proyek p ON pi.proyek_id = p.id
        WHERE 1=1
        """
        params = []
        if proyek_id:
            query += " AND pi.proyek_id = ?"
            params.append(proyek_id)
        if start_date:
            query += " AND pi.tanggal >= ?"
            params.append(start_date)
        if end_date:
            query += " AND pi.tanggal <= ?"
            params.append(end_date)
            
        query += " ORDER BY pi.tanggal DESC, pi.id DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def get_proyek_pembayaran_list(proyek_id: Optional[int] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
        SELECT pb.*, p.nama AS proyek_nama, p.lokasi AS proyek_lokasi
        FROM proyek_pembayaran pb
        JOIN proyek p ON pb.proyek_id = p.id
        WHERE 1=1
        """
        params = []
        if proyek_id:
            query += " AND pb.proyek_id = ?"
            params.append(proyek_id)
        if start_date:
            query += " AND pb.tanggal >= ?"
            params.append(start_date)
        if end_date:
            query += " AND pb.tanggal <= ?"
            params.append(end_date)
            
        query += " ORDER BY pb.tanggal DESC, pb.id DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

# Aliases
get_piutang_by_proyek = get_proyek_piutang_list
get_pembayaran_by_proyek = get_proyek_pembayaran_list


def get_rekap_saldo_per_proyek(tipe_proyek: Optional[str] = None) -> List[Dict[str, Any]]:
    """Rekapitulasi total tagihan, pembayaran masuk, sisa piutang, dan volume cor per proyek.
    Filter opsional: tipe_proyek = 'dalam' | 'luar' | None (semua)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        params = []
        where_clause = ""
        if tipe_proyek and tipe_proyek in ("dalam", "luar"):
            where_clause = "WHERE p.tipe_proyek = ?"
            params.append(tipe_proyek)
        cursor.execute(f"""
        SELECT 
            p.id, p.nama, p.lokasi, p.status,
            COALESCE(p.tipe_proyek, 'luar') AS tipe_proyek,
            COALESCE((SELECT SUM(pg.volume_m3) FROM pengiriman pg WHERE pg.proyek_id = p.id), 0) AS total_volume_m3,
            COALESCE((SELECT SUM(pi.total_tagihan) FROM proyek_piutang pi WHERE pi.proyek_id = p.id), 0) AS total_tagihan,
            COALESCE((SELECT SUM(pb.nominal) FROM proyek_pembayaran pb WHERE pb.proyek_id = p.id), 0) AS total_bayar,
            (COALESCE((SELECT SUM(pi.total_tagihan) FROM proyek_piutang pi WHERE pi.proyek_id = p.id), 0) - 
             COALESCE((SELECT SUM(pb.nominal) FROM proyek_pembayaran pb WHERE pb.proyek_id = p.id), 0)) AS sisa_saldo_piutang
        FROM proyek p
        {where_clause}
        ORDER BY p.status ASC, p.nama ASC
        """, params)
        return [dict(row) for row in cursor.fetchall()]

def get_ringkasan_piutang_proyek() -> Dict[str, float]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(SUM(total_tagihan), 0) FROM proyek_piutang")
        total_tagihan = cursor.fetchone()[0]
        cursor.execute("SELECT COALESCE(SUM(nominal), 0) FROM proyek_pembayaran")
        total_bayar = cursor.fetchone()[0]
        return {
            "total_tagihan_proyek": total_tagihan,
            "total_terbayar": total_bayar,
            "sisa_piutang_proyek": total_tagihan - total_bayar
        }


# ==============================================================================
# PILAR 3: KEUANGAN - KAS KANTOR (PENGELUARAN HARIAN NON-SEMEN)
# ==============================================================================

def catat_kas_kantor(tanggal: str, nominal: Any = 0.0, kategori: str = "Operasional", 
                     nomor_nota: str = "", penerima_toko: str = "", 
                     keterangan: str = "", lampiran_foto: str = "",
                     kendaraan_id: Optional[int] = None,
                     driver: Optional[str] = None,
                     proyek_id: Optional[int] = None,
                     pengiriman_id: Optional[int] = None) -> int:
    """Mencatat nota pengeluaran operasional harian kantor / kendaraan & otomatis memotong Saldo Kas Plant"""
    if isinstance(nominal, str) and isinstance(nomor_nota, (int, float)):
        # Signature: (tanggal, nomor_nota, kategori, nominal, penerima_toko, keterangan, lampiran_foto)
        actual_nota = str(nominal).strip()
        actual_kategori = str(kategori).strip()
        actual_nominal = float(nomor_nota)
        actual_penerima = str(penerima_toko).strip()
        actual_ket = str(keterangan).strip()
        actual_foto = str(lampiran_foto).strip()
    else:
        actual_nominal = float(nominal or 0)
        actual_kategori = str(kategori or "").strip()
        actual_nota = str(nomor_nota or "").strip()
        actual_penerima = str(penerima_toko or "").strip()
        actual_ket = str(keterangan or "").strip()
        actual_foto = str(lampiran_foto or "").strip()

    actual_driver = str(driver).strip() if driver else None

    with get_connection() as conn:
        cursor = conn.cursor()
        if not actual_driver and kendaraan_id:
            cursor.execute("SELECT driver_default FROM kendaraan WHERE id = ?", (kendaraan_id,))
            row_k = cursor.fetchone()
            if row_k and row_k[0]:
                actual_driver = str(row_k[0]).strip()

        cursor.execute("""
        INSERT INTO kas_kantor (tanggal, nomor_nota, kategori, nominal, penerima_toko, keterangan, lampiran_foto, kendaraan_id, driver, proyek_id, pengiriman_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tanggal, actual_nota, actual_kategori, actual_nominal, actual_penerima, actual_ket, actual_foto, kendaraan_id, actual_driver, proyek_id, pengiriman_id))
        kk_id = cursor.lastrowid

        if pengiriman_id:
            cursor.execute("UPDATE pengiriman SET status_bbm = 'Sudah Diisi' WHERE id = ?", (pengiriman_id,))

        # Re-sync saldo kas
        recalculate_master_kas_balances(cursor)
        conn.commit()
        return kk_id

def update_kas_kantor(kas_kantor_id: int, tanggal: str, nominal: float, kategori: str = "Operasional",
                      nomor_nota: str = "", penerima_toko: str = "", keterangan: str = "",
                      lampiran_foto: str = "", kendaraan_id: Optional[int] = None,
                      driver: Optional[str] = None, proyek_id: Optional[int] = None,
                      pengiriman_id: Optional[int] = None) -> bool:
    """Memperbarui data pengeluaran kas kantor / kendaraan"""
    with get_connection() as conn:
        cursor = conn.cursor()
        actual_driver = str(driver).strip() if driver else None
        if not actual_driver and kendaraan_id:
            cursor.execute("SELECT driver_default FROM kendaraan WHERE id = ?", (kendaraan_id,))
            row_k = cursor.fetchone()
            if row_k and row_k[0]:
                actual_driver = str(row_k[0]).strip()

        cursor.execute("""
        UPDATE kas_kantor
        SET tanggal = ?, nomor_nota = ?, kategori = ?, nominal = ?, penerima_toko = ?, keterangan = ?, lampiran_foto = ?, kendaraan_id = ?, driver = ?, proyek_id = ?, pengiriman_id = ?
        WHERE id = ?
        """, (tanggal, nomor_nota.strip(), kategori.strip(), float(nominal or 0), penerima_toko.strip(), keterangan.strip(), lampiran_foto.strip(), kendaraan_id, actual_driver, proyek_id, pengiriman_id, kas_kantor_id))
        
        if pengiriman_id:
            cursor.execute("UPDATE pengiriman SET status_bbm = 'Sudah Diisi' WHERE id = ?", (pengiriman_id,))

        recalculate_master_kas_balances(cursor)
        conn.commit()
        return cursor.rowcount > 0

def hapus_kas_kantor(kas_kantor_id: int) -> Tuple[bool, str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        # Ambil pengiriman_id jika ada sebelum dihapus
        cursor.execute("SELECT pengiriman_id FROM kas_kantor WHERE id = ?", (kas_kantor_id,))
        row_kk = cursor.fetchone()
        p_id = row_kk[0] if (row_kk and row_kk[0]) else None

        cursor.execute("DELETE FROM kas_kantor WHERE id = ?", (kas_kantor_id,))

        if p_id:
            # Cek apakah ada kas_kantor lain yang masih merujuk ke pengiriman ini
            cursor.execute("SELECT COUNT(*) FROM kas_kantor WHERE pengiriman_id = ?", (p_id,))
            cnt = cursor.fetchone()[0]
            if cnt == 0:
                cursor.execute("UPDATE pengiriman SET status_bbm = 'Belum Diisi' WHERE id = ?", (p_id,))

        recalculate_master_kas_balances(cursor)
        conn.commit()
        return True, "Data pengeluaran kas kantor berhasil dihapus dan saldo kas telah disesuaikan."

def get_kas_kantor_list(start_date: Optional[str] = None, end_date: Optional[str] = None, kategori: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
        SELECT kk.*, k.no_plat, k.nama_kendaraan, k.jenis_kendaraan
        FROM kas_kantor kk
        LEFT JOIN kendaraan k ON kk.kendaraan_id = k.id
        WHERE 1=1
        """
        params = []
        if start_date:
            query += " AND kk.tanggal >= ?"
            params.append(start_date)
        if end_date:
            query += " AND kk.tanggal <= ?"
            params.append(end_date)
        if kategori and kategori != "Semua Kategori":
            query += " AND kk.kategori = ?"
            params.append(kategori)
            
        query += " ORDER BY kk.tanggal DESC, kk.id DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def get_biaya_kendaraan_list(kendaraan_id: Optional[int] = None,
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None,
                             kategori: Optional[str] = None,
                             search: Optional[str] = None,
                             driver: Optional[str] = None,
                             proyek_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Mengambil riwayat pengeluaran operasional kendaraan lengkap dengan driver & proyek"""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
        SELECT kk.*, k.no_plat, k.nama_kendaraan, k.jenis_kendaraan,
               COALESCE(NULLIF(kk.driver, ''), k.driver_default, '-') AS driver_nama,
               p.nama AS proyek_nama,
               pg.no_surat_jalan
        FROM kas_kantor kk
        LEFT JOIN kendaraan k ON kk.kendaraan_id = k.id
        LEFT JOIN proyek p ON kk.proyek_id = p.id
        LEFT JOIN pengiriman pg ON kk.pengiriman_id = pg.id
        WHERE kk.kendaraan_id IS NOT NULL
        """
        params = []
        if kendaraan_id and kendaraan_id != -1:
            query += " AND kk.kendaraan_id = ?"
            params.append(kendaraan_id)
        if start_date:
            query += " AND kk.tanggal >= ?"
            params.append(start_date)
        if end_date:
            query += " AND kk.tanggal <= ?"
            params.append(end_date)
        if kategori and kategori != "Semua Kategori":
            query += " AND kk.kategori = ?"
            params.append(kategori)
        if driver and driver != "Semua Driver":
            query += " AND (kk.driver = ? OR (kk.driver IS NULL AND k.driver_default = ?))"
            params.extend([driver, driver])
        if proyek_id and proyek_id != -1:
            query += " AND kk.proyek_id = ?"
            params.append(proyek_id)
        if search:
            query += " AND (kk.nomor_nota LIKE ? OR kk.penerima_toko LIKE ? OR kk.keterangan LIKE ? OR k.no_plat LIKE ? OR k.nama_kendaraan LIKE ? OR kk.driver LIKE ? OR k.driver_default LIKE ? OR pg.no_surat_jalan LIKE ?)"
            s_val = f"%{search}%"
            params.extend([s_val, s_val, s_val, s_val, s_val, s_val, s_val, s_val])
            
        query += " ORDER BY kk.tanggal DESC, kk.id DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def get_biaya_kendaraan_by_id(biaya_id: int) -> Optional[Dict[str, Any]]:
    """Mengambil rincian detail 1 transaksi biaya operasional kendaraan"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT kk.*, k.no_plat, k.nama_kendaraan, k.jenis_kendaraan, k.kapasitas_m3, k.status AS status_kendaraan,
               COALESCE(NULLIF(kk.driver, ''), k.driver_default, '-') AS driver_nama,
               p.nama AS proyek_nama, p.lokasi AS proyek_lokasi,
               pg.no_surat_jalan, pg.volume_m3 AS pengiriman_volume, pg.tujuan_pengiriman AS pengiriman_tujuan
        FROM kas_kantor kk
        LEFT JOIN kendaraan k ON kk.kendaraan_id = k.id
        LEFT JOIN proyek p ON kk.proyek_id = p.id
        LEFT JOIN pengiriman pg ON kk.pengiriman_id = pg.id
        WHERE kk.id = ?
        """, (biaya_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_pengiriman_pending_bbm(kendaraan_id: Optional[int] = None, no_plat: Optional[str] = None) -> List[Dict[str, Any]]:
    """Mengambil daftar pengiriman cor yang status_bbm bernilai 'Belum Diisi'"""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
        SELECT p.id, p.tanggal, p.no_surat_jalan, p.volume_m3, p.no_plat_truk, p.driver, p.tujuan_pengiriman,
               p.proyek_id, pr.nama AS proyek_nama
        FROM pengiriman p
        LEFT JOIN proyek pr ON p.proyek_id = pr.id
        WHERE (p.status_bbm IS NULL OR p.status_bbm = 'Belum Diisi')
        """
        params = []
        if kendaraan_id:
            query += " AND (p.kendaraan_id = ? OR p.no_plat_truk IN (SELECT no_plat FROM kendaraan WHERE id = ?))"
            params.extend([kendaraan_id, kendaraan_id])
        elif no_plat:
            query += " AND p.no_plat_truk = ?"
            params.append(no_plat)
            
        query += " ORDER BY p.tanggal DESC, p.id DESC LIMIT 50"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def get_biaya_by_pengiriman_id(pengiriman_id: int) -> Optional[Dict[str, Any]]:
    """Mengambil transaksi biaya kas kantor yang tertaut ke suatu pengiriman_id"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM kas_kantor WHERE pengiriman_id = ? ORDER BY id DESC LIMIT 1", (pengiriman_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_status_bbm_pengiriman(pengiriman_id: int, status_bbm: str) -> bool:
    """Mengubah status BBM pengiriman (Belum Diisi, Sudah Diisi, Tangki Cukup)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE pengiriman SET status_bbm = ? WHERE id = ?", (status_bbm, pengiriman_id))
        conn.commit()
        return cursor.rowcount > 0

def get_all_drivers() -> List[str]:
    """Mendapatkan daftar semua nama driver/supir unik dari armada dan transaksi operasional"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT DISTINCT TRIM(driver_default) AS d_name FROM kendaraan WHERE driver_default IS NOT NULL AND TRIM(driver_default) != ''
        UNION
        SELECT DISTINCT TRIM(driver) AS d_name FROM kas_kantor WHERE driver IS NOT NULL AND TRIM(driver) != ''
        ORDER BY d_name ASC
        """)
        return [row[0] for row in cursor.fetchall() if row[0]]

def get_rekap_biaya_per_kendaraan(start_date: Optional[str] = None, 
                                  end_date: Optional[str] = None,
                                  jenis_kendaraan: Optional[str] = None,
                                  search: Optional[str] = None) -> List[Dict[str, Any]]:
    """Rekapitulasi total biaya operasional per armada (BBM, Servis, Lain-lain, dan Frekuensi)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        conds = []
        params = []
        if start_date:
            conds.append("kk.tanggal >= ?")
            params.append(start_date)
        if end_date:
            conds.append("kk.tanggal <= ?")
            params.append(end_date)
        where_join = (" AND " + " AND ".join(conds)) if conds else ""
        
        query = f"""
        SELECT 
            k.id AS kendaraan_id,
            k.no_plat,
            k.nama_kendaraan,
            k.jenis_kendaraan,
            k.status,
            k.driver_default,
            COALESCE(SUM(kk.nominal), 0) AS total_biaya,
            COALESCE(SUM(CASE WHEN kk.kategori LIKE '%BBM%' OR kk.kategori LIKE '%Solar%' THEN kk.nominal ELSE 0 END), 0) AS total_bbm,
            COALESCE(SUM(CASE WHEN kk.kategori LIKE '%Servis%' OR kk.kategori LIKE '%Bengkel%' OR kk.kategori LIKE '%Sparepart%' OR kk.kategori LIKE '%Oli%' THEN kk.nominal ELSE 0 END), 0) AS total_servis,
            COALESCE(SUM(CASE WHEN kk.kategori NOT LIKE '%BBM%' AND kk.kategori NOT LIKE '%Solar%' AND kk.kategori NOT LIKE '%Servis%' AND kk.kategori NOT LIKE '%Bengkel%' AND kk.kategori NOT LIKE '%Sparepart%' AND kk.kategori NOT LIKE '%Oli%' AND kk.nominal IS NOT NULL THEN kk.nominal ELSE 0 END), 0) AS total_lainnya,
            COUNT(kk.id) AS frekuensi_transaksi
        FROM kendaraan k
        LEFT JOIN kas_kantor kk ON k.id = kk.kendaraan_id {where_join}
        WHERE 1=1
        """
        k_params = []
        if jenis_kendaraan and jenis_kendaraan != "Semua Jenis":
            query += " AND k.jenis_kendaraan = ?"
            k_params.append(jenis_kendaraan)
        if search:
            query += " AND (k.no_plat LIKE ? OR k.nama_kendaraan LIKE ? OR k.driver_default LIKE ?)"
            s_val = f"%{search}%"
            k_params.extend([s_val, s_val, s_val])
            
        query += " GROUP BY k.id ORDER BY total_biaya DESC, k.nama_kendaraan ASC"
        cursor.execute(query, params + k_params)
        return [dict(row) for row in cursor.fetchall()]

def get_stat_keuangan_kendaraan() -> Dict[str, Any]:
    """Ringkasan KPI keuangan operasional armada"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cur_month = datetime.now().strftime("%Y-%m")
        
        cursor.execute("""
        SELECT 
            COALESCE(SUM(nominal), 0) AS total_bulan_ini,
            COALESCE(SUM(CASE WHEN kategori LIKE '%BBM%' OR kategori LIKE '%Solar%' THEN nominal ELSE 0 END), 0) AS bbm_bulan_ini,
            COALESCE(SUM(CASE WHEN kategori LIKE '%Servis%' OR kategori LIKE '%Bengkel%' OR kategori LIKE '%Sparepart%' OR kategori LIKE '%Oli%' THEN nominal ELSE 0 END), 0) AS servis_bulan_ini,
            COALESCE(SUM(CASE WHEN kategori NOT LIKE '%BBM%' AND kategori NOT LIKE '%Solar%' AND kategori NOT LIKE '%Servis%' AND kategori NOT LIKE '%Bengkel%' AND kategori NOT LIKE '%Sparepart%' AND kategori NOT LIKE '%Oli%' THEN nominal ELSE 0 END), 0) AS lainnya_bulan_ini,
            COUNT(id) AS jumlah_transaksi
        FROM kas_kantor
        WHERE kendaraan_id IS NOT NULL AND strftime('%Y-%m', tanggal) = ?
        """, (cur_month,))
        row = cursor.fetchone()
        
        cursor.execute("SELECT COALESCE(SUM(nominal), 0) FROM kas_kantor WHERE kendaraan_id IS NOT NULL")
        total_all = cursor.fetchone()[0]
        
        return {
            "total_bulan_ini": float(row["total_bulan_ini"] or 0) if row else 0.0,
            "bbm_bulan_ini": float(row["bbm_bulan_ini"] or 0) if row else 0.0,
            "servis_bulan_ini": float(row["servis_bulan_ini"] or 0) if row else 0.0,
            "lainnya_bulan_ini": float(row["lainnya_bulan_ini"] or 0) if row else 0.0,
            "jumlah_transaksi": int(row["jumlah_transaksi"] or 0) if row else 0,
            "total_all_time": float(total_all or 0)
        }

def get_ringkasan_kas_kantor() -> Dict[str, float]:
    with get_connection() as conn:
        cursor = conn.cursor()
        month_prefix = datetime.now().strftime("%Y-%m")
        cursor.execute("SELECT COALESCE(SUM(nominal), 0) FROM kas_kantor")
        total_semua = cursor.fetchone()[0]
        cursor.execute("SELECT COALESCE(SUM(nominal), 0) FROM kas_kantor WHERE tanggal LIKE ?", (f"{month_prefix}%",))
        total_bulan = cursor.fetchone()[0]
        return {
            "total_kas_kantor": total_semua,
            "total_kas_kantor_bulan_ini": total_bulan
        }


# ==============================================================================
# PILAR 4: KEUANGAN - GAJI KARYAWAN (PAYROLL PEKERJA)
# ==============================================================================

def catat_gaji_karyawan(tanggal_bayar: str, periode_gaji: str, nama_karyawan: str, 
                        nominal_gaji: float, jabatan: str = "", potongan_tunjangan: float = 0.0, 
                        metode_bayar: str = "Tunai", keterangan: str = "") -> int:
    """Mencatat pembayaran gaji karyawan dan otomatis memotong Saldo Kas Plant"""
    total_dibayar = nominal_gaji + potongan_tunjangan
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO gaji_karyawan (
            tanggal_bayar, periode_gaji, nama_karyawan, jabatan, nominal_gaji, 
            potongan_tunjangan, total_dibayar, metode_bayar, keterangan
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tanggal_bayar, periode_gaji.strip(), nama_karyawan.strip(), jabatan.strip(), nominal_gaji,
              potongan_tunjangan, total_dibayar, metode_bayar.strip(), keterangan.strip()))
        gaji_id = cursor.lastrowid

        # Re-sync saldo kas
        recalculate_master_kas_balances(cursor)
        conn.commit()
        return gaji_id

def hapus_gaji_karyawan(gaji_id: int) -> Tuple[bool, str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM gaji_karyawan WHERE id = ?", (gaji_id,))
        recalculate_master_kas_balances(cursor)
        conn.commit()
        return True, "Data pembayaran gaji karyawan berhasil dihapus dan saldo kas telah disesuaikan."

def get_gaji_karyawan_list(start_date: Optional[str] = None, end_date: Optional[str] = None, periode: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM gaji_karyawan WHERE 1=1"
        params = []
        if start_date:
            query += " AND tanggal_bayar >= ?"
            params.append(start_date)
        if end_date:
            query += " AND tanggal_bayar <= ?"
            params.append(end_date)
        if periode:
            query += " AND periode_gaji LIKE ?"
            params.append(f"%{periode.strip()}%")
            
        query += " ORDER BY tanggal_bayar DESC, id DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def get_ringkasan_gaji_karyawan() -> Dict[str, float]:
    with get_connection() as conn:
        cursor = conn.cursor()
        month_prefix = datetime.now().strftime("%Y-%m")
        cursor.execute("SELECT COALESCE(SUM(total_dibayar), 0) FROM gaji_karyawan")
        total_semua = cursor.fetchone()[0]
        cursor.execute("SELECT COALESCE(SUM(total_dibayar), 0) FROM gaji_karyawan WHERE tanggal_bayar LIKE ?", (f"{month_prefix}%",))
        total_bulan = cursor.fetchone()[0]
        return {
            "total_gaji": total_semua,
            "total_gaji_bulan_ini": total_bulan
        }

# Convenience Aliases
save_kas_kantor = catat_kas_kantor
delete_kas_kantor = hapus_kas_kantor
save_gaji_karyawan = catat_gaji_karyawan
delete_gaji_karyawan = hapus_gaji_karyawan

# BUKU KAS UTAMA & SALDO KAS TERPADU (SINGLE SOURCE OF TRUTH)
# ==============================================================================

def catat_kas_manual(tanggal: str, keterangan: str, masuk: float, keluar: float, kategori: str = "Modal Awal") -> int:
    """Mencatat modal awal kas atau kas masuk/keluar khusus lainnya"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO saldo_kas (tanggal, keterangan, saldo_masuk, saldo_keluar, total_saldo, kategori, referensi_tipe, referensi_id)
        VALUES (?, ?, ?, ?, 0, ?, 'manual', NULL)
        """, (tanggal, keterangan.strip(), masuk, keluar, kategori.strip()))
        k_id = cursor.lastrowid
        recalculate_master_kas_balances(cursor)
        conn.commit()
        return k_id

def recalculate_master_kas_balances(cursor):
    """
    Logika Penjaga Konsistensi Saldo Kas (Anti Selisih).
    Mengumpulkan seluruh mutasi riil dari 4 Pilar:
    1. (+) Pembayaran Proyek (proyek_pembayaran)
    2. (+) Modal Awal / Kas Manual Masuk (saldo_kas where referensi_tipe = 'manual' or null)
    3. (-) Pembayaran Cicilan Semen (pembayaran_semen_cicilan)
    4. (-) Pengeluaran Kas Kantor (kas_kantor)
    5. (-) Pembayaran Gaji Karyawan (gaji_karyawan)
    Lalu menyusun Buku Kas Umum secara kronologis tanggal dan menghitung running balance.
    """
    # 1. Ambil seluruh transaksi manual/modal
    cursor.execute("SELECT id, tanggal, keterangan, saldo_masuk, saldo_keluar, kategori FROM saldo_kas WHERE referensi_tipe = 'manual' OR (referensi_tipe IS NULL AND kategori IN ('Modal', 'Modal Awal', 'Kas Masuk Lain'))")
    manual_entries = cursor.fetchall()
    
    # 2. Hapus entri turunan otomatis lama dari saldo_kas
    cursor.execute("DELETE FROM saldo_kas WHERE referensi_tipe IN ('proyek_bayar', 'semen_bayar', 'kas_kantor', 'gaji')")
    
    # 3. Masukkan kembali mutasi dari Pembayaran Proyek
    cursor.execute("""
    SELECT pb.id, pb.tanggal, pb.nominal, pb.metode, pb.keterangan, p.nama AS proyek_nama 
    FROM proyek_pembayaran pb
    JOIN proyek p ON pb.proyek_id = p.id
    """)
    for pb in cursor.fetchall():
        ket = f"Penerimaan Pembayaran {pb['proyek_nama']} ({pb['metode']})"
        if pb["keterangan"]: ket += f" - {pb['keterangan']}"
        cursor.execute("""
        INSERT INTO saldo_kas (tanggal, keterangan, saldo_masuk, saldo_keluar, total_saldo, kategori, referensi_tipe, referensi_id)
        VALUES (?, ?, ?, 0, 0, 'Pembayaran Proyek', 'proyek_bayar', ?)
        """, (pb["tanggal"], ket, pb["nominal"], pb["id"]))

    # 4. Masukkan kembali mutasi dari Pembayaran Semen
    cursor.execute("""
    SELECT c.id, c.tanggal, c.nominal, c.metode, c.keterangan, p.supplier, p.no_order
    FROM pembayaran_semen_cicilan c
    LEFT JOIN pembayaran_semen p ON c.pembayaran_semen_id = p.id
    """)
    for sc in cursor.fetchall():
        ket = f"Pembayaran Semen {sc['supplier'] or 'Supplier'} ({sc['no_order'] or 'DO'}) via {sc['metode']}"
        if sc["keterangan"]: ket += f" - {sc['keterangan']}"
        cursor.execute("""
        INSERT INTO saldo_kas (tanggal, keterangan, saldo_masuk, saldo_keluar, total_saldo, kategori, referensi_tipe, referensi_id)
        VALUES (?, ?, 0, ?, 0, 'Pembayaran Semen', 'semen_bayar', ?)
        """, (sc["tanggal"], ket, sc["nominal"], sc["id"]))

    # 5. Masukkan kembali mutasi dari Kas Kantor & Operasional Kendaraan
    cursor.execute("""
    SELECT kk.id, kk.tanggal, kk.nomor_nota, kk.kategori, kk.nominal, kk.penerima_toko, kk.keterangan, kk.kendaraan_id,
           k.no_plat, k.nama_kendaraan
    FROM kas_kantor kk
    LEFT JOIN kendaraan k ON kk.kendaraan_id = k.id
    """)
    for kk in cursor.fetchall():
        is_kendaraan = (kk["kendaraan_id"] is not None) or any(
            w in str(kk["kategori"]).lower() 
            for w in ["bbm", "solar", "servis", "bengkel", "sparepart", "ban", "uang jalan", "kir", "mobil", "truk", "cuci & kebersihan"]
        )
        if is_kendaraan:
            kategori_saldo = "Operasional Kendaraan"
            plat_str = f" [{kk['no_plat']}]" if kk["no_plat"] else ""
            ket = f"Operasional Kendaraan{plat_str} ({kk['kategori']}): {kk['keterangan'] or kk['penerima_toko'] or 'Nota'}"
        else:
            kategori_saldo = "Kas Kantor"
            ket = f"Kas Kantor [{kk['kategori']}]: {kk['keterangan'] or kk['penerima_toko'] or 'Nota'}"

        if kk["nomor_nota"]: ket += f" (Nota #{kk['nomor_nota']})"
        cursor.execute("""
        INSERT INTO saldo_kas (tanggal, keterangan, saldo_masuk, saldo_keluar, total_saldo, kategori, referensi_tipe, referensi_id)
        VALUES (?, ?, 0, ?, 0, ?, 'kas_kantor', ?)
        """, (kk["tanggal"], ket, kk["nominal"], kategori_saldo, kk["id"]))

    # 6. Masukkan kembali mutasi dari Gaji Karyawan
    cursor.execute("SELECT id, tanggal_bayar, periode_gaji, nama_karyawan, jabatan, total_dibayar, keterangan FROM gaji_karyawan")
    for gj in cursor.fetchall():
        ket = f"Gaji {gj['nama_karyawan']} ({gj['jabatan'] or 'Karyawan'}) - Periode {gj['periode_gaji']}"
        cursor.execute("""
        INSERT INTO saldo_kas (tanggal, keterangan, saldo_masuk, saldo_keluar, total_saldo, kategori, referensi_tipe, referensi_id)
        VALUES (?, ?, 0, ?, 0, 'Gaji Karyawan', 'gaji', ?)
        """, (gj["tanggal_bayar"], ket, gj["total_dibayar"], gj["id"]))

    # 7. Urutkan seluruh saldo_kas dan hitung total_saldo running balance
    cursor.execute("SELECT id, saldo_masuk, saldo_keluar FROM saldo_kas ORDER BY tanggal ASC, id ASC")
    all_rows = cursor.fetchall()
    running = 0.0
    for r in all_rows:
        running += (float(r["saldo_masuk"] or 0) - float(r["saldo_keluar"] or 0))
        cursor.execute("UPDATE saldo_kas SET total_saldo = ? WHERE id = ?", (running, r["id"]))

def catat_kas(tanggal: str, keterangan: str, masuk: float, keluar: float, kategori: str = "Operasional") -> int:
    """Wrapper kompatibilitas catat_kas"""
    return catat_kas_manual(tanggal, keterangan, masuk, keluar, kategori)

def hapus_kas(kas_id: int) -> Tuple[bool, str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT referensi_tipe, referensi_id FROM saldo_kas WHERE id = ?", (kas_id,))
        row = cursor.fetchone()
        if not row:
            return False, "Data transaksi kas tidak ditemukan."
            
        ref_type = row["referensi_tipe"]
        ref_id = row["referensi_id"]

        if ref_type == "proyek_bayar" and ref_id:
            cursor.execute("DELETE FROM proyek_pembayaran WHERE id = ?", (ref_id,))
        elif ref_type == "semen_bayar" and ref_id:
            cursor.execute("DELETE FROM pembayaran_semen_cicilan WHERE id = ?", (ref_id,))
        elif ref_type == "kas_kantor" and ref_id:
            cursor.execute("DELETE FROM kas_kantor WHERE id = ?", (ref_id,))
        elif ref_type == "gaji" and ref_id:
            cursor.execute("DELETE FROM gaji_karyawan WHERE id = ?", (ref_id,))
        else:
            cursor.execute("DELETE FROM saldo_kas WHERE id = ?", (kas_id,))

        recalculate_master_kas_balances(cursor)
        conn.commit()
        return True, "Transaksi kas berhasil dihapus dan seluruh saldo berjalan telah dihitung ulang."

def get_saldo_kas(start_date: Optional[str] = None, end_date: Optional[str] = None, search: Optional[str] = None, kategori: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM saldo_kas WHERE 1=1"
        params = []
        if start_date:
            query += " AND tanggal >= ?"
            params.append(start_date)
        if end_date:
            query += " AND tanggal <= ?"
            params.append(end_date)
        if kategori and kategori != "Semua Kategori":
            query += " AND kategori = ?"
            params.append(kategori)
        if search:
            query += " AND (keterangan LIKE ? OR kategori LIKE ?)"
            s = f"%{search.strip()}%"
            params.extend([s, s])
            
        query += " ORDER BY tanggal DESC, id DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def get_ringkasan_kas(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, float]:
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Total Saldo Kas Aktif Saat Ini (Seluruh Waktu)
        cursor.execute("SELECT total_saldo FROM saldo_kas ORDER BY tanggal DESC, id DESC LIMIT 1")
        last_row = cursor.fetchone()
        saldo_akhir = last_row["total_saldo"] if last_row else 0.0

        # Rincian 4 Pilar
        cursor.execute("SELECT COALESCE(SUM(nominal), 0) FROM proyek_pembayaran")
        total_in_proyek = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(nominal), 0) FROM pembayaran_semen_cicilan")
        total_out_semen = cursor.fetchone()[0]

        # Rincian Operasional Kendaraan vs Kas Kantor Murni
        cursor.execute("""
        SELECT COALESCE(SUM(nominal), 0) FROM kas_kantor 
        WHERE kendaraan_id IS NOT NULL 
           OR LOWER(kategori) LIKE '%bbm%' 
           OR LOWER(kategori) LIKE '%solar%'
           OR LOWER(kategori) LIKE '%servis%'
           OR LOWER(kategori) LIKE '%bengkel%'
           OR LOWER(kategori) LIKE '%sparepart%'
           OR LOWER(kategori) LIKE '%ban%'
           OR LOWER(kategori) LIKE '%uang jalan%'
        """)
        total_out_kendaraan = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(nominal), 0) FROM kas_kantor")
        total_out_kantor = cursor.fetchone()[0]
        total_out_kantor_murni = max(0.0, total_out_kantor - total_out_kendaraan)

        cursor.execute("SELECT COALESCE(SUM(total_dibayar), 0) FROM gaji_karyawan")
        total_out_gaji = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(saldo_masuk), 0) FROM saldo_kas WHERE kategori IN ('Modal', 'Modal Awal', 'Kas Masuk Lain')")
        total_in_modal = cursor.fetchone()[0]

        # Rincian Periode (jika ada filter)
        query_in = "SELECT COALESCE(SUM(saldo_masuk), 0) FROM saldo_kas WHERE 1=1"
        query_out = "SELECT COALESCE(SUM(saldo_keluar), 0) FROM saldo_kas WHERE 1=1"
        params = []
        if start_date:
            query_in += " AND tanggal >= ?"
            query_out += " AND tanggal >= ?"
            params.append(start_date)
        if end_date:
            query_in += " AND tanggal <= ?"
            query_out += " AND tanggal <= ?"
            params.append(end_date)
            
        cursor.execute(query_in, params)
        periode_masuk = cursor.fetchone()[0]
        cursor.execute(query_out, params)
        periode_keluar = cursor.fetchone()[0]

        return {
            "saldo_akhir": saldo_akhir,
            "total_in_proyek": total_in_proyek,
            "total_out_semen": total_out_semen,
            "total_out_kantor": total_out_kantor,
            "total_out_kantor_murni": total_out_kantor_murni,
            "total_out_kendaraan": total_out_kendaraan,
            "total_out_gaji": total_out_gaji,
            "total_in_modal": total_in_modal,
            "periode_masuk": periode_masuk,
            "periode_keluar": periode_keluar,
            "periode_selisih": periode_masuk - periode_keluar
        }


# ==============================================================================
# DASHBOARD STATS & REKAP
# ==============================================================================

def get_dashboard_data(user_id: Optional[int] = None) -> Dict[str, Any]:
    """Mengumpulkan seluruh metrik KPI untuk Dashboard Operasional Modern"""
    with get_connection() as conn:
        cursor = conn.cursor()
        today_dt = datetime.now()
        today_str = today_dt.strftime("%Y-%m-%d")
        month_prefix = today_dt.strftime("%Y-%m")

        # 1. Stok Material
        cursor.execute("SELECT id, kode, nama, satuan, stok_saat_ini, stok_minimum, harga_beli_terbaru FROM material ORDER BY id ASC")
        stok_materials = [dict(r) for r in cursor.fetchall()]

        # Jika user_id diberikan, gunakan stok individual per user dari user_material_stok
        if user_id:
            cursor.execute("SELECT material_id, stok_saat_ini FROM user_material_stok WHERE user_id = ?", (user_id,))
            user_stoks = {r["material_id"]: float(r["stok_saat_ini"] or 0) for r in cursor.fetchall()}
            for m in stok_materials:
                if m["id"] in user_stoks:
                    m["stok_saat_ini"] = user_stoks[m["id"]]

        # Hitung kapasitas acuan, persentase & status untuk visualisasi progress bar
        for m in stok_materials:
            stk = float(m["stok_saat_ini"] or 0)
            min_stk = float(m["stok_minimum"] or 0)
            
            # Acuan kapasitas normal:
            if min_stk > 0:
                kapasitas = max(min_stk, stk) if stk > min_stk else min_stk
            else:
                kapasitas = max(stk, 1000.0)
            m["kapasitas"] = kapasitas
            
            if kapasitas > 0:
                pct = int(round((stk / kapasitas) * 100))
                m["persentase"] = max(0, min(100, pct))
            else:
                m["persentase"] = 100
            
            # Status: Kritis vs Aman
            if stk <= min_stk or stk < 0:
                m["status_kategori"] = "Kritis"
            else:
                m["status_kategori"] = "Aman"

        # 2. Volume Cor Hari Ini & Bulan Ini
        cursor.execute("SELECT COALESCE(SUM(volume_m3), 0) FROM pengiriman WHERE tanggal = ?", (today_str,))
        vol_today = float(cursor.fetchone()[0] or 0)

        cursor.execute("SELECT COALESCE(SUM(volume_m3), 0) FROM pengiriman WHERE tanggal LIKE ?", (f"{month_prefix}%",))
        vol_month = float(cursor.fetchone()[0] or 0)

        # Target Hari Ini (default 10 m³ atau dari target harian)
        target_today = 10.0
        target_pct = int(min(100, (vol_today / target_today) * 100)) if target_today > 0 else 0

        # Pertumbuhan Bulan Lalu
        first_this_month = today_dt.replace(day=1)
        prev_month_dt = first_this_month - timedelta(days=1)
        prev_month_prefix = prev_month_dt.strftime("%Y-%m")
        cursor.execute("SELECT COALESCE(SUM(volume_m3), 0) FROM pengiriman WHERE tanggal LIKE ?", (f"{prev_month_prefix}%",))
        vol_prev_month = float(cursor.fetchone()[0] or 0)
        if vol_prev_month > 0:
            vol_growth_pct = round(((vol_month - vol_prev_month) / vol_prev_month) * 100.0, 1)
        else:
            vol_growth_pct = 12.0 if vol_month > 0 else 0.0

        # 3. Pengiriman Hari Ini (Truk selesai vs dalam proses)
        cursor.execute("""
        SELECT p.id, p.no_plat_truk, k.status AS k_status
        FROM pengiriman p
        LEFT JOIN kendaraan k ON (p.kendaraan_id = k.id OR UPPER(p.no_plat_truk) = UPPER(k.no_plat))
        WHERE p.tanggal = ?
        """, (today_str,))
        today_ships = cursor.fetchall()
        count_ships_today = len(today_ships)
        ships_proses = sum(1 for s in today_ships if (s["k_status"] == "operasional"))
        ships_selesai = count_ships_today - ships_proses

        # 4. Kendaraan Aktif (Operasional vs Standby)
        cursor.execute("SELECT COUNT(*) FROM kendaraan WHERE status = 'operasional'")
        kend_perjalanan = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM kendaraan WHERE status = 'tersedia'")
        kend_standby = cursor.fetchone()[0]
        kend_aktif = kend_perjalanan + kend_standby

        # 5. Saldo Kas & Ringkasan 4 Pilar
        kas_summary = get_ringkasan_kas()
        piutang_summary = get_ringkasan_piutang_proyek()
        semen_summary = get_ringkasan_hutang_semen()

        # 6. Volume Cor per Proyek (Default All-Time / Top Proyek)
        cursor.execute("""
        SELECT p.nama, COALESCE(SUM(pg.volume_m3), 0) AS total_vol
        FROM proyek p
        JOIN pengiriman pg ON p.id = pg.proyek_id
        GROUP BY p.id, p.nama
        HAVING total_vol > 0
        ORDER BY total_vol DESC
        LIMIT 5
        """)
        proyek_vol = [dict(r) for r in cursor.fetchall()]
        total_vol_proyek = sum(p["total_vol"] for p in proyek_vol)
        count_proyek = len(proyek_vol)

        # 7. Pengiriman Terakhir (Maks 10 transaksi terbaru)
        raw_recent = get_riwayat_pengiriman()[:10]
        recent_shipments = []
        months_id = ["", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
        
        for r in raw_recent:
            r_dict = dict(r)
            plat = (r_dict.get("no_plat_truk") or "").strip().upper()
            st_val = "Selesai"
            if plat:
                cursor.execute("SELECT status FROM kendaraan WHERE UPPER(no_plat) = ?", (plat,))
                st_row = cursor.fetchone()
                if st_row and st_row["status"] == "operasional" and r_dict.get("tanggal") == today_str:
                    st_val = "Dalam Proses"
            r_dict["status_kirim"] = st_val

            # Format Waktu: e.g. "18 Sep 2026 14:30"
            tgl_raw = str(r_dict.get("tanggal") or "")
            created_at_raw = str(r_dict.get("created_at") or "")
            time_part = "10:00"
            if " " in created_at_raw:
                time_part = created_at_raw.split(" ")[1][:5]
            elif "T" in created_at_raw:
                time_part = created_at_raw.split("T")[1][:5]

            try:
                dt_obj = datetime.strptime(tgl_raw[:10], "%Y-%m-%d")
                waktu_formatted = f"{dt_obj.day:02d} {months_id[dt_obj.month]} {dt_obj.year} {time_part}"
            except Exception:
                waktu_formatted = f"{tgl_raw} {time_part}"
            r_dict["waktu_str"] = waktu_formatted
            recent_shipments.append(r_dict)

        # 8. Material Peringatan Stok Rendah (berdasarkan stok aktual user)
        critical_materials = [
            m for m in stok_materials 
            if m["stok_saat_ini"] <= m["stok_minimum"] or m["stok_saat_ini"] < 0
        ]

        return {
            "stok_materials": stok_materials,
            "vol_today": vol_today,
            "target_today": target_today,
            "target_pct": target_pct,
            "vol_month": vol_month,
            "vol_growth_pct": vol_growth_pct,
            "count_ships_today": count_ships_today,
            "ships_selesai": ships_selesai,
            "ships_proses": ships_proses,
            "kend_aktif": kend_aktif,
            "kend_perjalanan": kend_perjalanan,
            "kend_standby": kend_standby,
            "saldo_kas": kas_summary["saldo_akhir"],
            "total_piutang": piutang_summary["sisa_piutang_proyek"],
            "total_hutang_semen": semen_summary["sisa_hutang_semen"],
            "total_in_proyek": kas_summary["total_in_proyek"],
            "total_out_semen": kas_summary["total_out_semen"],
            "total_out_kantor": kas_summary["total_out_kantor"],
            "total_out_gaji": kas_summary["total_out_gaji"],
            "proyek_vol": proyek_vol,
            "total_vol_proyek": total_vol_proyek,
            "count_proyek": count_proyek,
            "recent_shipments": recent_shipments,
            "critical_materials": critical_materials
        }


def get_proyek_volume_distribution(filter_time: str = "semua") -> Dict[str, Any]:
    """Mengambil data distribusi volume cor per proyek berdasarkan filter waktu"""
    with get_connection() as conn:
        cursor = conn.cursor()
        today_str = datetime.now().strftime("%Y-%m-%d")
        month_prefix = datetime.now().strftime("%Y-%m")

        where_clause = ""
        params = []
        if filter_time == "hari_ini":
            where_clause = "WHERE pg.tanggal = ?"
            params.append(today_str)
        elif filter_time == "bulan_ini":
            where_clause = "WHERE pg.tanggal LIKE ?"
            params.append(f"{month_prefix}%")

        cursor.execute(f"""
        SELECT p.nama, COALESCE(SUM(pg.volume_m3), 0) AS total_vol
        FROM proyek p
        JOIN pengiriman pg ON p.id = pg.proyek_id
        {where_clause}
        GROUP BY p.id, p.nama
        HAVING total_vol > 0
        ORDER BY total_vol DESC
        LIMIT 6
        """, params)
        items = [dict(r) for r in cursor.fetchall()]

        # Jika filter hari ini belum ada pengiriman hari ini, fallback ke all-time
        if not items and filter_time != "semua":
            cursor.execute("""
            SELECT p.nama, COALESCE(SUM(pg.volume_m3), 0) AS total_vol
            FROM proyek p
            JOIN pengiriman pg ON p.id = pg.proyek_id
            GROUP BY p.id, p.nama
            HAVING total_vol > 0
            ORDER BY total_vol DESC
            LIMIT 6
            """)
            items = [dict(r) for r in cursor.fetchall()]

        total_vol = sum(p["total_vol"] for p in items)
        proyek_count = len(items)

        return {
            "items": items,
            "total_vol": total_vol,
            "proyek_count": proyek_count
        }


# ==============================================================================
# PENGATURAN & BACKUP
# ==============================================================================

def get_settings() -> Dict[str, str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT kunci, nilai FROM pengaturan")
        return {r["kunci"]: r["nilai"] for r in cursor.fetchall()}

def save_setting(kunci: str, nilai: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO pengaturan (kunci, nilai) VALUES (?, ?)", (kunci, nilai))
        conn.commit()

def backup_db(destination_filepath: str) -> Tuple[bool, str]:
    """Membuat salinan cadangan file database SQLite"""
    try:
        source_path = get_db_path()
        if not os.path.exists(source_path):
            return False, "File database sumber tidak ditemukan."
        
        import shutil
        shutil.copy2(source_path, destination_filepath)
        return True, f"Database berhasil di-backup ke:\n{destination_filepath}"
    except Exception as e:
        return False, f"Gagal membuat backup: {str(e)}"


def restore_db(source_filepath: str) -> Tuple[bool, str]:
    """Merestore database dari file cadangan SQLite"""
    try:
        if not os.path.exists(source_filepath):
            return False, "File cadangan sumber tidak ditemukan."
        target_path = get_db_path()
        import shutil
        shutil.copy2(source_filepath, target_path)
        return True, "Database berhasil dipulihkan dari file cadangan."
    except Exception as e:
        return False, f"Gagal memulihkan database: {str(e)}"


def _clear_all_transactions(conn):
    """
    Mengosongkan seluruh tabel transaksi secara aman terhadap foreign key constraints.
    Mematikan sementara PRAGMA foreign_keys dan menghapus child table terlebih dahulu.
    """
    conn.execute("PRAGMA foreign_keys = OFF")
    cursor = conn.cursor()
    tables = [
        "kas_kantor",
        "proyek_piutang",
        "proyek_pembayaran",
        "tagihan_proyek",
        "gaji_karyawan",
        "saldo_kas",
        "pengiriman_detail",
        "pengiriman",
        "pembayaran_semen_cicilan",
        "pembayaran_semen",
        "stok_masuk",
        "material_harga_histori",
        "user_stok_log"
    ]
    for tbl in tables:
        cursor.execute(f"DELETE FROM {tbl}")

    cursor.execute("UPDATE material SET stok_saat_ini = 0")
    cursor.execute("UPDATE user_material_stok SET stok_saat_ini = 0")
    cursor.execute("DELETE FROM user_stok_log")
    cursor.execute("UPDATE kendaraan SET status = 'tersedia', keterangan_operasional = 'Standby di Batching Plant'")
    conn.execute("PRAGMA foreign_keys = ON")


def reset_data_transaksi() -> Tuple[bool, str]:
    """
    Mengosongkan seluruh riwayat transaksi (pengiriman, stok masuk, keuangan, kas, piutang, gaji).
    Stok material dikembalikan ke 0. Master data (material, mutu beton, resep, akun login) tetap dipertahankan.
    """
    try:
        with get_connection() as conn:
            _clear_all_transactions(conn)
            conn.commit()
        return True, "Seluruh data transaksi, pengiriman, stok, dan arus kas berhasil dikosongkan (di-reset ke nol)."
    except Exception as e:
        return False, f"Gagal mereset data transaksi: {str(e)}"


def reset_database_factory() -> Tuple[bool, str]:
    """
    Mereset database secara menyeluruh ke kondisi awal pabrik.
    Membersihkan seluruh transaksi dan mengembalikan master data standar awal.
    """
    try:
        with get_connection() as conn:
            _clear_all_transactions(conn)
            conn.execute("PRAGMA foreign_keys = OFF")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM proyek")
            cursor.execute("DELETE FROM kendaraan")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.commit()

        seed_default_data()
        sinkronkan_kode_beton_standar()
        return True, "Database berhasil di-reset ke kondisi awal pabrik (bersih total)."
    except Exception as e:
        return False, f"Gagal mereset database: {str(e)}"


# ==============================================================================
# DEMO DATA SEEDER LENGKAP & TERINTEGRASI
# ==============================================================================

def seed_data_ringkas() -> Tuple[bool, str]:
    """
    Mengisi database dengan data contoh transaksi ringkas (sedikit saja, realistis & terintegrasi):
    - 1 entri Modal Awal Kas (Rp 50.000.000)
    - 6 penerimaan stok material awal (Semen 10 ton, Pasir 15 ton, Split 20 ton, Air 10.000 L, Solar 1.000 L, Admixture 200 L)
    - 1 transaksi pembayaran cicilan semen ke supplier (Rp 5.000.000)
    - 3 transaksi pengiriman cor beton (SJ) untuk 3 proyek berbeda
    - 1 transaksi penerimaan pembayaran termin dari proyek klien (Rp 3.000.000)
    - 1 transaksi pengeluaran operasional kas kantor untuk BBM (Rp 1.500.000)
    - 1 transaksi pembayaran gaji supir mixer (Rp 2.200.000)
    """
    try:
        init_db()
        with get_connection() as conn:
            # 1. Bersihkan transaksi lama secara aman FK
            _clear_all_transactions(conn)
            cursor = conn.cursor()

            # 2. Master Proyek
            proyeks = [
                ("Proyek Pelebaran Windusari", "Kec. Windusari, Magelang", "aktif", "Pekerjaan jalan & saluran Windusari"),
                ("Proyek Pelebaran Jembatan", "Jembatan Kali Progo", "aktif", "Pekerjaan pelebaran jembatan utama"),
                ("Proyek Pelebaran Puring", "Puring, Magelang", "aktif", "Pelebaran jalan area Puring"),
                ("Proyek Pelebaran Polres", "Area Kantor Polres", "aktif", "Pembangunan & pengecoran area Polres")
            ]
            proyek_map = {}
            for nama, lok, stat, ket in proyeks:
                cursor.execute("SELECT id FROM proyek WHERE nama = ?", (nama,))
                row = cursor.fetchone()
                if row:
                    p_id = row["id"]
                    cursor.execute("UPDATE proyek SET lokasi=?, status=?, keterangan=? WHERE id=?", (lok, stat, ket, p_id))
                else:
                    cursor.execute("INSERT INTO proyek (nama, lokasi, status, keterangan) VALUES (?, ?, ?, ?)", (nama, lok, stat, ket))
                    p_id = cursor.lastrowid
                proyek_map[nama] = p_id

            # Ambil ID material & mutu beton
            cursor.execute("SELECT id, LOWER(nama) AS nama_lower, kode, harga_beli_terbaru FROM material")
            mat_map = {r["nama_lower"]: r["id"] for r in cursor.fetchall()}

            cursor.execute("SELECT id, kode, harga_jual_per_m3, biaya_operasional_per_m3 FROM mutu_beton")
            mutu_map = {r["kode"]: dict(r) for r in cursor.fetchall()}

            # 3. Modal Awal Kas (Rp 50.000.000)
            cursor.execute("""
            INSERT INTO saldo_kas (tanggal, keterangan, saldo_masuk, saldo_keluar, total_saldo, kategori, referensi_tipe, referensi_id)
            VALUES ('2026-09-08', 'Modal Awal Kas Operasional Batching Plant', 50000000.0, 0, 50000000.0, 'Modal Awal', 'manual', NULL)
            """)

            # 4. Stok Masuk Material (Sedikit saja)
            stok_masuk_data = [
                # Semen (kg) - 10.000 kg (10 ton) @ Rp 1.150/kg
                (mat_map.get("semen"), "2026-09-08", 10000.0, "H 9102 OA", "PT Semen Indonesia (Gresik)", 1150.0, "Semen Curah OPC Type 1 (10 Ton)"),
                # Pasir (kg) - 15.000 kg @ Rp 150/kg
                (mat_map.get("pasir"), "2026-09-08", 15000.0, "AA 8111 FA", "CV Pasir Merapi Muntilan", 150.0, "Pasir Pasang Merapi Grade A"),
                # Split 1.2 (kg) - 20.000 kg @ Rp 160/kg
                (mat_map.get("split 1.2"), "2026-09-08", 20000.0, "AA 8201 GA", "Stone Crusher Clereng", 160.0, "Batu Pecah / Split 1-2 Standar Cor"),
                # Air (Liter) - 10.000 liter @ Rp 10/liter
                (mat_map.get("air"), "2026-09-08", 10000.0, "-", "Sumur Artesis Plant", 10.0, "Air Bersih Tandon Utama"),
                # Solar (Liter) - 1.000 liter @ Rp 14.500/liter
                (mat_map.get("solar"), "2026-09-08", 1000.0, "-", "SPBU Pertamina Secang", 14500.0, "Bahan Bakar Genset & Wheel Loader"),
                # Admixture (Liter) - 200 liter @ Rp 22.000/liter
                (mat_map.get("admixture"), "2026-09-08", 200.0, "B 9901 SIK", "PT Sika Indonesia", 22000.0, "Sikament NN High Range Water Reducer")
            ]

            semen_id = None
            for m_id, tgl, jml, plat, supp, hrg, ket in stok_masuk_data:
                if not m_id:
                    continue
                tot = jml * hrg
                
                cursor.execute("SELECT kode FROM material WHERE id = ?", (m_id,))
                m_kd = cursor.fetchone()["kode"]
                is_smn = (m_kd == "MAT-SMN")
                current_semen_id = None
                
                if is_smn:
                    ton = jml / 1000.0
                    hrg_ton = hrg * 1000.0
                    no_do = f"DO-SMN-{tgl.replace('-', '')}-{int(ton)}T"
                    cursor.execute("""
                    INSERT INTO pembayaran_semen (no_order, supplier, tanggal_order, tanggal_datang, jumlah_ton, harga_per_ton, total_harga, keterangan)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (no_do, supp, tgl, tgl, ton, hrg_ton, tot, ket))
                    current_semen_id = cursor.lastrowid
                    semen_id = current_semen_id

                cursor.execute("""
                INSERT INTO stok_masuk (material_id, tanggal, jumlah, no_plat, supplier, harga_satuan, total_biaya, pembayaran_semen_id, keterangan)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (m_id, tgl, jml, plat, supp, hrg, tot, current_semen_id, ket))
                stk_in_id = cursor.lastrowid
                
                if current_semen_id:
                    cursor.execute("UPDATE pembayaran_semen SET stok_masuk_id = ? WHERE id = ?", (stk_in_id, current_semen_id))

                cursor.execute("""
                UPDATE material SET stok_saat_ini = stok_saat_ini + ?, harga_beli_terbaru = ? WHERE id = ?
                """, (jml, hrg, m_id))

                cursor.execute("""
                INSERT INTO material_harga_histori (material_id, tanggal, harga_beli, keterangan)
                VALUES (?, ?, ?, ?)
                """, (m_id, tgl, hrg, f"Penerimaan {supp}"))

            # 5. Pembayaran Cicilan Semen (1 transaksi: Rp 5.000.000)
            if semen_id:
                cursor.execute("""
                INSERT INTO pembayaran_semen_cicilan (pembayaran_semen_id, tanggal, nominal, metode, keterangan)
                VALUES (?, '2026-09-10', 5000000.0, 'Transfer Mandiri', 'Pembayaran Termin 1 Semen Curah 10 Ton')
                """, (semen_id,))

            # 6. Pengiriman Beton (Hanya 3 Transaksi Ringkas)
            pengiriman_data = [
                ("2026-09-10", "SJ-20260910-001", "K-250", 5.0, "Proyek Pelebaran Windusari", "STA 0+200 - 0+250", "AA 8123 AB", "Supriyanto", "Pengecoran rigid pavement, slump 12±2 cm"),
                ("2026-09-11", "SJ-20260911-001", "K-300", 6.0, "Proyek Pelebaran Jembatan", "Abutment Jembatan Sisi Barat", "AA 8456 CB", "Slamet Riyadi", "Mutu K-300 struktur abutment"),
                ("2026-09-12", "SJ-20260912-001", "K-225", 4.0, "Proyek Pelebaran Puring", "Plat Saluran Drainase", "AA 8990 BB", "Joko Susilo", "Cor plat lantai saluran drainase")
            ]

            for tgl, no_sj, k_mutu, vol, nm_pr, tujuan, plat, driver, cat in pengiriman_data:
                m_data = mutu_map.get(k_mutu)
                pr_id = proyek_map.get(nm_pr)
                if not m_data or not pr_id:
                    continue
                
                m_id = m_data["id"]
                h_jual = float(m_data["harga_jual_per_m3"] or 850000.0)
                b_ops = float(m_data["biaya_operasional_per_m3"] or 30000.0)

                # Hitung HPP
                calc_hpp = calculate_mutu_hpp_from_cursor(cursor, m_id, b_ops)
                hpp_m3 = calc_hpp["hpp_per_m3"]
                tot_hpp = hpp_m3 * vol
                tot_pendapatan = h_jual * vol
                laba_rp = tot_pendapatan - tot_hpp
                laba_pct = (laba_rp / tot_pendapatan * 100.0) if tot_pendapatan > 0 else 0.0

                cursor.execute("""
                INSERT INTO pengiriman (
                    no_surat_jalan, tanggal, mutu_beton_id, volume_m3, proyek_id, tujuan_pengiriman, 
                    no_plat_truk, driver, hpp_per_m3, total_hpp, harga_jual_per_m3, total_pendapatan, 
                    margin_laba_rp, margin_laba_persen, catatan
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (no_sj, tgl, m_id, vol, pr_id, tujuan, plat, driver, hpp_m3, tot_hpp, h_jual, tot_pendapatan, laba_rp, laba_pct, cat))
                p_id = cursor.lastrowid
                
                # Potong stok material
                cursor.execute("SELECT material_id, jumlah_per_m3 FROM mutu_beton_resep WHERE mutu_beton_id = ?", (m_id,))
                for r in cursor.fetchall():
                    mat_pakai = r["jumlah_per_m3"] * vol
                    cursor.execute("""
                    INSERT INTO pengiriman_detail (pengiriman_id, material_id, jumlah_terpakai)
                    VALUES (?, ?, ?)
                    """, (p_id, r["material_id"], mat_pakai))
                    cursor.execute("""
                    UPDATE material SET stok_saat_ini = stok_saat_ini - ? WHERE id = ?
                    """, (mat_pakai, r["material_id"]))

                # Catat piutang proyek
                cursor.execute("""
                INSERT INTO proyek_piutang (
                    proyek_id, pengiriman_id, tanggal, no_surat_jalan, mutu_beton_kode, volume_m3, 
                    harga_satuan_m3, total_tagihan, keterangan
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (pr_id, p_id, tgl, no_sj, k_mutu, vol, h_jual, tot_pendapatan, f"Pengecoran {k_mutu} ({vol} m³) - {tujuan}"))

            # 7. Penerimaan Pembayaran Termin Masuk (1 Transaksi: Rp 3.000.000)
            cursor.execute("""
            INSERT INTO proyek_pembayaran (proyek_id, tanggal, nominal, metode, nomor_bukti, keterangan)
            VALUES (?, '2026-09-12', 3000000.0, 'Transfer BCA', 'TRF-BCA-5512', 'Penerimaan Termin 1 Cor Rigid Jalan Windusari')
            """, (proyek_map["Proyek Pelebaran Windusari"],))

            # 8. Pengeluaran Kas Kantor (1 Transaksi: Rp 1.500.000)
            cursor.execute("""
            INSERT INTO kas_kantor (tanggal, nomor_nota, kategori, nominal, penerima_toko, keterangan, lampiran_foto)
            VALUES ('2026-09-11', 'NOTA-01/BBM', 'BBM / Solar Operasional', 1500000.0, 'SPBU 44.561.01 Secang', 'BBM Solar Truk Mixer untuk Pengiriman Windusari & Jembatan', '')
            """)

            # 9. Gaji Karyawan (1 Transaksi: Rp 2.200.000)
            cursor.execute("""
            INSERT INTO gaji_karyawan (tanggal_bayar, periode_gaji, nama_karyawan, jabatan, nominal_gaji, potongan_tunjangan, total_dibayar, metode_bayar, keterangan)
            VALUES ('2026-09-12', 'Minggu 2 Sept 2026', 'Supriyanto', 'Supir Truk Mixer', 2000000.0, 200000.0, 2200000.0, 'Tunai', 'Gaji Mingguan + Uang Ritase Truk AA 8123 AB')
            """)

            # 10. Hitung Ulang Arus Kas Master Terpadu
            recalculate_master_kas_balances(cursor)

            conn.commit()

        return True, "Data contoh ringkas (sedikit saja & terpadu) berhasil dimuat!"
    except Exception as e:
        return False, f"Gagal memuat data contoh ringkas: {str(e)}"


def seed_demo_data() -> Tuple[bool, str]:
    """Mengisi database dengan data contoh transaksi lengkap, realistis, dan terintegrasi 4 pilar"""
    try:
        init_db()
        with get_connection() as conn:
            # 1. Bersihkan transaksi lama secara aman FK
            _clear_all_transactions(conn)
            cursor = conn.cursor()
            
            # 2. Master Proyek
            proyeks = [
                ("Proyek Pelebaran Jalan Windusari", "Kec. Windusari, Magelang", "aktif", "Proyek Rigid Pavement & Pelebaran Jalan"),
                ("Proyek Pembangunan Jembatan Kali Progo", "Secang - Temanggung", "aktif", "Konstruksi Abutment & Pier Jembatan"),
                ("Proyek Gedung Rawat Inap RSUD", "Muntilan, Magelang", "aktif", "Struktur Balok, Kolom, & Plat Lantai"),
                ("Proyek Rigid Pavement Lingkar Selatan", "Magelang Selatan", "aktif", "Pengecoran Jalan Beton Kelas 1"),
                ("Proyek Perumahan Griya Asri Harmoni", "Mertoyudan, Magelang", "aktif", "Jalan Lingkungan & Saluran Perumahan"),
                ("Proyek Drainase & Box Culvert Poros Timur", "Grabag, Magelang", "selesai", "Pemasangan Box Culvert & Saluran Irigasi")
            ]
            proyek_map = {}
            for nama, lok, stat, ket in proyeks:
                cursor.execute("SELECT id FROM proyek WHERE nama = ?", (nama,))
                row = cursor.fetchone()
                if row:
                    p_id = row["id"]
                    cursor.execute("UPDATE proyek SET lokasi=?, status=?, keterangan=? WHERE id=?", (lok, stat, ket, p_id))
                else:
                    cursor.execute("INSERT INTO proyek (nama, lokasi, status, keterangan) VALUES (?, ?, ?, ?)", (nama, lok, stat, ket))
                    p_id = cursor.lastrowid
                proyek_map[nama] = p_id

            # Ambil ID material & mutu beton
            cursor.execute("SELECT id, LOWER(nama) AS nama_lower, kode, harga_beli_terbaru FROM material")
            mat_map = {r["nama_lower"]: r["id"] for r in cursor.fetchall()}
            
            cursor.execute("SELECT id, kode, harga_jual_per_m3, biaya_operasional_per_m3 FROM mutu_beton")
            mutu_map = {r["kode"]: dict(r) for r in cursor.fetchall()}

            # 3. Modal Awal Kas
            cursor.execute("""
            INSERT INTO saldo_kas (tanggal, keterangan, saldo_masuk, saldo_keluar, total_saldo, kategori, referensi_tipe, referensi_id)
            VALUES ('2026-08-30', 'Modal Awal Kas Operasional Batching Plant AKP', 75000000.0, 0, 75000000.0, 'Modal Awal', 'manual', NULL)
            """)

            # 4. Stok Masuk Material (Lengkap dengan Harga Beli Satuan)
            stok_masuk_data = [
                # Semen (kg) - Rp 1.150/kg
                (mat_map.get("semen"), "2026-08-30", 30000.0, "H 9102 OA", "PT Semen Indonesia (Gresik)", 1150.0, "Semen Curah OPC Type 1 (Tronton 30 Ton)"),
                (mat_map.get("semen"), "2026-09-03", 30000.0, "AB 8912 CD", "PT Semen Indonesia (Gresik)", 1150.0, "Semen Curah OPC Type 1 (Tronton 30 Ton)"),
                (mat_map.get("semen"), "2026-09-05", 30000.0, "H 9102 OA", "PT Semen Indonesia (Gresik)", 1150.0, "Semen Curah OPC Type 1 (Tronton 30 Ton)"),
                # Pasir (kg) - Rp 150/kg
                (mat_map.get("pasir"), "2026-08-30", 45000.0, "AA 8111 FA", "CV Pasir Merapi Muntilan", 150.0, "Pasir Pasang Merapi Grade A"),
                (mat_map.get("pasir"), "2026-09-02", 45000.0, "AA 8112 FA", "CV Pasir Merapi Muntilan", 150.0, "Pasir Pasang Merapi Grade A"),
                (mat_map.get("pasir"), "2026-09-04", 50000.0, "AA 8113 FA", "CV Pasir Merapi Muntilan", 150.0, "Pasir Pasang Merapi Grade A"),
                # Split 1.2 (kg) - Rp 160/kg
                (mat_map.get("split 1.2"), "2026-08-30", 50000.0, "AA 8201 GA", "Stone Crusher Clereng", 160.0, "Batu Pecah / Split 1-2 Standar Cor"),
                (mat_map.get("split 1.2"), "2026-09-02", 60000.0, "AA 8202 GA", "Stone Crusher Clereng", 160.0, "Batu Pecah / Split 1-2 Standar Cor"),
                (mat_map.get("split 1.2"), "2026-09-04", 60000.0, "AA 8203 GA", "Stone Crusher Clereng", 160.0, "Batu Pecah / Split 1-2 Standar Cor"),
                # Split 1.1 (kg) - Rp 170/kg
                (mat_map.get("split 1.1"), "2026-08-31", 30000.0, "AA 8205 GA", "Stone Crusher Clereng", 170.0, "Batu Pecah / Split 1-1 Screening"),
                # Air (Liter) - Rp 10/liter
                (mat_map.get("air"), "2026-08-30", 50000.0, "-", "Sumur Artesis Plant", 10.0, "Air Bersih Tandon Utama"),
                (mat_map.get("air"), "2026-09-03", 50000.0, "-", "Sumur Artesis Plant", 10.0, "Air Bersih Tandon Utama"),
                # Admixture (Liter) - Rp 22.000/liter
                (mat_map.get("admixture"), "2026-08-30", 1000.0, "B 9901 SIK", "PT Sika Indonesia", 22000.0, "Sikament NN High Range Water Reducer"),
                (mat_map.get("admixture"), "2026-09-04", 1000.0, "B 9901 SIK", "PT Sika Indonesia", 22000.0, "Sikament NN High Range Water Reducer")
            ]

            semen_order_ids = []
            for m_id, tgl, jml, plat, supp, hrg, ket in stok_masuk_data:
                if not m_id:
                    continue
                tot = jml * hrg
                
                # Check jika Semen -> buat hutang semen
                cursor.execute("SELECT kode FROM material WHERE id = ?", (m_id,))
                m_kd = cursor.fetchone()["kode"]
                is_smn = (m_kd == "MAT-SMN")
                semen_id = None
                
                if is_smn:
                    ton = jml / 1000.0
                    hrg_ton = hrg * 1000.0
                    no_do = f"DO-SMN-{tgl.replace('-', '')}-{int(ton)}T"
                    cursor.execute("""
                    INSERT INTO pembayaran_semen (no_order, supplier, tanggal_order, tanggal_datang, jumlah_ton, harga_per_ton, total_harga, keterangan)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (no_do, supp, tgl, tgl, ton, hrg_ton, tot, ket))
                    semen_id = cursor.lastrowid
                    semen_order_ids.append(semen_id)

                cursor.execute("""
                INSERT INTO stok_masuk (material_id, tanggal, jumlah, no_plat, supplier, harga_satuan, total_biaya, pembayaran_semen_id, keterangan)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (m_id, tgl, jml, plat, supp, hrg, tot, semen_id, ket))
                stk_in_id = cursor.lastrowid
                
                if semen_id:
                    cursor.execute("UPDATE pembayaran_semen SET stok_masuk_id = ? WHERE id = ?", (stk_in_id, semen_id))

                cursor.execute("""
                UPDATE material SET stok_saat_ini = stok_saat_ini + ?, harga_beli_terbaru = ? WHERE id = ?
                """, (jml, hrg, m_id))

                cursor.execute("""
                INSERT INTO material_harga_histori (material_id, tanggal, harga_beli, keterangan)
                VALUES (?, ?, ?, ?)
                """, (m_id, tgl, hrg, f"Penerimaan {supp}"))

            # 5. Pembayaran Cicilan Semen
            if len(semen_order_ids) >= 1:
                cursor.execute("""
                INSERT INTO pembayaran_semen_cicilan (pembayaran_semen_id, tanggal, nominal, metode, keterangan)
                VALUES (?, '2026-08-31', 34500000.0, 'Transfer Mandiri', 'Pelunasan Order Semen Curah 30 Ton (DO Pertama)')
                """, (semen_order_ids[0],))
            if len(semen_order_ids) >= 2:
                cursor.execute("""
                INSERT INTO pembayaran_semen_cicilan (pembayaran_semen_id, tanggal, nominal, metode, keterangan)
                VALUES (?, '2026-09-04', 20000000.0, 'Transfer Mandiri', 'Pembayaran Termin 1 Semen Curah 30 Ton')
                """, (semen_order_ids[1],))

            # 6. Transaksi Pengiriman / Produksi Dispatch & Piutang Proyek Otomatis
            pengiriman_data = [
                # 1 Sept 2026
                ("2026-09-01", "SJ-20260901-001", "K-250", 6.0, "Proyek Pelebaran Jalan Windusari", "STA 0+200 - 0+250", "AA 8123 AB", "Supriyanto", "Slump 12±2 cm, cor lancar jalur kiri"),
                ("2026-09-01", "SJ-20260901-002", "K-250", 6.0, "Proyek Pelebaran Jalan Windusari", "STA 0+250 - 0+300", "AA 8456 CB", "Slamet Riyadi", "Slump 12±2 cm, agregat merata"),
                ("2026-09-01", "SJ-20260901-003", "K-350", 6.0, "Proyek Pembangunan Jembatan Kali Progo", "Abutment Sisi Barat", "AA 8990 BB", "Joko Susilo", "Mutu K-350 struktur abutment"),
                ("2026-09-01", "SJ-20260901-004", "K-300", 6.0, "Proyek Gedung Rawat Inap RSUD", "Kolom Utama Lt 1", "AA 8234 XY", "Budi Santoso", "Slump 10±2 cm pompa beton"),
                
                # 2 Sept 2026
                ("2026-09-02", "SJ-20260902-001", "K-350", 6.0, "Proyek Pembangunan Jembatan Kali Progo", "Abutment Sisi Barat", "AA 8123 AB", "Supriyanto", "Slump 10±2 cm, uji silinder 3 sampel"),
                ("2026-09-02", "SJ-20260902-002", "K-300", 6.0, "Proyek Gedung Rawat Inap RSUD", "Balok & Kolom Lt 2", "AA 8456 CB", "Slamet Riyadi", "Cor lantai 2 zona barat"),
                ("2026-09-02", "SJ-20260902-003", "K-300", 6.0, "Proyek Gedung Rawat Inap RSUD", "Plat Lantai 2 Zona A", "AA 8234 XY", "Budi Santoso", "Slump 12±2 cm finish trowel"),
                ("2026-09-02", "SJ-20260902-004", "K-250", 6.0, "Proyek Pelebaran Jalan Windusari", "STA 0+300 - 0+350", "AA 8990 BB", "Joko Susilo", "Pengecoran rigid pavement"),

                # 3 Sept 2026
                ("2026-09-03", "SJ-20260903-001", "K-300", 6.5, "Proyek Rigid Pavement Lingkar Selatan", "Lajur Lambat STA 2+100", "AA 8123 AB", "Supriyanto", "Rigid Pavement Tebal 25cm"),
                ("2026-09-03", "SJ-20260903-002", "K-300", 6.5, "Proyek Rigid Pavement Lingkar Selatan", "Lajur Lambat STA 2+150", "AA 8990 BB", "Joko Susilo", "Rigid Pavement Tebal 25cm"),
                ("2026-09-03", "SJ-20260903-003", "K-350", 6.0, "Proyek Pembangunan Jembatan Kali Progo", "Pier Jembatan P1", "AA 8456 CB", "Slamet Riyadi", "Pengecoran pilar jembatan"),
                ("2026-09-03", "SJ-20260903-004", "K-300", 6.0, "Proyek Gedung Rawat Inap RSUD", "Plat Lantai 2 Zona B", "AA 8234 XY", "Budi Santoso", "Pengecoran lanjutan plat"),

                # 4 Sept 2026
                ("2026-09-04", "SJ-20260904-001", "K-175", 6.0, "Proyek Perumahan Griya Asri Harmoni", "Jalan Blok C", "AA 8456 CB", "Slamet Riyadi", "Pengecoran jalan perumahan"),
                ("2026-09-04", "SJ-20260904-002", "K-175", 6.0, "Proyek Perumahan Griya Asri Harmoni", "Saluran Lingkungan", "AA 8234 XY", "Budi Santoso", "Pengecoran tutup saluran & drainase"),
                ("2026-09-04", "SJ-20260904-003", "K-300", 6.5, "Proyek Rigid Pavement Lingkar Selatan", "Lajur Lambat STA 2+200", "AA 8123 AB", "Supriyanto", "Slump 10±2 cm"),
                ("2026-09-04", "SJ-20260904-004", "K-250", 6.0, "Proyek Pelebaran Jalan Windusari", "STA 0+350 - 0+400", "AA 8990 BB", "Joko Susilo", "Rigid segmen 4"),

                # 5 Sept 2026
                ("2026-09-05", "SJ-20260905-001", "K-225", 5.0, "Proyek Pelebaran Jalan Windusari", "Bahu Jalan Segmen B", "AA 8123 AB", "Supriyanto", "Slump 12±2 cm bahu jalan"),
                ("2026-09-05", "SJ-20260905-002", "K-275", 5.0, "Proyek Drainase & Box Culvert Poros Timur", "Crossing Box Culvert", "AA 8990 BB", "Joko Susilo", "Pengecoran top slab box"),
                ("2026-09-05", "SJ-20260905-003", "K-275", 5.0, "Proyek Drainase & Box Culvert Poros Timur", "Wingwall Box Culvert", "AA 8456 CB", "Slamet Riyadi", "Pengecoran dinding sayap culvert"),
                ("2026-09-05", "SJ-20260905-004", "K-300", 6.5, "Proyek Rigid Pavement Lingkar Selatan", "Lajur Lambat STA 2+250", "AA 8234 XY", "Budi Santoso", "Rigid Pavement STA akhir"),

                # 6 Sept 2026
                ("2026-09-06", "SJ-20260906-001", "K-250", 6.0, "Proyek Pelebaran Jalan Windusari", "STA 0+400 - 0+450", "AA 8123 AB", "Supriyanto", "Pengecoran pagi hari jalur kanan"),
                ("2026-09-06", "SJ-20260906-002", "K-350", 6.0, "Proyek Pembangunan Jembatan Kali Progo", "Pier Jembatan P1 Cap", "AA 8456 CB", "Slamet Riyadi", "Slump 12±2 cm pier head")
            ]

            for tgl, no_sj, k_mutu, vol, nm_pr, tujuan, plat, driver, cat in pengiriman_data:
                m_data = mutu_map.get(k_mutu)
                pr_id = proyek_map.get(nm_pr)
                if not m_data or not pr_id:
                    continue
                
                m_id = m_data["id"]
                h_jual = float(m_data["harga_jual_per_m3"] or 850000.0)
                b_ops = float(m_data["biaya_operasional_per_m3"] or 30000.0)

                # Hitung HPP
                calc_hpp = calculate_mutu_hpp_from_cursor(cursor, m_id, b_ops)
                hpp_m3 = calc_hpp["hpp_per_m3"]
                tot_hpp = hpp_m3 * vol
                tot_pendapatan = h_jual * vol
                laba_rp = tot_pendapatan - tot_hpp
                laba_pct = (laba_rp / tot_pendapatan * 100.0) if tot_pendapatan > 0 else 0.0

                cursor.execute("""
                INSERT INTO pengiriman (
                    no_surat_jalan, tanggal, mutu_beton_id, volume_m3, proyek_id, tujuan_pengiriman, 
                    no_plat_truk, driver, hpp_per_m3, total_hpp, harga_jual_per_m3, total_pendapatan, 
                    margin_laba_rp, margin_laba_persen, catatan
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (no_sj, tgl, m_id, vol, pr_id, tujuan, plat, driver, hpp_m3, tot_hpp, h_jual, tot_pendapatan, laba_rp, laba_pct, cat))
                p_id = cursor.lastrowid
                
                # Potong stok material
                cursor.execute("SELECT material_id, jumlah_per_m3 FROM mutu_beton_resep WHERE mutu_beton_id = ?", (m_id,))
                for r in cursor.fetchall():
                    mat_pakai = r["jumlah_per_m3"] * vol
                    cursor.execute("""
                    INSERT INTO pengiriman_detail (pengiriman_id, material_id, jumlah_terpakai)
                    VALUES (?, ?, ?)
                    """, (p_id, r["material_id"], mat_pakai))
                    cursor.execute("""
                    UPDATE material SET stok_saat_ini = stok_saat_ini - ? WHERE id = ?
                    """, (mat_pakai, r["material_id"]))

                # Otomatis catat piutang proyek
                cursor.execute("""
                INSERT INTO proyek_piutang (
                    proyek_id, pengiriman_id, tanggal, no_surat_jalan, mutu_beton_kode, volume_m3, 
                    harga_satuan_m3, total_tagihan, keterangan
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (pr_id, p_id, tgl, no_sj, k_mutu, vol, h_jual, tot_pendapatan, f"Pengecoran {k_mutu} ({vol} m³) - {tujuan}"))

            # 7. Pembayaran Termin Masuk dari Klien Proyek (Total Rp 153.000.000)
            pembayaran_proyek_data = [
                (proyek_map["Proyek Pelebaran Jalan Windusari"], "2026-09-04", 50000000.0, "Transfer BNI", "TRF-BNI-8921", "Penerimaan Termin 1 (DP & Pengecoran Windusari)"),
                (proyek_map["Proyek Pembangunan Jembatan Kali Progo"], "2026-09-04", 25000000.0, "Transfer Mandiri", "TRF-MDR-4412", "Penerimaan Termin 1 PT Adi Karya (Jembatan Progo)"),
                (proyek_map["Proyek Gedung Rawat Inap RSUD"], "2026-09-05", 48000000.0, "Transfer BCA", "TRF-BCA-1002", "Penerimaan Termin 1 Cor Balok & Plat Lt 2 RSUD"),
                (proyek_map["Proyek Rigid Pavement Lingkar Selatan"], "2026-09-05", 30000000.0, "Transfer Bank Jateng", "TRF-BJT-7721", "Penerimaan Termin 1 Dinas PUPR (Rigid Pavement)")
            ]
            for p_id, tgl, nom, met, buk, ket in pembayaran_proyek_data:
                cursor.execute("""
                INSERT INTO proyek_pembayaran (proyek_id, tanggal, nominal, metode, nomor_bukti, keterangan)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (p_id, tgl, nom, met, buk, ket))

            # 8. Pengeluaran Kas Kantor (Non-Semen)
            kas_kantor_data = [
                ("2026-09-01", "NOTA-01/BBM", "BBM / Solar Operasional", 4500000.0, "SPBU 44.561.01 Secang", "BBM Solar Industri untuk Truk Mixer & Genset", ""),
                ("2026-09-02", "NOTA-02/SVC", "Servis & Maintenance", 3200000.0, "Bengkel Hidrolik Abadi", "Pembelian Oli Hidrolik & Penggantian Filter Batching Plant", ""),
                ("2026-09-03", "NOTA-03/KNS", "Konsumsi & Dapur", 450000.0, "RM Padang Murah", "Konsumsi Lembur Operator & Kru Lapangan", ""),
                ("2026-09-04", "NOTA-04/ATK", "ATK & Perlengkapan", 350000.0, "Toko Buku & ATK Jaya", "Kertas Surat Jalan Cor 3 Ply, Tinta Printer & Map Faktur", ""),
                ("2026-09-06", "NOTA-05/BBM", "BBM / Solar Operasional", 3000000.0, "SPBU 44.561.01 Secang", "BBM Solar Truk Mixer Pengiriman Hari Ini", "")
            ]
            for tgl, nota, kat, nom, toko, ket, foto in kas_kantor_data:
                cursor.execute("""
                INSERT INTO kas_kantor (tanggal, nomor_nota, kategori, nominal, penerima_toko, keterangan, lampiran_foto)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (tgl, nota, kat, nom, toko, ket, foto))

            # 9. Pembayaran Gaji Karyawan
            gaji_data = [
                ("2026-09-05", "Minggu 1 Sept 2026", "Supriyanto", "Supir Truk Mixer", 2200000.0, 300000.0, 2500000.0, "Tunai", "Gaji Pokok + Uang Ritase"),
                ("2026-09-05", "Minggu 1 Sept 2026", "Slamet Riyadi", "Supir Truk Mixer", 2200000.0, 300000.0, 2500000.0, "Tunai", "Gaji Pokok + Uang Ritase"),
                ("2026-09-05", "Minggu 1 Sept 2026", "Joko Susilo", "Supir Truk Mixer", 2200000.0, 300000.0, 2500000.0, "Tunai", "Gaji Pokok + Uang Ritase"),
                ("2026-09-05", "Minggu 1 Sept 2026", "Agus Wahyudi", "Operator Batching Plant", 2500000.0, 500000.0, 3000000.0, "Transfer Mandiri", "Gaji Mingguan Operator Utama"),
                ("2026-09-05", "Minggu 1 Sept 2026", "Bambang Kurniawan", "Operator Wheel Loader", 2000000.0, 250000.0, 2250000.0, "Tunai", "Gaji Mingguan Loader")
            ]
            for tgl, per, nm, jab, gj, pot, tot, met, ket in gaji_data:
                cursor.execute("""
                INSERT INTO gaji_karyawan (tanggal_bayar, periode_gaji, nama_karyawan, jabatan, nominal_gaji, potongan_tunjangan, total_dibayar, metode_bayar, keterangan)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (tgl, per, nm, jab, gj, pot, tot, met, ket))

            # 10. Sinkronkan dan Hitung Ulang Arus Kas Master
            recalculate_master_kas_balances(cursor)

            # 11. Profil Perusahaan
            cursor.execute("INSERT OR REPLACE INTO pengaturan (kunci, nilai) VALUES ('nama_perusahaan', 'AKP BATCHING PLANT')")
            cursor.execute("INSERT OR REPLACE INTO pengaturan (kunci, nilai) VALUES ('alamat_perusahaan', 'Jl. Raya Magelang - Secang KM 7, Jawa Tengah')")
            cursor.execute("INSERT OR REPLACE INTO pengaturan (kunci, nilai) VALUES ('telepon_perusahaan', '0812-3456-7890 / (0293) 362819')")
            cursor.execute("INSERT OR REPLACE INTO pengaturan (kunci, nilai) VALUES ('pj_lapangan', 'Ir. H. Sudirman (Plant Manager)')")

            conn.commit()

        return True, "Data contoh transaksi terintegrasi penuh (POS & Keuangan Proyek) berhasil dimuat lengkap!"
    except Exception as e:
        return False, f"Gagal memuat data contoh: {str(e)}"


# ==============================================================================
# MODUL MANAJEMEN PENGGUNA & AUTENTIKASI (USER LOGIN)
# ==============================================================================

def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Menghasilkan hash aman SHA-256 PBKDF2 dengan salt acak"""
    if not salt:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
    return f"{salt}${pwd_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Memverifikasi kecocokan password dengan hash tersimpan"""
    if not stored_hash or "$" not in stored_hash:
        return False
    try:
        salt, expected = stored_hash.split("$", 1)
        calculated = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
        return hmac.compare_digest(calculated, expected)
    except Exception:
        return False


def authenticate_user(username: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Memverifikasi login username dan password.
    Returns: (is_success, message, user_data)
    """
    clean_u = username.strip()
    if not clean_u:
        return False, "Username tidak boleh kosong.", None
    if not password:
        return False, "Password tidak boleh kosong.", None

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (clean_u,))
        row = cursor.fetchone()
        if not row:
            return False, "Username tidak ditemukan.", None
        
        user = dict(row)
        if not user.get("is_active", 1):
            return False, "Akun ini telah dinonaktifkan. Hubungi pengelola sistem.", None
        
        if not verify_password(password, user.get("password_hash", "")):
            return False, "Password salah.", None
        
        # Update last_login
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (now_str, user["id"]))
        conn.commit()

        # Hilangkan password_hash dari objek session
        user.pop("password_hash", None)
        user["last_login"] = now_str
        return True, "Login berhasil.", user


def get_all_users() -> List[Dict[str, Any]]:
    """Mengambil seluruh daftar pengguna aplikasi"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, nama_lengkap, role, is_active, last_login, created_at
            FROM users
            ORDER BY id ASC
        """)
        users = []
        for r in cursor.fetchall():
            u = dict(r)
            if not u.get("role"):
                u["role"] = "Administrator" if u.get("username") == "admin" else "Operator"
            users.append(u)
        return users


def create_user(username: str, password: str, nama_lengkap: str, role: str = "Operator", is_active: int = 1) -> Tuple[bool, str]:
    """Menambahkan user baru"""
    u = username.strip()
    nama = nama_lengkap.strip()
    r = role.strip() if role else "Operator"
    if not u or not nama:
        return False, "Username dan Nama Lengkap wajib diisi."
    if len(password) < 4:
        return False, "Password minimal 4 karakter."

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (u,))
        if cursor.fetchone():
            return False, f"Username '{u}' sudah digunakan. Silakan pilih username lain."
        
        pwd_hash = hash_password(password)
        cursor.execute("""
            INSERT INTO users (username, password_hash, nama_lengkap, role, is_active)
            VALUES (?, ?, ?, ?, ?)
        """, (u, pwd_hash, nama, r, is_active))
        new_user_id = cursor.lastrowid
        
        # Inisialisasi stok individual untuk user baru (dari stok global saat ini)
        cursor.execute("SELECT id, stok_saat_ini FROM material")
        all_mats = cursor.fetchall()
        for mat in all_mats:
            cursor.execute("""
            INSERT OR IGNORE INTO user_material_stok (user_id, material_id, stok_saat_ini)
            VALUES (?, ?, ?)
            """, (new_user_id, mat["id"], float(mat["stok_saat_ini"] or 0)))

        conn.commit()
        return True, f"Pengguna '{u}' berhasil didaftarkan. Stok material telah diinisialisasi."


def update_user(user_id: int, nama_lengkap: str, is_active: int, role: str = None) -> Tuple[bool, str]:
    """Mengubah data user (nama lengkap, status aktif, dan role)"""
    nama = nama_lengkap.strip()
    if not nama:
        return False, "Nama lengkap tidak boleh kosong."

    with get_connection() as conn:
        cursor = conn.cursor()
        # Jika menonaktifkan, pastikan bukan satu-satunya user aktif
        if is_active == 0:
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1 AND id != ?", (user_id,))
            if cursor.fetchone()[0] == 0:
                return False, "Tidak dapat menonaktifkan satu-satunya pengguna aktif yang tersisa."

        if role:
            cursor.execute("""
                UPDATE users SET nama_lengkap = ?, is_active = ?, role = ?
                WHERE id = ?
            """, (nama, is_active, role.strip(), user_id))
        else:
            cursor.execute("""
                UPDATE users SET nama_lengkap = ?, is_active = ?
                WHERE id = ?
            """, (nama, is_active, user_id))
        conn.commit()
        return True, "Data pengguna berhasil diperbarui."


def change_user_password(user_id: int, new_password: str) -> Tuple[bool, str]:
    """Mengubah password pengguna"""
    if len(new_password) < 4:
        return False, "Password baru minimal 4 karakter."

    with get_connection() as conn:
        cursor = conn.cursor()
        pwd_hash = hash_password(new_password)
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (pwd_hash, user_id))
        conn.commit()
        return True, "Password berhasil diperbarui."


def delete_user(user_id: int) -> Tuple[bool, str]:
    """Menghapus akun pengguna"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1 AND id != ?", (user_id,))
        if cursor.fetchone()[0] == 0:
            return False, "Tidak dapat menghapus satu-satunya akun aktif yang tersisa."

        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True, "Pengguna berhasil dihapus."


# ==============================================================================
# PENGATURAN UMUM APLIKASI
# ==============================================================================

def get_pengaturan(kunci: str, default: str = "") -> str:
    """Mengambil nilai pengaturan berdasarkan kunci"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT nilai FROM pengaturan WHERE kunci = ?", (kunci,))
        row = cursor.fetchone()
        return str(row[0]) if row and row[0] is not None else default


def set_pengaturan(kunci: str, nilai: str):
    """Menyimpan atau memperbarui nilai pengaturan"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pengaturan (kunci, nilai) VALUES (?, ?)
            ON CONFLICT(kunci) DO UPDATE SET nilai = excluded.nilai
        """, (kunci, str(nilai)))
        conn.commit()


def get_settings() -> Dict[str, str]:
    """Mengambil semua pengaturan sebagai dictionary"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT kunci, nilai FROM pengaturan")
        return {row[0]: row[1] for row in cursor.fetchall()}


def save_setting(kunci: str, nilai: str):
    """Alias untuk set_pengaturan"""
    set_pengaturan(kunci, nilai)




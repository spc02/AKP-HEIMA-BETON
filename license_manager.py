"""
AKP Beton Management System - License Manager
Modul Keamanan & Aktivasi Aplikasi (Hardware ID Binding & Cryptographic Verification)
"""

import os
import sys
import hmac
import hashlib
import json
import base64
import subprocess
from datetime import datetime
from typing import Tuple, Optional, Dict, Any

# Secret salt unik untuk AKP Construction Building
# JANGAN disebarkan ke publik
LICENSE_SECRET = b"AKP_CONTRUCTION_BUILDING_SECURE_SALT_2026_V1"

def _get_app_data_dir() -> str:
    """Mendapatkan direktori penyimpanan lisensi yang aman di komputer lokal"""
    appdata = os.getenv('LOCALAPPDATA') or os.getenv('APPDATA')
    if not appdata:
        appdata = os.path.expanduser('~')
    target_dir = os.path.join(appdata, 'AKPBetonLicense')
    os.makedirs(target_dir, exist_ok=True)
    return target_dir

def get_license_file_path() -> str:
    return os.path.join(_get_app_data_dir(), "app_license.dat")


def _get_windows_machine_guid() -> str:
    """Mengambil MachineGuid dari registry Windows (stabil & unik per instalasi Windows)"""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(guid).strip()
    except Exception:
        pass
    return ""


# Flag untuk mencegah jendela CMD / PowerShell berkedip saat query hardware
NO_WINDOW_FLAG = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)

_CACHED_MACHINE_ID: Optional[str] = None

def _get_motherboard_uuid() -> str:
    """Mengambil UUID Motherboard via powershell atau wmic tanpa memunculkan jendela konsol"""
    try:
        cmd = ["powershell", "-NoProfile", "-Command", "(Get-CimInstance -ClassName Win32_ComputerSystemProduct).UUID"]
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=4, creationflags=NO_WINDOW_FLAG).decode().strip()
        if out and out.lower() != "to be filled by o.e.m.":
            return out
    except Exception:
        pass

    try:
        cmd = ["wmic", "csproduct", "get", "UUID"]
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=4, creationflags=NO_WINDOW_FLAG).decode().split()
        if len(out) > 1 and out[1].lower() != "to be filled by o.e.m.":
            return out[1]
    except Exception:
        pass

    return ""


def _get_cpu_id() -> str:
    """Mengambil ProcessorId via powershell atau wmic tanpa memunculkan jendela konsol"""
    try:
        cmd = ["powershell", "-NoProfile", "-Command", "(Get-CimInstance -ClassName Win32_Processor).ProcessorId"]
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=4, creationflags=NO_WINDOW_FLAG).decode().strip()
        if out:
            return out
    except Exception:
        pass
    return ""


def _get_system_drive_serial() -> str:
    """Mengambil volume serial drive sistem C: tanpa memunculkan jendela konsol"""
    try:
        cmd = ["powershell", "-NoProfile", "-Command", "(Get-Volume -DriveLetter C).SerialNumber"]
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=4, creationflags=NO_WINDOW_FLAG).decode().strip()
        if out:
            return out
    except Exception:
        pass
    return ""


def get_machine_id() -> str:
    """
    Menghasilkan Machine ID unik dan stabil untuk komputer ini.
    Format tampilan: AKP-XXXX-XXXX-XXXX-XXXX
    Disimpan dalam memori cache agar query hardware hanya berjalan satu kali.
    """
    global _CACHED_MACHINE_ID
    if _CACHED_MACHINE_ID:
        return _CACHED_MACHINE_ID

    guid = _get_windows_machine_guid()
    mb_uuid = _get_motherboard_uuid()
    cpu_id = _get_cpu_id()
    drive_ser = _get_system_drive_serial()

    # Fallback jika di lingkungan virtual / batasan izin
    if not (guid or mb_uuid or cpu_id or drive_ser):
        import uuid
        guid = str(uuid.getnode())

    raw_fingerprint = f"{guid}::{mb_uuid}::{cpu_id}::{drive_ser}".encode('utf-8')
    digest = hashlib.sha256(raw_fingerprint).hexdigest().upper()

    # Format 4 blok x 4 karakter: AKP-XXXX-XXXX-XXXX-XXXX
    _CACHED_MACHINE_ID = f"AKP-{digest[0:4]}-{digest[4:8]}-{digest[8:12]}-{digest[12:16]}"
    return _CACHED_MACHINE_ID


def generate_license_key(machine_id: str, license_type: str = "PERM") -> str:
    """
    Membuat kunci lisensi kriptografis untuk Machine ID tertentu.
    Digunakan oleh pengembang / admin untuk membuat kunci aktivasi.
    
    Format:
    AKP-[TYPE]-[SIG1]-[SIG2]-[SIG3]
    Contoh:
    AKP-PERM-7F8A-901B-3C2D
    """
    clean_mid = machine_id.strip().upper()
    clean_type = license_type.strip().upper()  # e.g. "PERM" atau "20271231" (YYYYMMDD)

    msg = f"{clean_mid}::{clean_type}".encode('utf-8')
    sig = hmac.new(LICENSE_SECRET, msg, hashlib.sha256).hexdigest().upper()

    key = f"AKP-{clean_type}-{sig[0:4]}-{sig[4:8]}-{sig[8:12]}"
    return key


def verify_license_key(machine_id: str, license_key: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Memverifikasi apakah License Key valid untuk Machine ID saat ini.
    
    Returns:
        (is_valid: bool, message: str, metadata: dict)
    """
    clean_key = license_key.strip().upper().replace(" ", "")
    clean_mid = machine_id.strip().upper()

    parts = clean_key.split("-")
    if len(parts) != 5 or parts[0] != "AKP":
        return False, "Format Kunci Lisensi tidak valid (harus AKP-TYPE-XXXX-XXXX-XXXX).", None

    lic_type = parts[1]
    expected_key = generate_license_key(clean_mid, lic_type)

    if clean_key != expected_key:
        return False, "Kunci Lisensi salah atau tidak sesuai dengan Machine ID komputer ini.", None

    # Cek tanggal kedaluwarsa jika bukan PERM
    expiry_date_str = None
    if lic_type != "PERM":
        try:
            exp_dt = datetime.strptime(lic_type, "%Y%m%d")
            expiry_date_str = exp_dt.strftime("%d-%m-%Y")
            if datetime.now() > exp_dt:
                return False, f"Lisensi telah kedaluwarsa pada tanggal {expiry_date_str}.", None
        except ValueError:
            return False, "Tipe lisensi tidak dikenali.", None

    meta = {
        "machine_id": clean_mid,
        "license_key": clean_key,
        "type": lic_type,
        "expiry_date": expiry_date_str,
        "is_permanent": (lic_type == "PERM")
    }
    return True, "Lisensi valid.", meta


def save_license(machine_id: str, license_key: str, meta: Dict[str, Any]) -> bool:
    """Menyimpan data lisensi yang sudah diverifikasi ke file terenkripsi lokal"""
    try:
        data = {
            "machine_id": machine_id,
            "license_key": license_key,
            "activated_at": datetime.now().isoformat(),
            "meta": meta
        }
        json_str = json.dumps(data).encode('utf-8')
        
        # Enkripsi sederhana dengan XOR hash secret agar tidak terbaca plain text
        key_hash = hashlib.sha256(LICENSE_SECRET).digest()
        encrypted = bytes([b ^ key_hash[i % len(key_hash)] for i, b in enumerate(json_str)])
        b64 = base64.b64encode(encrypted).decode('utf-8')

        with open(get_license_file_path(), 'w', encoding='utf-8') as f:
            f.write(b64)
        return True
    except Exception as e:
        print(f"Error menyimpan lisensi: {e}")
        return False


def load_saved_license() -> Optional[Dict[str, Any]]:
    """Membaca data lisensi tersimpan dari komputer"""
    filepath = get_license_file_path()
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            b64 = f.read().strip()
        encrypted = base64.b64decode(b64)
        key_hash = hashlib.sha256(LICENSE_SECRET).digest()
        decrypted = bytes([b ^ key_hash[i % len(key_hash)] for i, b in enumerate(encrypted)])
        return json.loads(decrypted.decode('utf-8'))
    except Exception:
        return None


def is_activated() -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Memeriksa apakah komputer saat ini sudah teraktivasi dengan lisensi yang sah.
    
    Returns:
        (activated: bool, status_message: str, license_data: dict)
    """
    saved = load_saved_license()
    if not saved:
        return False, "Aplikasi belum diaktivasi.", None

    current_mid = get_machine_id()
    saved_mid = saved.get("machine_id", "")
    saved_key = saved.get("license_key", "")

    if current_mid != saved_mid:
        return False, "Machine ID komputer tidak cocok dengan lisensi tersimpan (aplikasi disalin/dipindahkan).", None

    valid, msg, meta = verify_license_key(current_mid, saved_key)
    if not valid:
        return False, msg, None

    return True, "Aplikasi telah teraktivasi secara sah.", saved


def reset_license() -> bool:
    """Mereset aktivasi aplikasi (menghapus file lisensi tersimpan)"""
    filepath = get_license_file_path()
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            return True
        except Exception as e:
            print(f"Gagal menghapus file lisensi: {e}")
            return False
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--reset", "-r", "reset"):
        if reset_license():
            print("[SUKSES] Lisensi aplikasi berhasil di-reset. Aplikasi sekarang berada dalam status belum diaktivasi.")
        else:
            print("[GAGAL] Gagal me-reset lisensi.")
    else:
        mid = get_machine_id()
        is_act, msg, _ = is_activated()
        print(f"Machine ID: {mid}")
        print(f"Status Lisensi: {msg}")
        print("\nTip: Jalankan 'python license_manager.py --reset' untuk me-reset lisensi kembali ke awal.")


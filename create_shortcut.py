"""
Script Pembuat Shortcut Desktop Windows dengan Icon Logo PlantBase
"""
import os
import sys
import subprocess

def get_desktop_dir():
    # Cek via powershell / special folder
    candidates = [
        os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive", "Desktop"),
        os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]

def create_desktop_shortcut():
    desktop = get_desktop_dir()
    if not os.path.exists(desktop):
        os.makedirs(desktop, exist_ok=True)

    proj_dir = os.path.dirname(os.path.abspath(__file__))
    ico_path = os.path.join(proj_dir, "assets", "app_logo.ico")
    shortcut_path = os.path.join(desktop, "PlantBase AKP Beton.lnk")
    exe_dist = os.path.join(proj_dir, "dist", "AKP Contruction Building.exe")

    # Temukan executable pythonw untuk menjalankan tanpa konsol hitam
    py_executable = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(py_executable):
        py_executable = sys.executable

    main_py = os.path.join(proj_dir, "main.py")

    ps_command = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
if (Test-Path '{exe_dist}') {{
    $Shortcut.TargetPath = '{exe_dist}'
    $Shortcut.WorkingDirectory = '{proj_dir}\\dist'
}} else {{
    $Shortcut.TargetPath = '{py_executable}'
    $Shortcut.Arguments = '\"{main_py}\"'
    $Shortcut.WorkingDirectory = '{proj_dir}'
}}
$Shortcut.IconLocation = '{ico_path}, 0'
$Shortcut.Description = 'PlantBase - Sistem Manajemen Batching Plant'
$Shortcut.Save()
"""

    res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_command], capture_output=True, text=True)
    if os.path.exists(shortcut_path):
        print(f"[SUKSES] Shortcut berhasil dibuat di Desktop:\n{shortcut_path}")
        print(f"Icon terpasang: {ico_path}")
        return True
    else:
        print(f"[GAGAL] Gagal membuat shortcut. Error:\n{res.stderr}")
        return False

if __name__ == "__main__":
    create_desktop_shortcut()

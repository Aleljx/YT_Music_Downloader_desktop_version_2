"""Создание ярлыка программы на рабочем столе (только Windows, без доп. зависимостей —
через PowerShell и COM-объект WScript.Shell)."""

import os
import subprocess
import sys

from app import config

SHORTCUT_NAME = "YouTube Music Downloader.lnk"


def _ps_quote(text: str) -> str:
    """Строка в одинарных кавычках PowerShell (внутренние ' удваиваются)."""
    return "'" + text.replace("'", "''") + "'"


def _launch_target() -> tuple[str, str]:
    """(что запускать, аргументы). Для собранного exe — он сам, иначе pythonw + main.py."""
    if getattr(sys, "frozen", False):
        return sys.executable, ""
    exe = sys.executable
    pythonw = os.path.join(os.path.dirname(exe), "pythonw.exe")  # без чёрного окна консоли
    if os.path.exists(pythonw):
        exe = pythonw
    main_py = os.path.join(config.BASE_DIR, "main.py")
    return exe, f'"{main_py}"'


def build_powershell_script() -> str:
    target, args = _launch_target()
    lines = [
        "$desktop = [Environment]::GetFolderPath('Desktop')",  # учитывает перенос в OneDrive
        f"$path = Join-Path $desktop {_ps_quote(SHORTCUT_NAME)}",
        "$sh = New-Object -ComObject WScript.Shell",
        "$lnk = $sh.CreateShortcut($path)",
        f"$lnk.TargetPath = {_ps_quote(target)}",
        f"$lnk.Arguments = {_ps_quote(args)}",
        f"$lnk.WorkingDirectory = {_ps_quote(config.BASE_DIR)}",
        "$lnk.Description = 'YouTube Music Downloader'",
    ]
    if os.path.exists(config.ICON_PATH):
        lines.append(f"$lnk.IconLocation = {_ps_quote(config.ICON_PATH)}")
    lines += ["$lnk.Save()", "Write-Output $path"]
    return "; ".join(lines)


def create_desktop_shortcut() -> tuple[bool, str]:
    """Возвращает (успех, путь к ярлыку или текст ошибки)."""
    if os.name != "nt":
        return False, "Ярлыки на рабочем столе поддерживаются только в Windows"
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", build_powershell_script()],
            capture_output=True, encoding="utf-8", errors="replace", timeout=20, startupinfo=si,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)[:200]
    if result.returncode != 0:
        return False, (result.stderr or "не удалось создать ярлык").strip()[:200]
    return True, result.stdout.strip()
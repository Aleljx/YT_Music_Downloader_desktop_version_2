"""
Проверка обновлений yt-dlp / ffmpeg при запуске.

yt-dlp публикует релизы с тегом == версии (например "2025.01.15"),
поэтому для него достаточно сравнить `yt-dlp --version` с тегом
последнего релиза на GitHub.

У ffmpeg-сборок (BtbN/FFmpeg-Builds) номера версии как такового нет —
есть git-хэш коммита ffmpeg, из которого собран билд. Он виден и в
`ffmpeg -version` (например "...N-121374-g1a2b3c4d..."), и в описании
последнего релиза на GitHub — сравниваем эти хэши.

Если по какой-то причине (нет сети, не удалось распарсить) сравнить
не получилось — компонент считается АКТУАЛЬНЫМ (не обновляем),
чтобы не долбить лишними скачиваниями на ровном месте.
"""

import json
import os
import re
import subprocess
import urllib.request

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.config import FFMPEG_PATH, YTDLP_PATH

YTDLP_LATEST_RELEASE_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
FFMPEG_LATEST_RELEASE_API = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"

REQUEST_TIMEOUT_SEC = 10


def _startupinfo():
    if os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return si
    return None


def _fetch_json(url: str) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SEC) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


# ─────────────────────────────────────────────
#  yt-dlp — сравнение по версии (теги совпадают 1 в 1)
# ─────────────────────────────────────────────
def get_local_ytdlp_version() -> str | None:
    try:
        result = subprocess.run(
            [YTDLP_PATH, "--version"], capture_output=True, encoding="utf-8", errors="replace",
            timeout=REQUEST_TIMEOUT_SEC, startupinfo=_startupinfo(),
        )
        return result.stdout.strip() or None
    except Exception:
        return None


def get_latest_ytdlp_version() -> str | None:
    data = _fetch_json(YTDLP_LATEST_RELEASE_API)
    return data.get("tag_name") if data else None


# ─────────────────────────────────────────────
#  ffmpeg — сравнение по git-хэшу коммита, на котором собран билд
# ─────────────────────────────────────────────
_HASH_RE = re.compile(r"-g([0-9a-f]{7,})", re.IGNORECASE)


def get_local_ffmpeg_hash() -> str | None:
    try:
        result = subprocess.run(
            [FFMPEG_PATH, "-version"], capture_output=True, encoding="utf-8", errors="replace",
            timeout=REQUEST_TIMEOUT_SEC, startupinfo=_startupinfo(),
        )
        first_line = result.stdout.splitlines()[0] if result.stdout else ""
        match = _HASH_RE.search(first_line)
        return match.group(1) if match else None
    except Exception:
        return None


def get_latest_ffmpeg_hash() -> str | None:
    data = _fetch_json(FFMPEG_LATEST_RELEASE_API)
    if not data:
        return None
    text = f"{data.get('name', '')} {data.get('body', '')}"
    match = _HASH_RE.search(text)
    return match.group(1) if match else None


def hashes_differ(local_hash: str, remote_hash: str) -> bool:
    """Хэши могут быть обрезаны по-разному (7 vs 9+ символов) — сравниваем по общей длине."""
    n = min(len(local_hash), len(remote_hash))
    if n == 0:
        return False
    return local_hash[:n].lower() != remote_hash[:n].lower()


# ─────────────────────────────────────────────
#  Воркер проверки (выполняется в фоне при старте приложения)
# ─────────────────────────────────────────────
class UpdateCheckWorker(QThread):
    """
    Проверяет yt-dlp и ffmpeg на наличие обновлений (поход в сеть).
    Если компонента ещё нет на диске (missing_dependencies уже его поймал
    и SetupWindow его поставит) — такой компонент из проверки пропускаем,
    чтобы не делать двойную работу.

    finished эмитит список имён файлов, которые нужно обновить —
    пустой список означает "всё актуально, обновлять нечего".
    """

    finished = pyqtSignal(list)  # например ["yt-dlp.exe"] или []
    log_line = pyqtSignal(str)   # для debug-панели главного окна

    def run(self) -> None:
        outdated: list[str] = []

        if os.path.exists(YTDLP_PATH):
            local_v = get_local_ytdlp_version()
            remote_v = get_latest_ytdlp_version()
            self.log_line.emit(f"[update-check] yt-dlp: локальная={local_v!r}, последняя={remote_v!r}")
            if local_v and remote_v and local_v != remote_v:
                outdated.append("yt-dlp.exe")

        if os.path.exists(FFMPEG_PATH):
            local_h = get_local_ffmpeg_hash()
            remote_h = get_latest_ffmpeg_hash()
            self.log_line.emit(f"[update-check] ffmpeg: локальный хэш={local_h!r}, последний хэш={remote_h!r}")
            if local_h and remote_h and hashes_differ(local_h, remote_h):
                outdated.append("ffmpeg.exe")

        self.finished.emit(outdated)


# ─────────────────────────────────────────────
#  Лёгкий сплэш на время сетевой проверки
# ─────────────────────────────────────────────
class UpdateCheckSplash(QWidget):
    """
    Маленькое окно "Проверяем обновления...", видимое только на время
    самой проверки (обычно 1-3 сек, но сетевая операция может занять
    и больше — без этого окна пользователь в этот момент видел бы пустоту).
    main.py закрывает его сразу после получения результата проверки.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("YouTube Music Downloader")
        self.resize(320, 100)
        layout = QVBoxLayout(self)
        label = QLabel("Проверяем обновления yt-dlp и ffmpeg...")
        label.setWordWrap(True)
        layout.addWidget(label)
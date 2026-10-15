"""
Пути к ресурсам приложения, а также загрузка/сохранение
пользовательских настроек и истории загрузок.

Модуль не зависит от UI-фреймворка — его можно использовать
как из PyQt6, так и в тестах без запуска GUI.
"""

import json
import os
import shutil
import sys
from typing import Any


# ─────────────────────────────────────────────
#  Базовые пути
# ─────────────────────────────────────────────
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

APP_NAME = "YouTubeMusicDownloader"


def _user_data_dir() -> str:
    """Папка пользователя для данных приложения: %LOCALAPPDATA%\\YouTubeMusicDownloader (Windows)."""
    if os.name == "nt":
        root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
    else:
        root = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(root, APP_NAME)


# Всё, что нужно программе для работы (настройки, история, yt-dlp, ffmpeg, ffprobe),
# лежит здесь, а не рядом с программой: так работает автообновление без прав
# администратора, а переустановка/сборка в один exe ничего не стирает.
APP_DATA_DIR = _user_data_dir()
os.makedirs(APP_DATA_DIR, exist_ok=True)

YTDLP_PATH = os.path.join(APP_DATA_DIR, "yt-dlp.exe")
FFMPEG_PATH = os.path.join(APP_DATA_DIR, "ffmpeg.exe")
FFPROBE_PATH = os.path.join(APP_DATA_DIR, "ffprobe.exe")


def _find_icon() -> str:
    """Иконка — часть самой программы. Ищем icon.ico в корне проекта и в типичных
    подпапках; если не нашли, возвращаем путь в корне (файла может не быть)."""
    here = os.path.dirname(os.path.abspath(__file__))  # папка app/
    for folder in (BASE_DIR, here, *(os.path.join(BASE_DIR, d) for d in ("assets", "resources", "icons", "img", "images"))):
        path = os.path.join(folder, "icon.ico")
        if os.path.exists(path):
            return path
    return os.path.join(BASE_DIR, "icon.ico")


ICON_PATH = _find_icon()

HISTORY_FILE = os.path.join(APP_DATA_DIR, "history.json")
SETTINGS_FILE = os.path.join(APP_DATA_DIR, "settings.json")

# Названия файлов, которые приложение хранит в APP_DATA_DIR (показываются пользователю)
DATA_FILE_NAMES = ["settings.json", "history.json", "yt-dlp.exe", "ffmpeg.exe", "ffprobe.exe"]


def _migrate_old_files() -> None:
    """Однократно переносит settings.json/history.json из папки рядом с программой
    (старое расположение), если в новой папке их ещё нет."""
    for name in ("settings.json", "history.json"):
        old, new = os.path.join(BASE_DIR, name), os.path.join(APP_DATA_DIR, name)
        if os.path.exists(old) and not os.path.exists(new):
            try:
                shutil.copy2(old, new)
            except OSError:
                pass


_migrate_old_files()

YTDLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/"
    "latest/ffmpeg-master-latest-win64-gpl.zip"
)

DEFAULT_ACCENT_COLOR = "#1f6aa5"


def default_music_folder() -> str:
    """Папка для сохранения по умолчанию (Музыка пользователя)."""
    if os.name == "nt":
        return os.path.expanduser("~\\Music")
    return os.path.expanduser("~/Music")


# ─────────────────────────────────────────────
#  Настройки приложения
# ─────────────────────────────────────────────
class Settings:
    """Хранилище пользовательских настроек с автосохранением в JSON."""

    def __init__(self) -> None:
        self.accent_color: str = DEFAULT_ACCENT_COLOR
        self.save_folder: str = default_music_folder()
        self.appearance_mode: str = "System"  # "Light" | "Dark" | "System"
        self._load()

    def _load(self) -> None:
        data = self._read_json(SETTINGS_FILE)
        if not data:
            return
        self.accent_color = data.get("accent_color", self.accent_color)
        self.save_folder = data.get("save_folder", self.save_folder)
        self.appearance_mode = data.get("appearance_mode", self.appearance_mode)

    def save(self) -> None:
        self._write_json(SETTINGS_FILE, {
            "accent_color": self.accent_color,
            "save_folder": self.save_folder,
            "appearance_mode": self.appearance_mode,
        })

    @staticmethod
    def _read_json(path: str) -> dict[str, Any]:
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _write_json(path: str, data: dict[str, Any]) -> None:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except OSError:
            pass


# ─────────────────────────────────────────────
#  История загрузок
# ─────────────────────────────────────────────
class History:
    """Список последних загрузок (максимум MAX_ITEMS), с автосохранением."""

    MAX_ITEMS = 100

    def __init__(self) -> None:
        self.items: list[dict[str, str]] = self._load()

    def _load(self) -> list[dict[str, str]]:
        if not os.path.exists(HISTORY_FILE):
            return []
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return []

    def save(self) -> None:
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.items, f, ensure_ascii=False, indent=4)
        except OSError:
            pass

    def add(self, title: str, url: str, timestamp: str) -> None:
        self.items.insert(0, {"title": title, "url": url, "time": timestamp})
        self.items = self.items[: self.MAX_ITEMS]
        self.save()

    def clear(self) -> None:
        self.items.clear()
        self.save()


def missing_dependencies() -> list[str]:
    """Возвращает список отсутствующих внешних утилит (yt-dlp / ffmpeg)."""
    missing = []
    if not os.path.exists(YTDLP_PATH):
        missing.append("yt-dlp.exe")
    if not os.path.exists(FFMPEG_PATH):
        missing.append("ffmpeg.exe")
    return missing
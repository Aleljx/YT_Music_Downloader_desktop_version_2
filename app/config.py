"""
Пути к ресурсам приложения, а также загрузка/сохранение пользовательских настроек и истории загрузок.

Модуль не зависит от UI-фреймворка - его можно использовать как из PyQt6, так и в тестах без запуска GUI.
"""

import json
import os
import sys
from typing import Any

#--------------------#
#    Базовые пути    #
#--------------------#

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

YTDLP_PATH = os.path.join(BASE_DIR, "yt-dlp.exe")
FFMPEG_PATH = os.path.join(BASE_DIR, "ffmpeg.exe")
ICON_PATH = os.path.join(BASE_DIR, "icon.ico")

HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

YTDLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

DEFUALT_ACCENT_COLOR = "#1f6aa5"

def defualt_music_folder() -> str:
    """Папка для сохранения по умоланию (Музыка пользователя)."""
    if os.name == "nt":
        return os.path.expanduser("~\\Music")
    return os.path.expanduser("~/Music")

#----------------------------#
#    Настройка приложения    #
#----------------------------#

class Settings:
    """"Хранилище пользовательских настроек приложения с автосохранением в JSON."""

    def __init__(self) -> None:
        self.accent_color: str = DEFUALT_ACCENT_COLOR
        self.save_folder: str = defualt_music_folder()
        self.apperance_mode: str = "System"  # "Light", "Dark", "System"
        self._load()

    def _load(self) -> None:
        data = self._read_json(SETTINGS_FILE)
        if not data:
            return
        self.accent_color = data.get("accent_color", self.accent_color)
        self.save_folder = data.get("save_folder", self.save_folder)
        self.apperance_mode = data.get("apperance_mode", self.apperance_mode)

    def save(self) -> None:
        self.write_json(SETTINGS_FILE, {
            "accent_color": self.accent_color,
            "save_folder": self.save_folder,
            "apperance_mode": self.apperance_mode,
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
    def write_json(path: str, data: dict[str, Any]) -> None:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except OSError:
            pass

#------------------------#
#    История загрузок    #
#------------------------#

class History:
    """Список последних загрузок (максимум MAX_ITEMS), с автосохранением."""

    MAX_ITEMS = 100

    def __init__(self) -> None:
        self.item: list[dict[str, str]] = self._load()

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

    
    def missing_dependencies() -> list[str]:
        """Возвращает список отсутвующих внешних утилит (yt-dlp / ffmpeg)."""
        missing = []
        if not os.path.exists(YTDLP_PATH):
            missing.append("yt-dlp.exe")
        if not os.path.exists(FFMPEG_PATH):
            missing.append("ffmpeg.exe")
        return missing
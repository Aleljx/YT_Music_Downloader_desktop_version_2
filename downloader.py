"""
QThread-воркеры для взаимодействия с yt-dlp / ffmpeg.
 
Каждый воркер выполняет одну операцию в фоновом потоке и сообщает
результат через сигналы — никакого прямого обращения к виджетам
из фонового потока (в отличие от старого `self.after(0, lambda: ...)`
в customtkinter-версии).
"""

import json
import os
import subprocess
import urllib.request

from PyQt6.QtCore import QThread, pyqtSignal

from app.config import BASE_DIR, YTDLP_PATH


def _startupinfo():
    """Прячет консольное окно yt-dlp на Windows."""
    if os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return si
    return None

def _subprocess_env() -> dict:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return env

#-------------------------------------------#
#    Получение метаданных трека по ссылке   #
#-------------------------------------------#

class MetadataWorker(QThread):
    """Запрашивает title/artist/duration/обложку по ссылке через yt-dlp --dump-json."""

    finished = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            result = subprocess.run(
                [YTDLP_PATH, "--dump-json", "--no-playlist", self.url],
                capture_output=True, encoding="utf-8", errors="replace",
                timeout=20, startupinfo=_startupinfo(),
            )
            data = json.loads(result.stdout)

            title = data.get("title", "Неизвестно")
            artist = data.get("artist") or data.get("uploader") or "Неизвестно"
            duration_sec = data.get("duration", 0)
            duration = (
                f"{int(duration_sec) // 60}:{int(duration_sec) % 60:02d}"
                if duration_sec else ""
            )

            thumb_url = data.get("thumbnail") or ""
            for t in reversed(data.get("thumbnails", [])):
                if t.get("width") and t.get("height") and t["width"] == t["height"]:
                    thumb_url = t["url"]
                    break

            thumb_bytes = None
            if thumb_url:
                try:
                    with urllib.request.urlopen(thumb_url, timeout=10) as resp:
                        thumb_bytes = resp.read()
                except Exception:
                    thumb_bytes = None

            self.finished.emit({
                "title": title,
                "artist": artist,
                "duration": duration,
                "thumb_bytes": thumb_bytes,
                "url": self.url,
            })
        except Exception as e:
            self.failed.emit(str(e)[:80])

#------------------------#
#    Скачивание трека    #
#------------------------#

class DownloadWorker(QThread):
    """Скачивает и конвертирует трек в mp3, сообщая прогресс по ходу дела."""

    progress = pyqtSignal(float, str)  # доля 0..1, доп. инфо ("3.1 MB/s")
    finished = pyqtSignal(bool)  # True — успех

    def __init__(self, url: str, save_folder: str, parent=None) -> None:
        super().__init__(parent)
        self.url = url
        self.save_folder = save_folder

    def run(self) -> None:
        output_template = os.path.join(
            self.save_folder, "%(artist,uploader)s - %(title)s.%(ext)s"
        )
        command = [
            YTDLP_PATH, "-f", "ba", "-x",
            "--audio-format", "mp3", "--audio-quality", "0",
            "--embed-thumbnail", "--embed-metadata",
            "--convert-thumbnails", "jpg",
            "--ffmpeg-location", BASE_DIR,
            "--ppa", "ThumbnailsConvertor:-vf crop=ih:ih",
            "--newline", "-o", output_template, self.url,
        ]
        try:
            proc = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                encoding="utf-8", errors="replace",
                env=_subprocess_env(), startupinfo=_startupinfo(),
            )
            for line in proc.stdout:
                line = line.strip()
                if "[download]" in line and "%" in line:
                    try:
                        pct = float(line.split("%")[0].split()[-1]) / 100.0
                        info = line.split("at")[1].strip() if "at" in line else ""
                        self.progress.emit(pct, info)
                    except (ValueError, IndexError):
                        pass
            proc.wait()
            self.progress.emit(1.0, "")
            self.finished.emit(proc.returncode == 0)
        except Exception:
            self.finished.emit(False)

#---------------------------------------------#
#    Поиск треков - YouTube и YouTube Music   #
#---------------------------------------------#
#search_prefix -> (source_id, шаблон ссылки на watch-страницу)

_SEARCH_SOURCES = {
    "ytsearch5:": ("youtube", "https://www.youtube.com/watch?v={id}"),
    "ytmsearch5:": ("youtube_music", "https://music.youtube.com/watch?v={id}"), 
}

class SearchWorker(QThread):
    """
    Ищет до 5 треков по текстовому запросу — сразу на обычном YouTube
    и на YouTube Music — и возвращает объединённый список.
    """

    finished = pyqtSignal(list) #[{title, url, source}, ...]
    # source: "youtube" | "youtube_music" — по этому полю UI выбирает иконку

    def __init__(self, query: str, parent=None) -> None:
        super().__init__(parent)
        self.query = query

    def run(self) -> None:
        results = []
        for prefix, (source_id, url_template) in _SEARCH_SOURCES.items():
            results.extend(self._search_one(prefix, source_id, url_template))
        self.finished.emit(results)

    def _search_one(self, prefix: str, source: str, url_template: str) -> list[dict]:
        try:
            command = [YTDLP_PATH, prefix + self.query, "--dump-json", "--flat-playlist"]
            proc = subprocess.run(
                command, capture_output=True, encoding="utf-8", errors="replace",
                startupinfo=_startupinfo(),
            )
            items = []
            for line in proc.stdout.splitlines():
                if not line.strip():
                    continue
                data = json.loads(line)
                video_id = data.get("id")
                if not video_id:
                    continue
                items.append({
                    "title": data.get("title", "Неизвестно"),
                    "url": url_template.format(id=video_id),
                    "source": source,
                })
            return items
        except Exception:
            return []
        
#------------------------------------------------------#
#    Аудио-превью — получение прямой ссылки на поток   #
#------------------------------------------------------#

class PreviewStreamWorker(QThread):
    """Резолвит прямую ссылку на аудиопоток для предпрослушивания."""

    finished = pyqtSignal(str)  # прямая ссылка на поток ("" — ошибка)

    def __init__(self, url: str, parent=None) -> None:
        super().__init__(parent)
        self.url = url

    def run(self) -> None:
        try:
            cmd = [YTDLP_PATH, "-g", "-f", "ba", self.url]
            proc = subprocess.run(
                cmd, capture_output=True, encoding="utf-8", errors="replace",
                startupinfo=_startupinfo(),
            )
            self.finished.emit(proc.stdout.strip())
        except Exception:
            self.finished.emit(""

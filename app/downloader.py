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
import sys
import tempfile
import traceback
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtCore import QThread, pyqtSignal

from app.config import BASE_DIR, YTDLP_PATH
from app.image_utils import process_cover_image


def _startupinfo():
    """Прячет консольное окно yt-dlp на Windows. На других ОС не нужно."""
    if os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return si
    return None


def _subprocess_env() -> dict:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return env


# ─────────────────────────────────────────────
#  Получение метаданных трека по ссылке
# ─────────────────────────────────────────────
class MetadataWorker(QThread):
    """Запрашивает title/artist/duration/обложку по ссылке через yt-dlp --dump-json."""

    finished = pyqtSignal(dict)   # {title, artist, duration, thumb_bytes, url}
    failed = pyqtSignal(str)

    def __init__(self, url: str, parent=None) -> None:
        super().__init__(parent)
        self.url = url

    def run(self) -> None:
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
                        raw = resp.read()
                    # Прогоняем через обрезку чёрных полос — многие авто-превью
                    # YouTube для музыки вписывают квадратную обложку в кадр 16:9
                    # с чёрными полями прямо в пикселях, простого вписывания
                    # в квадратный виджет для этого недостаточно.
                    thumb_bytes = process_cover_image(raw) or raw
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


# ─────────────────────────────────────────────
#  Скачивание трека
# ─────────────────────────────────────────────
class DownloadWorker(QThread):
    """
    Скачивает и конвертирует трек в mp3, сообщая прогресс по ходу дела.

    Обложку встраиваем сами (через mutagen), а не через
    yt-dlp/ffmpeg (`--embed-thumbnail`) — так мы можем передать уже
    обрезанную от чёрных полос картинку (см. app.image_utils),
    а не сырое превью с YouTube.
    """

    progress = pyqtSignal(float, str)  # доля 0..1, доп. инфо ("3.1 MB/s")
    finished = pyqtSignal(bool, bool)  # (успех скачивания, обложка встроена)

    def __init__(self, url: str, save_folder: str, thumb_bytes: bytes | None = None, parent=None) -> None:
        super().__init__(parent)
        self.url = url
        self.save_folder = save_folder
        self.thumb_bytes = thumb_bytes  # уже обработанные (без чёрных полос, квадратные) байты обложки

    def run(self) -> None:
        output_template = os.path.join(
            self.save_folder, "%(artist,uploader)s - %(title)s.%(ext)s"
        )

        # Путь к финальному файлу получаем через --print-to-file, а не через
        # парсинг stdout: имя файла может содержать кириллицу/иероглифы
        # (как в этом примере — "Coda, Saori Kodama, 大森俊之"), а кодировка
        # консоли Windows не всегда UTF-8 — при парсинге строки из stdout
        # такие символы могли бы превращаться в "битые" и путь переставал
        # совпадать с реальным файлом на диске. Запись в файл этого не имеет.
        filepath_tmp = os.path.join(
            tempfile.gettempdir(), f"ytmusicdl_path_{os.getpid()}_{id(self)}.txt"
        )
        if os.path.exists(filepath_tmp):
            try:
                os.remove(filepath_tmp)
            except OSError:
                pass

        command = [
            YTDLP_PATH, "-f", "ba", "-x",
            "--audio-format", "mp3", "--audio-quality", "0",
            "--embed-metadata",
            "--ffmpeg-location", BASE_DIR,
            "--newline", "-o", output_template,
            "--print-to-file", "after_move:filepath", filepath_tmp,
            self.url,
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
            success = proc.returncode == 0

            cover_embedded = False
            if success and self.thumb_bytes:
                mp3_path = self._read_output_filepath(filepath_tmp)
                if mp3_path and os.path.isfile(mp3_path):
                    cover_embedded = _embed_cover(mp3_path, self.thumb_bytes)
                else:
                    print(
                        f"[downloader] Не удалось определить путь к скачанному файлу "
                        f"(mp3_path={mp3_path!r}) — обложка не встроена.",
                        file=sys.stderr,
                    )

            self.finished.emit(success, cover_embedded)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            self.finished.emit(False, False)
        finally:
            try:
                if os.path.exists(filepath_tmp):
                    os.remove(filepath_tmp)
            except OSError:
                pass

    @staticmethod
    def _read_output_filepath(tmp_path: str) -> str | None:
        try:
            with open(tmp_path, "r", encoding="utf-8") as f:
                return f.readline().strip()
        except OSError:
            return None

    def _find_output_file(lines: list[str]) -> str | None:
        # УСТАРЕЛО: заменено на _read_output_filepath + --print-to-file (см. выше),
        # оставлено на случай отладки старого поведения. Не используется.
        for line in reversed(lines):
            if line and os.path.isfile(line):
                return line
        return None


def _embed_cover(mp3_path: str, jpeg_bytes: bytes) -> bool:
    """
    Встраивает обложку (уже обрезанную от чёрных полос) в ID3-тег mp3-файла.
    Возвращает True при успехе. Ошибка не должна ронять всё скачивание
    (трек и так уже сохранён), но должна быть видна в консоли — раньше
    она проглатывалась молча, что затрудняло диагностику.
    """
    try:
        from mutagen.id3 import ID3, APIC, ID3NoHeaderError

        try:
            tags = ID3(mp3_path)
        except ID3NoHeaderError:
            tags = ID3()

        tags.delall("APIC")
        tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=jpeg_bytes))
        tags.save(mp3_path, v2_version=3)
        return True
    except Exception as e:
        # Обложка необязательна — сам трек уже скачан, это не должно ронять
        # весь процесс, но ошибку важно видеть в консоли для диагностики.
        print(f"[downloader] Не удалось встроить обложку в '{mp3_path}': {e}", file=sys.stderr)
        return False


# ─────────────────────────────────────────────
#  Поиск треков — YouTube и YouTube Music
# ─────────────────────────────────────────────
# search_prefix -> (source_id, шаблон ссылки на watch-страницу)
_SEARCH_SOURCES = {
    "ytsearch5:": ("youtube", "https://www.youtube.com/watch?v={id}"),
    "ytmsearch5:": ("youtube_music", "https://music.youtube.com/watch?v={id}"),
}


class SearchWorker(QThread):
    """
    Ищет до 5 треков по текстовому запросу — сразу на обычном YouTube
    и на YouTube Music — и возвращает объединённый список.

    Оба запроса идут параллельно (а не один за другим) и с таймаутом —
    раньше без таймаута сетевой затык внутри yt-dlp мог "подвесить" поиск
    навсегда, а UI продолжал показывать "Ищем...".
    """

    finished = pyqtSignal(list)  # [{title, url, source}, ...]
    failed = pyqtSignal(str)
    # source: "youtube" | "youtube_music" — по этому полю UI выбирает иконку

    SEARCH_TIMEOUT_SEC = 15

    def __init__(self, query: str, parent=None) -> None:
        super().__init__(parent)
        self.query = query

    def run(self) -> None:
        try:
            with ThreadPoolExecutor(max_workers=len(_SEARCH_SOURCES)) as pool:
                futures = [
                    pool.submit(self._search_one, prefix, source_id, url_template)
                    for prefix, (source_id, url_template) in _SEARCH_SOURCES.items()
                ]
                results = []
                for future in futures:
                    results.extend(future.result())
            self.finished.emit(results)
        except Exception as e:
            self.failed.emit(str(e)[:120])
            self.finished.emit([])

    def _search_one(self, prefix: str, source_id: str, url_template: str) -> list[dict]:
        try:
            command = [YTDLP_PATH, prefix + self.query, "--dump-json", "--flat-playlist"]
            proc = subprocess.run(
                command, capture_output=True, encoding="utf-8", errors="replace",
                startupinfo=_startupinfo(), timeout=self.SEARCH_TIMEOUT_SEC,
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
                    "source": source_id,
                })
            return items
        except subprocess.TimeoutExpired:
            return []
        except Exception:
            return []


# ─────────────────────────────────────────────
#  Аудио-превью — получение прямой ссылки на поток
# ─────────────────────────────────────────────
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
                startupinfo=_startupinfo(), timeout=20,
            )
            self.finished.emit(proc.stdout.strip())
        except Exception:
            self.finished.emit("")
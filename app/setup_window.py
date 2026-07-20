"""
Окно первого запуска.

Показывается, если в папке приложения нет yt-dlp.exe и/или ffmpeg.exe
(см. app.config.missing_dependencies). Скачивает недостающее в фоновом
потоке и сообщает прогресс через сигналы — сам процесс скачивания и
распаковки вынесен в DependencyDownloadWorker, окно только отображает
результат.
"""

import os
import shutil
import tempfile
import urllib.request
import zipfile

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from app import config


# ─────────────────────────────────────────────
#  Воркер: скачивание + распаковка зависимостей
# ─────────────────────────────────────────────
class DependencyDownloadWorker(QThread):
    """
    Скачивает недостающие yt-dlp.exe / ffmpeg.exe в BASE_DIR.
    Работает по списку missing (например ["yt-dlp.exe", "ffmpeg.exe"]).
    """

    status = pyqtSignal(str)          # "Скачивание yt-dlp..."
    progress = pyqtSignal(float)      # 0..1 для текущего файла
    finished = pyqtSignal(bool, str)  # (успех, сообщение об ошибке если есть)

    def __init__(self, missing: list[str], parent=None) -> None:
        super().__init__(parent)
        self.missing = missing

    def run(self) -> None:
        try:
            if "yt-dlp.exe" in self.missing:
                self.status.emit("Скачивание yt-dlp...")
                self._download_file(config.YTDLP_URL, config.YTDLP_PATH)

            if "ffmpeg.exe" in self.missing:
                self.status.emit("Скачивание ffmpeg...")
                self._download_and_extract_ffmpeg()

            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e)[:200])

    def _download_file(self, url: str, dest_path: str) -> None:
        with urllib.request.urlopen(url, timeout=30) as response:
            total = int(response.headers.get("Content-Length", 0)) or None
            downloaded = 0
            chunk_size = 256 * 1024
            tmp_path = dest_path + ".part"
            with open(tmp_path, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        self.progress.emit(downloaded / total)
            os.replace(tmp_path, dest_path)

    def _download_and_extract_ffmpeg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = os.path.join(tmp_dir, "ffmpeg.zip")
            self._download_file(config.FFMPEG_URL, zip_path)

            self.status.emit("Распаковка ffmpeg...")
            self.progress.emit(0.0)
            extract_dir = os.path.join(tmp_dir, "extracted")
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                for i, name in enumerate(names):
                    zf.extract(name, extract_dir)
                    self.progress.emit((i + 1) / len(names))

            ffmpeg_exe = self._find_file(extract_dir, "ffmpeg.exe")
            if not ffmpeg_exe:
                raise FileNotFoundError("ffmpeg.exe не найден в архиве после распаковки")
            shutil.copy(ffmpeg_exe, config.FFMPEG_PATH)

            # ffprobe тоже пригодится yt-dlp для чтения метаданных — копируем, если есть
            ffprobe_exe = self._find_file(extract_dir, "ffprobe.exe")
            if ffprobe_exe:
                ffprobe_dest = os.path.join(config.BASE_DIR, "ffprobe.exe")
                shutil.copy(ffprobe_exe, ffprobe_dest)

    @staticmethod
    def _find_file(root_dir: str, filename: str) -> str | None:
        for dirpath, _dirnames, filenames in os.walk(root_dir):
            if filename in filenames:
                return os.path.join(dirpath, filename)
        return None


# ─────────────────────────────────────────────
#  Само окно
# ─────────────────────────────────────────────
class SetupWindow(QWidget):
    """
    Окно первого запуска. Держит ссылку на self._worker, чтобы поток
    не был собран сборщиком мусора раньше времени.

    setup_finished эмитится один раз — по успешному завершению скачивания.
    main.py подписывается на него (setup_window.setup_finished.connect(...)),
    чтобы закрыть это окно и показать основное.
    """

    setup_finished = pyqtSignal()

    def __init__(self, missing: list[str]) -> None:
        super().__init__()
        self.missing = missing
        self._worker: DependencyDownloadWorker | None = None

        self.setWindowTitle("Первый запуск — установка компонентов")
        self.resize(420, 200)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Нужно скачать пару компонентов")
        title.setStyleSheet("font-size: 15px; font-weight: 600;")
        layout.addWidget(title)

        names = ", ".join(self.missing)
        description = QLabel(
            f"Отсутствуют: {names}.\n"
            "Это разовая установка, дальше приложение будет открываться сразу."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        self.status_label = QLabel("Готово к загрузке")
        self.status_label.setObjectName("secondary")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.start_btn = QPushButton("Начать установку")
        self.start_btn.setObjectName("accent")
        self.start_btn.clicked.connect(self._start_download)
        layout.addWidget(self.start_btn)

        self.retry_btn = QPushButton("Повторить")
        self.retry_btn.setObjectName("accent")
        self.retry_btn.clicked.connect(self._start_download)
        self.retry_btn.hide()
        layout.addWidget(self.retry_btn)

    def _start_download(self) -> None:
        self.start_btn.hide()
        self.retry_btn.hide()
        self.progress_bar.setValue(0)
        self.status_label.setText("Подготовка...")

        self._worker = DependencyDownloadWorker(self.missing)
        self._worker.status.connect(self.status_label.setText)
        self._worker.progress.connect(lambda f: self.progress_bar.setValue(int(f * 100)))
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_finished(self, ok: bool, error_message: str) -> None:
        if ok:
            self.status_label.setText("Готово!")
            self.setup_finished.emit()
        else:
            self.status_label.setText(f"Ошибка: {error_message}")
            self.retry_btn.show()
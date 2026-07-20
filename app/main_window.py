"""
Главное окно приложения.

Собирает воедино три ранее написанных модуля:
  - app.config     — настройки и история (чистая логика)
  - app.downloader — QThread-воркеры для yt-dlp
  - app.theme      — генерация QSS

Сам файл отвечает только за компоновку виджетов и обработку сигналов —
никакой логики работы с yt-dlp здесь напрямую нет, вся она вызывается
через воркеры.
"""

import datetime
import os

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QClipboard, QPixmap
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QProgressBar, QPushButton,
    QSizePolicy, QTabWidget, QVBoxLayout, QWidget,
)

from app import config, theme
from app.downloader import (
    DownloadWorker, MetadataWorker, PreviewStreamWorker, SearchWorker,
)

# Значки источника в результатах поиска — без внешних иконок, просто эмодзи-маркер
SOURCE_ICON = {
    "youtube": "▶",
    "youtube_music": "🎵",
}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = config.Settings()
        self.history = config.History()

        self.download_queue: list[dict] = []
        self.current_download_url: str | None = None
        self._compact = False

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)

        self.setWindowTitle("YouTube Music Downloader")
        self.resize(980, 560)

        self._build_ui()
        self._apply_theme()
        self._refresh_history_list()

    # ─────────────────────────────────────────────
    #  Сборка интерфейса
    # ─────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)

        header = self._build_header()
        root_layout.addLayout(header)

        columns = QHBoxLayout()
        columns.setSpacing(10)
        self.left_panel = self._build_left_panel()
        self.center_panel = self._build_center_panel()
        self.right_panel = self._build_right_panel()
        columns.addWidget(self.left_panel, 4)
        columns.addWidget(self.center_panel, 4)
        columns.addWidget(self.right_panel, 3)
        root_layout.addLayout(columns)

    def _build_header(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        title = QLabel("YouTube Music Downloader")
        title.setStyleSheet("font-size: 15px; font-weight: 600;")
        self.compact_btn = QPushButton("Компактный режим")
        self.compact_btn.clicked.connect(self._toggle_compact_mode)
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self.compact_btn)
        return layout

    def _panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("panel")
        return frame

    # ---- Левая панель: ссылка, папка, скачивание, тема ----
    def _build_left_panel(self) -> QFrame:
        panel = self._panel()
        layout = QVBoxLayout(panel)

        layout.addWidget(QLabel("Вставь ссылку на музыку"))
        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        paste_btn = QPushButton("📋")
        paste_btn.setFixedWidth(36)
        paste_btn.clicked.connect(self._paste_url)
        clear_btn = QPushButton("✕")
        clear_btn.setFixedWidth(36)
        clear_btn.clicked.connect(lambda: self.url_input.clear())
        url_row.addWidget(self.url_input)
        url_row.addWidget(paste_btn)
        url_row.addWidget(clear_btn)
        layout.addLayout(url_row)

        layout.addWidget(QLabel("Папка сохранения"))
        folder_row = QHBoxLayout()
        self.folder_label = QLabel(self.settings.save_folder)
        self.folder_label.setObjectName("secondary")
        self.folder_label.setWordWrap(True)
        browse_btn = QPushButton("Обзор")
        browse_btn.clicked.connect(self._choose_folder)
        folder_row.addWidget(self.folder_label, 1)
        folder_row.addWidget(browse_btn)
        layout.addLayout(folder_row)

        buttons_row = QHBoxLayout()
        self.download_now_btn = QPushButton("⬇ Скачать сейчас")
        self.download_now_btn.setObjectName("accent")
        self.download_now_btn.clicked.connect(self._download_now)
        self.add_queue_btn = QPushButton("＋ В очередь")
        self.add_queue_btn.clicked.connect(self._add_current_url_to_queue)
        buttons_row.addWidget(self.download_now_btn)
        buttons_row.addWidget(self.add_queue_btn)
        layout.addLayout(buttons_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("secondary")
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)

        layout.addWidget(QLabel("Цвет темы"))
        colors_row = QHBoxLayout()
        for color in theme.ACCENT_PRESETS:
            swatch = QPushButton()
            swatch.setFixedSize(22, 22)
            swatch.setStyleSheet(
                f"background-color: {color}; border-radius: 11px; border: none;"
            )
            swatch.clicked.connect(lambda _checked, c=color: self._set_accent_color(c))
            colors_row.addWidget(swatch)
        colors_row.addStretch()
        layout.addLayout(colors_row)

        layout.addStretch()
        return panel

    # ---- Центральная панель: вкладки ----
    def _build_center_panel(self) -> QFrame:
        panel = self._panel()
        layout = QVBoxLayout(panel)
        self.tabs = QTabWidget()

        # -- Поиск --
        search_tab = QWidget()
        search_layout = QVBoxLayout(search_tab)
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск музыки...")
        self.search_input.returnPressed.connect(self._run_search)
        search_btn = QPushButton("🔍")
        search_btn.setFixedWidth(36)
        search_btn.clicked.connect(self._run_search)
        search_row.addWidget(self.search_input)
        search_row.addWidget(search_btn)
        search_layout.addLayout(search_row)
        self.search_results_list = QListWidget()
        search_layout.addWidget(self.search_results_list)
        self.tabs.addTab(search_tab, "Поиск")

        # -- Очередь --
        queue_tab = QWidget()
        queue_layout = QVBoxLayout(queue_tab)
        self.queue_list = QListWidget()
        queue_layout.addWidget(self.queue_list)
        queue_buttons = QHBoxLayout()
        remove_btn = QPushButton("Удалить выбранное")
        remove_btn.clicked.connect(self._remove_selected_from_queue)
        queue_buttons.addWidget(remove_btn)
        queue_buttons.addStretch()
        queue_layout.addLayout(queue_buttons)
        self.tabs.addTab(queue_tab, "Очередь")

        # -- История --
        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        self.history_list = QListWidget()
        history_layout.addWidget(self.history_list)
        history_buttons = QHBoxLayout()
        clear_history_btn = QPushButton("Очистить историю")
        clear_history_btn.clicked.connect(self._clear_history)
        history_buttons.addWidget(clear_history_btn)
        history_buttons.addStretch()
        history_layout.addLayout(history_buttons)
        self.tabs.addTab(history_tab, "История")

        layout.addWidget(self.tabs)
        return panel

    # ---- Правая панель: обложка + превью ----
    def _build_right_panel(self) -> QFrame:
        panel = self._panel()
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.cover_label = QLabel()
        self.cover_label.setFixedSize(180, 180)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("border-radius: 8px; background-color: rgba(128,128,128,40);")
        self.cover_label.setText("🎵")
        cover_row = QHBoxLayout()
        cover_row.addStretch()
        cover_row.addWidget(self.cover_label)
        cover_row.addStretch()
        layout.addLayout(cover_row)

        self.track_title_label = QLabel("Название трека")
        self.track_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.track_title_label.setStyleSheet("font-weight: 600;")
        self.track_artist_label = QLabel("Исполнитель")
        self.track_artist_label.setObjectName("secondary")
        self.track_artist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.track_title_label)
        layout.addWidget(self.track_artist_label)

        self.preview_btn = QPushButton("▶ Предпрослушать")
        self.preview_btn.setObjectName("accent")
        self.preview_btn.clicked.connect(self._toggle_preview)
        layout.addWidget(self.preview_btn)

        layout.addStretch()
        return panel

    # ─────────────────────────────────────────────
    #  Тема
    # ─────────────────────────────────────────────
    def _apply_theme(self) -> None:
        theme.apply_theme(QApplication.instance(), self.settings.accent_color, self.settings.appearance_mode)

    def _set_accent_color(self, color: str) -> None:
        self.settings.accent_color = color
        self.settings.save()
        self._apply_theme()

    # ─────────────────────────────────────────────
    #  Ссылка / папка
    # ─────────────────────────────────────────────
    def _paste_url(self) -> None:
        text = QApplication.clipboard().text(QClipboard.Mode.Clipboard)
        if text:
            self.url_input.setText(text.strip())

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Выбери папку", self.settings.save_folder)
        if folder:
            self.settings.save_folder = folder
            self.settings.save()
            self.folder_label.setText(folder)

    # ─────────────────────────────────────────────
    #  Скачивание — сейчас / в очередь
    # ─────────────────────────────────────────────
    def _download_now(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            return
        self._start_download(url, title=None)

    def _add_current_url_to_queue(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            return
        self._add_to_queue(url, title=url)
        self.url_input.clear()

    def _add_to_queue(self, url: str, title: str) -> None:
        self.download_queue.append({"url": url, "title": title})
        item = QListWidgetItem(title)
        item.setData(Qt.ItemDataRole.UserRole, url)
        self.queue_list.addItem(item)
        self._maybe_process_queue()

    def _remove_selected_from_queue(self) -> None:
        for item in self.queue_list.selectedItems():
            url = item.data(Qt.ItemDataRole.UserRole)
            self.download_queue = [q for q in self.download_queue if q["url"] != url]
            self.queue_list.takeItem(self.queue_list.row(item))

    def _maybe_process_queue(self) -> None:
        if self.current_download_url is not None:
            return  # уже что-то качается — очередь подождёт
        if not self.download_queue:
            return
        next_item = self.download_queue[0]
        self._start_download(next_item["url"], title=next_item["title"], from_queue=True)

    def _start_download(self, url: str, title: str | None, from_queue: bool = False) -> None:
        if self.current_download_url is not None:
            # Уже идёт скачивание — просто добавим в очередь вместо параллельного запуска
            self._add_to_queue(url, title or url)
            return

        self.current_download_url = url
        self.download_now_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Подготовка...")

        self._download_worker = DownloadWorker(url, self.settings.save_folder)
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.finished.connect(
            lambda ok: self._on_download_finished(ok, url, title, from_queue)
        )
        self._download_worker.start()

    def _on_download_progress(self, fraction: float, info: str) -> None:
        self.progress_bar.setValue(int(fraction * 100))
        self.progress_label.setText(f"{int(fraction * 100)}% · {info}" if info else f"{int(fraction * 100)}%")

    def _on_download_finished(self, ok: bool, url: str, title: str | None, from_queue: bool) -> None:
        self.current_download_url = None
        self.download_now_btn.setEnabled(True)
        self.progress_label.setText("Готово" if ok else "Ошибка скачивания")

        if ok:
            entry_title = title or url
            self.history.add(entry_title, url, datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
            self._refresh_history_list()

        if from_queue and self.download_queue:
            self.download_queue.pop(0)
            self.queue_list.takeItem(0)

        self._maybe_process_queue()

    # ─────────────────────────────────────────────
    #  Поиск
    # ─────────────────────────────────────────────
    def _run_search(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            return
        self.search_results_list.clear()
        self.search_results_list.addItem("Ищем...")
        self._search_worker = SearchWorker(query)
        self._search_worker.finished.connect(self._on_search_finished)
        self._search_worker.start()

    def _on_search_finished(self, results: list[dict]) -> None:
        self.search_results_list.clear()
        if not results:
            self.search_results_list.addItem("Ничего не найдено")
            return
        for r in results:
            icon = SOURCE_ICON.get(r["source"], "")
            item = QListWidgetItem(f"{icon}  {r['title']}")
            item.setData(Qt.ItemDataRole.UserRole, r)
            self.search_results_list.addItem(item)
        self.search_results_list.itemDoubleClicked.connect(self._on_search_result_chosen)

    def _on_search_result_chosen(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        self._add_to_queue(data["url"], data["title"])

    # ─────────────────────────────────────────────
    #  История
    # ─────────────────────────────────────────────
    def _refresh_history_list(self) -> None:
        self.history_list.clear()
        for entry in self.history.items:
            self.history_list.addItem(f"{entry['time']} — {entry['title']}")

    def _clear_history(self) -> None:
        self.history.clear()
        self._refresh_history_list()

    # ─────────────────────────────────────────────
    #  Превью
    # ─────────────────────────────────────────────
    def _toggle_preview(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.preview_btn.setText("▶ Предпрослушать")
            return

        url = self.url_input.text().strip()
        if not url:
            return
        self.preview_btn.setText("⏳ Загрузка...")
        self._preview_worker = PreviewStreamWorker(url)
        self._preview_worker.finished.connect(self._on_preview_stream_ready)
        self._preview_worker.start()

        self._metadata_worker = MetadataWorker(url)
        self._metadata_worker.finished.connect(self._on_metadata_ready)
        self._metadata_worker.start()

    def _on_preview_stream_ready(self, stream_url: str) -> None:
        if not stream_url:
            self.preview_btn.setText("▶ Предпрослушать")
            return
        self.player.setSource(QUrl(stream_url))
        self.player.play()
        self.preview_btn.setText("⏸ Пауза")

    def _on_metadata_ready(self, data: dict) -> None:
        self.track_title_label.setText(data.get("title") or "Название трека")
        self.track_artist_label.setText(data.get("artist") or "Исполнитель")
        thumb_bytes = data.get("thumb_bytes")
        if thumb_bytes:
            pixmap = QPixmap()
            pixmap.loadFromData(thumb_bytes)
            side = min(pixmap.width(), pixmap.height())
            cropped = pixmap.copy(
                (pixmap.width() - side) // 2, (pixmap.height() - side) // 2, side, side
            )
            self.cover_label.setPixmap(
                cropped.scaled(
                    180, 180,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    # ─────────────────────────────────────────────
    #  Мини-режим
    # ─────────────────────────────────────────────
    def _toggle_compact_mode(self) -> None:
        self._compact = not self._compact
        self.center_panel.setVisible(not self._compact)
        self.right_panel.setVisible(not self._compact)
        self.compact_btn.setText("Полный режим" if self._compact else "Компактный режим")
        if self._compact:
            self.resize(360, 420)
        else:
            self.resize(980, 560)    
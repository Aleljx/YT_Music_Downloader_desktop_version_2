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

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtCore import QRect
from PyQt6.QtGui import QClipboard, QColor, QFontMetrics, QPixmap
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QProgressBar, QPushButton,
    QSizePolicy, QStyle, QStyledItemDelegate, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from app import config, theme
from app.about_window import AboutWindow
from app.background import BlobBackground
from app.confirm_dialog import confirm_clear_history, confirm_clear_queue, confirm_remove_from_queue
from app import i18n
from app.help_window import HelpWindow
from app.i18n import tr
from app.downloader import (
    DownloadWorker, MetadataWorker, PreviewStreamWorker, SearchWorker,
)

# Значки источника в результатах поиска — текстовый тег надёжнее эмодзи
# (эмодзи может не отрисоваться нужным шрифтом на некоторых системах Windows)
SOURCE_TAG = {
    "youtube": "[YouTube]",
    "youtube_music": "[YT Music]",
}


class HoverListWidget(QListWidget):
    """
    Обычный QListWidget умеет сообщать о наведении на конкретный элемент
    (itemEntered), но не сообщает, когда мышь покидает список целиком —
    а это нужно, чтобы вернуть превью в исходное состояние.
    """

    mouse_left = pyqtSignal()

    def leaveEvent(self, event) -> None:
        self.mouse_left.emit()
        super().leaveEvent(event)


REMOVE_BTN_SIZE = 22
REMOVE_BTN_MARGIN = 6


def _remove_btn_rect(item_rect: QRect) -> QRect:
    return QRect(
        item_rect.right() - REMOVE_BTN_MARGIN - REMOVE_BTN_SIZE,
        item_rect.center().y() - REMOVE_BTN_SIZE // 2,
        REMOVE_BTN_SIZE, REMOVE_BTN_SIZE,
    )


class _QueueDelegate(QStyledItemDelegate):
    """Рисует обычную строку и справа кнопку «✕» (без отдельных виджетов — надёжнее)."""

    def paint(self, painter, option, index) -> None:
        super().paint(painter, option, index)
        painter.save()
        rect = _remove_btn_rect(option.rect)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        painter.setPen(QColor("#d64545") if hovered else QColor("#888888"))
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), "✕")
        painter.restore()


class QueueListWidget(HoverListWidget):
    """Список очереди: клик по «✕» в строке сообщает remove_requested(item)."""

    remove_requested = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()
        self.setItemDelegate(_QueueDelegate(self))
        self.setMouseTracking(True)

    def _item_with_btn_at(self, pos):
        item = self.itemAt(pos)
        if item is not None and _remove_btn_rect(self.visualItemRect(item)).contains(pos):
            return item
        return None

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._item_with_btn_at(event.position().toPoint()):
            event.accept()  # клик по «✕» не должен выделять строку
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            item = self._item_with_btn_at(event.position().toPoint())
            if item is not None:
                self.remove_requested.emit(item)
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event) -> None:
        over = self._item_with_btn_at(event.position().toPoint()) is not None
        self.viewport().setCursor(Qt.CursorShape.PointingHandCursor if over else Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = config.Settings()
        # Язык интерфейса: сохранённый в настройках, иначе язык системы
        i18n.set_language(self.settings.language or i18n.detect_system_language())
        self.history = config.History()

        self.download_queue: list[dict] = []
        self.current_download_url: str | None = None
        self._compact = False
        self._previous_appearance = "System"

        # "Активный" трек — то, что реально будет скачано по кнопке "Скачать сейчас".
        # Устанавливается либо из поля ссылки, либо кликом по результату поиска —
        # они не могут быть источником одновременно (см. _on_url_input_changed
        # и _on_search_result_selected).
        self._active_url: str | None = None
        self._last_hovered_queue_url: str | None = None  # последний трек очереди под курсором

        # Кэш метаданных по ссылке, чтобы не запрашивать yt-dlp повторно
        # при каждом наведении мыши на один и тот же трек.
        self._metadata_cache: dict[str, dict] = {}
        # Держим ссылки на "фоновые" (не основные) воркеры метаданных,
        # чтобы Python не удалил их сборщиком мусора до завершения потока.
        self._active_metadata_workers: list[MetadataWorker] = []

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
        root = BlobBackground()
        self.background = root
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)

        header = self._build_header()
        root_layout.addLayout(header)

        # Единая строка статуса — сюда пишутся все фоновые действия программы:
        # "Собираем метаданные...", "Ищем треки...", "Скачивание..." и т.д.
        self.status_label = QLabel(tr("status.ready"))
        self.status_label.setObjectName("secondary")
        root_layout.addWidget(self.status_label)

        columns = QHBoxLayout()
        columns.setSpacing(10)
        self.left_panel = self._build_left_panel()
        self.center_panel = self._build_center_panel()
        self.right_panel = self._build_right_panel()
        columns.addWidget(self.left_panel, 4)
        columns.addWidget(self.center_panel, 4)
        columns.addWidget(self.right_panel, 3)
        root_layout.addLayout(columns)

        self.debug_panel = self._build_debug_panel()
        self.debug_panel.hide()
        root_layout.addWidget(self.debug_panel)

    def _build_debug_panel(self) -> QFrame:
        panel = self._panel()
        layout = QVBoxLayout(panel)

        header_row = QHBoxLayout()
        self.debug_title_label = QLabel(tr("ui.debug_log_title"))
        header_row.addWidget(self.debug_title_label)
        header_row.addStretch()
        self.debug_clear_btn = QPushButton(tr("ui.clear"))
        self.debug_clear_btn.clicked.connect(lambda: self.debug_log.clear())
        header_row.addWidget(self.debug_clear_btn)
        layout.addLayout(header_row)

        self.debug_log = QTextEdit()
        self.debug_log.setReadOnly(True)
        self.debug_log.setFixedHeight(160)
        self.debug_log.setStyleSheet(
            "font-family: Consolas, 'Courier New', monospace; font-size: 11px;"
        )
        layout.addWidget(self.debug_log)
        return panel

    def _toggle_debug_mode(self) -> None:
        visible = not self.debug_panel.isVisible()
        self.debug_panel.setVisible(visible)
        self.debug_btn.setText(tr("ui.debug_hide") if visible else tr("ui.debug"))

    def _open_about(self) -> None:
        AboutWindow(self).exec()

    def _open_help(self) -> None:
        """Окно «Помощь»; ошибки, уже попавшие в debug-лог, в нём подсвечиваются."""
        log_text = self.debug_log.toPlainText()
        win = getattr(self, "_help_window", None)
        if win is not None and win.isVisible():
            win.set_log_text(log_text)
        else:
            win = HelpWindow(log_text, parent=self)
            self._help_window = win
        win.show()
        win.raise_()
        win.activateWindow()

    def _append_debug_log(self, text: str) -> None:
        self.debug_log.append(text)
        scrollbar = self.debug_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _build_header(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        title = QLabel("YouTube Music Downloader")
        title.setStyleSheet("font-size: 15px; font-weight: 600;")
        self.language_combo = QComboBox()
        for code, name in i18n.LANGUAGES.items():
            self.language_combo.addItem(name, code)
        self.language_combo.setCurrentIndex(self.language_combo.findData(i18n.current_language()))
        self.language_combo.setToolTip(tr("ui.language_tooltip"))
        self.language_combo.currentIndexChanged.connect(self._on_language_chosen)
        self.about_btn = QPushButton(tr("ui.about"))
        self.about_btn.clicked.connect(self._open_about)
        self.help_btn = QPushButton(tr("ui.help"))
        self.help_btn.clicked.connect(self._open_help)
        self.debug_btn = QPushButton(tr("ui.debug"))
        self.debug_btn.clicked.connect(self._toggle_debug_mode)
        self.compact_btn = QPushButton(tr("ui.compact"))
        self.compact_btn.clicked.connect(self._toggle_compact_mode)
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self.language_combo)
        layout.addWidget(self.about_btn)
        layout.addWidget(self.help_btn)
        layout.addWidget(self.debug_btn)
        layout.addWidget(self.compact_btn)
        return layout

    def _panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("panel")
        return frame

    def _set_status(self, text: str) -> None:
        """Единая точка вывода статуса — 'что программа делает прямо сейчас'."""
        self.status_label.setText(text)

    # ---- Левая панель: ссылка, папка, скачивание, тема ----
    def _build_left_panel(self) -> QFrame:
        panel = self._panel()
        layout = QVBoxLayout(panel)

        self.paste_label = QLabel(tr("ui.paste_label"))
        layout.addWidget(self.paste_label)
        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.url_input.editingFinished.connect(self._on_url_input_changed)
        paste_btn = QPushButton("📋")
        paste_btn.setFixedWidth(36)
        paste_btn.clicked.connect(self._paste_url)
        clear_btn = QPushButton("✕")
        clear_btn.setFixedWidth(36)
        clear_btn.clicked.connect(self._clear_url_input)
        url_row.addWidget(self.url_input)
        url_row.addWidget(paste_btn)
        url_row.addWidget(clear_btn)
        layout.addLayout(url_row)

        self.folder_title_label = QLabel(tr("ui.folder_label"))
        layout.addWidget(self.folder_title_label)
        folder_row = QHBoxLayout()
        self.folder_label = QLabel(self.settings.save_folder)
        self.folder_label.setObjectName("secondary")
        self.folder_label.setWordWrap(True)
        self.browse_btn = QPushButton(tr("ui.browse"))
        self.browse_btn.clicked.connect(self._choose_folder)
        folder_row.addWidget(self.folder_label, 1)
        folder_row.addWidget(self.browse_btn)
        layout.addLayout(folder_row)

        buttons_row = QHBoxLayout()
        self.download_now_btn = QPushButton(tr("ui.download_now"))
        self.download_now_btn.setObjectName("accent")
        self.download_now_btn.clicked.connect(self._download_now)
        self.add_queue_btn = QPushButton(tr("ui.add_queue"))
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

        self.theme_label = QLabel(tr("ui.theme_color"))
        layout.addWidget(self.theme_label)
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

        self.beautiful_btn = QPushButton(tr("ui.beautiful"))
        self.beautiful_btn.setCheckable(True)
        self.beautiful_btn.setChecked(self.settings.appearance_mode == theme.BEAUTIFUL_MODE)
        self.beautiful_btn.clicked.connect(self._toggle_beautiful_theme)
        layout.addWidget(self.beautiful_btn)

        layout.addStretch()
        return panel

    # ---- Центральная панель: вкладки ----
    def _build_center_panel(self) -> QFrame:
        panel = self._panel()
        layout = QVBoxLayout(panel)
        self.tabs = QTabWidget()
        self.tabs.tabBar().setExpanding(True)  # вкладки делят всю ширину поровну — визуально по центру

        # -- Поиск --
        search_tab = QWidget()
        search_layout = QVBoxLayout(search_tab)
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("ui.search_placeholder"))
        self.search_input.returnPressed.connect(self._run_search)
        search_btn = QPushButton("🔍")
        search_btn.setFixedWidth(36)
        search_btn.clicked.connect(self._run_search)
        search_row.addWidget(self.search_input)
        search_row.addWidget(search_btn)
        search_layout.addLayout(search_row)
        self.search_results_list = HoverListWidget()
        self.search_results_list.setMouseTracking(True)
        self.search_results_list.itemEntered.connect(self._on_list_item_hovered)
        self.search_results_list.itemClicked.connect(self._on_search_result_selected)
        self.search_results_list.itemDoubleClicked.connect(self._on_search_result_chosen)
        self.search_results_list.mouse_left.connect(self._restore_preview)
        search_layout.addWidget(self.search_results_list)
        self.tabs.addTab(search_tab, tr("tab.search"))

        # -- Очередь --
        queue_tab = QWidget()
        queue_layout = QVBoxLayout(queue_tab)
        self.queue_list = QueueListWidget()
        self.queue_list.remove_requested.connect(self._on_remove_clicked)
        self.queue_list.setMouseTracking(True)
        self.queue_list.itemEntered.connect(self._on_list_item_hovered)
        self.queue_list.itemClicked.connect(self._on_search_result_selected)
        self.queue_list.mouse_left.connect(self._on_queue_mouse_left)
        self.queue_list.setStyleSheet("QListWidget::item { padding-right: 32px; }")
        self.queue_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # место под «✕»
        queue_layout.addWidget(self.queue_list)
        queue_buttons = QHBoxLayout()
        self.start_queue_btn = QPushButton(tr("ui.start_queue"))
        self.start_queue_btn.setObjectName("accent")
        self.start_queue_btn.clicked.connect(self._maybe_process_queue)
        self.clear_queue_btn = QPushButton(tr("ui.clear_queue"))
        self.clear_queue_btn.clicked.connect(self._remove_selected_from_queue)
        queue_buttons.addWidget(self.start_queue_btn)
        queue_buttons.addWidget(self.clear_queue_btn)
        queue_buttons.addStretch()
        queue_layout.addLayout(queue_buttons)
        self.tabs.addTab(queue_tab, tr("tab.queue"))

        # -- История --
        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        self.history_list = HoverListWidget()
        self.history_list.setMouseTracking(True)
        self.history_list.itemEntered.connect(self._on_list_item_hovered)
        self.history_list.itemClicked.connect(self._on_search_result_selected)
        self.history_list.mouse_left.connect(self._restore_preview)
        history_layout.addWidget(self.history_list)
        history_buttons = QHBoxLayout()
        self.clear_history_btn = QPushButton(tr("ui.clear_history"))
        self.clear_history_btn.clicked.connect(self._clear_history)
        history_buttons.addWidget(self.clear_history_btn)
        history_buttons.addStretch()
        history_layout.addLayout(history_buttons)
        self.tabs.addTab(history_tab, tr("tab.history"))

        # При запуске главной вкладкой является «Очередь», а не «Поиск»
        self.tabs.setCurrentWidget(queue_tab)
        self._refresh_download_buttons()

        layout.addWidget(self.tabs)
        return panel

    # ---- Правая панель: обложка + превью ----
    def _build_right_panel(self) -> QFrame:
        panel = self._panel()
        panel.setFixedWidth(240)  # фиксированная ширина — не "гуляет" при смене текста
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

        # Название/исполнитель — фиксированная высота в одну строку с эллипсисом,
        # чтобы длинные названия не растягивали панель по вертикали при наведении.
        self.track_title_label = QLabel(tr("track.title"))
        self.track_title_label.setFixedWidth(210)
        self.track_title_label.setFixedHeight(20)
        self.track_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.track_title_label.setStyleSheet("font-weight: 600;")
        self.track_artist_label = QLabel(tr("track.artist"))
        self.track_artist_label.setFixedWidth(210)
        self.track_artist_label.setFixedHeight(18)
        self.track_artist_label.setObjectName("secondary")
        self.track_artist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.track_title_label)
        layout.addWidget(self.track_artist_label)

        self.preview_btn = QPushButton(tr("preview.start"))
        self.preview_btn.setObjectName("accent")
        self.preview_btn.clicked.connect(self._toggle_preview)
        layout.addWidget(self.preview_btn)

        layout.addStretch()
        return panel

    @staticmethod
    def _set_elided_text(label: QLabel, text: str) -> None:
        """Обрезает текст многоточием по ширине лейбла — не даёт ему растянуть панель."""
        metrics = QFontMetrics(label.font())
        elided = metrics.elidedText(text, Qt.TextElideMode.ElideRight, label.width())
        label.setText(elided)
        label.setToolTip(text)  # полное название доступно во всплывающей подсказке

    # ─────────────────────────────────────────────
    #  Язык интерфейса
    # ─────────────────────────────────────────────
    def _on_language_chosen(self) -> None:
        code = self.language_combo.currentData()
        if not code or code == i18n.current_language():
            return
        self.settings.language = code
        self.settings.save()
        i18n.set_language(code)
        self._retranslate_ui()

    def _retranslate_ui(self) -> None:
        """Обновляет все надписи под выбранный язык — без перезапуска программы.
        Тексты статусов и названия треков не трогаем: они описывают уже случившееся."""
        self.about_btn.setText(tr("ui.about"))
        self.help_btn.setText(tr("ui.help"))
        self.debug_btn.setText(tr("ui.debug_hide") if self.debug_panel.isVisible() else tr("ui.debug"))
        self.compact_btn.setText(tr("ui.full") if self._compact else tr("ui.compact"))
        self.language_combo.setToolTip(tr("ui.language_tooltip"))
        self.debug_title_label.setText(tr("ui.debug_log_title"))
        self.debug_clear_btn.setText(tr("ui.clear"))
        self.paste_label.setText(tr("ui.paste_label"))
        self.folder_title_label.setText(tr("ui.folder_label"))
        self.browse_btn.setText(tr("ui.browse"))
        self.download_now_btn.setText(tr("ui.download_now"))
        self.add_queue_btn.setText(tr("ui.add_queue"))
        self.theme_label.setText(tr("ui.theme_color"))
        self.beautiful_btn.setText(tr("ui.beautiful"))
        self.search_input.setPlaceholderText(tr("ui.search_placeholder"))
        self.tabs.setTabText(0, tr("tab.search"))
        self.tabs.setTabText(1, tr("tab.queue"))
        self.tabs.setTabText(2, tr("tab.history"))
        self.start_queue_btn.setText(tr("ui.start_queue"))
        self.clear_queue_btn.setText(tr("ui.clear_queue"))
        self.clear_history_btn.setText(tr("ui.clear_history"))
        self._refresh_download_buttons()
        # кнопка предпрослушивания: «пауза», если играет, иначе «предпрослушать»
        playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        self.preview_btn.setText(tr("preview.pause") if playing else tr("preview.start"))
        if not self._current_target_url():
            self._default_cover_state()
        self._set_status(tr("status.ready"))
        help_win = getattr(self, "_help_window", None)
        if help_win is not None and help_win.isVisible():
            help_win.retranslate()

    # ─────────────────────────────────────────────
    #  Тема
    # ─────────────────────────────────────────────
    def _apply_theme(self) -> None:
        beautiful = self.settings.appearance_mode == theme.BEAUTIFUL_MODE
        theme.apply_theme(QApplication.instance(), self.settings.accent_color, self.settings.appearance_mode)
        self.background.configure(beautiful, self.settings.accent_color)
        self.beautiful_btn.setChecked(beautiful)

    def _toggle_beautiful_theme(self) -> None:
        if self.settings.appearance_mode == theme.BEAUTIFUL_MODE:
            self.settings.appearance_mode = self._previous_appearance
        else:
            self._previous_appearance = self.settings.appearance_mode
            self.settings.appearance_mode = theme.BEAUTIFUL_MODE
        self.settings.save()
        self._apply_theme()

    def _set_accent_color(self, color: str) -> None:
        self.settings.accent_color = color
        self.settings.save()
        self._apply_theme()

    def _fetch_metadata(self, url: str, callback) -> None:
        """
        Запрашивает метаданные по ссылке в фоне и передаёт результат в callback(dict).
        Результат кэшируется по url, чтобы повторные наведения мышью не били по yt-dlp заново.
        """
        worker = MetadataWorker(url)
        self._active_metadata_workers.append(worker)
        worker.log_line.connect(lambda ln: self._append_debug_log(f"[metadata] {ln}"))

        def _on_done(data: dict) -> None:
            self._metadata_cache[url] = data
            if worker in self._active_metadata_workers:
                self._active_metadata_workers.remove(worker)
            callback(data)

        worker.finished.connect(_on_done)
        worker.failed.connect(
            lambda _err: self._active_metadata_workers.remove(worker)
            if worker in self._active_metadata_workers else None
        )
        worker.start()

    # ─────────────────────────────────────────────
    #  Ссылка / папка
    # ─────────────────────────────────────────────
    def _paste_url(self) -> None:
        text = QApplication.clipboard().text(QClipboard.Mode.Clipboard)
        if text:
            self.url_input.setText(text.strip())
            self._on_url_input_changed()

    def _on_url_input_changed(self) -> None:
        """Вызывается при вставке/ручном изменении ссылки — подтягивает обложку и название."""
        url = self.url_input.text().strip()
        if not url:
            self._active_url = None
            self._default_cover_state()
            self._set_status(tr("status.ready"))
            return

        self._active_url = url
        self.search_results_list.clearSelection()  # поле ссылки теперь единственный источник

        cached = self._metadata_cache.get(url)
        if cached:
            self._on_metadata_ready(cached)
            self._set_status(tr("status.metadata_cache"))
            return

        self._set_status(tr("status.metadata_collecting"))

        def _on_done(data: dict) -> None:
            self._on_metadata_ready(data)
            self._set_status(tr("status.metadata_done"))

        self._fetch_metadata(url, _on_done)

    def _current_target_url(self) -> str:
        """
        Единая точка определения "что именно скачивать" — устраняет ситуацию,
        когда одновременно и поле ссылки, и выбор в поиске претендуют на скачивание.
        Приоритет: то, что реально написано в поле ссылки прямо сейчас,
        иначе — трек, выбранный кликом в поиске.
        """
        typed = self.url_input.text().strip()
        return typed if typed else (self._active_url or "")

    def _clear_url_input(self) -> None:
        self.url_input.clear()
        self._active_url = None
        self._default_cover_state()

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, tr("ui.choose_folder"), self.settings.save_folder)
        if folder:
            self.settings.save_folder = folder
            self.settings.save()
            self.folder_label.setText(folder)

    # ─────────────────────────────────────────────
    #  Скачивание — сейчас / в очередь
    # ─────────────────────────────────────────────
    def _download_now(self) -> None:
        url = self._current_target_url()
        if not url:
            return
        cached = self._metadata_cache.get(url)
        title = cached.get("title") if cached else None
        self._start_download(url, title=title)

    def _add_current_url_to_queue(self) -> None:
        url = self._current_target_url()
        if not url:
            return
        cached = self._metadata_cache.get(url)
        if cached and cached.get("title"):
            self._add_to_queue(url, cached["title"])
            self._set_status(tr("status.queued", title=cached["title"]))
        else:
            # Название ещё неизвестно — добавляем плейсхолдер и обновим его,
            # когда придут метаданные.
            item = self._add_to_queue(url, tr("queue.fetching"))
            self._set_status(tr("status.queued_fetching"))
            self._fetch_metadata(url, lambda data, it=item: self._update_queue_item_title(it, url, data))
        self.url_input.clear()

    def _update_queue_item_title(self, item: QListWidgetItem, url: str, data: dict) -> None:
        title = data.get("title")
        if not title:
            return
        item.setText(title)
        for entry in self.download_queue:
            if entry["url"] == url and entry["title"] == tr("queue.fetching"):
                entry["title"] = title
                break

    def _add_to_queue(self, url: str, title: str) -> QListWidgetItem:
        self.download_queue.append({"url": url, "title": title})
        item = QListWidgetItem(title)
        item.setData(Qt.ItemDataRole.UserRole, url)
        self.queue_list.addItem(item)
        self._refresh_download_buttons()
        return item

    def _on_remove_clicked(self, item: QListWidgetItem) -> None:
        self._remove_from_queue_with_confirm([item])

    def _remove_from_queue_with_confirm(self, items: list) -> None:
        # Трек, который качается прямо сейчас (он всегда первый), удалять нельзя
        worker = getattr(self, "_download_worker", None)
        downloading = worker is not None and worker.isRunning()
        items = [it for it in items if not (downloading and self.queue_list.row(it) == 0)]
        if not items:
            self._set_status(tr("status.cannot_remove_downloading"))
            return
        if not confirm_remove_from_queue(self):
            return
        removed: set = set()
        for item in items:
            row = self.queue_list.row(item)
            if row < 0:
                continue
            if row < len(self.download_queue):
                removed.add(self.download_queue.pop(row)["url"])
            self.queue_list.takeItem(row)
        remaining = {q["url"] for q in self.download_queue}
        self._forget_removed_urls(removed - remaining)
        self._refresh_download_buttons()

    def _remove_selected_from_queue(self) -> None:
        """Кнопка «Очистить очередь»: удаляет всю очередь после подтверждения."""
        worker = getattr(self, "_download_worker", None)
        downloading = worker is not None and worker.isRunning()
        # трек, который качается сейчас (первый), остаётся в очереди
        keep = 1 if downloading else 0
        if self.queue_list.count() <= keep:
            self._set_status(tr("status.queue_empty") if not keep else tr("status.queue_last_downloading"))
            return
        if not confirm_clear_queue(self):
            return
        removed = {q["url"] for q in self.download_queue[keep:]}
        del self.download_queue[keep:]
        self._forget_removed_urls(removed - {q["url"] for q in self.download_queue})
        while self.queue_list.count() > keep:
            self.queue_list.takeItem(self.queue_list.count() - 1)
        self._refresh_download_buttons()
        self._set_status(tr("status.queue_cleared"))

    def _refresh_download_buttons(self) -> None:
        """«Скачать сейчас» доступна, только если очередь пуста и ничего не качается;
        когда в очереди есть треки — работает «Скачать очередь»."""
        idle = self.current_download_url is None
        has_queue = bool(self.download_queue)
        self.download_now_btn.setEnabled(idle and not has_queue)
        self.download_now_btn.setToolTip(
            tr("queue.now_tooltip") if has_queue else ""
        )
        self.start_queue_btn.setEnabled(idle and has_queue)

    def _maybe_process_queue(self) -> None:
        if self.current_download_url is not None:
            return  # уже что-то качается — очередь подождёт
        if not self.download_queue:
            return
        next_item = self.download_queue[0]
        self._set_status(tr("status.queue_start", title=next_item["title"]))
        self._start_download(next_item["url"], title=next_item["title"], from_queue=True)

    def _start_download(self, url: str, title: str | None, from_queue: bool = False) -> None:
        if self.current_download_url is not None:
            # Уже идёт скачивание — просто добавим в очередь вместо параллельного запуска
            self._add_to_queue(url, title or url)
            self._set_status(tr("status.busy_added"))
            return

        self.current_download_url = url
        self._refresh_download_buttons()
        self.progress_bar.setValue(0)
        self.progress_label.setText(tr("progress.preparing"))
        self._set_status(tr("status.downloading", title=title or url))

        cached = self._metadata_cache.get(url)
        thumb_bytes = cached.get("thumb_bytes") if cached else None
        self._download_worker = DownloadWorker(url, self.settings.save_folder, thumb_bytes=thumb_bytes)
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.log_line.connect(lambda ln: self._append_debug_log(f"[download] {ln}"))
        self._download_worker.finished.connect(
            lambda ok, cover_ok: self._on_download_finished(ok, cover_ok, url, title, from_queue)
        )
        self._download_worker.start()

    def _on_download_progress(self, fraction: float, info: str) -> None:
        self.progress_bar.setValue(int(fraction * 100))
        self.progress_label.setText(f"{int(fraction * 100)}% · {info}" if info else f"{int(fraction * 100)}%")

    def _on_download_finished(
        self, ok: bool, cover_embedded: bool, url: str, title: str | None, from_queue: bool
    ) -> None:
        self.current_download_url = None
        self.progress_label.setText(tr("progress.done") if ok else tr("progress.error"))

        if ok:
            status = tr("status.downloaded", title=title or url)
            if not cover_embedded:
                status += tr("status.no_cover_suffix")
            self._set_status(status)
        else:
            self._set_status(tr("status.download_failed", title=title or url))

        if ok:
            entry_title = title or url
            self.history.add(entry_title, url, datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
            self._refresh_history_list()

        if from_queue and self.download_queue:
            self.download_queue.pop(0)
            self.queue_list.takeItem(0)

        self._refresh_download_buttons()
        self._maybe_process_queue()

    # ─────────────────────────────────────────────
    #  Поиск
    # ─────────────────────────────────────────────
    def _run_search(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            return
        if getattr(self, "_search_worker", None) and self._search_worker.isRunning():
            return  # предыдущий поиск ещё не завершился — не плодим параллельные запросы
        self.search_results_list.clear()
        self.search_results_list.addItem(tr("search.searching"))
        self._set_status(tr("status.searching", query=query))
        self.search_input.setEnabled(False)
        self._search_worker = SearchWorker(query)
        self._search_worker.log_line.connect(self._append_debug_log)
        self._search_worker.finished.connect(self._on_search_finished)
        self._search_worker.start()

    def _on_search_finished(self, results: list[dict]) -> None:
        self.search_input.setEnabled(True)
        self.search_results_list.clear()
        if not results:
            self.search_results_list.addItem(tr("search.none"))
            self._set_status(tr("status.search_none"))
            return
        for r in results:
            tag = SOURCE_TAG.get(r["source"], "")
            item = QListWidgetItem(f"{tag}  {r['title']}")
            item.setData(Qt.ItemDataRole.UserRole, r)
            self.search_results_list.addItem(item)
        self._set_status(tr("status.search_found", n=len(results)))

    def _on_search_result_chosen(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        self._add_to_queue(data["url"], data["title"])

    def _on_search_result_selected(self, item: QListWidgetItem) -> None:
        """
        Одинарный клик по треку (в поиске, очереди или истории) — делает его "активным"
        (тем, что уйдёт в скачивание/предпрослушивание) и закрепляет превью: когда мышь
        уходит со списка, превью возвращается именно к нему, а не пропадает — так можно
        спокойно перевести курсор на «Предпрослушать».
        Раз выбор сделан в списке, поле ссылки больше не должно указывать на другой трек,
        поэтому очищаем его, а выделение в остальных списках снимаем.
        """
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        url = data["url"] if isinstance(data, dict) else data
        title = data["title"] if isinstance(data, dict) else item.text()
        self._active_url = url
        self.url_input.blockSignals(True)
        self.url_input.clear()
        self.url_input.blockSignals(False)

        for lst in (self.search_results_list, self.queue_list, self.history_list):
            if lst is not item.listWidget():
                lst.clearSelection()

        cached = self._metadata_cache.get(url)
        if cached:
            self._on_metadata_ready(cached)
            self._set_status(tr("status.selected", title=title))
        else:
            self._set_status(tr("status.loading_selected"))

            def _on_done(meta: dict) -> None:
                self._on_metadata_ready(meta)
                self._set_status(tr("status.selected", title=title))

            self._fetch_metadata(url, _on_done)

    def _on_list_item_hovered(self, item: QListWidgetItem) -> None:
        """
        Общий обработчик для search_results_list / queue_list / history_list.
        Данные элемента бывают либо словарём результата поиска ({"url", "title", "source"}),
        либо просто ссылкой (str) — для очереди и истории.
        """
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        url = data["url"] if isinstance(data, dict) else data
        if item.listWidget() is self.queue_list:
            self._last_hovered_queue_url = url

        cached = self._metadata_cache.get(url)
        if cached:
            self._on_metadata_ready(cached)
            return
        self._fetch_metadata(url, self._on_metadata_ready)

    # ─────────────────────────────────────────────
    #  История
    # ─────────────────────────────────────────────
    def _refresh_history_list(self) -> None:
        self.history_list.clear()
        for entry in self.history.items:
            item = QListWidgetItem(f"{entry['time']} — {entry['title']}")
            item.setData(Qt.ItemDataRole.UserRole, entry["url"])
            self.history_list.addItem(item)

    def _clear_history(self) -> None:
        if not self.history.items:
            self._set_status(tr("status.history_empty"))
            return
        if not confirm_clear_history(self):
            return
        self.history.clear()
        self._refresh_history_list()

    # ─────────────────────────────────────────────
    #  Превью
    # ─────────────────────────────────────────────
    def _toggle_preview(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.preview_btn.setText(tr("preview.start"))
            return

        url = self._current_target_url()
        if not url:
            return
        self.preview_btn.setText(tr("preview.loading"))
        self._set_status(tr("status.preview_getting"))
        self._preview_worker = PreviewStreamWorker(url)
        self._preview_worker.log_line.connect(lambda ln: self._append_debug_log(f"[preview] {ln}"))
        self._preview_worker.finished.connect(self._on_preview_stream_ready)
        self._preview_worker.start()

        self._metadata_worker = MetadataWorker(url)
        self._metadata_worker.log_line.connect(lambda ln: self._append_debug_log(f"[metadata] {ln}"))
        self._metadata_worker.finished.connect(self._on_metadata_ready)
        self._metadata_worker.start()

    def _on_preview_stream_ready(self, stream_url: str) -> None:
        if not stream_url:
            self.preview_btn.setText(tr("preview.start"))
            self._set_status(tr("status.preview_failed"))
            return
        self.player.setSource(QUrl(stream_url))
        self.player.play()
        self._set_status(tr("status.preview_playing"))
        self.preview_btn.setText(tr("preview.pause"))

    def _on_metadata_ready(self, data: dict) -> None:
        self._set_elided_text(self.track_title_label, data.get("title") or tr("track.title"))
        self._set_elided_text(self.track_artist_label, data.get("artist") or tr("track.artist"))
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
        else:
            self.cover_label.setPixmap(QPixmap())  # очищаем pixmap
            self.cover_label.setText("🎵")

    # ─────────────────────────────────────────────
    #  Восстановление превью (устраняет "залипание" после наведения — пункт 1)
    # ─────────────────────────────────────────────
    def _default_cover_state(self) -> None:
        """Заглушка «ничего не выбрано» — серый квадрат с нотой."""
        self.cover_label.setPixmap(QPixmap())
        self.cover_label.setText("🎵")
        self._set_elided_text(self.track_title_label, tr("track.title"))
        self._set_elided_text(self.track_artist_label, tr("track.artist"))

    def _on_queue_mouse_left(self) -> None:
        """
        Курсор ушёл со списка очереди. Трек, на который наводили, становится
        выбранным (как после клика) и остаётся в превью — иначе данные пропадали
        бы, и до кнопки «Предпрослушать» нельзя было бы дойти. Исключение — когда
        в поле ссылки введён адрес: он имеет приоритет, и превью вернётся к нему.
        """
        url = self._last_hovered_queue_url
        if url and not self.url_input.text().strip():
            for i in range(self.queue_list.count()):
                item = self.queue_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == url:
                    self._on_search_result_selected(item)  # активный трек + выделение + превью
                    item.setSelected(True)
                    return
        self._restore_preview()

    def _forget_removed_urls(self, removed: set) -> None:
        """Убирает из превью трек, который только что удалили из очереди."""
        if self._last_hovered_queue_url in removed:
            self._last_hovered_queue_url = None
        if self._active_url in removed and not self.url_input.text().strip():
            self._active_url = None
            self._default_cover_state()

    def _restore_preview(self) -> None:
        """
        Вызывается, когда мышь уходит со списка (поиск/очередь/история).
        Возвращаем превью к текущему активному треку (ссылка в поле ИЛИ
        трек, выбранный кликом в поиске) — а если ничего не выбрано,
        возвращаем заглушку "ничего не выбрано".
        """
        url = self._current_target_url()
        if not url:
            self._default_cover_state()
            return
        cached = self._metadata_cache.get(url)
        if cached:
            self._on_metadata_ready(cached)
        else:
            self._fetch_metadata(url, self._on_metadata_ready)

    # ─────────────────────────────────────────────
    #  Мини-режим
    # ─────────────────────────────────────────────
    def _toggle_compact_mode(self) -> None:
        self._compact = not self._compact
        self.center_panel.setVisible(not self._compact)
        self.right_panel.setVisible(not self._compact)
        self.compact_btn.setText(tr("ui.full") if self._compact else tr("ui.compact"))
        if self._compact:
            self.resize(360, 420)
        else:
            self.resize(980, 560)
"""
Окно «Помощь» — справочник ошибок yt-dlp с причинами и решениями.

Слева — список ошибок (те, что уже есть в debug-логе, помечены ⚠ и стоят
первыми), сверху — поиск, справа — подробное описание выбранной ошибки.
Данные берутся из app.help_data.
"""

import html
import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QTextBrowser, QVBoxLayout,
)

from app.help_data import HELP_ENTRIES, HelpEntry, find_matches


def _fmt(text: str) -> str:
    """Экранирует HTML и превращает `текст` в обратных кавычках в <code>."""
    escaped = html.escape(text)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)


def render_entry_html(entry: HelpEntry) -> str:
    parts = [
        f'<div style="color:#8a8a8a">{html.escape(entry.category)}</div>',
        f"<h3>{html.escape(entry.title)}</h3>",
    ]
    if entry.log_example:
        parts.append("<p><b>Как выглядит в логе</b></p>")
        parts.append(f"<blockquote><code>{html.escape(entry.log_example)}</code></blockquote>")
    parts.append("<p><b>Что это значит</b></p>")
    parts.append(f"<p>{_fmt(entry.cause)}</p>")
    parts.append("<p><b>Как исправить</b></p>")
    parts.append("<ol>" + "".join(f"<li>{_fmt(s)}</li>" for s in entry.steps) + "</ol>")
    if entry.link:
        link = html.escape(entry.link, quote=True)
        parts.append(f'<p><b>Подробнее:</b> <a href="{link}">{link}</a></p>')
    return "".join(parts)


class HelpWindow(QDialog):
    def __init__(self, log_text: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Помощь — ошибки yt-dlp")
        self.resize(860, 540)
        self.setModal(False)

        self._matched_keys: set[str] = set()
        self._log_empty = True

        layout = QVBoxLayout(self)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск: 403, ffmpeg, bot, обложка…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search)

        self.hint_label = QLabel()
        self.hint_label.setObjectName("secondary")
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

        body = QHBoxLayout()
        self.list = QListWidget()
        self.list.setFixedWidth(300)
        self.list.setWordWrap(True)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.currentItemChanged.connect(self._on_current_changed)
        body.addWidget(self.list)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        body.addWidget(self.browser, 1)
        layout.addLayout(body, 1)

        footer = QLabel(
            "Не нашли свою ошибку? Откройте «Debug режим», скопируйте строку с ERROR "
            "и вставьте часть её текста в поиск."
        )
        footer.setObjectName("secondary")
        footer.setWordWrap(True)
        layout.addWidget(footer)

        self.set_log_text(log_text)

    # ── данные ──
    def set_log_text(self, log_text: str) -> None:
        """Пересчитать, какие ошибки из справочника уже есть в логе, и перестроить список."""
        self._log_empty = not log_text.strip()
        matched = find_matches(log_text)
        self._matched_keys = {e.key for e in matched}

        if self._log_empty:
            self.hint_label.setText("Debug-лог пока пуст — показан весь справочник.")
        elif matched:
            self.hint_label.setText(
                f"В debug-логе найдено совпадений: {len(matched)} — они отмечены ⚠ и стоят первыми."
            )
        else:
            self.hint_label.setText("В debug-логе известных ошибок не найдено.")

        current = self._current_key()
        ordered = sorted(HELP_ENTRIES, key=lambda e: e.key not in self._matched_keys)

        self.list.blockSignals(True)
        self.list.clear()
        for entry in ordered:
            prefix = "⚠ " if entry.key in self._matched_keys else ""
            item = QListWidgetItem(prefix + entry.title)
            item.setData(Qt.ItemDataRole.UserRole, entry.key)
            self.list.addItem(item)
        self.list.blockSignals(False)

        self._apply_filter()
        if current:
            for i in range(self.list.count()):
                it = self.list.item(i)
                if not it.isHidden() and it.data(Qt.ItemDataRole.UserRole) == current:
                    self.list.setCurrentRow(i)
                    break

    def _current_key(self) -> str | None:
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _apply_filter(self) -> None:
        query = self.search.text()
        by_key = {e.key: e for e in HELP_ENTRIES}
        first_visible = -1
        for i in range(self.list.count()):
            item = self.list.item(i)
            visible = by_key[item.data(Qt.ItemDataRole.UserRole)].matches_query(query)
            item.setHidden(not visible)
            if visible and first_visible < 0:
                first_visible = i

        current = self.list.currentItem()
        if first_visible < 0:
            self.list.setCurrentItem(None)
            self.browser.setHtml(
                "<p>Ничего не найдено. Попробуйте другое слово — например код ошибки "
                "(<code>403</code>), часть текста из лога или «ffmpeg».</p>"
            )
        elif current is None or current.isHidden():
            self.list.setCurrentRow(first_visible)

    def _on_current_changed(self, current, _previous) -> None:
        if current is None:
            return
        key = current.data(Qt.ItemDataRole.UserRole)
        for entry in HELP_ENTRIES:
            if entry.key == key:
                self.browser.setHtml(render_entry_html(entry))
                return
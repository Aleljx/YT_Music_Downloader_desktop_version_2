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
from app.i18n import current_language, tr


def _fmt(text: str) -> str:
    """Экранирует HTML и превращает `текст` в обратных кавычках в <code>."""
    escaped = html.escape(text)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)


def render_entry_html(entry: HelpEntry) -> str:
    loc = entry.localized(current_language())
    parts = [
        f'<div style="color:#8a8a8a">{html.escape(tr(loc.category_key))}</div>',
        f"<h3>{html.escape(loc.title)}</h3>",
    ]
    if loc.log_example:
        parts.append(f"<p><b>{html.escape(tr('help.sec_log'))}</b></p>")
        parts.append(f"<blockquote><code>{html.escape(loc.log_example)}</code></blockquote>")
    parts.append(f"<p><b>{html.escape(tr('help.sec_meaning'))}</b></p>")
    parts.append(f"<p>{_fmt(loc.cause)}</p>")
    parts.append(f"<p><b>{html.escape(tr('help.sec_fix'))}</b></p>")
    parts.append("<ol>" + "".join(f"<li>{_fmt(s)}</li>" for s in loc.steps) + "</ol>")
    if loc.link:
        link = html.escape(loc.link, quote=True)
        parts.append(f'<p><b>{html.escape(tr("help.more"))}</b> <a href="{link}">{link}</a></p>')
    return "".join(parts)


class HelpWindow(QDialog):
    def __init__(self, log_text: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("help.title"))
        self.resize(860, 540)
        self.setModal(False)

        self._matched_keys: set[str] = set()
        self._log_empty = True
        self._log_text = log_text

        layout = QVBoxLayout(self)

        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("help.search_placeholder"))
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

        self.footer = QLabel(tr("help.footer"))
        self.footer.setObjectName("secondary")
        self.footer.setWordWrap(True)
        layout.addWidget(self.footer)

        self.set_log_text(log_text)

    # ── данные ──
    def set_log_text(self, log_text: str) -> None:
        """Пересчитать, какие ошибки из справочника уже есть в логе, и перестроить список."""
        self._log_text = log_text
        self._log_empty = not log_text.strip()
        matched = find_matches(log_text)
        self._matched_keys = {e.key for e in matched}

        if self._log_empty:
            self.hint_label.setText(tr("help.hint_empty"))
        elif matched:
            self.hint_label.setText(tr("help.hint_matches", n=len(matched)))
        else:
            self.hint_label.setText(tr("help.hint_none"))

        current = self._current_key()
        ordered = sorted(HELP_ENTRIES, key=lambda e: e.key not in self._matched_keys)

        self.list.blockSignals(True)
        self.list.clear()
        for entry in ordered:
            prefix = "⚠ " if entry.key in self._matched_keys else ""
            item = QListWidgetItem(prefix + entry.localized(current_language()).title)
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
            visible = by_key[item.data(Qt.ItemDataRole.UserRole)].matches_query(query, current_language())
            item.setHidden(not visible)
            if visible and first_visible < 0:
                first_visible = i

        current = self.list.currentItem()
        if first_visible < 0:
            self.list.setCurrentItem(None)
            self.browser.setHtml(f"<p>{tr('help.not_found')}</p>")
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

    def retranslate(self) -> None:
        """Вызывается при смене языка интерфейса: обновляет все надписи и список."""
        self.setWindowTitle(tr("help.title"))
        self.search.setPlaceholderText(tr("help.search_placeholder"))
        self.footer.setText(tr("help.footer"))
        self.set_log_text(self._log_text)
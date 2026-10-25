"""Небольшое окно подтверждения с кнопками «Да» / «Нет» («Нет» — красная)."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app.i18n import tr

DANGER_STYLE = """
QPushButton {
    background-color: #d64545; color: white; border: none;
    border-radius: 6px; padding: 6px 18px;
}
QPushButton:hover { background-color: #e05a5a; }
QPushButton:pressed { background-color: #b83a3a; }
"""


class ConfirmDialog(QDialog):
    def __init__(
        self, text: str, parent=None, title: str | None = None, danger: str = "no"
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title or tr("confirm.title"))
        self.setModal(True)

        layout = QVBoxLayout(self)
        label = QLabel(text)
        label.setWordWrap(True)
        label.setMinimumWidth(320)
        layout.addWidget(label)

        row = QHBoxLayout()
        row.addStretch()
        self.yes_btn = QPushButton(tr("common.yes"))
        self.no_btn = QPushButton(tr("common.no"))
        # какая из кнопок красная: "no" (безопасный отказ) или "yes" (опасное действие)
        (self.yes_btn if danger == "yes" else self.no_btn).setStyleSheet(DANGER_STYLE)
        self.yes_btn.clicked.connect(self.accept)
        self.no_btn.clicked.connect(self.reject)
        row.addWidget(self.yes_btn)
        row.addWidget(self.no_btn)
        layout.addLayout(row)

        self.no_btn.setDefault(True)  # случайный Enter не удалит трек
        self.no_btn.setFocus()


def confirm_remove_from_queue(parent=None) -> bool:
    dlg = ConfirmDialog(
        tr("confirm.remove_track"), parent, danger="yes"
    )
    return dlg.exec() == QDialog.DialogCode.Accepted


def confirm_clear_queue(parent=None) -> bool:
    """Предупреждение об удалении всей очереди — здесь красная кнопка «Да»."""
    dlg = ConfirmDialog(
        tr("confirm.clear_queue"), parent, danger="yes"
    )
    return dlg.exec() == QDialog.DialogCode.Accepted


def confirm_clear_history(parent=None) -> bool:
    """Предупреждение перед полной очисткой истории — красная кнопка «Да»."""
    dlg = ConfirmDialog(
        tr("confirm.clear_history"), parent, danger="yes"
    )
    return dlg.exec() == QDialog.DialogCode.Accepted
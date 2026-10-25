"""Окно «О программе»: версия приложения и авторы."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app import config
from app.i18n import tr

APP_NAME = "YouTube Music Downloader"
APP_VERSION = "2.0"

ICON_AUTHOR_URL = "https://www.youtube.com/channel/UCLQTyU9nJ7V_BF1kRmytalw"

# Эмодзи выводим отдельным span с цветным эмодзи-шрифтом и увеличенным размером —
# иначе они берутся из обычного шрифта и выглядят мелкими/серыми.
_EMOJI_FONT = "'Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji', sans-serif"


EMOJI_FAMILIES = ["Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji"]


def credits(link_color: str) -> tuple:
    """(подпись, HTML текста, эмодзи). Эмодзи — в отдельной метке со своим шрифтом
    и запасом по высоте, чтобы крупный значок не обрезался; цвет ссылки задан в теге."""
    return (
        (tr("about.author"), "aleljx", "🔴👓"),
        (tr("about.co_author"), "Claude", "🟠"),
        (
            tr("about.icon_author"),
            f'<a href="{ICON_AUTHOR_URL}" style="color: {link_color};">{tr("about.icon_author_name")}</a>',
            "🌻🕶",
        ),
    )


def _emoji_label(text: str) -> QLabel:
    label = QLabel(text)
    families = ", ".join(f'"{f}"' for f in EMOJI_FAMILIES)
    # размер и шрифт — через QSS: общий стиль приложения (font-size: 13px) иначе перебивает setFont
    label.setStyleSheet(f"font-family: {families}; font-size: 22px; padding: 2px 0px;")
    label.setMinimumHeight(38)
    label.setMinimumWidth(30 * len(text.replace("\ufe0f", "")) // 1)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


class AboutWindow(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("about.title"))
        self.setModal(True)
        self.setFixedWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(6)

        pix = QIcon(config.ICON_PATH).pixmap(128, 128)  # берёт из .ico самый подходящий размер
        if not pix.isNull():
            icon = QLabel()
            icon.setPixmap(pix)
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(icon)

        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        version = QLabel(tr("about.version", version=APP_VERSION))
        version.setObjectName("secondary")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        layout.addSpacing(14)
        accent = getattr(getattr(parent, "settings", None), "accent_color", None) or "#378ADD"
        for caption, text_html, emoji in credits(accent):
            cap = QLabel(caption)
            cap.setObjectName("secondary")
            cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(cap)

            line = QHBoxLayout()
            line.setSpacing(4)
            line.addStretch()
            val = QLabel(text_html)
            val.setTextFormat(Qt.TextFormat.RichText)
            val.setOpenExternalLinks(True)  # клик по ссылке открывает браузер
            val.setStyleSheet("font-size: 15px; font-weight: 600;")
            line.addWidget(val)
            line.addWidget(_emoji_label(emoji))
            line.addStretch()
            layout.addLayout(line)
            layout.addSpacing(6)

        row = QHBoxLayout()
        row.addStretch()
        close_btn = QPushButton(tr("common.close"))
        close_btn.setObjectName("accent")
        close_btn.clicked.connect(self.accept)
        row.addWidget(close_btn)
        row.addStretch()
        layout.addLayout(row)
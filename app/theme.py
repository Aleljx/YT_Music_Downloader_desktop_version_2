"""
Генерация QSS-стилей приложения.

Тема строится из одного акцентного цвета (выбирается пользователем)
и режима светлый/тёмный. Никакой логики UI здесь нет — модуль просто
возвращает готовую строку QSS, которую main_window применяет через
`widget.setStyleSheet(...)`.
"""

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication


# Пресеты акцентного цвета — те же, что в старом customtkinter-варианте
ACCENT_PRESETS: list[str] = [
    "#378ADD",  # синий (по умолчанию)
    "#D85A30",  # оранжевый
    "#639922",  # зелёный
    "#7F77DD",  # фиолетовый
]


# ─────────────────────────────────────────────
#  Определение тёмного/светлого режима
# ─────────────────────────────────────────────
def resolve_dark_mode(appearance_mode: str) -> bool:
    """
    appearance_mode: "Light" | "Dark" | "System"
    Возвращает True, если нужно применять тёмную тему.
    """
    if appearance_mode == "Dark":
        return True
    if appearance_mode == "Light":
        return False
    return _system_prefers_dark()


def _system_prefers_dark() -> bool:
    """Определяет системную тему через Qt (работает начиная с Qt 6.5)."""
    try:
        scheme = QApplication.styleHints().colorScheme()
        # Qt.ColorScheme.Dark == 2, Light == 1, Unknown == 0
        return scheme.name == "Dark"
    except Exception:
        return True  # если не удалось определить — тёмная тема как безопасный дефолт


# ─────────────────────────────────────────────
#  Вспомогательные функции для работы с цветом
# ─────────────────────────────────────────────
def _shade(hex_color: str, factor: float) -> str:
    """
    factor > 1.0 — осветлить, factor < 1.0 — затемнить.
    Используется для hover/pressed-состояний кнопок.
    """
    color = QColor(hex_color)
    h, s, l, a = color.getHslF()
    l = max(0.0, min(1.0, l * factor))
    color.setHslF(h, s, l, a)
    return color.name()


# ─────────────────────────────────────────────
#  Палитры для светлой/тёмной темы
# ─────────────────────────────────────────────
_DARK_PALETTE = {
    "bg": "#1a1a1a",
    "surface": "#242424",
    "surface_alt": "#2b2b2b",
    "border": "#3a3a3a",
    "text": "#e6e6e6",
    "text_secondary": "#9a9a9a",
}

_LIGHT_PALETTE = {
    "bg": "#f2f2f2",
    "surface": "#ffffff",
    "surface_alt": "#e9e9e9",
    "border": "#d6d6d6",
    "text": "#1a1a1a",
    "text_secondary": "#5c5c5c",
}


# ─────────────────────────────────────────────
#  Сборка итогового QSS
# ─────────────────────────────────────────────
def build_stylesheet(accent_color: str, dark: bool) -> str:
    p = _DARK_PALETTE if dark else _LIGHT_PALETTE
    accent_hover = _shade(accent_color, 1.15 if dark else 0.9)
    accent_pressed = _shade(accent_color, 0.85 if dark else 0.75)

    return f"""
    QWidget {{
        background-color: {p['bg']};
        color: {p['text']};
        font-family: "Segoe UI", sans-serif;
        font-size: 13px;
    }}

    QMainWindow {{
        background-color: {p['bg']};
    }}

    /* ---- Панели-контейнеры ---- */
    QFrame#panel {{
        background-color: {p['surface']};
        border: 1px solid {p['border']};
        border-radius: 8px;
    }}

    /* ---- Кнопки ---- */
    QPushButton {{
        background-color: {p['surface_alt']};
        border: 1px solid {p['border']};
        border-radius: 6px;
        padding: 6px 14px;
        color: {p['text']};
    }}
    QPushButton:hover {{
        background-color: {p['border']};
    }}
    QPushButton:disabled {{
        color: {p['text_secondary']};
    }}

    QPushButton#accent {{
        background-color: {accent_color};
        border: none;
        color: white;
        font-weight: 600;
    }}
    QPushButton#accent:hover {{
        background-color: {accent_hover};
    }}
    QPushButton#accent:pressed {{
        background-color: {accent_pressed};
    }}

    /* ---- Поля ввода ---- */
    QLineEdit {{
        background-color: {p['surface']};
        border: 1px solid {p['border']};
        border-radius: 6px;
        padding: 6px 10px;
        color: {p['text']};
    }}
    QLineEdit:focus {{
        border: 1px solid {accent_color};
    }}

    /* ---- Прогресс-бар ---- */
    QProgressBar {{
        background-color: {p['surface_alt']};
        border: none;
        border-radius: 4px;
        height: 8px;
        text-align: center;
        color: transparent;
    }}
    QProgressBar::chunk {{
        background-color: {accent_color};
        border-radius: 4px;
    }}

    /* ---- Вкладки ---- */
    QTabWidget::pane {{
        border: 1px solid {p['border']};
        border-radius: 8px;
        top: -1px;
    }}
    QTabBar::tab {{
        background: transparent;
        padding: 6px 16px;
        color: {p['text_secondary']};
        border: none;
    }}
    QTabBar::tab:selected {{
        color: {accent_color};
        font-weight: 600;
        border-bottom: 2px solid {accent_color};
    }}

    /* ---- Списки (поиск / очередь / история) ---- */
    QListWidget {{
        background-color: transparent;
        border: none;
        outline: none;
    }}
    QListWidget::item {{
        background-color: {p['surface']};
        border: 1px solid {p['border']};
        border-radius: 6px;
        padding: 8px;
        margin-bottom: 4px;
    }}
    QListWidget::item:hover {{
        border: 1px solid {accent_color};
    }}
    QListWidget::item:selected {{
        background-color: {p['surface_alt']};
    }}

    /* ---- Скроллбар ---- */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
    }}
    QScrollBar::handle:vertical {{
        background: {p['border']};
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QLabel#secondary {{
        color: {p['text_secondary']};
    }}
    """


def apply_theme(app: QApplication, accent_color: str, appearance_mode: str) -> None:
    """Удобный вход из main.py/main_window.py: считает тему и применяет её ко всему приложению."""
    dark = resolve_dark_mode(appearance_mode)
    app.setStyleSheet(build_stylesheet(accent_color, dark))
"""
Локализация интерфейса: русский (ru), украинский (uk), английский (en).

Использование:
    from app.i18n import tr
    label.setText(tr("ui.browse"))
    status = tr("status.queued", title=title)      # подстановка {title}

Тексты лежат в app/locales/{ru,uk,en}.py (словари STRINGS). Если ключа нет
в выбранном языке — берётся английский, потом русский, потом сам ключ.
Смена языка вызывает подписчиков (subscribe), чтобы окна обновили свои надписи.
"""

from typing import Callable

from app.locales import en, ru, uk

LANGUAGES: dict[str, str] = {"ru": "Русский 🇷🇺", "uk": "Українська 🇺🇦", "en": "English 🇺🇸"}
DEFAULT_LANGUAGE = "en"

_CATALOGS: dict[str, dict[str, str]] = {"ru": ru.STRINGS, "uk": uk.STRINGS, "en": en.STRINGS}
_current = "ru"
_subscribers: list[Callable[[], None]] = []


def detect_system_language() -> str:
    """Язык Windows → ru / uk / en (всё остальное — английский)."""
    try:
        from PyQt6.QtCore import QLocale

        name = QLocale.system().name().lower()  # например "uk_ua", "ru_ru", "en_us"
    except Exception:
        return DEFAULT_LANGUAGE
    for code in ("uk", "ru"):
        if name.startswith(code):
            return code
    return DEFAULT_LANGUAGE


def current_language() -> str:
    return _current


def set_language(code: str) -> None:
    """Выбирает язык и уведомляет подписчиков. Неизвестный код → английский."""
    global _current
    _current = code if code in _CATALOGS else DEFAULT_LANGUAGE
    for callback in list(_subscribers):
        callback()


def subscribe(callback: Callable[[], None]) -> None:
    _subscribers.append(callback)


def tr(key: str, **kwargs) -> str:
    text = (
        _CATALOGS[_current].get(key)
        or _CATALOGS["en"].get(key)
        or _CATALOGS["ru"].get(key)
        or key
    )
    return text.format(**kwargs) if kwargs else text
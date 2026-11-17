"""
Тема «Material You» (Material Design 3).

Все цвета строятся библиотекой materialyoucolor из одного исходного цвета —
выбранного акцента (схема TonalSpot, как в Android): фон, панели, кнопки,
выделение, поля ввода — всё получается в одной гамме. Светлая или тёмная
версия выбирается по теме Windows. Это имитация через QSS: без анимаций
ряби (ripple) и без цветов из обоев.
"""

from PyQt6.QtGui import QColor

from materialyoucolor.dynamiccolor.material_dynamic_colors import MaterialDynamicColors as MDC
from materialyoucolor.hct import Hct
from materialyoucolor.scheme.scheme_tonal_spot import SchemeTonalSpot

MATERIAL_MODE = "MaterialYou"


def _hex(argb: int) -> str:
    return "#{:06x}".format(argb & 0xFFFFFF)


def _mix(base: str, over: str, amount: float) -> str:
    """Накладывает цвет `over` на `base` с прозрачностью amount (state layer из Material 3)."""
    b, o = QColor(base), QColor(over)
    return QColor(
        round(b.red() + (o.red() - b.red()) * amount),
        round(b.green() + (o.green() - b.green()) * amount),
        round(b.blue() + (o.blue() - b.blue()) * amount),
    ).name()


def build_palette(seed_color: str, dark: bool) -> dict[str, str]:
    """Роли цветов Material 3 для исходного цвета seed_color (#rrggbb)."""
    seed = QColor(seed_color)
    argb = 0xFF000000 | (seed.red() << 16) | (seed.green() << 8) | seed.blue()
    scheme = SchemeTonalSpot(Hct.from_int(argb), dark, 0.0)
    names = (
        "primary", "onPrimary", "primaryContainer", "onPrimaryContainer",
        "secondaryContainer", "onSecondaryContainer",
        "surface", "onSurface", "onSurfaceVariant",
        "surfaceContainer", "surfaceContainerHigh", "surfaceContainerHighest",
        "outline", "outlineVariant", "inverseSurface", "inverseOnSurface",
    )
    return {n: _hex(getattr(MDC, n).get_argb(scheme)) for n in names}


def build_stylesheet(seed_color: str, dark: bool) -> str:
    c = build_palette(seed_color, dark)
    bg, text, text2 = c["surface"], c["onSurface"], c["onSurfaceVariant"]
    panel, card, card_hi = c["surfaceContainer"], c["surfaceContainerHigh"], c["surfaceContainerHighest"]

    def states(base: str, on: str) -> tuple[str, str]:
        return _mix(base, on, 0.08), _mix(base, on, 0.12)  # hover, pressed

    tonal_h, tonal_p = states(c["secondaryContainer"], c["onSecondaryContainer"])
    prim_h, prim_p = states(c["primary"], c["onPrimary"])
    chk_h, chk_p = states(c["primaryContainer"], c["onPrimaryContainer"])
    card_h = _mix(card, text, 0.08)
    disabled_bg = _mix(bg, text, 0.12)
    disabled_fg = _mix(bg, text, 0.38)

    return f"""
    QWidget {{
        background-color: {bg};
        color: {text};
        font-family: "Segoe UI", sans-serif;
        font-size: 13px;
    }}
    QMainWindow, QDialog {{ background-color: {bg}; }}
    QLabel {{ background-color: transparent; }}
    QLabel#secondary {{ color: {text2}; }}

    QFrame#panel {{
        background-color: {panel};
        border: 1px solid transparent;
        border-radius: 28px;
    }}

    /* ---- Кнопки: tonal / filled / выбранная ---- */
    QPushButton {{
        background-color: {c['secondaryContainer']};
        color: {c['onSecondaryContainer']};
        border: 1px solid transparent;
        border-radius: 16px;
        padding: 8px 18px;
        min-height: 16px;
        font-weight: 600;
    }}
    QPushButton:hover {{ background-color: {tonal_h}; }}
    QPushButton:pressed {{ background-color: {tonal_p}; }}
    QPushButton:checked {{
        background-color: {c['primaryContainer']};
        color: {c['onPrimaryContainer']};
    }}
    QPushButton:checked:hover {{ background-color: {chk_h}; }}
    QPushButton:checked:pressed {{ background-color: {chk_p}; }}
    QPushButton:disabled {{ background-color: {disabled_bg}; color: {disabled_fg}; }}
    QPushButton#accent {{
        background-color: {c['primary']};
        color: {c['onPrimary']};
    }}
    QPushButton#accent:hover {{ background-color: {prim_h}; }}
    QPushButton#accent:pressed {{ background-color: {prim_p}; }}
    QPushButton#accent:disabled {{ background-color: {disabled_bg}; color: {disabled_fg}; }}
    QPushButton#swatch {{ padding: 0px; }}
    QPushButton#iconBtn {{ padding: 0px; font-size: 14px; min-height: 32px; }}

    /* ---- Поля ввода и список языков ---- */
    QLineEdit {{
        background-color: {card_hi};
        border: 2px solid transparent;
        border-radius: 16px;
        padding: 7px 14px;
        selection-background-color: {c['primaryContainer']};
        selection-color: {c['onPrimaryContainer']};
    }}
    QLineEdit:focus {{ border: 2px solid {c['primary']}; }}
    QComboBox {{
        background-color: {card_hi};
        border: 1px solid transparent;
        border-radius: 16px;
        padding: 6px 14px;
    }}
    QComboBox:hover {{ background-color: {_mix(card_hi, text, 0.08)}; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{
        background-color: {card};
        border: 1px solid {c['outlineVariant']};
        border-radius: 12px;
        padding: 4px;
        outline: none;
        selection-background-color: {c['secondaryContainer']};
        selection-color: {c['onSecondaryContainer']};
    }}

    /* ---- Прогресс ---- */
    QProgressBar {{
        background-color: {card_hi};
        border: none;
        border-radius: 4px;
        height: 8px;
        text-align: center;
        color: transparent;
    }}
    QProgressBar::chunk {{ background-color: {c['primary']}; border-radius: 4px; }}

    /* ---- Вкладки ---- */
    QTabWidget::pane {{ border: none; background: transparent; }}
    QTabWidget QStackedWidget, QTabWidget QStackedWidget > QWidget {{ background: transparent; }}
    QTabBar {{ background-color: transparent; }}
    QTabBar::tab {{
        background: transparent;
        color: {text2};
        padding: 8px 18px;
        margin: 2px;
        border: none;
        border-radius: 16px;
        font-weight: 600;
    }}
    QTabBar::tab:hover {{ background-color: {card_h}; }}
    QTabBar::tab:selected {{
        background-color: {c['secondaryContainer']};
        color: {c['onSecondaryContainer']};
    }}

    /* ---- Списки ---- */
    QListWidget {{ background-color: transparent; border: none; outline: none; }}
    QListWidget::item {{
        background-color: {card};
        border: 1px solid transparent;
        border-radius: 16px;
        padding: 10px 12px;
        margin-bottom: 6px;
    }}
    QListWidget::item:hover {{ background-color: {card_h}; }}
    QListWidget::item:selected {{
        background-color: {c['primaryContainer']};
        color: {c['onPrimaryContainer']};
    }}

    QTextEdit, QTextBrowser {{
        background-color: {card};
        border: none;
        border-radius: 16px;
        padding: 6px;
    }}

    /* ---- Скроллбар ---- */
    QScrollBar:vertical {{ background: transparent; width: 8px; }}
    QScrollBar::handle:vertical {{ background: {c['outlineVariant']}; border-radius: 4px; min-height: 24px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar:horizontal {{ background: transparent; height: 8px; }}
    QScrollBar::handle:horizontal {{ background: {c['outlineVariant']}; border-radius: 4px; min-width: 24px; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}

    QToolTip {{
        background-color: {c['inverseSurface']};
        color: {c['inverseOnSurface']};
        border: none;
        padding: 4px 8px;
    }}
    """
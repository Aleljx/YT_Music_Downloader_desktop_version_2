"""
Точка входа приложения.

Логика простая:
  1. Создать QApplication.
  2. Проверить, есть ли yt-dlp.exe / ffmpeg.exe рядом с программой.
  3. Если чего-то не хватает — показать SetupWindow и дождаться его
     сигнала setup_finished, потом открыть основное окно.
  4. Если всё на месте — сразу открыть основное окно.
"""

import sys

from PyQt6.QtWidgets import QApplication

from app import config
from app.main_window import MainWindow
from app.setup_window import SetupWindow


def main() -> None:
    app = QApplication(sys.argv)

    # Храним ссылки на окна на уровне функции, чтобы Python
    # не удалил их сборщиком мусора сразу после создания.
    windows: dict[str, object] = {}

    def show_main_window() -> None:
        windows["main"] = MainWindow()
        windows["main"].show()

    missing = config.missing_dependencies()

    if missing:
        setup = SetupWindow(missing)
        windows["setup"] = setup

        def on_setup_finished() -> None:
            setup.close()
            show_main_window()

        setup.setup_finished.connect(on_setup_finished)
        setup.show()
    else:
        show_main_window()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
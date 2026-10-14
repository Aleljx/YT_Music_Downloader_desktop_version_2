"""
Точка входа приложения.

Логика запуска:
  1. Создать QApplication.
  2. Проверить, есть ли yt-dlp.exe / ffmpeg.exe рядом с программой.
     Если чего-то не хватает — показать SetupWindow(mode="missing")
     и дождаться его сигнала setup_finished (первая установка).
  3. Дальше, когда компоненты точно на месте — проверить, не устарели
     ли они (сетевой запрос, app.update_check). Пока идёт проверка,
     показываем лёгкий сплэш "Проверяем обновления...".
     - Если нашлось устаревшее — показать SetupWindow(mode="update"),
       который качает обновление автоматически, без клика пользователя.
     - Если всё актуально — сразу открыть основное окно, готовое к работе.
"""

import sys

from PyQt6.QtWidgets import QApplication

from app import config
from app.main_window import MainWindow
from app.setup_window import SetupWindow
from app.update_check import UpdateCheckSplash, UpdateCheckWorker


def main() -> None:
    app = QApplication(sys.argv)

    # Храним ссылки на окна/воркеры на уровне функции, чтобы Python
    # не удалил их сборщиком мусора сразу после создания.
    state: dict[str, object] = {}

    def show_main_window() -> None:
        state["main"] = MainWindow()
        state["main"].show()

    def run_update_check() -> None:
        """Шаг 3: компоненты точно на диске есть — проверяем, не устарели ли."""
        splash = UpdateCheckSplash()
        state["splash"] = splash
        splash.show()

        worker = UpdateCheckWorker()
        state["update_worker"] = worker

        def on_update_check_finished(outdated: list) -> None:
            splash.close()

            if outdated:
                setup = SetupWindow(outdated, mode="update")
                state["setup_update"] = setup
                setup.setup_finished.connect(lambda: (setup.close(), show_main_window()))
                setup.show()
            else:
                show_main_window()

        worker.finished.connect(on_update_check_finished)
        worker.start()

    missing = config.missing_dependencies()

    if missing:
        setup = SetupWindow(missing, mode="missing")
        state["setup_missing"] = setup

        def on_first_setup_finished() -> None:
            setup.close()
            run_update_check()

        setup.setup_finished.connect(on_first_setup_finished)
        setup.show()
    else:
        run_update_check()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
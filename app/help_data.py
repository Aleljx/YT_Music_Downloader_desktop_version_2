"""
Справочник ошибок yt-dlp (и самого приложения) с причинами и решениями.

Только данные и поиск — никакого UI (окно лежит в app.help_window).

Как это используется:
  - HELP_ENTRIES — полный список записей для окна «Помощь».
  - find_matches(log_text) — находит записи, чьи `patterns` встречаются
    в тексте debug-лога, чтобы окно «Помощь» подсветило ошибки, которые
    у пользователя реально случились.

Правила для patterns: подстроки в нижнем регистре; они не должны
срабатывать на обычный (успешный) вывод — в том числе на строку с командой
`$ yt-dlp.exe ... --ffmpeg-location ...`, которую приложение пишет в лог
перед каждой загрузкой. Запись без patterns просто не подсвечивается
автоматически, но остаётся в справочнике и в поиске.
"""

from dataclasses import dataclass

EJS_WIKI_URL = "https://github.com/yt-dlp/yt-dlp/wiki/EJS"


@dataclass(frozen=True)
class HelpEntry:
    key: str
    category: str
    title: str
    log_example: str          # как ошибка выглядит в логе ("" — если в лог не попадает)
    patterns: tuple[str, ...]  # подстроки (lowercase) для автоподсветки по debug-логу
    cause: str
    steps: tuple[str, ...]     # `текст в обратных кавычках` в окне выводится как код
    link: str = ""

    @property
    def search_blob(self) -> str:
        return " ".join(
            [self.title, self.category, self.log_example, self.cause, *self.steps, *self.patterns]
        ).lower()

    def matches_query(self, query: str, lang: str = "ru") -> bool:
        """Все слова запроса должны встретиться где-то в записи на выбранном языке (регистр не важен)."""
        words = query.strip().lower().split()
        if not words:
            return True
        blob = self.localized(lang).search_blob
        return all(w in blob for w in words)

    def localized(self, lang: str) -> "LocalizedEntry":
        """Запись на нужном языке: русский — из самой записи, uk/en — из help_translations."""
        from app.help_translations import TRANSLATIONS  # импорт здесь — чтобы не плодить циклы

        tr_data = TRANSLATIONS.get(lang, {}).get(self.key, {})
        title = tr_data.get("title", self.title)
        log_example = tr_data.get("log_example", self.log_example)
        cause = tr_data.get("cause", self.cause)
        steps = tuple(tr_data.get("steps", self.steps))
        blob = " ".join([title, log_example, cause, *steps, *self.patterns, self.title]).lower()
        return LocalizedEntry(
            key=self.key,
            category_key=CATEGORY_KEYS[self.category],
            title=title,
            log_example=log_example,
            cause=cause,
            steps=steps,
            link=self.link,
            search_blob=blob,
        )


@dataclass(frozen=True)
class LocalizedEntry:
    key: str
    category_key: str   # ключ локализации названия категории (help.cat_*)
    title: str
    log_example: str
    cause: str
    steps: tuple[str, ...]
    link: str
    search_blob: str


CAT_YT = "YouTube и доступ"
CAT_NET = "Сеть"
CAT_FILES = "Файлы и ffmpeg"
CAT_APP = "Само приложение"


CATEGORY_KEYS = {
    CAT_YT: "help.cat_yt",
    CAT_NET: "help.cat_net",
    CAT_FILES: "help.cat_files",
    CAT_APP: "help.cat_app",
}


HELP_ENTRIES: tuple[HelpEntry, ...] = (
    # ───────────────  YouTube и доступ  ───────────────
    HelpEntry(
        key="bot-check",
        category=CAT_YT,
        title="Sign in to confirm you're not a bot",
        log_example="ERROR: [youtube] xxxx: Sign in to confirm you’re not a bot. "
                    "Use --cookies-from-browser or --cookies for the authentication.",
        patterns=("not a bot",),
        cause="YouTube принял запросы из вашей сети за автоматические и просит войти в аккаунт. "
              "Чаще всего это бывает при VPN, общем IP-адресе или когда запросов было слишком много подряд.",
        steps=(
            "Перезапусти приложение — оно проверит и обновит yt-dlp.",
            "Отключи VPN/прокси или смени сеть (например, раздай интернет с телефона).",
            "Подожди 15–30 минут и повтори, не запуская много загрузок подряд.",
            "Если не помогает: запусти `yt-dlp.exe` вручную с флагом `--cookies-from-browser chrome` "
            "(в самом приложении входа в аккаунт нет).",
        ),
    ),
    HelpEntry(
        key="http-403",
        category=CAT_YT,
        title="HTTP Error 403: Forbidden",
        log_example="ERROR: unable to download video data: HTTP Error 403: Forbidden",
        patterns=("http error 403", "403: forbidden"),
        cause="Сервер отклонил запрос на аудиопоток. Причины: устаревший yt-dlp, "
              "не решён JavaScript-челлендж YouTube (нет Deno) или временная блокировка вашего IP.",
        steps=(
            "Перезапусти приложение — оно обновит yt-dlp.",
            "Установи Deno — см. запись «No supported JavaScript runtime».",
            "Отключи VPN/прокси или смени сеть.",
            "Повтори позже — блокировка по IP часто снимается сама.",
        ),
    ),
    HelpEntry(
        key="http-429",
        category=CAT_YT,
        title="HTTP Error 429: Too Many Requests",
        log_example="ERROR: [youtube] xxxx: Unable to download webpage: HTTP Error 429: Too Many Requests",
        patterns=("http error 429", "too many requests"),
        cause="За короткое время ушло слишком много запросов — YouTube временно ограничил ваш IP.",
        steps=(
            "Подожди от нескольких минут до часа, потом повтори.",
            "Не запускай сразу длинную очередь много раз подряд.",
            "Смени сеть или IP-адрес.",
        ),
    ),
    HelpEntry(
        key="js-runtime",
        category=CAT_YT,
        title="No supported JavaScript runtime could be found (нет Deno)",
        log_example="WARNING: [youtube] No supported JavaScript runtime could be found. "
                    "(текст может немного отличаться в разных версиях yt-dlp)",
        patterns=("javascript runtime", "js runtime", "n challenge", "challenge solving failed"),
        cause="Чтобы получить ссылки на аудио, yt-dlp решает JavaScript-задачи YouTube. Скрипты-решатели "
              "уже встроены в `yt-dlp.exe`, а вот сам JavaScript-движок (по умолчанию Deno) — нет. "
              "Без него YouTube отдаёт неполный список форматов, и тогда появляются ошибки "
              "403 или «Requested format is not available».",
        steps=(
            "Установи Deno: в PowerShell выполни `winget install DenoLand.Deno` "
            "(или скачай `deno.exe` с сайта Deno).",
            "Либо положи `deno.exe` в папку рядом с `yt-dlp.exe`, либо убедись, что он есть в PATH.",
            "Перезапусти приложение и повтори загрузку.",
        ),
        link=EJS_WIKI_URL,
    ),
    HelpEntry(
        key="format-unavailable",
        category=CAT_YT,
        title="Requested format is not available",
        log_example="ERROR: [youtube] xxxx: Requested format is not available. "
                    "Use --list-formats for a list of available formats",
        patterns=("requested format is not available",),
        cause="yt-dlp не нашёл аудиоформат, который просит приложение (лучший аудиоформат, `-f ba`). "
              "Чаще всего причина — устаревший yt-dlp или нерешённый JavaScript-челлендж: "
              "в этом случае YouTube отдаёт только картинки.",
        steps=(
            "Перезапусти приложение — оно обновит yt-dlp.",
            "Установи Deno — см. запись «No supported JavaScript runtime».",
            "Проверь, что трек вообще играет в браузере по этой же ссылке.",
        ),
        link=EJS_WIKI_URL,
    ),
    HelpEntry(
        key="unavailable",
        category=CAT_YT,
        title="Video unavailable / This video is not available",
        log_example="ERROR: [youtube] xxxx: Video unavailable",
        patterns=("video unavailable", "this video is not available", "video is no longer available"),
        cause="Видео удалено, скрыто автором или недоступно именно вам (регион, настройки канала).",
        steps=(
            "Открой ссылку в браузере. Если там тоже недоступно — скачать нельзя.",
            "Если в браузере трек играет — перезапусти приложение (обновление yt-dlp) и повтори.",
            "Найди этот же трек во вкладке «Поиск»: там могут быть другие загрузки.",
        ),
    ),
    HelpEntry(
        key="private",
        category=CAT_YT,
        title="Private video",
        log_example="ERROR: [youtube] xxxx: Private video. Sign in if you've been granted access to this video",
        patterns=("private video",),
        cause="Видео приватное: доступно только владельцу и тем, кому он выдал доступ. "
              "Приложение не умеет входить в аккаунт.",
        steps=(
            "Попроси автора открыть доступ по ссылке («Доступ по ссылке»).",
            "Либо найди публичную версию трека через вкладку «Поиск».",
        ),
    ),
    HelpEntry(
        key="age-restricted",
        category=CAT_YT,
        title="Sign in to confirm your age",
        log_example="ERROR: [youtube] xxxx: Sign in to confirm your age. "
                    "This video may be inappropriate for some users.",
        patterns=("confirm your age", "age-restricted", "inappropriate for some users"),
        cause="Видео с возрастным ограничением: YouTube показывает его только вошедшим в аккаунт.",
        steps=(
            "Найди ту же песню без ограничения через «Поиск» — часто есть версия на другом канале "
            "или на YouTube Music.",
            "Продвинутый способ: запусти `yt-dlp.exe` вручную с `--cookies-from-browser chrome` "
            "(в приложении входа в аккаунт нет).",
        ),
    ),
    HelpEntry(
        key="music-premium",
        category=CAT_YT,
        title="Only available to Music Premium members",
        log_example="ERROR: [youtube] xxxx: This video is only available to Music Premium members",
        patterns=("music premium",),
        cause="Трек доступен только по подписке YouTube Music Premium.",
        steps=(
            "В «Поиске» найди ту же песню с меткой `[YouTube]` — обычная версия часто доступна без подписки.",
            "Если такого варианта нет, скачать этот трек не получится.",
        ),
    ),
    HelpEntry(
        key="geo-blocked",
        category=CAT_YT,
        title="Видео заблокировано в вашей стране",
        log_example="ERROR: [youtube] xxxx: Video unavailable. This video contains content from X, "
                    "who has blocked it in your country on copyright grounds",
        patterns=("blocked it in your country", "not available in your country",
                  "not made this video available in your country"),
        cause="Правообладатель закрыл видео для вашего региона.",
        steps=(
            "Найди другую загрузку этого трека через «Поиск» (перезаливы, версия на другой площадке — "
            "`[YT Music]` или `[YouTube]`).",
            "Можно открыть ссылку через VPN в другой стране — но учитывай правила сервиса.",
        ),
    ),
    HelpEntry(
        key="premiere-live",
        category=CAT_YT,
        title="Премьера или трансляция ещё не началась",
        log_example="ERROR: [youtube] xxxx: Premieres in 2 hours",
        patterns=("premieres in", "live event will begin"),
        cause="Это запланированная премьера или прямой эфир — скачать можно только после начала или окончания.",
        steps=(
            "Подожди начала премьеры и повтори.",
            "Для трансляции дождись завершения эфира — запись станет обычным видео.",
        ),
    ),
    HelpEntry(
        key="unsupported-url",
        category=CAT_YT,
        title="Unsupported URL",
        log_example="ERROR: Unsupported URL: https://www.youtube.com/",
        patterns=("unsupported url",),
        cause="В поле ссылки не конкретный трек: главная страница, канал, результаты поиска "
              "или сайт, который yt-dlp не поддерживает.",
        steps=(
            "Открой нужный трек и скопируй ссылку из адресной строки или через «Поделиться».",
            "Ссылка должна вести на видео: `youtube.com/watch?v=…`, `music.youtube.com/watch?v=…` "
            "или `youtu.be/…`.",
            "Если ссылки под рукой нет — найди песню через вкладку «Поиск».",
        ),
    ),
    HelpEntry(
        key="unable-to-extract",
        category=CAT_YT,
        title="Unable to extract … (YouTube изменился)",
        log_example="ERROR: [youtube] xxxx: Unable to extract initial data; please report this issue on …",
        patterns=("unable to extract",),
        cause="YouTube изменил свой сайт, и установленная версия yt-dlp больше не умеет его разбирать. "
              "Обычно разработчики выпускают исправление за несколько часов или дней.",
        steps=(
            "Перезапусти приложение — оно само скачает свежий yt-dlp.",
            "Если обновление только что поставилось — подожди и повтори позже: исправление ещё не вышло.",
            "Удали `yt-dlp.exe` из папки данных приложения (`%LOCALAPPDATA%\\YouTubeMusicDownloader`) и запусти приложение — "
            "оно скачает чистую копию.",
        ),
    ),
    # ───────────────  Сеть  ───────────────
    HelpEntry(
        key="no-network",
        category=CAT_NET,
        title="Нет соединения / не удаётся найти сервер",
        log_example="ERROR: Unable to download webpage: <urlopen error [Errno 11001] getaddrinfo failed>",
        patterns=("getaddrinfo failed", "name or service not known", "failed to resolve",
                  "temporary failure in name resolution", "network is unreachable", "errno 11001"),
        cause="yt-dlp не смог достучаться до сайта: нет интернета, не работает DNS, "
              "либо соединение блокируют VPN, прокси, брандмауэр или антивирус.",
        steps=(
            "Проверь, открываются ли сайты в браузере.",
            "Отключи VPN/прокси или смени DNS (например, на `1.1.1.1` или `8.8.8.8`).",
            "Разреши `yt-dlp.exe` в брандмауэре Windows и в антивирусе.",
            "Повтори попытку.",
        ),
    ),
    HelpEntry(
        key="timeout",
        category=CAT_NET,
        title="Тайм-аут или обрыв соединения",
        log_example="ERROR: Unable to download webpage: The read operation timed out",
        patterns=("timed out", "connection reset", "connection aborted", "remote end closed connection",
                  "incomplete data"),
        cause="Соединение слишком медленное или нестабильное — сервер не ответил вовремя или оборвал передачу.",
        steps=(
            "Повтори — часто помогает с первого раза.",
            "Отключи VPN или перейди на более стабильную сеть.",
            "Закрой тяжёлые загрузки в фоне и проверь скорость интернета.",
        ),
    ),
    HelpEntry(
        key="ssl",
        category=CAT_NET,
        title="Ошибка SSL / сертификата",
        log_example="ERROR: Unable to download webpage: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] "
                    "certificate verify failed>",
        patterns=("certificate_verify_failed", "certificate verify failed", "ssl:"),
        cause="Компьютер не доверяет сертификату сайта: неверные дата и время, либо антивирус или прокси "
              "подменяет HTTPS-соединение.",
        steps=(
            "Проверь дату, время и часовой пояс в Windows — включи автоматическую установку времени.",
            "Отключи в антивирусе проверку HTTPS (веб-экран) или добавь `yt-dlp.exe` в исключения.",
            "Если сеть рабочая или с прокси — попробуй домашнюю.",
        ),
    ),
    # ───────────────  Файлы и ffmpeg  ───────────────
    HelpEntry(
        key="no-ffmpeg",
        category=CAT_FILES,
        title="ffmpeg / ffprobe не найден",
        log_example="ERROR: Postprocessing: ffprobe and ffmpeg not found. "
                    "Please install or provide the path using --ffmpeg-location",
        patterns=("ffprobe and ffmpeg not found", "ffmpeg not found", "ffprobe not found",
                  "ffmpeg/avconv not found", "ffprobe/avprobe"),
        cause="Для конвертации в mp3 нужны `ffmpeg.exe` и `ffprobe.exe` в папке данных приложения (`%LOCALAPPDATA%\\YouTubeMusicDownloader`). "
              "Файлы удалены, не докачались или заблокированы антивирусом.",
        steps=(
            "Проверь, что `ffmpeg.exe` лежит в папке данных приложения.",
            "Удали `ffmpeg.exe` и перезапусти приложение — окно установки скачает его заново.",
            "Добавь папку данных приложения в исключения антивируса, чтобы он снова не удалил файлы.",
        ),
    ),
    HelpEntry(
        key="postprocessing",
        category=CAT_FILES,
        title="Ошибка конвертации (ffmpeg)",
        log_example="ERROR: Postprocessing: Error opening input files: Invalid data found when processing input",
        patterns=("postprocessing:", "error opening input", "conversion failed",
                  "invalid data found when processing input"),
        cause="ffmpeg не смог превратить скачанный файл в mp3: загрузка повредилась, не хватило места, "
              "в имени файла неподходящий символ или ffmpeg устарел.",
        steps=(
            "Повтори загрузку.",
            "Проверь свободное место на диске.",
            "Выбери для сохранения папку с коротким путём без редких символов (например, `C:\\Music`).",
            "Обнови ffmpeg: удали `ffmpeg.exe` и перезапусти приложение.",
        ),
    ),
    HelpEntry(
        key="permission-denied",
        category=CAT_FILES,
        title="Нет доступа к папке (Permission denied)",
        log_example="PermissionError: [Errno 13] Permission denied: 'C:\\...\\track.mp3'",
        patterns=("permission denied", "[errno 13]", "access is denied", "[winerror 5]"),
        cause="Windows не даёт записать файл в выбранную папку: она защищена (Program Files, корень диска C:\\, "
              "«Контролируемый доступ к папкам» Защитника) или файл уже открыт в плеере.",
        steps=(
            "Выбери другую папку кнопкой «Обзор» — например, «Музыка» или «Загрузки».",
            "Закрой плеер или программу, где открыт этот файл.",
            "Добавь приложение в разрешённые в «Контролируемом доступе к папкам» Защитника Windows.",
        ),
    ),
    HelpEntry(
        key="disk-full",
        category=CAT_FILES,
        title="Нет места на диске",
        log_example="ERROR: unable to write data: [Errno 28] No space left on device",
        patterns=("no space left", "[errno 28]", "not enough space"),
        cause="На диске, куда сохраняется музыка (или на системном — для временных файлов), закончилось место.",
        steps=(
            "Освободи место на диске.",
            "Выбери папку на диске с запасом места («Обзор»).",
        ),
    ),
    HelpEntry(
        key="long-name",
        category=CAT_FILES,
        title="Слишком длинное имя файла",
        log_example="OSError: [Errno 36] File name too long",
        patterns=("file name too long", "filename too long", "[errno 36]"),
        cause="У трека очень длинное название, а общая длина пути к файлу в Windows ограничена "
              "примерно 260 символами (в стандартных настройках).",
        steps=(
            "Выбери папку с коротким путём, например `C:\\Music`.",
            "Либо включи поддержку длинных путей в Windows (параметр `LongPathsEnabled`).",
        ),
    ),
    HelpEntry(
        key="ytdlp-missing",
        category=CAT_FILES,
        title="yt-dlp.exe не найден",
        log_example="FileNotFoundError: [WinError 2] The system cannot find the file specified",
        patterns=("[winerror 2]", "cannot find the file specified"),
        cause="В папке данных приложения нет `yt-dlp.exe` (или `ffmpeg.exe`): файл удалён, переименован "
              "или убран антивирусом.",
        steps=(
            "Перезапусти приложение — окно «Первый запуск» скачает недостающее.",
            "Если файл исчезает снова — добавь папку данных приложения в исключения антивируса.",
        ),
    ),
    HelpEntry(
        key="file-in-use",
        category=CAT_FILES,
        title="Файл занят другим процессом",
        log_example="PermissionError: [WinError 32] The process cannot access the file because "
                    "it is being used by another process",
        patterns=("[winerror 32]", "being used by another process"),
        cause="Файл (`yt-dlp.exe`, `ffmpeg.exe` или mp3) открыт другой программой, поэтому его нельзя "
              "заменить или изменить — например, во время обновления.",
        steps=(
            "Закрой лишние окна приложения и процессы `yt-dlp.exe` / `ffmpeg.exe` в Диспетчере задач.",
            "Закрой плеер, в котором играет этот mp3.",
            "Перезапусти приложение и повтори.",
        ),
    ),
    # ───────────────  Само приложение  ───────────────
    HelpEntry(
        key="no-cover",
        category=CAT_APP,
        title="Трек скачан без обложки",
        log_example="[обложка] НЕ встроена (см. ошибку выше) — путь: '…'",
        patterns=("не удалось встроить обложку", "не встроена",
                  "не удалось определить путь к скачанному файлу"),
        cause="Сам трек скачался, но обложку не удалось записать в mp3: нет модуля `mutagen`, "
              "не получилось определить путь к файлу или у трека нет картинки.",
        steps=(
            "Открой «Debug режим» и найди строки `[обложка]` — там написана причина.",
            "Запуск из исходников: установи зависимости командой `pip install -r requirements.txt` "
            "(нужны `mutagen` и `Pillow`).",
            "Убедись, что обложка видна в правой панели ещё до скачивания.",
        ),
    ),
    HelpEntry(
        key="preview-fail",
        category=CAT_APP,
        title="Предпрослушивание не играет",
        log_example="Статус: «Не удалось получить аудиопоток»",
        patterns=(),
        cause="Не удалось получить прямую ссылку на аудио или воспроизвести её.",
        steps=(
            "Открой «Debug режим»: строки `[preview]` содержат ошибку yt-dlp (403, JavaScript runtime, "
            "недоступное видео…) — найди её в этом списке.",
            "Проверь звуковое устройство Windows и громкость.",
            "Если скачивание работает, а предпрослушивание нет — повтори позже: ссылка на поток живёт недолго.",
        ),
    ),
    HelpEntry(
        key="search-empty",
        category=CAT_APP,
        title="Поиск ничего не находит или долго думает",
        log_example="[youtube] ТАЙМАУТ (15 сек)",
        patterns=("таймаут (",),
        cause="yt-dlp не ответил за 15 секунд или вернул пустой список: медленная сеть, "
              "блокировка запросов или устаревший yt-dlp.",
        steps=(
            "Повтори поиск — источники работают независимо: если один не ответил, "
            "результаты второго всё равно покажутся.",
            "Посмотри строки `[youtube]` и `[youtube_music]` в «Debug режиме» — там причина.",
            "Перезапусти приложение (обновление yt-dlp) и отключи VPN.",
        ),
    ),
    HelpEntry(
        key="update-failed",
        category=CAT_APP,
        title="Ошибка при обновлении компонентов",
        log_example="В окне обновления: «Ошибка: <urlopen error …>»",
        patterns=(),
        cause="Не удалось скачать новую версию `yt-dlp.exe` или `ffmpeg.exe` с GitHub: нет сети, "
              "доступ к GitHub заблокирован, файл занят или его блокирует антивирус.",
        steps=(
            "Нажми «Повторить» или «Пропустить» — старые версии продолжат работать.",
            "Проверь интернет и доступ к `github.com`.",
            "Закрой другие копии приложения и процессы `yt-dlp.exe` / `ffmpeg.exe`.",
            "Если не выходит — скачай `yt-dlp.exe` и `ffmpeg.exe` вручную и положи в папку данных приложения.",
        ),
    ),
)


def find_matches(log_text: str) -> list[HelpEntry]:
    """Записи справочника, чьи patterns встречаются в тексте лога (порядок — как в справочнике)."""
    lowered = log_text.lower()
    return [e for e in HELP_ENTRIES if any(p in lowered for p in e.patterns)]
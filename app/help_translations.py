"""
Переводы справочника ошибок (app/help_data.py) на украинский и английский.

Русский текст лежит в самих записях HelpEntry; здесь — только то, что зависит
от языка: title / log_example (если они не английские), cause и steps.
Ключи совпадают с HelpEntry.key. `текст в обратных кавычках` выводится как код.
"""

D = "`%LOCALAPPDATA%\\YouTubeMusicDownloader`"

TRANSLATIONS: dict[str, dict[str, dict]] = {
    # ═══════════════════════════  УКРАЇНСЬКА  ═══════════════════════════
    "uk": {
        "bot-check": {
            "cause": "YouTube сприйняв запити з вашої мережі за автоматичні й просить увійти в акаунт. "
                     "Найчастіше таке буває при VPN, спільній IP-адресі або коли запитів було забагато поспіль.",
            "steps": (
                "Перезапусти програму — вона перевірить і оновить yt-dlp.",
                "Вимкни VPN/проксі або зміни мережу (наприклад, роздай інтернет з телефона).",
                "Зачекай 15–30 хвилин і повтори, не запускаючи багато завантажень поспіль.",
                "Якщо не допомагає: запусти `yt-dlp.exe` вручну з прапорцем `--cookies-from-browser chrome` "
                "(у самій програмі входу в акаунт немає).",
            ),
        },
        "http-403": {
            "cause": "Сервер відхилив запит на аудіопотік. Причини: застарілий yt-dlp, "
                     "не розв'язано JavaScript-завдання YouTube (немає Deno) або тимчасове блокування вашої IP.",
            "steps": (
                "Перезапусти програму — вона оновить yt-dlp.",
                "Встанови Deno — див. запис «No supported JavaScript runtime».",
                "Вимкни VPN/проксі або зміни мережу.",
                "Повтори пізніше — блокування за IP часто знімається саме.",
            ),
        },
        "http-429": {
            "cause": "За короткий час пішло забагато запитів — YouTube тимчасово обмежив вашу IP.",
            "steps": (
                "Зачекай від кількох хвилин до години, потім повтори.",
                "Не запускай одразу довгу чергу багато разів поспіль.",
                "Зміни мережу або IP-адресу.",
            ),
        },
        "js-runtime": {
            "title": "No supported JavaScript runtime could be found (немає Deno)",
            "log_example": "WARNING: [youtube] No supported JavaScript runtime could be found. "
                           "(текст може трохи відрізнятися в різних версіях yt-dlp)",
            "cause": "Щоб отримати посилання на аудіо, yt-dlp розв'язує JavaScript-завдання YouTube. Скрипти-розв'язувачі "
                     "вже вбудовано в `yt-dlp.exe`, а от сам JavaScript-рушій (за замовчуванням Deno) — ні. "
                     "Без нього YouTube віддає неповний список форматів, і тоді з'являються помилки "
                     "403 або «Requested format is not available».",
            "steps": (
                "Встанови Deno: у PowerShell виконай `winget install DenoLand.Deno` "
                "(або завантаж `deno.exe` з сайту Deno).",
                "Або поклади `deno.exe` у папку поруч із `yt-dlp.exe`, або переконайся, що він є в PATH.",
                "Перезапусти програму й повтори завантаження.",
            ),
        },
        "format-unavailable": {
            "cause": "yt-dlp не знайшов аудіоформат, який просить програма (найкращий аудіоформат, `-f ba`). "
                     "Найчастіше причина — застарілий yt-dlp або нерозв'язане JavaScript-завдання: "
                     "у цьому разі YouTube віддає лише картинки.",
            "steps": (
                "Перезапусти програму — вона оновить yt-dlp.",
                "Встанови Deno — див. запис «No supported JavaScript runtime».",
                "Перевір, що трек узагалі грає в браузері за цим самим посиланням.",
            ),
        },
        "unavailable": {
            "cause": "Відео видалено, приховано автором або недоступне саме вам (регіон, налаштування каналу).",
            "steps": (
                "Відкрий посилання в браузері. Якщо там теж недоступно — завантажити не можна.",
                "Якщо в браузері трек грає — перезапусти програму (оновлення yt-dlp) і повтори.",
                "Знайди цей самий трек на вкладці «Пошук»: там можуть бути інші завантаження.",
            ),
        },
        "private": {
            "cause": "Відео приватне: доступне лише власнику та тим, кому він надав доступ. "
                     "Програма не вміє входити в акаунт.",
            "steps": (
                "Попроси автора відкрити доступ за посиланням («Доступ за посиланням»).",
                "Або знайди публічну версію треку через вкладку «Пошук».",
            ),
        },
        "age-restricted": {
            "cause": "Відео з віковим обмеженням: YouTube показує його лише користувачам, які увійшли в акаунт.",
            "steps": (
                "Знайди ту саму пісню без обмеження через «Пошук» — часто є версія на іншому каналі "
                "або на YouTube Music.",
                "Просунутий спосіб: запусти `yt-dlp.exe` вручну з `--cookies-from-browser chrome` "
                "(у програмі входу в акаунт немає).",
            ),
        },
        "music-premium": {
            "cause": "Трек доступний лише за підпискою YouTube Music Premium.",
            "steps": (
                "У «Пошуку» знайди ту саму пісню з позначкою `[YouTube]` — звичайна версія часто доступна без підписки.",
                "Якщо такого варіанта немає, завантажити цей трек не вийде.",
            ),
        },
        "geo-blocked": {
            "title": "Відео заблоковано у вашій країні",
            "cause": "Правовласник закрив відео для вашого регіону.",
            "steps": (
                "Знайди інше завантаження цього треку через «Пошук» (перезаливи, версія на іншому майданчику — "
                "`[YT Music]` або `[YouTube]`).",
                "Можна відкрити посилання через VPN в іншій країні — але зважай на правила сервісу.",
            ),
        },
        "premiere-live": {
            "title": "Прем'єра або трансляція ще не почалася",
            "cause": "Це запланована прем'єра або пряма трансляція — завантажити можна лише після початку чи завершення.",
            "steps": (
                "Зачекай початку прем'єри й повтори.",
                "Для трансляції дочекайся завершення ефіру — запис стане звичайним відео.",
            ),
        },
        "unsupported-url": {
            "cause": "У полі посилання не конкретний трек: головна сторінка, канал, результати пошуку "
                     "або сайт, який yt-dlp не підтримує.",
            "steps": (
                "Відкрий потрібний трек і скопіюй посилання з адресного рядка або через «Поділитися».",
                "Посилання має вести на відео: `youtube.com/watch?v=…`, `music.youtube.com/watch?v=…` "
                "або `youtu.be/…`.",
                "Якщо посилання під рукою немає — знайди пісню через вкладку «Пошук».",
            ),
        },
        "unable-to-extract": {
            "title": "Unable to extract … (YouTube змінився)",
            "cause": "YouTube змінив свій сайт, і встановлена версія yt-dlp більше не вміє його розбирати. "
                     "Зазвичай розробники випускають виправлення за кілька годин або днів.",
            "steps": (
                "Перезапусти програму — вона сама завантажить свіжий yt-dlp.",
                "Якщо оновлення щойно встановилося — зачекай і повтори пізніше: виправлення ще не вийшло.",
                f"Видали `yt-dlp.exe` з папки даних програми ({D}) і запусти програму — вона завантажить чисту копію.",
            ),
        },
        "no-network": {
            "title": "Немає з'єднання / не вдається знайти сервер",
            "cause": "yt-dlp не зміг достукатися до сайту: немає інтернету, не працює DNS, "
                     "або з'єднання блокують VPN, проксі, брандмауер чи антивірус.",
            "steps": (
                "Перевір, чи відкриваються сайти в браузері.",
                "Вимкни VPN/проксі або зміни DNS (наприклад, на `1.1.1.1` або `8.8.8.8`).",
                "Дозволь `yt-dlp.exe` у брандмауері Windows і в антивірусі.",
                "Повтори спробу.",
            ),
        },
        "timeout": {
            "title": "Тайм-аут або обрив з'єднання",
            "cause": "З'єднання надто повільне або нестабільне — сервер не відповів вчасно або обірвав передачу.",
            "steps": (
                "Повтори — часто допомагає з першого разу.",
                "Вимкни VPN або перейди на стабільнішу мережу.",
                "Закрий важкі завантаження у фоні й перевір швидкість інтернету.",
            ),
        },
        "ssl": {
            "title": "Помилка SSL / сертифіката",
            "cause": "Комп'ютер не довіряє сертифікату сайту: неправильні дата й час, або антивірус чи проксі "
                     "підміняє HTTPS-з'єднання.",
            "steps": (
                "Перевір дату, час і часовий пояс у Windows — увімкни автоматичне встановлення часу.",
                "Вимкни в антивірусі перевірку HTTPS (веб-екран) або додай `yt-dlp.exe` до винятків.",
                "Якщо мережа робоча або з проксі — спробуй домашню.",
            ),
        },
        "no-ffmpeg": {
            "title": "ffmpeg / ffprobe не знайдено",
            "cause": f"Для конвертації в mp3 потрібні `ffmpeg.exe` і `ffprobe.exe` у папці даних програми ({D}). "
                     "Файли видалено, вони не докачалися або заблоковані антивірусом.",
            "steps": (
                "Перевір, що `ffmpeg.exe` лежить у папці даних програми.",
                "Видали `ffmpeg.exe` і перезапусти програму — вікно встановлення завантажить його знову.",
                "Додай папку даних програми до винятків антивіруса, щоб він знову не видалив файли.",
            ),
        },
        "postprocessing": {
            "title": "Помилка конвертації (ffmpeg)",
            "cause": "ffmpeg не зміг перетворити завантажений файл на mp3: завантаження пошкодилося, не вистачило місця, "
                     "в імені файла неприйнятний символ або ffmpeg застарів.",
            "steps": (
                "Повтори завантаження.",
                "Перевір вільне місце на диску.",
                "Обери для збереження папку з коротким шляхом без рідкісних символів (наприклад, `C:\\Music`).",
                "Онови ffmpeg: видали `ffmpeg.exe` і перезапусти програму.",
            ),
        },
        "permission-denied": {
            "title": "Немає доступу до папки (Permission denied)",
            "cause": "Windows не дозволяє записати файл у вибрану папку: вона захищена (Program Files, корінь диска C:\\, "
                     "«Контрольований доступ до папок» Захисника) або файл уже відкрито в плеєрі.",
            "steps": (
                "Обери іншу папку кнопкою «Огляд» — наприклад, «Музика» або «Завантаження».",
                "Закрий плеєр або програму, де відкрито цей файл.",
                "Додай програму до дозволених у «Контрольованому доступі до папок» Захисника Windows.",
            ),
        },
        "disk-full": {
            "title": "Немає місця на диску",
            "cause": "На диску, куди зберігається музика (або на системному — для тимчасових файлів), закінчилося місце.",
            "steps": (
                "Звільни місце на диску.",
                "Обери папку на диску із запасом місця («Огляд»).",
            ),
        },
        "long-name": {
            "title": "Надто довге ім'я файла",
            "cause": "У треку дуже довга назва, а загальна довжина шляху до файла у Windows обмежена "
                     "приблизно 260 символами (у стандартних налаштуваннях).",
            "steps": (
                "Обери папку з коротким шляхом, наприклад `C:\\Music`.",
                "Або ввімкни підтримку довгих шляхів у Windows (параметр `LongPathsEnabled`).",
            ),
        },
        "ytdlp-missing": {
            "title": "yt-dlp.exe не знайдено",
            "cause": f"У папці даних програми ({D}) немає `yt-dlp.exe` (або `ffmpeg.exe`): файл видалено, перейменовано "
                     "або прибрано антивірусом.",
            "steps": (
                "Перезапусти програму — вікно «Перший запуск» завантажить відсутнє.",
                "Якщо файл зникає знову — додай папку даних програми до винятків антивіруса.",
            ),
        },
        "file-in-use": {
            "title": "Файл зайнятий іншим процесом",
            "cause": "Файл (`yt-dlp.exe`, `ffmpeg.exe` або mp3) відкрито іншою програмою, тому його не можна "
                     "замінити чи змінити — наприклад, під час оновлення.",
            "steps": (
                "Закрий зайві вікна програми та процеси `yt-dlp.exe` / `ffmpeg.exe` у Диспетчері завдань.",
                "Закрий плеєр, у якому грає цей mp3.",
                "Перезапусти програму й повтори.",
            ),
        },
        "no-cover": {
            "title": "Трек завантажено без обкладинки",
            "log_example": "[обложка] НЕ встроена (см. ошибку выше) — путь: '…'",
            "cause": "Сам трек завантажився, але обкладинку не вдалося записати в mp3: немає модуля `mutagen`, "
                     "не вийшло визначити шлях до файла або в треку немає картинки.",
            "steps": (
                "Відкрий «Режим debug» і знайди рядки `[обложка]` — там написано причину.",
                "Запуск з вихідного коду: встанови залежності командою `pip install -r requirements.txt` "
                "(потрібні `mutagen` і `Pillow`).",
                "Переконайся, що обкладинку видно в правій панелі ще до завантаження.",
            ),
        },
        "preview-fail": {
            "title": "Попереднє прослуховування не грає",
            "log_example": "Статус: «Не вдалося отримати аудіопотік»",
            "cause": "Не вдалося отримати пряме посилання на аудіо або відтворити його.",
            "steps": (
                "Відкрий «Режим debug»: рядки `[preview]` містять помилку yt-dlp (403, JavaScript runtime, "
                "недоступне відео…) — знайди її в цьому списку.",
                "Перевір звуковий пристрій Windows і гучність.",
                "Якщо завантаження працює, а попереднє прослуховування ні — повтори пізніше: посилання на потік живе недовго.",
            ),
        },
        "search-empty": {
            "title": "Пошук нічого не знаходить або довго думає",
            "log_example": "[youtube] ТАЙМАУТ (15 сек)",
            "cause": "yt-dlp не відповів за 15 секунд або повернув порожній список: повільна мережа, "
                     "блокування запитів або застарілий yt-dlp.",
            "steps": (
                "Повтори пошук — джерела працюють незалежно: якщо одне не відповіло, "
                "результати другого все одно покажуться.",
                "Подивись рядки `[youtube]` і `[youtube_music]` у «Режимі debug» — там причина.",
                "Перезапусти програму (оновлення yt-dlp) і вимкни VPN.",
            ),
        },
        "update-failed": {
            "title": "Помилка під час оновлення компонентів",
            "log_example": "У вікні оновлення: «Помилка: <urlopen error …>»",
            "cause": "Не вдалося завантажити нову версію `yt-dlp.exe` або `ffmpeg.exe` з GitHub: немає мережі, "
                     "доступ до GitHub заблоковано, файл зайнятий або його блокує антивірус.",
            "steps": (
                "Натисни «Повторити» або «Пропустити» — старі версії продовжать працювати.",
                "Перевір інтернет і доступ до `github.com`.",
                "Закрий інші копії програми та процеси `yt-dlp.exe` / `ffmpeg.exe`.",
                f"Якщо не виходить — завантаж `yt-dlp.exe` і `ffmpeg.exe` вручну та поклади в папку даних програми ({D}).",
            ),
        },
    },
    # ═══════════════════════════  ENGLISH  ═══════════════════════════
    "en": {
        "bot-check": {
            "cause": "YouTube mistook the requests from your network for automated ones and asks you to sign in. "
                     "This usually happens with a VPN, a shared IP address, or after too many requests in a row.",
            "steps": (
                "Restart the app — it will check for and update yt-dlp.",
                "Turn off the VPN/proxy or switch networks (for example, share internet from your phone).",
                "Wait 15–30 minutes and try again, without starting many downloads in a row.",
                "If that doesn't help: run `yt-dlp.exe` manually with the `--cookies-from-browser chrome` flag "
                "(the app itself has no account sign-in).",
            ),
        },
        "http-403": {
            "cause": "The server rejected the request for the audio stream. Causes: an outdated yt-dlp, "
                     "YouTube's JavaScript challenge not being solved (no Deno), or a temporary block of your IP.",
            "steps": (
                "Restart the app — it will update yt-dlp.",
                "Install Deno — see the entry “No supported JavaScript runtime”.",
                "Turn off the VPN/proxy or switch networks.",
                "Try again later — IP blocks often lift on their own.",
            ),
        },
        "http-429": {
            "cause": "Too many requests were sent in a short time — YouTube temporarily limited your IP.",
            "steps": (
                "Wait from a few minutes to an hour, then try again.",
                "Don't start a long queue many times in a row.",
                "Switch networks or change your IP address.",
            ),
        },
        "js-runtime": {
            "title": "No supported JavaScript runtime could be found (no Deno)",
            "log_example": "WARNING: [youtube] No supported JavaScript runtime could be found. "
                           "(the wording may differ slightly between yt-dlp versions)",
            "cause": "To get audio links, yt-dlp solves YouTube's JavaScript challenges. The solver scripts "
                     "are already built into `yt-dlp.exe`, but the JavaScript engine itself (Deno by default) is not. "
                     "Without it YouTube returns an incomplete list of formats, which leads to "
                     "403 or “Requested format is not available” errors.",
            "steps": (
                "Install Deno: in PowerShell run `winget install DenoLand.Deno` "
                "(or download `deno.exe` from the Deno website).",
                "Either put `deno.exe` in the folder next to `yt-dlp.exe`, or make sure it is in your PATH.",
                "Restart the app and try the download again.",
            ),
        },
        "format-unavailable": {
            "cause": "yt-dlp couldn't find the audio format the app asks for (best audio, `-f ba`). "
                     "Most often the cause is an outdated yt-dlp or an unsolved JavaScript challenge: "
                     "in that case YouTube only returns images.",
            "steps": (
                "Restart the app — it will update yt-dlp.",
                "Install Deno — see the entry “No supported JavaScript runtime”.",
                "Check that the track actually plays in a browser at the same link.",
            ),
        },
        "unavailable": {
            "cause": "The video was deleted, hidden by its author, or is unavailable specifically to you (region, channel settings).",
            "steps": (
                "Open the link in a browser. If it's unavailable there too, it can't be downloaded.",
                "If the track plays in the browser, restart the app (yt-dlp update) and try again.",
                "Find the same track in the “Search” tab: there may be other uploads.",
            ),
        },
        "private": {
            "cause": "The video is private: only the owner and people they've granted access to can see it. "
                     "The app can't sign in to an account.",
            "steps": (
                "Ask the author to allow access by link (“Unlisted”).",
                "Or find a public version of the track via the “Search” tab.",
            ),
        },
        "age-restricted": {
            "cause": "The video is age-restricted: YouTube only shows it to signed-in users.",
            "steps": (
                "Find the same song without a restriction via “Search” — there is often a version on another channel "
                "or on YouTube Music.",
                "Advanced way: run `yt-dlp.exe` manually with `--cookies-from-browser chrome` "
                "(the app has no account sign-in).",
            ),
        },
        "music-premium": {
            "cause": "The track is only available with a YouTube Music Premium subscription.",
            "steps": (
                "In “Search” find the same song tagged `[YouTube]` — the regular version is often available without a subscription.",
                "If there is no such version, this track can't be downloaded.",
            ),
        },
        "geo-blocked": {
            "title": "Video is blocked in your country",
            "cause": "The rights holder blocked the video for your region.",
            "steps": (
                "Find another upload of this track via “Search” (re-uploads, a version on another platform — "
                "`[YT Music]` or `[YouTube]`).",
                "You can open the link through a VPN in another country — but keep the service's rules in mind.",
            ),
        },
        "premiere-live": {
            "title": "Premiere or live stream hasn't started yet",
            "cause": "This is a scheduled premiere or a live broadcast — it can only be downloaded after it starts or ends.",
            "steps": (
                "Wait for the premiere to start and try again.",
                "For a live stream, wait until the broadcast ends — the recording becomes a regular video.",
            ),
        },
        "unsupported-url": {
            "cause": "The link field doesn't contain a specific track: it's a home page, a channel, search results "
                     "or a site that yt-dlp doesn't support.",
            "steps": (
                "Open the track you need and copy the link from the address bar or via “Share”.",
                "The link must lead to a video: `youtube.com/watch?v=…`, `music.youtube.com/watch?v=…` "
                "or `youtu.be/…`.",
                "If you don't have a link at hand, find the song via the “Search” tab.",
            ),
        },
        "unable-to-extract": {
            "title": "Unable to extract … (YouTube has changed)",
            "cause": "YouTube changed its site, and the installed yt-dlp version can no longer parse it. "
                     "The developers usually release a fix within a few hours or days.",
            "steps": (
                "Restart the app — it will download a fresh yt-dlp by itself.",
                "If the update was just installed, wait and try again later: the fix isn't out yet.",
                f"Delete `yt-dlp.exe` from the app's data folder ({D}) and start the app — it will download a clean copy.",
            ),
        },
        "no-network": {
            "title": "No connection / can't find the server",
            "cause": "yt-dlp couldn't reach the site: there is no internet, DNS isn't working, "
                     "or the connection is blocked by a VPN, proxy, firewall or antivirus.",
            "steps": (
                "Check whether websites open in your browser.",
                "Turn off the VPN/proxy or change DNS (for example to `1.1.1.1` or `8.8.8.8`).",
                "Allow `yt-dlp.exe` in the Windows firewall and in your antivirus.",
                "Try again.",
            ),
        },
        "timeout": {
            "title": "Timeout or dropped connection",
            "cause": "The connection is too slow or unstable — the server didn't answer in time or cut the transfer.",
            "steps": (
                "Try again — it often works the second time.",
                "Turn off the VPN or switch to a more stable network.",
                "Close heavy background downloads and check your internet speed.",
            ),
        },
        "ssl": {
            "title": "SSL / certificate error",
            "cause": "The computer doesn't trust the site's certificate: the date and time are wrong, or an antivirus or proxy "
                     "is intercepting the HTTPS connection.",
            "steps": (
                "Check the date, time and time zone in Windows — turn on automatic time setting.",
                "Turn off HTTPS scanning (web shield) in your antivirus or add `yt-dlp.exe` to its exclusions.",
                "If the network is a work one or uses a proxy, try your home network.",
            ),
        },
        "no-ffmpeg": {
            "title": "ffmpeg / ffprobe not found",
            "cause": f"Converting to mp3 requires `ffmpeg.exe` and `ffprobe.exe` in the app's data folder ({D}). "
                     "The files were deleted, didn't finish downloading, or were blocked by an antivirus.",
            "steps": (
                "Check that `ffmpeg.exe` is in the app's data folder.",
                "Delete `ffmpeg.exe` and restart the app — the setup window will download it again.",
                "Add the app's data folder to your antivirus exclusions so it doesn't delete the files again.",
            ),
        },
        "postprocessing": {
            "title": "Conversion error (ffmpeg)",
            "cause": "ffmpeg couldn't turn the downloaded file into an mp3: the download got corrupted, there wasn't enough space, "
                     "the file name contains an unsuitable character, or ffmpeg is outdated.",
            "steps": (
                "Try the download again.",
                "Check the free space on the disk.",
                "Pick a save folder with a short path and no unusual characters (for example `C:\\Music`).",
                "Update ffmpeg: delete `ffmpeg.exe` and restart the app.",
            ),
        },
        "permission-denied": {
            "title": "No access to the folder (Permission denied)",
            "cause": "Windows doesn't allow writing a file to the chosen folder: it is protected (Program Files, the root of drive C:\\, "
                     "Defender's “Controlled folder access”) or the file is already open in a player.",
            "steps": (
                "Choose another folder with the “Browse” button — for example “Music” or “Downloads”.",
                "Close the player or program where this file is open.",
                "Add the app to the allowed apps in Windows Defender's “Controlled folder access”.",
            ),
        },
        "disk-full": {
            "title": "No space left on the disk",
            "cause": "The disk where the music is saved (or the system disk, for temporary files) is out of space.",
            "steps": (
                "Free up some disk space.",
                "Choose a folder on a disk with free space (“Browse”).",
            ),
        },
        "long-name": {
            "title": "File name too long",
            "cause": "The track has a very long title, and the total length of a file path in Windows is limited "
                     "to about 260 characters (with default settings).",
            "steps": (
                "Choose a folder with a short path, for example `C:\\Music`.",
                "Or enable long path support in Windows (the `LongPathsEnabled` setting).",
            ),
        },
        "ytdlp-missing": {
            "title": "yt-dlp.exe not found",
            "cause": f"There is no `yt-dlp.exe` (or `ffmpeg.exe`) in the app's data folder ({D}): the file was deleted, "
                     "renamed or removed by an antivirus.",
            "steps": (
                "Restart the app — the “First launch” window will download what's missing.",
                "If the file disappears again, add the app's data folder to your antivirus exclusions.",
            ),
        },
        "file-in-use": {
            "title": "File is being used by another process",
            "cause": "The file (`yt-dlp.exe`, `ffmpeg.exe` or an mp3) is open in another program, so it can't "
                     "be replaced or changed — for example, during an update.",
            "steps": (
                "Close extra app windows and the `yt-dlp.exe` / `ffmpeg.exe` processes in Task Manager.",
                "Close the player that is playing this mp3.",
                "Restart the app and try again.",
            ),
        },
        "no-cover": {
            "title": "Track downloaded without a cover",
            "log_example": "[обложка] НЕ встроена (см. ошибку выше) — путь: '…'  (= cover NOT embedded, see the error above)",
            "cause": "The track itself downloaded, but the cover couldn't be written into the mp3: the `mutagen` module is missing, "
                     "the file path couldn't be determined, or the track has no picture.",
            "steps": (
                "Open “Debug mode” and look for the `[обложка]` lines — the reason is written there.",
                "Running from source: install the dependencies with `pip install -r requirements.txt` "
                "(`mutagen` and `Pillow` are required).",
                "Make sure the cover is visible in the right panel even before downloading.",
            ),
        },
        "preview-fail": {
            "title": "Preview doesn't play",
            "log_example": "Status: “Couldn't get the audio stream”",
            "cause": "The direct audio link couldn't be obtained or played.",
            "steps": (
                "Open “Debug mode”: the `[preview]` lines contain the yt-dlp error (403, JavaScript runtime, "
                "unavailable video…) — find it in this list.",
                "Check the Windows sound device and the volume.",
                "If downloading works but the preview doesn't, try again later: the stream link doesn't live long.",
            ),
        },
        "search-empty": {
            "title": "Search finds nothing or takes too long",
            "log_example": "[youtube] ТАЙМАУТ (15 сек)  (= timeout, 15 s)",
            "cause": "yt-dlp didn't answer within 15 seconds or returned an empty list: a slow network, "
                     "blocked requests, or an outdated yt-dlp.",
            "steps": (
                "Search again — the sources work independently: if one didn't answer, "
                "the results of the other will still be shown.",
                "Look at the `[youtube]` and `[youtube_music]` lines in “Debug mode” — the reason is there.",
                "Restart the app (yt-dlp update) and turn off the VPN.",
            ),
        },
        "update-failed": {
            "title": "Error while updating components",
            "log_example": "In the update window: “Error: <urlopen error …>”",
            "cause": "The new version of `yt-dlp.exe` or `ffmpeg.exe` couldn't be downloaded from GitHub: there is no network, "
                     "access to GitHub is blocked, the file is in use, or an antivirus is blocking it.",
            "steps": (
                "Press “Retry” or “Skip” — the old versions will keep working.",
                "Check your internet and access to `github.com`.",
                "Close other copies of the app and the `yt-dlp.exe` / `ffmpeg.exe` processes.",
                f"If it doesn't work, download `yt-dlp.exe` and `ffmpeg.exe` manually and put them in the app's data folder ({D}).",
            ),
        },
    },
}

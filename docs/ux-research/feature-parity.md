# Контракт збереження функцій вебінтерфейсу

База: `36d93687`; джерело поведінки — `web/static/app.js` та `workspace_web.py`. Це acceptance checklist для майбутніх PR. У дослідницькій гілці немає змін застосунку; **позначення «заплановано» не означає, що новий UI уже реалізовано чи протестовано**.

Усі рядки нижче мають бути закриті до заміни старого UI. Зміна компонування допустима; видалення можливості, непомітна зміна семантики чи втрата даних — release blocker. A11y-вдосконалення та нові presentation states позначені в окремому плані, щоб не видавати їх за чинні можливості.

| ID | Поточна функція / контракт | Розміщення після редизайну | Приймальна перевірка |
| --- | --- | --- | --- |
| F01 | П'ять розділів: overview/inbox/graph/clusters/jobs | Стабільна головна навігація | Усі досяжні keyboard і pointer, активний стан зрозумілий |
| F02 | EN/UK, persisted language, `html.lang` | Мовний control у shell | Перемикання зберігає відкритий контекст і всі поточні чернетки |
| F03 | Refresh, health/connection state, назва локальної БД | Shell / статус підключення | Успіх/збій відображаються; refresh не очищує draft |
| F04 | Skip-link, focus-visible, aria-current, live/busy/error states | Shell та компоненти | Keyboard path, retry, announce без дублювання всього довгого контенту |
| F05 | Alt+1…5; `/`; Ctrl+Enter у notes | Ті самі сценарії + доступна довідка | Пошук не перехоплює `/` у полях; Ctrl+Enter виконує явне збереження |
| F06 | Overview counters: all/new/to-read/read | Чотири компактні metrics | Значення відповідають `/api/summary`, zero-state коректний |
| F07 | Recent papers, reading queue, перехід у бібліотеку/публікацію | Огляд | Відкривається правильний id; відсутні роботи не породжують фіктивних карток |
| F08 | Допомога початку роботи, CLI/TUI instructions, пояснення score | Empty state / довідка / score explanation | Інструкції лишаються досяжними; не з'являється фіктивний web-search |
| F09 | Пошук title/abstract/venue/notes, debounce, latest-request guard | Toolbar бібліотеки | Запит і результати узгоджені; застаріла відповідь не перезаписує нову |
| F10 | Фільтр all/new/to-read/read/archived/dismissed | Статус бібліотеки | Усі шість варіантів і чинні API enums збережені |
| F11 | П'ять sort: relevance_score/recent/newest_added/citations/title | Сортування | Вибір передає той самий параметр і реально змінює порядок |
| F12 | Results count і ліміт 200 | Над списком | Розрізняються total та displayed; не заявляється нова backend-pagination |
| F13 | Назва, рік/unknown, source/unknown, citations, status, relevance у рядку | Сканований bibliographic row | Жодне поле не зникло; score не названо quality/confidence |
| F14 | Open paper detail, selected id, stale detail-request guard | Detail pane / вузький detail-view | Повільна стара відповідь не відкриває іншу роботу |
| F15 | Title, authors, abstract/fallback, citation count, relevance у detail | Вкладка «Опис» | Повний текст доступний; Unicode/markup екрануються |
| F16 | Зовнішнє посилання DOI/URL із перевіркою http(s) | «Відкрити першоджерело» | Безпечний протокол, нова вкладка; відсутній URL не стає broken action |
| F17 | Редагування п'яти status, tags і research notes | «Мої нотатки» | PATCH зберігає notes/status/tags та сумісний зі старими клієнтами |
| F18 | Explicit save, disabled pending state, success/error feedback | Save-bar / форма | Подвійні кліки контрольовані, помилка не видаляє текст |
| F19 | Draft paper/form/inline edits при переходах, мові, refresh | Спільний UI state | Відновлюються note, tags, status, annotation kind/content/source й незавершені edits |
| F20 | Note provenance, legacy origin/time unknown | «Мої нотатки» / «Історія» | Migration time не видається за первинний час створення |
| F21 | Note history, lazy loading, cursor pagination, cleared notes | «Історія» | Load older працює; запис про очищення не пропускається; restore/delete не вигадуються |
| F22 | Перехід від detail до графа з `seed_id` | «Переглянути зв'язки» | Правильна стартова робота, збережена семантика graph state |
| F23 | Supplemental annotations окремі від `papers.notes` | «Матеріали та походження» | Імпорт/редагування додаткового запису не переписує власні нотатки |
| F24 | Перегляд annotation kind, method, source_ref, timestamps, revision, review state | Annotation card | Усі provenance-поля доступні; кольору недостатньо для розрізнення |
| F25 | Manual create: user/imported/extracted/generated, content, optional source | «Додати матеріал» | Усі варіанти є; ручний kind позначений як заявлений, а не перевірений adapter |
| F26 | Inline edit, save, cancel, draft | Editor annotation | Cancel справді скасовує; save передає `expected_revision` |
| F27 | Accepted/dismissed/unreviewed; accept/dismiss/reopen | Review actions | Усі переходи працюють; зміна review не підмінює походження |
| F28 | Optimistic revision conflict HTTP 409 | Conflict state біля editor | Текст користувача не губиться, немає тихого overwrite; доступний reload/reconcile path |
| F29 | Annotation cursor pagination, load older | Список матеріалів | Нові записи між сторінками не спричиняють втрат/дублів |
| F30 | JSON array import, ≤100 records / ≤1 MB, validation, idempotency | Import dialog / секція | Invalid/too-large/duplicate/partial-invalid сценарії; atomicity збережена |
| F31 | Stored metadata extraction | Extraction action | Використовує збережені дані, повторення не дублює матеріали |
| F32 | Opt-in generated suggestions зі stored assessment або local heuristic | Явний checkbox і пояснення | За замовчуванням opt-in вимкнений; немає нового provider/model request |
| F33 | Graph relation all/cites/related та edge-provider filter | Панель фільтрів | Значення/очищення збережені; provider не плутається з primary paper source |
| F34 | Graph depth 1/2 | Панель фільтрів | Збережено traversal semantics і межі API |
| F35 | Inclusive year_from/year_to, unknown-year policy, invalid range error | Панель фільтрів | Seed лишається видимим за межами діапазону з поясненням |
| F36 | Apply/reset graph filters | Toolbar + filter panel | Reset повертає всі дефолти; видимі активні умови відповідають запиту |
| F37 | Bounded graph, counts, truncated notice; web limit 80 | Canvas status | Ліміт не приховано; zero/isolated/no edges коректно пояснені |
| F38 | Citing→cited arrows; undirected related; unique edges, multi-provider provenance | Легенда, ребра, inspector | Тип і напрям не змінені; усі observations/providers доступні |
| F39 | Pan drag, bounded zoom in/out, reset view | Canvas controls | Pan/zoom не змінюють dataset; reset відновлює view |
| F40 | Node selection click/Enter/Space, visible selected state | Canvas + inspector | Вибір вузла відділений від recenter; клавіатура працює |
| F41 | Selected links: references/cited-by/related + timestamp/provider | Inspector | Списки відображають правильний напрям відносно selected node |
| F42 | Open selected paper та explore neighborhood | Дві різні inspector actions | Перша відкриває detail; друга змінює seed, не викликає зовнішній provider |
| F43 | SVG, GraphML, JSON export поточного filtered snapshot | Export-menu | Три формати, Unicode escaping, напрям, related semantics, provenance; JSON filters |
| F44 | Heuristic clusters tag/venue/topic/unclustered, counts, paper previews | «Групи публікацій» | Підстава групування й disclaimer збережені; preview≠повний склад |
| F45 | Jobs scan/digest enabled flags і OS instructions | Розклад | Enabled config не видається за підтверджену runtime-активність |
| F46 | Remove/disable scan чи digest із confirmation | Дії розкладу | Cancel без мутації; success/error коректні; жодного видалення papers |
| F47 | Install default jobs і опис default times/customization CLI/TUI | Дія розкладу | Збережені defaults і platform semantics; тести мокають реальний scheduler |
| F48 | Page-level loading/error/retry, toasts, empty states; no stale page replacement | Усі розділи | Zero-data, slow response, offline/error, rapid navigation не створюють неправдивого success |

## Інваріанти безпеки та сумісності

- Зберігаються API paths, методи, validation, id, enum values, storage schema та `LITRADAR_*` identifiers. Перекладаються labels, а не protocol values.
- Вміст notes, annotations, source references і title трактувати як текст; не вставляти неперевірений HTML. Download/export коректно екранує Unicode/XML.
- Локальний backend, loopback binding і наявна модель single-user не змінюються через UI-роботи. Не додавати telemetry або зовнішній CDN без окремого рішення.
- Жодного доступу до production DB/.env/PDF/Telegram; усі acceptance fixtures синтетичні. Jobs endpoints у browser-тестах підміняються, щоб не змінювати реальний scheduler/config.
- Current tests — регресійна основа, не доказ повного E2E. Новий UI мусить пройти всі наведені сценарії незалежно від зміни CSS selectors.

## Покриття в демонстраційному HTML

`concept.html` показує візуальний напрям і кілька переходів: п'ять макетних екранів, theme/density, вибір синтетичної роботи, вкладки detail, демо-редагування notes, graph inspector. Він не реалізує production API, JSON import, збереження annotations, scheduler чи справжній graph export. Такі дії явно позначені як специфікація/демо й не можуть замінити F01–F48 під час приймання реалізації.

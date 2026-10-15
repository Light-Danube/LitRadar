# План наступного оновлення вебінтерфейсу

Актуалізація 2026-10-13: [Phase 1 реалізована як кандидат для review](phase-1.md); [офіційні публічні джерела конкурентів прочитані повторно](live-review-2026-10-13.md). Початкові обмеження й концепт нижче збережені як історія дослідження. Hands-on конкурентів і browser visual acceptance залишаються відкритими.


Статус: reviewable draft. Реалізація починається після узгодження напряму та базової перевірки концепту. Наявний frontend — HTML/CSS/vanilla JS/SVG; новий framework, Node runtime у production, нова база чи сервіс не потрібні.

## 1. Межі робіт

Мета: покращити читання, пошук потрібної дії та збереження контексту з повною відповідністю [F01–F48](feature-parity.md). Головні величини — час/помилки у конкретних завданнях, розуміння походження матеріалів, відсутність втрати draft. Красива landing page або кількість анімацій не є критерієм успіху.

Поточні API та data model — незмінна основа першої серії PR. Якщо компонент потребує нового endpoint, винести залежність в окремий технічний RFC і не блокувати типографіку/компонування. Наприклад, pagination понад 200 results, backend saved views, history restore та browser scholarly search не входять у цей редизайн.

## 2. Послідовність невеликих PR

Оцінки нижче — орієнтир планування для одного розробника, а не обіцянка строків; не включають очікування CI, доступу, recruiting чи user review. Після першого PR уточнити їх за фактом.

| Крок | Зміни / основні файли | Залежність | Критерій готовності | Орієнтир |
| --- | --- | --- | --- | --- |
| UX-00 | Прочитати живі джерела, перевірити концепт 3–5 внутрішніми проходами; погодити терміни й default theme | Доступ до S1–S8, браузер | Ledger оновлений; відкриті рішення записані, а не сховані в CSS | 1–2 дні активної роботи |
| UX-01 | Семантичні CSS tokens, typography scale, light/dark/system preference, control states; `styles.css`, shell | UX-00 | Контраст усіх states; 200%/320 px smoke; нуль втрат функцій | 2–3 дні |
| UX-02 | Адаптивна оболонка, nav, status, settings menu, focus/keyboard conventions; `index.html`, `app.js`, locales | UX-01 | Усі 5 розділів; мова/theme/draft; немає offscreen focused controls | 1–2 дні |
| UX-03 | Library rows, selected state, counts, detail width, narrow detail/back, full abstract; `renderInbox/renderDetail` | UX-02 | F09–F19/F22, відновлення контексту, no nested abstract scroll | 3–4 дні |
| UX-04 | Notes/materials/history sections, explicit save state, provenance card, import/extract grouping, conflict state | UX-03 | F20–F32, 409 зберігає чернетку, opt-in вимкнений, pagination не губиться | 3–4 дні |
| UX-05 | Graph toolbar/filter panel, selected inspector, legend, доступна альтернатива drag, export menu | UX-02; shared detail UX-03 | F33–F43; граф/експорти семантично ідентичні baseline | 3–4 дні |
| UX-06 | Overview empty/established states, group explanations, jobs clarity; locales | UX-02 | F06–F08/F44–F48, правильні platform messages | 1–2 дні |
| UX-07 | E2E regression, accessibility/localization review, usability iteration, документація й screenshots | Попередні UI PR | Повна parity matrix, виправлені blockers, рішення про default theme | 3–5 днів + usability sessions |

Не об'єднувати всі екрани в один великий PR. Кожен PR містить before/after на тих самих synthetic fixtures, регресійні перевірки зміненої поведінки, точні passed/failed/skipped counts, screenshots і оновлення README/CHANGELOG/handoff за потреби. Відкривати як draft; merge залишається за власником.

## 3. Компонентний backlog

### Tokens та shared primitives

- Токени мають semantic names: text/surface/muted/selected/border/focus/danger/success, а не `blue-17` у кожному renderer.
- Єдині Button, IconButton, Field, Select, Badge, EmptyState, ErrorState, Toast patterns. Усі pending/disabled/hover/focus стани описані.
- Preference для теми/щільності зберігати окремо від наукових даних; default theme strategy не порушує існуючі налаштування. Локальна preference не є синхронізацією акаунта.
- Не починати з повного переписування `app.js`. Виносити невеликі render/helpers за потреби, підтримуючи поточні API contracts і latest-response guards.

### Library/detail

- Виділений рядок використовує фон, indicator і accessibility state; вибір зберігає paper id.
- Heading hierarchy не змішує номер запису з головним заголовком. Поряд із title — автори/рік/видання, далі abstract; score другорядний і підписаний.
- Notes/status/tags залишаються в єдиній save transaction, поки backend-контракт такий. Label кнопки: «Зберегти зміни»; поруч пояснення, які поля будуть збережені.
- Dirty state не заявляє збереження до успішного PATCH. Перемикання вкладки, мови, теми чи розділу зберігає draft у поточній сесії. Refresh сторінки браузера — окреме UX-рішення; чинний in-memory draft не оголошувати durable storage.
- На вузькому екрані Back повертає до того ж рядка. Deep-link/browser history можна додати в окремому кроці з регресійними тестами; не змішувати з CSS-only PR.

### Provenance/import/conflicts

- Card завжди розрізняє kind, origin_method і review_status: «Згенеровано» не означає «Прийнято», «Імпортовано» не означає «Перевірено».
- Згорнуті деталі можуть приховати довгі timestamps/source strings, але indicator і шлях «Показати походження» завжди видимі.
- Import dialog пояснює JSON-масив, 100 записів/1 MB, ідемпотентність; помилка валідації лишає зрозумілий шлях повторної спроби. Не обіцяє PDF/RIS/BibTeX.
- Extraction dialog явно називає «збережені метадані»; generation checkbox unchecked. Допоміжний текст пояснює stored assessment/local heuristic та відсутність нового model request.
- Для 409: зберегти локальний текст, показати «Запис змінився після відкриття», запропонувати завантажити актуальну версію для порівняння. Не виконувати force overwrite або вигаданий merge endpoint.

### Graph

- Filter panel зберігає всі контролі й draft/applied distinction; active count рахує справді застосовані non-default умови.
- Inspector не перекриває canvas на desktop і не забирає фокус у keyboard selection без явної дії.
- При graph load/error або зміні seed не показувати старий inspector як актуальний. Ліміт, unknown-year policy й seed-exception доступні.
- Export menu працює keyboard/Touch/Escape. Тести порівнюють node ids, edge direction/type та provider provenance у всіх форматах із поточним filtered API snapshot; pan/zoom не обрізає дані.
- Додаткові pan controls — покращення доступності, а не зміна topology/layout. Dense graphs перевіряються окремо, не лише на 4 красивих вузлах.

## 4. Дані та стани для приймання

Тільки synthetic fixtures і disposable SQLite. Поточна бібліотека користувача, `.env`, notes, PDFs чи токени не потрібні.

| Набір | Що перевіряємо |
| --- | --- |
| 0 / 1 / 8 / 200+ papers | Empty/normal/capped results, точний count, відсутність фіктивної pagination |
| Long EN/UK titles, unknown author/year, no abstract, emoji/markup | Переноси, fallback, escaping, відповідний заголовок без обрізання доступного тексту |
| Long abstract 8–12 абзаців; notes 1–50k chars | Тривале читання, scroll ownership, save/error, text-spacing overrides |
| Annotation 0/1/51+, усі kind/method/review combinations | Load older, source distinction, idempotent import, довгі source_ref, редагування |
| Concurrent revision, 409; invalid JSON; 1 MB boundary; 101 records | Помилки й recovery без втрати тексту чи часткової мутації |
| Graph 0/1/10/80 nodes, multi-provider edges, related/cites, unknown years | Легенда, keyboard select, bounding, seed exception, exports, dense labels |
| Jobs enabled/disabled, Windows/Unix mocks, failed action | Config/runtime distinction; confirmation; жодного реального scheduler side effect |
| Slow/out-of-order 200, 404/422/409/500, lost connection | Latest-request guards, retry, stale-state indicators, відсутність false success |

## 5. Перевірки й gates

### Regression suite

З root репозиторію з підготовленим venv:

```bash
.venv/bin/python -m pytest -q -ra
node --check web/static/app.js
node --check web/static/locales.js
node --check web/static/graph-tools.js
node --test tests/test_web_frontend.cjs
```

Запуск restricted Docker runner за наявності робочого build environment: `docker compose -f compose.isolated-dev.yaml run --build --rm dev`. Очікувані optional skips класифікувати окремо. Не вимикати sandbox/network/TLS заради зеленого результату.

### Browser acceptance

- Viewports 1440×900, 1280×800, 1024×768, 768×1024, 390×844, 320 CSS px; EN і UK; світла/темна; 200% zoom; reduced motion.
- Keyboard-only: skip → nav → search → row → detail → notes/save → graph → node/inspector → export. Таб-порядок логічний, focus не закритий sticky bar.
- Browser E2E fixtures підміняють зовнішні APIs та jobs; для реального локального API — лише disposable DB, no `.env`.
- Automated a11y scan — допоміжний; screen-reader smoke і manual keyboard review обов'язкові. «0 автоматичних помилок» не означає повну WCAG-відповідність.
- Перевірка текстових кольорів/controls/graph в усіх states; 1.4.12 spacing overrides без обрізання. На mobile звичайний контент не потребує горизонтальної прокрутки.
- Не виставляти Lighthouse score як доказ наукової usability. Performance budget визначити після baseline; орієнтир — локальна навігація без full-page flash і без помітних input stalls на 200 рядках.

### Release blockers

Будь-яка втрата notes/draft/provenance; зміна enum або API semantics; пропущена функція F01–F48; неправдивий saved-state; неможливість виконати основний сценарій клавіатурою; непрацюючий експорт; некоректне пояснення `cites`/`related`; неоднозначна згода на generation; доступ до реальних даних у тестах.

## 6. План дослідження з користувачами H

Перший formative round: **6–8 учасників**, 45–60 хвилин, цільовий баланс початківців/досвідчених дослідників, EN/UK та різних reading preferences; за можливості включити користувачів клавіатури/assistive technology. Це якісна вибірка, не статистично репрезентативне дослідження ринку. Потрібні згода, мінімальний запис даних і синтетичний corpus.

1. Знайти конкретну роботу за частиною назви/нотатки, позначити «До читання», додати тег.
2. Прочитати довгу анотацію, написати власну нотатку, перейти в граф і повернутися без втрати тексту.
3. Визначити, який матеріал є власним, імпортованим, extracted або generated; назвати джерело й метод.
4. Імпортувати JSON, повторити імпорт, пояснити результат без дублів.
5. На графі знайти роботу, яка цитує seed; застосувати роки/provider; пояснити unknown-year і seed exception; експортувати GraphML.
6. Змінити мову/тему; завершити note-save клавіатурою; відновитися після контрольованого 409.
7. Пояснити стан scan/digest на mocked Unix screen; відмовитися від видалення на confirmation.

Порівнювати baseline і draft на еквівалентних, але різних synthetic tasks; чергувати порядок, щоб зменшити learning effect. Записувати task success, critical errors, допомогу модератора, час, кількість повернень/пошуків дії, SEQ після завдання та якісні цитати зі згодою.

Початкові цілі для приймання (не вже отримані результати): жодної втрати draft або помилкового overwrite; усі critical tasks досяжні; щонайменше 80% учасників завершують core tasks без допомоги; напрям цитування та generated provenance не плутаються повторювано. Для 6–8 людей звітувати абсолютні n/N, не лише відсоток. Бажане скорочення медіанного часу triage на 15–20% — гіпотеза, яку можна відхилити, не маркетингова обіцянка.

## 7. Відкриті рішення та handoff

1. Default theme: system preference чи явний light default для нових користувачів; поточних не мігрувати примусово без рішення.
2. Українські назви abstract/annotation та «Матеріали та походження» — перевірити comprehension.
3. Desktop split поріг і комфортна щільність — за довгими назвами й laptop viewport, не лише 4K mock.
4. Persistent draft після повного reload браузера — окреме рішення щодо приватності/життєвого циклу; не входить автоматично в parity.
5. Пошук понад 200 results та повний склад cluster — окремий API increment; у першому UI чесно показати межі.

Перший implementation PR має містити tokens/type scale, одну тему-пару й адаптивні control states. Перед передаванням усіх screens перевірити один повний сценарій «Бібліотека → нотатка → граф → повернення». Запуск нових features roadmap — після закриття parity й Docker/CI gates відповідної release-гілки.

# Local bibliography import / Імпорт локальної бібліографії

Post-1.0 implementation for review; no new release. This workflow adds **paper records** to SQLite. Annotation import attaches supplemental material to an existing paper and remains a separate action. Ukrainian publication discovery, Ukrainian institutional providers and your own local files are separate capabilities.

## English instructions

1. Before a large import, make a trusted [library backup](../USER-GUIDE.md#consistent-local-backup-and-restore).
2. In the browser's Inbox, expand **Import papers from local files**, select individual RIS, BibTeX or PDF files, and request a preview.
3. Review metadata and new/duplicate/conflict/skipped/failed statuses. Uncheck unwanted rows. Conflicts cannot overwrite existing papers; correct the input or review the existing record separately.
4. Confirm the selected rows. New papers enter the ordinary library and its metadata search. Duplicate papers retain their existing fields and user data; a separate provenance observation records the import. Changing files or matching library records requires a fresh preview.

RIS works with the standard installation. BibTeX and PDF require the existing optional parsers: from a checkout, run `python -m pip install -r requirements-annotations.txt`; for a wheel install, use `python -m pip install "litradar[annotations]"`. Installing dependencies uses the network; importing does not.

CLI preview (individual paths relative to an explicitly chosen input root):

```sh
python cli.py --db data/litradar.sqlite3 import-papers --root selected-files references.ris papers.bib
```

After reviewing the JSON output, repeat the same command with `--commit --preview-token TOKEN`. Optionally add `--select 0 2` to import specific zero-based preview rows. Without `--select`, CLI confirmation imports all new/duplicate rows; conflict/skipped/failed rows remain excluded. A preview neither creates nor migrates the target database. No folder scanning occurs.

## Інструкція українською

1. Перед великим імпортом створіть довірену резервну копію бібліотеки.
2. У розділі «Вхідні» відкрийте панель імпорту локальних файлів, виберіть окремі RIS, BibTeX або PDF і запустіть попередній перегляд.
3. Перевірте метадані та статуси записів. Зніміть позначки з непотрібних рядків і підтвердьте збереження вибраних. Конфлікти не перезаписують наявні праці; виправте вхідний файл або перевірте наявний запис окремо.
4. Нові праці з'являться у звичайній бібліотеці та пошуку за її метаданими. Для дублікатів зберігається окремий запис походження; наявні нотатки, теги та інші дані не змінюються. Після зміни файлів чи відповідних записів бібліотеки повторіть перегляд.

Для CLI використовуйте наведену вище команду: `--root` задає каталог, а аргументи — лише окремі відносні назви файлів. Після перевірки JSON повторіть команду з `--commit --preview-token TOKEN`; `--select 0 2` обмежує вибір рядками 0 і 2. Попередній перегляд не створює й не змінює БД. RIS доступний одразу; для BibTeX/PDF потрібні необов'язкові залежності з `requirements-annotations.txt` або extra `annotations`.

## Scope and limits

- Maximum 10 files, 5,000,000 bytes per file, 10,000,000 bytes combined, 500 preview rows, 2 MB parsed/preview metadata and a 30-second batch parsing budget. Optional parser workers have a maximum 10-second timeout each. On POSIX they additionally use CPU/address-space limits; Windows has the parent timeout and byte/page caps, without the POSIX memory limit.
- PDF support reads **PDF Info title/author only**, with low confidence, for unencrypted PDFs up to 50 pages. No page-text extraction, OCR, filename inference or full-text indexing. Missing usable titles are skipped. A scanned PDF with suitable Info metadata can supply a metadata record; its pages are not interpreted. Add reliable DOI/year/abstract through RIS/BibTeX instead.
- Metadata search uses the existing SQLite search. Ukrainian Unicode is preserved; FTS behavior is covered by synthetic tests. This makes no claim about Ukrainian semantic ranking, morphology or full-text search quality. New records are unranked; import loads no embedding model.
- File links/attachments in bibliography fields are not opened or copied. No URL resolution, DOI lookup, provider call, watcher or filesystem scan. Browser uploads send selected bytes only to the local server; filenames are labels. CLI rejects traversal, network roots, symlinks, hard links, reparse points, devices, archives and directories as inputs, with no-follow handle checks where supported. Native platform behavior requires separate validation.
- The importer stores metadata, safe basenames, SHA-256, parser version, record key, format, timestamp, batch journal and per-paper observations. It does not retain the original RIS/BibTeX/PDF bytes or absolute input paths. Keep originals separately; deleting them does not break stored records. Declared language remains provenance, not verified full-text language.
- Canonical DOI/title normalization is reused. Ambiguous title/DOI cases and differing existing metadata are conflicts rather than automatic merges. Missing incoming metadata never clears existing metadata. Notes, tags, annotations, citations, evidence, status and rankings stay intact on duplicates.

## Recovery and compatibility

Each confirmed batch saves papers and provenance in one SQLite transaction; a failed commit rolls back the batch. Re-importing an identical file/record does not duplicate its paper or observation. Batches may still record separate confirmations. Two additive tables, `local_import_batches` and `local_import_observations`, are included automatically in the existing whole-database backup. Existing backup format and restore rules are unchanged; originals are not included.

This first increment intentionally provides **no automatic destructive undo**. The earlier feasibility design proposed undo for untouched additions; safe ownership checks and deletion UX are deferred. To recover a complete prior state, restore a trusted pre-import backup into a **new destination**, then explicitly choose that library. Do not overwrite the active library or delete papers with subsequent user edits. Reverting this feature's code leaves its additive tables and existing records in place; never drop user data as a code rollback.

## Technical and licensing evidence

| Concern | Evidence and interpretation |
| --- | --- |
| Offline boundary | [byte-only import service](../../storage/local_import.py), [parser worker](../../storage/local_import_parsers.py), [CLI selected-path reader](../../storage/local_import_paths.py), [upload API](../../web/local_import_api.py). No new provider, resolver or transport. |
| Identity and preservation | Existing `Paper` normalization and `PaperStore.find_existing_paper_id`; only new records use insertion, duplicates append observations. Synthetic preservation, stale-preview and rollback tests in [core tests](../../tests/test_local_import.py). |
| Parsers | Existing optional dependency ranges remain `bibtexparser>=1.4,<2` and `pypdf>=5,<7`. Installed distribution evidence: bibtexparser 1.4.4 declares `License: LGPLv3 or BSD`; pypdf 6.21.2 declares `License-Expression: BSD-3-Clause`. Official projects: [bibtexparser](https://github.com/sciunto-org/python-bibtexparser), [pypdf](https://github.com/py-pdf/pypdf). Consult the installed distribution's license terms when redistributing dependencies. RIS parsing uses Python's standard library. No parser code is vendored. |
| Content rights | Parser licenses do not license imported research. Users must have the right to use their selected files; no redistribution permission is inferred from importing metadata. No NBUV/OUCI/NRAT content is fetched by this workflow. |
| Recovery | [existing backup/restore](../../storage/recovery.py), [CLI/legacy/backup roundtrip tests](../../tests/test_local_import_cli.py). No backup-format or release-version change. |

Validation results and platform limits are recorded in the focused Draft PR. Linux tests do not establish native Windows/macOS or real-browser rendering; hosted CI must be checked separately. The NBUV JNAS pilot remains pending interface/permission evidence and separate implementation approval.

## Increment and validation record

The implementation follows three steps within this focused feature: (1) bounded byte parsers, conservative deduplication and additive transaction journal; (2) explicit CLI and EN/UK browser preview/selection/confirmation; (3) preservation, unsafe-input, Unicode search and recovery regression checks. Modified areas are `storage/local_import*.py`, the additive schema in `storage/sqlite.py`, CLI registration, a separate upload API/browser module, locale strings, documentation and focused tests. The Windows workflow now includes this synthetic import suite; configuring a job is not evidence it ran.

Local Linux Python 3.12.14 / Node 24.19.0 verification:

- Full Python suite: **832 passed, 0 failed, 0 skipped**, one Starlette/httpx deprecation warning. Final import-only recheck: **64 passed, 0 failed, 0 skipped** with the same warning; optional BibTeX/PDF parsers were installed.
- `npm ci --prefix tests/web --ignore-scripts`, then full DOM suite: **9 file-level tests passed, 0 failed, 0 skipped**. The standalone import module contains **8 passing scenarios**. This is jsdom evidence, not native browser rendering.
- Changed JS syntax checks and `git diff --check` passed. A locally built, unversioned-development wheel installed into an isolated repository-local target passed module/CLI registration, selected-file import and packaged browser-asset checks. It is not a published release artifact.
- Exact storage code read from the public v1.0.0 tag opened a synthetic imported library, edited notes, and reopened with current storage while retaining tags, annotations and import journal. Existing backup/new-destination restore preserved the new tables. This scoped compatibility check does not certify every old client operation.
- No live scholarly provider, embedding model or personal research data was used. Native Windows/macOS execution and same-commit hosted CI remain unverified; report actual PR checks separately.

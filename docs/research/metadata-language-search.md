# OpenAlex metadata-language search / Пошук за мовою метаданих

This post-1.0 change is proposed in a Draft PR. It keeps the three default providers and existing unfiltered search behavior. No version, tag or release is changed.

## Meaning and coverage

OpenAlex documents `language` as the automatically detected language of a work's **title and abstract**, not necessarily its full text. `uk` means Ukrainian metadata; it cannot certify a Ukrainian-language publication. Query language, venue identity/country, author affiliation and EN/UK interface locale remain separate. See the [official language definition](https://help.openalex.org/data/languages/), [filter syntax](https://help.openalex.org/api/filtering/) and [CC0 metadata/service terms](https://help.openalex.org/access/pricing/), checked 2026-10-21. Full-text rights remain separate.

`any` is the default and sends no language filter. `uk` and `en` use the server's structured filter. Only OpenAlex has this verified capability in the implementation; a filtered broad search including Semantic Scholar or arXiv fails before any provider request or database opening. Select OpenAlex explicitly, or deliberately run an unfiltered search. It never silently filters the first N broad results or retries unfiltered. Unknown/contradictory returned language in a filtered response is an error, not an empty successful page.

Missing or malformed language stays unknown, including Cyrillic titles. Raw language remains in provider metadata and is also recorded with normalized language and interpretation in per-provider SQLite source references. A different provider's observation retains those references. This is current per-provider provenance, not a complete historical language audit log.

One bounded page is retrieved. Venue search uses the **primary** OpenAlex source identity and may miss repository copies listed only as other locations. Zero results do not prove absence of Ukrainian scholarship. See [pagination](https://help.openalex.org/api/paging/) and [current budgets/authentication](https://help.openalex.org/api/authentication/). No provider API smoke was used to substantiate documentation semantics.

## English instructions

From a source checkout, explicitly run:

```sh
python cli.py search "розпізнавання емоцій" --sources openalex --metadata-language uk --no-semantic
python cli.py search "emotion recognition" --sources openalex --metadata-language en --profile research_profile.uk-en.example.json --no-semantic
python cli.py venue lookup "journal name"
python cli.py venue search SOURCE_ID "дослідження" --metadata-language uk
```

Replace `SOURCE_ID` with a concrete `S`+digits identity returned by lookup. These commands perform explicit network discovery and store results. `venue search` also saves an immutable `search.json` snapshot containing the original query, applied filter, language basis and returned raw metadata. Broad CLI search has no new automatic snapshot/export workflow.

In **Research**, select **OpenAlex metadata language** (`Any language`, `Ukrainian`, `English`) and explicitly submit the source search. Merely changing the selection, locale, theme or preset makes no scholarly request. Results disclose the applied language scope and returned language/unknown values. General TUI and Telegram searches remain unfiltered; they do not gain an implicit language mode.

The separate example profile is optional; it does not replace `research_profile.json`, alter schedules or download a model. Wheel users can explicitly download the [source example](https://github.com/Light-Danube/LitRadar/blob/codex/openalex-metadata-language/research_profile.uk-en.example.json) to a chosen local path and pass that path with `--profile`. It is not automatically seeded into user data. Use `--no-semantic` for keyword-only ranking. NFC normalization and casefolding support Ukrainian combining sequences and case; no translation, stemming, inflection coverage or Ukrainian neural-ranking quality is claimed. Stored-library FTS uses Unicode tokenization; stock SQLite LIKE fallback still lacks equivalent Cyrillic case-insensitivity and is deferred to local-library work.

## Інструкція українською

У **Research** оберіть **Мова метаданих OpenAlex → Українська** та явно запустіть пошук у вибраному джерелі. Це мова назви й анотації за даними OpenAlex; мова повного тексту може відрізнятися. У CLI використовуйте першу команду вище з `--sources openalex --metadata-language uk --no-semantic`. Типове значення `any` зберігає пошук без мовного фільтра. Для інших провайдерів цей фільтр явно не підтримується. Невідома мова не визначається за абеткою. Приклад профілю UK/EN підключається окремо через `--profile` і не змінює ваш профіль чи розклад. Імпорт PDF/RIS/BibTeX до вже наявної праці залишається імпортом анотацій; окремий імпорт бібліографії та новий український адаптер тут не реалізовані.

## Compatibility, validation and rollback

No SQLite schema migration is added. Notes, tags, statuses, annotations, citations, evidence and backup format remain unchanged. New optional Paper fields have defaults, so old cached JSON remains readable. Unfiltered cache keys stay unchanged; filtered broad and venue caches include normalized language in addition to existing scope. Revert the feature commit without deleting any database/cache. Additive language provenance in JSON is harmless to old readers; old versions may treat new-field source caches as cache misses during explicit searches.

No new provider, filesystem traversal, model download, background job or listener change is introduced. Documentation access is distinct from live API behavior and from permission for a future Ukrainian provider. Local tests use synthetic responses/databases; native Windows/macOS, real-browser rendering, hosted CI and Ukrainian semantic-quality evaluation require separate evidence. Exact validation and Draft PR references belong in the PR description; Phase0 audit and local-bibliography design are in [Draft PR49](https://github.com/Light-Danube/LitRadar/pull/49).

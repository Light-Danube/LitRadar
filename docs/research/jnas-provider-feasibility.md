# JNAS NBUV: focused provider feasibility dossier

Checked 2026-10-21. The user selected **JNAS NBUV as the research priority**, not as approval to implement an adapter. This supplements the [Phase0 matrix](multilingual-local-discovery-feasibility.md) in Draft PR49. Remote main was independently rechecked at `82ba1b1d5a2c9279f164542d173c526245d04092`; PR49 and PR50 were open drafts. No application, source registry, data, listener, model or release change is part of this investigation.

## Decision

**Metadata-reuse evidence found; adapter still no-go pending a verified machine interface and service constraints.** The earlier matrix's licensing uncertainty can now be narrowed. An open metadata license does not establish a functioning endpoint, unlimited harvesting, full-text rights or approval to implement.

## Evidence matrix

All sources are public institutional/operator pages or primary protocol documentation. A readable web page is not an API smoke test; unsuccessful web-tool retrieval does not prove a service is down.

| Question | Evidence and status | Consequence |
| --- | --- | --- |
| Resource identity | [JNAS about](https://jnas.nbuv.gov.ua/en/about) identifies the journal segment and links its regulations. [NBUV ResearchUA](https://research.nbuv.gov.ua/node/61) explicitly reports OAI-PMH support. **Official documentation.** | Scope is the JNAS/NAS journal collection, not every NBUV catalog or every Ukrainian publication. |
| Metadata reuse | [JNAS regulations](https://jnas.nbuv.gov.ua/rr.pdf#page=7), §6.6, explicitly identify **CC0 1.0** for scientific-publication metadata on the site. Cyrillic PDF extraction is imperfect; the clean [NAS regulatory collection](https://openscience.nas.gov.ua/storage/editor/files/zbirnyk-akty-nan-ukrainy-vn-chastina-1-10-12-2025.pdf#page=27), §7.8.1–7.8.2, corroborates CC0 metadata reuse, including commercial and noncommercial uses. **Published policy evidence.** | Preserve the policy URL/section/access date as metadata-license provenance. Do not continue describing JNAS metadata rights as wholly unverified. Confirm whether the eventual feed includes material outside this scope. |
| Full texts | JNAS regulations §6.4 and §7 distinguish publication-specific licenses from metadata licensing. **Published policy.** | Metadata CC0 is not a blanket PDF license. Pilot should retrieve metadata/landing links only; no full-text downloader or OCR. |
| Actual architecture | [NBUV's 2024 conference report](https://www.conference.nbuv.gov.ua/report/view/id/2184) describes JNAS metadata exported to `http://open-science.nbuv.gov.ua/biblio`, a Drupal repository with OAI-PMH, then harvested by NAS. The [operator's resource list](https://harvester.nas.gov.ua/doc/books/spisok-resursiv-na-indeksaciiu/page/spisok-elektronnix-bibliotek-ta-zurnaliv-nan-ukrayini) lists LibNAS at `http://open-science.nbuv.gov.ua/` with a positive status. **Historical/operator documentation.** | Keep JNAS article pages, the metadata repository and the harvester distinct. Do not invent an OAI endpoint on `jnas.nbuv.gov.ua` from its hostname. The resource-list status is not a fresh protocol test. |
| Exact interface | [Repository landing](https://open-science.nbuv.gov.ua/) was readable and links JNAS and a Repository view; the bibliography view was not successfully returned by the web tool. No exact current OAI base URL was established from reviewed material. **Not verified.** | No guessed `/oai`, `/oai2` or Drupal route probes. Ask operator for the current documented base URL or supported export. |
| Schema / language | A [single JNAS article page](https://jnas.nbuv.gov.ua/article/UJRN-0000483820) displays original and English titles, authors, year, journal/issue/pages, a stable-looking UJRN landing identifier and a citation marked Ukrainian. **Observed human-readable example only.** | This does not prove feed fields, DOI completeness or machine-readable language semantics. Bilingual titles do not imply bilingual full text. Do not derive language from title script. |
| Identifiers | UJRN article URL is observable; OAI header IDs and DOI mapping are not. **Partially observed.** | Store provider ID, OAI ID and DOI separately. Do not synthesize DOI or equate a journal issue with a paper. |
| Pagination / updates | No provider-specific `resumptionToken`, set, deletion, datestamp/granularity or expiry behavior observed. **Not verified.** | General OAI rules are design requirements, not claims about this deployment. |
| Authentication / rate limits | No documented machine-access auth, request rate, concurrency, batch size, retry policy or maintenance window found in reviewed pages. **Not verified.** | Public reading and CC0 do not imply unlimited machine access. Obtain service guidance. |
| Transport restrictions | Following the JNAS harvester link reached an Anubis access-denied page. Bibliography/PDF fetches sometimes timed out or failed in the web reader. **Observed tool limitation.** | Do not bypass challenges or treat blocked HTML as zero papers. No complete service-availability conclusion follows. |

## Interface design, conditional on evidence and later approval

[OAI-PMH](https://www.openarchives.org/OAI/openarchivesprotocol.html) is a metadata-harvesting protocol, not arbitrary keyword search. Do not advertise JNAS keyword queries as a remote search API without documentation.

A small candidate pilot would ingest a user-selected, documented journal set or bounded date window into a local collection, then search the imported metadata locally. It must remain disabled by default, with explicit user-triggered retrieval. The final choice between bounded local harvesting and a genuinely documented remote-search service depends on the operator's answer.

Proposed observation fields: provider label, exact approved endpoint, OAI identifier/datestamp/set, JNAS UJRN landing URL, DOI if supplied, original titles/authors/date/venue, original language value and its documented interpretation, retrieval time and metadata-license policy reference. Keep article language, translated-metadata language and interface locale separate. Preserve unknown and conflicting values and reuse canonical identity checks without overwriting user notes/tags/annotations/evidence/citations.

Any proposed request/page/record/byte/time caps must be labeled application safety bounds, not provider quotas. Tokens are opaque and must not become arbitrary remote URLs. Bound XML before parsing; reject DTD/external entities and entity-expansion hazards. Do not follow metadata file/URL references. An operator-declared endpoint/redirect must remain within a reviewed allowlist.

## Missing evidence to obtain

1. Exact current OAI-PMH base URL, supported HTTPS access and any permitted redirects; or a supported machine-readable export.
2. `Identify` and `ListMetadataFormats` documentation/sample responses; actual metadata prefixes and field definitions, especially language/translated titles/DOI/UJRN.
3. A selectable journal set/date range and a small sample record with a stable OAI identifier; deleted/empty-record rules and update granularity.
4. Paging/resumption-token mechanics, expiry, maximum response size and recovery after failures.
5. Authentication, permitted request frequency/concurrency, retry/maintenance guidance and any registration requirements.
6. Confirmation that the documented CC0 metadata scope covers that feed, including abstracts/translations where present; full-text rights remain separate.
7. After this dossier is complete, the user's separate approval of one concrete adapter scope.

Only after interface/access conditions are confirmed should a bounded protocol smoke be proposed: `Identify`, `ListMetadataFormats`, optional set discovery, one selected record/page, and one next-page token if safely bounded. No unbounded `ListRecords`, corpus mirror or live provider call in ordinary tests.

## Draft operator inquiry — Ukrainian

Contact published on the [repository landing page](https://open-science.nbuv.gov.ua/): **libnas@nbuv.gov.ua**. This text is a draft for the user; no message was sent.

**Тема: Документований доступ до метаданих JNAS / LibNAS через OAI-PMH**

Добрий день! Для локального дослідницького інструмента LitBeacon розглядаємо добровільне, обмежене отримання бібліографічних метаданих журналів JNAS. У регламенті сайту (§6.6) зазначено CC0 1.0 для метаданих; у матеріалах НБУВ описано їх передавання через репозитарій open-science.nbuv.gov.ua. Просимо надати актуальну базову адресу OAI-PMH або документацію підтримуваного експорту, формати й приклад запису, спосіб вибору окремого журналу/періоду, правила пагінації та оновлення/видалення записів, вимоги до автентифікації й допустимі частоту та паралельність запитів. Також просимо підтвердити поширення CC0 на метадані цього інтерфейсу, включно з анотаціями та перекладами за їх наявності. Початковий сценарій — лише метадані та посилання на оригінальні сторінки, без завантаження повних текстів. Дякуємо!

## Checks, changed files and rollback

This follow-up adds this dossier and updates the JNAS row/link in the audit document on the existing `codex/multilingual-local-feasibility` documentation branch / [Draft PR49](https://github.com/Light-Danube/LitRadar/pull/49). Validate whitespace, relative Markdown links, exact policy sections and the decision's consistency with the matrix. No implementation tests were rerun for these documentation changes; prior Phase1 local/CI results are separate evidence and are not relabeled as JNAS validation. No JNAS OAI XML response, native-platform test or new CI pass is claimed.

Rollback: revert these documentation commits. No SQLite migration or application rollback is needed. Application source, models, user files, source registry and release artifacts are unchanged.

**Українською:** наразі користуйтеся JNAS вручну через його офіційний сайт. CC0 для метаданих підтверджено документами; інтеграція LitBeacon очікує точного інтерфейсу, правил доступу та окремого погодження. Нової команди JNAS у програмі немає.

**English:** use the official JNAS site manually for now. Published policy supports CC0 metadata reuse; LitBeacon integration awaits a verified interface, service rules and separate approval. No JNAS command or adapter has been implemented.

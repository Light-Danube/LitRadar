# Optional local semantic exploration

Semantic workspace exploration is OFF by default. Existing tag/venue/title-term
clusters and provider citation records remain the default. Install
`requirements-semantic.txt` only when this optional feature is wanted. Enable the
workspace flag `LITBEACON_SEMANTIC_WORKSPACE=1` and provide an explicitly selected
existing directory with `LITBEACON_EMBEDDING_MODEL_PATH`. Legacy `LITRADAR_*`
aliases are supported. The model path is server-side and is not returned to the
browser;
the UI must additionally request semantic exploration for each graph/clustering
operation. Missing dependencies/models produce an actionable error, not an
automatic network download or silent fallback claiming semantic results.

The loader uses `local_files_only=True`, `trust_remote_code=False`, and
`use_safetensors=True`. Only title/abstract text is embedded: personal notes and
annotations are omitted. Inputs are bounded to 200 papers and 6,000 characters
per paper. These limits are intentional; no persistent embedding cache or schema
migration is introduced.

Related edges use **raw cosine similarity**, default threshold 0.72, and maximum
five neighbors per node. They are undirected, deduplicated, ephemeral and labeled
with `embedding:<model>` provenance. They are never stored as citations and never
imply causation or a citation relationship. Thresholds are exploratory settings,
not probabilities or validated acceptance cutoffs. Complete-link clusters require
every cross-cluster pair to meet the threshold, preventing similarity chains from
grouping dissimilar endpoints. Singleton groups remain visible. Clusters are
deterministic and separately identified from heuristic clusters.

## Reproducible evaluation and its limits

`tests/fixtures/semantic-public-titles.json` contains six real public bibliographic
titles and DOI links in three author-labeled topics. It includes no article text
or abstracts. Metadata was manually curated: attempts to verify all six entries
through the Crossref API on 2026-10-14 returned proxy **403 Forbidden**. These
entries must not be represented as freshly verified API downloads. Topic labels
are author judgments, not a representative benchmark or gold standard.

Run the no-network control with:

```bash
python -m ranking.evaluate_semantic_workspace --lexical-control
python -m ranking.evaluate_semantic_workspace --lexical-control --threshold 0.5
```

Executed results: at 0.72 the lexical control emits no edges (precision undefined,
recall 0/3); at 0.5 it emits one correct gravitational-wave pair (precision 1/1,
recall 1/3). Cluster pair metrics match those results. **This control is bag of
words, not neural embedding evaluation.** Synthetic-vector unit tests validate
cosine math, zero/invalid vectors, neighbor caps, deduplication, complete-link
behavior, text bounds and offline loading settings; they do not demonstrate
language-model quality.

Evaluate a user-provided local safetensors model without downloading anything:

```bash
python -m ranking.evaluate_semantic_workspace --local-model ./models/your-model
```

The repository-local `models/` directory and safetensors weights are excluded
from Git and Docker build contexts. Do not commit model binaries or include
personalized weights in the isolated runner.

No local neural model was available during this change; its quality evaluation
remains pending. Before promoting this experimental feature, verify bibliographic
metadata, run the local-model command, inspect edge precision/recall and cluster
pair precision/recall, and expand the public corpus across languages and topics.
The present title-only corpus cannot establish multilingual or abstract-level
quality, optimal thresholds, or usefulness to participants.

## Browser/API integration

The graph checkbox adds `include_semantic=true`; default requests are unchanged.
Computed related edges can participate in seeded traversal within a bounded
200-paper/year-filtered candidate cohort. Relation/provider filters still apply.
The threshold and evaluated-node count are returned as metadata; computed
provenance has no fabricated provider-observation timestamp. No computed edge is
written to `paper_relations`.

Clusters offer the existing heuristic method and an explicit local-embedding
mode (`/api/clusters?mode=semantic`, capped to 200 papers). A single-cohort
in-memory result cache avoids repeated encoding; current status/tags/notes are
attached from the latest database snapshot without embedding their contents.
Both graph and clusters return 409 when semantic mode is requested while the
server flag is off, and 503 when a local model/dependency is unavailable. There
is no silent switch to lexical results.

Four API regressions cover OFF-default/no encoding, ephemeral seeded links,
relation/provider/year filters, current workflow metadata on cache hits and a
missing-model failure. Official model metadata retrieval from Hugging Face also
returned proxy 403; neural quality validation remains pending.

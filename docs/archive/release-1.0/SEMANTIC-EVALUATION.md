# LitBeacon 1.0 semantic evaluation record

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

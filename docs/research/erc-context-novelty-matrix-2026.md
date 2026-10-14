# Context selection for ERC and sarcasm: working evidence matrix

Review cutoff: **2026-10-14**. Recent window: 2023-01-01–2026-10-14, inclusive; five older foundations retained. This is a bounded discovery review of **20 unique papers**, not a systematic review or a certified novelty statement. Sources and verification are recorded in [the source ledger](erc-context-sources-2026.json).

## Research question and comparison hypothesis

At a fixed token and inference budget, does task-aware selection of discussion context improve emotion recognition or sarcasm detection compared with target-only input, chronological windows, reply ancestors and semantic retrieval? A useful outcome would be a reproducible accuracy/cost/robustness trade-off, including cases where adding context hurts. “Minimally sufficient” must mean a declared tolerance relative to a comparator, not a mathematically proven minimum inferred from attention weights.

The comparison hypothesis is that reply structure and task cues can remove distractors without removing distant emotional or pragmatic evidence. This is an **agent-suggested hypothesis**, awaiting user review and experiments. No experiments below have been run.

## Verification and access limits

Exa connector discovery inspected 42 search-result slots across four topic clusters and three follow-up queries plus one InstructERC version query (duplicate pages included). Official ACL Anthology, AAAI, arXiv and ICLR pages were fetched on 2026-10-14. Generic browsing additionally checked missing venue/year metadata and arXiv version identity. Connector page access worked while direct scholarly API requests through the execution environment proxy were blocked (OpenAlex/Crossref tunnel HTTP 403). These sources verify this document, not the application's live OpenAlex adapter.

All entries have **abstract reviewed** granularity. Three entries additionally have selected full-text passages reviewed: InstructERC §2.2, RECOMP §6 via official-PDF indexed excerpts, and Jang et al. §4.2/§4.3/Limitations via PDF extraction. Bounded extraction is not a complete methodological review; no entry is marked “full text reviewed.” Result statements below are **paper-author claims**, not independently reproduced results. Exact strongest baselines and numerical metrics are not verified unless explicitly given. Missing author limitations mean “not verified,” not “none.” Bibliographic author lists and known DOI values are in the cards; missing DOI remains unknown rather than constructed from an Anthology ID.

Two journals are represented: *Computational Linguistics* and *TACL*. ACL/EMNLP/COLING/LREC-COLING, Findings, workshops, AAAI and ICLR are conference/proceedings publications; ACL Anthology is their host/index. InstructERC is a verified arXiv preprint record with peer-reviewed publication **unverified**. No Scopus/WoS status is asserted for any venue. Coverage of specialized affective-computing journals and complete 2025–2026 prior art remains pending; there is one verified March-2026 paper, not an invented fresh bibliography.

## Concise matrix

“A” = abstract reviewed; “A+” = abstract plus explicitly named full-text passages. Author limitations and hypotheses are separate columns.

| Paper (year, venue) | Task/data | Context used | Selection mechanism | Baselines/evidence | Limitations (author-stated) | My hypothesis / possible gap | Evidence quality |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [DialogueRNN](https://ojs.aaai.org/index.php/AAAI/article/view/4657) (2019, AAAI) | ERC; two datasets, names not in abstract | Individual speaker state | Recurrent state/attention | Author reports gain; exact comparator not verified | Not verified | Control speaker modeling before attributing gains to selection | A |
| [DialogueGCN](https://aclanthology.org/D19-1015/) (2019, EMNLP-IJCNLP) | ERC benchmarks | Self/inter-speaker dependency | Graph context propagation | Author reports benchmark gains | Not verified | Graph modeling already established; compare budget-matched neighborhoods | A |
| [COSMIC](https://aclanthology.org/2020.findings-emnlp.224/) (2020, Findings EMNLP) | ERC; four benchmarks | Commonsense mental states/events/causality | Commonsense representations and interaction modeling | Author reports gains | Not verified | Separate extra knowledge from better context selection | A |
| [DAG-ERC](https://aclanthology.org/2021.acl-long.123/) (2021, ACL-IJCNLP) | ERC; four benchmarks | Nearby and distant dialogue | Directed acyclic graph | Author reports gains over SOTA comparators | Not verified | Distant-context selection must outperform structured propagation | A |
| [Sarcasm Analysis Using Conversation Context](https://aclanthology.org/J18-4009/) (2018, Computational Linguistics) | Sarcasm; Twitter/forums | Prior/succeeding turn | Sentence attention; conditional LSTM | Context models beat target-only LSTM (abstract) | Not verified | “Context helps sarcasm” is established; prevent future-turn leakage | A |
| [DualGATs](https://aclanthology.org/2023.acl-long.408/) (2023, ACL) | ERC; four datasets | Discourse and speaker dependencies | Dual graph attention with interaction | Author reports majority-dataset gains | Not verified | Structure-aware ERC is direct prior art | A |
| [InstructERC](https://arxiv.org/abs/2309.11911v4) (2023 first submission; 2024 v4, arXiv) | ERC; three benchmarks | Historical window + training demonstration | Fixed history + semantic demonstration retrieval (§2.2) | Claimed benchmark gains; numeric table not reviewed | Not verified | Demonstration retrieval differs from selecting same-thread utterances | A+ |
| [LaERC-S](https://aclanthology.org/2025.coling-main.451/) (2025, COLING) | ERC; three benchmarks | Speaker mental state/behavior | Two-stage speaker-characteristic learning | Claimed gains | Not verified | Speaker information is a strong alternative explanation | A |
| [Who You Are, What You Say / PERC](https://aclanthology.org/2026.findings-eacl.172/) (2026, Findings EACL) | ERC; three benchmarks | Intra/inter-speaker context and personality | Segregation + contrastive alignment | Abstract reports weighted-F1 gains; tables not reviewed | Not verified | Context segregation is direct recent competition | A |
| [CoE](https://aclanthology.org/2025.acl-long.1148/) (2025, ACL) | ERC; EmoryNLP/MELD/IEMOCAP | Conversational clues | Progressive integration + auxiliary learning | Abstract reports gains | Not verified | A selector must disentangle clue enrichment and task supervision | A |
| [Beyond Linguistic Cues](https://aclanthology.org/2024.lrec-main.207/) (2024, LREC-COLING) | Fine-grained ERC; four datasets | Events, beliefs, desires, speaker state | Graph message passing | Claimed module/benchmark gains | Not verified | Pragmatic state modeling is established prior art | A |
| [When Do “More Contexts” Help?](https://aclanthology.org/2024.lrec-main.1525/) (2024, LREC-COLING) | Sarcasm; three benchmarks | Multiple contextual cues | Sequential cue addition | Four approaches; claimed benefit | Societal bias risk (abstract) | Extra contextual cue types are not necessarily extra reply turns | A |
| [Context vs. Human Disagreement](https://aclanthology.org/2024.figlang-1.1/) (2024, FigLang workshop) | Sarcasm; collected dialogue responses | None/short/long context | Controlled context conditions | Context generally helps; length benefit depends on disagreement | Information amount not quantified; small sample; male-only participants (Limitations) | Test sufficiency separately on ambiguous items | A+ |
| [Action and Reaction / MM-SARDAC](https://aclanthology.org/2024.lrec-main.28/) (2024, LREC-COLING) | Sarcasm; extended MUStARD | Dialogue acts + multimodal signals | Multitask transformer; modality attention | Claimed gain over sarcasm-only task | Not verified | Auxiliary labels/modality can confound context-selection gains | A |
| [RedSD](https://aclanthology.org/2025.findings-acl.607/) (2025, Findings ACL) | Fine-grained sarcasm; sitcom dialogues | Rhetorical devices/counterfactuals | Data augmentation, not verified turn selection | Fine-tuned vs zero-shot comparison (abstract) | Not verified | Label semantics/domain may dominate selection effects | A |
| [Lost in the Middle](https://aclanthology.org/2024.tacl-1.9/) (2024, TACL) | Multi-document QA/key-value retrieval | Long input; position manipulation | No selector; utility diagnostic | Position-sensitive performance (abstract) | Not verified | A robustness rationale, not evidence that ERC has the same failure | A |
| [LongLLMLingua](https://aclanthology.org/2024.acl-long.91/) (2024, ACL) | Long-context tasks; NaturalQuestions/LooGLE | Compressed prompt/key information | Prompt compression | Abstract claims performance/cost/latency gains | Not verified | Token compression and utterance selection require separate controls | A |
| [RECOMP](https://proceedings.iclr.cc/paper_files/paper/2024/hash/bda88ed2892f5e61c9a9bf215c566913-Abstract-Conference.html) (2024, ICLR) | LM/open-domain QA | Retrieved documents | Task-trained extractive/abstractive compression; empty augmentation | End-task vs length objective; no reproduction | QA compressor transfer weaker (§6) | Learned selective augmentation already exists outside ERC | A+ |
| [CoLoR](https://aclanthology.org/2025.acl-long.740/) (2025, ACL) | Long-context IR; nine datasets | Compressed passages | Preference training + length regularization | Abstract claims retrieval/size gains | Not verified | Task/budget-aware retrieval compression is established | A |
| [Never Lost in the Middle](https://aclanthology.org/2024.acl-long.736/) (2024, ACL) | Multi-document QA/retrieval | Long contexts | Position-agnostic multistep training | Abstract claims shuffled/retrieval gains | Not verified | Better backbone training may remove the selector's advantage | A |

## Evidence cards

Every card inherits provenance: public source linked in the heading; retrieved 2026-10-14; bibliographic metadata verified against that official page; summary authored by the Codex review agent (LLM-assisted, model identifier not exposed by the environment); not human-validated. Paper outcome claims are attributed to the **abstract** unless a section is named. All user verdicts are **unassigned**, reading status **abstract reviewed**, and rationale **awaiting researcher judgment**. These documentation IDs are not existing library paper IDs; map by canonical identity before importing. No local notes, private PDFs or application inference were used.

### R01 — DialogueRNN

Navonil Majumder, Soujanya Poria, Devamanyu Hazarika, Rada Mihalcea, Alexander Gelbukh, Erik Cambria. *DialogueRNN: An Attentive RNN for Emotion Detection in Conversations*. AAAI 2019 (conference proceedings). [Official record](https://ojs.aaai.org/index.php/AAAI/article/view/4657); DOI 10.1609/aaai.v33i01.33016818 (publisher-hosted citation).

Abstract: recurrent tracking of individual party states; two datasets. Attention is not proof of minimal context. Exact dataset names, strongest baseline, metrics and author limitations are not verified here. Candidate comparator: speaker-aware recurrence with matched input budget.

### R02 — DialogueGCN

Deepanway Ghosal, Navonil Majumder, Soujanya Poria, Niyati Chhaya, Alexander Gelbukh. *DialogueGCN: A Graph Convolutional Neural Network for Emotion Recognition in Conversation*. EMNLP-IJCNLP 2019, pp. 154–164 (conference proceedings). [Record](https://aclanthology.org/D19-1015/); DOI 10.18653/v1/D19-1015.

Abstract: self/inter-speaker dependencies address context propagation. Exact window construction, strongest baseline and metric values need full-text verification. Author limitations not verified. This disconfirms novelty based only on graph-based conversational context.

### R03 — COSMIC

Deepanway Ghosal, Navonil Majumder, Alexander Gelbukh, Rada Mihalcea, Soujanya Poria. *COSMIC: COmmonSense knowledge for eMotion Identification in Conversations*. Findings EMNLP 2020, pp. 2470–2481 (proceedings). [Record](https://aclanthology.org/2020.findings-emnlp.224/); DOI 10.18653/v1/2020.findings-emnlp.224.

Abstract: mental states, events and causal relations support interlocutor interaction modeling on four benchmarks. Exact datasets/strongest baseline/metrics not verified. Author limitations not verified. Hypothesis: selector gains may instead come from extra commonsense information.

### R04 — DAG-ERC

Weizhou Shen, Siyue Wu, Yunyi Yang, Xiaojun Quan. *Directed Acyclic Graph Network for Conversational Emotion Recognition*. ACL-IJCNLP **2021**, pp. 1551–1560 (conference proceedings). [Record](https://aclanthology.org/2021.acl-long.123/); DOI 10.18653/v1/2021.acl-long.123.

The attached lead's 2022 date/title is corrected against the official record. Abstract: DAG encodes nearby and long-distance background; four ERC benchmarks. Exact graph edges and metrics not reviewed. Author limitations not verified. Structured propagation is an obligatory comparator.

### R05 — Sarcasm Analysis Using Conversation Context

Debanjan Ghosh, Alexander R. Fabbri, Smaranda Muresan. *Sarcasm Analysis Using Conversation Context*. **Computational Linguistics** 44(4), 2018, pp. 755–792 (journal). [Record](https://aclanthology.org/J18-4009/); DOI 10.1162/coli_a_00336.

Abstract: Twitter and discussion forums; prior/succeeding turns or both; sentence-attentive and conditional LSTMs outperform current-turn-only LSTM. Attention interpretation is qualitative, not a causal sufficiency proof. Author limitations not verified. Hypothesis: succeeding turns are unavailable in an online causal setting; separate offline and online protocols.

### R06 — DualGATs

Duzhen Zhang, Feilong Chen, Xiuyi Chen. *DualGATs: Dual Graph Attention Networks for Emotion Recognition in Conversations*. ACL 2023, pp. 7395–7408 (conference proceedings). [Record](https://aclanthology.org/2023.acl-long.408/); DOI 10.18653/v1/2023.acl-long.408.

Abstract: discourse-aware and speaker-aware graph attention exchange information; four datasets. Exact strongest baseline/metric and author limitations not verified. Candidate difference must concern explicit budgeted selection or a different tested discussion structure; discourse awareness itself is already prior art.

### R07 — InstructERC (version-controlled preprint)

Shanglin Lei, Guanting Dong, Xiaoping Wang, Keheng Wang, Sirui Wang. *InstructERC: Reforming Emotion Recognition in Conversation with a Retrieval Multi-task LLMs Framework* (arXiv landing title for v4). [Record](https://arxiv.org/abs/2309.11911v4); DOI 10.48550/arXiv.2309.11911. First submitted 2023-09-21; v4 revised 2024-03-12. Venue type: repository/preprint; peer-reviewed publication unverified.

[Versioned HTML](https://arxiv.org/html/2309.11911v4) uses a different subtitle (“Multi-task Retrieval-based LLMs Framework”); latest unversioned record changes it again. Do not create multiple papers for these titles. §2.2/Figure 2 specifies a historical window and speaker information, with SBERT retrieval of one training-set demonstration. This is **demonstration retrieval**, not arbitrary retrieval of distant same-thread utterances. Three benchmark gains are author claims. Strongest baseline/metrics/limitations not verified. Only these passages were reviewed.

### R08 — LaERC-S

Yumeng Fu, Junjie Wu, Zhongjie Wang, Meishan Zhang, Lili Shan, Yulin Wu, Bingquan Liu. *LaERC-S: Improving LLM-based Emotion Recognition in Conversation with Speaker Characteristics*. COLING 2025, pp. 6748–6761 (conference proceedings). [Record](https://aclanthology.org/2025.coling-main.451/); DOI not supplied by reviewed record.

Abstract: two-stage learning reasons about interlocutor mental states/behavior and emotion tracking; three benchmarks. Exact dataset names/metrics/author limitations not verified. Hypothesis: compare equivalent speaker cues before crediting gains to context pruning.

### R09 — PERC

Tazeek Bin Abdur Rakib, Lay-Ki Soon, Wern Han Lim. *Who You Are, What You Say: Intra- and Inter- Context Personality for Emotion Recognition in Conversation*. Findings EACL **March 2026**, pp. 3293–3308 (proceedings). [Record](https://aclanthology.org/2026.findings-eacl.172/); DOI 10.18653/v1/2026.findings-eacl.172.

Abstract: intra/inter-speaker segregation, static/dynamic personality, contrastive alignment; three ERC benchmarks. Weighted-F1 gains are asserted against non-LLM/recent LLM methods; exact comparison tables not reviewed and numbers deliberately not transplanted into cross-paper ranking. Author limitations not verified. This directly challenges a broad claim of new context segregation.

### R10 — CoE

Zhiyu Shen, Yunhe Pang, Yanghui Rao, Jianxing Yu. *CoE: A Clue of Emotion Framework for Emotion Recognition in Conversations*. ACL 2025, pp. 23548–23563 (conference proceedings). [Record](https://aclanthology.org/2025.acl-long.1148/); DOI 10.18653/v1/2025.acl-long.1148.

Abstract: progressively integrated clues plus role-playing, speaker identification and emotion reasoning; EmoryNLP, MELD, IEMOCAP. Metric/comparator for the abstract's improvement is not resolved here; no numerical comparison is made. Author limitations not verified. Hypothesis: auxiliary training and context selection need factorial controls.

### R11 — Beyond Linguistic Cues

Bo Xu, Longjiao Li, Wei Luo, Mehdi Naseriparsa, Zhehuan Zhao, Hongfei Lin, Feng Xia. *Beyond Linguistic Cues: Fine-grained Conversational Emotion Recognition via Belief-Desire Modelling*. LREC-COLING 2024, pp. 2318–2328 (conference proceedings). [Record](https://aclanthology.org/2024.lrec-main.207/); DOI not supplied by reviewed record.

Abstract: emotion-eliciting events and belief/desire graphs model context, speaker state and their interaction; four datasets. Exact metrics and strongest baselines not verified. Author limitations not verified. Hypothesis: pragmatic knowledge could explain gains without adaptive context selection.

### R12 — When Do “More Contexts” Help with Sarcasm Recognition?

Ojas Nimase, Sanghyun Hong. *When Do “More Contexts” Help with Sarcasm Recognition?* LREC-COLING 2024, pp. 17537–17543 (conference proceedings). [Record](https://aclanthology.org/2024.lrec-main.1525/); DOI not supplied by reviewed record.

Abstract: framework combines contextual cues; four approaches on three benchmarks. Authors identify a risk that improved results require societal biases. “More contexts” here concerns richer cue types, so it should not silently become “more ancestor turns.” Exact datasets/metrics not reviewed. Hypothesis: report contextual-source bias and budget, not only aggregate accuracy.

### R13 — Context vs. Human Disagreement in Sarcasm Detection

Hyewon Jang, Moritz Jakob, Diego Frassinelli. *Context vs. Human Disagreement in Sarcasm Detection*. FigLang 2024 workshop, pp. 1–7 (workshop proceedings). [Record](https://aclanthology.org/2024.figlang-1.1/); DOI 10.18653/v1/2024.figlang-1.1. [Reviewed PDF version 2](https://aclanthology.org/2024.figlang-1.1v2.pdf).

§4.2/Table 3 and §4.3/Tables 4–5 discuss context amounts and agreement strata, including BERT; numeric cells not transcribed. Context presence generally helps; more context is not consistently better. **Author Limitations:** information amount not systematically quantified, small filtered sample, male-only participants. These are explicitly acknowledged, not inferred. Candidate gap: test a gradient of context budgets, disagreement-sensitive utility and broader sampling. Partial full text reviewed; not a complete review.

### R14 — MM-SARDAC

Mohit Tomar, Tulika Saha, Abhisek Tiwari, Sriparna Saha. *Action and Reaction Go Hand in Hand! a Multi-modal Dialogue Act Aided Sarcasm Identification*. LREC-COLING 2024, pp. 298–309 (conference proceedings). [Record](https://aclanthology.org/2024.lrec-main.28/); DOI not supplied by reviewed record.

Abstract: MUStARD extended with dialogue acts; joint dialogue-act/sarcasm transformer and ordered modality infusion. Authors report better performance than sarcasm-only identification. Exact metric and author limitations not verified. Hypothesis: a text-only selector cannot claim comparable gains without modality/label controls.

### R15 — RedSD

Qingqing Hong, Dongyu Zhang, Jiayi Lin, Dapeng Yin, Shuyue Zhu, Junli Wang. *Rhetorical Device-Aware Sarcasm Detection with Counterfactual Data Augmentation*. Findings ACL 2025, pp. 11672–11685 (proceedings). [Record](https://aclanthology.org/2025.findings-acl.607/); DOI 10.18653/v1/2025.findings-acl.607.

Abstract: sitcom dialogues, nine rhetorical devices, LLM-assisted counterfactual generation with human revision; fine-tuned models compared with GPT-3.5/LLaMA 3.1 zero-shot models. Exact metric and author limitations not verified. Candidate relevance: rhetorical strata and label semantics, not evidence for a new turn selector.

### R16 — Lost in the Middle

Nelson F. Liu, Kevin Lin, John Hewitt, Ashwin Paranjape, Michele Bevilacqua, Fabio Petroni, Percy Liang. *Lost in the Middle: How Language Models Use Long Contexts*. **TACL** 12, 2024, pp. 157–173 (journal). [Record](https://aclanthology.org/2024.tacl-1.9/); DOI 10.1162/tacl_a_00638.

Abstract: multi-document QA and key-value retrieval show sensitivity to relevant-information position. Exact models/metrics and author limitations not reviewed. This supports a position-perturbation protocol, not an ERC finding. Hypothesis: retain the same distractors while moving the relevant ancestor to distinguish retrieval benefit from position bias.

### R17 — LongLLMLingua

Huiqiang Jiang, Qianhui Wu, Xufang Luo, Dongsheng Li, Chin-Yew Lin, Yuqing Yang, Lili Qiu. *LongLLMLingua: Accelerating and Enhancing LLMs in Long Context Scenarios via Prompt Compression*. ACL 2024, pp. 1658–1677 (conference proceedings). [Record](https://aclanthology.org/2024.acl-long.91/); DOI 10.18653/v1/2024.acl-long.91.

Abstract: prompt compression tackles cost, performance and position bias; NaturalQuestions and LooGLE named. Claims of reduced tokens/cost/latency are setting-specific; not transferable ERC outcomes. Exact matched-budget comparators and author limitations not verified. Hypothesis: compare whole-utterance selection with token compression under equal total cost.

### R18 — RECOMP

Fangyuan Xu, Weijia Shi, Eunsol Choi. *RECOMP: Improving Retrieval-Augmented LMs with Context Compression and Selective Augmentation*. ICLR 2024 (conference proceedings). [Official abstract](https://proceedings.iclr.cc/paper_files/paper/2024/hash/bda88ed2892f5e61c9a9bf215c566913-Abstract-Conference.html); DOI unknown. [Official PDF](https://proceedings.iclr.cc/paper_files/paper/2024/file/bda88ed2892f5e61c9a9bf215c566913-Paper-Conference.pdf).

Abstract: task-trained extractive/abstractive compressors trade performance against length and may return empty augmentation. §6 indexed PDF excerpts state QA transfer to a different LM can be weaker and leave a gap to oracle compression. Numerical results and full comparator tables not reviewed. This is direct counterevidence to a general claim of first task-aware minimal context. Candidate difference must be tested in same-thread ERC/sarcasm, with structure, causality and budget controls.

### R19 — CoLoR

Minju Seo, Jinheon Baek, Seongyun Lee, Sung Ju Hwang. *Efficient Long Context Language Model Retrieval with Compression*. ACL 2025, pp. 15251–15268 (conference proceedings). [Record](https://aclanthology.org/2025.acl-long.740/); DOI 10.18653/v1/2025.acl-long.740.

Abstract: synthetic chosen/rejected compressions train preference optimization with length regularization; nine IR datasets. Authors claim retrieval and context-size improvements; exact metric/comparators not reviewed. Author limitations not verified. Hypothesis: applying a selector to ERC alone may be a transfer of an existing optimization idea rather than a new method.

### R20 — Never Lost in the Middle

Junqing He, Kunhao Pan, Xiaoqun Dong, Zhuoyang Song, Yibo Liu, Qianguo Sun, Yuxin Liang, Hao Wang, Enming Zhang, Jiaxing Zhang. *Never Lost in the Middle: Mastering Long-Context Question Answering with Position-Agnostic Decompositional Training*. ACL 2024, pp. 13628–13642 (conference proceedings). [Record](https://aclanthology.org/2024.acl-long.736/); DOI 10.18653/v1/2024.acl-long.736.

Abstract: position-agnostic multistep QA training improves information search in long context. Exact backbone, strongest baseline and numerical tables not reviewed. Author limitations not verified. Hypothesis: selection gains may vanish when the classifier is trained to handle distractors; vary backbone training as an explicit control.

## Disconfirming evidence and candidate gaps

Existing evidence already challenges broad novelty: R05 models conversation context for sarcasm; R06 and R09 model discourse/speaker context; R07 retrieves demonstrations; R18 and R19 optimize task utility against context length; R13 studies when extra context ceases to help. None establishes that the narrower proposed combination is absent elsewhere. Attention weights do not demonstrate causal relevance, and a shorter successful context on one sample does not prove minimal sufficiency.

| Candidate claim (unverified) | Known prior art / strongest challenge | Potential difference to test | Alternative explanation and falsifier | Verification needed |
| --- | --- | --- | --- | --- |
| Structure-constrained, task-aware same-thread selection improves the accuracy/cost frontier | R06 DualGATs; R07 InstructERC; R18 RECOMP | Explicit ancestor/speaker constraints and total selection overhead | Equal-budget chronological/ancestor/semantic baselines tie or win | Full-text nearest-neighbor search for adaptive ERC/thread selectors; threaded data fit |
| Per-instance sufficiency stopping preserves ambiguous pragmatic evidence | R13 disagreement/context amounts; R18 empty augmentation; R19 length regularization | Declared utility tolerance and abstention/stopping calibration | Benefit is only shorter input or classifier confidence miscalibration | Review learned stopping/rationales; preregister noninferiority margin |
| Context-selection robustness differs by emotion, sarcasm and annotator disagreement | R12 cue bias; R13 disagreement; R16 position utility | Matched position/distractor stress tests and disagreement strata | Dataset leakage, cue bias or an improved backbone explains differences | Validate labels, causal availability, splits, domain shift and R20 controls |

No final «вперше», «удосконалено», or «набуло подальшого розвитку» classification is assigned. A dissertation contribution would require a confirmed difference, suitable comparison, reproducible experiment and disciplinary review.

## Two low-cost experiments (proposed, not executed)

1. **Budget-matched context frontier.** Use one licensed public ERC dataset (e.g., MELD textual tracks) and one accessible public threaded sarcasm set after checking license and reconstruction availability. Split by conversation/thread; keep all fitting/retrieval inside the training split. Freeze one inexpensive classifier and tokenization. Compare target-only, previous k turns, reply ancestors, same-speaker history, lexical BM25 retrieval and structure-constrained retrieval at 64/128/256 context-token budgets. Include random and length-matched selection. Report task-appropriate macro/weighted F1 separately, paired thread-level confidence intervals, tokens, selector time, inference time and peak memory. “Sufficient” provisionally means no more than a preregistered 1-point F1 loss versus the largest allowed context, not proof of a minimum. Start with a small pilot and report uncertainty; do not mix ERC and sarcasm scores into one ranking.

2. **Distractor, position and leakage ablation.** Reuse those splits, budgets and classifier. Add same-topic unrelated comments, shuffle only admissible context order, move one relevant ancestor across input positions, and remove speaker/reply edges one at a time. Separate causal prefix-only evaluation from offline full-thread evaluation; never allow later replies into the causal condition. Measure performance loss, extra cost, prediction stability and disagreement-stratum effects where independent annotations exist. If no disagreement labels are available, report the missing measurement instead of inferring them. A selector that merely deletes inconvenient examples or relies on future information fails this experiment.

## Title advice and remaining review work

A narrower working title is warranted while task/domain evidence is incomplete. Possible Ukrainian title: **«Методи бюджетованого відбору контексту для розпізнавання емоцій у структурованих онлайн-дискусіях»**. If ERC datasets remain mostly scripted chronological dialogue, use **«… у багатосторонніх діалогах»** until threaded-discussion transfer is demonstrated. Retain sarcasm as a separate validation task only if appropriate intended/perceived labels and context are available; it should not silently stand for all pragmatic characteristics.

Before claiming novelty: read complete R06/R07/R09/R13/R18/R19 texts and strongest baselines, expand specialized journals (especially IEEE Transactions on Affective Computing and Language Resources and Evaluation), verify intended-sarcasm datasets and available reply trees, and search budgeted rationales/learned stopping. Discovery leads SARC, iSarcasm and iSarcasmEval need a separate dataset/license review; no SARC methods or dataset figures were verified here. Paywalled texts and indexation checks were not bypassed. A failed OpenReview fetch during RECOMP discovery was replaced by the accessible official ICLR record/PDF; anonymous InstructERC submission pages were not used to certify acceptance.

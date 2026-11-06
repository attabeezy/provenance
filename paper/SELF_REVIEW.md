# Self-Review — "Authorship Needs Provenance, Not Prediction"

Adversarial pass per the research-paper-writing skill. Claim-evidence map first,
then the five rejection dimensions. Status: `pass` / `revise` / `experiment`.

## Claim-Evidence Map

| # | Claim (location) | Evidence | Status |
|---|---|---|---|
| C1 | Lexical tells spike then purge; structure persists (Abstract, §3.1) | E1: delve 0–3→13.3→0 /100K (upper bound 4.1 for 2026); core slop 91→253→138; triads 0.65→1.97 persisting; HN +73% | pass — all numbers verified against `e1_timeseries.json`, `e1_summary.json` |
| C2 | No folk marker separates AI from all human registers (Abstract, §3.2) | E2: all four markers overlap across 8 corpora; em-dash inverted (0.03 AI vs 1.06 human /1K in HC3 pair); triad is the only consistent AI marker | pass — `e2_overlap.json` |
| C3 | In-domain success, cross-register collapse (Abstract, §3.3) | E3: 0.98+ in-domain AUC vs 0.56–0.81 cross-pair; both model families × both training pairs | pass — `e3_detector.json` |
| C4 | Error concentrates by register and author (Abstract, §3.4) | E3: FPR@95%TPR range 0–73% by test corpus; 13–99% by author (n=23); Borges/Lawrence outlier case | pass |
| C5 | Claimed-accuracy arithmetic yields false accusations at scale (Abstract, §3.5) | E4: 100/day at 1e-4 FPR, 20% human, 5M docs/day (250 working days → 25,000/yr stated); posterior inversion 99.96% vs 44/30%; LR ≤ 7.3 | pass — `e4_math.json`; working-day basis now stated in text |
| C6 | Causal claim: detector-driven adaptation (§3.2) | Correlation + Yakura mechanism; NOT direct causation | revise — **fixed**: "_consistent with_ detector pressure — the one mechanism directly documented [2]"; "that its own deployment **may** be moving" |
| C7 | "Human" ground truth in corpora (§3.3, Table 1) | Wiki snapshot 2022 (labeled); Gutenberg pre-model; HC3 human answers pre-ChatGPT Q&A | pass — labeled in Table 1; measurement crisis itself argued in §7 item 3 |
| C8 | AI corpora are 2023-era (Abstract) | wiki-davinci-003 + ChatGPT-era HC3 | pass — explicitly "2023-era" in abstract; scope limit stated |
| C9 | Meta-audit footnote | `meta_audit.py`: 22 windows, W flags 50%, H flags 0%; 12.4 em-dash/1K | pass — newly measured this session |

## Five Rejection Dimensions (position-paper adaptation)

### 1. Contribution — pass
- New insight: the evidentiary-adequacy framing (posterior/LR *per accused writer*, not aggregate accuracy) — not present in Weber-Wulff or Liang, which stop at aggregate bias. E4 posterior table is the sharpest existing device for it.
- New quantification: reflexivity measured in *written* prose + structure (triads persist); transfer collapse across AI generations (davinci-003 → ChatGPT) framed as "each detector is an artifact of one snapshot."
- Non-obvious: "no marker separates AI from all human registers" is supported by an inverted marker (em-dash), not just failure-to-separate.

### 2. Writing clarity — pass (after fixes)
- All terms defined at first use (provenance-text gap, detectability fallacy, folk model, register).
- Reproducibility: scripts collect, extract features, fit, and score; feature definitions in §3.1 are complete enough to reimplement. Numbers in text verified against analysis JSONs this session.
- One-paragraph message discipline checked; reverse outline matches § order (gap → evidence → proposal → positioning → principles → CTA).

### 3. Empirical strength — pass, with honest scope
- Not a "beat SOTA" paper; the empirical benchmark is: do the folklore's own instruments behave as the folklore predicts? They do not.
- Weakness flagged honestly: three AI generation points only (davinci-003, ChatGPT-era, plus the 2026 prose drift). Does not measure Pangram itself — deliberately: uses vendor-claimed 1e-4 FPR for arithmetic so no vendetta-metrics.

### 4. Evaluation completeness — pass
- Four independent experiments (time series, marker overlap, three classifier families, Bayesian arithmetic) triangulate one thesis rather than one experiment with ablations.
- Baseline completeness: the "baseline" for a position paper is the prior field consensus — represented by Weber-Wulff [4], Liang [3], Sadasivan [5], Kirchenbauer [6], plus (added Nov 2026 revision) Gehrmann GLTR [11], RoFT [12], DetectGPT [13], Ghostbuster [14], Crothers survey [15], Biber register variation [16], DIPPER paraphrase attacks [17], OUTFOX adversarial detection [18], Crompton & Burke education review [19], Longpre consent audit [20] — 20 references, all metadata verified against ACL Anthology / PMLR / NeurIPS proceedings / journals in this session.

### 5. Method soundness — pass
- Known limitation, stated: folk models are weak instruments, but they are the *deployed* instruments of the accusation ecosystem, and the strong-model result (tfidf/char collapse) covers the "you used a strawman" rejoinder.
- Thresholds use FPR@95%TPR (fixed-sensitivity), the vendor-relevant operating point — not arbitrary.

## Actions taken this session
1. Fixed delve pre-2024 count (9→4) and "0–2" range (→0–3) against `e1_summary.json`.
2. Stated the 250-working-day basis for "25,000/year."
3. Rephrased posterior sentence ("more likely than not" bar) for precision.
4. Table 1 wiki-human row labeled "2022 snapshot."
5. Weakened §3.2 causal claim (C6).
6. Meta-audit footnote: real numbers replacing placeholder.

## Remaining risks accepted deliberately
- R1: 2023-era AI corpora — accepted; thesis is about *structure of the regime*, and E4 uses vendor claims precisely to sidestep "your detector is old."
- R2: HN 2026 +73% could partly reflect more AI-related discussion in comments. Mitigated by weakened causal language; the opposite-movement design (purge + hybridize) is the claim's spine.
- R3: Cannot render-check the four PNG figures in this environment — user eyeballs `figures\` before submission.

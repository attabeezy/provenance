"""Central path configuration for the provenance codebase.

All locations are derived from the repository root, which is found
relative to this file (src/provenance/paths.py -> parents[2]) and can be
overridden with the PROVENANCE_ROOT environment variable.
"""
import os
from pathlib import Path

ROOT = Path(os.environ.get("PROVENANCE_ROOT", Path(__file__).resolve().parents[2]))

DATA = ROOT / "data"
DATA_RAW = DATA / "raw"
ANALYSIS = ROOT / "analysis"
FIGURES = ROOT / "figures"
PAPER = ROOT / "paper"

# frozen raw corpora (downloaded / collected)
HN_COMMENTS = DATA_RAW / "hn_comments.jsonl"
ARXIV_ABSTRACTS = DATA_RAW / "arxiv_abstracts.jsonl"
GUTENBERG_SEGMENTS = DATA_RAW / "gutenberg_segments.jsonl"
WIKI_PAIRS = DATA_RAW / "wiki_pairs.jsonl"
HC3_PAIRS = DATA_RAW / "hc3_pairs.jsonl"
HC3_ALL = DATA_RAW / "hc3_all.jsonl"
GPT_WIKI_INTRO_ZIP = DATA_RAW / "gpt_wiki_intro.zip"
GPT2_ARX = DATA_RAW / "xl-1542M.test.jsonl"
WEBTEXT_ARX = DATA_RAW / "webtext.test.jsonl"
GPT2_AI = DATA_RAW / "gpt2_ai.jsonl"
WEBTEXT_HUMAN = DATA_RAW / "webtext_human.jsonl"

# derived feature caches
def feat_path(name: str) -> Path:
    return ANALYSIS / f"feat_{name}.jsonl"

# analysis results
E1_TIMESERIES = ANALYSIS / "e1_timeseries.json"
E1_SUMMARY = ANALYSIS / "e1_summary.json"
E2_OVERLAP = ANALYSIS / "e2_overlap.json"
E3_DETECTOR = ANALYSIS / "e3_detector.json"
E4_MATH = ANALYSIS / "e4_math.json"
META_AUDIT = ANALYSIS / "meta_audit.json"
E5_VINTAGE = ANALYSIS / "e5_vintage.json"

# paper artifacts
DRAFT = PAPER / "draft.md"
PAPER_TEX = PAPER / "paper.tex"

def figure_path(name: str) -> Path:
    return FIGURES / name

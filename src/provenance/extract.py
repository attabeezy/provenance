"""Derived-corpus builders: matched pairs and feature caches.

Subcommands:
  wiki    matched human/AI Wikipedia-intro pairs from GPT-wiki-intro zip
  hc3     matched human/ChatGPT Q&A pairs from HC3 (+ their feat caches)
  feats   feature caches for gutenberg / wiki / hn_pre / arxiv_{pre,post}
  gpt2    feature caches for the vintage-2019 corpus pair (E5)
"""
import csv
import io
import json
import random
import zipfile

from . import corpora, paths
from .features import full as feat_full

random.seed(13)  # reproduces build_feat_cache.py's hn_pre shuffling


# ---------------------------------------------------------------------------
# wiki pairs
# ---------------------------------------------------------------------------
def wiki_pairs():
    """Extract matched human/AI intro pairs from GPT-wiki-intro csv zip.

    Keep pairs where both sides >= 60 words. Sample up to 6000 pairs.
    Output: data/raw/wiki_pairs.jsonl  {title, human, ai}
    """
    MIN_WORDS = 60
    MAX_PAIRS = 6000
    z = zipfile.ZipFile(paths.GPT_WIKI_INTRO_ZIP)
    name = z.namelist()[0]
    kept = 0
    seen_titles = set()
    with z.open(name) as f, open(paths.WIKI_PAIRS, "w", encoding="utf-8") as out:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"))
        total = 0
        for row in reader:
            total += 1
            if kept >= MAX_PAIRS:
                break
            human = (row.get("wiki_intro") or "").strip()
            ai = (row.get("generated_intro") or "").strip()
            title = (row.get("title") or "").strip()
            if len(human.split()) < MIN_WORDS or len(ai.split()) < MIN_WORDS:
                continue
            if title in seen_titles:
                continue
            seen_titles.add(title)
            out.write(json.dumps({
                "title": title, "human": human, "ai": ai,
            }) + "\n")
            kept += 1
    print(f"rows scanned: {total}, pairs kept: {kept}")


# ---------------------------------------------------------------------------
# hc3 pairs (+ feature caches, as in the original pipeline)
# ---------------------------------------------------------------------------
def hc3_pairs():
    """Extract HC3 chat-register matched pairs + build their feature caches.

    Output: data/raw/hc3_pairs.jsonl {source, qid, human, ai}
            analysis/feat_hc3_human.jsonl / feat_hc3_ai.jsonl
    Cap: 800 pairs per source domain, min 60 words per answer.
    """
    MIN_WORDS = 60
    CAP_PER_SOURCE = 800

    def clean(t):
        return " ".join(t.replace("\\n", " ").split())

    per_source = {}
    pairs = []
    with open(paths.HC3_ALL, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            src = d.get("source", "?")
            if per_source.get(src, 0) >= CAP_PER_SOURCE:
                continue
            human = next((a for a in d.get("human_answers", [])
                          if len(a.split()) >= MIN_WORDS), None)
            ai = next((a for a in d.get("chatgpt_answers", [])
                       if len(a.split()) >= MIN_WORDS), None)
            if not human or not ai:
                continue
            pairs.append({
                "source": src, "qid": d.get("index"),
                "human": clean(human), "ai": clean(ai),
            })
            per_source[src] = per_source.get(src, 0) + 1
    corpora.write_jsonl(paths.HC3_PAIRS, pairs)
    print("pairs:", len(pairs), "per source:", per_source)

    for side in ["human", "ai"]:
        with open(paths.feat_path(f"hc3_{side}"), "w", encoding="utf-8") as f:
            for p in pairs:
                r = feat_full(p[side])
                r["meta"] = p["source"]
                f.write(json.dumps(r) + "\n")
        print(f"wrote feat_hc3_{side}.jsonl ({len(pairs)})")


# ---------------------------------------------------------------------------
# feature cache builder (for the remaining corpora)
# ---------------------------------------------------------------------------
def _emit(name, docs):
    with open(paths.feat_path(name), "w", encoding="utf-8") as f:
        for meta, text in docs:
            r = feat_full(text)
            r["meta"] = meta
            f.write(json.dumps(r) + "\n")
    print(f"{name}: {len(docs)} docs -> {paths.feat_path(name)}")


def feat_cache():
    """Cache per-document features for all comparison corpora.

    Outputs analysis/feat_{name}.jsonl with fields:
      meta (author/title/year as available), n_words, and all rates.
    """
    # Gutenberg (pre-LLM human, 600-word segments)
    rows = corpora.read_jsonl(paths.GUTENBERG_SEGMENTS)
    _emit("gutenberg", [(f"{r['author']}|{r['title']}", r["text"]) for r in rows])

    # Wiki pairs (matched domain)
    rows = corpora.read_jsonl(paths.WIKI_PAIRS)
    _emit("wiki_human", [(r["title"], r["human"]) for r in rows])
    _emit("wiki_ai", [(r["title"], r["ai"]) for r in rows])

    # HN pre-LLM sample (2015-2019), cap 6000
    rows = corpora.read_jsonl(paths.HN_COMMENTS)
    pre = [r for r in rows if 2015 <= r["year"] <= 2019]
    random.shuffle(pre)
    _emit("hn_pre", [(f"{r['year']}-{r['author']}", r["text"]) for r in pre[:6000]])

    # arXiv pre-LLM (2010-2019)
    rows = corpora.read_jsonl(paths.ARXIV_ABSTRACTS)
    pre = [r for r in rows if 2010 <= r["year"] <= 2019]
    _emit("arxiv_pre", [(f"{r['year']}", r["text"]) for r in pre])

    # arXiv post-LLM (2023-2026)
    post = [r for r in corpora.read_jsonl(paths.ARXIV_ABSTRACTS)
            if 2023 <= r["year"] <= 2026]
    _emit("arxiv_post", [(f"{r['year']}", r["text"]) for r in post])


# ---------------------------------------------------------------------------
# vintage-2019 corpus pair (E5)
# ---------------------------------------------------------------------------
def gpt2_caches():
    """Feature caches for the vintage corpora from the GPT-2 archive.

    Outputs analysis/feat_gpt2_ai.jsonl and analysis/feat_webtext_human.jsonl,
    one feature row per filtered archive doc, meta = '<name>-<index>'.
    """
    _emit("gpt2_ai", [(f"gpt2-{i}", r["text"])
                      for i, r in enumerate(corpora.read_jsonl(paths.GPT2_AI))])
    _emit("webtext_human", [(f"web-{i}", r["text"])
                            for i, r in enumerate(
                                corpora.read_jsonl(paths.WEBTEXT_HUMAN))])

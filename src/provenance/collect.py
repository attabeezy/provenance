"""Collectors for the three primary raw corpora (networked, resumable).

Subcommands:
  hn        Hacker News comments via Algolia API (2015-2026)
  arxiv     arXiv cs.CL abstracts via export API (2010-2026, CLI year filter)
  gutenberg Project Gutenberg classic literature segments
"""
import calendar
import csv
import html
import io
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

from . import paths

HFA_UA = "stylometry-research/0.1"


# ---------------------------------------------------------------------------
# Hacker News (Algolia API)
# ---------------------------------------------------------------------------
HN_API = "https://hn.algolia.com/api/v1/search_by_date"
HN_TAG_RE = re.compile(r"<[^>]+>")
HN_MIN_WORDS = 30


def hn_fetch(ts0, ts1, page=0):
    url = (
        f"{HN_API}?tags=comment&hitsPerPage=250&page={page}"
        f"&numericFilters=created_at_i>={ts0},created_at_i<{ts1}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": HFA_UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def hn_clean(text):
    text = HN_TAG_RE.sub(" ", html.unescape(text or ""))
    return re.sub(r"\s+", " ", text).strip()


def hn_month_windows(year, month):
    """Three ~10-day windows inside the month: (ts0, ts1) pairs."""
    days = calendar.monthrange(year, month)[1]
    bounds = [1, 11, 21, days + 1]
    wins = []
    for b0, b1 in zip(bounds, bounds[1:]):
        ts0 = calendar.timegm((year, month, b0, 0, 0, 0))
        y2, m2 = (year + 1, 1) if month == 12 else (year, month + 1)
        ts1 = calendar.timegm((y2, m2, b1, 0, 0, 0))
        wins.append((ts0, ts1))
    return wins


def collect_hn():
    n_total = 0
    with open(paths.HN_COMMENTS, "w", encoding="utf-8") as out:
        for year in range(2015, 2027):
            for month in range(1, 13):
                got = 0
                for ts0, ts1 in hn_month_windows(year, month):
                    try:
                        res = hn_fetch(ts0, ts1)
                    except Exception as e:
                        print(f"ERR {year}-{month:02d}: {e}", file=sys.stderr)
                        time.sleep(5)
                        continue
                    hits = res.get("hits", [])
                    for h in hits:
                        text = hn_clean(h.get("comment_text") or "")
                        if len(text.split()) >= HN_MIN_WORDS:
                            out.write(json.dumps({
                                "year": year, "month": month,
                                "author": h.get("author"),
                                "text": text,
                            }) + "\n")
                            got += 1
                    time.sleep(1.2)
                n_total += got
                print(f"{year}-{month:02d}: {got} comments", flush=True)
    print(f"TOTAL: {n_total}")


# ---------------------------------------------------------------------------
# arXiv cs.CL abstracts (export API)
# ---------------------------------------------------------------------------
ARXIV_API = "http://export.arxiv.org/api/query"
ARXIV_NS = {"a": "http://www.w3.org/2005/Atom"}

ARXIV_QUARTERS = [
    ("01010000", "04010000"), ("04010000", "07010000"),
    ("07010000", "10010000"), ("10010000", "01010000"),
]


def arxiv_fetch(date0, date1, start=0):
    q = f"cat:cs.CL AND submittedDate:[{date0} TO {date1}]"
    url = (
        f"{ARXIV_API}?search_query={urllib.request.quote(q)}"
        f"&sortBy=submittedDate&sortOrder=ascending"
        f"&start={start}&max_results=100"
    )
    req = urllib.request.Request(url, headers={"User-Agent": HFA_UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def collect_arxiv(years=None):
    years = years or list(range(2010, 2027))
    n_total = 0
    with open(paths.ARXIV_ABSTRACTS, "a", encoding="utf-8") as out:
        for year in years:
            got = 0
            for i, (d0, d1) in enumerate(ARXIV_QUARTERS):
                if d1 == "01010000":
                    q_end = f"{year + 1}{d1}"
                else:
                    q_end = f"{year}{d1}"
                for attempt in range(4):
                    try:
                        xml = arxiv_fetch(f"{year}{d0}", q_end)
                        break
                    except Exception as e:
                        print(f"ERR {year} Q{i+1} try{attempt}: {e}", file=sys.stderr)
                        time.sleep(20 * (attempt + 1))
                else:
                    continue
                root = ET.fromstring(xml)
                entries = root.findall("a:entry", ARXIV_NS)
                for e in entries:
                    aid = e.findtext("a:id", namespaces=ARXIV_NS)
                    text = re.sub(
                        r"\s+", " ",
                        (e.findtext("a:summary", namespaces=ARXIV_NS) or "").strip(),
                    )
                    if len(text.split()) >= 20:
                        out.write(json.dumps({
                            "year": year, "id": aid, "text": text,
                        }) + "\n")
                        got += 1
                time.sleep(6.0)
            n_total += got
            print(f"{year}: {got} abstracts", flush=True)
    print(f"TOTAL: {n_total}")


# ---------------------------------------------------------------------------
# Project Gutenberg classic literature
# ---------------------------------------------------------------------------
GB_BASE = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"
GB_SEG_WORDS = 600

GB_BOOKS = {
    "Charles Dickens": [98, 730, 766, 1023, 1400, 19337],
    "Jane Austen": [1342, 161, 141, 121],
    "Charlotte Bronte": [1260],
    "Emily Bronte": [768],
    "George Eliot": [6688, 145],
    "Herman Melville": [2701],
    "Thomas Hardy": [153, 230],
    "Joseph Conrad": [974, 219],
    "Henry James": [2833, 209],
    "Mark Twain": [74, 76, 3176],
    "Virginia Woolf": [144, 58],
    "Oscar Wilde": [174, 924],
    "Arthur Conan Doyle": [1661, 2852],
    "Mary Shelley": [84],
    "Louisa May Alcott": [514, 4792],
    "Leo Tolstoy": [2600, 1399],
    "Fyodor Dostoevsky": [2554, 8117],
    "William Makepeace Thackeray": [599],
    "Anthony Trollope": [787],
    "Elizabeth Gaskell": [39423, 43924],
    "Jack London": [910, 215],
    "Edith Wharton": [284, 45],
    "James Joyce": [4300, 2814],
    "D.H. Lawrence": [217],
    "Robert Louis Stevenson": [120],
}

GB_START_RE = re.compile(
    r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*",
    re.IGNORECASE | re.DOTALL,
)
GB_END_RE = re.compile(
    r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*.*$",
    re.IGNORECASE | re.DOTALL,
)
GB_ALIASES = {"dostoevsky": ["dostoevsky", "dostoyevsky", "dostoevski", "dostoevskii"]}


def gb_fetch_text(gid):
    for url in [
        GB_BASE.format(id=gid),
        f"https://www.gutenberg.org/files/{gid}/{gid}-0.txt",
    ]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 research/0.1"})
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
            if raw[:2] == b"PK":
                z = zipfile.ZipFile(io.BytesIO(raw))
                raw = z.read(z.namelist()[0])
            return raw.decode("utf-8", errors="replace")
        except Exception:
            time.sleep(2)
    return None


def gb_strip(text):
    m = GB_START_RE.search(text)
    if m:
        text = text[m.end():]
    m = GB_END_RE.search(text)
    if m:
        text = text[: m.start()]
    return text.strip()


def gb_segments(text):
    words = text.split()
    n = len(words)
    return [" ".join(words[i: i + GB_SEG_WORDS])
            for i in range(0, n - GB_SEG_WORDS + 1, GB_SEG_WORDS)]


def gb_deaccent(s):
    import unicodedata
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )


def gb_author_matches(surname, header_author):
    h = gb_deaccent(header_author).lower()
    variants = GB_ALIASES.get(surname.lower(), [surname.lower()])
    return any(v in h for v in variants)


def collect_gutenberg():
    total = 0
    kept_books = 0
    with open(paths.GUTENBERG_SEGMENTS, "a", encoding="utf-8") as out:
        for author, ids in GB_BOOKS.items():
            surname = author.split()[-1].split("(")[0].strip()
            for gid in ids:
                text = gb_fetch_text(gid)
                if text is None:
                    print(f"FAIL fetch {author} {gid}", flush=True)
                    continue
                hm = re.search(r"Title:\s*(.+)", text[:4000])
                am = re.search(r"Author:\s*(.+)", text[:4000])
                title = hm.group(1).strip() if hm else "?"
                header_author = am.group(1).strip() if am else "?"
                if not gb_author_matches(surname, header_author):
                    print(f"SKIP {author} {gid}: header says '{header_author}' / '{title[:40]}'", flush=True)
                    continue
                body = gb_strip(text)
                segs = gb_segments(body)
                for i, s in enumerate(segs):
                    out.write(json.dumps({
                        "author": author, "title": title, "gutenberg_id": gid,
                        "seg_idx": i, "text": s,
                    }) + "\n")
                    total += 1
                kept_books += 1
                print(f"OK {author} #{gid} '{title[:45]}': {len(segs)} segs", flush=True)
                time.sleep(2)
    print(f"books: {kept_books}, segments: {total}")


# ---------------------------------------------------------------------------
# Hugging Face dataset downloads (GPT-wiki-intro, HC3)
# ---------------------------------------------------------------------------
def download_hf(filename, url, dest=None):
    """Stream a public HF asset to data/raw (overwrite)."""
    dest = dest or (paths.DATA_RAW / filename)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": HFA_UA})
    with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    tmp.replace(dest)
    print(f"downloaded {filename} -> {dest}")
    return dest


# Expected HF asset URLs (verified against the HF API in Nov 2026;
# dataset names and file names are case-sensitive).
HF_ASSETS = {
    "gpt_wiki_intro.zip": "https://huggingface.co/datasets/aadityaubhat/GPT-wiki-intro/resolve/main/GPT-wiki-intro.csv.zip",
    "hc3_all.jsonl": "https://huggingface.co/datasets/Hello-SimpleAI/HC3/resolve/main/all.jsonl",
}

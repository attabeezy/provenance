"""Command-line entry point.

Subcommands:
  collect hn|arxiv|gutenberg|gpt2 [years...]  network collection of raw corpora
  download {wiki|hc3}                     download Hugging Face assets
  extract wiki|hc3|feats|gpt2             build derived pairs + feature caches
  run {e1|e1fig|e1report|e2|e3|e4|e5|meta}  execute experiments
"""
import argparse
import sys


def main(argv=None):
    p = argparse.ArgumentParser(prog="prov", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("collect", help="collect raw corpora (networked)")
    c.add_argument("corpus", choices=["hn", "arxiv", "gutenberg", "gpt2"])
    c.add_argument("years", nargs="*", type=int,
                   help="optional year filter (arxiv only)")

    d = sub.add_parser("download", help="download HF dataset assets")
    d.add_argument("asset", choices=["wiki", "hc3", "all"])

    e = sub.add_parser("extract", help="build derived pairs / feature caches")
    e.add_argument("what", choices=["wiki", "hc3", "feats", "gpt2"])
    r = sub.add_parser("run", help="run an experiment")
    r.add_argument("exp", choices=["e1", "e1fig", "e1report", "e2", "e3",
                                   "e4", "e5", "meta"])

    args = p.parse_args(argv)

    from . import collect, extract, paths  # noqa: F401  paths: fail fast if bad

    if args.cmd == "collect":
        if args.corpus == "hn":
            collect.collect_hn()
        elif args.corpus == "arxiv":
            collect.collect_arxiv(args.years or None)
        elif args.corpus == "gpt2":
            collect.collect_gpt2()
        else:
            collect.collect_gutenberg()
    elif args.cmd == "download":
        if args.asset in ("wiki", "all"):
            _d = collect.HF_ASSETS["gpt_wiki_intro.zip"]
            collect.download_hf("gpt_wiki_intro.zip", _d)
        if args.asset in ("hc3", "all"):
            _u = collect.HF_ASSETS["hc3_all.jsonl"]
            collect.download_hf("hc3_all.jsonl", _u)
    elif args.cmd == "extract":
        if args.what == "wiki":
            extract.wiki_pairs()
        elif args.what == "hc3":
            extract.hc3_pairs()
        elif args.what == "gpt2":
            extract.gpt2_caches()
        else:
            extract.feat_cache()
    elif args.cmd == "run":
        from .experiments import (
            e1_timeseries, e1_figure, e1_report, e2_overlap, e3_detector,
            e4_math, e5_vintage, meta_audit,
        )
        mods = {
            "e1": e1_timeseries, "e1fig": e1_figure, "e1report": e1_report,
            "e2": e2_overlap, "e3": e3_detector, "e4": e4_math, "e5": e5_vintage,
            "meta": meta_audit,
        }
        mods[args.exp].main()
    return 0


if __name__ == "__main__":
    sys.exit(main())

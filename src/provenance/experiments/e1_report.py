"""Pretty-print E1 results table."""
import json

from .. import paths


def main():
    d = json.load(open(paths.E1_TIMESERIES, encoding="utf-8"))
    for corpus in ["hn", "arxiv"]:
        print("=" * 20, corpus.upper(), "=" * 20)
        hdr = (f"{'yr':>4} {'words':>9} {'emdash/1k':>10} {'delve/100k':>11} "
               f"{'core/100k':>10} {'moreover/100k':>13} {'triad/1k':>9} "
               f"{'notxbut/100k':>13}")
        print(hdr)
        for y in sorted(d[corpus], key=int):
            v = d[corpus][y]
            print(f"{y:>4} {v['n_words']:>9,} "
                  f"{v['emdash_per_1k']['rate']:>10.2f} "
                  f"{v['delve_per_100k']['rate']:>11.2f} "
                  f"{v['core_per_100k']['rate']:>10.2f} "
                  f"{v['moreover_per_100k']['rate']:>13.2f} "
                  f"{v['triad_per_1k']['rate']:>9.2f} "
                  f"{v['notxbut_per_100k']['rate']:>13.2f}")


if __name__ == "__main__":
    main()

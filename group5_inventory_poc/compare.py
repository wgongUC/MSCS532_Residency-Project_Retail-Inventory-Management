"""Before/after comparison at progressively larger sizes (timeit-based).

Runs timeit_bench.py for the ORIGINAL code (original_phase2/) and the
OPTIMIZED code (this folder) on identical data, checks that both give
identical answers, and prints a before/after table for each size.

    python3 compare.py                         # n = 10k, 50k, 200k (synthetic)
    python3 compare.py --sizes 10000 50000     # choose sizes
    python3 compare.py --dataset common.csv --sizes 1000 10000 100000

Results are also saved to perf_results/compare_results.txt.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OPS = ["get", "sell", "bestseller", "price_range", "change_price", "top_k(10)"]


def run(impl, n, dataset):
    cmd = [sys.executable, os.path.join(HERE, "timeit_bench.py"), "--impl", impl, "--n", str(n)]
    if dataset:
        cmd += ["--dataset", dataset]
    return json.loads(subprocess.check_output(cmd, cwd=HERE).decode().strip().splitlines()[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=int, nargs="+", default=[10_000, 50_000, 200_000])
    ap.add_argument("--dataset")
    args = ap.parse_args()

    lines = []
    def out(s=""):
        print(s, flush=True)
        lines.append(s)

    src = f"dataset {args.dataset}" if args.dataset else "synthetic data (seed 532)"
    out(f"Before/after, timeit best-of-5, microseconds per call, {src}")
    for n in args.sizes:
        before, after = run("original", n, args.dataset), run("optimized", n, args.dataset)
        same = before["answers"] == after["answers"]
        out()
        out(f"n = {before['n']:,} products   answers identical: {'YES' if same else 'NO  <-- PROBLEM'}")
        out(f"  {'operation':<14}{'before µs':>12}{'after µs':>12}{'speedup':>10}")
        for op in OPS:
            b, a = before["us_per_call"][op], after["us_per_call"][op]
            out(f"  {op:<14}{b:>12.2f}{a:>12.2f}{b / a:>9.1f}x")
    out()
    out("Note: the original has no top-k operation; its 'before' column uses")
    out("heapq.nsmallest over all products, the best read-only alternative.")

    os.makedirs(os.path.join(HERE, "perf_results"), exist_ok=True)
    with open(os.path.join(HERE, "perf_results", "compare_results.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()

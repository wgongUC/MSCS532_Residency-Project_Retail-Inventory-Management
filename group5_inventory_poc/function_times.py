"""Per-function times BEFORE vs AFTER optimization.

Runs the same 50,000-product / 500,000-operation workload (profile_run.py)
on the ORIGINAL code (original_phase2/) and the OPTIMIZED code (this folder):

  Table 1: wall-clock time per operation type (no profiler running)
  Table 2: cProfile per function: number of calls and time inside each
           function (tottime), before vs after

    python3 function_times.py              # full workload (~1-2 minutes)
    python3 function_times.py --scale 0.2  # quick version

Saved to perf_results/function_times.txt.
"""
import argparse
import cProfile
import json
import os
import pstats
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_FILES = {"inventory.py", "avl_tree.py", "max_heap.py", "product.py"}


def child(impl, scale, stats_path):
    """Run inside a subprocess so each version imports its own modules."""
    sys.path.insert(0, os.path.join(HERE, "original_phase2") if impl == "original" else HERE)
    sys.path.insert(1, HERE)
    import profile_run  # uses whichever `inventory` module is first on the path
    data = profile_run.build_workload(scale)
    _, times, counts, checksum = profile_run.run(*data)          # 1) plain timing
    prof = cProfile.Profile()
    prof.enable()
    profile_run.run(*data)                                       # 2) profiled run
    prof.disable()
    prof.dump_stats(stats_path)
    print(json.dumps({"times": times, "counts": counts, "checksum": checksum}))


def per_function(stats_path):
    """{function name: (calls, tottime)} for project files, merged by name."""
    out = {}
    for (file, _line, func), (_cc, nc, tt, _ct, _callers) in pstats.Stats(stats_path).stats.items():
        base = os.path.basename(file)
        if base in PROJECT_FILES:
            key = f"{base}: {func}"
            calls, t = out.get(key, (0, 0.0))
            out[key] = (calls + nc, t + tt)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--child", nargs=2, metavar=("IMPL", "STATS"))
    args = ap.parse_args()
    if args.child:
        return child(args.child[0], args.scale, args.child[1])

    tmp = tempfile.mkdtemp()
    res = {}
    for impl in ("original", "optimized"):
        print(f"running {impl} ...", flush=True)
        path = os.path.join(tmp, impl + ".prof")
        outp = subprocess.check_output([sys.executable, __file__, "--scale", str(args.scale), "--child", impl, path], cwd=HERE)
        res[impl] = json.loads(outp.decode().strip().splitlines()[-1])
        res[impl]["funcs"] = per_function(path)

    lines = []
    def out(s=""):
        print(s)
        lines.append(s)

    b, a = res["original"], res["optimized"]
    out()
    out(f"Answers identical (checksum): {'YES' if b['checksum'] == a['checksum'] else 'NO'}  ({a['checksum']})")
    out()
    out("TABLE 1: Time per operation type, wall clock, no profiler")
    out(f"  {'operation':<14}{'calls':>9}{'before (s)':>12}{'after (s)':>11}{'before µs':>11}{'after µs':>10}{'change':>9}")
    tb = ta = 0.0
    for op in sorted(b["times"], key=b["times"].get, reverse=True):
        n, x, y = b["counts"][op], b["times"][op], a["times"][op]
        tb, ta = tb + x, ta + y
        out(f"  {op:<14}{n:>9,}{x:>12.3f}{y:>11.3f}{x / n * 1e6:>11.2f}{y / n * 1e6:>10.2f}{(y - x) / x * 100:>8.0f}%")
    out(f"  {'ALL':<14}{'':>9}{tb:>12.3f}{ta:>11.3f}{'':>11}{'':>10}{(ta - tb) / tb * 100:>8.0f}%")

    out()
    out("TABLE 2: Time inside each function (cProfile tottime; profiler overhead inflates all numbers)")
    out(f"  {'function':<34}{'calls before':>14}{'calls after':>13}{'before (s)':>12}{'after (s)':>11}")
    names = sorted(set(b["funcs"]) | set(a["funcs"]), key=lambda k: -max(b["funcs"].get(k, (0, 0))[1], a["funcs"].get(k, (0, 0))[1]))
    for k in names:
        cb, tbf = b["funcs"].get(k, (0, 0.0))
        ca, taf = a["funcs"].get(k, (0, 0.0))
        if max(tbf, taf) < 0.005:
            continue
        fmt = lambda c: f"{c:,}" if c else "(none)"
        out(f"  {k:<34}{fmt(cb):>14}{fmt(ca):>13}{tbf:>12.3f}{taf:>11.3f}")
    out()
    out("(none) = the function does not exist in that version, or is no longer called.")

    os.makedirs(os.path.join(HERE, "perf_results"), exist_ok=True)
    with open(os.path.join(HERE, "perf_results", "function_times.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()

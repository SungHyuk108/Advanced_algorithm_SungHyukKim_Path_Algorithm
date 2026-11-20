"""실험 CSV를 요약표와 그래프로 만든다.

사용 예 (저장소 맨 위 폴더에서)
  python -m src.plot                                  # results/results.csv → results/figures/
  python -m src.plot --csv results/quick.csv --out results/quick_figures

만드는 것
  summary.csv / summary.md : 조건 × 크기 × 알고리즘별 평균 ± 표준편차
  expanded_vs_cells.png    : 칸 수에 따른 확장 칸 수 (로그-로그)
  time_vs_cells.png        : 칸 수에 따른 실행 시간 (로그-로그)
  max_open_vs_cells.png    : 칸 수에 따른 큐 최대 길이 (로그-로그)
  bfs_excess.png           : 조건 ③에서 BFS 경로 비용의 최소 대비 초과율 분포
  tradeoff.png             : 조건 ③, 가장 큰 n에서 확장 칸 수 대 비용 초과율 (지도 한 장 = 점 하나)
"""
from __future__ import annotations

import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ALGO_ORDER = ["bfs", "dijkstra", "astar", "astar_large_g"]
ALGO_LABEL = {"bfs": "BFS", "dijkstra": "Dijkstra", "astar": "A* (tie: FIFO)",
              "astar_large_g": "A* (tie: larger g)"}
ALGO_COLOR = {"bfs": "#d97706", "dijkstra": "#2563eb", "astar": "#0f766e", "astar_large_g": "#9333ea"}
ALGO_STYLE = {"bfs": "o-", "dijkstra": "s-", "astar": "^-", "astar_large_g": "v--"}
COND_ORDER = ["empty", "walls", "walls_mud"]
COND_LABEL = {"empty": "(1) empty", "walls": "(2) walls 20%", "walls_mud": "(3) walls 20% + mud 30%"}
METRICS = ["expanded", "max_open", "time_ms", "steps", "cost", "excess_pct", "updates"]


def load(path: Path) -> list:
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["n"] = int(r["n"])
        r["cells"] = int(r["cells"])
        for m in METRICS:
            r[m] = float(r[m])
    return rows


def summarize(rows: list) -> dict:
    """(조건, n, 알고리즘) → {지표: (평균, 표준편차, 지도 수)}"""
    groups = defaultdict(list)
    for r in rows:
        groups[(r["condition"], r["n"], r["algorithm"])].append(r)
    out = {}
    for key, rs in groups.items():
        out[key] = {}
        for m in METRICS:
            vals = [r[m] for r in rs]
            sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
            out[key][m] = (statistics.mean(vals), sd, len(vals))
    return out


def ordered(keys, order):
    return [k for k in order if k in keys] + sorted(k for k in keys if k not in order)


def write_summary(summary: dict, out_dir: Path) -> None:
    def rank(k):
        c = COND_ORDER.index(k[0]) if k[0] in COND_ORDER else 99
        a = ALGO_ORDER.index(k[2]) if k[2] in ALGO_ORDER else 99
        return (c, k[1], a)
    keys = sorted(summary, key=rank)
    with (out_dir / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["condition", "n", "algorithm", "maps"] +
                   [f"{m}_{s}" for m in METRICS for s in ("mean", "std")])
        for k in keys:
            s = summary[k]
            w.writerow([*k, s["expanded"][2]] +
                       [round(v, 4) for m in METRICS for v in s[m][:2]])
    lines = ["| 조건 | n | 알고리즘 | 지도 수 | 확장 칸 수 | 큐 최대 길이 | 시간(ms) | 경로 칸 수 | 비용 초과율(%) | 갱신 |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for k in keys:
        s = summary[k]

        def ms(m, d=1):
            mean, sd, _ = s[m]
            return f"{mean:.{d}f} ± {sd:.{d}f}"
        lines.append(f"| {k[0]} | {k[1]} | {k[2]} | {s['expanded'][2]} | {ms('expanded')} | "
                     f"{ms('max_open')} | {ms('time_ms', 3)} | {ms('steps')} | {ms('excess_pct', 2)} | "
                     f"{ms('updates')} |")
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_growth(summary: dict, metric: str, ylabel: str, path: Path) -> None:
    conds = ordered({k[0] for k in summary}, COND_ORDER)
    fig, axes = plt.subplots(1, len(conds), figsize=(5 * len(conds), 4.2), squeeze=False)
    for ax, cond in zip(axes[0], conds):
        algos = ordered({k[2] for k in summary if k[0] == cond}, ALGO_ORDER)
        for algo in algos:
            ns = sorted(k[1] for k in summary if k[0] == cond and k[2] == algo)
            xs = [n * n for n in ns]
            means = [summary[(cond, n, algo)][metric][0] for n in ns]
            sds = [summary[(cond, n, algo)][metric][1] for n in ns]
            ax.errorbar(xs, means, yerr=sds, fmt=ALGO_STYLE.get(algo, "o-"), capsize=3,
                        color=ALGO_COLOR.get(algo), label=ALGO_LABEL.get(algo, algo), markersize=5)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(COND_LABEL.get(cond, cond))
        ax.set_xlabel("cells (n x n)")
        ax.set_ylabel(ylabel)
        ax.grid(True, which="both", alpha=0.25)
    axes[0][0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_bfs_excess(rows: list, path: Path) -> None:
    data = [r for r in rows if r["condition"] == "walls_mud" and r["algorithm"] == "bfs"]
    if not data:
        return
    ns = sorted({r["n"] for r in data})
    fig, ax = plt.subplots(figsize=(6, 4.2))
    ax.boxplot([[r["excess_pct"] for r in data if r["n"] == n] for n in ns])
    ax.set_xticks(range(1, len(ns) + 1), [str(n) for n in ns])
    ax.set_xlabel("n")
    ax.set_ylabel("BFS path cost over optimum (%)")
    ax.set_title("(3) walls + mud: how much BFS overpays")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_tradeoff(rows: list, path: Path) -> None:
    data = [r for r in rows if r["condition"] == "walls_mud"]
    if not data:
        return
    n = max(r["n"] for r in data)
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for algo in ordered({r["algorithm"] for r in data}, ALGO_ORDER):
        pts = [r for r in data if r["n"] == n and r["algorithm"] == algo]
        ax.scatter([r["expanded"] for r in pts], [r["excess_pct"] for r in pts], s=22, alpha=0.7,
                   color=ALGO_COLOR.get(algo), label=ALGO_LABEL.get(algo, algo))
    ax.set_xlabel("expanded cells (work)")
    ax.set_ylabel("path cost over optimum (%)")
    ax.set_title(f"(3) walls + mud, n = {n}: work vs. cost (one dot = one map)")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="실험 결과 요약과 그래프")
    p.add_argument("--csv", type=Path, default=Path("results/results.csv"))
    p.add_argument("--out", type=Path, default=Path("results/figures"))
    a = p.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    rows = load(a.csv)
    summary = summarize(rows)
    write_summary(summary, a.out)
    plot_growth(summary, "expanded", "expanded cells", a.out / "expanded_vs_cells.png")
    plot_growth(summary, "time_ms", "time (ms, median)", a.out / "time_vs_cells.png")
    plot_growth(summary, "max_open", "max queue size (cells)", a.out / "max_open_vs_cells.png")
    plot_bfs_excess(rows, a.out / "bfs_excess.png")
    plot_tradeoff(rows, a.out / "tradeoff.png")
    print(f"요약표와 그래프 저장: {a.out}")


if __name__ == "__main__":
    main()

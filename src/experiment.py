"""실험 실행기: 조건 × 크기 × 시드마다 지도를 만들고 모든 알고리즘을 같은 지도에서 돌려 CSV로 저장한다.

사용 예 (저장소 맨 위 폴더에서)
  python -m src.experiment            # 본 실험 (n = 25, 50, 100, 200 · 시드 50 · 시간 5회)
  python -m src.experiment --quick    # 빠른 점검 (n = 25, 50 · 시드 3 · 시간 1회)

측정
- 확장 칸 수, 큐 최대 길이, 갱신 횟수, 경로 비용, 경로 칸 수: 결정적이라 한 번 재면 됨
  (반복 실행마다 같은 값이 나오는지도 확인한다)
- 실행 시간: 탐색 함수 호출부터 경로 복원까지(지도 생성 제외), reps번 재서 중앙값.
  측정 중에는 가비지 컬렉션을 잠시 끈다.
- 조건 ① 빈 격자는 무작위 요소가 없어 크기마다 지도 1장(seed 0)만 쓴다.
"""
from __future__ import annotations

import argparse
import csv
import gc
import json
import platform
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

from .algorithms import ALGORITHMS
from .grid import CONDITIONS, DEFAULT_MUD_COST, make_grid
from .validate import cross_check

FIELDS = ["condition", "n", "cells", "seed", "attempts", "mud_cost", "algorithm",
          "found", "cost", "steps", "expanded", "max_open", "updates",
          "time_ms", "opt_cost", "excess_pct"]


def timed(fn, grid, reps: int):
    """reps번 실행해 실행 시간 중앙값(ms)과 결과를 돌려준다. 결과가 매번 같은지도 확인한다."""
    times, first = [], None
    gc_was_enabled = gc.isenabled()
    for _ in range(reps):
        gc.collect()
        gc.disable()
        t0 = time.perf_counter()
        r = fn(grid)
        t1 = time.perf_counter()
        if gc_was_enabled:
            gc.enable()
        times.append((t1 - t0) * 1000)
        if first is None:
            first = r
        elif (r.cost, r.steps, r.expanded, r.max_open, r.updates) != \
             (first.cost, first.steps, first.expanded, first.max_open, first.updates):
            raise RuntimeError(f"{r.algorithm}: 반복 실행 결과가 다릅니다")
    return first, statistics.median(times)


def run(sizes, seeds, reps, conditions, algorithms, mud_cost, out_path: Path) -> list:
    if "dijkstra" not in algorithms:
        raise ValueError("최소 비용 기준이 되는 dijkstra는 항상 포함해야 합니다")
    rows = []
    for cond in conditions:
        for n in sizes:
            seed_list = [0] if cond == "empty" else list(range(seeds))
            t_start = time.perf_counter()
            for seed in seed_list:
                grid = make_grid(n, cond, seed, mud_cost=mud_cost)
                results, times = {}, {}
                for name in algorithms:
                    results[name], times[name] = timed(ALGORITHMS[name], grid, reps)
                cross_check(grid, results)          # 이론상 관계가 깨지면 여기서 멈춘다
                opt = results["dijkstra"].cost
                for name in algorithms:
                    r = results[name]
                    rows.append({
                        "condition": cond, "n": n, "cells": n * n, "seed": seed,
                        "attempts": grid.attempts, "mud_cost": mud_cost, "algorithm": name,
                        "found": r.found, "cost": r.cost, "steps": r.steps,
                        "expanded": r.expanded, "max_open": r.max_open, "updates": r.updates,
                        "time_ms": round(times[name], 4), "opt_cost": opt,
                        "excess_pct": round((r.cost - opt) / opt * 100, 4),
                    })
            print(f"[{cond:9s}] n={n:<4d} 지도 {len(seed_list):>3d}장 완료 "
                  f"({time.perf_counter() - t_start:.1f}s)", flush=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="BFS · 다익스트라 · A* 비교 실험")
    p.add_argument("--sizes", type=int, nargs="+", default=[25, 50, 100, 200])
    p.add_argument("--seeds", type=int, default=50, help="조건 ②③에서 쓸 시드 개수 (0부터)")
    p.add_argument("--reps", type=int, default=5, help="실행 시간 반복 횟수 (중앙값 사용)")
    p.add_argument("--conditions", nargs="+", default=list(CONDITIONS), choices=list(CONDITIONS))
    p.add_argument("--algorithms", nargs="+", default=list(ALGORITHMS), choices=list(ALGORITHMS))
    p.add_argument("--mud-cost", type=int, default=DEFAULT_MUD_COST)
    p.add_argument("--out", type=Path, default=Path("results/results.csv"))
    p.add_argument("--quick", action="store_true", help="빠른 점검용 축소 실행")
    a = p.parse_args(argv)
    if a.quick:
        a.sizes, a.seeds, a.reps = [25, 50], 3, 1
        if a.out == Path("results/results.csv"):
            a.out = Path("results/quick.csv")

    t0 = time.perf_counter()
    rows = run(a.sizes, a.seeds, a.reps, a.conditions, a.algorithms, a.mud_cost, a.out)
    info = {
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "elapsed_s": round(time.perf_counter() - t0, 1),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor(),
        "args": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(a).items()},
        "rows": len(rows),
    }
    info_path = a.out.with_name(a.out.stem + "_info.json")
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(rows)}행 저장: {a.out}  (실행 환경: {info_path})")


if __name__ == "__main__":
    main()

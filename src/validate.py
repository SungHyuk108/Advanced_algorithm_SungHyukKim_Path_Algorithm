"""결과 검증. 실험 중 매 지도마다 호출해 잘못된 결과가 CSV에 들어가지 않게 막는다."""
from __future__ import annotations

from .grid import INF, Grid


class ValidationError(AssertionError):
    pass


def check_path(grid: Grid, result) -> None:
    """경로가 시작→목표로 한 칸씩 이어지고 벽을 지나지 않으며, 보고한 비용·칸 수와 맞는지."""
    if not result.found:
        raise ValidationError(f"{result.algorithm}: 경로를 찾지 못했습니다")
    p = result.path
    if p[0] != grid.start or p[-1] != grid.goal:
        raise ValidationError(f"{result.algorithm}: 경로의 처음과 끝이 시작·목표가 아닙니다")
    w = grid.width
    for a, b in zip(p, p[1:]):
        if grid.cost[b] == INF:
            raise ValidationError(f"{result.algorithm}: 경로가 벽 {grid.xy(b)}을 지납니다")
        if abs(a % w - b % w) + abs(a // w - b // w) != 1:
            raise ValidationError(f"{result.algorithm}: {grid.xy(a)}→{grid.xy(b)}가 한 칸 이동이 아닙니다")
    if grid.path_cost(p) != result.cost:
        raise ValidationError(f"{result.algorithm}: 경로 비용이 보고값과 다릅니다")
    if len(p) - 1 != result.steps:
        raise ValidationError(f"{result.algorithm}: 경로 칸 수가 보고값과 다릅니다")


def cross_check(grid: Grid, results: dict) -> None:
    """알고리즘끼리 이론상 성립해야 하는 관계를 확인한다.

    - 다익스트라와 A*(w=1, 동점 처리 무관)의 경로 비용이 같다 (둘 다 최소 비용)
    - BFS의 경로 비용 ≥ 최소 비용
    - BFS의 경로 칸 수 ≤ 다른 알고리즘의 경로 칸 수 (BFS는 칸 수 최소)
    """
    for r in results.values():
        check_path(grid, r)
    opt = results["dijkstra"].cost
    for name, r in results.items():
        if name.startswith("astar") and r.cost != opt:
            raise ValidationError(f"{name}의 비용 {r.cost}이 최소 비용 {opt}과 다릅니다")
    if "bfs" in results:
        b = results["bfs"]
        if b.cost < opt:
            raise ValidationError("BFS 비용이 최소 비용보다 작습니다")
        for name, r in results.items():
            if r.steps < b.steps:
                raise ValidationError(f"{name}의 칸 수가 BFS보다 적습니다")

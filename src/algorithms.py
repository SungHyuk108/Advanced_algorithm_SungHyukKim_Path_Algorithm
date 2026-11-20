"""BFS · 다익스트라 · A*.

세 알고리즘은 같은 뼈대를 쓴다.
  1. 후보 목록(큐)에서 칸 하나를 꺼낸다 (= 확장, expanded를 1 늘린다)
  2. 꺼낸 칸이 목표면 끝낸다
  3. 이웃을 위, 아래, 왼쪽, 오른쪽 순서로 보고, 새로 알게 되면 부모를 적고 큐에 넣는다
다른 것은 1번에서 "어떤 칸을 먼저 꺼내느냐" 하나뿐이다.
  BFS        : 먼저 들어온 칸 (일반 큐, FIFO)
  다익스트라 : g가 가장 작은 칸 (우선순위 큐)
  A*         : f = g + w*h 가 가장 작은 칸 (우선순위 큐)

측정 정의
- expanded : 큐에서 꺼내 확장한 칸 수 (목표 칸 포함). 낡은 항목을 꺼내 건너뛴 것은 세지 않는다.
- max_open : 큐에 동시에 들어 있던 "서로 다른 칸" 수의 최댓값.
             heapq는 키를 바꿀 수 없어 갱신 때 항목을 하나 더 넣는데, 그 낡은 항목은 세지 않는다.
- updates  : 이미 g가 적혀 있던 칸의 g가 더 작은 값으로 바뀐 횟수 (갱신).
- 동점 처리 : 키가 같으면 먼저 큐에 들어온 칸 우선 (fifo). A*는 g가 큰 칸 우선(large_g)도 고를 수 있다.
"""
from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass, field

from .grid import INF, Grid


@dataclass
class SearchResult:
    algorithm: str
    found: bool
    cost: int | None        # 경로 비용 합 (시작 칸 제외)
    steps: int | None       # 경로 칸 수 (이동 횟수)
    expanded: int           # 확장한 칸 수
    max_open: int           # 큐 최대 길이 (서로 다른 칸 수)
    updates: int            # 갱신 횟수
    path: list = field(default_factory=list, repr=False)


def _build_path(parent: list, goal: int) -> list:
    """목표에서 부모를 거꾸로 따라가 시작→목표 순서의 경로를 만든다."""
    path, k = [], goal
    while k != -1:
        path.append(k)
        k = parent[k]
    path.reverse()
    return path


def _result(name: str, grid: Grid, found: bool, parent: list,
            expanded: int, max_open: int, updates: int) -> SearchResult:
    if not found:
        return SearchResult(name, False, None, None, expanded, max_open, updates, [])
    path = _build_path(parent, grid.goal)
    return SearchResult(name, True, grid.path_cost(path), len(path) - 1,
                        expanded, max_open, updates, path)


def bfs(grid: Grid) -> SearchResult:
    """BFS: 먼저 발견한 칸부터 꺼낸다. 비용을 보지 않으므로 칸 수가 최소인 경로를 낸다."""
    parent = [-1] * grid.size
    seen = [False] * grid.size          # 발견 표시 (큐에 넣는 순간 표시)
    seen[grid.start] = True
    queue = deque([grid.start])
    expanded, max_open, found = 0, 1, False

    while queue:
        c = queue.popleft()
        expanded += 1
        if c == grid.goal:
            found = True
            break
        for nb in grid.neighbors(c):
            if seen[nb]:
                continue                 # 이미 발견한 칸은 무시 (갱신 없음)
            seen[nb] = True
            parent[nb] = c
            queue.append(nb)
        if len(queue) > max_open:
            max_open = len(queue)

    return _result("bfs", grid, found, parent, expanded, max_open, 0)


def _best_first(grid: Grid, name: str, w: float, tie: str) -> SearchResult:
    """다익스트라와 A*의 공통 구현. 키 = g + w*h (다익스트라는 w = 0).

    tie = "fifo"    : 키가 같으면 먼저 큐에 들어온 칸 우선
    tie = "large_g" : 키가 같으면 g가 큰 칸(목표에 더 가까이 간 칸) 우선, 그다음 먼저 들어온 칸
    """
    if tie not in ("fifo", "large_g"):
        raise ValueError(f"알 수 없는 동점 처리: {tie}")
    size = grid.size
    g = [INF] * size
    parent = [-1] * size
    closed = [False] * size              # 확장 끝
    in_open = [False] * size             # 지금 큐에 들어 있음 (서로 다른 칸 수 세기용)
    heap: list = []
    seq = 0                               # 큐에 넣은 순서 (fifo 동점 처리용)
    use_h = w != 0

    def key_of(i: int) -> float:
        return g[i] + w * grid.manhattan(i) if use_h else g[i]

    def push(i: int) -> None:
        nonlocal seq
        tb = -g[i] if tie == "large_g" else 0
        heapq.heappush(heap, (key_of(i), tb, seq, i))
        seq += 1

    g[grid.start] = 0
    push(grid.start)
    in_open[grid.start] = True
    open_count, max_open = 1, 1
    expanded, updates, found = 0, 0, False

    while heap:
        key, _, _, c = heapq.heappop(heap)
        if closed[c] or key != key_of(c):
            continue                      # 낡은 항목: 갱신 전에 넣었던 것이라 건너뜀
        in_open[c] = False
        open_count -= 1
        closed[c] = True
        expanded += 1
        if c == grid.goal:
            found = True
            break
        gc = g[c]
        for nb in grid.neighbors(c):
            cand = gc + grid.cost[nb]
            if cand >= g[nb]:
                continue                  # 무시: 이번 후보가 기존 기록보다 싸지 않음
            if g[nb] != INF:
                updates += 1              # 이미 적힌 g가 더 작아짐 = 갱신
            g[nb] = cand
            parent[nb] = c
            if closed[nb]:
                closed[nb] = False        # 확장 끝난 칸에 더 싼 길 → 다시 큐로 (w > 1에서 생길 수 있음)
            if not in_open[nb]:
                in_open[nb] = True
                open_count += 1
            push(nb)
        if open_count > max_open:
            max_open = open_count

    return _result(name, grid, found, parent, expanded, max_open, updates)


def dijkstra(grid: Grid) -> SearchResult:
    """다익스트라: g(지금까지 쓴 비용)가 가장 작은 칸부터 꺼낸다. 항상 최소 비용."""
    return _best_first(grid, "dijkstra", w=0, tie="fifo")


def astar(grid: Grid, w: float = 1.0, tie: str = "fifo", name: str | None = None) -> SearchResult:
    """A*: f = g + w*h 가 가장 작은 칸부터 꺼낸다. h는 목표까지의 맨해튼 거리.

    w = 1이면 최소 비용이 보장된다 (칸 비용이 1 이상이라 h가 실제 남은 비용을 넘지 않음).
    """
    if name is None:
        name = "astar" if tie == "fifo" else f"astar_{tie}"
    return _best_first(grid, name, w=w, tie=tie)


# 실험에서 돌릴 알고리즘 목록. 메인 A*는 fifo, astar_large_g는 해석용 보조 변형.
ALGORITHMS = {
    "bfs": bfs,
    "dijkstra": dijkstra,
    "astar": lambda grid: astar(grid, w=1.0, tie="fifo"),
    "astar_large_g": lambda grid: astar(grid, w=1.0, tie="large_g"),
}

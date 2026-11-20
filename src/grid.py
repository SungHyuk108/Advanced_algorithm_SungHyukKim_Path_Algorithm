"""격자 지도와 지도 생성기.

규칙 (보고서의 실험 설계와 같음)
- 칸 번호는 i = y * width + x 로 한 줄로 펼쳐서 쓴다.
- 진입 비용은 그 칸에 "들어갈 때" 낸다. 시작 칸의 비용은 세지 않는다.
- 벽은 비용 INF(들어갈 수 없음)로 표시한다.
- 이웃은 위, 아래, 왼쪽, 오른쪽 순서로 본다. (공모전 search.py와 같은 순서)
- 지도 생성: 시작·목표 칸을 뺀 칸에서 전체 칸 수 기준 정확한 비율만큼
  장애물과 진흙을 무작위로 고른다. 목표에 갈 수 없으면 같은 난수 생성기로
  이어서 다시 뽑고, 몇 번 뽑았는지(attempts)를 기록한다.
"""
from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, field

INF = math.inf

# 이웃 순서: 위, 아래, 왼쪽, 오른쪽 (dx, dy)
DIRECTIONS = ((0, -1), (0, 1), (-1, 0), (1, 0))

# 지도 조건: 장애물 비율(%)과 진흙 비율(%)은 모두 "전체 칸 수" 기준
CONDITIONS = {
    "empty": {"wall_pct": 0, "mud_pct": 0},       # ① 빈 격자
    "walls": {"wall_pct": 20, "mud_pct": 0},      # ② 장애물
    "walls_mud": {"wall_pct": 20, "mud_pct": 30},  # ③ 장애물 + 진흙
}
DEFAULT_MUD_COST = 5


@dataclass
class Grid:
    width: int
    height: int
    cost: list            # 칸마다 진입 비용 (벽은 INF)
    start: int
    goal: int
    condition: str = "custom"
    seed: int | None = None
    attempts: int = 1      # 도달 가능한 지도가 나올 때까지 뽑은 횟수
    meta: dict = field(default_factory=dict)

    @property
    def size(self) -> int:
        return self.width * self.height

    def xy(self, i: int) -> tuple[int, int]:
        return i % self.width, i // self.width

    def index(self, x: int, y: int) -> int:
        return y * self.width + x

    def neighbors(self, i: int):
        """벽이 아닌 이웃을 위, 아래, 왼쪽, 오른쪽 순서로 돌려준다."""
        w, h = self.width, self.height
        x, y = i % w, i // w
        for dx, dy in DIRECTIONS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                j = ny * w + nx
                if self.cost[j] != INF:
                    yield j

    def manhattan(self, i: int) -> int:
        """칸 i에서 목표까지의 맨해튼 거리 (A*의 h)."""
        w = self.width
        return abs(i % w - self.goal % w) + abs(i // w - self.goal // w)

    def path_cost(self, path: list) -> int:
        """경로의 비용 합. 시작 칸은 세지 않는다."""
        return sum(self.cost[i] for i in path[1:])

    def to_text(self) -> str:
        """디버깅용 문자열 지도. S 시작, G 목표, # 벽, m 진흙, . 잔디"""
        rows = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                i = self.index(x, y)
                if i == self.start:
                    row.append("S")
                elif i == self.goal:
                    row.append("G")
                elif self.cost[i] == INF:
                    row.append("#")
                elif self.cost[i] > 1:
                    row.append("m")
                else:
                    row.append(".")
            rows.append("".join(row))
        return "\n".join(rows)


def from_text(rows: list, mud_cost: int = DEFAULT_MUD_COST) -> Grid:
    """문자열 지도로 Grid를 만든다. 테스트와 예시용.

    S 시작, G 목표, # 벽, m 진흙(mud_cost), 숫자 1~9는 그 비용, 나머지는 잔디(1).
    """
    height, width = len(rows), len(rows[0])
    cost, start, goal = [], None, None
    for y, row in enumerate(rows):
        assert len(row) == width, "모든 줄의 길이가 같아야 합니다"
        for x, ch in enumerate(row):
            i = y * width + x
            if ch == "S":
                start = i
            elif ch == "G":
                goal = i
            if ch == "#":
                cost.append(INF)
            elif ch == "m":
                cost.append(mud_cost)
            elif ch.isdigit():
                cost.append(int(ch))
            else:
                cost.append(1)
    assert start is not None and goal is not None, "S와 G가 필요합니다"
    return Grid(width, height, cost, start, goal)


def is_reachable(grid: Grid) -> bool:
    """BFS로 시작에서 목표까지 갈 수 있는지 확인한다."""
    seen = [False] * grid.size
    seen[grid.start] = True
    queue = deque([grid.start])
    while queue:
        c = queue.popleft()
        if c == grid.goal:
            return True
        for nb in grid.neighbors(c):
            if not seen[nb]:
                seen[nb] = True
                queue.append(nb)
    return False


def count_of(n_cells: int, pct: int) -> int:
    """전체 칸의 pct%를 반올림한 개수 (정수 계산으로 부동소수 오차를 피함)."""
    return (n_cells * pct + 50) // 100


def make_grid(n: int, condition: str, seed: int,
              mud_cost: int = DEFAULT_MUD_COST, max_attempts: int = 10_000) -> Grid:
    """n×n 지도를 만든다. 시작 (0, 0), 목표 (n-1, n-1).

    같은 (n, condition, seed, mud_cost)이면 어느 컴퓨터에서든 같은 지도가 나온다.
    """
    if condition not in CONDITIONS:
        raise ValueError(f"알 수 없는 조건: {condition}")
    spec = CONDITIONS[condition]
    n_cells = n * n
    start, goal = 0, n_cells - 1
    n_wall = count_of(n_cells, spec["wall_pct"])
    n_mud = count_of(n_cells, spec["mud_pct"])
    candidates = [i for i in range(n_cells) if i not in (start, goal)]
    if n_wall + n_mud > len(candidates):
        raise ValueError("장애물과 진흙이 칸 수보다 많습니다")

    rng = random.Random(seed)
    for attempt in range(1, max_attempts + 1):
        picked = rng.sample(candidates, n_wall + n_mud)
        cost = [1] * n_cells
        for i in picked[:n_wall]:
            cost[i] = INF
        for i in picked[n_wall:]:
            cost[i] = mud_cost
        grid = Grid(n, n, cost, start, goal, condition=condition,
                    seed=seed, attempts=attempt,
                    meta={"n_wall": n_wall, "n_mud": n_mud, "mud_cost": mud_cost})
        if is_reachable(grid):
            return grid
    raise RuntimeError(f"{max_attempts}번 안에 도달 가능한 지도를 만들지 못했습니다")

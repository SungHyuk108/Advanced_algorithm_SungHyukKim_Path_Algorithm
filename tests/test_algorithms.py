"""정답을 손으로(또는 실험실 페이지로) 확인할 수 있는 지도에서 결과를 검사한다.

실행: 저장소 맨 위 폴더에서  python -m unittest -v
"""
import random
import unittest

from src.algorithms import astar, bfs, dijkstra
from src.grid import CONDITIONS, INF, Grid, count_of, from_text, is_reachable, make_grid
from src.validate import cross_check


def run_all(grid):
    return {
        "bfs": bfs(grid),
        "dijkstra": dijkstra(grid),
        "astar": astar(grid, tie="fifo"),
        "astar_large_g": astar(grid, tie="large_g"),
    }


def reference_cost(grid):
    """검사용 정답: 값이 더 이상 줄지 않을 때까지 모든 칸을 반복해서 고친다 (느리지만 단순)."""
    d = [INF] * grid.size
    d[grid.start] = 0
    changed = True
    while changed:
        changed = False
        for i in range(grid.size):
            if d[i] == INF:
                continue
            for nb in grid.neighbors(i):
                if d[i] + grid.cost[nb] < d[nb]:
                    d[nb] = d[i] + grid.cost[nb]
                    changed = True
    return d[grid.goal]


class SmallExample(unittest.TestCase):
    """설명에 쓴 5×3 예시. 진흙 띠를 가로지르면 4칸·비용 16, 돌아가면 6칸·비용 6."""

    def setUp(self):
        self.grid = from_text([".....", "SmmmG", "....."], mud_cost=5)
        self.r = run_all(self.grid)

    def test_bfs_takes_fewest_cells(self):
        b = self.r["bfs"]
        self.assertEqual((b.steps, b.cost, b.expanded), (4, 16, 13))

    def test_dijkstra_takes_cheapest(self):
        d = self.r["dijkstra"]
        self.assertEqual((d.steps, d.cost, d.expanded, d.updates), (6, 6, 13, 0))

    def test_astar_tie_breaking(self):
        self.assertEqual((self.r["astar"].cost, self.r["astar"].expanded), (6, 12))
        self.assertEqual((self.r["astar_large_g"].cost, self.r["astar_large_g"].expanded), (6, 7))

    def test_cross_check(self):
        cross_check(self.grid, self.r)


class TwoByTwo(unittest.TestCase):
    """대화에서 나온 2×2 예시: 비용이 도착 칸에 붙어 있으면 다익스트라는 갱신하지 않는다."""

    def make(self, up, right):
        # 위 줄: (0,0)=up, (1,0)=G(비용 3) / 아래 줄: (0,1)=S, (1,1)=right
        g = from_text([f"{up}G", f"S{right}"])
        g.cost[g.goal] = 3
        return g

    def test_equal_branches(self):
        d = dijkstra(self.make(2, 2))
        self.assertEqual((d.cost, d.updates), (5, 0))

    def test_unequal_branches(self):
        d = dijkstra(self.make(2, 4))
        self.assertEqual((d.cost, d.updates), (5, 0))


class LabPagePresets(unittest.TestCase):
    """경로 탐색 실험실 페이지(11×7)와 같은 수치가 나오는지."""
    MAP_A = ["..........."] * 7
    MAP_C = ["...........", "....mmm....", "....mmm....", "....mmm....",
             "....mmm....", "....mmm....", "..........."]

    def build(self, rows, ends, mud_cost=5):
        rows = [list(r) for r in rows]
        (sx, sy), (gx, gy) = ends
        rows[sy][sx], rows[gy][gx] = "S", "G"
        return from_text(["".join(r) for r in rows], mud_cost=mud_cost)

    def test_map_c_middle(self):
        r = run_all(self.build(self.MAP_C, ((0, 3), (10, 3))))
        self.assertEqual((r["bfs"].expanded, r["bfs"].cost, r["bfs"].steps), (65, 22, 10))
        self.assertEqual((r["dijkstra"].expanded, r["dijkstra"].cost, r["dijkstra"].steps), (74, 16, 16))
        self.assertEqual((r["astar"].expanded, r["astar"].cost), (65, 16))
        self.assertEqual((r["astar_large_g"].expanded, r["astar_large_g"].cost), (34, 16))

    def test_map_a_corner_tie_problem(self):
        r = run_all(self.build(self.MAP_A, ((0, 0), (10, 6))))
        self.assertEqual(r["bfs"].expanded, 77)
        self.assertEqual(r["astar"].expanded, 77)        # 모든 칸의 f가 같아 BFS처럼 퍼짐
        self.assertEqual(r["astar_large_g"].expanded, 17)

    def test_updates_only_in_astar(self):
        r = run_all(self.build(self.MAP_C, ((0, 3), (10, 3)), mud_cost=2))
        self.assertEqual(r["dijkstra"].updates, 0)
        self.assertEqual(r["astar"].updates, 4)


class CornerToCorner(unittest.TestCase):
    def test_empty_25(self):
        g = make_grid(25, "empty", seed=0)
        self.assertEqual(astar(g, tie="fifo").expanded, 625)
        self.assertEqual(astar(g, tie="large_g").expanded, 49)
        self.assertEqual(bfs(g).expanded, 625)


class RandomCrossCheck(unittest.TestCase):
    """무작위 지도 300장에서 독립 정답과 비교하고 이론상 관계를 확인한다."""

    def test_random_grids(self):
        rng = random.Random(2026)
        tested = 0
        for _ in range(400):
            w, h = rng.randint(2, 14), rng.randint(2, 12)
            cost = []
            for _ in range(w * h):
                u = rng.random()
                cost.append(INF if u < 0.2 else (rng.randint(2, 9) if u < 0.5 else 1))
            start, goal = rng.sample(range(w * h), 2)
            cost[start] = cost[goal] = 1
            grid = Grid(w, h, cost, start, goal)
            if not is_reachable(grid):
                continue
            tested += 1
            r = run_all(grid)
            cross_check(grid, r)
            self.assertEqual(r["dijkstra"].cost, reference_cost(grid))
            self.assertEqual(r["dijkstra"].updates, 0)   # 비용이 도착 칸에 붙어 있으면 갱신 없음
            for name in ("astar", "astar_large_g"):
                self.assertLessEqual(r[name].expanded, r["dijkstra"].expanded)
        self.assertGreater(tested, 200)


class MapGenerator(unittest.TestCase):
    def test_same_seed_same_map(self):
        a = make_grid(30, "walls_mud", seed=7)
        b = make_grid(30, "walls_mud", seed=7)
        self.assertEqual(a.cost, b.cost)
        self.assertEqual(a.attempts, b.attempts)

    def test_exact_counts_and_free_ends(self):
        for n in (25, 50):
            for cond, spec in CONDITIONS.items():
                g = make_grid(n, cond, seed=3)
                walls = sum(1 for c in g.cost if c == INF)
                mud = sum(1 for c in g.cost if c not in (1, INF))
                self.assertEqual(walls, count_of(n * n, spec["wall_pct"]))
                self.assertEqual(mud, count_of(n * n, spec["mud_pct"]))
                self.assertEqual(g.cost[g.start], 1)
                self.assertEqual(g.cost[g.goal], 1)
                self.assertTrue(is_reachable(g))


if __name__ == "__main__":
    unittest.main()

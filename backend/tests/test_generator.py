import pytest
from puzzle.generator import _generate_solution, _count_solutions, generate_puzzle


def check_solution(grid, size):
    """Vérifie les contraintes de base d'une grille complète."""
    for r, row in enumerate(grid):
        assert row.count("S") == size // 2, f"Ligne {r} déséquilibrée : {row}"
        assert row.count("L") == size // 2, f"Ligne {r} déséquilibrée : {row}"

    for c in range(size):
        col = [grid[r][c] for r in range(size)]
        assert col.count("S") == size // 2, f"Colonne {c} déséquilibrée : {col}"
        assert col.count("L") == size // 2, f"Colonne {c} déséquilibrée : {col}"

    for r in range(size):
        for c in range(size - 2):
            assert not (grid[r][c] == grid[r][c + 1] == grid[r][c + 2]), \
                f"3 consécutifs ligne {r}, col {c}-{c+2}"

    for c in range(size):
        for r in range(size - 2):
            assert not (grid[r][c] == grid[r + 1][c] == grid[r + 2][c]), \
                f"3 consécutifs colonne {c}, ligne {r}-{r+2}"


@pytest.mark.parametrize("size", [4, 6])
def test_generate_solution_valid(size):
    grid = _generate_solution(size)
    assert grid is not None
    check_solution(grid, size)


@pytest.mark.parametrize("_", range(10))
def test_generate_solution_repeated(_):
    grid = _generate_solution(4)
    assert grid is not None
    check_solution(grid, 4)


def test_generate_solution_with_clues():
    clues = [
        {"cell1": [0, 0], "cell2": [0, 1], "type": "equal"},
        {"cell1": [1, 0], "cell2": [2, 0], "type": "opposite"},
    ]
    grid = _generate_solution(4, clues)
    assert grid is not None
    assert grid[0][0] == grid[0][1], "(0,0) et (0,1) doivent être égaux"
    assert grid[1][0] != grid[2][0], "(1,0) et (2,0) doivent être opposés"
    check_solution(grid, 4)


def test_count_solutions_complete_grid():
    grid = _generate_solution(4)
    assert grid is not None
    assert _count_solutions(grid, [], 4, limit=2) == 1


def test_count_solutions_empty_grid():
    empty = [[None] * 4 for _ in range(4)]
    assert _count_solutions(empty, [], 4, limit=2) >= 2


@pytest.mark.parametrize("size,min_visible,max_clues", [
    (4, None, None),
    (4, 6, 4),
    (4, 4, 8),
    (6, None, None),
])
def test_generate_puzzle_unique(size, min_visible, max_clues):
    kwargs = {}
    if min_visible is not None:
        kwargs["min_visible"] = min_visible
    if max_clues is not None:
        kwargs["max_clues"] = max_clues

    result = generate_puzzle(size, **kwargs)
    assert "size" in result
    assert "puzzle" in result
    assert "clues" in result
    assert result["size"] == size
    assert len(result["puzzle"]) == size
    assert all(len(row) == size for row in result["puzzle"])

    n = _count_solutions(result["puzzle"], result["clues"], size, limit=2)
    assert n == 1, f"Le puzzle doit avoir exactement 1 solution, trouvé {n}"


def test_generate_puzzle_min_visible():
    result = generate_puzzle(4, min_visible=8)
    visible = sum(v is not None for row in result["puzzle"] for v in row)
    assert visible >= 8


def test_generate_puzzle_max_clues():
    result = generate_puzzle(4, max_clues=3)
    assert len(result["clues"]) <= 3

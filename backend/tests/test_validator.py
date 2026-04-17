import pytest
from puzzle.generator import _generate_solution
from puzzle.validator import validate


@pytest.fixture
def solution_4x4():
    grid = _generate_solution(4)
    assert grid is not None
    return grid


def test_final_valid(solution_4x4):
    result = validate(solution_4x4, [], 4, partial=False)
    assert result == {"valid": True, "complete": True, "error_cells": []}


def test_final_wrong_balance():
    grid = [
        ["S", "S", "S", "L"],
        ["L", "L", "S", "S"],
        ["S", "L", "L", "S"],
        ["L", "S", "L", "L"],
    ]
    result = validate(grid, [], 4, partial=False)
    assert result["valid"] is False
    assert result["complete"] is True
    # Ligne 0 déséquilibrée (3S 1L) et colonne 2 déséquilibrée (3S 1L)
    assert [0, 0] in result["error_cells"]
    assert [0, 2] in result["error_cells"]


def test_final_three_consecutive_horizontal():
    grid = [
        ["S", "S", "L", "L"],
        ["L", "L", "S", "S"],
        ["S", "S", "L", "L"],
        ["L", "L", "S", "S"],
    ]
    assert validate(grid, [], 4, partial=False) == {"valid": True, "complete": True, "error_cells": []}

    bad = [row[:] for row in grid]
    bad[0] = ["S", "S", "S", "L"]
    bad[1] = ["L", "L", "L", "S"]
    result = validate(bad, [], 4, partial=False)
    assert result["valid"] is False
    # Les trois cellules du triplet doivent être en erreur
    assert [0, 0] in result["error_cells"]
    assert [0, 1] in result["error_cells"]
    assert [0, 2] in result["error_cells"]


def test_final_three_consecutive_vertical():
    grid = [
        ["S", "L", "S", "L"],
        ["S", "L", "L", "S"],
        ["S", "S", "L", "L"],
        ["L", "S", "L", "S"],  # col 0 : S S S L → triplet
    ]
    result = validate(grid, [], 4, partial=False)
    assert result["valid"] is False
    assert [0, 0] in result["error_cells"]
    assert [1, 0] in result["error_cells"]
    assert [2, 0] in result["error_cells"]


def test_partial_no_contradiction():
    grid = [
        ["S", None, None, None],
        [None, None, None, None],
        [None, None, None, None],
        [None, None, None, None],
    ]
    assert validate(grid, [], 4, partial=True) == {"valid": True, "complete": False, "error_cells": []}


def test_partial_three_consecutive():
    grid = [
        ["S", "S", "S", None],
        [None, None, None, None],
        [None, None, None, None],
        [None, None, None, None],
    ]
    result = validate(grid, [], 4, partial=True)
    assert result["valid"] is False
    assert result["complete"] is False
    assert [0, 0] in result["error_cells"]
    assert [0, 1] in result["error_cells"]
    assert [0, 2] in result["error_cells"]


def test_partial_false_on_incomplete_grid():
    grid = [
        ["S", None, None, None],
        [None, None, None, None],
        [None, None, None, None],
        [None, None, None, None],
    ]
    assert validate(grid, [], 4, partial=False) == {"valid": False, "complete": False, "error_cells": []}


@pytest.mark.parametrize("v1,v2,clue_type,expected_valid,expect_error", [
    ("S", "S", "equal",    True,  False),
    ("S", "L", "equal",    False, True),
    ("S", "L", "opposite", True,  False),
    ("S", "S", "opposite", False, True),
])
def test_clue_constraints(v1, v2, clue_type, expected_valid, expect_error):
    clues = [{"cell1": [0, 0], "cell2": [0, 1], "type": clue_type}]
    grid = [
        [v1, v2, None, None],
        [None, None, None, None],
        [None, None, None, None],
        [None, None, None, None],
    ]
    result = validate(grid, clues, 4, partial=True)
    assert result["valid"] is expected_valid
    assert result["complete"] is False
    if expect_error:
        assert [0, 0] in result["error_cells"]
        assert [0, 1] in result["error_cells"]
    else:
        assert result["error_cells"] == []


def test_clue_skipped_when_cell_empty():
    clues = [{"cell1": [0, 0], "cell2": [0, 1], "type": "equal"}]
    grid = [
        ["S", None, None, None],
        [None, None, None, None],
        [None, None, None, None],
        [None, None, None, None],
    ]
    assert validate(grid, clues, 4, partial=True) == {"valid": True, "complete": False, "error_cells": []}


def test_error_cells_multiple_rules():
    """Une case peut être en erreur pour plusieurs raisons à la fois."""
    clues = [{"cell1": [0, 0], "cell2": [0, 1], "type": "opposite"}]
    grid = [
        ["S", "S", "S", None],  # triplet ET clue opposite violée sur (0,0)-(0,1)
        [None, None, None, None],
        [None, None, None, None],
        [None, None, None, None],
    ]
    result = validate(grid, clues, 4, partial=True)
    assert result["valid"] is False
    assert [0, 0] in result["error_cells"]
    assert [0, 1] in result["error_cells"]
    assert [0, 2] in result["error_cells"]

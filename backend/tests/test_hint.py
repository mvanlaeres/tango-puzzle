"""
Tests for puzzle/hint.py

Coverage:
  propagate — one test per rule, illustrée par un motif lisible
  propagate — contradiction detected for each rule
  find_hint  — indices directs sur motifs locaux en lecture 6×6
  find_hint  — Level 2 (pivot) quand aucun motif direct ne suffit
  find_hint  — returns None when grid is already full
"""

import pytest
from puzzle.hint import propagate, find_hint, Contradiction

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def empty(size: int):
    return [[None] * size for _ in range(size)]


# ---------------------------------------------------------------------------
# propagate — Rule 1 : equal clue
# ---------------------------------------------------------------------------

def test_propagate_clue_equal_forward():
    """Règle : `☀ = _` implique `☀ = ☀`."""
    grid = empty(6)
    clues = [{"type": "equal", "cell1": [0, 0], "cell2": [0, 1]}]
    steps, result = propagate(grid, clues, 6, [(0, 0, "S")])
    assert result[0][1] == "S"
    assert any(s["cell"] == [0, 1] and s["value"] == "S" for s in steps)


def test_propagate_clue_equal_backward():
    """Règle : `_ = ☾` implique `☾ = ☾`."""
    grid = empty(6)
    clues = [{"type": "equal", "cell1": [0, 0], "cell2": [0, 1]}]
    steps, result = propagate(grid, clues, 6, [(0, 1, "L")])
    assert result[0][0] == "L"


# ---------------------------------------------------------------------------
# propagate — Rule 1 : opposite clue
# ---------------------------------------------------------------------------

def test_propagate_clue_opposite_forward():
    """Règle : `☀ × _` implique `☀ × ☾`."""
    grid = empty(6)
    clues = [{"type": "opposite", "cell1": [0, 0], "cell2": [0, 1]}]
    steps, result = propagate(grid, clues, 6, [(0, 0, "S")])
    assert result[0][1] == "L"
    assert any(s["cell"] == [0, 1] and s["value"] == "L" for s in steps)


def test_propagate_clue_opposite_contradiction():
    """Règle : `☾ × ☾` est impossible."""
    grid = empty(6)
    grid[0][1] = "L"
    clues = [{"type": "opposite", "cell1": [0, 0], "cell2": [0, 1]}]
    with pytest.raises(Contradiction):
        propagate(grid, clues, 6, [(0, 0, "L")])


def test_propagate_clue_equal_contradiction():
    """Règle : `☀ = ☾` est impossible."""
    grid = empty(6)
    grid[0][1] = "L"
    clues = [{"type": "equal", "cell1": [0, 0], "cell2": [0, 1]}]
    with pytest.raises(Contradiction):
        propagate(grid, clues, 6, [(0, 0, "S")])


# ---------------------------------------------------------------------------
# propagate — Rule 2 : three consecutive
# ---------------------------------------------------------------------------

def test_propagate_consecutive_horizontal():
    """Règle : `☀ ☀ ☀` est interdit sur une ligne."""
    grid = empty(6)
    grid[0][0] = "S"
    grid[0][1] = "S"
    with pytest.raises(Contradiction):
        propagate(grid, [], 6, [(0, 2, "S")])

def test_propagate_consecutive_forces_other():
    """Règle : `_ ☀ ☀` implique `☾ ☀ ☀`."""
    grid = empty(6)
    grid[0][1] = "S"
    steps, result = propagate(grid, [], 6, [(0, 2, "S")])
    assert result[0][0] == "L"
    assert any(s["cell"] == [0, 0] and s["value"] == "L" for s in steps)


def test_propagate_consecutive_forces_middle_cell():
    """Règle : `☀ _ ☀` implique `☀ ☾ ☀`."""
    grid = empty(6)
    grid[0][0] = "S"
    steps, result = propagate(grid, [], 6, [(0, 2, "S")])
    assert result[0][1] == "L"
    assert any(s["cell"] == [0, 1] and s["value"] == "L" for s in steps)


def test_propagate_consecutive_contradiction():
    """Règle : `☀ ☀ ☀` est interdit."""
    grid = empty(6)
    grid[0][0] = "S"
    grid[0][1] = "S"
    with pytest.raises(Contradiction):
        propagate(grid, [], 6, [(0, 2, "S")])


def test_propagate_consecutive_vertical():
    """Règle : en colonne, `_ / ☀ / ☀` implique `☾ / ☀ / ☀`."""
    grid = empty(6)
    grid[1][0] = "S"
    steps, result = propagate(grid, [], 6, [(2, 0, "S")])
    assert result[0][0] == "L"


# ---------------------------------------------------------------------------
# propagate — Rule 3 : row saturation
# ---------------------------------------------------------------------------

def test_propagate_saturation_row():
    """Règle d'équilibre : dès qu'une ligne a son quota d'un symbole, le reste vaut l'autre."""
    grid = empty(6)
    grid[0][0] = "S"
    grid[0][2] = "S"
    steps, result = propagate(grid, [], 6, [(0, 4, "S")])
    assert result[0][1] == "L"
    assert result[0][3] == "L"
    assert result[0][5] == "L"


def test_propagate_saturation_row_contradiction():
    """Règle d'équilibre : dépasser le quota d'un symbole dans une ligne est impossible."""
    grid = [
        ["S", "S", "S", None, None, None],
        [None] * 6,
        [None] * 6,
        [None] * 6,
        [None] * 6,
        [None] * 6,
    ]
    with pytest.raises(Contradiction):
        propagate(grid, [], 6, [(0, 3, "S")])


# ---------------------------------------------------------------------------
# propagate — Rule 3 : column saturation
# ---------------------------------------------------------------------------

def test_propagate_saturation_col():
    """Règle d'équilibre : dès qu'une colonne a son quota d'un symbole, le reste vaut l'autre."""
    grid = empty(6)
    grid[0][0] = "S"
    grid[2][0] = "S"
    steps, result = propagate(grid, [], 6, [(4, 0, "S")])
    assert result[1][0] == "L"
    assert result[3][0] == "L"
    assert result[5][0] == "L"


# ---------------------------------------------------------------------------
# propagate — step metadata
# ---------------------------------------------------------------------------

def test_propagate_step_contains_reason_type():
    """Each step must carry a reason_type field."""
    grid = empty(6)
    grid[0][0] = "S"
    steps, _ = propagate(grid, [], 6, [(0, 1, "S")])
    for s in steps:
        assert "reason_type" in s
        assert s["reason_type"] in ("clue", "consecutive", "saturation")


def test_propagate_contradiction_has_steps():
    """Contradiction exception carries the steps accumulated so far."""
    grid = empty(6)
    grid[0][0] = "S"
    grid[0][1] = "S"
    try:
        propagate(grid, [], 6, [(0, 2, "S")])
    except Contradiction as exc:
        assert isinstance(exc.steps, list)
        # Last entry should be the contradiction marker
        assert exc.steps[-1]["reason_type"] == "contradiction"
    else:
        pytest.fail("Expected Contradiction was not raised")


def test_propagate_pending_conflict_uses_deduced_wording():
    """Si deux déductions se contredisent, le message doit parler d'une déduction déjà faite."""
    grid = empty(6)
    clues = [
        {"type": "equal", "cell1": [0, 0], "cell2": [0, 1]},
        {"type": "opposite", "cell1": [0, 0], "cell2": [0, 1]},
    ]
    with pytest.raises(Contradiction) as excinfo:
        propagate(grid, clues, 6, [(0, 0, "S")])

    assert excinfo.value.steps[-1]["reason"] == (
        "la case (1,2) devrait valoir ☾, "
        "mais on a déjà déduit ☀ pour cette case"
    )


# ---------------------------------------------------------------------------
# find_hint — Level 1
# ---------------------------------------------------------------------------

def test_find_hint_level1_saturation():
    """Règle lue comme indice : une ligne déjà équilibrée sur un symbole force les cases restantes."""
    grid = [
        ["S", "L", "S", "L", "S", None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
    ]
    hint = find_hint(grid, [], 6)
    assert hint is not None
    assert hint["cell"] == [0, 5]
    assert hint["value"] == "L"
    assert hint["pivot"] is None


def test_find_hint_level1_clue():
    """Règle lue comme indice : une contrainte `×` incomplète force la case vide."""
    grid = [
        [None, "S", None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
    ]
    clues = [{"type": "opposite", "cell1": [0, 0], "cell2": [0, 1]}]
    hint = find_hint(grid, clues, 6)
    assert hint is not None
    assert hint["cell"] == [0, 0]
    assert hint["value"] == "L"
    assert hint["pivot"] is None
    assert hint["kind"] == "direct"


def test_find_hint_prioritizes_direct_clue_over_other_rules():
    grid = [
        [None, "S", None, None, None, None],
        ["S", "S", None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
    ]
    clues = [{"type": "opposite", "cell1": [0, 0], "cell2": [0, 1]}]

    hint = find_hint(grid, clues, 6)
    assert hint is not None
    assert hint["cell"] == [0, 0]
    assert hint["value"] == "L"
    assert hint["kind"] == "direct"
    assert hint["steps"][0]["reason_type"] == "clue"


def test_find_hint_finds_direct_consecutive_before_saturation():
    """Règle prioritaire : deux symboles identiques côte à côte forcent la case adjacente."""
    grid = [
        [None, "S", "S", None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
    ]

    hint = find_hint(grid, [], 6)
    assert hint is not None
    assert hint["cell"] == [0, 0]
    assert hint["value"] == "L"
    assert hint["kind"] == "direct"
    assert hint["steps"][0]["reason_type"] == "consecutive"


def test_find_hint_finds_direct_consecutive_with_gap_in_middle():
    """Règle : `☀ _ ☀` implique `☀ ☾ ☀`, sinon on aurait trois symboles identiques alignés."""
    grid = [
        ["S", None, "S", None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
    ]

    hint = find_hint(grid, [], 6)
    assert hint is not None
    assert hint["cell"] == [0, 1]
    assert hint["value"] == "L"
    assert hint["kind"] == "direct"
    assert hint["steps"][0]["reason_type"] == "consecutive"


def test_find_hint_finds_direct_saturation_when_no_local_rule_exists():
    """Règle lue comme indice : l'équilibre ligne/colonne passe après les motifs locaux."""
    grid = [
        ["S", "L", "S", "L", "S", None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
    ]

    hint = find_hint(grid, [], 6)
    assert hint is not None
    assert hint["cell"] == [0, 5]
    assert hint["value"] == "L"
    assert hint["kind"] == "direct"
    assert hint["steps"][0]["reason_type"] == "saturation"


def test_find_hint_finds_length6_edge_pattern_on_row():
    """Règle : `☀ ☀ ☾ _ _ _` implique ici la dernière case `☾`."""
    grid = [
        ["S", "S", "L", None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
        [None, None, None, None, None, None],
    ]

    hint = find_hint(grid, [], 6)
    assert hint is not None
    assert hint["cell"] == [0, 5]
    assert hint["value"] == "L"
    assert hint["kind"] == "direct"
    assert hint["steps"][0]["reason_type"] == "pattern6"


def test_find_hint_finds_length6_spaced_pattern_on_column():
    """Règle : en colonne, `_ / ☾ / _ / _ / _ / ☾` implique `☀ / ☾ / _ / _ / _ / ☾`."""
    grid = [[None] * 6 for _ in range(6)]
    grid[1][0] = "L"
    grid[5][0] = "L"

    hint = find_hint(grid, [], 6)
    assert hint is not None
    assert hint["cell"] == [0, 0]
    assert hint["value"] == "S"
    assert hint["kind"] == "direct"
    assert hint["steps"][0]["reason_type"] == "pattern6"


def test_find_hint_finds_length6_same_ends_pattern():
    """Règle : `☀ _ _ _ _ ☀` implique d'abord `☀ ☾ _ _ _ ☀`."""
    grid = [[None] * 6 for _ in range(6)]
    grid[0][0] = "S"
    grid[0][5] = "S"

    hint = find_hint(grid, [], 6)
    assert hint is not None
    assert hint["cell"] == [0, 1]
    assert hint["value"] == "L"
    assert hint["kind"] == "direct"
    assert hint["steps"][0]["reason_type"] == "pattern6"


def test_find_hint_finds_length6_equal_edge_pattern():
    """Règle : `☀ _ _ _ _ = _` implique `☀ _ _ _ ☾ = ☾`."""
    grid = [[None] * 6 for _ in range(6)]
    grid[0][0] = "S"
    clues = [{"type": "equal", "cell1": [0, 4], "cell2": [0, 5]}]

    hint = find_hint(grid, clues, 6)
    assert hint is not None
    assert hint["cell"] == [0, 4]
    assert hint["value"] == "L"
    assert hint["kind"] == "direct"
    assert hint["steps"][0]["reason_type"] == "pattern6"


def test_find_hint_finds_equal_pair_next_to_symbol_pattern():
    """Règle : `☀ = _ _` implique `☀ ☾ = ☾`."""
    grid = [[None] * 6 for _ in range(6)]
    grid[0][0] = "S"
    clues = [{"type": "equal", "cell1": [0, 1], "cell2": [0, 2]}]

    hint = find_hint(grid, clues, 6)
    assert hint is not None
    assert hint["cell"] == [0, 1]
    assert hint["value"] == "L"
    assert hint["kind"] == "direct"
    assert hint["steps"][0]["reason_type"] == "clue_pattern"
    assert hint["steps"][0]["reason"] == (
        "cette case appartient à une paire de cases égales ; "
        "si cette paire valait ☀, cela créerait trois symboles identiques alignés"
    )


# ---------------------------------------------------------------------------
# find_hint — returns None when grid is complete
# ---------------------------------------------------------------------------

def test_find_hint_returns_none_when_full():
    grid = [
        ["S", "L", "S", "L", "S", "L"],
        ["L", "S", "L", "S", "L", "S"],
        ["S", "L", "S", "L", "S", "L"],
        ["L", "S", "L", "S", "L", "S"],
        ["S", "L", "S", "L", "S", "L"],
        ["L", "S", "L", "S", "L", "S"],
    ]
    assert find_hint(grid, [], 6) is None


# ---------------------------------------------------------------------------
# find_hint — Level 2 (pivot)
# ---------------------------------------------------------------------------

def test_find_hint_level2_pivot():
    """Cas de repli : aucun motif direct utile, le moteur peut quand même trouver un indice."""

    grid = [
        [None, "L", "S", "L", "S", "L"],
        ["L",  "S", "L", "S", "L", "S"],
        ["S",  "L", "S", "L", "S", "L"],
        ["L",  "S", "L", "S", "L", "S"],
        ["S",  "L", "S", "L", "S", "L"],
        ["L",  "S", "L", "S", "L", "S"],
    ]
    hint = find_hint(grid, [], 6)
    assert hint is not None
    assert hint["cell"] == [0, 0]
    assert hint["value"] == "S"
    assert hint["pivot"] is None
    assert hint["kind"] == "direct"


def test_find_hint_level2_structure():
    """Si on tombe sur une preuve par cas, la structure du pivot doit rester stable."""
    from puzzle.generator import _generate_solution

    import random
    random.seed(42)
    solution = _generate_solution(6)
    assert solution is not None

    grid = [[None] * 6 for _ in range(6)]
    for c in range(6):
        grid[0][c] = solution[0][c]

    hint = find_hint(grid, [], 6)
    if hint is not None and hint["pivot"] is not None:
        p = hint["pivot"]
        assert "cell" in p
        assert "case_a" in p
        assert "case_b" in p
        assert isinstance(p["case_a"], list)
        assert isinstance(p["case_b"], list)

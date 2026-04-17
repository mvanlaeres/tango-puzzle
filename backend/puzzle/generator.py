import random

Clues = list[dict]
Grid = list[list[str | None]]


def _check_placement(grid: Grid, row: int, col: int, value: str, size: int, clues: Clues) -> bool:
    """Return True if placing `value` at (row, col) violates no constraint."""

    # 1. At most size//2 of each symbol per row
    if sum(1 for c in range(size) if grid[row][c] == value) >= size // 2:
        return False

    # 2. At most size//2 of each symbol per column
    if sum(1 for r in range(size) if grid[r][col] == value) >= size // 2:
        return False

    # 3. No 3 consecutive identical symbols horizontally
    if col >= 2 and grid[row][col - 1] == grid[row][col - 2] == value:
        return False

    # 4. No 3 consecutive identical symbols vertically
    if row >= 2 and grid[row - 1][col] == grid[row - 2][col] == value:
        return False

    # 5. Clue constraints — only checked when both cells are filled
    for clue in clues:
        r1, c1 = clue["cell1"]
        r2, c2 = clue["cell2"]

        if (r1, c1) == (row, col):
            other = grid[r2][c2]
        elif (r2, c2) == (row, col):
            other = grid[r1][c1]
        else:
            continue

        if other is None:
            continue

        if clue["type"] == "equal" and value != other:
            return False
        if clue["type"] == "opposite" and value == other:
            return False

    return True


def _generate_solution(size: int, clues: Clues | None = None) -> Grid | None:
    """
    Return a fully filled grid satisfying all constraints, or None if impossible.
    Uses backtracking with constraint checking at each placement.
    """
    if clues is None:
        clues = []

    grid: Grid = [[None] * size for _ in range(size)]
    symbols = ["S", "L"]

    def backtrack(pos: int) -> bool:
        if pos == size * size:
            return True

        row, col = divmod(pos, size)
        candidates = symbols[:]
        random.shuffle(candidates)

        for value in candidates:
            if _check_placement(grid, row, col, value, size, clues):
                grid[row][col] = value
                if backtrack(pos + 1):
                    return True
                grid[row][col] = None

        return False

    return grid if backtrack(0) else None


def _count_solutions(grid: Grid, clues: Clues, size: int, limit: int = 2) -> int:
    """Count solutions up to `limit`. Stops early once limit is reached."""
    grid = [row[:] for row in grid]
    count = [0]

    def backtrack(pos: int) -> None:
        if count[0] >= limit:
            return
        if pos == size * size:
            count[0] += 1
            return

        row, col = divmod(pos, size)
        if grid[row][col] is not None:
            backtrack(pos + 1)
            return

        for value in ["S", "L"]:
            if _check_placement(grid, row, col, value, size, clues):
                grid[row][col] = value
                backtrack(pos + 1)
                grid[row][col] = None

    backtrack(0)
    return count[0]


def _all_adjacent_pairs(size: int) -> list[tuple[list[int], list[int]]]:
    """Return all adjacent cell pairs (cell1 always left-of or above cell2)."""
    pairs = []
    for r in range(size):
        for c in range(size):
            if c + 1 < size:
                pairs.append(([r, c], [r, c + 1]))
            if r + 1 < size:
                pairs.append(([r, c], [r + 1, c]))
    return pairs


def _make_clue(solution: Grid, cell1: list[int], cell2: list[int]) -> dict:
    r1, c1 = cell1
    r2, c2 = cell2
    return {
        "cell1": cell1,
        "cell2": cell2,
        "type": "equal" if solution[r1][c1] == solution[r2][c2] else "opposite",
    }


def generate_puzzle(size: int = 6, min_visible: int | None = None, max_clues: int | None = None) -> dict:
    """
    Generate a Tango puzzle of the given size.

    Strategy:
      1. Generate a full solution.
      2. Dig holes (no clues yet) until the puzzle is no longer uniquely solvable
         or min_visible is reached.
      3. For each remaining hole that broke uniqueness, try adding one clue that
         restores it — keeping the total number of clues <= max_clues.

    Returns {"size", "puzzle", "clues"}.
    """
    solution = _generate_solution(size)
    if solution is None:
        raise RuntimeError(f"Could not generate a solution for size {size}")

    effective_min_visible = min_visible if min_visible is not None else size * size // 3
    effective_max_clues   = max_clues   if max_clues   is not None else size + size // 2

    grid: Grid = [row[:] for row in solution]
    clues: Clues = []

    positions = list(range(size * size))
    random.shuffle(positions)

    for pos in positions:
        visible = sum(v is not None for row in grid for v in row)
        if visible <= effective_min_visible:
            break

        r, c = divmod(pos, size)
        saved = grid[r][c]
        grid[r][c] = None

        if _count_solutions(grid, clues, size, limit=2) == 1:
            continue  # still unique — keep the hole

        # Uniqueness broken: try to restore it with one new clue
        grid[r][c] = saved  # tentatively restore

        if len(clues) >= effective_max_clues:
            continue  # clue budget exhausted — leave cell visible

        candidate_pairs = _all_adjacent_pairs(size)
        random.shuffle(candidate_pairs)
        used = {(tuple(cl["cell1"]), tuple(cl["cell2"])) for cl in clues}

        added = False
        for cell1, cell2 in candidate_pairs:
            if (tuple(cell1), tuple(cell2)) in used:
                continue
            new_clue = _make_clue(solution, cell1, cell2)
            clues.append(new_clue)
            grid[r][c] = None  # try the hole again with the new clue
            if _count_solutions(grid, clues, size, limit=2) == 1:
                added = True
                break
            # Clue didn't help — remove it and restore cell
            clues.pop()
            grid[r][c] = saved

        if not added:
            grid[r][c] = saved  # no useful clue found — leave cell visible

    return {"size": size, "puzzle": grid, "clues": clues}

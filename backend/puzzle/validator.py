from puzzle.generator import Grid, Clues


def validate(grid: Grid, clues: Clues, size: int, partial: bool) -> dict:
    """
    Validate a Tango grid.

    partial=True  : only filled cells are checked (no contradiction so far)
    partial=False : grid must be complete and fully correct

    Returns {"valid": bool, "complete": bool, "error_cells": list[list[int]]}
    """
    filled = [(r, c) for r in range(size) for c in range(size) if grid[r][c] is not None]
    complete = len(filled) == size * size

    if not partial and not complete:
        return {"valid": False, "complete": False, "error_cells": []}

    error_cells: set[tuple[int, int]] = set()

    # --- Row / column balance ---
    for r in range(size):
        row = [grid[r][c] for c in range(size)]
        if None not in row or not partial:
            if row.count("S") != size // 2 or row.count("L") != size // 2:
                for c in range(size):
                    if row[c] is not None:
                        error_cells.add((r, c))

    for c in range(size):
        col = [grid[r][c] for r in range(size)]
        if None not in col or not partial:
            if col.count("S") != size // 2 or col.count("L") != size // 2:
                for r in range(size):
                    if col[r] is not None:
                        error_cells.add((r, c))

    # --- No 3 consecutive identical symbols ---
    for r in range(size):
        for c in range(size - 2):
            a, b, cc = grid[r][c], grid[r][c + 1], grid[r][c + 2]
            if a is not None and a == b == cc:
                error_cells.add((r, c))
                error_cells.add((r, c + 1))
                error_cells.add((r, c + 2))

    for c in range(size):
        for r in range(size - 2):
            a, b, cc = grid[r][c], grid[r + 1][c], grid[r + 2][c]
            if a is not None and a == b == cc:
                error_cells.add((r, c))
                error_cells.add((r + 1, c))
                error_cells.add((r + 2, c))

    # --- Clue constraints ---
    for clue in clues:
        r1, c1 = clue["cell1"]
        r2, c2 = clue["cell2"]
        v1, v2 = grid[r1][c1], grid[r2][c2]

        if v1 is None or v2 is None:
            continue

        if clue["type"] == "equal" and v1 != v2:
            error_cells.add((r1, c1))
            error_cells.add((r2, c2))
        elif clue["type"] == "opposite" and v1 == v2:
            error_cells.add((r1, c1))
            error_cells.add((r2, c2))

    return {
        "valid": len(error_cells) == 0,
        "complete": complete,
        "error_cells": [list(cell) for cell in sorted(error_cells)],
    }

from __future__ import annotations

Grid  = list[list[str | None]]
Clues = list[dict]

SYMBOLS = ["S", "L"]
OTHER   = {"S": "L", "L": "S"}
ICONS   = {"S": "☀", "L": "☾"}
NAMES   = {"S": "jaune", "L": "bleu"}


class Contradiction(Exception):
    def __init__(self, steps: list[dict]) -> None:
        self.steps = steps


def _step(
    r: int,
    c: int,
    value: str,
    reason_type: str,
    reason: str,
    premises: list[tuple[int, int]] | None = None,
) -> dict:
    return {
        "cell":        [r, c],
        "value":       value,
        "symbol":      NAMES[value],
        "reason_type": reason_type,
        "reason":      reason,
        "premises":    [list(cell) for cell in (premises or [])],
    }


def _contradiction(reason: str) -> dict:
    return {
        "cell":        None,
        "value":       None,
        "symbol":      None,
        "reason_type": "contradiction",
        "reason":      reason,
    }


def _hint(cell: tuple[int, int], value: str, steps: list[dict], kind: str, pivot: dict | None = None) -> dict:
    r, c = cell
    return {
        "cell":   [r, c],
        "value":  value,
        "symbol": NAMES[value],
        "steps":  steps,
        "pivot":  pivot,
        "kind":   kind,
    }


def _visible_step(step: dict) -> dict:
    return {k: v for k, v in step.items() if k != "premises"}


def _chain_for_step(step: dict | None, derived_steps: dict[tuple[int, int], dict]) -> list[dict]:
    if step is None:
        return []

    chain: list[dict] = []
    seen: set[tuple[tuple[int, int], str, str, str]] = set()

    def visit(cur: dict) -> None:
        for premise in cur.get("premises", []):
            parent = derived_steps.get(tuple(premise))
            if parent is not None:
                visit(parent)

        cell = tuple(cur["cell"])
        key = (cell, cur["value"], cur["reason_type"], cur["reason"])
        if key not in seen:
            seen.add(key)
            chain.append(_visible_step(cur))

    visit(step)
    return chain


def propagate(
    grid:   Grid,
    clues:  Clues,
    size:   int,
    forced: list[tuple[int, int, str]],
) -> tuple[list[dict], Grid]:
    """
    BFS from a list of (r, c, value) hypotheses.
    Works on a copy of grid — never mutates the input.
    Returns (steps, new_grid).
    Raises Contradiction(steps) if a conflict is detected.
    Initial forced cells are placed silently (they are the hypothesis).
    Only derived cells produce steps.
    """
    working = [row[:] for row in grid]
    steps: list[dict] = []
    queue: list[tuple[int, int, str]] = list(forced)
    # Track values that are queued but not yet placed, to catch conflicts early.
    pending: dict[tuple[int, int], str] = {(r, c): v for r, c, v in forced}
    causes: dict[tuple[int, int], dict | None] = {(r, c): None for r, c, _ in forced}
    derived_steps: dict[tuple[int, int], dict] = {}

    def enqueue(r: int, c: int, value: str, step: dict) -> None:
        existing_working = working[r][c]
        existing_pending = pending.get((r, c))
        existing = existing_working if existing_working is not None else existing_pending
        if existing == value:
            return  # already correct — no-op
        if existing == OTHER[value]:
            if existing_working is not None:
                reason = (
                    f"la case ({r+1},{c+1}) devrait valoir {NAMES[value]} "
                    f"mais est déjà {NAMES[OTHER[value]]}"
                )
            else:
                reason = (
                    f"la case ({r+1},{c+1}) devrait valoir {NAMES[value]}, "
                    f"mais on a déjà déduit {NAMES[OTHER[value]]} pour cette case"
                )
            raise Contradiction(_chain_for_step(step, derived_steps) + [_contradiction(
                reason
            )])
        steps.append(_visible_step(step))
        queue.append((r, c, value))
        pending[(r, c)] = value
        causes[(r, c)] = step
        derived_steps[(r, c)] = step

    while queue:
        r, c, value = queue.pop(0)

        if working[r][c] == OTHER[value]:
            raise Contradiction(_chain_for_step(causes.get((r, c)), derived_steps) + [_contradiction(
                f"la case ({r+1},{c+1}) devrait valoir {NAMES[value]} "
                f"mais est déjà {NAMES[OTHER[value]]}"
            )])
        if working[r][c] == value:
            continue

        working[r][c] = value

        # ── Règle 1 : contraintes = et × ──────────────────────────────
        for clue in clues:
            r1, c1 = clue["cell1"]
            r2, c2 = clue["cell2"]

            if (r1, c1) == (r, c):
                nr, nc = r2, c2
            elif (r2, c2) == (r, c):
                nr, nc = r1, c1
            else:
                continue

            forced_val = value if clue["type"] == "equal" else OTHER[value]
            sym = "=" if clue["type"] == "equal" else "×"
            if clue["type"] == "equal":
                reason = (
                    "cette case doit contenir un symbole identique au symbole de la case voisine déjà remplie"
                )
            else:
                reason = (
                    "cette case doit contenir un symbole different de celui de la case voisine deja remplie"
                )
            enqueue(nr, nc, forced_val, _step(
                nr, nc, forced_val, "clue",
                reason,
                premises=[(r, c)],
            ))

        # ── Règle 2 : trois consécutifs ────────────────────────────────
        for dr, dc in ((0, 1), (1, 0)):
            for offset in range(-2, 1):
                cells = [
                    (r + dr * (offset + i), c + dc * (offset + i))
                    for i in range(3)
                ]
                if any(nr < 0 or nr >= size or nc < 0 or nc >= size
                       for nr, nc in cells):
                    continue

                vals = [working[nr][nc] for nr, nc in cells]

                if vals.count(value) == 3:
                    raise Contradiction(_chain_for_step(causes.get((r, c)), derived_steps) + [_contradiction(
                        f"trois cases {NAMES[value]} consécutives en "
                        f"({cells[0][0]+1},{cells[0][1]+1})–({cells[2][0]+1},{cells[2][1]+1})"
                    )])

                if vals.count(value) == 2 and vals.count(None) == 1:
                    idx = vals.index(None)
                    nr, nc = cells[idx]
                    filled = [(cells[i][0], cells[i][1]) for i in range(3) if vals[i] == value]
                    axis = "la ligne" if dr == 0 else "la colonne"
                    if idx == 1:
                        reason = (
                            f"si un {NAMES[value]} était placé ici, "
                            f"cela créerait trois symboles identiques alignés dans {axis}"
                        )
                    else:
                        reason = (
                            f"si un {NAMES[value]} était placé ici, "
                            f"cela créerait trois symboles identiques alignés dans {axis}"
                        )
                    enqueue(nr, nc, OTHER[value], _step(
                        nr, nc, OTHER[value], "consecutive",
                        reason,
                        premises=filled,
                    ))

        # ── Règle 3 : saturation ligne / colonne ───────────────────────
        for is_row in (True, False):
            if is_row:
                line_vals  = [working[r][cc] for cc in range(size)]
                empty_idxs = [cc for cc in range(size) if working[r][cc] is None]
                label      = f"ligne {r+1}"
            else:
                line_vals  = [working[rr][c] for rr in range(size)]
                empty_idxs = [rr for rr in range(size) if working[rr][c] is None]
                label      = f"colonne {c+1}"

            count = line_vals.count(value)
            if count > size // 2:
                raise Contradiction(_chain_for_step(causes.get((r, c)), derived_steps) + [_contradiction(
                    f"la {label} aurait {count} cases {NAMES[value]} (max {size // 2})"
                )])
            if count == size // 2:
                subject = "cette ligne" if is_row else "cette colonne"
                reason = (
                    f"{subject} contient déjà {size // 2} cases remplies de ce type, "
                    f"donc cette case doit contenir un {NAMES[OTHER[value]]}"
                )
                for idx in empty_idxs:
                    nr, nc = (r, idx) if is_row else (idx, c)
                    enqueue(nr, nc, OTHER[value], _step(
                        nr, nc, OTHER[value], "saturation", reason,
                        premises=[(r, c)],
                    ))

    return steps, working


def _adjacent(r: int, c: int, size: int) -> set[tuple[int, int]]:
    return {
        (r + dr, c + dc)
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
        if 0 <= r + dr < size and 0 <= c + dc < size
    }


def _find_direct_clue_hint(grid: Grid, clues: Clues) -> dict | None:
    for clue in clues:
        r1, c1 = clue["cell1"]
        r2, c2 = clue["cell2"]
        v1, v2 = grid[r1][c1], grid[r2][c2]

        if v1 is None and v2 is None:
            continue
        if v1 is not None and v2 is not None:
            continue

        if v1 is None:
            nr, nc = r1, c1
            ref_r, ref_c = r2, c2
            ref_v = v2
        else:
            nr, nc = r2, c2
            ref_r, ref_c = r1, c1
            ref_v = v1

        forced_val = ref_v if clue["type"] == "equal" else OTHER[ref_v]
        if clue["type"] == "equal":
            reason = (
                "cette case doit contenir un symbole identique au symbole de la case voisine déjà remplie"
            )
        else:
            reason = (
                "cette case doit contenir un symbole different de celui de la case voisine deja remplie"
            )
        step = _step(
            nr, nc, forced_val, "clue",
            reason,
        )
        return _hint((nr, nc), forced_val, [step], "direct")

    return None


def _find_direct_consecutive_hint(grid: Grid, size: int) -> dict | None:
    for dr, dc in ((0, 1), (1, 0)):
        for r in range(size):
            for c in range(size):
                cells = [(r + dr * i, c + dc * i) for i in range(3)]
                if any(nr < 0 or nr >= size or nc < 0 or nc >= size for nr, nc in cells):
                    continue

                vals = [grid[nr][nc] for nr, nc in cells]
                for value in SYMBOLS:
                    if vals.count(value) != 2 or vals.count(None) != 1:
                        continue

                    idx = vals.index(None)
                    nr, nc = cells[idx]
                    filled = [cells[i] for i in range(3) if vals[i] == value]
                    axis = "la ligne" if dr == 0 else "la colonne"
                    if idx == 1:
                        reason = (
                            f"si un {NAMES[value]} était placé ici, "
                            f"cela créerait trois symboles identiques alignés dans {axis}"
                        )
                    else:
                        reason = (
                            f"si un {NAMES[value]} était placé ici, "
                            f"cela créerait trois symboles identiques alignés dans {axis}"
                        )
                    step = _step(
                        nr, nc, OTHER[value], "consecutive",
                        reason,
                    )
                    return _hint((nr, nc), OTHER[value], [step], "direct")

    return None


def _find_direct_saturation_hint(grid: Grid, size: int) -> dict | None:
    half = size // 2

    for r in range(size):
        row = [grid[r][c] for c in range(size)]
        empties = [c for c in range(size) if row[c] is None]
        if not empties:
            continue
        for value in SYMBOLS:
            if row.count(value) == half:
                c = empties[0]
                step = _step(
                    r, c, OTHER[value], "saturation",
                    f"cette ligne contient déjà {half} cases remplies de ce type, donc cette case doit contenir un {NAMES[OTHER[value]]}",
                )
                return _hint((r, c), OTHER[value], [step], "direct")

    for c in range(size):
        col = [grid[r][c] for r in range(size)]
        empties = [r for r in range(size) if col[r] is None]
        if not empties:
            continue
        for value in SYMBOLS:
            if col.count(value) == half:
                r = empties[0]
                step = _step(
                    r, c, OTHER[value], "saturation",
                    f"cette colonne contient déjà {half} cases remplies de ce type, donc cette case doit contenir un {NAMES[OTHER[value]]}",
                )
                return _hint((r, c), OTHER[value], [step], "direct")

    return None


def _line_coords(size: int, is_row: bool, idx: int) -> list[tuple[int, int]]:
    if is_row:
        return [(idx, c) for c in range(size)]
    return [(r, idx) for r in range(size)]


def _has_equal_clue(clues: Clues, a: tuple[int, int], b: tuple[int, int]) -> bool:
    for clue in clues:
        if clue["type"] != "equal":
            continue
        c1 = tuple(clue["cell1"])
        c2 = tuple(clue["cell2"])
        if (c1 == a and c2 == b) or (c1 == b and c2 == a):
            return True
    return False


def _find_direct_length6_equal_edge_hint(grid: Grid, clues: Clues, size: int) -> dict | None:
    if size != 6:
        return None

    for is_row in (True, False):
        for idx in range(size):
            coords = _line_coords(size, is_row, idx)
            vals = [grid[r][c] for r, c in coords]
            label = f"ligne {idx+1}" if is_row else f"colonne {idx+1}"

            left = coords[0]
            right_pair = (coords[4], coords[5])
            if (
                vals[0] is not None
                and vals[4] is None
                and vals[5] is None
                and _has_equal_clue(clues, right_pair[0], right_pair[1])
            ):
                tr, tc = coords[4]
                value = OTHER[vals[0]]
                step = _step(
                    tr, tc, value, "pattern6",
                    f"dans la {label}, la première case est déjà {NAMES[vals[0]]} et les positions 5 et 6 doivent être égales, donc la position 5 doit être {NAMES[value]}",
                )
                return _hint((tr, tc), value, [step], "direct")

            right = coords[5]
            left_pair = (coords[0], coords[1])
            if (
                vals[5] is not None
                and vals[0] is None
                and vals[1] is None
                and _has_equal_clue(clues, left_pair[0], left_pair[1])
            ):
                tr, tc = coords[1]
                value = OTHER[vals[5]]
                step = _step(
                    tr, tc, value, "pattern6",
                    f"cette case appartient à une paire de cases égales ; si cette paire valait {NAMES[vals[5]]}, "
                    f"les cases restantes ne pourraient plus être que {NAMES[value]}, "
                    f"ce qui créerait trois symboles identiques alignés",
                )
                return _hint((tr, tc), value, [step], "direct")

    return None


def _find_direct_equal_pair_next_to_symbol_hint(grid: Grid, clues: Clues, size: int) -> dict | None:
    for is_row in (True, False):
        for idx in range(size):
            coords = _line_coords(size, is_row, idx)
            vals = [grid[r][c] for r, c in coords]
            label = f"ligne {idx+1}" if is_row else f"colonne {idx+1}"

            for start in range(size - 2):
                left = coords[start]
                mid = coords[start + 1]
                right = coords[start + 2]
                left_val = vals[start]
                mid_val = vals[start + 1]
                right_val = vals[start + 2]

                if (
                    left_val is not None
                    and mid_val is None
                    and right_val is None
                    and _has_equal_clue(clues, mid, right)
                ):
                    mr, mc = mid
                    value = OTHER[left_val]
                    step = _step(
                        mr, mc, value, "clue_pattern",
                        f"cette case appartient à une paire de cases égales ; si cette paire valait {NAMES[left_val]}, cela créerait trois symboles identiques alignés",
                    )
                    return _hint((mr, mc), value, [step], "direct")

                if (
                    left_val is None
                    and mid_val is None
                    and right_val is not None
                    and _has_equal_clue(clues, left, mid)
                ):
                    mr, mc = mid
                    value = OTHER[right_val]
                    step = _step(
                        mr, mc, value, "clue_pattern",
                        f"cette case appartient à une paire de cases égales ; si cette paire valait {NAMES[right_val]}, cela créerait trois symboles identiques alignés",
                    )
                    return _hint((mr, mc), value, [step], "direct")

    return None


def _find_direct_length6_pattern_hint(grid: Grid, size: int) -> dict | None:
    if size != 6:
        return None

    patterns = (
        # AA____ -> opposite on the far edge
        {
            "same": (0, 1),
            "target": 5,
            "reason": "la ligne ou colonne commence par deux symboles identiques, donc l'extrémité opposée doit être le symbole inverse",
        },
        # ____AA -> opposite on the far edge
        {
            "same": (4, 5),
            "target": 0,
            "reason": "la ligne ou colonne se termine par deux symboles identiques, donc l'extrémité opposée doit être le symbole inverse",
        },
        # _A___A -> opposite on the left edge
        {
            "same": (1, 5),
            "target": 0,
            "reason": "les positions 2 et 6 portent déjà le même symbole, donc la case 1 doit être le symbole inverse",
        },
        # A___A_ -> opposite on the right edge
        {
            "same": (0, 4),
            "target": 5,
            "reason": "les positions 1 et 5 portent déjà le même symbole, donc la case 6 doit être le symbole inverse",
        },
        # A____A -> opposite near the left edge first
        {
            "same": (0, 5),
            "target": 1,
            "reason": "les deux extrémités portent déjà le même symbole, donc la case près du bord doit être le symbole inverse",
        },
        # A____A -> opposite near the right edge
        {
            "same": (0, 5),
            "target": 4,
            "reason": "les deux extrémités portent déjà le même symbole, donc la case près du bord doit être le symbole inverse",
        },
    )

    for is_row in (True, False):
        for idx in range(size):
            coords = _line_coords(size, is_row, idx)
            vals = [grid[r][c] for r, c in coords]

            for pattern in patterns:
                i, j = pattern["same"]
                t = pattern["target"]
                value = vals[i]

                if value is None or vals[j] != value or vals[t] is not None:
                    continue

                tr, tc = coords[t]
                label = f"ligne {idx+1}" if is_row else f"colonne {idx+1}"
                pos_i = i + 1
                pos_j = j + 1
                if (i, j) == (0, 5):
                    axis = "la ligne" if is_row else "la colonne"
                    step = _step(
                        tr, tc, OTHER[value], "pattern6",
                        f"si un {NAMES[value]} était placé ici, cela créerait trois symboles identiques alignés dans {axis}",
                    )
                else:
                    axis = "cette ligne" if is_row else "cette colonne"
                    step = _step(
                        tr, tc, OTHER[value], "pattern6",
                        f"si un {NAMES[value]} était placé ici, "
                        f"les cases restantes ne pourraient plus être que {NAMES[OTHER[value]]} dans {axis}, "
                        f"ce qui créerait trois symboles identiques alignés",
                    )
                return _hint((tr, tc), OTHER[value], [step], "direct")

    return None


def find_hint(grid: Grid, clues: Clues, size: int) -> dict | None:
    """
    Find the simplest deducible hint for the current (partial) grid.

    Level 1 — pour chaque case vide, on suppose la mauvaise valeur et on
    propage : si contradiction immédiate, la bonne valeur est déduite.

    Level 2 — si la propagation de niveau 1 ne mène pas à contradiction,
    on cherche une case pivot telle que ses deux valeurs possibles mènent
    toutes les deux à contradiction (preuve par cas exhaustifs).

    Retourne le hint dont la chaîne totale est la plus courte, ou None.
    """
    if size != 6:
        return None

    def cost(h: dict) -> int:
        c = len(h["steps"])
        if h.get("pivot"):
            c += len(h["pivot"]["case_a"]) + len(h["pivot"]["case_b"])
        return c

    # 1. Indices les plus simples à lire pour un humain
    for finder in (
        lambda: _find_direct_clue_hint(grid, clues),
        lambda: _find_direct_consecutive_hint(grid, size),
        lambda: _find_direct_saturation_hint(grid, size),
        lambda: _find_direct_equal_pair_next_to_symbol_hint(grid, clues, size),
        lambda: _find_direct_length6_equal_edge_hint(grid, clues, size),
        lambda: _find_direct_length6_pattern_hint(grid, size),
    ):
        hint = finder()
        if hint is not None:
            return hint

    empty = [
        (r, c)
        for r in range(size)
        for c in range(size)
        if grid[r][c] is None
    ]
    best: dict | None = None

    def _update(hint: dict) -> None:
        nonlocal best
        if best is None or cost(hint) < cost(best):
            best = hint

    for r, c in empty:
        for wrong in SYMBOLS:
            correct = OTHER[wrong]

            # ── Niveau 1 ──────────────────────────────────────────────
            try:
                steps1, grid1 = propagate(grid, clues, size, [(r, c, wrong)])
            except Contradiction as exc:
                _update(_hint((r, c), correct, exc.steps, "contradiction"))
                continue  # pas besoin du niveau 2 pour cette combinaison

            # ── Niveau 2 : recherche d'un pivot ───────────────────────
            remaining = [
                (rr, cc)
                for rr in range(size)
                for cc in range(size)
                if grid1[rr][cc] is None
            ]
            # Priorité aux cases adjacentes à (r,c)
            adj = _adjacent(r, c, size)
            pivots = sorted(remaining, key=lambda p: p not in adj)

            for pr, pc in pivots:
                try:
                    propagate(grid1, clues, size, [(pr, pc, "S")])
                    continue  # S ne mène pas à contradiction → pas un bon pivot
                except Contradiction as ea:
                    steps_a = ea.steps

                try:
                    propagate(grid1, clues, size, [(pr, pc, "L")])
                    continue  # L ne mène pas à contradiction → pas un bon pivot
                except Contradiction as eb:
                    steps_b = eb.steps

                # Les deux valeurs du pivot mènent à contradiction → hint de niveau 2
                _update(_hint((r, c), correct, steps1, "pivot", {
                        "cell":   [pr, pc],
                        "case_a": steps_a,
                        "case_b": steps_b,
                    }))
                break  # un seul pivot suffit par combinaison (r,c,wrong)

    return best

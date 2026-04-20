const SYMBOLS = [null, 'S', 'L'];
const ICONS   = { S: '☀', L: '☾' };

let state = { size: 0, fixed: [], grid: [], clues: [], errorCells: [], solved: false, hintsUsed: 0 };
const MAX_HINTS = 3;

// ── Minuteur ───────────────────────────────────────────────────────
let timerInterval = null;
let timerStart    = null;

function formatTime(ms) {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

function formatTimeText(ms) {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const sec = s % 60;
  if (m === 0) return `${sec} seconde${sec > 1 ? 's' : ''}`;
  return `${m} min et ${sec} seconde${sec > 1 ? 's' : ''}`;
}

function startTimer() {
  if (timerInterval) return;
  timerStart = Date.now();
  const el = document.getElementById('timer');
  el.className = 'running';
  timerInterval = setInterval(() => {
    el.textContent = formatTime(Date.now() - timerStart);
  }, 1000);
}

function stopTimer() {
  clearInterval(timerInterval);
  timerInterval = null;
  const ms = Date.now() - timerStart;
  const el = document.getElementById('timer');
  el.className = 'done';
  el.textContent = formatTime(ms);
  return formatTimeText(ms);
}

function resetTimer() {
  clearInterval(timerInterval);
  timerInterval = null;
  timerStart    = null;
  const el = document.getElementById('timer');
  el.className   = '';
  el.textContent = '00:00';
}

// ── API ────────────────────────────────────────────────────────────

async function newPuzzle() {
  clearTimeout(validateTimer);
  closeWinModal();
  resetTimer();
  setStatus('');
  document.getElementById('btn-reset').disabled = false;
  const difficulty = document.getElementById('difficulty').value;
  const res  = await fetch(`/puzzle?size=6&difficulty=${difficulty}`);
  const data = await res.json();
  state.size       = data.size;
  state.fixed      = data.puzzle.map((row) => row.map((v) => v));
  state.grid       = data.puzzle.map((row) => row.map((v) => v));
  state.clues      = data.clues;
  state.errorCells = [];
  state.solved     = false;
  state.hintsUsed  = 0;
  clearHintPanel();
  updateHintButton();
  render();
}

let validateTimer = null;
let validateAbort = null;

function scheduleValidation() {
  clearTimeout(validateTimer);
  if (validateAbort) {
    validateAbort.abort();
    validateAbort = null;
  }
  validateAbort = new AbortController();
  const { signal } = validateAbort;
  validateTimer = setTimeout(async () => {
    try {
      const res  = await fetch('/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ grid: state.grid, clues: state.clues, partial: true }),
        signal,
      });
      const data = await res.json();
      validateAbort = null;
      applyErrorCells(data.error_cells);
    } catch (e) {
      if (e.name !== 'AbortError') throw e;
    }
  }, 600);
}

async function checkWin() {
  const res  = await fetch('/validate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ grid: state.grid, clues: state.clues, partial: false }),
  });
  const data = await res.json();
  applyErrorCells(data.error_cells);
  if (data.valid && data.complete) {
    state.solved = true;
    document.getElementById('btn-reset').disabled = true;
    updateHintButton();
    const t = stopTimer();
    setStatus('');
    showWinModal(t);
  } else if (!data.complete) {
    setStatus('Grille incomplète.', 'warn');
  } else {
    setStatus('Solution incorrecte.', 'warn');
  }
}

function applyErrorCells(errorCells) {
  document.querySelectorAll('.cell.error').forEach((el) => el.classList.remove('error'));
  state.errorCells = errorCells || [];
  paintErrors();
}

function paintErrors() {
  for (const [r, c] of state.errorCells) {
    const el = document.querySelector(`[data-row="${r}"][data-col="${c}"]`);
    if (el) el.classList.add('error');
  }
}

// ── Interactions ───────────────────────────────────────────────────

function cellClick(r, c) {
  if (state.solved) return;
  if (state.fixed[r][c] !== null) return;
  const cur = state.grid[r][c];
  state.grid[r][c] = SYMBOLS[(SYMBOLS.indexOf(cur) + 1) % SYMBOLS.length];
  if (validateAbort) {
    validateAbort.abort();
    validateAbort = null;
  }
  state.errorCells = state.errorCells.filter(([er, ec]) => er !== r || ec !== c);
  document.querySelectorAll('.cell.hint-target, .cell.hint-step').forEach((el) => {
    el.classList.remove('hint-target', 'hint-step');
  });
  document.getElementById('hint-panel').innerHTML = '';
  syncHintVisibility();
  if (state.grid[r][c] !== null) startTimer();
  const cellEl = document.querySelector(`[data-row="${r}"][data-col="${c}"]`);
  if (cellEl) {
    cellEl.textContent = state.grid[r][c] ? ICONS[state.grid[r][c]] : '';
    cellEl.classList.remove('error');
  }
  const complete = state.grid.every((row) => row.every((v) => v !== null));
  if (complete) checkWin();
  else scheduleValidation();
}

// ── Rendu ──────────────────────────────────────────────────────────

function render() {
  const { size, grid, fixed, clues } = state;
  const board  = document.getElementById('board');
  const slots  = 2 * size - 1;
  const cellPx = 64;
  const cluePx = 20;

  const tpl = Array.from({ length: slots }, (_, i) =>
    i % 2 === 0 ? `${cellPx}px` : `${cluePx}px`
  ).join(' ');
  board.style.gridTemplateColumns = tpl;
  board.innerHTML = '';

  const clueMap = {};
  for (const cl of clues) {
    clueMap[`${cl.cell1}-${cl.cell2}`] = cl.type;
  }

  for (let gi = 0; gi < slots; gi++) {
    for (let gj = 0; gj < slots; gj++) {
      const el = document.createElement('div');
      const evenI = gi % 2 === 0;
      const evenJ = gj % 2 === 0;

      if (evenI && evenJ) {
        const r = gi / 2;
        const c = gj / 2;
        const val = grid[r][c];
        el.className = 'cell' + (fixed[r][c] !== null ? ' fixed' : '');
        el.dataset.row = r;
        el.dataset.col = c;
        el.textContent = val ? ICONS[val] : '';
        if (fixed[r][c] === null) el.onclick = () => cellClick(r, c);
      } else if (evenI && !evenJ) {
        const r = gi / 2;
        const c = (gj - 1) / 2;
        const type = clueMap[`${r},${c}-${r},${c + 1}`];
        el.className = 'clue-h' + (type ? ` clue-${type}` : '');
        if (type) {
          const s = document.createElement('span');
          s.textContent = type === 'equal' ? '=' : '×';
          el.appendChild(s);
        }
      } else if (!evenI && evenJ) {
        const r = (gi - 1) / 2;
        const c = gj / 2;
        const type = clueMap[`${r},${c}-${r + 1},${c}`];
        el.className = 'clue-v' + (type ? ` clue-${type}` : '');
        if (type) {
          const s = document.createElement('span');
          s.textContent = type === 'equal' ? '=' : '×';
          el.appendChild(s);
        }
      } else {
        el.className = 'clue-corner';
        el.style.width  = `${cluePx}px`;
        el.style.height = `${cluePx}px`;
      }

      board.appendChild(el);
    }
  }

  paintErrors();
}

function setStatus(msg, cls = '') {
  const el = document.getElementById('status');
  el.textContent = msg;
  el.className   = cls;
}

function resetPuzzle() {
  clearTimeout(validateTimer);
  closeWinModal();
  setStatus('');
  state.grid       = state.fixed.map((row) => row.map((v) => v));
  state.errorCells = [];
  state.solved     = false;
  clearHintPanel();
  render();
}

// ── Indices ────────────────────────────────────────────────────────

function updateHintButton() {
  const btn = document.getElementById('btn-hint');
  const ctr = document.getElementById('hint-count');
  const remaining = MAX_HINTS - state.hintsUsed;
  ctr.textContent = `(${remaining})`;
  btn.disabled = state.solved || remaining <= 0;
  syncHintVisibility();
}

function clearHintPanel() {
  document.getElementById('hint-panel').innerHTML = '';
  document.querySelectorAll('.cell.hint-target, .cell.hint-step').forEach((el) => {
    el.classList.remove('hint-target', 'hint-step');
  });
  syncHintVisibility();
}

async function requestHint() {
  if (state.solved || state.hintsUsed >= MAX_HINTS) return;
  const btn = document.getElementById('btn-hint');
  btn.disabled = true;

  const res  = await fetch('/hint', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ grid: state.grid, clues: state.clues }),
  });
  const data = await res.json();

  state.hintsUsed++;
  updateHintButton();

  if (!data.hint) {
    renderHintPanel(null);
    return;
  }

  renderHintPanel(data.hint);
  highlightHint(data.hint);
}

function highlightHint(hint) {
  document.querySelectorAll('.cell.hint-target, .cell.hint-step').forEach((el) => {
    el.classList.remove('hint-target', 'hint-step');
  });
  const [r, c] = hint.cell;
  const target = document.querySelector(`[data-row="${r}"][data-col="${c}"]`);
  if (target) target.classList.add('hint-target');
  for (const step of hint.steps) {
    if (!step.cell) continue;
    const [sr, sc] = step.cell;
    if (sr === r && sc === c) continue;
    const el = document.querySelector(`[data-row="${sr}"][data-col="${sc}"]`);
    if (el) el.classList.add('hint-step');
  }
}

function renderHintPanel(hint) {
  const panel = document.getElementById('hint-panel');
  if (!hint) {
    panel.innerHTML = '<p class="hint-none">Aucun indice trouvé — la grille est peut-être déjà résolue ou invalide.</p>';
    syncHintVisibility();
    return;
  }

  const [r, c] = hint.cell;
  let explanation = '';

  if (hint.kind === 'direct') {
    explanation = buildChain(hint.steps, '');
  } else if (hint.pivot === null) {
    explanation = buildHypothesisChain(hint.steps, [r, c], ICONS[hint.value === 'S' ? 'L' : 'S']);
  } else {
    const [pr, pc] = hint.pivot.cell;
    explanation = buildHypothesisChain(hint.steps, [r, c], ICONS[hint.value === 'S' ? 'L' : 'S']);
    explanation += `<div class="hint-pivot-intro">Quelle que soit la valeur de (${pr+1},${pc+1}), contradiction :</div>`;
    explanation += `<div class="hint-cases">`;
    explanation += `<div class="hint-case"><div class="hint-case-label">Si (${pr+1},${pc+1}) = ☀</div>${buildHypothesisCase(hint.pivot.case_a, [pr, pc], '☀')}</div>`;
    explanation += `<div class="hint-case"><div class="hint-case-label">Si (${pr+1},${pc+1}) = ☾</div>${buildHypothesisCase(hint.pivot.case_b, [pr, pc], '☾')}</div>`;
    explanation += `</div>`;
  }

  panel.innerHTML = `
    <div class="hint-header">Le bon symbole ici est <span class="hint-sym">${hint.symbol}</span></div>
    <details class="hint-details">
      <summary class="hint-summary">Voir l’explication</summary>
      <div class="hint-body">${explanation}</div>
    </details>
  `;
  syncHintVisibility();
}

function syncHintVisibility() {
  const panel = document.getElementById('hint-panel');
  panel.style.display = panel.innerHTML.trim() !== '' ? '' : 'none';
}

function buildChain(steps, intro) {
  if (!steps || steps.length === 0) return '';
  let html = '';
  if (intro && steps[0] && steps[0].reason_type !== 'contradiction') {
    html += `<div class="hint-intro">${formatSentence(steps[0].reason)}</div>`;
    steps = steps.slice(1);
  } else if (intro) {
    html += `<div class="hint-intro">${intro}</div>`;
  }
  html += '<div class="hint-steps">';
  for (const s of steps) {
    if (s.reason_type === 'contradiction') {
      html += `<div class="hint-contradiction">Contradiction : ${formatSentence(s.reason)}</div>`;
    } else {
      html += `<div class="hint-step-reason">${formatSentence(s.reason)}</div>`;
    }
  }
  html += '</div>';
  return html;
}

function buildHypothesisChain(steps, hypothesisCell, wrongSymbol) {
  if (!steps || steps.length === 0) return '';
  const [r, c] = hypothesisCell;
  let html = '<div class="hint-steps">';
  html += `<div class="hint-step-reason"><span class="hint-prefix">Hypothèse :</span> ${wrongSymbol} en (${r+1},${c+1}).</div>`;

  let previousStep = null;
  for (const s of steps) {
    if (s.reason_type === 'contradiction') {
      let contradictionText = s.reason;
      if (previousStep && previousStep.cell) {
        const [pr, pc] = previousStep.cell;
        contradictionText = `on vient de déduire ${previousStep.symbol} en (${pr+1},${pc+1}), mais ${s.reason}`;
      }
      html += `<div class="hint-contradiction"><span class="hint-prefix">Contradiction :</span> ${formatSentence(contradictionText)}</div>`;
    } else {
      const [sr, sc] = s.cell;
      html += `<div class="hint-step-reason"><span class="hint-prefix">Implique :</span> ${s.symbol} en (${sr+1},${sc+1}), car ${formatClause(s.reason)}.</div>`;
      previousStep = s;
    }
  }

  html += '</div>';
  return html;
}

function buildHypothesisCase(steps, hypothesisCell, symbol) {
  if (!steps || steps.length === 0) return '';
  let html = '<div class="hint-steps">';
  if (hypothesisCell && symbol) {
    const [r, c] = hypothesisCell;
    html += `<div class="hint-step-reason"><span class="hint-prefix">Hypothèse :</span> ${symbol} en (${r+1},${c+1}).</div>`;
  }
  let previousStep = null;
  for (const s of steps) {
    if (s.reason_type === 'contradiction') {
      let contradictionText = s.reason;
      if (previousStep && previousStep.cell) {
        const [pr, pc] = previousStep.cell;
        contradictionText = `on vient de déduire ${previousStep.symbol} en (${pr+1},${pc+1}), mais ${s.reason}`;
      }
      html += `<div class="hint-contradiction"><span class="hint-prefix">Contradiction :</span> ${formatSentence(contradictionText)}</div>`;
    } else {
      const [sr, sc] = s.cell;
      html += `<div class="hint-step-reason"><span class="hint-prefix">Implique :</span> ${s.symbol} en (${sr+1},${sc+1}), car ${formatClause(s.reason)}.</div>`;
      previousStep = s;
    }
  }
  html += '</div>';
  return html;
}

function formatClause(text) {
  if (!text) return '';
  const trimmed = text.trim().replace(/[.]+$/g, '');
  return trimmed.charAt(0).toLowerCase() + trimmed.slice(1);
}

function formatSentence(text) {
  if (!text) return '';
  const trimmed = text.trim().replace(/[.]+$/g, '');
  return trimmed.charAt(0).toUpperCase() + trimmed.slice(1) + '.';
}

function showWinModal(timeText) {
  const modal = document.getElementById('win-modal');
  const message = document.getElementById('win-message');
  message.textContent = `Vous avez terminé le puzzle en ${timeText}.`;
  modal.hidden = false;
}

function closeWinModal() {
  const modal = document.getElementById('win-modal');
  if (modal) modal.hidden = true;
}

function setupDifficultyDropdown() {
  const banner  = document.getElementById('difficulty-banner');
  const input   = document.getElementById('difficulty');
  const label   = document.getElementById('difficulty-value');
  const options = document.querySelectorAll('#difficulty-options li');
  if (!banner || !input || !label) return;

  function open() {
    banner.classList.add('is-open');
    banner.setAttribute('aria-expanded', 'true');
  }

  function close() {
    banner.classList.remove('is-open');
    banner.setAttribute('aria-expanded', 'false');
  }

  function select(li) {
    options.forEach(o => o.removeAttribute('aria-selected'));
    li.setAttribute('aria-selected', 'true');
    input.value  = li.dataset.value;
    label.textContent = li.textContent;
    close();
    newPuzzle();
  }

  banner.addEventListener('click', (e) => {
    if (e.target.closest('#difficulty-options')) return;
    banner.classList.contains('is-open') ? close() : open();
  });

  options.forEach(li => {
    li.addEventListener('click', () => select(li));
  });

  document.addEventListener('click', (e) => {
    if (!banner.contains(e.target)) close();
  });

  banner.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      banner.classList.contains('is-open') ? close() : open();
    } else if (e.key === 'Escape') {
      close();
    } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      const current = [...options].findIndex(o => o.getAttribute('aria-selected') === 'true');
      const next = e.key === 'ArrowDown'
        ? Math.min(current + 1, options.length - 1)
        : Math.max(current - 1, 0);
      select(options[next]);
    }
  });
}

setupDifficultyDropdown();
newPuzzle();

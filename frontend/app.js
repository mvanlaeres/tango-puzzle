const SYMBOLS = [null, 'S', 'L'];
const COLOR_NAMES = { S: 'jaune', L: 'bleu' };
const COLUMN_LABELS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');

function symbolMarkup(value, size = '') {
  if (!value) return '';
  const sizeClass = size ? ` token-${size}` : '';
  const label = COLOR_NAMES[value];
  return `<span class="token token-${value}${sizeClass}" aria-label="${label}" title="${label}"></span>`;
}

function colorWordToMarkup(name) {
  if (name === 'jaune') return symbolMarkup('S', 'inline');
  if (name === 'bleu') return symbolMarkup('L', 'inline');
  return name;
}

function formatLegacyCell(row, col) {
  return formatCell([Number(row) - 1, Number(col) - 1]);
}

function renderReasonText(text) {
  if (!text) return '';
  return text
    .replace(/\((\d+),(\d+)\)–\((\d+),(\d+)\)/g, (_, r1, c1, r2, c2) =>
      `${formatLegacyCell(r1, c1)} a ${formatLegacyCell(r2, c2)}`
    )
    .replace(/\((\d+),(\d+)\)/g, (_, r, c) => formatLegacyCell(r, c))
    .replace(/Cette case doit contenir un jaune, car /g, '')
    .replace(/Cette case doit contenir un bleu, car /g, '')
    .replace(/cette case doit contenir un jaune, car /g, '')
    .replace(/cette case doit contenir un bleu, car /g, '')
    .replace(/\bjaune\b/g, symbolMarkup('S', 'inline'))
    .replace(/\bbleu\b/g, symbolMarkup('L', 'inline'));
}

function formatContradictionText(text) {
  if (!text) return '';
  const trimmed = text.trim().replace(/[.]+$/g, '');

  let match = trimmed.match(/^la case \((\d+),(\d+)\) devrait valoir (jaune|bleu), mais on a déjà déduit (jaune|bleu) pour cette case$/i);
  if (match) {
    const [, row, col, expected, actual] = match;
    return `Cette hypothèse mène à une contradiction : ${formatLegacyCell(row, col)} devrait contenir ${colorWordToMarkup(expected.toLowerCase())}, mais cette case a déjà été déduite comme ${colorWordToMarkup(actual.toLowerCase())}.`;
  }

  match = trimmed.match(/^la case \((\d+),(\d+)\) devrait valoir (jaune|bleu) mais est déjà (jaune|bleu)$/i);
  if (match) {
    const [, row, col, expected, actual] = match;
    return `Cette hypothèse mène à une contradiction : ${formatLegacyCell(row, col)} devrait contenir ${colorWordToMarkup(expected.toLowerCase())}, mais cette case contient déjà ${colorWordToMarkup(actual.toLowerCase())}.`;
  }

  match = trimmed.match(/^trois cases (jaune|bleu) consécutives en \((\d+),(\d+)\)–\((\d+),(\d+)\)$/i);
  if (match) {
    const [, value, r1, c1, r2, c2] = match;
    return `Cette hypothèse mène à une contradiction : elle créerait trois symboles ${colorWordToMarkup(value.toLowerCase())} consécutifs entre ${formatLegacyCell(r1, c1)} et ${formatLegacyCell(r2, c2)}.`;
  }

  return formatSentence(trimmed)
    .replace(/^La case ([A-Z]\d+) devrait valoir /, 'Cette hypothèse mène à une contradiction : $1 devrait contenir ')
    .replace(/^La /, 'Cette hypothèse mène à une contradiction : la ');
}

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
  setCoordinateVisibility(false);
  syncHintVisibility();
  if (state.grid[r][c] !== null) startTimer();
  const cellEl = document.querySelector(`[data-row="${r}"][data-col="${c}"]`);
  if (cellEl) {
    cellEl.innerHTML = symbolMarkup(state.grid[r][c], 'cell');
    cellEl.classList.remove('error');
  }
  const complete = state.grid.every((row) => row.every((v) => v !== null));
  if (complete) checkWin();
  else scheduleValidation();
}

// ── Rendu ──────────────────────────────────────────────────────────

function render() {
  const { size, grid, fixed, clues } = state;
  const shell  = document.getElementById('board-shell');
  const slots  = 2 * size - 1;
  const cellPx = 64;
  const cluePx = 20;

  const tpl = Array.from({ length: slots }, (_, i) =>
    i % 2 === 0 ? `${cellPx}px` : `${cluePx}px`
  ).join(' ');
  shell.innerHTML = '<div id="board"></div>';
  const nextBoard = document.getElementById('board');
  nextBoard.style.gridTemplateColumns = tpl;
  nextBoard.style.gridTemplateRows = tpl;
  nextBoard.innerHTML = '';
  const activeBoard = nextBoard;

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
        el.innerHTML = symbolMarkup(val, 'cell');
        if (r === size - 1) {
          el.innerHTML += `<span class="cell-coord cell-coord-col">${COLUMN_LABELS[c]}</span>`;
        }
        if (c === size - 1) {
          el.innerHTML += `<span class="cell-coord cell-coord-row">${size - r}</span>`;
        }
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

      activeBoard.appendChild(el);
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
  setCoordinateVisibility(false);
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
    setCoordinateVisibility(false);
    syncHintVisibility();
    return;
  }

  const wrongValue = hint.value === 'S' ? 'L' : 'S';
  const summary = hint.kind === 'direct'
    ? ''
    : `Si on mettait ${symbolMarkup(wrongValue, 'inline')} en ${formatCell(hint.cell)}, on arriverait à une contradiction.`;
  const explanation = hint.kind === 'direct'
    ? buildDirectExplanation(hint.steps)
    : buildHypothesisExplanation(hint, wrongValue);

  panel.innerHTML = `
    <div class="hint-header">Cette case doit contenir un <span class="hint-sym">${symbolMarkup(hint.value, 'inline')}</span></div>
    ${summary ? `<div class="hint-lead">${summary}</div>` : ''}
    <div class="hint-body">${explanation}</div>
  `;
  setCoordinateVisibility(true);
  syncHintVisibility();
}

function syncHintVisibility() {
  const panel = document.getElementById('hint-panel');
  const visible = panel.innerHTML.trim() !== '';
  panel.style.display = visible ? '' : 'none';
}

function setCoordinateVisibility(visible) {
  document.querySelectorAll('.cell-coord').forEach((el) => {
    el.classList.toggle('is-visible', visible);
  });
}

function formatCell(cell) {
  const [r, c] = cell;
  return `${COLUMN_LABELS[c]}${state.size - r}`;
}

function buildHintCard(title, note = '', tone = '', noteIsHtml = false) {
  const toneClass = tone ? ` hint-card-${tone}` : '';
  return `
    <div class="hint-card${toneClass}">
      <div class="hint-card-title">${title}</div>
      ${note ? `<div class="hint-card-note">${noteIsHtml ? note : renderReasonText(note)}</div>` : ''}
    </div>
  `;
}

function buildDeductionCards(steps) {
  const deductions = (steps || []).filter((step) => step.cell && step.reason_type !== 'contradiction');
  if (deductions.length === 0) {
    return '<div class="hint-mini-note">Aucune déduction intermédiaire.</div>';
  }
  let html = '<div class="hint-card-list">';
  for (const step of deductions) {
    html += buildHintCard(
      `${formatCell(step.cell)} = ${symbolMarkup(step.value, 'inline')}`,
      formatSentence(step.reason),
    );
  }
  html += '</div>';
  return html;
}

function buildContradictionCard(steps) {
  const contradiction = (steps || []).find((step) => step.reason_type === 'contradiction');
  if (!contradiction) return '';
  return buildHintCard('Contradiction', formatContradictionText(contradiction.reason), 'danger', true);
}

function buildDirectExplanation(steps) {
  const firstStep = (steps || []).find((step) => step.cell && step.reason_type !== 'contradiction');
  const note = firstStep ? formatSentence(firstStep.reason) : '';
  return `
    <div class="hint-section">
      <div class="hint-section-title">Pourquoi</div>
      <div class="hint-mini-note">${renderReasonText(note)}</div>
    </div>
  `;
}

function buildHypothesisCaseDetails(steps, cell, symbol) {
  return `
    <div class="hint-section">
      <div class="hint-section-title">Hypothèse</div>
      ${buildHintCard(`${formatCell(cell)} = ${symbolMarkup(symbol, 'inline')}`)}
    </div>
    <div class="hint-section">
      <div class="hint-section-title">Déductions</div>
      ${buildDeductionCards(steps)}
    </div>
    <div class="hint-section">
      <div class="hint-section-title">Issue</div>
      ${buildContradictionCard(steps)}
    </div>
  `;
}

function buildHypothesisExplanation(hint, wrongValue) {
  let html = `
    <div class="hint-section">
      <div class="hint-section-title">Hypothèse</div>
      ${buildHintCard(`${formatCell(hint.cell)} = ${symbolMarkup(wrongValue, 'inline')}`)}
    </div>
    <div class="hint-section">
      <div class="hint-section-title">Déductions</div>
      ${buildDeductionCards(hint.steps)}
    </div>
  `;

  if (hint.pivot === null) {
    html += `
      <div class="hint-section">
        <div class="hint-section-title">Issue</div>
        ${buildContradictionCard(hint.steps)}
      </div>
    `;
    return html;
  }

  const pivotCell = formatCell(hint.pivot.cell);
  html += `
    <div class="hint-section">
      <div class="hint-section-title">Conclusion</div>
      <div class="hint-mini-note">Pour ${pivotCell}, les deux possibilités mènent à une contradiction.</div>
    </div>
    <div class="hint-case-stack">
      <details class="hint-case-details">
        <summary class="hint-case-summary">Si ${pivotCell} = ${symbolMarkup('S', 'inline')}</summary>
        <div class="hint-case-body">${buildHypothesisCaseDetails(hint.pivot.case_a, hint.pivot.cell, 'S')}</div>
      </details>
      <details class="hint-case-details">
        <summary class="hint-case-summary">Si ${pivotCell} = ${symbolMarkup('L', 'inline')}</summary>
        <div class="hint-case-body">${buildHypothesisCaseDetails(hint.pivot.case_b, hint.pivot.cell, 'L')}</div>
      </details>
    </div>
  `;

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

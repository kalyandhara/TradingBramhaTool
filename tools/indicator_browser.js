// indicator_browser.js — the card-style Indicator Browser (B-150) with
// Favorites + Recent (B-152).
//
// One overlay for the whole page, opened from a pane's INDICATORS button and
// acting on THAT pane only ("Adding to RELIANCE.NS · 1d"). It never touches
// pane.indicators directly: add / remove go through the pane's own hidden
// checkbox in the classic dropdown, so every rule already wired there — ETF-mode
// refusal, RSI↔divergence coupling, savePaneCfg, the active count — applies
// unchanged. The classic dropdown stays one click away (B-148: for one release).
//
// Reads, as globals from chart_dashboard.html: INDICATOR_DEFS (with the B-149
// catalogue folded in), INDICATOR_GROUPS, GROUP_BLURB, INDICATOR_GOALS and
// INDICATOR_CATALOGUE_STATUS (indicator_catalogue.js).
//
// Preview pictures come from ind-thumbs/ (B-151); the NSE evidence line from
// /api/indicator_evidence (B-154). Discover is the landing view (B-153), the goal
// chips filter any view (B-156), the keyboard works inside the overlay only
// (B-155), and Learn more opens the indicator's wiki concept page (B-157).
(function () {
  'use strict';

  const LS_FAVS = 'tb_ind_favs';
  const LS_RECENT = 'tb_ind_recent';
  const LS_CLASSIC = 'tb_ind_classic';
  const RECENT_MAX = 8;

  // ── storage: per-person, global across panes; never fatal (B-152) ─────────
  function lsGet(k, dflt) {
    try { const v = JSON.parse(localStorage.getItem(k)); return v == null ? dflt : v; }
    catch (_) { return dflt; }
  }
  function lsSet(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) {} }
  const favs = () => new Set(lsGet(LS_FAVS, []));
  const recent = () => lsGet(LS_RECENT, []);
  function toggleFav(key) {
    const f = favs();
    f.has(key) ? f.delete(key) : f.add(key);
    lsSet(LS_FAVS, [...f]);
  }
  function pushRecent(key) {
    lsSet(LS_RECENT, [key, ...recent().filter(k => k !== key)].slice(0, RECENT_MAX));
  }
  const classicPreferred = () => lsGet(LS_CLASSIC, false) === true;

  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g,
    c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

  // ── pane bridge — everything goes through the classic checkbox ─────────────
  function chkFor(pane, key) {
    return pane && pane.el ? pane.el.querySelector(`.ind-panel .ind-chk[data-key="${key}"]`) : null;
  }
  function isDisabled(pane, key) {
    const c = chkFor(pane, key);
    return !!(c && c.closest('.ind-row') && c.closest('.ind-row').classList.contains('ind-disabled'));
  }
  const isOn = (pane, key) => !!(pane && pane.indicators && pane.indicators.has(key));
  function setOn(pane, key, on) {
    const c = chkFor(pane, key);
    if (!c || isDisabled(pane, key) || c.checked === on) return;
    c.checked = on;
    c.dispatchEvent(new Event('change', {bubbles: true}));
    if (on && isOn(pane, key)) pushRecent(key);
  }

  // ── preview pictures (B-151) — gen_indicator_thumbs.py writes them ─────────
  // Loaded once, on first open. A key with no picture (the detector found
  // nothing on the reference chart), a missing manifest or a failed image all
  // fall back to the colour swatch — never a broken image.
  let thumbs = null;
  function loadThumbs() {
    if (thumbs) return;
    thumbs = {};
    fetch('/ind-thumbs/manifest.json')
      .then(r => (r.ok ? r.json() : null))
      .then(m => { thumbs = (m && m.thumbs) || {}; if (root && root.classList.contains('open')) paint(); })
      .catch(() => {});
  }
  // ── NSE evidence line (B-154) — indicator_evidence.py via the chart server ──
  // Shown to every reader. If the request fails the line is simply absent: an
  // unknown is better left unsaid than shown as "not measured".
  let evidence = null;
  function loadEvidence() {
    if (evidence) return;
    evidence = {};
    fetch('/api/indicator_evidence')
      .then(r => (r.ok ? r.json() : null))
      .then(m => { evidence = m || {}; if (root && root.classList.contains('open')) paint(); })
      .catch(() => {});
  }
  function evidenceRow(d) {
    const e = evidence && evidence[d.key];
    if (!e) return '';
    const cls = {POSITIVE: 'pos', NEGATIVE: 'neg', NULL: 'neg', MIXED: 'mix'}[e.verdict] || 'none';
    const cite = e.items && e.items.length ? ` <span class="ib-ev-cite">(${e.items.map(esc).join(', ')})</span>` : '';
    return `<div class="ib-evidence ${cls}"><div class="ib-ev-head">Evidence on NSE · ` +
           `<span class="ib-ev-label">${esc(e.label)}</span></div>` +
           (e.verdict ? `<div class="ib-ev-line">${esc(e.line)}${cite}</div>` : '') + '</div>';
  }

  function pic(d, big) {
    const t = thumbs && thumbs[d.key];
    const img = t && t.file
      ? `<img src="/ind-thumbs/${encodeURIComponent(t.file)}" alt="" loading="lazy" decoding="async"` +
        ` title="${esc('Drawn on ' + t.chart)}" onerror="this.remove()">`
      : '';
    return `<div class="ib-pic${big ? ' big' : ''}" style="--sw:${esc(d.color)}">` +
           `<span>${esc((d.group || '?')[0])}</span>${img}</div>`;
  }

  // ── state ─────────────────────────────────────────────────────────────────
  let root = null, pane = null, view = '__discover__', selected = null, query = '', goal = null;
  let explore = [];   // B-153 "More to explore" — reshuffled on every open

  //: B-153 "Start here": the six a beginner meets first on any charting site.
  //: Chosen by hand, not ranked — one user, no usage data worth ranking by.
  const START_HERE = ['ema20', 'ema50', 'volume', 'rsi', 'bollinger', 'atr'];
  const EXPLORE_N = 6;
  const defs = () => (typeof INDICATOR_DEFS !== 'undefined' ? INDICATOR_DEFS : []);
  const defBy = key => defs().find(d => d.key === key);
  const isDraft = () => (window.INDICATOR_CATALOGUE_STATUS || 'draft') !== 'approved';

  function newest() {
    return defs().reduce((m, d) => (d.added && d.added > m ? d.added : m), '');
  }

  function visibleDefs() {
    const q = query.trim().toLowerCase();
    let list = defs();
    if (q) {
      // A search spans the whole library, the way the classic dropdown's does.
      return list.filter(d => (d.label + ' ' + d.key + ' ' + d.group + ' ' + (d.alias || '') + ' ' +
                               (d.short || '')).toLowerCase().includes(q));
    }
    if (view === '__fav__') { const f = favs(); list = list.filter(d => f.has(d.key)); }
    else if (view === '__active__') list = list.filter(d => isOn(pane, d.key));
    else if (view === '__recent__') list = recent().map(defBy).filter(Boolean);
    else if (view !== '__all__' && view !== '__discover__') list = list.filter(d => d.group === view);
    // A goal chip narrows whatever view is showing; on Discover it means "all of them".
    return goal ? list.filter(d => (d.goals || []).includes(goal)) : list;
  }

  function newestThree() {
    return defs().filter(d => d.added).slice().sort((a, b) => (a.added < b.added ? 1 : a.added > b.added ? -1 : 0)).slice(0, 3);
  }
  function reshuffle() {
    const skip = new Set([...START_HERE, ...newestThree().map(d => d.key)]);
    const pool = defs().filter(d => !skip.has(d.key));
    for (let i = pool.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1)); [pool[i], pool[j]] = [pool[j], pool[i]];
    }
    explore = pool.slice(0, EXPLORE_N).map(d => d.key);
  }

  // ── markup ────────────────────────────────────────────────────────────────
  function railBtn(id, name, n) {
    return `<button type="button" class="ib-fam${view === id ? ' active' : ''}" data-view="${esc(id)}">` +
           `<span class="ib-fam-name">${esc(name)}</span><span class="ib-fam-n">${n}</span></button>`;
  }
  function renderRail() {
    const all = defs();
    let h = '<div class="ib-rail-head">Yours</div>' +
      railBtn('__fav__', '★ Favorites', favs().size) +
      railBtn('__active__', 'On this chart', all.filter(d => isOn(pane, d.key)).length) +
      railBtn('__recent__', 'Recent', recent().filter(defBy).length) +
      '<div class="ib-rail-head">Library</div>' +
      railBtn('__discover__', 'Discover', '') +
      railBtn('__all__', 'All', all.length);
    (typeof INDICATOR_GROUPS !== 'undefined' ? INDICATOR_GROUPS : []).forEach(g => {
      h += railBtn(g, g, all.filter(d => d.group === g).length);
    });
    return h;
  }
  function renderCard(d) {
    const on = isOn(pane, d.key), off = isDisabled(pane, d.key), fav = favs().has(d.key);
    return `<div class="ib-card${on ? ' on' : ''}${off ? ' disabled' : ''}${selected === d.key ? ' sel' : ''}"` +
      ` data-key="${esc(d.key)}" tabindex="0" role="button" aria-pressed="${selected === d.key}"` +
      ` title="${esc(d.short || d.label)}">` +
      pic(d, false) +
      `<button type="button" class="ib-star${fav ? ' on' : ''}" data-fav="${esc(d.key)}"` +
      ` aria-label="${fav ? 'Remove from' : 'Add to'} favorites" title="${fav ? 'Remove from' : 'Add to'} favorites">${fav ? '★' : '☆'}</button>` +
      `<div class="ib-card-name">${esc(d.label)}</div>` +
      `<div class="ib-card-meta">${esc(d.group)}${d.level ? ' · ' + esc(d.level) : ''}</div>` +
      (on ? '<span class="ib-badge">On chart</span>' : '') +
      (off ? '<span class="ib-badge muted">Off for this symbol</span>' : '') +
      `</div>`;
  }
  function renderChips() {
    const g = window.INDICATOR_GOALS || {};
    return '<div class="ib-chips" role="group" aria-label="What do you want to see?">' +
      '<span class="ib-chips-q">What do you want to see?</span>' +
      Object.keys(g).map(id => `<button type="button" class="ib-chip${goal === id ? ' on' : ''}"` +
        ` data-goal="${esc(id)}" aria-pressed="${goal === id}">${esc(g[id])}</button>`).join('') +
      '</div>';
  }
  function renderDiscover() {
    const row = (title, note, ds) => ds.length
      ? `<div class="ib-row-head">${esc(title)}<span>${esc(note)}</span></div>` +
        '<div class="ib-cards">' + ds.map(renderCard).join('') + '</div>' : '';
    return row('Start here', 'the indicators most charts begin with', START_HERE.map(defBy).filter(Boolean)) +
           row('New on the desk', 'most recently added', newestThree()) +
           row('More to explore', 'a different handful each time', explore.map(defBy).filter(Boolean));
  }
  function renderGrid() {
    if (view === '__discover__' && !query && !goal) return renderChips() + renderDiscover();
    return renderChips() + renderList();
  }
  function renderList() {
    const list = visibleDefs();
    if (!list.length) {
      const msg = query ? 'No indicators match' :
        goal ? 'None in this list answers that — try All.' :
        view === '__fav__' ? 'No favorites yet — tap ☆ on a card.' :
        view === '__active__' ? 'Nothing on this chart yet.' :
        view === '__recent__' ? 'Nothing added recently.' : 'Nothing here.';
      return `<div class="ib-empty">${msg}</div>`;
    }
    const blurb = !query && typeof GROUP_BLURB !== 'undefined' && GROUP_BLURB[view]
      ? `<div class="ib-blurb">${esc(GROUP_BLURB[view])}</div>` : '';
    return blurb + '<div class="ib-cards">' + list.map(renderCard).join('') + '</div>';
  }
  function renderDetail() {
    const d = selected && defBy(selected);
    if (!d) return '<div class="ib-detail-empty">Pick a card to read what it shows, how to read it and when it misleads.</div>';
    const on = isOn(pane, d.key), off = isDisabled(pane, d.key), fav = favs().has(d.key);
    const goals = (d.goals || []).map(g => (window.INDICATOR_GOALS || {})[g]).filter(Boolean);
    const limits = [];
    if (d.whyIntraday) limits.push(d.whyIntraday);
    if (off) limits.push('Switched off for this symbol: it looks like a liquid ETF / cash-equivalent, where momentum readings are noise.');
    return `<button type="button" class="ib-back" data-act="back">‹ Back</button>` +
      pic(d, true) +
      `<div class="ib-d-meta">${esc(d.group)}${d.level ? ' · ' + esc(d.level) : ''}${d.added ? ' · added ' + esc(d.added) : ''}</div>` +
      `<h3 class="ib-d-name">${esc(d.label)}</h3>` +
      (d.short ? `<p class="ib-d-short">${esc(d.short)}</p>` : '') +
      (d.desc ? `<p class="ib-d-desc">${esc(d.desc)}</p>` : '') +
      (d.desc && isDraft() ? '<div class="ib-draft" title="Written by Claude from the code and the wiki; the owner has not reviewed it yet (B-149).">Draft — under review</div>' : '') +
      evidenceRow(d) +
      `<div class="ib-d-row"><b>Draws on</b> ${d.pane === 'sub' ? 'its own pane below the chart (shortens the price chart)' : 'the price chart'}</div>` +
      (goals.length ? `<div class="ib-d-row"><b>Answers</b> ${goals.map(esc).join(' · ')}</div>` : '') +
      limits.map(l => `<div class="ib-d-row warn">${esc(l)}</div>`).join('') +
      `<div class="ib-d-actions">` +
      `<button type="button" class="ib-act primary" data-act="toggle" ${off && !on ? 'disabled' : ''}>${on ? 'Remove from chart' : 'Add to chart'}</button>` +
      `<button type="button" class="ib-act" data-act="fav">${fav ? '★ Favorite' : '☆ Favorite'}</button>` +
      (d.concept ? `<a class="ib-act" href="/learn/${encodeURIComponent(d.key)}" target="_blank" rel="noopener"` +
                   ` title="The desk's wiki page on this idea — opens in a new tab">Learn more ↗</a>` : '') +
      `</div>`;
  }
  function paint(focusKey) {
    if (!root) return;
    const grid = root.querySelector('.ib-grid'), top = grid.scrollTop;
    root.querySelector('.ib-rail').innerHTML = renderRail();
    grid.innerHTML = renderGrid();
    grid.scrollTop = top;
    root.querySelector('.ib-detail').innerHTML = renderDetail();
    root.classList.toggle('has-sel', !!selected);
    // Re-rendering replaces the cards, so keyboard focus would fall to <body>.
    if (focusKey) {
      const c = grid.querySelector(`.ib-card[data-key="${focusKey}"]`);
      if (c) { c.focus({preventScroll: true}); c.scrollIntoView({block: 'nearest'}); }
    }
  }

  // B-155: arrow keys move through the cards in reading order; up/down jump a
  // visual row by matching the nearest card on the next line.
  function moveFocus(from, dir) {
    const cards = [...root.querySelectorAll('.ib-grid .ib-card')];
    if (!cards.length) return null;
    const i = from ? cards.indexOf(from) : -1;
    if (i < 0) return cards[0];
    if (dir === 'ArrowRight') return cards[Math.min(cards.length - 1, i + 1)];
    if (dir === 'ArrowLeft') return cards[Math.max(0, i - 1)];
    const r = from.getBoundingClientRect(), cx = r.left + r.width / 2;
    const down = dir === 'ArrowDown';
    const line = cards.filter(c => {
      const t = c.getBoundingClientRect().top;
      return down ? t > r.top + 4 : t < r.top - 4;
    });
    if (!line.length) return from;
    const rowTop = down ? Math.min(...line.map(c => c.getBoundingClientRect().top))
                        : Math.max(...line.map(c => c.getBoundingClientRect().top));
    const row = line.filter(c => Math.abs(c.getBoundingClientRect().top - rowTop) < 4);
    return row.reduce((a, c) => {
      const d = Math.abs(c.getBoundingClientRect().left + c.getBoundingClientRect().width / 2 - cx);
      return d < a.d ? {c, d} : a;
    }, {c: row[0], d: Infinity}).c;
  }

  function build() {
    root = document.createElement('div');
    root.className = 'ib-overlay';
    root.innerHTML =
      '<div class="ib-backdrop" data-act="close"></div>' +
      '<div class="ib-modal" role="dialog" aria-modal="true" aria-label="Indicators">' +
      '  <div class="ib-head">' +
      '    <div class="ib-title">Indicators <span class="ib-target"></span></div>' +
      '    <input type="text" class="ib-search" placeholder="Search indicators…" spellcheck="false" autocomplete="off" aria-label="Search indicators">' +
      '    <button type="button" class="ib-close" data-act="close" aria-label="Close">✕</button>' +
      '  </div>' +
      '  <div class="ib-body">' +
      '    <nav class="ib-rail" aria-label="Indicator lists"></nav>' +
      '    <div class="ib-grid"></div>' +
      '    <aside class="ib-detail" aria-live="polite"></aside>' +
      '  </div>' +
      '  <div class="ib-foot">' +
      '    <span class="ib-keys"><kbd>/</kbd> search · <kbd>←↑→↓</kbd> move · <kbd>Enter</kbd> add / remove &amp; close · ' +
      '<kbd>Shift</kbd>+<kbd>Enter</kbd> keep open · <kbd>F</kbd> favorite · <kbd>Esc</kbd> close</span>' +
      '    <span class="ib-count"></span>' +
      '    <button type="button" class="ib-classic" data-act="classic" title="Use the compact list instead; switch back from its header">Classic list</button>' +
      '  </div>' +
      '</div>';
    document.body.appendChild(root);

    root.addEventListener('click', e => {
      e.stopPropagation();
      const t = e.target.closest('[data-act],[data-fav],[data-view],[data-goal],.ib-card');
      if (!t) return;
      if (t.dataset.goal) { goal = goal === t.dataset.goal ? null : t.dataset.goal; paint(); return; }
      if (t.dataset.fav) { toggleFav(t.dataset.fav); paint(); return; }
      if (t.dataset.view) {
        view = t.dataset.view; query = ''; root.querySelector('.ib-search').value = '';
        root.querySelector('.ib-grid').scrollTop = 0; paint(); return;
      }
      if (t.classList.contains('ib-card')) { selected = t.dataset.key; paint(selected); return; }
      const act = t.dataset.act;
      if (act === 'close') close();
      else if (act === 'back') { selected = null; paint(); }
      else if (act === 'toggle' && selected) { setOn(pane, selected, !isOn(pane, selected)); paint(); }
      else if (act === 'fav' && selected) { toggleFav(selected); paint(); }
      else if (act === 'classic') { lsSet(LS_CLASSIC, true); const p = pane; close(); openClassic(p); }
    });
    root.addEventListener('dblclick', e => {
      const c = e.target.closest('.ib-card');
      if (c && !e.target.closest('[data-fav]')) { selected = c.dataset.key; setOn(pane, selected, !isOn(pane, selected)); paint(); }
    });
    root.querySelector('.ib-search').addEventListener('input', e => { query = e.target.value; paint(); });
    root.addEventListener('keydown', e => {
      if (e.key === 'Escape') { e.preventDefault(); close(); return; }
      const inSearch = e.target.classList && e.target.classList.contains('ib-search');
      if (e.key === '/' && !inSearch) { e.preventDefault(); root.querySelector('.ib-search').focus(); return; }
      const card = e.target.closest && e.target.closest('.ib-card');
      if (e.key.startsWith('Arrow') && (card || (inSearch && e.key === 'ArrowDown'))) {
        e.preventDefault();
        const next = moveFocus(card, card ? e.key : 'ArrowRight');
        if (next) { selected = next.dataset.key; paint(selected); }
        return;
      }
      if ((e.key === 'f' || e.key === 'F') && card && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault(); toggleFav(card.dataset.key); paint(card.dataset.key); return;
      }
      if (e.key === 'Enter') {
        let key = card ? card.dataset.key : null;
        if (!key && inSearch) {
          const vis = visibleDefs().filter(d => !isDisabled(pane, d.key));
          if (vis.length === 1) key = vis[0].key;
        }
        if (!key) return;
        e.preventDefault();
        selected = key;
        setOn(pane, key, !isOn(pane, key));
        // Enter is "do it and get back to the chart"; Shift+Enter keeps browsing.
        if (e.shiftKey) paint(key); else close();
      }
    });
  }

  function openClassic(p) {
    if (!p || !p.el) return;
    const btn = p.el.querySelector('.ind-btn:not(.snap-btn)');
    const panel = p.el.querySelector('.ind-panel');
    if (typeof closeAllIndicatorPanels === 'function') closeAllIndicatorPanels();
    if (panel) panel.classList.add('open');
    if (btn) btn.classList.add('active');
    const s = panel && panel.querySelector('.ind-search');
    if (s) setTimeout(() => { s.focus(); s.select(); }, 0);
  }

  function open(p) {
    if (!root) build();
    loadThumbs();
    loadEvidence();
    pane = p; selected = null; query = '';
    reshuffle();
    root.querySelector('.ib-search').value = '';
    root.querySelector('.ib-target').textContent = p ? `· adding to ${p.symbol} · ${p.tf}` : '';
    const n = newest();
    root.querySelector('.ib-count').textContent = `${defs().length} indicators` + (n ? ` · newest ${n}` : '');
    root.classList.add('open');
    document.documentElement.classList.add('ib-lock');
    paint();
    setTimeout(() => root.querySelector('.ib-search').focus(), 0);
  }
  function close() {
    if (!root) return;
    root.classList.remove('open');
    document.documentElement.classList.remove('ib-lock');
    if (pane && pane._refreshIndActiveCount) pane._refreshIndActiveCount();
    pane = null;
  }

  window.IndicatorBrowser = {
    open, close,
    isOpen: () => !!(root && root.classList.contains('open')),
    classicPreferred,
    useCards: () => lsSet(LS_CLASSIC, false),
  };
})();

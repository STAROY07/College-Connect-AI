// College Connect AI — Global JS

document.addEventListener('DOMContentLoaded', () => {

  // ── Mobile nav toggle ──────────────────────────────────────
  const navToggle = document.getElementById('nav-toggle');
  const navLinks  = document.getElementById('nav-links');
  if (navToggle && navLinks) {
    navToggle.addEventListener('click', () => {
      navLinks.classList.toggle('open');
    });
    // close on outside click
    document.addEventListener('click', e => {
      if (!navToggle.contains(e.target) && !navLinks.contains(e.target)) {
        navLinks.classList.remove('open');
      }
    });
  }

  // ── Global Search ─────────────────────────────────────────
  const searchInput = document.getElementById('global-search');
  const searchDrop  = document.getElementById('search-drop');
  let searchTimer = null;

  if (searchInput && searchDrop) {
    searchInput.addEventListener('input', () => {
      const q = searchInput.value.trim();
      clearTimeout(searchTimer);
      if (q.length < 2) { hideDrop(); return; }
      searchTimer = setTimeout(() => doSearch(q), 220);
    });

    searchInput.addEventListener('keydown', e => {
      if (e.key === 'Escape') { hideDrop(); searchInput.blur(); }
    });

    document.addEventListener('click', e => {
      if (!searchInput.closest('.nav-search').contains(e.target)) hideDrop();
    });
  }

  async function doSearch(q) {
    try {
      const res  = await fetch('/api/search?q=' + encodeURIComponent(q));
      const data = await res.json();
      renderDrop(data.results || [], q);
    } catch { hideDrop(); }
  }

  let currentSearchResults = [];
  let currentSearchQuery = "";
  let searchResultsLimit = 6;

  function renderDrop(results, q) {
    if (!searchDrop) return;
    currentSearchResults = results;
    currentSearchQuery = q;
    searchResultsLimit = 6;
    renderResultsList();
  }

  function renderResultsList() {
    if (!searchDrop) return;
    if (currentSearchResults.length === 0) {
      searchDrop.innerHTML = `<div class="sd-empty">No results for "<strong>${esc(currentSearchQuery)}</strong>". Try the chatbot.</div>`;
    } else {
      const toShow = currentSearchResults.slice(0, searchResultsLimit);
      const hasMore = currentSearchResults.length > searchResultsLimit;
      
      searchDrop.innerHTML = toShow.map(r =>
        `<a href="${esc(r.url)}" class="sd-item">
          <div class="sd-item-title">
            <span>${esc(r.title)}</span>
            <span class="sd-item-cat">${esc(r.category)}</span>
          </div>
          <div class="sd-item-snip">${esc(r.snippet)}</div>
        </a>`
      ).join('');
      
      if (hasMore) {
        const btnContainer = document.createElement('div');
        btnContainer.className = 'sd-btn-container';
        const btn = document.createElement('button');
        btn.className = 'sd-show-more';
        btn.innerHTML = `View All Results (${currentSearchResults.length} matches)`;
        btn.onclick = (e) => {
            e.preventDefault();
            searchResultsLimit = currentSearchResults.length;
            renderResultsList();
        };
        btnContainer.appendChild(btn);
        searchDrop.appendChild(btnContainer);
      }
    }
    showDrop();
  }

  function showDrop() { if (searchDrop) searchDrop.classList.add('show'); }
  function hideDrop() { if (searchDrop) searchDrop.classList.remove('show'); }

  // ── Utility ──────────────────────────────────────────────
});

function esc(str) {
  if (!str) return '';
  return String(str).replace(/[&<>'"]/g, c =>
    ({ '&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;' }[c])
  );
}

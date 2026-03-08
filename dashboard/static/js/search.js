/* BSS Dashboard — Search Panel */
(function() {
    let debounce = null;

    function load() {
        const input = document.getElementById('search-input');
        if (input && !input._bound) {
            input._bound = true;
            input.addEventListener('input', () => {
                clearTimeout(debounce);
                debounce = setTimeout(doSearch, 300);
            });
        }
    }

    async function doSearch() {
        const q = document.getElementById('search-input').value.trim();
        const results = document.getElementById('search-results');
        if (!q) { results.innerHTML = '<div class="roster-empty">Type to search across all blink summaries</div>'; return; }
        results.innerHTML = '<div class="loading-spinner"></div>';
        const data = await BSS.apiFetch(`/api/search?q=${encodeURIComponent(q)}&limit=50`);
        if (!data || !data.results?.length) { results.innerHTML = '<div class="roster-empty">No results found</div>'; return; }

        const e = BSS.escHtml;
        let html = `<div style="font-size:12px;color:var(--text-muted);margin-bottom:12px">${data.count} result${data.count !== 1 ? 's' : ''} for "${e(q)}"</div>`;
        for (const b of data.results) {
            const color = BSS.sigColor(b.author || '?');
            const summary = highlightTerm(b.summary || '', q);
            html += `<div class="timeline-item" onclick="openBlink('${e(b.blink_id)}')"><span class="timeline-seq">${e((b.blink_id || '').substring(0, 5))}</span><span class="sigil-badge" style="color:${color};border-color:${color};width:28px;height:28px;font-size:12px">${e(b.author || '?')}</span><span class="timeline-action">${BSS.actionIcon(b.action_state || '')}</span><span class="timeline-summary">${summary}</span><span class="timeline-dir">${e(b.directory || '')}</span><span></span></div>`;
        }
        results.innerHTML = html;
    }

    function highlightTerm(text, term) {
        const escaped = BSS.escHtml(text);
        const termEscaped = BSS.escHtml(term);
        const regex = new RegExp(`(${termEscaped.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        return escaped.replace(regex, '<mark>$1</mark>');
    }

    BSS.panels.search = { load };
})();

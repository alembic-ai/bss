/* BSS Dashboard — Timeline Panel */
(function() {
    async function load() {
        const sigil = document.getElementById('timeline-sigil-filter')?.value || '';
        const dir = document.getElementById('timeline-dir-filter')?.value || 'all';
        let url = `/api/blinks?directory=${dir}&limit=200`;
        if (sigil) url += `&sigil=${sigil}`;
        const data = await BSS.apiFetch(url);
        if (!data) return;
        renderChart(data.blinks);
        renderList(data.blinks);
    }

    function renderChart(blinks) {
        const chart = document.getElementById('timeline-chart');
        if (!blinks.length) { chart.innerHTML = '<div style="color:var(--text-muted);text-align:center;width:100%;padding:40px">No data</div>'; return; }
        let html = '';
        const display = blinks.slice(0, 80).reverse();
        for (const b of display) {
            const color = BSS.sigColor(b.author || '?');
            html += `<div class="chart-bar" style="height:80px;background:${color}" data-count="${b.sequence || ''}" title="${b.author || '?'}: ${(b.action_state || '').substring(0, 20)}" onclick="openBlink('${BSS.escHtml(b.blink_id)}')"></div>`;
        }
        chart.innerHTML = html;
    }

    function renderList(blinks) {
        const list = document.getElementById('timeline-list');
        if (!blinks.length) { list.innerHTML = '<div class="roster-empty">No blinks found</div>'; return; }
        const e = BSS.escHtml;
        let html = '';
        for (const b of blinks) {
            const color = BSS.sigColor(b.author || '?');
            html += `<div class="timeline-item" onclick="openBlink('${e(b.blink_id)}')"><span class="timeline-seq">${e(b.sequence || '?')}</span><span class="timeline-author" style="color:${color}">${e(b.author || '?')}</span><span class="timeline-action">${BSS.actionIcon(b.action_state || '')}</span><span class="timeline-summary">${e(b.summary || '')}</span><span class="timeline-dir">${e(b.directory || '')}</span><span class="timeline-priority" style="color:${BSS.priorityColor(b.priority)}">${e(b.priority || '')}</span></div>`;
        }
        list.innerHTML = html;
    }

    // Expose for inline onclick
    window.loadTimeline = load;
    BSS.panels.timeline = { load };
})();

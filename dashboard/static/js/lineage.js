/* BSS Dashboard — Lineage Panel */
(function() {
    const RELATIONAL_ICONS = { 'Origin': '\u2070', 'Continuation': '\u2192', 'Branch': '\u2197', 'Convergence': '\u2199', 'Dead-end': '\u2717', 'Echo': '\u2261', 'Conflict': '\u2694' };

    function load() { /* no auto-load, user triggers via button */ }

    window.loadLineage = async function() {
        const blinkId = document.getElementById('lineage-input').value.trim();
        if (!blinkId || blinkId.length !== 17) { alert('Please enter a valid 17-character blink ID'); return; }
        const data = await BSS.apiFetch(`/api/blinks/${encodeURIComponent(blinkId)}/lineage`);
        if (!data) { document.getElementById('lineage-tree').innerHTML = '<div class="lineage-empty">Blink not found</div>'; return; }

        const tree = document.getElementById('lineage-tree');
        const info = document.getElementById('lineage-info');
        if (!data.chain?.length) { tree.innerHTML = '<div class="lineage-empty">No lineage chain found</div>'; info.innerHTML = ''; return; }

        const e = BSS.escHtml;
        let html = '';
        for (let i = 0; i < data.chain.length; i++) {
            const node = data.chain[i], depth = i * 28, color = BSS.sigColor(node.author || '?');
            const relIcon = RELATIONAL_ICONS[node.relational] || '\u2022';
            const isTarget = node.blink_id === data.blink_id;
            html += `<div class="lineage-node" style="--depth:${depth}px;${isTarget ? 'background:rgba(59,130,246,0.08);border-left-color:var(--accent)' : ''}" onclick="openBlink('${e(node.blink_id)}')"><span class="lineage-connector" style="color:${color}">${relIcon}</span><div class="lineage-content"><div class="lineage-id" style="color:${color}">${e(node.blink_id)} ${isTarget ? '\u2190 target' : ''}</div><div class="lineage-summary-text">${e(node.summary || '')}</div></div><span class="sigil-badge" style="color:${color};border-color:${color};width:24px;height:24px;font-size:10px">${e(node.author || '?')}</span></div>`;
        }
        tree.innerHTML = html;
        info.innerHTML = `<strong>Generation:</strong> ${data.generation} / 7 &nbsp;&nbsp;<strong>Chain length:</strong> ${data.chain.length} &nbsp;&nbsp;${data.needs_convergence ? '<span style="color:var(--warning)">\u26A0 Convergence needed</span>' : '<span style="color:var(--success)">\u2713 Within generation limit</span>'}`;
    };

    BSS.panels.lineage = { load };
})();

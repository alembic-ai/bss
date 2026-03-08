/* BSS Dashboard — Relay Queue Panel */
(function() {
    async function load() {
        const data = await BSS.apiFetch('/api/relay/queue');
        if (!data) return;
        document.getElementById('relay-count-badge').textContent = data.count;
        const container = document.getElementById('relay-queue');
        if (!data.queue.length) { container.innerHTML = '<div class="roster-empty">Relay queue is empty</div>'; return; }
        const e = BSS.escHtml;
        let html = '';
        for (const item of data.queue) {
            const color = BSS.sigColor(item.author || '?');
            html += `<div class="relay-item" onclick="openBlink('${e(item.blink_id)}')"><span class="timeline-seq">${e(item.blink_id.substring(0, 5))}</span><span class="sigil-badge" style="color:${color};border-color:${color};width:28px;height:28px;font-size:12px">${e(item.author || '?')}</span><span style="color:var(--text-dim)">${BSS.actionIcon(item.action_state || '')} ${e(item.summary || '')}</span><span class="role-tag">${e(item.priority || 'Normal')}</span><span class="scope-tag">${e(item.scope || '')}</span></div>`;
        }
        container.innerHTML = html;
    }
    BSS.panels.relay = { load };
})();

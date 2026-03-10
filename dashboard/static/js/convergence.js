/* BSS Dashboard — Convergence Manager */
(function() {
    async function load() {
        const data = await BSS.apiFetch('/api/convergence/candidates');
        if (!data) return;
        const container = document.getElementById('convergence-list');
        const badge = document.getElementById('convergence-count');
        if (badge) badge.textContent = data.candidates?.length || 0;

        if (!data.candidates?.length) {
            container.innerHTML = '<div class="roster-empty">No chains approaching convergence. All chains are within the 7-generation limit.</div>';
            return;
        }

        const e = BSS.escHtml;
        let html = '';
        for (const c of data.candidates) {
            const urgency = c.generation >= 7 ? 'error' : 'warning';
            const color = urgency === 'error' ? 'var(--error)' : 'var(--warning)';
            html += `
                <div class="convergence-item" style="border-left-color:${color}">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                        <span style="color:${color};font-weight:600">Generation ${c.generation}/7</span>
                        <span class="badge ${urgency}">${c.generation >= 7 ? 'MUST CONVERGE' : 'APPROACHING'}</span>
                    </div>
                    <div class="lineage-id" style="cursor:pointer;margin-bottom:4px" onclick="openBlink('${e(c.leaf_blink_id)}')">${e(c.leaf_blink_id)}</div>
                    <div style="font-size:12px;color:var(--text-dim);margin-bottom:8px">${e(c.summary || '')}</div>
                    <div style="font-size:11px;color:var(--text-muted);margin-bottom:8px">Chain: ${c.chain_ids?.map(id => `<span style="cursor:pointer;color:var(--accent)" onclick="openBlink('${e(id)}')">${e(id.substring(0,7))}</span>`).join(' \u2192 ') || 'N/A'}</div>
                    <button class="btn-primary" onclick="triggerConvergence('${e(c.leaf_blink_id)}')" style="font-size:11px;padding:4px 12px">Converge</button>
                </div>
            `;
        }
        container.innerHTML = html;
    }

    window.triggerConvergence = async function(leafBlinkId) {
        const summary = prompt('Enter convergence summary (2+ sentences):');
        if (!summary || summary.split(/[.!?]+/).filter(s => s.trim()).length < 2) {
            alert('Convergence summary must have at least 2 sentences.'); return;
        }
        const data = await BSS.apiPost('/api/convergence/converge', { leaf_blink_id: leafBlinkId, summary });

        if (data.error) {
            alert('Error: ' + (data.error || data.detail));
        } else {
            alert('Convergence blink created: ' + (data.blink_id || 'success'));
            load();
        }
    };

    BSS.panels.convergence = { load };
})();

/* BSS Dashboard — Overview Panel */

(function() {
    const PHASE_DETAILS = {
        INTAKE: { description: 'Read the relay queue, active blinks, and profile data. Build a complete picture of the current environment state.', reads: '/relay/, /active/, /profile/', writes: 'None', color: '#3b82f6' },
        TRIAGE: { description: 'Sort relay blinks by urgency, recency, and scope ceiling. Identify the highest-priority work items.', reads: '/relay/', writes: 'None', color: '#f59e0b' },
        WORK: { description: 'Process triaged items. Generate responses, make decisions, create artifacts. The core processing phase.', reads: '/relay/, /active/, /profile/', writes: '/active/', color: '#10b981' },
        OUTPUT: { description: 'Write results as handoff blinks to /relay/. Archive completed work. Register any generated artifacts.', reads: '/active/', writes: '/relay/, /archive/, /artifacts/', color: '#8b5cf6' },
        DORMANCY: { description: 'Session ends cleanly. All state is persisted in blinks. The next model in the relay can pick up without coordination.', reads: 'None', writes: 'None', color: '#6b7280' },
    };

    async function load() {
        const [status, roster, errors, blinks] = await Promise.all([
            BSS.apiFetch('/api/environment/status'),
            BSS.apiFetch('/api/roster'),
            BSS.apiFetch('/api/relay/errors'),
            BSS.apiFetch('/api/blinks?limit=20'),
        ]);
        if (status) renderStatus(status);
        if (roster) { renderRoster(roster); BSS._rosterCache = roster; }
        if (errors) renderErrors(errors);
        if (blinks) renderRecent(blinks);

        const pill = document.getElementById('status-pill');
        const text = document.getElementById('status-text');
        if (status) {
            text.textContent = 'Connected';
            pill.style.borderColor = 'rgba(16,185,129,0.3)';
            pill.style.background = 'rgba(16,185,129,0.1)';
        } else {
            text.textContent = 'Disconnected';
            pill.style.borderColor = 'rgba(239,68,68,0.3)';
            pill.style.background = 'rgba(239,68,68,0.1)';
        }
    }

    function renderStatus(data) {
        const dirs = data.directories;
        const maxCount = Math.max(...Object.values(dirs), 1);
        for (const [name, count] of Object.entries(dirs)) {
            const el = document.getElementById(`stat-${name}`);
            if (el) el.textContent = count;
            const bar = document.getElementById(`bar-${name}`);
            if (bar) bar.style.width = `${Math.min(100, (count / Math.max(maxCount, 10)) * 100)}%`;
        }
        document.getElementById('stat-sequence').textContent = data.next_sequence || '\u2014';
    }

    function renderRoster(data) {
        const container = document.getElementById('roster-table');
        if (!data.entries?.length) { container.innerHTML = '<div class="roster-empty">No models in roster</div>'; return; }
        const e = BSS.escHtml;
        let html = '<div class="roster-row header"><span>Sigil</span><span>Model</span><span>Role</span><span>Ceiling</span></div>';
        for (const entry of data.entries) {
            const color = BSS.sigColor(entry.sigil);
            html += `<div class="roster-row"><span class="sigil-badge" style="color:${color};border-color:${color}">${e(entry.sigil)}</span><span style="color:${color}">${e(entry.model_id)}</span><span class="role-tag">${e(entry.role)}</span><span class="scope-tag">${e(entry.scope_ceiling)}</span></div>`;
        }
        container.innerHTML = html;
    }

    function renderErrors(data) {
        const badge = document.getElementById('error-count');
        const list = document.getElementById('error-list');
        badge.textContent = data.count;
        data.count > 0 ? badge.classList.add('error') : badge.classList.remove('error');
        if (data.count === 0) { list.innerHTML = '<div class="no-errors">No error escalation chains detected</div>'; return; }
        const e = BSS.escHtml;
        let html = '';
        for (let i = 0; i < data.error_chains.length; i++) {
            html += `<div class="error-chain"><div class="error-chain-title">Chain #${i + 1} (${data.error_chains[i].length} blinks)</div>`;
            for (const b of data.error_chains[i]) html += `<div class="error-blink" onclick="openBlink('${e(b.blink_id)}')">${e(b.blink_id)} \u2014 ${e(b.summary)}</div>`;
            html += '</div>';
        }
        list.innerHTML = html;
    }

    function renderRecent(data) {
        const list = document.getElementById('recent-list');
        if (!data.blinks?.length) { list.innerHTML = '<div class="roster-empty">No blinks found</div>'; return; }
        const e = BSS.escHtml;
        let html = '';
        for (const b of data.blinks) {
            const color = BSS.sigColor(b.author || '?');
            html += `<div class="blink-row" onclick="openBlink('${e(b.blink_id)}')"><span class="blink-seq">${e(b.sequence || '?')}</span><span class="sigil-badge" style="color:${color};border-color:${color};width:24px;height:24px;font-size:11px">${e(b.author || '?')}</span><span class="blink-summary">${BSS.actionIcon(b.action_state || '')} ${e(b.summary || '')}</span><span class="blink-scope">${e(b.scope || '')}</span></div>`;
        }
        list.innerHTML = html;
    }

    // Lifecycle
    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('.phase-node').forEach(node => {
            node.addEventListener('click', () => {
                document.querySelectorAll('.phase-node').forEach(n => n.classList.remove('active'));
                node.classList.add('active');
                const info = PHASE_DETAILS[node.dataset.phase];
                if (!info) return;
                document.getElementById('phase-detail').innerHTML = `<div style="padding:12px 0"><p style="color:${info.color};font-weight:600;margin-bottom:8px">${node.dataset.phase}</p><p class="phase-detail-text">${info.description}</p><div style="display:flex;gap:24px;margin-top:12px;font-size:12px"><span style="color:var(--text-muted)">Reads: <span style="color:var(--text-dim)">${info.reads}</span></span><span style="color:var(--text-muted)">Writes: <span style="color:var(--text-dim)">${info.writes}</span></span></div></div>`;
            });
        });
        const playBtn = document.getElementById('lifecycle-play');
        if (playBtn) playBtn.addEventListener('click', () => {
            const phases = ['intake','triage','work','output','dormancy'];
            let i = 0;
            const iv = setInterval(() => {
                document.querySelectorAll('.phase-node').forEach(n => n.classList.remove('active'));
                const nd = document.getElementById(`phase-${phases[i]}`);
                if (nd) { nd.classList.add('active'); nd.click(); }
                if (++i >= phases.length) { clearInterval(iv); setTimeout(() => document.querySelectorAll('.phase-node').forEach(n => n.classList.remove('active')), 2000); }
            }, 1200);
        });
    });

    BSS.panels.overview = { load };
})();

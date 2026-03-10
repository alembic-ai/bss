/* ═══════════════════════════════════════════════════════════
   BSS Dashboard — Core (shared constants, helpers, navigation)
   ═══════════════════════════════════════════════════════════ */

const BSS = {
    API: '',
    SIGIL_COLORS: {
        A: '#3b82f6', B: '#8b5cf6', C: '#06b6d4', D: '#f59e0b',
        E: '#ef4444', F: '#10b981', G: '#ec4899', H: '#f97316',
        I: '#a78bfa', J: '#34d399', K: '#fb923c', L: '#38bdf8',
        M: '#e879f9', N: '#facc15', O: '#f87171', P: '#94a3b8',
        Q: '#2dd4bf', R: '#c084fc', S: '#fca5a5', T: '#86efac',
        U: '#fde68a', V: '#67e8f9', W: '#d8b4fe', X: '#fda4af',
        Y: '#a3e635', Z: '#818cf8',
    },
    ACTION_ICONS: {
        'Handoff': '\u2B06', 'In progress': '\u23F3', 'Completed': '\u2713',
        'Error': '\u2717', 'Informational': '\u2139', 'Idle': '\u2014',
        'Blocked': '\u26D4', 'Decision needed': '\u2753', 'Awaiting user input': '\u23F8',
        'Cancelled': '\u00D7',
    },
    panels: {},
    _refreshInterval: null,
    _rosterCache: null,
};

BSS._authHeaders = function() {
    const headers = {};
    if (window.__BSS_TOKEN__) {
        headers['Authorization'] = `Bearer ${window.__BSS_TOKEN__}`;
    }
    return headers;
};

BSS.apiFetch = async function(endpoint) {
    try {
        const res = await fetch(`${BSS.API}${endpoint}`, {
            headers: BSS._authHeaders(),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (err) {
        console.error(`API error: ${endpoint}`, err);
        return null;
    }
};

BSS.apiPost = async function(endpoint, body) {
    try {
        const headers = { 'Content-Type': 'application/json', ...BSS._authHeaders() };
        const res = await fetch(`${BSS.API}${endpoint}`, {
            method: 'POST',
            headers,
            body: JSON.stringify(body),
        });
        return await res.json();
    } catch (err) {
        console.error(`API POST error: ${endpoint}`, err);
        return { error: String(err) };
    }
};

BSS.sigColor = function(sigil) {
    return BSS.SIGIL_COLORS[sigil] || '#94a3b8';
};

BSS.actionIcon = function(state) {
    return BSS.ACTION_ICONS[state] || '\u2022';
};

BSS.escHtml = function(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
};

BSS.priorityColor = function(p) {
    if (p === 'Critical') return '#ef4444';
    if (p === 'High') return '#f59e0b';
    if (p === 'Normal') return '#94a3b8';
    if (p === 'Low') return '#6b7280';
    return '#4a5568';
};

// ═══════════ MODAL ═══════════

BSS.openBlink = async function(blinkId) {
    const modal = document.getElementById('blink-modal');
    const content = document.getElementById('modal-content');
    content.innerHTML = '<div class="loading-spinner"></div>';
    modal.classList.add('active');

    const data = await BSS.apiFetch(`/api/blinks/${encodeURIComponent(blinkId)}`);
    if (!data) {
        content.innerHTML = '<p style="color:var(--error)">Failed to load blink</p>';
        return;
    }

    const color = BSS.sigColor(data.metadata?.author || '?');
    const meta = data.metadata || {};
    const e = BSS.escHtml;

    let html = `
        <div class="modal-title" style="color:${color}">${e(data.blink_id)}</div>
        <div class="modal-section">
            <div class="modal-section-title">Summary</div>
            <div class="modal-summary">${e(data.summary || 'No summary')}</div>
        </div>
        <div class="modal-section">
            <div class="modal-section-title">Metadata</div>
            <div class="modal-meta-grid">
                ${['author','action_state','relational','confidence','cognitive','domain','subdomain','scope','maturity','priority','sensitivity'].map(k =>
                    `<div class="modal-meta-item"><span class="modal-meta-key">${k.replace('_',' ')}</span><span class="modal-meta-val">${e(meta[k] || '?')}</span></div>`
                ).join('')}
                <div class="modal-meta-item"><span class="modal-meta-key">Sequence</span><span class="modal-meta-val">${e(meta.sequence || '?')} (${meta.sequence_decimal || '?'})</span></div>
                <div class="modal-meta-item"><span class="modal-meta-key">Directory</span><span class="modal-meta-val">${e(data.directory || '?')}</span></div>
                <div class="modal-meta-item"><span class="modal-meta-key">Immutable</span><span class="modal-meta-val">${data.immutable ? '\u2713 Yes' : '\u2717 No'}</span></div>
            </div>
        </div>`;

    if (data.born_from?.length > 0) {
        html += `<div class="modal-section"><div class="modal-section-title">Born From</div><ul class="modal-lineage">${data.born_from.map(id => `<li>${e(id)}</li>`).join('')}</ul></div>`;
    }
    if (data.lineage?.length > 0) {
        html += `<div class="modal-section"><div class="modal-section-title">Lineage Chain</div><ul class="modal-lineage">${data.lineage.map(id => `<li>${e(id)}</li>`).join('')}</ul></div>`;
    }
    if (data.description) {
        html += `<div class="modal-section"><div class="modal-section-title">Full Description</div><div style="font-size:13px;color:var(--text-dim);white-space:pre-wrap;font-family:monospace;padding:12px;background:var(--bg-surface);border-radius:var(--radius)">${e(data.description)}</div></div>`;
    }
    content.innerHTML = html;
};

BSS.closeModal = function() {
    document.getElementById('blink-modal').classList.remove('active');
};

// Global aliases for onclick handlers in HTML
function openBlink(id) { BSS.openBlink(id); }
function closeModal() { BSS.closeModal(); }

// ═══════════ NAVIGATION ═══════════

document.addEventListener('DOMContentLoaded', () => {
    // Tab navigation (direct tabs)
    document.querySelectorAll('.nav-tab[data-panel]').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            tab.classList.add('active');
            const panel = document.getElementById(`panel-${tab.dataset.panel}`);
            if (panel) panel.classList.add('active');
            const p = BSS.panels[tab.dataset.panel];
            if (p && p.load) p.load();
        });
    });

    // Tools dropdown items
    document.querySelectorAll('.nav-dropdown-item[data-panel]').forEach(item => {
        item.addEventListener('click', () => {
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            // Highlight the dropdown trigger
            const trigger = document.querySelector('.nav-dropdown-trigger');
            if (trigger) trigger.classList.add('active');
            const panel = document.getElementById(`panel-${item.dataset.panel}`);
            if (panel) panel.classList.add('active');
            const handler = BSS.panels[item.dataset.panel];
            if (handler && handler.load) handler.load();
        });
    });

    // Modal events
    document.addEventListener('click', (e) => { if (e.target.classList.contains('modal-overlay')) BSS.closeModal(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') BSS.closeModal(); });

    // Load overview on start
    if (BSS.panels.overview && BSS.panels.overview.load) BSS.panels.overview.load();

    // Auto-refresh overview every 10s
    BSS._refreshInterval = setInterval(() => {
        const activePanel = document.querySelector('.panel.active');
        if (activePanel && activePanel.id === 'panel-overview' && BSS.panels.overview) {
            BSS.panels.overview.load();
        }
    }, 10000);
});

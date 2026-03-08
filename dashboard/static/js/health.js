/* BSS Dashboard — Health Monitor, Artifacts, Models */
(function() {
    async function load() {
        const [health, artifacts, models] = await Promise.all([
            BSS.apiFetch('/api/health'),
            BSS.apiFetch('/api/artifacts'),
            BSS.apiFetch('/api/models'),
        ]);
        if (health) renderHealth(health);
        if (artifacts) renderArtifacts(artifacts);
        if (models) renderModels(models);
    }

    function renderHealth(data) {
        const container = document.getElementById('health-checks');
        if (!container) return;
        const e = BSS.escHtml;
        let html = '';
        for (const check of (data.checks || [])) {
            const icon = check.status === 'ok' ? '\u2713' : check.status === 'warning' ? '\u26A0' : '\u2717';
            const color = check.status === 'ok' ? 'var(--success)' : check.status === 'warning' ? 'var(--warning)' : 'var(--error)';
            html += `<div class="health-check"><span style="color:${color};font-size:18px;width:24px">${icon}</span><div><div style="font-weight:600">${e(check.name)}</div><div style="font-size:12px;color:var(--text-dim)">${e(check.detail)}</div></div></div>`;
        }
        container.innerHTML = html || '<div class="roster-empty">No health data</div>';
    }

    function renderArtifacts(data) {
        const container = document.getElementById('artifacts-list');
        if (!container) return;
        if (!data.artifacts?.length) { container.innerHTML = '<div class="roster-empty">No artifacts registered</div>'; return; }
        const e = BSS.escHtml;
        let html = '';
        for (const a of data.artifacts) {
            const sizeKb = (a.size / 1024).toFixed(1);
            html += `<div class="artifact-item"><span style="color:var(--accent)">\uD83D\uDCC4</span><div><div style="font-weight:500">${e(a.name)}</div><div style="font-size:11px;color:var(--text-muted)">${sizeKb} KB</div></div></div>`;
        }
        container.innerHTML = html;
    }

    function renderModels(data) {
        const container = document.getElementById('models-list');
        if (!container) return;
        if (data.error) { container.innerHTML = `<div class="roster-empty">${BSS.escHtml(data.error)}</div>`; return; }
        const e = BSS.escHtml;
        let html = '';
        if (data.loaded) html += `<div style="margin-bottom:12px;color:var(--success)">Loaded: <strong>${e(data.loaded)}</strong></div>`;
        const models = data.available || {};
        if (Object.keys(models).length === 0) { container.innerHTML = '<div class="roster-empty">No models configured</div>'; return; }
        for (const [sigil, config] of Object.entries(models)) {
            const color = BSS.sigColor(sigil);
            const isLoaded = data.loaded === sigil;
            html += `<div class="model-item${isLoaded ? ' active' : ''}"><span class="sigil-badge" style="color:${color};border-color:${color}">${e(sigil)}</span><div><div style="color:${color};font-weight:500">${e(config.name || config.model || sigil)}</div><div style="font-size:11px;color:var(--text-muted)">${e(config.backend || 'unknown')} ${isLoaded ? '\u2022 LOADED' : ''}</div></div></div>`;
        }
        container.innerHTML = html;
    }

    BSS.panels.health = { load };
})();

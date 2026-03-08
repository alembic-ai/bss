/* BSS Dashboard — Settings Panel */
(function() {
    let currentConfig = {};

    async function load() {
        const container = document.getElementById('settings-content');
        if (!container) return;
        container.innerHTML = '<div class="loading-spinner"></div>';

        const [config, env] = await Promise.all([
            BSS.apiFetch('/api/settings/config'),
            BSS.apiFetch('/api/settings/environment'),
        ]);
        currentConfig = config?.models || {};

        const e = BSS.escHtml;
        let html = '';

        // ── Environment Section ──
        html += `<div class="settings-section">
            <h3 class="settings-section-title">Environment</h3>
            <div class="settings-env-grid">
                <div class="settings-env-item"><span class="settings-env-label">Path</span><span class="settings-env-value">${e(env?.path || '—')}</span></div>
                <div class="settings-env-item"><span class="settings-env-label">Total Blinks</span><span class="settings-env-value">${env?.total_blinks || 0}</span></div>
                <div class="settings-env-item"><span class="settings-env-label">Onboarding</span><span class="settings-env-value">${env?.onboarding_complete ? '<span style="color:var(--success)">Complete</span>' : '<span style="color:var(--warning)">Incomplete</span>'}</span></div>
            </div>
            <div class="settings-dir-counts">
                ${Object.entries(env?.directories || {}).map(([d, c]) =>
                    `<span class="settings-dir-badge">${e(d)} <strong>${c}</strong></span>`
                ).join('')}
            </div>
        </div>`;

        // ── Models Section ──
        html += `<div class="settings-section">
            <h3 class="settings-section-title">Configured Models
                <button class="btn-primary btn-sm" onclick="BSS._settingsAddModel()">+ Add Model</button>
            </h3>
            <div id="settings-models-list" class="settings-models-grid">`;

        if (Object.keys(currentConfig).length === 0) {
            html += '<div class="roster-empty">No models configured. Add a model or scan for backends.</div>';
        } else {
            for (const [sigil, cfg] of Object.entries(currentConfig)) {
                const color = BSS.sigColor(sigil);
                html += renderModelCard(sigil, cfg, color);
            }
        }
        html += '</div></div>';

        // ── Discovery Section ──
        html += `<div class="settings-section">
            <h3 class="settings-section-title">Backend Discovery
                <button class="btn-primary btn-sm" onclick="BSS._settingsScan()">Scan for Backends</button>
            </h3>
            <div id="settings-discovery-results" class="settings-discovery-results">
                <div class="roster-empty">Click "Scan for Backends" to detect available model backends.</div>
            </div>
        </div>`;

        // ── Gateway Section ──
        html += `<div class="settings-section">
            <h3 class="settings-section-title">Terminal Gateway</h3>
            <div class="settings-gateway">
                <p style="color:var(--text-dim);margin-bottom:12px">Launch the BSS terminal gateway for TUI-based setup, onboarding, and advanced configuration.</p>
                <button class="btn-primary" onclick="BSS._settingsLaunchGateway()">Launch Terminal Gateway</button>
                <span id="settings-gateway-status" style="margin-left:12px;color:var(--text-dim)"></span>
            </div>
        </div>`;

        container.innerHTML = html;
    }

    function renderModelCard(sigil, cfg, color) {
        const e = BSS.escHtml;
        const backend = cfg.backend || 'unknown';
        const model = cfg.model || cfg.path || '—';
        const name = cfg.name || `Model ${sigil}`;
        const url = cfg.base_url || '';

        return `<div class="settings-model-card">
            <div class="settings-model-header">
                <span class="sigil-badge" style="background:${color}">${e(sigil)}</span>
                <span class="settings-model-name">${e(name)}</span>
                <span class="settings-model-backend">${e(backend)}</span>
            </div>
            <div class="settings-model-details">
                <div><span class="settings-detail-label">Model:</span> ${e(model)}</div>
                ${url ? `<div><span class="settings-detail-label">URL:</span> ${e(url)}</div>` : ''}
                ${cfg.max_tokens ? `<div><span class="settings-detail-label">Max tokens:</span> ${cfg.max_tokens}</div>` : ''}
                ${cfg.temperature != null ? `<div><span class="settings-detail-label">Temperature:</span> ${cfg.temperature}</div>` : ''}
            </div>
            <div class="settings-model-actions">
                <button class="btn-icon" onclick="BSS._settingsEditModel('${e(sigil)}')" title="Edit">\u270F\uFE0F</button>
                <button class="btn-icon" onclick="BSS._settingsRemoveModel('${e(sigil)}')" title="Remove">\u274C</button>
            </div>
        </div>`;
    }

    // ── Add Model ──
    BSS._settingsAddModel = function() {
        showModelForm(null, {});
    };

    // ── Edit Model ──
    BSS._settingsEditModel = function(sigil) {
        showModelForm(sigil, currentConfig[sigil] || {});
    };

    // ── Remove Model ──
    BSS._settingsRemoveModel = async function(sigil) {
        if (!confirm(`Remove model ${sigil}? This updates config.yaml.`)) return;
        delete currentConfig[sigil];
        await saveConfig();
        load();
    };

    function showModelForm(existingSigil, cfg) {
        const modal = document.getElementById('blink-modal');
        const content = document.getElementById('modal-content');
        const isEdit = existingSigil !== null;
        const e = BSS.escHtml;

        const backends = ['openai', 'gguf', 'anthropic', 'gemini', 'huggingface'];

        content.innerHTML = `
            <div class="modal-title">${isEdit ? 'Edit' : 'Add'} Model</div>
            <div class="settings-model-form">
                <div class="composer-row">
                    <div class="composer-field">
                        <label>Sigil (A-Z)</label>
                        <input type="text" id="sf-sigil" maxlength="1" value="${e(existingSigil || '')}" ${isEdit ? 'disabled' : ''} placeholder="A" style="text-transform:uppercase">
                    </div>
                    <div class="composer-field">
                        <label>Name</label>
                        <input type="text" id="sf-name" value="${e(cfg.name || '')}" placeholder="My Model">
                    </div>
                    <div class="composer-field">
                        <label>Backend</label>
                        <select id="sf-backend" onchange="BSS._settingsBackendChanged()">
                            ${backends.map(b => `<option value="${b}" ${cfg.backend === b ? 'selected' : ''}>${b}</option>`).join('')}
                        </select>
                    </div>
                </div>
                <div id="sf-backend-fields"></div>
                <div class="composer-row" style="margin-top:16px">
                    <div class="composer-field">
                        <label>Max Tokens</label>
                        <input type="number" id="sf-max-tokens" value="${cfg.max_tokens || 1024}" min="1">
                    </div>
                    <div class="composer-field">
                        <label>Temperature</label>
                        <input type="number" id="sf-temperature" value="${cfg.temperature != null ? cfg.temperature : 0.7}" min="0" max="2" step="0.1">
                    </div>
                </div>
                <div style="margin-top:16px;display:flex;gap:8px">
                    <button class="btn-primary" onclick="BSS._settingsSaveModel('${e(existingSigil || '')}')">${isEdit ? 'Update' : 'Add'} Model</button>
                    <button class="btn-secondary" onclick="BSS.closeModal()">Cancel</button>
                    <span id="sf-test-result" style="margin-left:auto;color:var(--text-dim)"></span>
                    <button class="btn-secondary" onclick="BSS._settingsTestFromForm()">Test Connection</button>
                </div>
            </div>`;

        modal.classList.add('active');
        BSS._settingsBackendChanged(cfg);
    }

    BSS._settingsBackendChanged = function(prefill) {
        const backend = document.getElementById('sf-backend').value;
        const container = document.getElementById('sf-backend-fields');
        const cfg = prefill || {};
        const e = BSS.escHtml;

        let html = '<div class="composer-row">';
        if (backend === 'openai') {
            html += `
                <div class="composer-field"><label>Base URL</label><input type="text" id="sf-base-url" value="${e(cfg.base_url || 'http://localhost:11434/v1')}" placeholder="http://localhost:11434/v1"></div>
                <div class="composer-field"><label>Model ID</label><input type="text" id="sf-model" value="${e(cfg.model || '')}" placeholder="phi3:mini"></div>
                <div class="composer-field"><label>API Key (optional)</label><input type="password" id="sf-api-key" value="${e(cfg.api_key || '')}" placeholder="sk-..."></div>`;
        } else if (backend === 'gguf') {
            html += `
                <div class="composer-field" style="flex:2"><label>GGUF File Path</label><input type="text" id="sf-path" value="${e(cfg.path || '')}" placeholder="/path/to/model.gguf"></div>
                <div class="composer-field"><label>Context Length</label><input type="number" id="sf-ctx" value="${cfg.n_ctx || 2048}" min="512"></div>`;
        } else if (backend === 'anthropic') {
            html += `
                <div class="composer-field"><label>API Key</label><input type="password" id="sf-api-key" value="${e(cfg.api_key || '')}" placeholder="sk-ant-..."></div>
                <div class="composer-field"><label>Model</label><input type="text" id="sf-model" value="${e(cfg.model || 'claude-opus-4-6')}" placeholder="claude-opus-4-6"></div>`;
        } else if (backend === 'gemini') {
            html += `
                <div class="composer-field"><label>API Key</label><input type="password" id="sf-api-key" value="${e(cfg.api_key || '')}" placeholder="AIza..."></div>
                <div class="composer-field"><label>Model</label><input type="text" id="sf-model" value="${e(cfg.model || 'gemini-2.5-flash')}" placeholder="gemini-2.5-flash"></div>`;
        } else if (backend === 'huggingface') {
            html += `
                <div class="composer-field"><label>HF Token</label><input type="password" id="sf-api-key" value="${e(cfg.api_key || '')}" placeholder="hf_..."></div>
                <div class="composer-field"><label>Model</label><input type="text" id="sf-model" value="${e(cfg.model || '')}" placeholder="mistralai/Mistral-7B-Instruct-v0.3"></div>`;
        }
        html += '</div>';
        container.innerHTML = html;
    };

    BSS._settingsSaveModel = async function(existingSigil) {
        const sigil = (document.getElementById('sf-sigil').value || '').toUpperCase().trim();
        if (!sigil || sigil.length !== 1 || sigil < 'A' || sigil > 'Z') {
            alert('Sigil must be a single letter A-Z');
            return;
        }
        const backend = document.getElementById('sf-backend').value;
        const cfg = {
            backend,
            name: document.getElementById('sf-name').value.trim() || `Model ${sigil}`,
            max_tokens: parseInt(document.getElementById('sf-max-tokens').value) || 1024,
            temperature: parseFloat(document.getElementById('sf-temperature').value) || 0.7,
        };

        // Backend-specific fields
        const model = document.getElementById('sf-model');
        const baseUrl = document.getElementById('sf-base-url');
        const apiKey = document.getElementById('sf-api-key');
        const path = document.getElementById('sf-path');
        const ctx = document.getElementById('sf-ctx');

        if (model) cfg.model = model.value.trim();
        if (baseUrl) cfg.base_url = baseUrl.value.trim();
        if (apiKey && apiKey.value.trim()) cfg.api_key = apiKey.value.trim();
        if (path) cfg.path = path.value.trim();
        if (ctx) cfg.n_ctx = parseInt(ctx.value) || 2048;

        // Remove old sigil if renamed
        if (existingSigil && existingSigil !== sigil) {
            delete currentConfig[existingSigil];
        }
        currentConfig[sigil] = cfg;

        await saveConfig();
        BSS.closeModal();
        load();
    };

    BSS._settingsTestFromForm = async function() {
        const backend = document.getElementById('sf-backend').value;
        const baseUrl = document.getElementById('sf-base-url')?.value || '';
        const apiKey = document.getElementById('sf-api-key')?.value || '';
        const result = document.getElementById('sf-test-result');
        result.textContent = 'Testing...';
        result.style.color = 'var(--text-dim)';

        const data = await fetch('/api/settings/test', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({backend, base_url: baseUrl, api_key: apiKey}),
        }).then(r => r.json()).catch(() => ({ok: false, message: 'Request failed'}));

        result.textContent = data.message || (data.ok ? 'OK' : 'Failed');
        result.style.color = data.ok ? 'var(--success)' : 'var(--error)';
    };

    async function saveConfig() {
        await fetch('/api/settings/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({models: currentConfig}),
        });
    }

    // ── Backend Discovery ──
    BSS._settingsScan = async function() {
        const container = document.getElementById('settings-discovery-results');
        container.innerHTML = '<div class="loading-spinner"></div>';

        const data = await BSS.apiFetch('/api/settings/discover');
        if (!data?.results?.length) {
            container.innerHTML = '<div class="roster-empty">No backends detected. Make sure Ollama is running, API keys are set, or GGUF files are in ./mind/</div>';
            return;
        }

        const e = BSS.escHtml;
        let html = `<div style="color:var(--text-dim);margin-bottom:8px">Scanned in ${data.elapsed}s — found ${data.results.length} backend(s)</div>`;
        for (const r of data.results) {
            const icon = {gguf: '\uD83D\uDCBE', openai: '\uD83C\uDF10', anthropic: '\uD83E\uDDE0', gemini: '\u2728', huggingface: '\uD83E\uDD17'}[r.backend] || '\u2699';
            html += `<div class="settings-discovery-item">
                <span class="settings-discovery-icon">${icon}</span>
                <div class="settings-discovery-info">
                    <div class="settings-discovery-label">${e(r.label)}</div>
                    <div class="settings-discovery-meta">${e(r.backend)} \u2022 ${e(r.source)}</div>
                </div>
                <button class="btn-primary btn-sm" onclick="BSS._settingsAddFromDiscovery(${e(JSON.stringify(JSON.stringify(r)))})">Add</button>
            </div>`;
        }
        container.innerHTML = html;
    };

    BSS._settingsAddFromDiscovery = function(jsonStr) {
        const r = JSON.parse(jsonStr);
        const cfg = {backend: r.backend};
        if (r.details.model) cfg.model = r.details.model;
        if (r.details.base_url) cfg.base_url = r.details.base_url;
        if (r.details.path) cfg.path = r.details.path;
        showModelForm(null, cfg);
    };

    // ── Gateway ──
    BSS._settingsLaunchGateway = async function() {
        const status = document.getElementById('settings-gateway-status');
        status.textContent = 'Launching...';
        const data = await fetch('/api/settings/gateway/launch', {method: 'POST'}).then(r => r.json()).catch(() => ({ok: false}));
        status.textContent = data.ok ? 'Gateway launched in terminal' : 'Failed to launch';
        status.style.color = data.ok ? 'var(--success)' : 'var(--error)';
    };

    BSS.panels.settings = { load };
})();

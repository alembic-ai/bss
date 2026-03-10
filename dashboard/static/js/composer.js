/* BSS Dashboard — Blink Composer */
(function() {
    async function load() {
        // Populate author dropdown from roster
        const select = document.getElementById('composer-author');
        if (select && select.options.length <= 1) {
            const roster = BSS._rosterCache || await BSS.apiFetch('/api/roster');
            if (roster?.entries) {
                for (const e of roster.entries) {
                    const opt = document.createElement('option');
                    opt.value = e.sigil; opt.textContent = `${e.sigil} \u2014 ${e.model_id}`;
                    select.appendChild(opt);
                }
            }
        }
    }

    window.composeBlink = async function() {
        const summary = document.getElementById('composer-summary').value.trim();
        const author = document.getElementById('composer-author').value;
        const energy = document.getElementById('composer-energy').value;
        const valence = document.getElementById('composer-valence').value;
        const domain = document.getElementById('composer-domain').value;
        const subdomain = document.getElementById('composer-subdomain').value;
        const scope = document.getElementById('composer-scope').value;
        const parent = document.getElementById('composer-parent').value.trim();

        if (!summary || summary.split(/[.!?]+/).filter(s => s.trim()).length < 2) {
            alert('Summary must have at least 2 sentences.'); return;
        }
        if (!author) { alert('Please select an author sigil.'); return; }

        if (!confirm('Blinks are immutable once created. Continue?')) return;

        const result = document.getElementById('composer-result');
        result.innerHTML = '<div class="loading-spinner"></div>';

        const data = await BSS.apiPost('/api/blinks/compose', { summary, author, action_energy: energy, action_valence: valence, domain, subdomain, scope, parent: parent || null });

        if (data.error) {
            result.innerHTML = `<div style="color:var(--error);padding:12px">\u2717 Error: ${BSS.escHtml(data.error || data.detail || 'Unknown error')}</div>`;
        } else {
            result.innerHTML = `<div style="color:var(--success);padding:12px">\u2713 Blink created: <span style="font-family:monospace;color:var(--accent);cursor:pointer" onclick="openBlink('${BSS.escHtml(data.blink_id)}')">${BSS.escHtml(data.blink_id)}</span></div>`;
            document.getElementById('composer-summary').value = '';
            document.getElementById('composer-parent').value = '';
        }
    };

    BSS.panels.composer = { load };
})();

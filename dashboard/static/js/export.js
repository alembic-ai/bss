/* BSS Dashboard — Export / Report Generator */
(function() {
    function load() {
        // Populate author checkboxes from roster
        populateAuthors();
    }

    async function populateAuthors() {
        const container = document.getElementById('export-authors');
        if (!container || container._populated) return;
        container._populated = true;
        const roster = BSS._rosterCache || await BSS.apiFetch('/api/roster');
        if (roster?.entries) {
            for (const entry of roster.entries) {
                const color = BSS.sigColor(entry.sigil);
                container.innerHTML += `<label class="export-author-label" style="color:${color}"><input type="checkbox" value="${BSS.escHtml(entry.sigil)}" checked> ${BSS.escHtml(entry.sigil)} \u2014 ${BSS.escHtml(entry.model_id)}</label>`;
            }
        }
    }

    window.generateReport = async function() {
        const result = document.getElementById('export-result');
        result.innerHTML = '<div class="loading-spinner"></div>';

        const format = document.getElementById('export-format').value;
        const sections = [...document.querySelectorAll('#export-sections input:checked')].map(cb => cb.value);
        const authors = [...document.querySelectorAll('#export-authors input:checked')].map(cb => cb.value);
        const title = document.getElementById('export-title').value.trim() || 'BSS Swarm Report';

        if (!sections.length) {
            result.innerHTML = '<div style="color:var(--error);padding:12px">Select at least one section to include.</div>';
            return;
        }

        const data = await fetch('/api/export/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ format, sections, authors, title }),
        }).then(r => r.json()).catch(e => ({ error: String(e) }));

        if (data.error) {
            result.innerHTML = `<div style="color:var(--error);padding:12px">${BSS.escHtml(data.error)}</div>`;
            return;
        }

        // Render preview
        const e = BSS.escHtml;
        let html = `
            <div class="export-preview-header">
                <h4>${e(data.title || title)}</h4>
                <div class="export-preview-actions">
                    <button class="btn-primary" onclick="downloadReport()">Download ${format.toUpperCase()}</button>
                    <button class="btn-icon" onclick="copyReport()" title="Copy to clipboard">\uD83D\uDCCB</button>
                </div>
            </div>
            <pre class="export-preview-content" id="export-content">${e(data.content || '')}</pre>`;
        result.innerHTML = html;
    };

    window.downloadReport = function() {
        const content = document.getElementById('export-content')?.textContent;
        if (!content) return;
        const format = document.getElementById('export-format').value;
        const ext = format === 'json' ? 'json' : 'md';
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `bss-report.${ext}`;
        a.click();
        URL.revokeObjectURL(url);
    };

    window.copyReport = function() {
        const content = document.getElementById('export-content')?.textContent;
        if (content) {
            navigator.clipboard.writeText(content).then(() => {
                const btn = document.querySelector('.export-preview-actions .btn-icon');
                if (btn) { btn.textContent = '\u2713'; setTimeout(() => btn.textContent = '\uD83D\uDCCB', 1500); }
            });
        }
    };

    BSS.panels.export = { load };
})();

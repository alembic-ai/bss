/* BSS Dashboard — Artifact Viewer */
(function() {
    async function load() {
        const data = await BSS.apiFetch('/api/artifacts/detailed');
        if (!data) return;
        const container = document.getElementById('artifacts-viewer');
        if (!data.artifacts?.length) {
            container.innerHTML = '<div class="roster-empty">No artifacts found. Artifacts are created when models produce files during relay sessions.</div>';
            return;
        }
        const e = BSS.escHtml;
        let html = '<div class="artifacts-grid">';
        for (const a of data.artifacts) {
            const sizeStr = formatSize(a.size || 0);
            const ext = (a.name || '').split('.').pop()?.toLowerCase() || '';
            const icon = getFileIcon(ext);
            const previewable = ['txt', 'md', 'json', 'py', 'js', 'yml', 'yaml', 'toml', 'cfg', 'log', 'csv'].includes(ext);

            html += `
                <div class="artifact-card">
                    <div class="artifact-icon">${icon}</div>
                    <div class="artifact-info">
                        <div class="artifact-name">${e(a.name)}</div>
                        <div class="artifact-meta">${sizeStr} \u2022 .${e(ext)}</div>
                    </div>
                    <div class="artifact-actions">
                        ${previewable ? `<button class="btn-icon" onclick="previewArtifact('${e(a.path)}')" title="Preview">\u{1F441}</button>` : ''}
                        <a href="/api/artifacts/download/${encodeURIComponent(a.name)}" class="btn-icon" download title="Download">\u2B07</a>
                    </div>
                </div>`;
        }
        html += '</div>';
        container.innerHTML = html;
    }

    window.previewArtifact = async function(path) {
        const data = await BSS.apiFetch(`/api/artifacts/preview?path=${encodeURIComponent(path)}`);
        if (!data) return;
        const modal = document.getElementById('blink-modal');
        const content = document.getElementById('modal-content');
        const e = BSS.escHtml;
        content.innerHTML = `
            <div class="modal-title">${e(data.name || 'Artifact')}</div>
            <div class="modal-section">
                <div class="modal-section-title">Preview</div>
                <pre class="artifact-preview-content">${e(data.content || 'No content')}</pre>
            </div>`;
        modal.classList.add('active');
    };

    function formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    function getFileIcon(ext) {
        const icons = {
            py: '\uD83D\uDC0D', js: '\uD83D\uDFE8', json: '{}', md: '\uD83D\uDCDD',
            txt: '\uD83D\uDCC4', yml: '\u2699', yaml: '\u2699', toml: '\u2699',
            csv: '\uD83D\uDCCA', log: '\uD83D\uDCCB', pdf: '\uD83D\uDCC5',
            png: '\uD83D\uDDBC', jpg: '\uD83D\uDDBC', gif: '\uD83D\uDDBC',
        };
        return icons[ext] || '\uD83D\uDCC4';
    }

    BSS.panels.artifacts = { load };
})();

/* BSS Dashboard — Reference Panel */
(function() {
    let loaded = false;
    async function load() {
        if (loaded) return;
        const data = await BSS.apiFetch('/api/sigils');
        if (!data) return;
        loaded = true;
        const tables = [
            {key:'action_states',title:'Action States',color:'#fbbf24'},{key:'relational',title:'Relational',color:'#34d399'},
            {key:'confidence',title:'Confidence',color:'#a78bfa'},{key:'cognitive',title:'Cognitive',color:'#fb923c'},
            {key:'domain',title:'Domain',color:'#38bdf8'},{key:'subdomain',title:'Subdomain',color:'#4ade80'},
            {key:'scope',title:'Scope',color:'#e879f9'},{key:'maturity',title:'Maturity',color:'#facc15'},
            {key:'priority',title:'Priority',color:'#f87171'},{key:'sensitivity',title:'Sensitivity',color:'#94a3b8'},
            {key:'action_energy',title:'Action Energy',color:'#fbbf24'},{key:'action_valence',title:'Action Valence',color:'#fbbf24'},
        ];
        const e = BSS.escHtml;
        let html = '';
        for (const t of tables) {
            const entries = data[t.key]; if (!entries) continue;
            html += `<div class="reference-card"><div class="reference-card-header" style="color:${t.color}">${t.title}</div><div class="reference-entries">`;
            for (const [sym, meaning] of Object.entries(entries)) {
                html += `<div class="ref-entry"><span class="ref-symbol" style="color:${t.color}">${e(sym)}</span><span class="ref-meaning">${e(meaning)}</span></div>`;
            }
            html += '</div></div>';
        }
        document.getElementById('reference-grid').innerHTML = html;
    }
    BSS.panels.reference = { load };
})();

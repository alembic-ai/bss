/* BSS Dashboard — Grammar Explorer Panel */
(function() {
    function load() { /* no auto-load */ }

    window.analyzeGrammar = async function() {
        const blinkId = document.getElementById('grammar-input').value.trim();
        if (!blinkId || blinkId.length !== 17) { alert('Please enter a valid 17-character blink ID'); return; }
        const data = await BSS.apiFetch(`/api/sigils/describe/${encodeURIComponent(blinkId)}`);
        if (!data) { document.getElementById('grammar-breakdown').innerHTML = '<div class="roster-empty">Invalid blink ID</div>'; return; }
        renderVisual(blinkId, data);
        renderBreakdown(data);
    };

    function renderVisual(id, data) {
        const positions = [
            { chars: id.slice(0,5), cls: 'seq', name: 'Sequence' }, { chars: id[5], cls: 'author', name: 'Author' },
            { chars: id[6], cls: 'action', name: 'Energy' }, { chars: id[7], cls: 'action', name: 'Valence' },
            { chars: id[8], cls: 'rel', name: 'Relational' }, { chars: id[9], cls: 'conf', name: 'Confidence' },
            { chars: id[10], cls: 'cog', name: 'Cognitive' }, { chars: id[11], cls: 'dom', name: 'Domain' },
            { chars: id[12], cls: 'sub', name: 'Subdomain' }, { chars: id[13], cls: 'scope', name: 'Scope' },
            { chars: id[14], cls: 'mat', name: 'Maturity' }, { chars: id[15], cls: 'pri', name: 'Priority' },
            { chars: id[16], cls: 'sens', name: 'Sensitivity' },
        ];
        const charHtml = positions.map(p => `<span class="gp ${p.cls}" title="${p.name}">${BSS.escHtml(p.chars)}</span>`).join('');
        document.getElementById('grammar-visual').innerHTML = `<div style="margin-bottom:12px;color:var(--text-muted);font-size:13px">Analyzed ID:</div><div class="grammar-format">${charHtml}</div><div style="margin-top:16px;color:var(--accent);font-size:13px">${data.positions.action_state || ''}</div>`;
    }

    function renderBreakdown(data) {
        const fields = [
            {key:'sequence',label:'Sequence',color:'#60a5fa'},{key:'author',label:'Author',color:'#f472b6'},
            {key:'action_energy',label:'Action Energy',color:'#fbbf24'},{key:'action_valence',label:'Action Valence',color:'#fbbf24'},
            {key:'relational',label:'Relational',color:'#34d399'},{key:'confidence',label:'Confidence',color:'#a78bfa'},
            {key:'cognitive',label:'Cognitive',color:'#fb923c'},{key:'domain',label:'Domain',color:'#38bdf8'},
            {key:'subdomain',label:'Subdomain',color:'#4ade80'},{key:'scope',label:'Scope',color:'#e879f9'},
            {key:'maturity',label:'Maturity',color:'#facc15'},{key:'priority',label:'Priority',color:'#f87171'},
            {key:'sensitivity',label:'Sensitivity',color:'#94a3b8'},
        ];
        const e = BSS.escHtml;
        let html = '';
        for (const f of fields) {
            const pos = data.positions[f.key]; if (!pos) continue;
            const value = typeof pos === 'object' ? (pos.value || '') : pos;
            const meaning = typeof pos === 'object' ? (pos.meaning || pos.decimal || '') : '';
            html += `<div class="grammar-position"><div class="grammar-pos-name" style="color:${f.color}">${f.label}</div><div class="grammar-pos-value" style="color:${f.color}">${e(String(value))}</div><div class="grammar-pos-meaning">${e(String(meaning))}</div></div>`;
        }
        html += `<div class="grammar-position" style="grid-column:1/-1;border-color:var(--warning)"><div class="grammar-pos-name" style="color:var(--warning)">Combined Action State</div><div class="grammar-pos-value" style="color:var(--warning)">${e(data.positions.action_state || '?')}</div><div class="grammar-pos-meaning">Energy + Valence combined interpretation</div></div>`;
        document.getElementById('grammar-breakdown').innerHTML = html;
    }

    BSS.panels.grammar = { load };
})();

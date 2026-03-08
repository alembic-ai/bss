/* BSS Dashboard — Obsidian-Style Knowledge Graph (Cytoscape.js) */
(function() {
    let cy = null;
    let graphData = null;

    const SCOPE_SIZE = { 'Global': 55, 'Regional': 45, 'Local': 35, 'Atomic': 25 };
    const REL_SHAPE = { '^': 'star', '}': 'diamond', '{': 'hexagon', '+': 'ellipse', '_': 'rectangle', '=': 'round-rectangle', '#': 'triangle' };
    const EDGE_STYLES = {
        born_from: { color: '#3b82f680', style: 'solid', width: 2 },
        link: { color: '#8b5cf680', style: 'dashed', width: 1.5 },
        error_chain: { color: '#ef444490', style: 'solid', width: 3 },
    };

    async function load() {
        if (cy) { cy.resize(); return; }
        const data = await BSS.apiFetch('/api/graph/data');
        if (!data) return;
        graphData = data;
        buildGraph(data);
        buildLegend();
        setupToolbar();
    }

    function buildGraph(data) {
        const container = document.getElementById('graph-container');
        if (!container) return;

        const elements = [];
        const nodeIds = new Set(data.nodes.map(n => n.id));

        for (const node of data.nodes) {
            elements.push({
                data: {
                    id: node.id,
                    label: (node.id || '').substring(0, 5) + (node.author || ''),
                    author: node.author || '?',
                    color: BSS.sigColor(node.author || '?'),
                    size: SCOPE_SIZE[node.scope] || 35,
                    shape: REL_SHAPE[node.relational] || 'ellipse',
                    summary: node.summary || '',
                    domain: node.domain || 'Unknown',
                    domain_key: node.domain_key || '?',
                    directory: node.directory || '?',
                    action_state: node.action_state || 'Unknown',
                    relational: node.relational || '+',
                    scope: node.scope || 'Unknown',
                    seq: node.sequence_decimal || 0,
                },
            });
        }

        for (const edge of data.edges) {
            if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) continue;
            const s = EDGE_STYLES[edge.type] || EDGE_STYLES.born_from;
            elements.push({
                data: {
                    source: edge.source,
                    target: edge.target,
                    edgeType: edge.type,
                    edgeColor: s.color,
                    lineStyle: s.style,
                    edgeWidth: s.width,
                },
            });
        }

        cy = cytoscape({
            container: container,
            elements: elements,
            style: [
                {
                    selector: 'node',
                    style: {
                        'background-color': 'data(color)',
                        'label': 'data(label)',
                        'width': 'data(size)',
                        'height': 'data(size)',
                        'shape': 'data(shape)',
                        'color': '#c8d0dc',
                        'font-size': '9px',
                        'font-family': '"JetBrains Mono", "Fira Code", monospace',
                        'text-valign': 'bottom',
                        'text-margin-y': 6,
                        'border-width': 2,
                        'border-color': 'data(color)',
                        'background-opacity': 0.65,
                        'text-background-color': '#0a0e17',
                        'text-background-opacity': 0.7,
                        'text-background-padding': '2px',
                        'text-background-shape': 'roundrectangle',
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'line-color': 'data(edgeColor)',
                        'line-style': 'data(lineStyle)',
                        'target-arrow-color': 'data(edgeColor)',
                        'target-arrow-shape': 'triangle',
                        'arrow-scale': 0.8,
                        'curve-style': 'bezier',
                        'width': 'data(edgeWidth)',
                        'opacity': 0.5,
                    }
                },
                {
                    selector: 'node:selected',
                    style: {
                        'border-width': 4,
                        'border-color': '#ffffff',
                        'background-opacity': 1,
                    }
                },
                {
                    selector: '.dimmed',
                    style: { 'opacity': 0.1 }
                },
                {
                    selector: '.highlighted',
                    style: { 'opacity': 1 }
                },
            ],
            layout: {
                name: typeof cytoscape !== 'undefined' && cytoscape('layout', 'fcose') ? 'fcose' : 'cose',
                animate: true,
                animationDuration: 800,
                nodeRepulsion: 6000,
                idealEdgeLength: 120,
                gravity: 0.2,
                gravityRange: 1.5,
                nodeSeparation: 80,
                randomize: true,
            },
            minZoom: 0.2,
            maxZoom: 4,
            wheelSensitivity: 0.3,
        });

        // Interactions
        cy.on('tap', 'node', function(evt) {
            BSS.openBlink(evt.target.id());
            showGraphDetail(evt.target);
        });

        cy.on('mouseover', 'node', function(evt) {
            const node = evt.target;
            const neighborhood = node.neighborhood().add(node);
            cy.elements().addClass('dimmed');
            neighborhood.removeClass('dimmed').addClass('highlighted');
            showTooltip(evt, node);
        });

        cy.on('mouseout', 'node', function() {
            cy.elements().removeClass('dimmed highlighted');
            hideTooltip();
        });
    }

    function showTooltip(evt, node) {
        let tip = document.getElementById('graph-tooltip');
        if (!tip) {
            tip = document.createElement('div');
            tip.id = 'graph-tooltip';
            tip.className = 'graph-tooltip';
            document.body.appendChild(tip);
        }
        const d = node.data();
        tip.innerHTML = `<strong style="color:${d.color}">${BSS.escHtml(d.id)}</strong><br><span style="color:var(--text-dim)">${BSS.escHtml(d.summary.substring(0, 80))}${d.summary.length > 80 ? '...' : ''}</span><br><span style="font-size:10px;color:var(--text-muted)">${d.action_state} | ${d.domain} | ${d.scope}</span>`;
        const rect = document.getElementById('graph-container').getBoundingClientRect();
        const pos = node.renderedPosition();
        tip.style.left = (rect.left + pos.x + 20) + 'px';
        tip.style.top = (rect.top + pos.y - 20) + 'px';
        tip.style.display = 'block';
    }

    function hideTooltip() {
        const tip = document.getElementById('graph-tooltip');
        if (tip) tip.style.display = 'none';
    }

    function showGraphDetail(node) {
        const panel = document.getElementById('graph-detail-panel');
        if (!panel) return;
        const d = node.data();
        const e = BSS.escHtml;
        const edges = node.connectedEdges();
        const parents = edges.filter(e => e.data('target') === d.id).sources();
        const children = edges.filter(e => e.data('source') === d.id).targets();

        panel.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                <span class="sigil-badge" style="color:${d.color};border-color:${d.color}">${e(d.author)}</span>
                <button class="btn-icon" onclick="document.getElementById('graph-detail-panel').classList.add('hidden')">&times;</button>
            </div>
            <div class="lineage-id" style="color:${d.color};margin-bottom:8px">${e(d.id)}</div>
            <div style="font-size:13px;color:var(--text-dim);margin-bottom:12px">${e(d.summary)}</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;font-size:11px">
                <span class="role-tag">${e(d.action_state)}</span>
                <span class="scope-tag">${e(d.scope)}</span>
                <span class="role-tag">${e(d.domain)}</span>
                <span class="scope-tag">${e(d.directory)}</span>
            </div>
            ${parents.length ? `<div style="margin-top:12px;font-size:11px;color:var(--text-muted)">Parents (${parents.length}):</div>${parents.map(p => `<div class="lineage-id" style="color:${BSS.sigColor(p.data('author'))};font-size:11px;cursor:pointer" onclick="openBlink('${e(p.id())}')">${e(p.id())}</div>`).join('')}` : ''}
            ${children.length ? `<div style="margin-top:8px;font-size:11px;color:var(--text-muted)">Children (${children.length}):</div>${children.map(c => `<div class="lineage-id" style="color:${BSS.sigColor(c.data('author'))};font-size:11px;cursor:pointer" onclick="openBlink('${e(c.id())}')">${e(c.id())}</div>`).join('')}` : ''}
        `;
        panel.classList.remove('hidden');
    }

    function buildLegend() {
        const legend = document.getElementById('graph-legend');
        if (!legend) return;
        legend.innerHTML = `
            <div class="graph-legend-section">
                <span class="graph-legend-title">Shapes:</span>
                <span class="graph-legend-item"><span style="color:#f59e0b">\u2605</span> Origin</span>
                <span class="graph-legend-item"><span style="color:#06b6d4">\u25C6</span> Branch</span>
                <span class="graph-legend-item"><span style="color:#8b5cf6">\u2B22</span> Convergence</span>
                <span class="graph-legend-item"><span style="color:#10b981">\u25CF</span> Continuation</span>
                <span class="graph-legend-item"><span style="color:#6b7280">\u25A0</span> Dead-end</span>
            </div>
            <div class="graph-legend-section">
                <span class="graph-legend-title">Edges:</span>
                <span class="graph-legend-item"><span style="color:#3b82f6">\u2500\u2500</span> Born from</span>
                <span class="graph-legend-item"><span style="color:#8b5cf6">- - -</span> Link</span>
                <span class="graph-legend-item"><span style="color:#ef4444">\u2501\u2501</span> Error chain</span>
            </div>
        `;
    }

    function setupToolbar() {
        const fitBtn = document.getElementById('graph-fit');
        if (fitBtn) fitBtn.onclick = () => cy && cy.fit(null, 40);

        const relayoutBtn = document.getElementById('graph-relayout');
        if (relayoutBtn) relayoutBtn.onclick = () => {
            if (!cy) return;
            cy.layout({ name: 'fcose', animate: true, animationDuration: 600, nodeRepulsion: 6000, idealEdgeLength: 120, gravity: 0.2, randomize: false }).run();
        };

        // Author filter
        const authorFilter = document.getElementById('graph-author-filter');
        if (authorFilter) {
            // Populate from graph data
            if (graphData) {
                const authors = new Set(graphData.nodes.map(n => n.author).filter(Boolean));
                for (const a of [...authors].sort()) {
                    const opt = document.createElement('option');
                    opt.value = a; opt.textContent = a;
                    opt.style.color = BSS.sigColor(a);
                    authorFilter.appendChild(opt);
                }
            }
            authorFilter.onchange = () => {
                if (!cy) return;
                const val = authorFilter.value;
                if (!val) { cy.elements().style('display', 'element'); return; }
                cy.nodes().forEach(n => { n.style('display', n.data('author') === val ? 'element' : 'none'); });
                cy.edges().forEach(e => { const s = cy.getElementById(e.data('source')), t = cy.getElementById(e.data('target')); e.style('display', s.style('display') === 'element' && t.style('display') === 'element' ? 'element' : 'none'); });
            };
        }

        // Cluster by
        const clusterBy = document.getElementById('graph-cluster-by');
        if (clusterBy) {
            clusterBy.onchange = () => {
                if (!cy) return;
                const field = clusterBy.value;
                if (field === 'none') { cy.layout({ name: 'fcose', animate: true, animationDuration: 600, nodeRepulsion: 6000, idealEdgeLength: 120, randomize: false }).run(); return; }
                // Color nodes by cluster field for visual grouping
                const groups = {};
                cy.nodes().forEach(n => {
                    const key = n.data(field) || 'Unknown';
                    if (!groups[key]) groups[key] = [];
                    groups[key].push(n);
                });
                // Use cose layout with compound nodes simulation
                cy.layout({ name: 'fcose', animate: true, animationDuration: 600, nodeRepulsion: 8000, idealEdgeLength: 80, randomize: false }).run();
            };
        }

        // Search
        const searchInput = document.getElementById('graph-search');
        if (searchInput) {
            let debounce = null;
            searchInput.oninput = () => {
                clearTimeout(debounce);
                debounce = setTimeout(() => {
                    if (!cy) return;
                    const q = searchInput.value.toLowerCase().trim();
                    if (!q) { cy.elements().removeClass('dimmed highlighted'); return; }
                    cy.elements().addClass('dimmed');
                    cy.nodes().forEach(n => {
                        if (n.data('summary').toLowerCase().includes(q) || n.data('id').toLowerCase().includes(q)) {
                            const nh = n.neighborhood().add(n);
                            nh.removeClass('dimmed').addClass('highlighted');
                        }
                    });
                }, 300);
            };
        }
    }

    BSS.panels.graph = { load };
})();

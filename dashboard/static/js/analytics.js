/* BSS Dashboard — Analytics Panel (Chart.js + Heatmap) */
(function() {
    let loaded = false;

    async function load() {
        if (loaded) return;
        loaded = true;
        const [distributions, authors, heatmap] = await Promise.all([
            BSS.apiFetch('/api/analytics/distributions'),
            BSS.apiFetch('/api/analytics/authors'),
            BSS.apiFetch('/api/analytics/heatmap'),
        ]);
        if (distributions) renderCharts(distributions);
        if (authors) renderLeaderboard(authors);
        if (heatmap) renderHeatmap(heatmap);
    }

    function renderCharts(data) {
        const charts = [
            { id: 'chart-domain', title: 'Domain Distribution', data: data.domains, colors: ['#3b82f6','#8b5cf6','#06b6d4','#f59e0b','#ef4444','#10b981','#ec4899','#f97316','#a78bfa','#34d399'] },
            { id: 'chart-scope', title: 'Scope Distribution', data: data.scopes, colors: ['#e879f9','#c084fc','#a78bfa','#8b5cf6'] },
            { id: 'chart-action', title: 'Action States', data: data.actions, colors: ['#3b82f6','#f59e0b','#10b981','#ef4444','#8b5cf6','#06b6d4','#ec4899','#94a3b8','#f97316','#6b7280'] },
            { id: 'chart-relational', title: 'Relational Types', data: data.relationals, colors: ['#f59e0b','#06b6d4','#8b5cf6','#10b981','#6b7280','#3b82f6','#ef4444'] },
        ];

        for (const c of charts) {
            const canvas = document.getElementById(c.id);
            if (!canvas || !c.data || Object.keys(c.data).length === 0) continue;
            const labels = Object.keys(c.data);
            const values = Object.values(c.data);
            new Chart(canvas, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{ data: values, backgroundColor: c.colors.slice(0, labels.length), borderColor: '#1a2235', borderWidth: 2 }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'right', labels: { color: '#8892a8', font: { size: 11 }, padding: 8, boxWidth: 12 } },
                        title: { display: true, text: c.title, color: '#e2e8f0', font: { size: 13, weight: '600' }, padding: { bottom: 12 } },
                    },
                    cutout: '60%',
                },
            });
        }
    }

    function renderLeaderboard(data) {
        const container = document.getElementById('author-leaderboard');
        if (!container || !data.authors?.length) { if (container) container.innerHTML = '<div class="roster-empty">No author data</div>'; return; }
        const e = BSS.escHtml;
        let html = '<div class="leaderboard-row header"><span>Sigil</span><span>Blinks</span><span>Errors</span><span>Error %</span><span>Top Domain</span></div>';
        for (const a of data.authors) {
            const color = BSS.sigColor(a.sigil);
            const errClass = a.error_rate > 20 ? 'color:var(--error)' : a.error_rate > 10 ? 'color:var(--warning)' : 'color:var(--success)';
            html += `<div class="leaderboard-row"><span class="sigil-badge" style="color:${color};border-color:${color}">${e(a.sigil)}</span><span style="font-weight:700">${a.blink_count}</span><span style="${a.error_count > 0 ? 'color:var(--error)' : ''}">${a.error_count}</span><span style="${errClass}">${a.error_rate}%</span><span class="role-tag">${e(a.top_domain)}</span></div>`;
        }
        container.innerHTML = html;
    }

    function renderHeatmap(data) {
        const container = document.getElementById('heatmap-container');
        if (!container || !data.days?.length) { if (container) container.innerHTML = '<div class="roster-empty">No activity data</div>'; return; }

        const maxCount = Math.max(...data.days.map(d => d.count), 1);
        let html = '<div class="heatmap-grid">';
        for (const day of data.days) {
            const intensity = day.count / maxCount;
            let color;
            if (day.count === 0) color = '#1a2235';
            else if (intensity < 0.25) color = '#1e3a5f';
            else if (intensity < 0.5) color = '#1d4ed8';
            else if (intensity < 0.75) color = '#3b82f6';
            else color = '#60a5fa';
            html += `<div class="heatmap-cell" style="background:${color}" title="${day.date}: ${day.count} blinks"></div>`;
        }
        html += '</div>';
        if (data.days.length > 0) {
            html += `<div style="display:flex;justify-content:space-between;font-size:10px;color:var(--text-muted);margin-top:4px"><span>${data.days[0].date}</span><span>${data.days[data.days.length - 1].date}</span></div>`;
        }
        container.innerHTML = html;
    }

    BSS.panels.analytics = { load };
})();

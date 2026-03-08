/* BSS Dashboard — Command Palette */
(function() {
    const COMMANDS = [
        { id: 'nav-overview', label: 'Go to Overview', icon: '\u2302', action: () => navTo('overview') },
        { id: 'nav-graph', label: 'Go to Knowledge Graph', icon: '\u25C8', action: () => navTo('graph') },
        { id: 'nav-analytics', label: 'Go to Analytics', icon: '\u2261', action: () => navTo('analytics') },
        { id: 'nav-timeline', label: 'Go to Timeline', icon: '\u23F1', action: () => navTo('timeline') },
        { id: 'nav-chat', label: 'Go to Chat', icon: '\u2709', action: () => navTo('chat') },
        { id: 'nav-tasks', label: 'Go to Task Board', icon: '\u2610', action: () => navTo('taskboard') },
        { id: 'nav-conversations', label: 'Go to Conversations', icon: '\u2194', action: () => navTo('conversations') },
        { id: 'nav-search', label: 'Search Blinks', icon: '\uD83D\uDD0D', action: () => navTo('search') },
        { id: 'nav-composer', label: 'Compose New Blink', icon: '\u270E', action: () => navTo('composer') },
        { id: 'nav-runner', label: 'Start Relay Runner', icon: '\u25B6', action: () => navTo('runner') },
        { id: 'nav-health', label: 'Health & Models', icon: '\u2665', action: () => navTo('health') },
        { id: 'nav-convergence', label: 'Convergence Manager', icon: '\u21C4', action: () => navTo('convergence') },
        { id: 'nav-artifacts', label: 'View Artifacts', icon: '\uD83D\uDCC4', action: () => navTo('artifacts') },
        { id: 'nav-glossary', label: 'Open Glossary', icon: '\uD83D\uDCD6', action: () => navTo('glossary') },
        { id: 'nav-export', label: 'Export Report', icon: '\uD83D\uDCE5', action: () => navTo('export') },
        { id: 'action-refresh', label: 'Refresh Current Panel', icon: '\u21BB', action: refreshPanel },
        { id: 'action-feed', label: 'View Activity Feed', icon: '\uD83D\uDD14', action: () => navTo('feed') },
        { id: 'nav-lineage', label: 'Trace Lineage', icon: '\uD83C\uDF33', action: () => navTo('lineage') },
        { id: 'nav-grammar', label: 'ID Grammar Explorer', icon: '\uD83E\uDDE9', action: () => navTo('grammar') },
        { id: 'nav-reference', label: 'Sigil Reference', icon: '\uD83D\uDCDA', action: () => navTo('reference') },
        { id: 'nav-settings', label: 'Settings', icon: '\u2699', action: () => navTo('settings') },
    ];

    function navTo(panel) {
        closePalette();
        // Activate the panel
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
        const el = document.getElementById(`panel-${panel}`);
        if (el) el.classList.add('active');
        // Try to highlight correct tab
        const tab = document.querySelector(`.nav-tab[data-panel="${panel}"]`);
        if (tab) tab.classList.add('active');
        else {
            const trigger = document.querySelector('.nav-dropdown-trigger');
            if (trigger) trigger.classList.add('active');
        }
        const handler = BSS.panels[panel];
        if (handler && handler.load) handler.load();
    }

    function refreshPanel() {
        closePalette();
        const active = document.querySelector('.panel.active');
        if (active) {
            const name = active.id.replace('panel-', '');
            const handler = BSS.panels[name];
            if (handler && handler.load) handler.load();
        }
    }

    function openPalette() {
        const overlay = document.getElementById('cmd-palette-overlay');
        const input = document.getElementById('cmd-palette-input');
        overlay.classList.add('active');
        input.value = '';
        input.focus();
        renderResults('');
    }

    function closePalette() {
        document.getElementById('cmd-palette-overlay').classList.remove('active');
    }

    function renderResults(query) {
        const list = document.getElementById('cmd-palette-results');
        const q = query.toLowerCase();
        const filtered = q ? COMMANDS.filter(c => c.label.toLowerCase().includes(q)) : COMMANDS;
        const e = BSS.escHtml;

        if (!filtered.length) {
            list.innerHTML = '<div class="cmd-empty">No matching commands</div>';
            return;
        }

        list.innerHTML = filtered.map((cmd, i) =>
            `<div class="cmd-item ${i === 0 ? 'active' : ''}" data-idx="${i}" onclick="executePaletteCommand(${COMMANDS.indexOf(cmd)})">
                <span class="cmd-icon">${cmd.icon}</span>
                <span class="cmd-label">${e(cmd.label)}</span>
            </div>`
        ).join('');
    }

    window.executePaletteCommand = function(idx) {
        if (COMMANDS[idx]) COMMANDS[idx].action();
    };

    // Keyboard handling
    document.addEventListener('keydown', (e) => {
        // Ctrl+K or Cmd+K to open
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const overlay = document.getElementById('cmd-palette-overlay');
            if (overlay.classList.contains('active')) closePalette();
            else openPalette();
            return;
        }
        // Escape to close
        if (e.key === 'Escape') {
            const overlay = document.getElementById('cmd-palette-overlay');
            if (overlay.classList.contains('active')) {
                e.preventDefault();
                e.stopPropagation();
                closePalette();
            }
        }
    });

    // Input filtering
    document.addEventListener('DOMContentLoaded', () => {
        const input = document.getElementById('cmd-palette-input');
        if (input) {
            input.addEventListener('input', () => renderResults(input.value));
            input.addEventListener('keydown', (e) => {
                const items = document.querySelectorAll('.cmd-item');
                const active = document.querySelector('.cmd-item.active');
                const idx = [...items].indexOf(active);

                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    items.forEach(i => i.classList.remove('active'));
                    const next = items[Math.min(idx + 1, items.length - 1)];
                    if (next) { next.classList.add('active'); next.scrollIntoView({ block: 'nearest' }); }
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    items.forEach(i => i.classList.remove('active'));
                    const prev = items[Math.max(idx - 1, 0)];
                    if (prev) { prev.classList.add('active'); prev.scrollIntoView({ block: 'nearest' }); }
                } else if (e.key === 'Enter') {
                    e.preventDefault();
                    if (active) active.click();
                }
            });
        }

        // Click overlay to close
        const overlay = document.getElementById('cmd-palette-overlay');
        if (overlay) {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) closePalette();
            });
        }
    });

    window.openCommandPalette = openPalette;
})();

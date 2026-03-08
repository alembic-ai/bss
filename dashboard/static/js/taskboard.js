/* BSS Dashboard — Task Board (Kanban) */
(function() {
    async function load() {
        const data = await BSS.apiFetch('/api/tasks/board');
        if (!data) return;
        renderBoard(data);
    }

    function renderBoard(data) {
        const e = BSS.escHtml;
        const columns = [
            { key: 'queued', title: 'Queued', icon: '\u23F3', color: 'var(--text-muted)' },
            { key: 'in_progress', title: 'In Progress', icon: '\u26A1', color: 'var(--warning)' },
            { key: 'completed', title: 'Completed', icon: '\u2713', color: 'var(--success)' },
            { key: 'errors', title: 'Errors', icon: '\u2717', color: 'var(--error)' },
        ];

        for (const col of columns) {
            const container = document.getElementById(`task-col-${col.key}`);
            if (!container) continue;
            const items = data[col.key] || [];
            const countBadge = container.parentElement.querySelector('.task-col-count');
            if (countBadge) countBadge.textContent = items.length;

            if (!items.length) {
                container.innerHTML = `<div class="task-empty">No ${col.title.toLowerCase()}</div>`;
                continue;
            }

            let html = '';
            for (const task of items) {
                const color = BSS.sigColor(task.author || '?');
                const priorityColor = BSS.priorityColor(task.priority || 'Normal');
                html += `
                    <div class="task-card" onclick="openBlink('${e(task.blink_id)}')" draggable="false">
                        <div class="task-card-top">
                            <span class="sigil-badge mini" style="color:${color};border-color:${color}">${e(task.author || '?')}</span>
                            <span class="task-priority" style="color:${priorityColor}">${e(task.priority || '')}</span>
                        </div>
                        <div class="task-card-summary">${e(task.summary || 'No summary')}</div>
                        <div class="task-card-bottom">
                            <span class="task-card-id">${e((task.blink_id || '').substring(0, 8))}</span>
                            <span class="task-card-scope">${e(task.scope || '')}</span>
                            <span class="task-card-domain">${e(task.domain || '')}</span>
                        </div>
                    </div>`;
            }
            container.innerHTML = html;
        }
    }

    BSS.panels.taskboard = { load };
})();

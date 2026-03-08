/* BSS Dashboard — Activity Feed */
(function() {
    let lastSeq = 0;
    let feedInterval = null;

    async function load() {
        await refreshFeed();
        // Poll every 5s for new activity
        if (!feedInterval) {
            feedInterval = setInterval(pollNew, 5000);
        }
    }

    async function refreshFeed() {
        const data = await BSS.apiFetch('/api/feed/recent?limit=50');
        if (!data) return;
        const container = document.getElementById('feed-list');
        if (!data.events?.length) {
            container.innerHTML = '<div class="roster-empty">No recent activity</div>';
            return;
        }
        renderEvents(container, data.events, false);
        if (data.events.length > 0) {
            lastSeq = data.events[0].sequence || 0;
        }
    }

    async function pollNew() {
        const active = document.querySelector('.panel.active');
        if (!active || active.id !== 'panel-feed') return;

        const data = await BSS.apiFetch(`/api/feed/recent?after=${lastSeq}&limit=10`);
        if (!data?.events?.length) return;

        const container = document.getElementById('feed-list');
        renderEvents(container, data.events, true);
        lastSeq = data.events[0].sequence || lastSeq;

        // Show toast for new items
        for (const evt of data.events.slice(0, 3)) {
            showToast(evt);
        }
    }

    function renderEvents(container, events, prepend) {
        const e = BSS.escHtml;
        let html = '';
        for (const evt of events) {
            const color = BSS.sigColor(evt.author || '?');
            const icon = BSS.actionIcon(evt.action_state || '');
            const typeClass = evt.type === 'error' ? 'feed-error' : evt.type === 'convergence' ? 'feed-convergence' : '';
            html += `
                <div class="feed-item ${typeClass}" onclick="openBlink('${e(evt.blink_id || '')}')">
                    <div class="feed-item-icon">
                        <span class="sigil-badge" style="color:${color};border-color:${color}">${e(evt.author || '?')}</span>
                    </div>
                    <div class="feed-item-body">
                        <div class="feed-item-action">
                            <span>${icon} ${e(evt.action_state || 'Unknown')}</span>
                            <span class="feed-item-dir">${e(evt.directory || '')}</span>
                        </div>
                        <div class="feed-item-summary">${e(evt.summary || '')}</div>
                    </div>
                    <div class="feed-item-id">${e((evt.blink_id || '').substring(0, 8))}</div>
                </div>`;
        }
        if (prepend) {
            container.insertAdjacentHTML('afterbegin', html);
        } else {
            container.innerHTML = html;
        }
    }

    function showToast(evt) {
        const toast = document.getElementById('toast-container');
        if (!toast) return;
        const e = BSS.escHtml;
        const color = BSS.sigColor(evt.author || '?');
        const div = document.createElement('div');
        div.className = 'toast-item';
        div.innerHTML = `<span class="sigil-badge mini" style="color:${color};border-color:${color}">${e(evt.author || '?')}</span><span>${BSS.actionIcon(evt.action_state || '')} ${e((evt.summary || '').substring(0, 80))}</span>`;
        div.onclick = () => { openBlink(evt.blink_id); div.remove(); };
        toast.appendChild(div);
        setTimeout(() => div.classList.add('show'), 10);
        setTimeout(() => { div.classList.remove('show'); setTimeout(() => div.remove(), 300); }, 5000);
    }

    BSS.panels.feed = { load };
})();

/* BSS Dashboard — Conversation View (relay chains as chat threads) */
(function() {
    async function load() {
        const data = await BSS.apiFetch('/api/conversations/threads');
        if (!data) return;
        const list = document.getElementById('convo-thread-list');
        const view = document.getElementById('convo-view');

        if (!data.threads?.length) {
            list.innerHTML = '<div class="roster-empty">No conversation threads found</div>';
            return;
        }

        const e = BSS.escHtml;
        let html = '';
        for (const thread of data.threads) {
            const color = BSS.sigColor(thread.initiator || '?');
            const participantBadges = (thread.participants || []).map(p => {
                const c = BSS.sigColor(p);
                return `<span class="sigil-badge mini" style="color:${c};border-color:${c}">${e(p)}</span>`;
            }).join('');
            html += `
                <div class="convo-thread-item" onclick="loadThread('${e(thread.root_id)}')">
                    <div class="convo-thread-header">
                        ${participantBadges}
                        <span class="convo-thread-count">${thread.message_count} messages</span>
                    </div>
                    <div class="convo-thread-preview">${e(thread.preview || '')}</div>
                    <div class="convo-thread-meta">
                        <span>Gen ${thread.generation || 1}/7</span>
                        <span>${e(thread.root_id?.substring(0, 8) || '')}</span>
                    </div>
                </div>`;
        }
        list.innerHTML = html;

        // Auto-load first thread
        if (data.threads.length > 0) {
            loadThread(data.threads[0].root_id);
        }
    }

    window.loadThread = async function(rootId) {
        const view = document.getElementById('convo-view');
        view.innerHTML = '<div class="loading-spinner"></div>';

        // Highlight active thread
        document.querySelectorAll('.convo-thread-item').forEach(el => el.classList.remove('active'));
        const items = document.querySelectorAll('.convo-thread-item');
        items.forEach(el => {
            if (el.onclick?.toString().includes(rootId)) el.classList.add('active');
        });

        const data = await BSS.apiFetch(`/api/conversations/thread/${encodeURIComponent(rootId)}`);
        if (!data || !data.messages?.length) {
            view.innerHTML = '<div class="roster-empty">Could not load thread</div>';
            return;
        }

        const e = BSS.escHtml;
        let html = '<div class="convo-messages">';
        let lastAuthor = null;

        for (const msg of data.messages) {
            const color = BSS.sigColor(msg.author || '?');
            const isNewAuthor = msg.author !== lastAuthor;
            lastAuthor = msg.author;

            html += `
                <div class="convo-message ${isNewAuthor ? 'convo-message-new' : ''}">
                    ${isNewAuthor ? `<div class="convo-author"><span class="sigil-badge" style="color:${color};border-color:${color}">${e(msg.author || '?')}</span><span class="convo-action">${BSS.actionIcon(msg.action_state || '')} ${e(msg.action_state || '')}</span></div>` : ''}
                    <div class="convo-text" onclick="openBlink('${e(msg.blink_id)}')">${e(msg.summary || '')}</div>
                    <div class="convo-msg-meta">
                        <span class="convo-msg-id">${e(msg.blink_id?.substring(0, 8) || '')}</span>
                        <span class="convo-msg-scope">${e(msg.scope || '')}</span>
                    </div>
                </div>`;
        }
        html += '</div>';

        // Thread info bar
        if (data.generation) {
            const urgency = data.generation >= 7 ? 'var(--error)' : data.generation >= 5 ? 'var(--warning)' : 'var(--text-muted)';
            html += `<div class="convo-info-bar"><span style="color:${urgency}">Generation ${data.generation}/7</span><span>${data.messages.length} blinks in chain</span></div>`;
        }

        view.innerHTML = html;
    };

    BSS.panels.conversations = { load };
})();

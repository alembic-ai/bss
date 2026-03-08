/* BSS Dashboard — Chat Interface (talk to the swarm) */
(function() {
    let selectedSigil = null;
    let chatHistory = [];

    async function load() {
        const select = document.getElementById('chat-sigil');
        if (select && select.options.length <= 2) {
            const roster = BSS._rosterCache || await BSS.apiFetch('/api/roster');
            if (roster?.entries) {
                BSS._rosterCache = roster;
                for (const e of roster.entries) {
                    const opt = document.createElement('option');
                    opt.value = e.sigil;
                    opt.textContent = `${e.sigil} \u2014 ${e.model_id}`;
                    select.appendChild(opt);
                }
            }
        }
    }

    window.sendChatMessage = async function() {
        const input = document.getElementById('chat-input');
        const sigil = document.getElementById('chat-sigil').value;
        const msg = input.value.trim();
        if (!msg) return;
        if (!sigil) { addChatBubble('system', 'Please select a model to chat with.'); return; }

        // Add user bubble
        addChatBubble('user', msg);
        input.value = '';
        input.focus();

        // Show typing indicator
        const typing = addTypingIndicator(sigil);

        try {
            const res = await fetch('/api/chat/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sigil, message: msg }),
            }).then(r => r.json());

            typing.remove();

            if (res.error) {
                addChatBubble('system', 'Error: ' + res.error);
            } else {
                addChatBubble('model', res.response, sigil, res.tokens, res.elapsed);
                if (res.blink_id) {
                    addChatMeta(`Blink created: ${res.blink_id}`, res.blink_id);
                }
            }
        } catch (err) {
            typing.remove();
            addChatBubble('system', 'Failed to reach the swarm: ' + err.message);
        }
    };

    window.sendChatOnEnter = function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    };

    window.clearChat = function() {
        document.getElementById('chat-messages').innerHTML =
            '<div class="chat-welcome"><div class="chat-welcome-icon">\u25C8</div><div class="chat-welcome-title">Talk to your Swarm</div><div class="chat-welcome-sub">Select a model and send a message. The model reads your relay state, processes your request, and writes a handoff blink with its response.</div></div>';
        chatHistory = [];
        fetch('/api/chat/clear', { method: 'POST' }).catch(() => {});
    };

    function addChatBubble(type, text, sigil, tokens, elapsed) {
        const container = document.getElementById('chat-messages');
        const welcome = container.querySelector('.chat-welcome');
        if (welcome) welcome.remove();

        const e = BSS.escHtml;
        const div = document.createElement('div');
        div.className = `chat-bubble chat-${type}`;

        if (type === 'user') {
            div.innerHTML = `<div class="chat-bubble-content">${e(text)}</div>`;
        } else if (type === 'model') {
            const color = BSS.sigColor(sigil || '?');
            // Render markdown-like formatting (basic)
            const formatted = formatResponse(text);
            div.innerHTML = `
                <div class="chat-bubble-header">
                    <span class="sigil-badge" style="color:${color};border-color:${color}">${e(sigil || '?')}</span>
                    ${tokens ? `<span class="chat-meta-info">${tokens} tokens \u2022 ${elapsed?.toFixed(1)}s</span>` : ''}
                </div>
                <div class="chat-bubble-content model-response">${formatted}</div>`;
        } else {
            div.innerHTML = `<div class="chat-bubble-content chat-system-text">${e(text)}</div>`;
        }

        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        return div;
    }

    function addTypingIndicator(sigil) {
        const container = document.getElementById('chat-messages');
        const color = BSS.sigColor(sigil);
        const div = document.createElement('div');
        div.className = 'chat-bubble chat-model chat-typing';
        div.innerHTML = `
            <div class="chat-bubble-header">
                <span class="sigil-badge" style="color:${color};border-color:${color}">${BSS.escHtml(sigil)}</span>
                <span class="chat-meta-info">thinking...</span>
            </div>
            <div class="chat-bubble-content"><div class="typing-dots"><span></span><span></span><span></span></div></div>`;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        return div;
    }

    function addChatMeta(text, blinkId) {
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.className = 'chat-blink-ref';
        div.innerHTML = `<span style="cursor:pointer;color:var(--accent)" onclick="openBlink('${BSS.escHtml(blinkId)}')">${BSS.escHtml(text)}</span>`;
        container.appendChild(div);
    }

    function formatResponse(text) {
        let html = BSS.escHtml(text);
        // Code blocks
        html = html.replace(/```([\s\S]*?)```/g, '<pre class="chat-code">$1</pre>');
        // Inline code
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        // Bold
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        // Newlines
        html = html.replace(/\n/g, '<br>');
        return html;
    }

    BSS.panels.chat = { load };
})();

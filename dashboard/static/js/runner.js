/* BSS Dashboard — Live Relay Runner (SSE) */
(function() {
    let eventSource = null;

    async function load() {
        // Populate sigil checkboxes from roster
        const container = document.getElementById('runner-sigils');
        if (container && !container._populated) {
            container._populated = true;
            const roster = BSS._rosterCache || await BSS.apiFetch('/api/roster');
            if (roster?.entries) {
                for (const entry of roster.entries) {
                    const color = BSS.sigColor(entry.sigil);
                    container.innerHTML += `<label class="runner-sigil-label" style="color:${color}"><input type="checkbox" value="${BSS.escHtml(entry.sigil)}" checked> ${BSS.escHtml(entry.sigil)} \u2014 ${BSS.escHtml(entry.model_id)}</label>`;
                }
            }
        }
        updateStatus();
    }

    window.startRelay = async function() {
        const sigils = [...document.querySelectorAll('#runner-sigils input:checked')].map(cb => cb.value);
        const maxRounds = parseInt(document.getElementById('runner-max-rounds')?.value) || 10;
        if (!sigils.length) { alert('Select at least one model sigil.'); return; }

        document.getElementById('runner-log').innerHTML = '';
        addLogEntry('system', `Starting relay with ${sigils.join(', ')} for ${maxRounds} rounds...`);

        const res = await fetch('/api/relay/run/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sigils, max_rounds: maxRounds }),
        }).then(r => r.json()).catch(e => ({ error: String(e) }));

        if (res.error) { addLogEntry('error', 'Failed to start: ' + res.error); return; }
        addLogEntry('system', 'Relay started. Connecting to event stream...');
        connectSSE();
        updateStatus();
    };

    window.stopRelay = async function() {
        await fetch('/api/relay/run/stop', { method: 'POST' }).catch(() => {});
        if (eventSource) { eventSource.close(); eventSource = null; }
        addLogEntry('system', 'Stop requested.');
        updateStatus();
    };

    function connectSSE() {
        if (eventSource) eventSource.close();
        eventSource = new EventSource('/api/relay/run/stream');
        eventSource.onmessage = (e) => {
            try {
                const evt = JSON.parse(e.data);
                if (evt.type === 'round_start') addLogEntry('info', `Round ${evt.round}/${evt.max_rounds}: Model ${evt.sigil} starting...`);
                else if (evt.type === 'round_end') addLogEntry('success', `Round ${evt.round}: ${evt.sigil} responded (${evt.tokens} tokens, ${evt.elapsed?.toFixed(1)}s)\n${evt.response?.substring(0, 200) || ''}`);
                else if (evt.type === 'idle') addLogEntry('info', `Model ${evt.sigil} idle at round ${evt.round}.`);
                else if (evt.type === 'error') addLogEntry('error', `Error at round ${evt.round}: ${evt.error}`);
                else if (evt.type === 'complete') { addLogEntry('system', `Relay complete. ${evt.rounds} rounds, ${evt.total_results} results.`); eventSource.close(); eventSource = null; updateStatus(); }
                else if (evt.type === 'done') { eventSource.close(); eventSource = null; updateStatus(); }
            } catch (err) { console.error('SSE parse error', err); }
        };
        eventSource.onerror = () => { addLogEntry('error', 'Event stream disconnected.'); eventSource.close(); eventSource = null; updateStatus(); };
    }

    function addLogEntry(type, message) {
        const log = document.getElementById('runner-log');
        const cls = type === 'error' ? 'runner-event error' : type === 'success' ? 'runner-event success' : type === 'system' ? 'runner-event system' : 'runner-event';
        log.innerHTML += `<div class="${cls}"><span style="font-size:10px;color:var(--text-muted)">${new Date().toLocaleTimeString()}</span><div style="margin-top:4px;white-space:pre-wrap">${BSS.escHtml(message)}</div></div>`;
        log.scrollTop = log.scrollHeight;
    }

    function updateStatus() {
        const indicator = document.getElementById('runner-status');
        if (indicator) {
            indicator.textContent = eventSource ? 'Running' : 'Stopped';
            indicator.style.color = eventSource ? 'var(--success)' : 'var(--text-muted)';
        }
    }

    BSS.panels.runner = { load };
})();

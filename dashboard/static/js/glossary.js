/* BSS Dashboard — Glossary */
(function() {
    const TERMS = [
        { term: 'Blink', category: 'Core', definition: 'The atomic unit of communication in BSS. A blink is an immutable markdown file with a 17-character ID encoding rich metadata. Once created, a blink can never be modified or deleted.' },
        { term: 'Blink ID', category: 'Core', definition: 'A 17-character positional grammar that encodes: sequence number (5 chars), author sigil (1), action state (2), relational type (1), confidence (1), cognitive mode (1), domain (1), subdomain (1), scope (1), maturity (1), priority (1), and sensitivity (1).' },
        { term: 'Sigil', category: 'Core', definition: 'A single uppercase letter (A-Z) that identifies a model in the swarm. Each model gets a unique sigil assigned in the roster.' },
        { term: 'Relay', category: 'Protocol', definition: 'The handoff mechanism between models. When a model finishes work, it writes a handoff blink to /relay/ for the next model to pick up. This is how stateless models maintain continuity.' },
        { term: 'Relay Queue', category: 'Protocol', definition: 'The /relay/ directory containing blinks awaiting processing. Blinks are triaged by urgency, recency, and scope to determine processing order.' },
        { term: 'Session Lifecycle', category: 'Protocol', definition: 'The 5-phase cycle every model session follows: INTAKE (read context), TRIAGE (prioritize work), WORK (process items), OUTPUT (write results), DORMANCY (session ends).' },
        { term: 'INTAKE', category: 'Lifecycle', definition: 'Phase 1: The model reads all directories (/relay/, /active/, /profile/) to absorb context about the current state of work.' },
        { term: 'TRIAGE', category: 'Lifecycle', definition: 'Phase 2: Sort relay blinks by urgency, recency, and scope. Identify the highest-priority work to process.' },
        { term: 'WORK', category: 'Lifecycle', definition: 'Phase 3: Process triaged items. Generate responses, make decisions, create artifacts.' },
        { term: 'OUTPUT', category: 'Lifecycle', definition: 'Phase 4: Write results as handoff blinks. Archive completed work. Register any artifacts produced.' },
        { term: 'DORMANCY', category: 'Lifecycle', definition: 'Phase 5: Session ends. All state is persisted in blinks. The next model can pick up cleanly from the relay.' },
        { term: 'Handoff', category: 'Protocol', definition: 'The act of writing a blink to /relay/ summarizing what was done, what state remains, and what the next model should focus on.' },
        { term: 'Generation', category: 'Lineage', definition: 'How deep a blink is in its lineage chain. Generation 1 is an origin blink. Maximum depth is 7 before convergence is required.' },
        { term: 'Convergence', category: 'Lineage', definition: 'When a chain reaches generation 7, it must be synthesized into a single convergence blink that summarizes the entire chain. This resets the generation counter and prevents unbounded chain growth.' },
        { term: 'Lineage', category: 'Lineage', definition: 'The ancestry chain of a blink. Each blink records its parent (born_from) creating a traceable history of how work evolved.' },
        { term: 'Born From', category: 'Lineage', definition: 'The parent blink(s) that a blink was created in response to. Origin blinks have born_from = ["Origin"].' },
        { term: 'Scope', category: 'Sigils', definition: 'How wide the impact of a blink is. Atomic (.) = single item, Local (-) = one directory, Regional (=) = multiple directories, Global (!) = entire environment.' },
        { term: 'Scope Ceiling', category: 'Roster', definition: 'The maximum scope level a model is allowed to operate at. Set in the roster to prevent lower-capability models from making system-wide changes.' },
        { term: 'Roster', category: 'Core', definition: 'The list of models participating in the swarm. Stored as a blink in /profile/. Defines each model\'s sigil, role, and scope ceiling.' },
        { term: 'Action State', category: 'Sigils', definition: 'Two characters encoding what a blink represents: energy (reactive ~, proactive !, neutral .) + valence (creative !, corrective ~, maintenance .). Combined they form states like "Handoff" (~!), "Completed" (~.), "Error" (!~).' },
        { term: 'Relational Type', category: 'Sigils', definition: 'How a blink relates to others: Origin (^) = no parent, Branch (+) = continues work, Convergence ({) = synthesizes chain, Continuation (}) = extends, Dead-end (.) = terminal.' },
        { term: 'Swarm', category: 'Core', definition: 'A group of AI models coordinating through BSS. Each model operates independently and statelessly, communicating only through blinks in the file system.' },
        { term: 'Artifact', category: 'Core', definition: 'A file produced by a model during work (code, documents, data). Stored in /artifacts/ and referenced by blinks.' },
        { term: 'Immutability', category: 'Core', definition: 'Once a blink is written, it can never be changed. This ensures a reliable audit trail and prevents models from altering history.' },
        { term: 'Error Escalation', category: 'Protocol', definition: 'When error blinks chain together, BSS detects the pattern. Repeated errors trigger escalation to a higher-scope model or human intervention.' },
        { term: 'Triage', category: 'Protocol', definition: 'The process of sorting relay blinks by priority, urgency, and scope to determine processing order.' },
    ];

    function load() {
        const container = document.getElementById('glossary-list');
        const input = document.getElementById('glossary-search');
        renderTerms(container, '');

        if (input && !input._bound) {
            input._bound = true;
            input.addEventListener('input', () => renderTerms(container, input.value));
        }
    }

    function renderTerms(container, query) {
        const q = query.toLowerCase();
        const filtered = q ? TERMS.filter(t =>
            t.term.toLowerCase().includes(q) ||
            t.definition.toLowerCase().includes(q) ||
            t.category.toLowerCase().includes(q)
        ) : TERMS;

        const e = BSS.escHtml;
        const categories = {};
        for (const t of filtered) {
            if (!categories[t.category]) categories[t.category] = [];
            categories[t.category].push(t);
        }

        let html = '';
        for (const [cat, terms] of Object.entries(categories)) {
            html += `<div class="glossary-category"><h4>${e(cat)}</h4>`;
            for (const t of terms) {
                const def = q ? highlightTerm(t.definition, q) : e(t.definition);
                html += `
                    <div class="glossary-entry">
                        <div class="glossary-term">${e(t.term)}</div>
                        <div class="glossary-def">${def}</div>
                    </div>`;
            }
            html += '</div>';
        }
        container.innerHTML = html || '<div class="roster-empty">No matching terms</div>';
    }

    function highlightTerm(text, term) {
        const escaped = BSS.escHtml(text);
        const termEscaped = BSS.escHtml(term);
        const regex = new RegExp(`(${termEscaped.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        return escaped.replace(regex, '<mark>$1</mark>');
    }

    BSS.panels.glossary = { load };
})();

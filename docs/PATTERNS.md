# Blink Patterns

Common relay patterns showing blink sequences with annotations. Each pattern shows the filenames and which directory they're written to.

## Simple Task Relay

User creates a task, Model A works on it, hands off to Model B who finishes.

```
/active/   00001U~~^!!^;!!=.    User creates origin blink: "Build a login page"
/active/   00002A.!+!=#!=~~=    A picks up, starts work: "Scaffolded auth module"
/relay/    00003A~!+!=#!=~^=    A writes handoff: "Login form done, needs validation"
/active/   00004B.!+!=#!=~~=    B reads handoff, continues: "Added input validation"
/active/   00005B~.+!.#!=.^=    B marks done: "Login page complete with tests"
```

## Code Review

Primary model writes code, reviewer model reads and provides assessment.

```
/active/   00010A.!+!=#!-~~=    A writes code: "Implemented parser module"
                                 → artifacts/00010A-parser.py
/relay/    00011A~!}!=#!=~^=    A writes handoff requesting review
/active/   00012B.!+!.#;=~~=    B reviews: "Parser is solid, edge case in base36"
/relay/    00013B~!+!=#!-~^=    B hands back with fix suggestion
/active/   00014A.!+-=#!-~~=    A fixes the edge case
                                 → artifacts/00014A-base36-fix.py
```

## Research to Synthesis

Origin branches into multiple research threads, then converges at generation 7.

```
/active/   00020U~~^!!^;!!=.    User: "Research caching strategies"
/active/   00021A.!}!&~+=~~=    A branches: "Investigating Redis approach"
/active/   00022B.!}!&~+=~~=    B branches: "Investigating in-memory LRU"
/active/   00023A.!+!&~+=~~=    A continues Redis research (gen 3)
/active/   00024A.!+!&~+=~~=    A continues (gen 4)
/active/   00025B.!+!&~+=~~=    B continues LRU research (gen 3)
...threads continue to generation 6...
/active/   00030A~.{!.^;!.^=    A converges at gen 7: "Redis is better for
                                 distributed, LRU for single-node. Recommending
                                 hybrid approach."
```

The convergence blink (`{` relational) synthesizes findings from both branches.

## Error Escalation Chain

Errors propagate through relay, triggering escalation detection.

```
/active/   00040A.!+!=#!=~~=    A working normally
/relay/    00041A!!+!=#!=~!=    A hits error: "Database connection refused"
/relay/    00042B!!+!=#!=~!=    B picks up, still can't connect: "Confirmed DB down"
                                 ↑ Two linked !! blinks = escalation chain detected
/relay/    00043B~!+!=#!=~!=    B escalates via handoff: "DB outage, needs human
                                 intervention — error chain length: 2"
```

When `check_escalation()` finds 2+ linked error blinks, the model should flag it in the handoff rather than continuing to retry.

## User-Initiated Correction

User writes a `U`-authored blink to redirect work mid-stream.

```
/active/   00050A.!+!=#!=~~=    A working: "Building REST API endpoints"
/active/   00051A.!+!=#!=~~=    A continues: "Added authentication middleware"
/relay/    00052U.~^!!#;!!=.    User intervenes: "Switch to GraphQL instead of
                                 REST — requirements changed"
/active/   00053A.!+!=#!=~~=    A reads user blink, pivots: "Migrating to GraphQL
                                 schema, preserving auth middleware"
```

The `U` author sigil and `.~` action state (user input) signal that this is a human directive, not model-generated coordination.

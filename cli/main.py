"""BSS CLI — Blink Sigil System command-line interface."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from src.bss.blink_file import BlinkFile, read as read_blink, write as write_blink
from src.bss.environment import BSSEnvironment
from src.bss.identifier import (
    generate,
    parse as parse_id,
    validate as validate_id,
    base36_decode,
)
from src.bss.sigils import (
    ACTION_STATES,
    DOMAIN,
    SUBDOMAIN,
    describe as describe_blink_id,
)
from src.bss.relay import check_escalation
from src.bss.roster import (
    RosterEntry,
    Roster,
    read_roster,
    update_roster,
    check_scope_compliance,
    generate_model_config,
    VALID_ROLES,
    VALID_CEILINGS,
)
from src.bss.generations import get_chain

app = typer.Typer(
    name="bss",
    help="Blink Sigil System — file-based coordination for stateless AI relay.",
    no_args_is_help=True,
)
console = Console()


def _get_env(path: Optional[Path] = None) -> BSSEnvironment:
    """Get or detect the BSS environment."""
    root = path or Path.cwd()
    env = BSSEnvironment(root)
    if not env.is_valid():
        console.print(f"[red]Not a BSS environment: {root}[/red]")
        console.print("Run [bold]bss init[/bold] to create one.")
        raise typer.Exit(1)
    return env


# ============================================================
# bss init
# ============================================================


@app.command()
def init(
    path: Optional[Path] = typer.Argument(None, help="Directory to initialize (default: current)"),
):
    """Initialize a new BSS environment."""
    root = path or Path.cwd()

    console.print(Panel(
        "[bold]BLINK SIGIL SYSTEM — v1.0[/bold]\n[dim]Alembic AI[/dim]",
        style="blue",
    ))
    console.print()

    env = BSSEnvironment.init(root)
    console.print(f"  [green]\u2192[/green] Created /relay/")
    console.print(f"  [green]\u2192[/green] Created /active/")
    console.print(f"  [green]\u2192[/green] Created /profile/")
    console.print(f"  [green]\u2192[/green] Created /archive/")
    console.print(f"  [green]\u2192[/green] Created /artifacts/")
    console.print()

    # Roster setup
    console.print("  [bold]Let's set up your roster.[/bold]")
    console.print()

    num_models = typer.prompt("  How many AI models will participate?", default=1, type=int)

    entries: list[RosterEntry] = []
    default_sigils = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    for i in range(num_models):
        console.print(f"\n  [bold]Model {i + 1}:[/bold]")
        name = typer.prompt("    Name/identifier", default=f"Model-{default_sigils[i]}")
        sigil = typer.prompt("    Author sigil", default=default_sigils[i])
        role = typer.prompt(
            "    Role (primary/reviewer/specialist/architect)",
            default="primary" if i == 0 else "reviewer",
        )
        ceiling = typer.prompt(
            "    Scope ceiling (atomic/local/regional/global)",
            default="global" if i == 0 else "local",
        )
        notes = typer.prompt("    Notes (optional)", default="")

        entries.append(RosterEntry(
            sigil=sigil.upper(),
            model_id=name,
            role=role,
            scope_ceiling=ceiling,
            notes=notes,
        ))

    console.print()

    # Write roster blink
    update_roster(env, entries)
    console.print(f"  [green]\u2192[/green] Wrote roster blink to /profile/")

    # Write origin blink
    origin_id = generate(
        sequence=int(env.next_sequence(), 36),
        author="U",
        action_energy="~", action_valence="~",
        relational="^",
        confidence="!", cognitive="!",
        domain="^", subdomain=";",
        scope="!", maturity=",",
        priority="=", sensitivity=".",
    )
    origin = BlinkFile(
        blink_id=origin_id,
        born_from=["Origin"],
        summary=(
            f"BSS environment initialized at {root}. "
            f"Roster configured with {num_models} model(s). "
            "Ready for coordination."
        ),
        lineage=[origin_id],
        links=[],
    )
    write_blink(origin, env.active_dir)
    console.print(f"  [green]\u2192[/green] Wrote origin blink to /active/")

    console.print()
    console.print(f"  [bold green]Environment ready.[/bold green] {env.relay_count() + 2} blinks written.")
    console.print(f"  Run [bold]bss status[/bold] to see your environment.")


# ============================================================
# bss status
# ============================================================


@app.command()
def status(
    path: Optional[Path] = typer.Option(None, "--path", "-p", help="BSS environment path"),
):
    """Show current environment state."""
    env = _get_env(path)

    relay_count = len(list(env.relay_dir.glob("*.md")))
    active_count = len(list(env.active_dir.glob("*.md")))
    profile_count = len(list(env.profile_dir.glob("*.md")))
    archive_count = len(list(env.archive_dir.rglob("*.md")))
    total = relay_count + active_count + profile_count + archive_count

    artifact_count = 0
    if env.artifacts_dir.exists():
        artifact_count = len([f for f in env.artifacts_dir.iterdir() if f.is_file()])

    console.print()
    console.print(f"  [bold]BSS Environment:[/bold] {env.root}")
    console.print(f"  Spec version: 1.0")
    console.print(f"  Total blinks: {total}")
    console.print()
    console.print(f"  /relay/    {relay_count} blinks")
    console.print(f"  /active/   {active_count} blinks")
    console.print(f"  /profile/  {profile_count} blinks")
    console.print(f"  /archive/  {archive_count} blinks")
    if artifact_count:
        console.print(f"  /artifacts/ {artifact_count} files")
    console.print()
    console.print(f"  Next sequence: {env.next_sequence()}")

    # Error chains
    chains = check_escalation(env)
    if chains:
        console.print(f"  [red]Error chains needing attention: {len(chains)}[/red]")

    # Latest blink
    highest = env.highest_sequence()
    if highest != "00000":
        console.print()
        # Find the latest blink
        for dirname in ["relay", "active", "profile"]:
            for f in (env.root / dirname).glob("*.md"):
                blink_name = f.name[:-3]  # Strip .md without losing trailing '.'
                if blink_name.startswith(highest):
                    try:
                        meta = parse_id(blink_name)
                        action = blink_name[6:8]
                        action_label = ACTION_STATES.get(action, "?")
                        console.print(f"  Latest blink: {blink_name}")
                        console.print(
                            f"    \u2192 {action_label} from "
                            f"{'User' if meta.author == 'U' else 'System' if meta.author == 'S' else f'Model {meta.author}'}"
                        )
                    except ValueError:
                        pass
    console.print()


# ============================================================
# bss read
# ============================================================


@app.command(name="read")
def read_cmd(
    blink_id: str = typer.Argument(..., help="Blink ID to read"),
    path: Optional[Path] = typer.Option(None, "--path", "-p"),
):
    """Read and display a blink."""
    env = _get_env(path)
    filepath = env.find_blink(blink_id)

    if filepath is None:
        console.print(f"[red]Blink not found: {blink_id}[/red]")
        raise typer.Exit(1)

    blink = read_blink(filepath)
    console.print()
    console.print(f"  [bold]{blink.blink_id}[/bold]  ({filepath.parent.name}/)")
    console.print()
    console.print(f"  Born from: {' | '.join(blink.born_from)}")
    console.print()
    console.print(f"  {blink.summary}")
    console.print()
    lineage_str = " \u2192 ".join(blink.lineage)
    console.print(f"  Lineage: {lineage_str}")
    if blink.links:
        console.print(f"  Links: {' | '.join(blink.links)}")
    console.print()


# ============================================================
# bss describe
# ============================================================


@app.command()
def describe(
    blink_id: str = typer.Argument(..., help="Blink ID to describe"),
):
    """Plain-English blink ID breakdown."""
    console.print()
    console.print(describe_blink_id(blink_id))
    console.print()


# ============================================================
# bss validate
# ============================================================


@app.command(name="validate")
def validate_cmd(
    blink_id: str = typer.Argument(..., help="Blink ID to validate"),
):
    """Validate a blink ID with violation report."""
    valid, violations = validate_id(blink_id)
    console.print()
    if valid:
        console.print(f"  [green]\u2713[/green] Valid blink ID: {blink_id}")
    else:
        console.print(f"  [red]\u2717[/red] Invalid blink ID: {blink_id}")
        for v in violations:
            console.print(f"    [red]\u2022[/red] {v}")
    console.print()


# ============================================================
# bss triage
# ============================================================


@app.command()
def triage(
    path: Optional[Path] = typer.Option(None, "--path", "-p"),
):
    """Show triaged relay queue."""
    env = _get_env(path)
    triaged = env.triage("relay")

    if not triaged:
        console.print("\n  /relay/ is empty. No handoffs pending.\n")
        return

    console.print(f"\n  [bold]/relay/[/bold] \u2014 {len(triaged)} blinks (triage order):\n")

    for i, blink in enumerate(triaged, 1):
        try:
            meta = parse_id(blink.blink_id)
            action = blink.blink_id[6:8]
            action_label = ACTION_STATES.get(action, "?")
            urgency = f"{meta.priority}{meta.sensitivity}"

            # Truncate summary
            summary = blink.summary[:60] + "..." if len(blink.summary) > 60 else blink.summary

            console.print(f"  {i}. [bold]{action}[/bold] {blink.blink_id}  {action_label} | {urgency}")
            console.print(f"     \u2192 \"{summary}\"")
            console.print()
        except ValueError:
            console.print(f"  {i}. {blink.blink_id} (parse error)")

    console.print()


# ============================================================
# bss log
# ============================================================


@app.command()
def log(
    last: int = typer.Option(10, "--last", "-n", help="Number of recent blinks to show"),
    path: Optional[Path] = typer.Option(None, "--path", "-p"),
):
    """Show recent blinks in sequence order."""
    env = _get_env(path)

    # Collect all blinks with their directory
    all_blinks: list[tuple[str, BlinkFile]] = []
    for dirname in ["relay", "active", "profile"]:
        for blink in env.scan(dirname):
            all_blinks.append((dirname, blink))

    # Sort by sequence (highest first)
    all_blinks.sort(
        key=lambda x: base36_decode(x[1].blink_id[:5]) if len(x[1].blink_id) >= 5 else 0,
        reverse=True,
    )

    # Take last N
    shown = all_blinks[:last]

    if not shown:
        console.print("\n  No blinks found.\n")
        return

    console.print()
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("Seq", style="dim")
    table.add_column("Au")
    table.add_column("Act")
    table.add_column("Rel")
    table.add_column("Dir", style="dim")
    table.add_column("Domain")
    table.add_column("Summary")
    table.add_column("Artifact", style="dim")

    for dirname, blink in shown:
        try:
            meta = parse_id(blink.blink_id)
            action = blink.blink_id[6:8]
            domain_label = DOMAIN.get(meta.domain, "?")
            subdomain_label = SUBDOMAIN.get(meta.subdomain, "?")
            theme = f"{domain_label.split('/')[0].strip()} + {subdomain_label.split('/')[0].strip()}"

            summary = blink.summary[:40] + "..." if len(blink.summary) > 40 else blink.summary
            summary = summary.replace("\n", " ")

            # Check for artifact
            artifact = env.find_artifact(meta.sequence, meta.author)
            artifact_name = artifact.name if artifact else ""

            table.add_row(
                meta.sequence,
                meta.author,
                action,
                meta.relational,
                f"/{dirname}/",
                theme,
                f'"{summary}"',
                f"\u2192 {artifact_name}" if artifact_name else "",
            )
        except ValueError:
            table.add_row(blink.blink_id[:5], "?", "??", "?", f"/{dirname}/", "", "", "")

    console.print(table)
    console.print()


# ============================================================
# bss roster
# ============================================================


@app.command()
def roster(
    path: Optional[Path] = typer.Option(None, "--path", "-p"),
):
    """Display current roster."""
    env = _get_env(path)
    r = read_roster(env)

    if r is None:
        console.print("\n  No roster found.\n")
        return

    console.print()
    table = Table(title="Model Roster", show_header=True, header_style="bold")
    table.add_column("Sigil")
    table.add_column("Model")
    table.add_column("Role")
    table.add_column("Scope Ceiling")
    table.add_column("Notes")

    for entry in r.entries:
        table.add_row(entry.sigil, entry.model_id, entry.role, entry.scope_ceiling, entry.notes)

    console.print(table)
    console.print()


# ============================================================
# bss tree
# ============================================================


@app.command()
def tree(
    blink_id: str = typer.Argument(..., help="Blink ID to trace lineage"),
    path: Optional[Path] = typer.Option(None, "--path", "-p"),
):
    """Show lineage tree for a blink."""
    env = _get_env(path)

    chain = get_chain(env, blink_id)

    if not chain:
        console.print(f"\n  [red]Blink not found: {blink_id}[/red]\n")
        raise typer.Exit(1)

    console.print()
    rich_tree = Tree(f"[bold]{chain[0].blink_id}[/bold]  ({_short_summary(chain[0])})")

    current_node = rich_tree
    for blink in chain[1:]:
        try:
            meta = parse_id(blink.blink_id)
            rel_symbol = {"^": "\u2500^", "}": "\u251c\u2500}", "+": "\u2514\u2500+",
                          "{": "\u2514\u2500{", "_": "\u2514\u2500_",
                          "=": "\u2514\u2500=", "#": "\u2514\u2500#"}.get(meta.relational, "\u2514\u2500")

            label = f"[bold]{blink.blink_id}[/bold]  ({_short_summary(blink)})"
            if blink.blink_id == blink_id:
                label += "  [green]\u2190 YOU ARE HERE[/green]"

            # Check for artifact
            artifact = env.find_artifact(meta.sequence, meta.author)
            if artifact:
                label += "  [dim][artifact][/dim]"

            current_node = current_node.add(label)
        except ValueError:
            current_node = current_node.add(blink.blink_id)

    console.print(rich_tree)
    console.print()


def _short_summary(blink: BlinkFile) -> str:
    """First 40 chars of summary."""
    s = blink.summary.replace("\n", " ")
    return s[:40] + "..." if len(s) > 40 else s


# ============================================================
# bss write
# ============================================================


@app.command(name="write")
def write_cmd(
    path: Optional[Path] = typer.Option(None, "--path", "-p"),
):
    """Interactive blink creation wizard."""
    env = _get_env(path)

    console.print()

    # Author
    author = typer.prompt("  Author sigil (U for user, A-Z for model)", default="U").upper()

    # Action state
    console.print("\n  What is this blink about?")
    action_choices = [
        ("~!", "Handoff to next model"),
        (".!", "Work in progress"),
        ("~.", "Completed work"),
        ("!!", "Error"),
        ("..", "Informational"),
        ("~~", "Idle"),
        ("!~", "Blocked"),
        ("!.", "Decision needed"),
        (".~", "Awaiting user input"),
        ("!#", "Cancelled"),
    ]
    for i, (code, label) in enumerate(action_choices, 1):
        console.print(f"    {i}. {label} ({code})")
    action_idx = typer.prompt("  Select", default=1, type=int) - 1
    action_energy = action_choices[action_idx][0][0]
    action_valence = action_choices[action_idx][0][1]

    # Relational
    console.print("\n  Relationship to existing work?")
    rel_choices = [
        ("^", "New thread (origin)"),
        ("+", "Continuing existing thread"),
        ("}", "Branching from existing thread"),
        ("{", "Merging/converging threads"),
        ("_", "Dead end / abandoned"),
        ("=", "Reinforcing / echoing"),
        ("#", "Contradicting / challenging"),
    ]
    for i, (code, label) in enumerate(rel_choices, 1):
        console.print(f"    {i}. {label} ({code})")
    rel_idx = typer.prompt("  Select", default=2, type=int) - 1
    relational = rel_choices[rel_idx][0]

    # Parent
    parent = None
    if relational != "^":
        parent = typer.prompt("  Parent blink ID")
        # Validate parent ID format
        parent_valid, parent_violations = validate_id(parent)
        if not parent_valid:
            console.print(f"\n  [red]Invalid parent blink ID:[/red] {'; '.join(parent_violations)}")
            raise typer.Exit(code=1)
        # Warn if parent not found (may be in an external environment)
        if not env.find_blink(parent):
            console.print(f"\n  [yellow]Warning:[/yellow] Parent blink '{parent}' not found in this environment.")

    # Confidence
    conf_choices = [("!", "High"), (".", "Moderate"), ("~", "Low"), (",", "Speculative")]
    console.print("\n  Confidence level?")
    for i, (code, label) in enumerate(conf_choices, 1):
        console.print(f"    {i}. {label} ({code})")
    conf_idx = typer.prompt("  Select", default=1, type=int) - 1
    confidence = conf_choices[conf_idx][0]

    # Cognitive
    cog_choices = [
        ("!", "Clarity"), ("=", "Flow"), ("^", "Breakthrough"),
        (".", "Resolution"), ("&", "Curiosity"), ("~", "Confusion"),
        ("%", "Frustration"), ("#", "Tension"),
    ]
    console.print("\n  Cognitive state?")
    for i, (code, label) in enumerate(cog_choices, 1):
        console.print(f"    {i}. {label} ({code})")
    cog_idx = typer.prompt("  Select", default=2, type=int) - 1
    cognitive = cog_choices[cog_idx][0]

    # Domain
    dom_choices = [
        ("#", "Work"), ("!", "Creation"), ("~", "Learning"), ("^", "System"),
        ("@", "Self"), ("&", "Relationships"), ("$", "Finance"),
        ("%", "Health"), ("+", "Play"), (";", "Conflict"),
    ]
    console.print("\n  Domain?")
    for i, (code, label) in enumerate(dom_choices, 1):
        console.print(f"    {i}. {label} ({code})")
    dom_idx = typer.prompt("  Select", default=1, type=int) - 1
    domain = dom_choices[dom_idx][0]

    # Subdomain
    sub_choices = [
        ("!", "Making"), ("~", "Exploring"), ("^", "Designing"),
        (".", "Maintaining"), ("=", "Communicating"), ("&", "Analyzing"),
        ("-", "Fixing"), ("+", "Growing"), (";", "Documenting"), (",", "Deciding"),
    ]
    console.print("\n  Subdomain (activity type)?")
    for i, (code, label) in enumerate(sub_choices, 1):
        console.print(f"    {i}. {label} ({code})")
    sub_idx = typer.prompt("  Select", default=1, type=int) - 1
    subdomain = sub_choices[sub_idx][0]

    # Scope
    scope_choices = [(".", "Atomic"), ("-", "Local"), ("=", "Regional"), ("!", "Global")]
    console.print("\n  Scope?")
    for i, (code, label) in enumerate(scope_choices, 1):
        console.print(f"    {i}. {label} ({code})")
    scope_idx = typer.prompt("  Select", default=2, type=int) - 1
    scope = scope_choices[scope_idx][0]

    # Maturity
    mat_choices = [(",", "Seed"), ("~", "In progress"), (".", "Near complete"),
                   ("!", "Complete"), ("-", "Needs revision")]
    console.print("\n  Maturity?")
    for i, (code, label) in enumerate(mat_choices, 1):
        console.print(f"    {i}. {label} ({code})")
    mat_idx = typer.prompt("  Select", default=2, type=int) - 1
    maturity = mat_choices[mat_idx][0]

    # Priority
    pri_choices = [("!", "Critical"), ("^", "High"), ("=", "Normal"),
                   (".", "Low"), ("~", "Background")]
    console.print("\n  Priority?")
    for i, (code, label) in enumerate(pri_choices, 1):
        console.print(f"    {i}. {label} ({code})")
    pri_idx = typer.prompt("  Select", default=3, type=int) - 1
    priority = pri_choices[pri_idx][0]

    # Sensitivity
    sens_choices = [("!", "Blocking"), ("^", "Soon"), ("=", "Whenever"), (".", "Passive")]
    console.print("\n  Time sensitivity?")
    for i, (code, label) in enumerate(sens_choices, 1):
        console.print(f"    {i}. {label} ({code})")
    sens_idx = typer.prompt("  Select", default=3, type=int) - 1
    sensitivity = sens_choices[sens_idx][0]

    # Generate the ID
    seq = env.next_sequence()
    blink_id = generate(
        sequence=seq,
        author=author,
        action_energy=action_energy,
        action_valence=action_valence,
        relational=relational,
        confidence=confidence,
        cognitive=cognitive,
        domain=domain,
        subdomain=subdomain,
        scope=scope,
        maturity=maturity,
        priority=priority,
        sensitivity=sensitivity,
    )

    # Scope compliance check
    roster = read_roster(env)
    if roster:
        temp_blink = BlinkFile(
            blink_id=blink_id,
            born_from=["Origin"],
            summary="temp",
            lineage=[blink_id],
            links=[],
        )
        if not check_scope_compliance(roster, author, temp_blink):
            entry = roster.get_entry(author)
            ceiling = entry.scope_ceiling if entry else "unknown"
            console.print(
                f"\n  [yellow]Warning: Author {author} has scope ceiling "
                f"'{ceiling}' but this blink uses scope '{scope}'.[/yellow]"
            )

    console.print(f"\n  [bold]Preview:[/bold]")
    console.print(f"    ID: {blink_id}")
    console.print(f"    {describe_blink_id(blink_id)}")

    # Summary
    console.print("\n  Summary (2-5 sentences):")
    summary = typer.prompt("  >")

    # Build the blink
    if parent:
        born_from = [parent]
        parent_path = env.find_blink(parent)
        if parent_path:
            parent_blink = read_blink(parent_path)
            lineage = parent_blink.lineage[-6:] + [blink_id]
        else:
            lineage = [parent, blink_id]
    else:
        born_from = ["Origin"]
        lineage = [blink_id]

    # Determine directory
    action = action_energy + action_valence
    if action in ("~!", "!!"):
        directory = env.relay_dir
        dir_name = "relay"
    elif author == "S":
        directory = env.profile_dir
        dir_name = "profile"
    else:
        directory = env.active_dir
        dir_name = "active"

    blink = BlinkFile(
        blink_id=blink_id,
        born_from=born_from,
        summary=summary,
        lineage=lineage,
        links=[],
    )

    confirm = typer.confirm(f"\n  Write this blink to /{dir_name}/?", default=True)
    if confirm:
        write_blink(blink, directory)
        console.print(f"  [green]\u2192[/green] Written to /{dir_name}/{blink_id}.md")
    else:
        console.print("  Cancelled.")

    console.print()


# ============================================================
# bss artifacts
# ============================================================


@app.command()
def artifacts(
    path: Optional[Path] = typer.Option(None, "--path", "-p"),
):
    """List all artifacts with parent blink info."""
    env = _get_env(path)

    files = env.list_artifacts()

    if not files:
        console.print("\n  No artifacts found.\n")
        return

    console.print()
    table = Table(title="Artifacts", show_header=True, header_style="bold")
    table.add_column("Artifact")
    table.add_column("Parent Blink")
    table.add_column("Size")

    for f in files:
        # Try to extract sequence + author from filename
        name = f.name
        if len(name) >= 7 and name[6] == "-":
            prefix = name[:6]
            parent = env.find_blink_by_prefix(prefix)
            parent_label = parent.name[:-3] if parent else f"{prefix}..."
        else:
            parent_label = "?"

        size = f.stat().st_size
        size_label = f"{size:,} B" if size < 1024 else f"{size / 1024:.1f} KB"
        table.add_row(name, parent_label, size_label)

    console.print(table)
    console.print()


# ============================================================
# bss artifact <sequence>
# ============================================================


@app.command()
def artifact(
    sequence: str = typer.Argument(..., help="5-char sequence or 6-char sequence+author prefix"),
    path: Optional[Path] = typer.Option(None, "--path", "-p"),
):
    """Show artifact details and parent blink info."""
    env = _get_env(path)

    # Search artifacts by prefix
    prefix = sequence.upper()
    if len(prefix) not in (5, 6):
        console.print(f"[red]Prefix must be 5 or 6 characters, got {len(prefix)}[/red]")
        raise typer.Exit(1)

    # Find matching artifact
    artifact_path = None
    search_prefix = prefix + ("-" if len(prefix) == 6 else "")
    for f in env.list_artifacts():
        if f.name.startswith(search_prefix) or (len(prefix) == 5 and f.name[:5] == prefix):
            artifact_path = f
            break

    if artifact_path is None:
        console.print(f"\n  [red]No artifact found matching '{prefix}'[/red]\n")
        raise typer.Exit(1)

    # Extract blink prefix from artifact name
    name = artifact_path.name
    blink_prefix = name[:6] if len(name) >= 7 and name[6] == "-" else None

    # Find parent blink
    parent_blink = None
    parent_path = None
    if blink_prefix:
        parent_path = env.find_blink_by_prefix(blink_prefix)
        if parent_path:
            parent_blink = read_blink(parent_path)

    # Display
    console.print()
    size = artifact_path.stat().st_size
    size_label = f"{size:,} B" if size < 1024 else f"{size / 1024:.1f} KB"

    panel_lines = [
        f"[bold]File:[/bold] {artifact_path.name}",
        f"[bold]Size:[/bold] {size_label}",
        f"[bold]Extension:[/bold] {artifact_path.suffix}",
    ]

    if parent_blink:
        panel_lines.append("")
        panel_lines.append(f"[bold]Parent Blink:[/bold] {parent_blink.blink_id}")
        panel_lines.append(f"[bold]Directory:[/bold] /{parent_path.parent.name}/")
        summary = parent_blink.summary.replace("\n", " ")
        if len(summary) > 80:
            summary = summary[:77] + "..."
        panel_lines.append(f"[bold]Summary:[/bold] {summary}")
    elif blink_prefix:
        panel_lines.append("")
        panel_lines.append(f"[bold]Parent Blink:[/bold] {blink_prefix}... (not found)")

    console.print(Panel(
        "\n".join(panel_lines),
        title=f"Artifact: {artifact_path.name}",
        style="blue",
    ))
    console.print()


# ============================================================
# bss produce <file>
# ============================================================


def _derive_slug(filename: str) -> str:
    """Derive an artifact slug from a filename.

    Lowercase, hyphens for separators, strip extension.
    """
    name = Path(filename).stem
    # Replace underscores, spaces, dots with hyphens
    slug = name.replace("_", "-").replace(" ", "-").replace(".", "-")
    # Lowercase
    slug = slug.lower()
    # Collapse multiple hyphens
    import re
    slug = re.sub(r"-+", "-", slug)
    # Strip leading/trailing hyphens
    slug = slug.strip("-")
    return slug


@app.command()
def produce(
    file: Path = typer.Argument(..., help="File to register as artifact"),
    blink: Optional[str] = typer.Option(None, "--blink", "-b", help="Link to existing blink ID"),
    slug: Optional[str] = typer.Option(None, "--slug", "-s", help="Artifact slug (default: derived from filename)"),
    path: Optional[Path] = typer.Option(None, "--path", "-p"),
):
    """Register an existing file as a BSS artifact."""
    env = _get_env(path)

    if not file.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(1)

    # Determine slug
    artifact_slug = slug or _derive_slug(file.name)

    # Determine parent blink
    blink_id = blink
    if blink_id is None:
        # Interactive: ask for blink ID or create one
        console.print()
        choice = typer.prompt(
            "  Link to existing blink ID, or 'new' to create one",
            default="new",
        )
        if choice.lower() == "new":
            # Create a simple informational blink
            seq = env.next_sequence()
            author = typer.prompt("  Author sigil", default="A").upper()
            summary = typer.prompt(
                "  Summary (2-5 sentences)",
                default=f"Produced artifact '{artifact_slug}' from {file.name}. Registered in artifacts directory.",
            )
            blink_id = generate(
                sequence=seq,
                author=author,
                action_energy="~",
                action_valence=".",
                relational="^",
                confidence="!",
                cognitive="=",
                domain="#",
                subdomain="!",
                scope="-",
                maturity="!",
                priority="=",
                sensitivity=".",
            )
            new_blink = BlinkFile(
                blink_id=blink_id,
                born_from=["Origin"],
                summary=summary,
                lineage=[blink_id],
                links=[],
            )
            write_blink(new_blink, env.active_dir)
            console.print(f"  [green]\u2192[/green] Created blink {blink_id}")
        else:
            blink_id = choice

    # Validate blink exists
    if env.find_blink(blink_id) is None:
        console.print(f"[red]Blink not found: {blink_id}[/red]")
        raise typer.Exit(1)

    # Register the artifact
    artifact_path = env.register_artifact(blink_id, file, artifact_slug)
    console.print(f"  [green]\u2192[/green] Registered artifact: {artifact_path.name}")
    console.print(f"    Linked to blink: {blink_id}")
    console.print()


# ============================================================
# bss roster-add
# ============================================================


@app.command(name="roster-add")
def roster_add(
    sigil: str = typer.Argument(..., help="Author sigil (single uppercase letter)"),
    model_id: str = typer.Argument(..., help="Model identifier"),
    role: str = typer.Option("reviewer", "--role", "-r", help="Role: primary/reviewer/specialist/architect"),
    ceiling: str = typer.Option("local", "--ceiling", "-c", help="Scope ceiling: atomic/local/regional/global"),
    notes: str = typer.Option("", "--notes", "-n", help="Notes about this model"),
    path: Optional[Path] = typer.Option(None, "--path", "-p"),
):
    """Add a model to the roster."""
    env = _get_env(path)

    sigil = sigil.upper()
    if len(sigil) != 1 or not sigil.isalnum():
        console.print("[red]Sigil must be a single alphanumeric character.[/red]")
        raise typer.Exit(1)

    if role not in VALID_ROLES:
        console.print(f"[red]Invalid role '{role}'. Must be one of: {', '.join(sorted(VALID_ROLES))}[/red]")
        raise typer.Exit(1)

    if ceiling not in VALID_CEILINGS:
        console.print(f"[red]Invalid ceiling '{ceiling}'. Must be one of: {', '.join(sorted(VALID_CEILINGS))}[/red]")
        raise typer.Exit(1)

    # Read current roster
    current = read_roster(env)
    entries = list(current.entries) if current else []
    old_id = current.blink_id if current else None

    # Check for duplicate sigil
    for entry in entries:
        if entry.sigil == sigil:
            console.print(f"[red]Sigil '{sigil}' already exists in roster.[/red]")
            raise typer.Exit(1)

    # Add new entry
    entries.append(RosterEntry(
        sigil=sigil,
        model_id=model_id,
        role=role,
        scope_ceiling=ceiling,
        notes=notes,
    ))

    new_roster = update_roster(env, entries, old_roster_id=old_id)
    console.print(f"\n  [green]\u2192[/green] Added {sigil} ({model_id}) to roster.")
    console.print(f"    Role: {role}, Ceiling: {ceiling}")
    console.print(f"    Roster blink: {new_roster.blink_id}\n")


# ============================================================
# bss roster-remove
# ============================================================


@app.command(name="roster-remove")
def roster_remove(
    sigil: str = typer.Argument(..., help="Author sigil to remove"),
    path: Optional[Path] = typer.Option(None, "--path", "-p"),
):
    """Remove a model from the roster."""
    env = _get_env(path)

    sigil = sigil.upper()

    current = read_roster(env)
    if current is None:
        console.print("[red]No roster found.[/red]")
        raise typer.Exit(1)

    entry = current.get_entry(sigil)
    if entry is None:
        console.print(f"[red]Sigil '{sigil}' not found in roster.[/red]")
        raise typer.Exit(1)

    confirm = typer.confirm(
        f"  Remove {sigil} ({entry.model_id}) from roster?",
        default=False,
    )
    if not confirm:
        console.print("  Cancelled.")
        return

    new_entries = [e for e in current.entries if e.sigil != sigil]
    new_roster = update_roster(env, new_entries, old_roster_id=current.blink_id)
    console.print(f"\n  [green]\u2192[/green] Removed {sigil} ({entry.model_id}) from roster.")
    console.print(f"    Roster blink: {new_roster.blink_id}\n")


# ============================================================
# bss roster-update
# ============================================================


@app.command(name="roster-update")
def roster_update_cmd(
    sigil: str = typer.Argument(..., help="Author sigil to update"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="New model identifier"),
    role: Optional[str] = typer.Option(None, "--role", "-r", help="New role"),
    ceiling: Optional[str] = typer.Option(None, "--ceiling", "-c", help="New scope ceiling"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="New notes"),
    path: Optional[Path] = typer.Option(None, "--path", "-p"),
):
    """Update a model's roster entry."""
    env = _get_env(path)

    sigil = sigil.upper()

    current = read_roster(env)
    if current is None:
        console.print("[red]No roster found.[/red]")
        raise typer.Exit(1)

    entry = current.get_entry(sigil)
    if entry is None:
        console.print(f"[red]Sigil '{sigil}' not found in roster.[/red]")
        raise typer.Exit(1)

    if role is not None and role not in VALID_ROLES:
        console.print(f"[red]Invalid role '{role}'. Must be one of: {', '.join(sorted(VALID_ROLES))}[/red]")
        raise typer.Exit(1)

    if ceiling is not None and ceiling not in VALID_CEILINGS:
        console.print(f"[red]Invalid ceiling '{ceiling}'. Must be one of: {', '.join(sorted(VALID_CEILINGS))}[/red]")
        raise typer.Exit(1)

    # Apply updates
    new_entries = []
    for e in current.entries:
        if e.sigil == sigil:
            new_entries.append(RosterEntry(
                sigil=sigil,
                model_id=model if model is not None else e.model_id,
                role=role if role is not None else e.role,
                scope_ceiling=ceiling if ceiling is not None else e.scope_ceiling,
                notes=notes if notes is not None else e.notes,
            ))
        else:
            new_entries.append(e)

    new_roster = update_roster(env, new_entries, old_roster_id=current.blink_id)
    console.print(f"\n  [green]\u2192[/green] Updated {sigil} in roster.")
    console.print(f"    Roster blink: {new_roster.blink_id}\n")


# ============================================================
# bss roster-config
# ============================================================


@app.command(name="roster-config")
def roster_config(
    sigil: str = typer.Argument(..., help="Author sigil to generate config for"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file (default: stdout)"),
    path: Optional[Path] = typer.Option(None, "--path", "-p"),
):
    """Generate model configuration (CLAUDE.md-style) for a roster member."""
    env = _get_env(path)

    sigil = sigil.upper()

    current = read_roster(env)
    if current is None:
        console.print("[red]No roster found.[/red]")
        raise typer.Exit(1)

    try:
        config = generate_model_config(current, sigil, env)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    if output:
        output.write_text(config, encoding="utf-8")
        console.print(f"\n  [green]\u2192[/green] Config written to {output}\n")
    else:
        console.print()
        console.print(config)
        console.print()


# ============================================================
# bss relay
# ============================================================


@app.command()
def relay(
    path: Optional[Path] = typer.Argument(None, help="BSS environment path (default: current)"),
    setup: bool = typer.Option(False, "--setup", help="Run model setup wizard (opens in TUI)"),
):
    """Launch the BSS relay terminal interface."""
    from terminal.app import BSSRelayApp
    BSSRelayApp(path or Path.cwd(), force_setup=setup).run()


if __name__ == "__main__":
    app()

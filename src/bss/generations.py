"""BSS generation tracking and forced convergence."""

from __future__ import annotations

from bss.blink_file import BlinkFile, read as read_blink, write as write_blink
from bss.environment import BSSEnvironment
from bss.identifier import generate, parse as parse_id

MAX_GENERATION = 7


def get_generation(env: BSSEnvironment, blink_id: str) -> int:
    """Walk the Born from chain to determine a blink's generation.

    Generation 1 = origin (^) or convergence ({) blink.
    Each continuation (+) or branch (}) increments by 1.

    Args:
        env: The BSS environment.
        blink_id: The blink to check.

    Returns:
        The generation number (1-7+).
    """
    generation = 1
    current_id = blink_id

    visited: set[str] = set()

    for _ in range(50):
        if current_id in visited:
            break
        visited.add(current_id)

        # Check relational sigil
        try:
            meta = parse_id(current_id)
        except ValueError:
            break

        # Origin or convergence = generation 1
        if meta.relational in ("^", "{"):
            return generation

        # Find the blink file to get its parent
        path = env.find_blink(current_id)
        if path is None:
            break

        blink = read_blink(path)
        if blink.born_from == ["Origin"] or not blink.born_from:
            return generation

        # Walk up to parent
        generation += 1
        current_id = blink.born_from[0]

    return generation


def needs_convergence(env: BSSEnvironment, blink_id: str) -> bool:
    """Check if a blink is at generation 7 and the next write must converge.

    Args:
        env: The BSS environment.
        blink_id: The blink to check.

    Returns:
        True if this blink is at generation 7.
    """
    return get_generation(env, blink_id) >= MAX_GENERATION


def get_chain(env: BSSEnvironment, blink_id: str, max_depth: int = 7) -> list[BlinkFile]:
    """Walk backwards from a blink, collecting the chain up to max_depth.

    Args:
        env: The BSS environment.
        blink_id: The starting blink.
        max_depth: Maximum chain length to collect.

    Returns:
        List of BlinkFile objects from oldest to newest.
    """
    chain: list[BlinkFile] = []
    current_id = blink_id
    visited: set[str] = set()

    while len(chain) < max_depth:
        if current_id in visited:
            break
        visited.add(current_id)

        path = env.find_blink(current_id)
        if path is None:
            break

        blink = read_blink(path)
        chain.insert(0, blink)

        if blink.born_from == ["Origin"] or not blink.born_from:
            break

        current_id = blink.born_from[0]

    return chain


def converge(
    env: BSSEnvironment,
    chain: list[BlinkFile],
    summary: str,
    author: str = "A",
    domain: str = "#",
    subdomain: str = "!",
    scope: str = "=",
) -> BlinkFile:
    """Write a convergence blink synthesizing a generation chain.

    The convergence blink:
    - Has relational sigil '{' (convergence)
    - Resets generation to 1 for the new chain
    - Moves key ancestor references to Links
    - Starts a new lineage from itself

    Args:
        env: The BSS environment.
        chain: List of BlinkFile objects to synthesize.
        summary: Synthesis summary covering the chain.
        author: Author sigil.

    Returns:
        The convergence BlinkFile.
    """
    seq = env.next_sequence()

    blink_id = generate(
        sequence=seq,
        author=author,
        action_energy="~",
        action_valence=".",
        relational="{",  # Convergence
        confidence="!",
        cognitive=".",  # Resolution
        domain=domain,
        subdomain=subdomain,
        scope=scope,
        maturity="~",
        priority="=",
        sensitivity="=",
    )

    # Born from: the last blink in the chain (and optionally earlier ones)
    last_blink = chain[-1] if chain else None
    born_from = [last_blink.blink_id] if last_blink else ["Origin"]

    # Links: key blinks from the preceding chain
    links = [b.blink_id for b in chain]

    # New lineage starts from this convergence blink
    lineage = [blink_id]

    blink = BlinkFile(
        blink_id=blink_id,
        born_from=born_from,
        summary=summary,
        lineage=lineage,
        links=links,
    )

    write_blink(blink, env.active_dir)
    return blink

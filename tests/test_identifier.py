"""Module 8.1 validation tests and identifier engine tests."""

import pytest

from src.bss.identifier import (
    BlinkMetadata,
    base36_decode,
    base36_encode,
    generate,
    next_sequence,
    parse,
    validate,
)
from src.bss.sigils import (
    VALID_ACTION_COMPOUNDS,
    VALID_CHARS,
    describe,
)


# ============================================================
# Module 8.1 — Canonical Validation Tests
# ============================================================
#
# NOTE: Some canonical test vectors in the spec (v1.0 Module 8.1)
# contain sigil values that are not in the grammar definitions
# (e.g., '=' at position 12 in 00001A~~^!!=~;,~. is not a valid
# domain sigil per Section 3.3). Where the grammar (Module 3) and
# the test vectors (Module 8) conflict, the grammar is authoritative.
#
# The spec also states "Blink 95 (0002F in base-36)" but 0002F
# actually decodes to 87 in decimal. Our implementation is
# mathematically correct: 0*36^4 + 0*36^3 + 2*36^2 + 15*36 + 87.
#
# These discrepancies are tracked as spec errata.
# ============================================================


class TestCanonicalValid:
    """The following blink identifiers from Module 8.1 MUST be parsed correctly.

    Where a canonical vector has a grammar violation, we test both the raw
    parse (which succeeds since parse doesn't validate) and note the
    validation result.
    """

    def test_second_canonical_blink(self):
        """0002FB~!}!^#!=~^= — Model B, handoff, branch, breakthrough.

        This is fully valid against the grammar. 0002F = 87 decimal
        (spec annotation says 95, which is a documentation error).
        """
        blink_id = "0002FB~!}!^#!=~^="
        valid, violations = validate(blink_id)
        assert valid, f"Should be valid but got violations: {violations}"
        meta = parse(blink_id)
        assert meta.sequence == "0002F"
        assert meta.sequence_decimal == 87  # Spec says 95, actual is 87
        assert meta.author == "B"
        assert meta.action_energy == "~"
        assert meta.action_valence == "!"
        assert meta.relational == "}"
        assert meta.confidence == "!"
        assert meta.cognitive == "^"
        assert meta.domain == "#"
        assert meta.subdomain == "!"
        assert meta.scope == "="
        assert meta.maturity == "~"
        assert meta.priority == "^"
        assert meta.sensitivity == "="

    def test_user_blink_informational(self):
        """00ZZZU..+.=@&.!.. — User blink, informational, continuation, self-analysis.

        Fully valid against the grammar.
        """
        blink_id = "00ZZZU..+.=@&.!.."
        valid, violations = validate(blink_id)
        assert valid, f"Should be valid but got violations: {violations}"
        meta = parse(blink_id)
        assert meta.sequence == "00ZZZ"
        assert meta.author == "U"
        assert meta.action_energy == "."
        assert meta.action_valence == "."
        assert meta.relational == "+"
        assert meta.confidence == "."
        assert meta.cognitive == "="
        assert meta.domain == "@"
        assert meta.subdomain == "&"
        assert meta.scope == "."
        assert meta.maturity == "!"
        assert meta.priority == "."
        assert meta.sensitivity == "."

    def test_foundation_origin_blink(self):
        """00001U~~^!!^;!!=. — The actual origin blink (corrected scope sigil).

        Foundation blink for the BSS reference implementation. Corrected
        from build plan draft which had ',' at scope (invalid per grammar).
        """
        blink_id = "00001U~~^!!^;!!=."
        valid, violations = validate(blink_id)
        assert valid, f"Foundation origin blink should be valid: {violations}"
        meta = parse(blink_id)
        assert meta.sequence == "00001"
        assert meta.sequence_decimal == 1
        assert meta.author == "U"
        assert meta.action_energy == "~"
        assert meta.action_valence == "~"
        assert meta.relational == "^"
        assert meta.confidence == "!"
        assert meta.cognitive == "!"
        assert meta.domain == "^"  # System / meta
        assert meta.subdomain == ";"  # Documenting
        assert meta.scope == "!"  # Global

    def test_foundation_roster_blink(self):
        """00002S~~^!!^;.!=. — The roster blink from the build plan."""
        blink_id = "00002S~~^!!^;.!=."
        valid, violations = validate(blink_id)
        assert valid, f"Foundation roster blink should be valid: {violations}"
        meta = parse(blink_id)
        assert meta.sequence == "00002"
        assert meta.author == "S"
        assert meta.relational == "^"

    def test_spec_canonical_first_blink_parse(self):
        """00001A~~^!!=~;,~. — First canonical vector.

        NOTE: This blink contains '=' at position 12 (domain) which is
        not in the domain grammar {@ # $ & ! ~ % ^ + ;}. The parser
        still extracts all fields. Validation correctly rejects it.
        This documents a spec errata in Module 8.1.
        """
        blink_id = "00001A~~^!!=~;,~."
        # Parse still works (it doesn't validate)
        meta = parse(blink_id)
        assert meta.sequence == "00001"
        assert meta.author == "A"
        assert meta.action_energy == "~"
        assert meta.action_valence == "~"
        assert meta.relational == "^"
        assert meta.confidence == "!"
        assert meta.cognitive == "!"
        # Position 12 = '=' — not in domain set, errata
        assert meta.domain == "="
        # Validation catches the errata
        valid, violations = validate(blink_id)
        assert not valid, "Spec errata: '=' is not a valid domain sigil"

    def test_spec_canonical_system_blink_parse(self):
        """0000SA~.+=.^~-!!! — Fourth canonical vector.

        NOTE: This blink contains '=' at position 10 (confidence) which
        is not in the confidence grammar {! . ~ ,}. Documents spec errata.
        """
        blink_id = "0000SA~.+=.^~-!!!"
        meta = parse(blink_id)
        assert meta.sequence == "0000S"
        assert meta.author == "A"
        assert meta.action_energy == "~"
        assert meta.action_valence == "."
        assert meta.relational == "+"
        # Position 10 = '=' — not in confidence set, errata
        assert meta.confidence == "="
        valid, violations = validate(blink_id)
        assert not valid, "Spec errata: '=' is not a valid confidence sigil"


class TestCanonicalInvalid:
    """The following blink identifiers are INVALID and MUST be rejected."""

    def test_too_short_16_chars(self):
        """0001A~~^!!=~;,~. — 16 characters (too short)"""
        blink_id = "0001A~~^!!=~;,~."
        valid, violations = validate(blink_id)
        assert not valid
        assert any("Length" in v or "16" in v for v in violations)

    def test_too_long_18_chars(self):
        """00001A~~^!!=~;,~.. — 18 characters (too long)"""
        blink_id = "00001A~~^!!=~;,~.."
        valid, violations = validate(blink_id)
        assert not valid
        assert any("Length" in v or "18" in v for v in violations)

    def test_lowercase_in_sequence(self):
        """00001a~~^!!=~;,~. — Lowercase in sequence (position 6 is lowercase 'a').

        The spec says 'Lowercase in sequence (position 1-5 must be uppercase)'
        but 'a' is at position 6 (author). Lowercase author is still invalid
        since author set is [A-Z0-9].
        """
        blink_id = "00001a~~^!!=~;,~."
        valid, violations = validate(blink_id)
        assert not valid
        # The lowercase 'a' is at position 6 (author), which rejects it
        assert any("author" in v.lower() or "sequence" in v.lower() for v in violations)

    def test_invalid_action_state(self):
        """000010~?^!!=~;,~. — Invalid action state ~?"""
        blink_id = "000010~?^!!=~;,~."
        valid, violations = validate(blink_id)
        assert not valid
        assert any("action" in v.lower() for v in violations)

    def test_invalid_relational_sigil(self):
        """00001A~~*!!=~;,~. — Invalid relational sigil *"""
        blink_id = "00001A~~*!!=~;,~."
        valid, violations = validate(blink_id)
        assert not valid
        assert any("relational" in v.lower() for v in violations)


# ============================================================
# Additional Edge Cases
# ============================================================


class TestSequenceEdgeCases:
    """Sequence validation edge cases."""

    def test_sequence_00000_rejected(self):
        """Sequence 00000 is reserved and MUST NOT be used."""
        blink_id = "00000A~~^!!=~;,~."
        valid, violations = validate(blink_id)
        assert not valid
        assert any("00000" in v or "reserved" in v.lower() for v in violations)

    def test_sequence_zzzzz_accepted(self):
        """Sequence ZZZZZ (max value) is valid."""
        blink_id = "ZZZZZB~!+.=#.-~.."
        valid, violations = validate(blink_id)
        assert valid, f"ZZZZZ should be valid but got: {violations}"

    def test_sequence_00001_accepted(self):
        """Sequence 00001 (min valid value) is valid."""
        blink_id = "00001A~~+.=#.-~.."
        valid, violations = validate(blink_id)
        assert valid, f"00001 should be valid but got: {violations}"


class TestAllActionCompounds:
    """Every valid action compound must be accepted individually."""

    @pytest.mark.parametrize("compound", sorted(VALID_ACTION_COMPOUNDS))
    def test_valid_action_compound(self, compound):
        blink_id = f"00001A{compound}+.=#.-~.."
        valid, violations = validate(blink_id)
        assert valid, f"Action compound '{compound}' should be valid: {violations}"

    @pytest.mark.parametrize(
        "compound",
        ["~#", ".#", "##", "!!", "~~", "~!", "~.", "!~", "!.", ".!", "..", ".~", "!#"],
    )
    def test_known_compounds_explicit(self, compound):
        """Explicitly test that known compounds are in the valid set or not."""
        if compound in VALID_ACTION_COMPOUNDS:
            blink_id = f"00001A{compound}+.=#.-~.."
            valid, _ = validate(blink_id)
            assert valid
        else:
            blink_id = f"00001A{compound}+.=#.-~.."
            valid, _ = validate(blink_id)
            assert not valid

    @pytest.mark.parametrize("compound", ["~#", "##", "#!", "#~", "#.", "?."])
    def test_invalid_action_compounds_rejected(self, compound):
        blink_id = f"00001A{compound}+.=#.-~.."
        valid, violations = validate(blink_id)
        assert not valid, f"Action compound '{compound}' should be invalid"


# ============================================================
# Exhaustive Sigil Position Tests
# ============================================================


class TestEveryValidSigil:
    """Test that every valid sigil in every position is accepted."""

    def _make_valid_base(self) -> str:
        """A known-valid blink ID to use as a base."""
        return "00001A~~+.=#.-~.."

    @pytest.mark.parametrize("sigil", sorted(VALID_CHARS["relational"]))
    def test_all_relational_sigils(self, sigil):
        base = list("00001A~~+.=#.-~..")
        base[8] = sigil  # Position 9 (0-indexed = 8)
        blink_id = "".join(base)
        valid, violations = validate(blink_id)
        assert valid, f"Relational '{sigil}' should be valid: {violations}"

    @pytest.mark.parametrize("sigil", sorted(VALID_CHARS["confidence"]))
    def test_all_confidence_sigils(self, sigil):
        base = list("00001A~~+.=#.-~..")
        base[9] = sigil
        blink_id = "".join(base)
        valid, violations = validate(blink_id)
        assert valid, f"Confidence '{sigil}' should be valid: {violations}"

    @pytest.mark.parametrize("sigil", sorted(VALID_CHARS["cognitive"]))
    def test_all_cognitive_sigils(self, sigil):
        base = list("00001A~~+.=#.-~..")
        base[10] = sigil
        blink_id = "".join(base)
        valid, violations = validate(blink_id)
        assert valid, f"Cognitive '{sigil}' should be valid: {violations}"

    @pytest.mark.parametrize("sigil", sorted(VALID_CHARS["domain"]))
    def test_all_domain_sigils(self, sigil):
        base = list("00001A~~+.=#.-~..")
        base[11] = sigil
        blink_id = "".join(base)
        valid, violations = validate(blink_id)
        assert valid, f"Domain '{sigil}' should be valid: {violations}"

    @pytest.mark.parametrize("sigil", sorted(VALID_CHARS["subdomain"]))
    def test_all_subdomain_sigils(self, sigil):
        base = list("00001A~~+.=#.-~..")
        base[12] = sigil
        blink_id = "".join(base)
        valid, violations = validate(blink_id)
        assert valid, f"Subdomain '{sigil}' should be valid: {violations}"

    @pytest.mark.parametrize("sigil", sorted(VALID_CHARS["scope"]))
    def test_all_scope_sigils(self, sigil):
        base = list("00001A~~+.=#.-~..")
        base[13] = sigil
        blink_id = "".join(base)
        valid, violations = validate(blink_id)
        assert valid, f"Scope '{sigil}' should be valid: {violations}"

    @pytest.mark.parametrize("sigil", sorted(VALID_CHARS["maturity"]))
    def test_all_maturity_sigils(self, sigil):
        base = list("00001A~~+.=#.-~..")
        base[14] = sigil
        blink_id = "".join(base)
        valid, violations = validate(blink_id)
        assert valid, f"Maturity '{sigil}' should be valid: {violations}"

    @pytest.mark.parametrize("sigil", sorted(VALID_CHARS["priority"]))
    def test_all_priority_sigils(self, sigil):
        base = list("00001A~~+.=#.-~..")
        base[15] = sigil
        blink_id = "".join(base)
        valid, violations = validate(blink_id)
        assert valid, f"Priority '{sigil}' should be valid: {violations}"

    @pytest.mark.parametrize("sigil", sorted(VALID_CHARS["sensitivity"]))
    def test_all_sensitivity_sigils(self, sigil):
        base = list("00001A~~+.=#.-~..")
        base[16] = sigil
        blink_id = "".join(base)
        valid, violations = validate(blink_id)
        assert valid, f"Sensitivity '{sigil}' should be valid: {violations}"


# ============================================================
# Base-36 Encoding/Decoding
# ============================================================


class TestBase36:
    """Base-36 encoding and decoding utilities."""

    def test_encode_1(self):
        assert base36_encode(1) == "00001"

    def test_encode_10(self):
        assert base36_encode(10) == "0000A"

    def test_encode_36(self):
        assert base36_encode(36) == "00010"

    def test_encode_0(self):
        assert base36_encode(0) == "00000"

    def test_encode_max(self):
        assert base36_encode(60_466_175) == "ZZZZZ"

    def test_encode_87_is_0002F(self):
        """Verify that 87 decimal = 0002F base-36 (spec says 95, actual is 87)."""
        assert base36_encode(87) == "0002F"

    def test_encode_95_is_0002N(self):
        """95 decimal = 0002N base-36 (not 0002F as spec annotation claims)."""
        assert base36_encode(95) == "0002N"

    def test_decode_00001(self):
        assert base36_decode("00001") == 1

    def test_decode_0000A(self):
        assert base36_decode("0000A") == 10

    def test_decode_0002F(self):
        """0002F base-36 = 87 decimal."""
        assert base36_decode("0002F") == 87

    def test_decode_ZZZZZ(self):
        assert base36_decode("ZZZZZ") == 60_466_175

    def test_roundtrip(self):
        for n in [1, 10, 36, 87, 95, 100, 999, 1000, 10000, 60_466_175]:
            assert base36_decode(base36_encode(n)) == n

    def test_encode_negative_raises(self):
        with pytest.raises(ValueError):
            base36_encode(-1)

    def test_spec_reference_table(self):
        """Verify Appendix B reference values."""
        assert base36_encode(1) == "00001"
        assert base36_encode(10) == "0000A"
        assert base36_encode(36) == "00010"
        assert base36_encode(100) == "0002S"
        assert base36_encode(999) == "000RR"
        assert base36_encode(1000) == "000RS"
        assert base36_encode(10000) == "007PS"
        assert base36_encode(100000) == "0255S"
        assert base36_encode(1000000) == "0LFLS"
        assert base36_encode(60466175) == "ZZZZZ"


# ============================================================
# Parse Function
# ============================================================


class TestParse:
    """parse() function tests."""

    def test_parse_returns_dataclass(self):
        meta = parse("0002FB~!}!^#!=~^=")
        assert isinstance(meta, BlinkMetadata)

    def test_parse_wrong_length_raises(self):
        with pytest.raises(ValueError, match="17"):
            parse("short")

    def test_parse_all_positions(self):
        meta = parse("0002FB~!}!^#!=~^=")
        assert meta.sequence == "0002F"
        assert meta.sequence_decimal == 87  # 0002F = 87, not 95
        assert meta.author == "B"
        assert meta.action_energy == "~"
        assert meta.action_valence == "!"
        assert meta.relational == "}"
        assert meta.confidence == "!"
        assert meta.cognitive == "^"
        assert meta.domain == "#"
        assert meta.subdomain == "!"
        assert meta.scope == "="
        assert meta.maturity == "~"
        assert meta.priority == "^"
        assert meta.sensitivity == "="


# ============================================================
# Generate Function
# ============================================================


class TestGenerate:
    """generate() function tests."""

    def test_generate_with_defaults(self):
        blink_id = generate(sequence=1, author="A")
        assert len(blink_id) == 17
        valid, _ = validate(blink_id)
        assert valid

    def test_generate_with_all_kwargs(self):
        blink_id = generate(
            sequence=87,  # 0002F in base-36
            author="B",
            action_energy="~",
            action_valence="!",
            relational="}",
            confidence="!",
            cognitive="^",
            domain="#",
            subdomain="!",
            scope="=",
            maturity="~",
            priority="^",
            sensitivity="=",
        )
        assert blink_id == "0002FB~!}!^#!=~^="

    def test_generate_with_string_sequence(self):
        blink_id = generate(sequence="0002F", author="A")
        assert blink_id.startswith("0002F")

    def test_generate_invalid_raises(self):
        with pytest.raises(ValueError):
            generate(sequence=0, author="A")  # 00000 is reserved

    def test_generate_roundtrip(self):
        blink_id = generate(
            sequence=42,
            author="C",
            action_energy="!",
            action_valence="!",
            relational="^",
            confidence="~",
            cognitive="%",
            domain="#",
            subdomain="-",
            scope="=",
            maturity="~",
            priority="!",
            sensitivity="!",
        )
        meta = parse(blink_id)
        assert meta.sequence_decimal == 42
        assert meta.author == "C"
        assert meta.action_energy == "!"
        assert meta.action_valence == "!"
        assert meta.relational == "^"
        assert meta.confidence == "~"
        assert meta.cognitive == "%"
        assert meta.domain == "#"
        assert meta.subdomain == "-"


# ============================================================
# Next Sequence
# ============================================================


class TestNextSequence:
    """next_sequence() function tests."""

    def test_increment_simple(self):
        assert next_sequence("00001") == "00002"

    def test_increment_rollover(self):
        assert next_sequence("00009") == "0000A"

    def test_increment_Z_rollover(self):
        assert next_sequence("0000Z") == "00010"

    def test_increment_max_raises(self):
        with pytest.raises(ValueError, match="exhausted"):
            next_sequence("ZZZZZ")


# ============================================================
# Describe Function
# ============================================================


class TestDescribe:
    """describe() function for human-readable output."""

    def test_describe_valid(self):
        result = describe("0002FB~!}!^#!=~^=")
        assert "Blink ID: 0002FB~!}!^#!=~^=" in result
        assert "Sequence" in result
        assert "87" in result  # 0002F = 87
        assert "Handoff" in result

    def test_describe_invalid(self):
        result = describe("short")
        assert "Invalid" in result


# ============================================================
# Sigil Character Set Completeness
# ============================================================


class TestSigilCompleteness:
    """Verify that all sigil maps are consistent with VALID_CHARS."""

    def test_relational_chars_match(self):
        from src.bss.sigils import RELATIONAL
        assert set(RELATIONAL.keys()) == VALID_CHARS["relational"]

    def test_confidence_chars_match(self):
        from src.bss.sigils import CONFIDENCE
        assert set(CONFIDENCE.keys()) == VALID_CHARS["confidence"]

    def test_cognitive_chars_match(self):
        from src.bss.sigils import COGNITIVE
        assert set(COGNITIVE.keys()) == VALID_CHARS["cognitive"]

    def test_domain_chars_match(self):
        from src.bss.sigils import DOMAIN
        assert set(DOMAIN.keys()) == VALID_CHARS["domain"]

    def test_subdomain_chars_match(self):
        from src.bss.sigils import SUBDOMAIN
        assert set(SUBDOMAIN.keys()) == VALID_CHARS["subdomain"]

    def test_scope_chars_match(self):
        from src.bss.sigils import SCOPE
        assert set(SCOPE.keys()) == VALID_CHARS["scope"]

    def test_maturity_chars_match(self):
        from src.bss.sigils import MATURITY
        assert set(MATURITY.keys()) == VALID_CHARS["maturity"]

    def test_priority_chars_match(self):
        from src.bss.sigils import PRIORITY
        assert set(PRIORITY.keys()) == VALID_CHARS["priority"]

    def test_sensitivity_chars_match(self):
        from src.bss.sigils import SENSITIVITY
        assert set(SENSITIVITY.keys()) == VALID_CHARS["sensitivity"]

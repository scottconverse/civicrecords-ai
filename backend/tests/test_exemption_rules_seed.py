import re
import pytest


def test_all_50_states_plus_dc_covered():
    """E-U1: At least one rule per state."""
    from scripts.seed_rules import RULES

    state_codes = {r["state_code"] for r in RULES}
    all_states = {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC",
    }
    missing = all_states - state_codes
    assert not missing, f"Missing states: {missing}"


def test_each_state_has_keyword_rule():
    """E-U4: Every state has at least one keyword rule."""
    from scripts.seed_rules import RULES

    keyword_states = {r["state_code"] for r in RULES if r["rule_type"] == "keyword"}
    all_states = {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC",
    }
    missing = all_states - keyword_states
    assert not missing, f"States without keyword rules: {missing}"


def test_regex_rules_are_valid():
    """E-U5: All regex rule definitions compile successfully."""
    from scripts.seed_rules import RULES

    for rule in RULES:
        if rule["rule_type"] == "regex":
            try:
                re.compile(rule["rule_definition"])
            except re.error as e:
                pytest.fail(
                    f"Invalid regex for {rule['state_code']}/{rule['category']}: "
                    f"{rule['rule_definition']} — {e}"
                )


def test_all_rules_have_descriptions():
    """Every rule has a non-empty description."""
    from scripts.seed_rules import RULES

    for i, rule in enumerate(RULES):
        assert rule.get("description"), (
            f"Rule {i} ({rule['state_code']}/{rule['category']}) missing description"
        )

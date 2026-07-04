"""
MLBB NexusOS v1.3.2 Safe Match Gate - failure pair add-on

Purpose:
Prevent weak reference_result_icons matches from allowing Hero Dictionary fallback
or semantic candidates to become incorrect Top candidates.

Failure seed:
FE-HERO-V132-20260705-0001
"""

FAILURE_DANGER_PAIRS_V132 = {
    tuple(sorted(("lesley", "ixia"))),
    tuple(sorted(("yin", "valir"))),
    tuple(sorted(("x_borg", "benedetta"))),
    tuple(sorted(("floryn", "odette"))),
    tuple(sorted(("beatrix", "cici"))),
}


def normalize_hero_id(hero_id: str | None) -> str | None:
    if not hero_id:
        return None
    return (
        hero_id.strip()
        .lower()
        .replace(" ", "_")
        .replace(".", "_")
        .replace("-", "_")
        .replace("’", "")
        .replace("'", "")
    )


def is_failure_danger_pair(hero_a: str | None, hero_b: str | None) -> bool:
    a = normalize_hero_id(hero_a)
    b = normalize_hero_id(hero_b)
    if not a or not b:
        return False
    return tuple(sorted((a, b))) in FAILURE_DANGER_PAIRS_V132


def should_block_top_promotion(reference_match: dict | None, dictionary_fallback: dict | None) -> bool:
    """
    Returns True when top_candidate must be blocked.

    Rule:
    - Missing / weak / ambiguous reference match blocks Top promotion.
    - Dictionary fallback never becomes Top when reference is not strong.
    - Known failure danger pairs require strong reference to allow Top.
    """
    if not reference_match:
        return True

    ref_status = reference_match.get("status")
    ref_hero = normalize_hero_id(reference_match.get("hero_id") or reference_match.get("hero"))

    dict_hero = None
    if dictionary_fallback:
        dict_hero = normalize_hero_id(dictionary_fallback.get("hero_id") or dictionary_fallback.get("hero"))

    if ref_status != "strong":
        return True

    if dict_hero and is_failure_danger_pair(ref_hero, dict_hero) and ref_status != "strong":
        return True

    return False


def apply_safe_match_gate(slot_result: dict) -> dict:
    reference_match = slot_result.get("reference_match")
    dictionary_fallback = slot_result.get("dictionary_fallback")

    blocked = should_block_top_promotion(reference_match, dictionary_fallback)

    if blocked:
        near_candidates = []

        if reference_match:
            if reference_match.get("hero_id") or reference_match.get("hero"):
                near_candidates.append({
                    "hero_id": normalize_hero_id(reference_match.get("hero_id") or reference_match.get("hero")),
                    "source": "reference_result_icons",
                    "top_promotion_allowed": False,
                })
            near_candidates.extend(reference_match.get("near_candidates", []))

        if dictionary_fallback:
            if dictionary_fallback.get("hero_id") or dictionary_fallback.get("hero"):
                near_candidates.append({
                    "hero_id": normalize_hero_id(dictionary_fallback.get("hero_id") or dictionary_fallback.get("hero")),
                    "source": "hero_dictionary_fallback",
                    "top_promotion_allowed": False,
                })
            near_candidates.extend(dictionary_fallback.get("candidates", []))

        return {
            **slot_result,
            "top_candidate": None,
            "near_candidates": near_candidates,
            "safe_gate_status": "BLOCK_FALLBACK_TOP_PROMOTION",
            "confirmation_status": "確認待ち",
            "hero_lock_allowed": False,
            "audit_note": "reference_result_icons の一致が弱い、または辞書fallbackと衝突したためTop候補昇格を禁止しました。",
        }

    return {
        **slot_result,
        "top_candidate": reference_match,
        "near_candidates": reference_match.get("near_candidates", []) if reference_match else [],
        "safe_gate_status": "PASS_REFERENCE_STRONG",
        "confirmation_status": "確認待ち",
        "hero_lock_allowed": False,
    }

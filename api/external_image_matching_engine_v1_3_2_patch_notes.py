"""
External API Integration Notes for v1.3.2 Safe Match Gate

In external_image_matching_engine.py:

1. Import:

    from api.safe_match_gate import apply_safe_match_gate

2. After `_match_reference(...)` returns candidates, convert candidates to dicts:

    candidate_dicts = [c.model_dump() for c in candidates]

3. Apply gate:

    gate = apply_safe_match_gate(
        candidates=candidate_dicts,
        crop_confidence=confidence,
        reference_icon_count=count,
    )

4. Add fields to SlotReport:

    match_status: Literal["strong", "ambiguous", "weak", "unregistered"]
    top_candidate_allowed: bool
    safe_gate_flags: List[str]

5. GPT behavior:
    - strong: display rank1 candidate + near candidates
    - ambiguous: display rank1 and near candidates with caution
    - weak: display 未確認 + near candidates
    - unregistered: display 未確認
"""

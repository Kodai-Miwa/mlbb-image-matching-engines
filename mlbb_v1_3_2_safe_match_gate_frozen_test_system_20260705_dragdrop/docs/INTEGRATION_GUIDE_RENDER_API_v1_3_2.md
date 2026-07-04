# Render API Integration Guide - v1.3.2 Safe Match Gate Failure Add-on

Target repository layout matches the existing MLBB External Image Matching Action Pack:

```text
api/
openapi/
patches/
examples/
Dockerfile
README.md
manifest.json
requirements.txt
```

## Files added by this drag-and-drop update

```text
api/safe_match_gate_failure_pair_patch.py
api/data/safe_match_gate_danger_pairs_v132.json
tests/test_safe_match_gate_failure_pair_patch.py
examples/failure_cases/FE-HERO-V132-20260705-0001.json
assets/images/F245AEFC-C7DF-4990-B858-2AD41F7FF6C5.jpeg
patches/CHANGELOG_v1_3_2_failure_addon.md
patches/README_v1_3_2_safe_match_gate_failure_addon.md
```

## Required code hook

In the existing candidate selection / safe match gate pipeline, import:

```python
from api.safe_match_gate_failure_pair_patch import should_block_top_promotion
```

Then apply it before any dictionary fallback can become `top_candidate`:

```python
blocked = should_block_top_promotion(reference_match, dictionary_fallback)

if blocked:
    return {
        **slot_result,
        "top_candidate": None,
        "near_candidates": build_near_candidates(reference_match, dictionary_fallback),
        "safe_gate_status": "BLOCK_FALLBACK_TOP_PROMOTION",
        "confirmation_status": "確認待ち",
        "hero_lock_allowed": False,
        "audit_note": "reference_result_icons の一致が弱い、または辞書fallbackと衝突したためTop候補昇格を禁止しました。",
    }
```

## Added failure danger pairs

```text
Lesley / Ixia
Yin / Valir
X.Borg / Benedetta
Floryn / Odette
Beatrix / Cici
```

## Expected policy

- If `reference_match.status != "strong"`, Top candidate promotion is blocked.
- Hero Dictionary fallback remains `near_candidates` only.
- Hero Lock remains forbidden until user confirmation.
- The UI should show `確認待ち`.

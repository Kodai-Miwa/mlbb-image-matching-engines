# MLBB v1.3.2 Safe Match Gate Patch

Status: patch_candidate  
Date: 2026-07-05  
Patch ID: HR-RESULT-MATCH-GATE-V1.3.2-20260705

## Purpose

v1.3.2 adds a **Safe Match Gate** between reference-result-icon matching and GPT candidate display.

The goal is to reduce wrong confident hero candidates when:

- reference coverage is weak
- crop confidence is low
- top candidates are too close
- dictionary fallback tries to overrule image match
- a danger-pair group is involved

## Core change

The API must return a `match_status` for every slot.

```text
strong       -> show top candidate, still confirmation required
ambiguous    -> show multiple candidates, confirmation required
weak         -> output 未確認
unregistered -> output 未確認
```

## Authority rule

```text
External reference_result_icons match = primary evidence
Hero Dictionary = secondary support only
Weak image match must not be replaced by semantic dictionary guess
```

## Pipeline

```text
result screen
↓
player-row search scope
↓
icon-center anchored crop
↓
125x125 normalized icon
↓
flag/level mask
↓
reference_result_icons comparison
↓
Safe Match Gate
↓
match_status + top/near candidates
↓
GPT candidate UI
↓
user confirmation
```

## Files

```text
api/safe_match_gate.py
api/external_image_matching_engine_v1_3_2_patch_notes.py
openapi/mlbb_image_matching_engine_openapi_v1_3_2_safe_match_gate.yaml
docs/11_CUSTOM_GPT_INSTRUCTIONS_V1_3_2_SAFE_MATCH_GATE_PATCH.md
docs/20_IMAGE_MATCHING_ACCURACY_ENGINE_V1_3_2_SAFE_MATCH_GATE_PATCH.md
tests/FE-HERO-V131-20260705-0001_REGRESSION.json
profiles/HR-RESULT-MATCH-GATE-V1.3.2.md
manifest.json
```

## Important

This patch is designed to be integrated into the current v1.3.1 API.

It does not remove candidate-only behavior.

```json
{
  "hero_lock_allowed": false,
  "user_confirmation_required": true
}
```

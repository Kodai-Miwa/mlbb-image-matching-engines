# Unit 20 Patch
## V1.3.2 Safe Match Gate

Add to `20_IMAGE_MATCHING_ACCURACY_ENGINE_20260704.md`.

## Purpose

The engine must not force a hero name when reference_result_icon evidence is weak.

## New Gate

```text
reference_result_icons comparison
↓
Safe Match Gate
↓
strong / ambiguous / weak / unregistered
```

## GPT Interpretation

```text
strong       -> candidate display + confirmation
ambiguous    -> multi-candidate display + confirmation
weak         -> 未確認
unregistered -> 未確認
```

## No Dictionary Rescue

Hero Dictionary cannot convert `weak` or `unregistered` into a top candidate.

## Regression

Add `FE-HERO-V131-20260705-0001` as a required regression case.

Expected:
- Correct hero if reference is strong
- Otherwise 未確認
- Never wrong confident semantic top candidate

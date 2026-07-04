# HR-RESULT-MATCH-GATE-V1.3.2
## Safe Match Gate

Status: Patch Candidate  
Date: 2026-07-05

## Purpose

Prevent wrong confident hero candidate output when image match evidence is weak.

## Match Status

| Status | Meaning | GPT Output |
|---|---|---|
| strong | top score and margin are strong | show top candidate, confirmation required |
| ambiguous | candidates are close or danger pair found | show multiple candidates, confirmation required |
| weak | top score weak or crop confidence low | show 未確認, near candidates optional |
| unregistered | no usable reference match | show 未確認 |

## Thresholds

Initial recommended values:

```json
{
  "strong_score_min": 0.84,
  "weak_score_max": 0.72,
  "strong_margin_min": 0.055,
  "ambiguous_margin_max": 0.055
}
```

These are calibration values and should be adjusted after test batches.

## Dictionary Fallback Rule

Hero Dictionary must not promote a weak match into a specific top hero candidate.

```text
weak / unregistered
↓
未確認
```

not:

```text
weak / unregistered
↓
semantic dictionary guess
```

## Regression Requirement

FE-HERO-V131-20260705-0001 must be tested after this patch.

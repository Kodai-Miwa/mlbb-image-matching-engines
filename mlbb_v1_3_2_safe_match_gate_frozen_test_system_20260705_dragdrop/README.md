# MLBB v1.3.2 Safe Match Gate Frozen Test System

Status: frozen for test + Safe Match Gate v1.3.2  
Date: 2026-07-05

This package keeps the v1.3 frozen reference-result-icon registry format and adds v1.3.2 Safe Match Gate so the external Python API can:

1. crop 10 hero icons from a MLBB result screen using `HR-RESULT-SCREEN-PARTITION-V1.3`;
2. normalize every crop to 125x125;
3. mask flag and level regions;
4. compare each crop with registered `reference_result_icons`;
5. return candidate hero IDs;
6. mark weak/ambiguous reference matches with `safe_gate_status`;
7. block Top promotion when reference strength is insufficient;
8. keep `hero_lock_allowed=false`.

## Current registry

- Reference entries: **55**
- Unique heroes: **40**
- Safe Match Gate failure cases: **1**
- Safe Match Gate danger pairs: **5**

## Files

```text
api/external_image_matching_engine.py
api/requirements.txt
Dockerfile
openapi/mlbb_image_matching_engine_openapi_v1_3_2_safe_match_gate.yaml
reference_result_icons/
reference_manifest.json
profiles/HR-RESULT-SCREEN-PARTITION-V1.3.md
docs/11_CUSTOM_GPT_INSTRUCTIONS_V1_3_FROZEN_TEST_PATCH.md
api/safe_match_gate_failure_pair_patch.py
api/data/safe_match_gate_danger_pairs_v132.json
docs/failure_cases/FE-HERO-V132-20260705-0001.json
docs/README_v1_3_2_safe_match_gate.md
docs/CHANGELOG_v1_3_2_safe_match_gate.md
```

## Render deployment

Replace your existing repo files with this package contents, commit, and redeploy.

After deployment, check:

```text
/health
/privacy
/docs
```

## GPT Action

Use the OpenAPI schema in:

```text
openapi/mlbb_image_matching_engine_openapi_v1_3_2_safe_match_gate.yaml
```

Set the server URL to your Render URL if needed.

## Test rule

During test mode, do not add more reference icons unless you are intentionally updating `reference_result_icons/` and `reference_manifest.json`. v1.3.2 Safe Match Gate updates should stay in the existing folder format: `api/`, `openapi/`, `docs/`, `tests/`, `profiles/`, and `reference_result_icons/`.

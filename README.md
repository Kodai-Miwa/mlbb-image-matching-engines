# MLBB v1.3 Frozen Test System

Status: frozen for test  
Date: 2026-07-04

This package freezes the current reference-result-icon registry and updates the external Python API so it can:

1. crop 10 hero icons from a MLBB result screen using `HR-RESULT-SCREEN-PARTITION-V1.3`;
2. normalize every crop to 125x125;
3. mask flag and level regions;
4. compare each crop with registered `reference_result_icons`;
5. return Top candidates as hero IDs;
6. keep `hero_lock_allowed=false`.

## Current registry

- Reference entries: **55**
- Unique heroes: **40**

## Files

```text
api/external_image_matching_engine.py
api/requirements.txt
Dockerfile
openapi/mlbb_image_matching_engine_openapi_v1_3_frozen.yaml
reference_result_icons/
reference_manifest.json
profiles/HR-RESULT-SCREEN-PARTITION-V1.3.md
docs/11_CUSTOM_GPT_INSTRUCTIONS_V1_3_FROZEN_TEST_PATCH.md
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
openapi/mlbb_image_matching_engine_openapi_v1_3_frozen.yaml
```

Set the server URL to your Render URL if needed.

## Test rule

During test mode, do not add more reference icons. New screenshots should be used only for evaluation until the freeze is lifted.

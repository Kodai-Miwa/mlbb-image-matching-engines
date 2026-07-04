# MLBB V1.3.1 Icon-Center Anchor Engine Patch

This package updates the external Python API from fixed-x row clipping to **icon-center anchored clipping**.

## Core pipeline

```text
Result screen
↓
Player row partition
↓
Search hero icon zone inside each row
↓
Detect hero icon circle center
↓
Crop 80x80 around center
↓
Normalize to 125x125
↓
Mask flag/level region
↓
Compare against reference_result_icons
↓
Return Top-K hero_id candidates
```

## Important rule

The API returns candidates only.

```json
"hero_lock_allowed": false
```

GPT/NexusOS must still ask user confirmation before Hero/Role Lock.

## Files

```text
api/external_image_matching_engine.py
api/requirements.txt
Dockerfile
openapi/mlbb_image_matching_engine_openapi_v1_3_1_icon_center_anchor.yaml
profiles/HR-RESULT-SCREEN-PARTITION-V1.3.1.md
reference_result_icons/
reference_manifest.json
docs/
```

## Deploy

Replace the GitHub repository contents with these files, commit, and redeploy on Render.

After deploy:

```text
/health
/docs
/privacy
```

`/health` should show:

```json
{
  "status": "ok",
  "version": "v1.3.1-icon-center-anchor-20260705",
  "profile_id": "HR-RESULT-SCREEN-PARTITION-V1.3.1"
}
```

## Note

This patch contains a template `reference_manifest.json`.
To use the currently frozen 55 official references, copy your official `reference_result_icons/` folders and manifest into this package before deploying.

# API folder rebuild v1.3.2

Purpose:
- Keep the existing v1.3.2 Safe Match Gate behavior.
- Fix image input handling for Custom GPT Action preview.
- Detect truncated placeholder base64 such as `/9j/....`.
- Accept optional `image_url` when `image_base64` is not provided.
- Keep `reference_result_icons/` outside normal update ZIPs.

Drag and drop:
- Copy this `api/` folder over the GitHub repository root.
- Do not replace `reference_result_icons/` unless a reference-icon update package is being applied.

Main file:
- `api/external_image_matching_engine.py`

Expected health version:
- `v1.3.2-safe-match-gate-20260705-api-input-fix`

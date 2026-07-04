# OpenAPI Fixed

This fixes the GPT Actions error:

`components section, schemas subsection is not an object`

Cause:
The previous YAML used compact inline YAML object syntax in several places. Some validators parse those incorrectly or reject them in OpenAPI Actions import.

Fix:
- `components.schemas` is now an explicit mapping object.
- All reusable schemas are placed under `components.schemas`.
- Responses reference schemas with `$ref`.
- Added `HealthResponse`, `AnalyzeRequest`, `AnalyzeResponse`, `SlotReport`, `MatchCandidate`, and `CropDebug`.

Use:
`mlbb_image_matching_engine_openapi_v1_3_2_safe_match_gate_FIXED.yaml`

# HR-RESULT-SCREEN-PARTITION-V1.3.1
## Player-row partition + icon-center anchored clipping

Last updated: 2026-07-05

## Purpose
This profile replaces the older fixed-x crop approach with an **icon-center anchored clipping** workflow.
The goal is to eliminate left/right margin inconsistency in result-screen hero crops.

## Problem in V1.3
In the previous method, crops were derived mainly from player-row partitions with fixed horizontal offsets.
That caused:
- excess left margin on some ally crops
- excess right-side UI intrusion on some enemy crops
- inconsistent hero-face centering
- unstable comparison quality for external icon matching

## V1.3.1 Core Improvement
### Old
- detect player row
- apply fixed x/y crop window
- normalize to target size

### New
- detect player row
- detect circular hero icon inside the row
- estimate icon center `(cx, cy)`
- crop a square around the icon center
- normalize the square crop to standard size

## Official Crop Rule
### Source anchor
- anchor type: `hero_icon_circle_center`
- anchor coordinates: `(cx, cy)` from detected hero icon circle

### Source crop
- source crop size: `80 x 80 px`
- crop box:
  - `x1 = cx - 40`
  - `y1 = cy - 40`
  - `x2 = cx + 40`
  - `y2 = cy + 40`

### Normalized output
- output size: `125 x 125 px`

## Row Partition Rule
Use row partitioning only to narrow search scope for the hero icon.

### Recommended row workflow
1. detect result screen side: ally / enemy
2. detect player-row bands
3. inside each row, search only the hero-icon zone
4. detect the circular icon boundary
5. compute center `(cx, cy)`
6. perform center-anchored crop
7. normalize to `125 x 125`

## Detection Priority
### Priority 1
Detect the circular hero icon boundary.

### Priority 2
If the full circle edge is weak, estimate center from:
- outer circular frame
- face mass center
- border color ring

### Priority 3 fallback
If no circle can be confidently detected:
- fall back to row-based approximate icon zone
- then apply local refinement
- if still unstable, mark crop as `low_confidence`

## Confidence Policy
Return a crop confidence field:
- `high`: clear circle / stable center
- `medium`: partial circle, center estimated reliably
- `low`: fallback crop used

## Standard Output Schema
```json
{
  "profile_version": "v1.3.1",
  "crop_method": "icon_center_anchor",
  "anchor_type": "hero_icon_circle_center",
  "source_crop_size": [80, 80],
  "normalized_clip_size": [125, 125],
  "confidence": "high|medium|low"
}
```

## Why This Is Better
This profile fixes:
- unequal left/right padding
- drifting icon positions between ally and enemy sides
- unstable direct image matching

It improves:
- reference registration consistency
- external Python icon matching reliability
- cross-match similarity scoring

## Registration Rule Going Forward
All newly registered result-screen icon references should use:
- `HR-RESULT-SCREEN-PARTITION-V1.3.1`
- `icon_center_anchor`
- normalized size `125 x 125`

Older V1.3 crops should be considered legacy unless migrated.

## Recommended Migration
For previously registered icons:
1. reload original result screen
2. re-crop each icon using detected circle center
3. regenerate normalized 125x125 references
4. replace older legacy references where possible

## Operational Note
Partitioning is still useful, but **partition is not the final crop anchor**.
The final crop anchor must be the icon center.

That is the key correction introduced in V1.3.1.

# HR-RESULT-SCREEN-PARTITION-V1.3

Status: Frozen for test
Date: 2026-07-04

## Purpose

Result-screen native player-row partition clipping for MLBB result screens.

The engine does not use hero-list source images as the primary reference. It uses confirmed result-screen icon crops.

## Fixed clipping profile

```json
{
  "base_image_size": [
    1536,
    710
  ],
  "row_bounds_y": [
    [
      150,
      239
    ],
    [
      239,
      329
    ],
    [
      329,
      420
    ],
    [
      420,
      511
    ],
    [
      511,
      601
    ]
  ],
  "source_crop_size": [
    80,
    80
  ],
  "normalized_clip_size": [
    125,
    125
  ],
  "left_team_crop_x": [
    202,
    282
  ],
  "right_team_crop_x": [
    1250,
    1330
  ],
  "mask_policy": "union_flag_and_level_mask_for_left_right_refs",
  "ignore_regions_125": [
    {
      "name": "left_flag",
      "box": [
        0,
        0,
        48,
        46
      ]
    },
    {
      "name": "right_flag",
      "box": [
        77,
        0,
        125,
        46
      ]
    },
    {
      "name": "left_level",
      "box": [
        0,
        88,
        54,
        125
      ]
    },
    {
      "name": "right_level",
      "box": [
        71,
        88,
        125,
        125
      ]
    }
  ]
}
```

## Frozen test registry

- Registered reference entries: 55
- Unique heroes: 40

## Safety

API candidate output is support data only. It must not perform Hero Lock. GPT/NexusOS must keep candidate-only UI until user confirmation.

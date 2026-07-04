# CHANGELOG v1.3.2 Safe Match Gate Failure Add-on

## 2026-07-05

Added regression failure seed:

- FE-HERO-V132-20260705-0001

Purpose:

- Prevent wrong Top candidates when reference_result_icons match is weak.
- Block Hero Dictionary fallback promotion for newly observed failure pairs.

Pairs added:

- Lesley / Ixia
- Yin / Valir
- X.Borg / Benedetta
- Floryn / Odette
- Beatrix / Cici

Expected result after patch:

- weak/conflict slots output top_candidate = null
- true and failed candidates remain near_candidates
- status remains 確認待ち
- Hero Lock remains forbidden until user confirmation

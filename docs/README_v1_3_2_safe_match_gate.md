# MLBB NexusOS v1.3.2 Safe Match Gate Failure Add-on

## Added case

`FE-HERO-V132-20260705-0001`

Correct labels:

Ally:
1. Lesley / ラズリー
2. Yin / 寅
3. Nana / ナナ
4. Akai / ガイ
5. X.Borg / エックス

Enemy:
1. Floryn / フローラ
2. Beatrix / ベアトリクス
3. Sun / 悟空
4. Paquito / パキート
5. Chang’e / チェン

## Observed failed AI output

Ally:
Ixia / Valir / Nana / Akai / Benedetta

Enemy:
Odette / Cici / Sun / Paquito / Chang’e

Accuracy: 5/10

## Added v1.3.2 failure danger pairs

- Lesley ↔ Ixia
- Yin ↔ Valir
- X.Borg ↔ Benedetta
- Floryn ↔ Odette
- Beatrix ↔ Cici

## Required behavior

When reference_result_icons match is weak, ambiguous, missing, or conflicts with dictionary fallback:

- Do not promote dictionary fallback to Top candidate.
- Keep fallback only in near_candidates / audit_note.
- Set confirmation_status to 確認待ち.
- Keep hero_lock_allowed false.

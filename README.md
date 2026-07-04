# MLBB External Image Matching Action Pack 20260704

このパッケージは、NexusOS v1.2 の画像照合を Custom GPT Actions / 外部APIで安定化するための実装セットです。

## 含まれるもの

```text
api/external_image_matching_engine.py
api/requirements.txt
openapi/mlbb_image_matching_engine_openapi_20260704.yaml
patches/11_CUSTOM_GPT_INSTRUCTIONS_ACTION_PATCH_20260704.md
Dockerfile
examples/request_example.json
examples/response_example.json
```

## 役割

- FastAPI: 画像を受け取り、10個のアイコン領域に対して Feature-Zero 輪郭検査を行う
- OpenAPI schema: Custom GPT Actions に登録する
- Instructions patch: 新規チャットでも必ず外部Actionを起動するための強化文

## 注意

このAPIはヒーロー名を確定しません。返すのは以下のような検査証拠です。

- normal crop / wide crop
- silhouette_symmetry
- mass_gravity
- contour_sharpness
- top_projection / side_projection
- crop disagreement flags

Hero候補化・危険ペア監査・ユーザー確認はNexusOS側で行います。

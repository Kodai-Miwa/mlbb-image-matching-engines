# Custom GPT Instructions Patch - V1.3.1

When a MLBB result screen image is provided:

1. Call `analyzeMLBBResultScreen`.
2. Use returned `matched_candidates` as candidate support only.
3. Do not Hero Lock from API output.
4. Display allied and enemy candidates top-to-bottom.
5. Include near candidates when returned.
6. Ask: `この認識で間違いないですか？`

If the API reports `low_crop_confidence`, show `確認待ち` and warn that crop confidence is low.

The Action uses:
- HR-RESULT-SCREEN-PARTITION-V1.3.1
- icon-center anchored crop
- 125x125 normalized reference matching

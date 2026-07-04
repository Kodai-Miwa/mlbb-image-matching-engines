import base64, json, requests, sys

API_URL = "https://mlbb-image-matching-engines.onrender.com/v1/mlbb/image-match/analyze"
API_KEY = "PUT_YOUR_KEY_HERE"

image_path = sys.argv[1]
with open(image_path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode("ascii")

payload = {
    "image_base64": b64,
    "screen_type": "result_screen",
    "slot_profile": "result_screen_partition_v1_3",
    "top_k": 5
}
headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}
r = requests.post(API_URL, headers=headers, json=payload, timeout=60)
print(r.status_code)
print(json.dumps(r.json(), ensure_ascii=False, indent=2))

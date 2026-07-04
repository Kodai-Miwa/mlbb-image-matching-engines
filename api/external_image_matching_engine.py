"""
MLBB External Image Matching Engine
Version: v1.3.1-icon-center-anchor-20260705

Purpose:
- FastAPI service for Custom GPT Actions.
- Receives a MLBB result screen image as base64.
- Detects 10 player rows.
- Searches each row for hero icon circles.
- Crops each hero icon around the detected circle center.
- Normalizes to 125x125.
- Masks flag/level areas depending on side.
- Compares against reference_result_icons.
- Returns candidate hero IDs only.
- DOES NOT lock or finalize hero identity.

Environment:
    MLBB_IMAGE_MATCHING_API_KEY=your-secret-key
"""

from __future__ import annotations

import base64
import io
import json
import math
import os
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

import numpy as np
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from PIL import Image, ImageFilter, ImageOps


ENGINE_NAME = "mlbb_external_image_matching_engine"
ENGINE_VERSION = "v1.3.1-icon-center-anchor-20260705"
PROFILE_ID = "HR-RESULT-SCREEN-PARTITION-V1.3.1"

BASE_DIR = Path(__file__).resolve().parent.parent
REFERENCE_DIR = BASE_DIR / "reference_result_icons"
MANIFEST_PATH = BASE_DIR / "reference_manifest.json"

NORMALIZED_SIZE = (125, 125)
SOURCE_CROP_SIZE = 80

# Reference profile is calibrated from 1536x710 screenshots.
BASE_SCREEN_SIZE = (1536, 710)

# Row bands are used only as search scopes.
BASE_ROW_BOUNDS_Y = [
    (150, 239),
    (239, 329),
    (329, 420),
    (420, 511),
    (511, 601),
]

# Approximate icon search zones per side in the 1536x710 base coordinate system.
# The final crop is NOT based on these fixed x values; these only constrain circle search.
BASE_SEARCH_ZONES = {
    "ally": (170, 285),
    "enemy": (1240, 1360),
}

# Normalized 125x125 mask regions after center-anchored crop.
MASKS_125 = {
    "ally": {
        "flag_ignore_region_safe": [0, 0, 48, 46],
        "level_ignore_region_safe": [0, 88, 54, 125],
    },
    "enemy": {
        "flag_ignore_region_safe": [77, 0, 125, 46],
        "level_ignore_region_safe": [71, 88, 125, 125],
    },
}


app = FastAPI(
    title="MLBB External Image Matching Engine",
    version=ENGINE_VERSION,
    description=(
        "V1.3.1 icon-center anchored result-screen image matching engine. "
        "Returns hero candidate IDs only. Hero Lock is never allowed."
    ),
)


class HealthResponse(BaseModel):
    status: str
    engine: str
    version: str
    profile_id: str
    reference_icon_count: int
    unique_hero_count: int


class AnalyzeRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded screenshot image. Data URL prefix is allowed.")
    screen_type: Literal["result_screen"] = "result_screen"
    top_k: int = Field(5, ge=1, le=10)
    return_debug_samples: bool = False


class MatchCandidate(BaseModel):
    hero_id: str
    display_name: Optional[str] = None
    reference_id: str
    rank: int
    score: float
    distance: float
    source: str


class CropDebug(BaseModel):
    side: Literal["ally", "enemy"]
    row_index: int
    crop_method: str
    confidence: Literal["high", "medium", "low"]
    anchor_center: List[int]
    source_crop_box: List[int]
    normalized_size: List[int]
    mask_regions: Dict[str, List[int]]
    detection_notes: List[str]


class SlotReport(BaseModel):
    slot: str
    side: Literal["ally", "enemy"]
    row_index: int
    hero_lock_allowed: bool = False
    crop_debug: CropDebug
    matched_candidates: List[MatchCandidate]
    risk_flags: List[str]
    notes: List[str]


class AnalyzeResponse(BaseModel):
    engine: str
    version: str
    profile_id: str
    screen_type: str
    hero_lock_allowed: bool = False
    rule: str = "candidate_only_until_user_confirmation"
    reference_icon_count: int
    unique_hero_count: int
    slots: List[SlotReport]


def _check_api_key(x_api_key: Optional[str]) -> None:
    required = os.getenv("MLBB_IMAGE_MATCHING_API_KEY")
    if not required:
        return
    if not x_api_key or x_api_key != required:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


def _decode_image_base64(image_base64: str) -> Image.Image:
    raw = image_base64.strip()
    if "," in raw and raw.lower().startswith("data:"):
        raw = raw.split(",", 1)[1]
    try:
        data = base64.b64decode(raw, validate=False)
        return Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image: {exc}") from exc


def _scale_box(box: Tuple[int, int, int, int], img_size: Tuple[int, int]) -> Tuple[int, int, int, int]:
    bw, bh = BASE_SCREEN_SIZE
    w, h = img_size
    sx, sy = w / bw, h / bh
    x1, y1, x2, y2 = box
    return (
        int(round(x1 * sx)),
        int(round(y1 * sy)),
        int(round(x2 * sx)),
        int(round(y2 * sy)),
    )


def _safe_crop_box(cx: int, cy: int, size: int, img_size: Tuple[int, int]) -> Tuple[int, int, int, int]:
    half = size // 2
    w, h = img_size
    x1 = max(0, cx - half)
    y1 = max(0, cy - half)
    x2 = min(w, cx + half)
    y2 = min(h, cy + half)

    # Preserve square size where possible by shifting back inside bounds.
    if x2 - x1 < size:
        if x1 == 0:
            x2 = min(w, size)
        elif x2 == w:
            x1 = max(0, w - size)
    if y2 - y1 < size:
        if y1 == 0:
            y2 = min(h, size)
        elif y2 == h:
            y1 = max(0, h - size)
    return x1, y1, x2, y2


def _preprocess_search_region(region: Image.Image) -> np.ndarray:
    gray = np.asarray(ImageOps.grayscale(region)).astype(np.uint8)
    # Edge-ish signal without cv2 dependency: local contrast via simple gradients.
    gy = np.abs(np.diff(gray.astype(np.int16), axis=0, prepend=gray[:1].astype(np.int16)))
    gx = np.abs(np.diff(gray.astype(np.int16), axis=1, prepend=gray[:, :1].astype(np.int16)))
    edge = np.clip(gx + gy, 0, 255).astype(np.uint8)
    return edge


def _estimate_circle_center_by_border(region: Image.Image, side: str) -> Tuple[int, int, str, List[str]]:
    """
    Lightweight circle center estimate.
    Avoids heavy Hough dependency. It estimates the hero circle center from:
    - saturated/bright border energy
    - foreground mass around the expected icon area
    - fallback geometric center of the search zone
    """
    notes: List[str] = []
    rgb = np.asarray(region.convert("RGB")).astype(np.float32)
    h, w, _ = rgb.shape

    gray = np.asarray(ImageOps.grayscale(region)).astype(np.float32)
    edge = _preprocess_search_region(region).astype(np.float32)

    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    sat = maxc - minc

    # Circle/border signal: edges plus saturation and brightness transitions.
    signal = edge * 0.55 + sat * 0.30 + np.abs(gray - np.median(gray)) * 0.15
    threshold = np.percentile(signal, 78)
    mask = signal >= threshold

    # Ignore extreme row borders.
    mask[:3, :] = False
    mask[-3:, :] = False

    ys, xs = np.where(mask)
    if len(xs) < 20:
        notes.append("fallback: weak circle signal")
        return w // 2, h // 2, "low", notes

    # Restrict to plausible icon area inside search zone.
    # Center should usually be near the middle of the row.
    # Robust median reduces text/item interference.
    cx = int(np.median(xs))
    cy = int(np.median(ys))

    # Refine: use mass center around a local window.
    local_radius = max(12, min(w, h) // 3)
    yy, xx = np.ogrid[:h, :w]
    local = ((xx - cx) ** 2 + (yy - cy) ** 2) <= local_radius ** 2
    refined_mask = mask & local
    rys, rxs = np.where(refined_mask)
    if len(rxs) >= 20:
        cx = int(np.mean(rxs))
        cy = int(np.mean(rys))
        confidence = "medium"
        notes.append("center estimated from local border/edge mass")
    else:
        confidence = "low"
        notes.append("center estimated from broad border/edge median")

    # Practical correction: hero circle is usually near row vertical center.
    # Blend detected cy with search region center to avoid item/text interference.
    cy = int(round(cy * 0.55 + (h // 2) * 0.45))

    if 0.30 * w < cx < 0.70 * w:
        confidence = "high" if confidence == "medium" else confidence
        notes.append("center inside expected search zone")
    else:
        notes.append("center outside ideal zone, retained with caution")
        confidence = "low"

    return cx, cy, confidence, notes


def _detect_icon_center(img: Image.Image, side: str, row_idx: int) -> Tuple[int, int, str, List[str]]:
    row_y1, row_y2 = BASE_ROW_BOUNDS_Y[row_idx]
    search_x1, search_x2 = BASE_SEARCH_ZONES[side]

    x1, y1, x2, y2 = _scale_box((search_x1, row_y1, search_x2, row_y2), img.size)
    region = img.crop((x1, y1, x2, y2))

    local_cx, local_cy, confidence, notes = _estimate_circle_center_by_border(region, side)
    cx = x1 + local_cx
    cy = y1 + local_cy
    notes.append(f"search_box={[x1, y1, x2, y2]}")
    return cx, cy, confidence, notes


def _normalize_crop(img: Image.Image, crop_box: Tuple[int, int, int, int]) -> Image.Image:
    crop = img.crop(crop_box)
    crop = ImageOps.autocontrast(crop)
    crop = crop.filter(ImageFilter.UnsharpMask(radius=1.0, percent=140, threshold=3))
    return crop.resize(NORMALIZED_SIZE, Image.Resampling.LANCZOS)


def _apply_masks_array(arr: np.ndarray, side: str) -> np.ndarray:
    out = arr.copy()
    for box in MASKS_125[side].values():
        x1, y1, x2, y2 = box
        out[y1:y2, x1:x2] = 0
    return out


def _image_feature_vector(img: Image.Image, side: str) -> np.ndarray:
    arr = np.asarray(img.convert("RGB")).astype(np.float32) / 255.0

    # Apply side-specific flag/level mask.
    arr = _apply_masks_array(arr, side)

    # Color histogram.
    hist_parts = []
    for c in range(3):
        vals = arr[:, :, c].flatten()
        hist, _ = np.histogram(vals, bins=24, range=(0.0, 1.0))
        hist_parts.append(hist.astype(np.float32))

    gray = np.asarray(ImageOps.grayscale(img)).astype(np.float32) / 255.0
    gray = _apply_masks_array(gray[:, :, None], side)[:, :, 0]

    # Simple edge profile.
    gx = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    gy = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
    edge = gx + gy
    edge_hist, _ = np.histogram(edge.flatten(), bins=24, range=(0.0, 1.0))
    hist_parts.append(edge_hist.astype(np.float32))

    # Low-res perceptual vector.
    small = Image.fromarray((gray * 255).astype(np.uint8)).resize((16, 16), Image.Resampling.BILINEAR)
    small_arr = np.asarray(small).astype(np.float32).flatten() / 255.0
    hist_parts.append(small_arr)

    vec = np.concatenate(hist_parts).astype(np.float32)
    norm = np.linalg.norm(vec)
    if norm > 1e-8:
        vec = vec / norm
    return vec


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(1.0 - np.dot(a, b))


def _load_manifest() -> Dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {"references": []}


def _reference_records() -> List[Dict]:
    manifest = _load_manifest()
    refs = manifest.get("references", [])
    # Also support folder-only references if manifest is absent/incomplete.
    if refs:
        return refs

    records: List[Dict] = []
    if not REFERENCE_DIR.exists():
        return records
    for path in sorted(REFERENCE_DIR.rglob("*.png")):
        hero_id = path.parent.name
        records.append({
            "reference_id": path.stem,
            "hero_id": hero_id,
            "display_name": hero_id,
            "path": str(path.relative_to(BASE_DIR)),
            "status": "official",
            "side": "unknown"
        })
    return records


_REFERENCE_CACHE: Optional[List[Tuple[Dict, np.ndarray]]] = None


def _load_reference_cache() -> List[Tuple[Dict, np.ndarray]]:
    global _REFERENCE_CACHE
    if _REFERENCE_CACHE is not None:
        return _REFERENCE_CACHE

    cache: List[Tuple[Dict, np.ndarray]] = []
    for rec in _reference_records():
        rel_path = rec.get("path")
        if not rel_path:
            continue
        path = BASE_DIR / rel_path
        if not path.exists():
            continue
        try:
            img = Image.open(path).convert("RGB").resize(NORMALIZED_SIZE, Image.Resampling.LANCZOS)
            side = rec.get("side")
            if side not in {"ally", "enemy"}:
                # Use ally mask by default for side-unknown references.
                side = "ally"
            vec = _image_feature_vector(img, side)
            cache.append((rec, vec))
        except Exception:
            continue

    _REFERENCE_CACHE = cache
    return cache


def _reference_stats() -> Tuple[int, int]:
    refs = _reference_records()
    heroes = {r.get("hero_id") for r in refs if r.get("hero_id")}
    return len(refs), len(heroes)


def _match_reference(img: Image.Image, side: str, top_k: int) -> List[MatchCandidate]:
    query_vec = _image_feature_vector(img, side)
    scored = []

    for rec, ref_vec in _load_reference_cache():
        dist = _cosine_distance(query_vec, ref_vec)
        # Score is an easy-to-read inverse. Internal use only; GPT may hide it.
        score = max(0.0, 1.0 - dist)
        scored.append((dist, score, rec))

    scored.sort(key=lambda x: x[0])

    results: List[MatchCandidate] = []
    for rank, (dist, score, rec) in enumerate(scored[:top_k], start=1):
        results.append(
            MatchCandidate(
                hero_id=rec.get("hero_id", "unknown"),
                display_name=rec.get("display_name"),
                reference_id=rec.get("reference_id", "unknown_reference"),
                rank=rank,
                score=round(float(score), 6),
                distance=round(float(dist), 6),
                source=rec.get("path", ""),
            )
        )
    return results


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    count, unique = _reference_stats()
    return HealthResponse(
        status="ok",
        engine=ENGINE_NAME,
        version=ENGINE_VERSION,
        profile_id=PROFILE_ID,
        reference_icon_count=count,
        unique_hero_count=unique,
    )


@app.get("/privacy", response_class=HTMLResponse)
def privacy_policy() -> str:
    return """
    <html>
      <head><meta charset="utf-8"><title>Privacy Policy</title></head>
      <body>
        <h1>Privacy Policy</h1>
        <p>Last updated: 2026-07-05</p>
        <h2>Overview</h2>
        <p>MLBB Image Matching Engine processes MLBB result screen images to generate candidate hero ID matches.</p>
        <h2>Data Processed</h2>
        <p>The service may process uploaded result screen images, cropped hero icon regions, contour data, and request metadata required for API operation.</p>
        <h2>Purpose</h2>
        <p>Data is processed only for hero candidate support, crop inspection, and recognition stability. The service does not finalize hero identity.</p>
        <h2>Storage</h2>
        <p>Uploaded images are intended to be processed transiently during the request. The service is designed not to permanently store uploaded gameplay images.</p>
        <h2>Data Sharing</h2>
        <p>We do not sell uploaded images, extracted feature data, or user data.</p>
        <h2>Contact</h2>
        <p>Privacy contact: YOUR_CONTACT_EMAIL_HERE</p>
      </body>
    </html>
    """


@app.post("/v1/mlbb/image-match/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> AnalyzeResponse:
    _check_api_key(x_api_key)
    img = _decode_image_base64(req.image_base64)

    slots: List[SlotReport] = []
    top_k = max(1, min(req.top_k, 10))

    for side in ["ally", "enemy"]:
        for row_idx in range(5):
            cx, cy, confidence, detection_notes = _detect_icon_center(img, side, row_idx)
            crop_box = _safe_crop_box(cx, cy, SOURCE_CROP_SIZE, img.size)
            norm = _normalize_crop(img, crop_box)
            candidates = _match_reference(norm, side, top_k)

            slot_name = f"{side}_{row_idx + 1}"
            risk_flags: List[str] = []
            if confidence == "low":
                risk_flags.append("low_crop_confidence")
            if len(candidates) == 0:
                risk_flags.append("no_reference_candidates")

            slots.append(
                SlotReport(
                    slot=slot_name,
                    side=side,
                    row_index=row_idx + 1,
                    hero_lock_allowed=False,
                    crop_debug=CropDebug(
                        side=side,
                        row_index=row_idx + 1,
                        crop_method="icon_center_anchor",
                        confidence=confidence,
                        anchor_center=[int(cx), int(cy)],
                        source_crop_box=list(map(int, crop_box)),
                        normalized_size=list(NORMALIZED_SIZE),
                        mask_regions=MASKS_125[side],
                        detection_notes=detection_notes,
                    ),
                    matched_candidates=candidates,
                    risk_flags=risk_flags,
                    notes=[
                        "V1.3.1 uses player-row partition only as search scope.",
                        "Final crop anchor is detected hero icon circle center.",
                        "Candidate-only output. Hero Lock is not allowed until user confirmation.",
                    ],
                )
            )

    count, unique = _reference_stats()
    return AnalyzeResponse(
        engine=ENGINE_NAME,
        version=ENGINE_VERSION,
        profile_id=PROFILE_ID,
        screen_type=req.screen_type,
        hero_lock_allowed=False,
        rule="candidate_only_until_user_confirmation",
        reference_icon_count=count,
        unique_hero_count=unique,
        slots=slots,
    )

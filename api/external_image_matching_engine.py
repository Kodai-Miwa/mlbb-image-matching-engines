
"""
MLBB External Image Matching Engine
Version: v1.3-frozen-test-20260704

Purpose:
- FastAPI service for Custom GPT Actions.
- Receives a MLBB result screen image as base64.
- Crops 10 hero icons using HR-RESULT-SCREEN-PARTITION-V1.3.
- Normalizes each crop to 125x125.
- Masks flag/level regions.
- Compares each crop with frozen reference_result_icons.
- Returns Top candidate hero_id list.
- DOES NOT lock or finalize hero identity.

Environment:
    MLBB_IMAGE_MATCHING_API_KEY=your-secret-key
"""

from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

import numpy as np
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from PIL import Image, ImageFilter, ImageOps


ENGINE_NAME = "mlbb_external_image_matching_engine"
ENGINE_VERSION = "v1.3-frozen-test-20260704"
BASE_SIZE = (1536, 710)
NORMALIZED_SIZE = (125, 125)

ROW_BOUNDS_Y = [(150, 239), (239, 329), (329, 420), (420, 511), (511, 601)]
LEFT_TEAM_CROP_X = (202, 282)
RIGHT_TEAM_CROP_X = (1250, 1330)

IGNORE_REGIONS_125 = [
    (0, 0, 48, 46),      # left flag
    (77, 0, 125, 46),    # right flag
    (0, 88, 54, 125),    # left level
    (71, 88, 125, 125),  # right level
]

app = FastAPI(
    title="MLBB External Image Matching Engine",
    version=ENGINE_VERSION,
    description=(
        "v1.3 frozen test engine. Crops MLBB result screen icons and compares them "
        "with frozen result-icon references. Candidate output only; no Hero Lock."
    ),
)


class AnalyzeRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded screenshot image. Data URL prefix is allowed.")
    screen_type: Literal["result_screen"] = "result_screen"
    engine_version: str = "v1.3"
    slot_profile: Literal["result_screen_partition_v1_3", "auto"] = "result_screen_partition_v1_3"
    top_k: int = Field(5, ge=1, le=10)
    return_debug_samples: bool = False


class Candidate(BaseModel):
    hero_id: str
    reference_id: str
    rank: int
    distance: float
    components: Dict[str, float]


class CropBox(BaseModel):
    source_box: List[int]
    normalized_size: List[int]


class SlotResponse(BaseModel):
    slot: str
    team: Literal["ally", "enemy"]
    row_index: int
    crop: CropBox
    matched_candidates: List[Candidate]
    risk_flags: List[str]
    notes: List[str]


class AnalyzeResponse(BaseModel):
    engine: str
    version: str
    screen_type: str
    profile_id: str
    reference_icon_count: int
    unique_hero_count: int
    hero_lock_allowed: bool = False
    rule: str = "candidate_only_until_user_confirmation"
    slots: List[SlotResponse]


class HealthResponse(BaseModel):
    status: str
    engine: str
    version: str
    reference_icon_count: int
    unique_hero_count: int
    profile_id: str


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
    w, h = img_size
    bw, bh = BASE_SIZE
    sx, sy = w / bw, h / bh
    x1, y1, x2, y2 = box
    return (
        int(round(x1 * sx)),
        int(round(y1 * sy)),
        int(round(x2 * sx)),
        int(round(y2 * sy)),
    )


def _slot_boxes(img_size: Tuple[int, int]) -> List[Tuple[str, str, int, Tuple[int, int, int, int]]]:
    slots: List[Tuple[str, str, int, Tuple[int, int, int, int]]] = []
    for i, (y1, y2) in enumerate(ROW_BOUNDS_Y, start=1):
        lx1, lx2 = LEFT_TEAM_CROP_X
        rx1, rx2 = RIGHT_TEAM_CROP_X
        slots.append((f"ally_{i}", "ally", i, _scale_box((lx1, y1, lx2, y2), img_size)))
        slots.append((f"enemy_{i}", "enemy", i, _scale_box((rx1, y1, rx2, y2), img_size)))
    # Output order: allies top-to-bottom, then enemies top-to-bottom.
    allies = [s for s in slots if s[1] == "ally"]
    enemies = [s for s in slots if s[1] == "enemy"]
    return allies + enemies


def _normalize_crop(img: Image.Image, box: Tuple[int, int, int, int]) -> Image.Image:
    crop = img.crop(box).resize(NORMALIZED_SIZE, Image.Resampling.LANCZOS)
    crop = ImageOps.autocontrast(crop)
    crop = crop.filter(ImageFilter.UnsharpMask(radius=1.0, percent=120, threshold=3))
    return crop.convert("RGB")


def _mask_array() -> np.ndarray:
    mask = np.ones((NORMALIZED_SIZE[1], NORMALIZED_SIZE[0]), dtype=bool)
    for x1, y1, x2, y2 in IGNORE_REGIONS_125:
        mask[y1:y2, x1:x2] = False
    return mask


MASK = _mask_array()


def _gray_masked(img: Image.Image) -> np.ndarray:
    gray = np.asarray(ImageOps.grayscale(img.resize(NORMALIZED_SIZE))).astype(np.float32)
    return gray


def _dhash_bits(img: Image.Image, hash_size: int = 8) -> np.ndarray:
    gray = ImageOps.grayscale(img.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS))
    arr = np.asarray(gray, dtype=np.float32)
    return (arr[:, 1:] > arr[:, :-1]).astype(np.uint8).flatten()


def _phash_bits(img: Image.Image, hash_size: int = 8, highfreq_factor: int = 4) -> np.ndarray:
    # Lightweight DCT-free pseudo-pHash: low-resolution mean comparison.
    size = hash_size * highfreq_factor
    gray = ImageOps.grayscale(img.resize((size, size), Image.Resampling.LANCZOS))
    arr = np.asarray(gray, dtype=np.float32)
    small = np.array(Image.fromarray(arr.astype(np.uint8)).resize((hash_size, hash_size), Image.Resampling.BILINEAR), dtype=np.float32)
    med = float(np.median(small))
    return (small > med).astype(np.uint8).flatten()


def _histogram(img: Image.Image, bins: int = 16) -> np.ndarray:
    arr = np.asarray(img.resize(NORMALIZED_SIZE).convert("RGB"), dtype=np.float32)
    pixels = arr[MASK]
    hist_parts = []
    for c in range(3):
        h, _ = np.histogram(pixels[:, c], bins=bins, range=(0, 255), density=False)
        hist_parts.append(h.astype(np.float32))
    hist = np.concatenate(hist_parts)
    denom = np.linalg.norm(hist) + 1e-6
    return hist / denom


def _edge_profile(img: Image.Image) -> np.ndarray:
    gray = _gray_masked(img)
    gx = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    gy = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
    edge = gx + gy
    vals = edge[MASK]
    # 25 quantile bins as compact profile.
    qs = np.quantile(vals, np.linspace(0, 1, 25))
    denom = np.linalg.norm(qs) + 1e-6
    return (qs / denom).astype(np.float32)


def _masked_mse_vector(img: Image.Image) -> np.ndarray:
    arr = np.asarray(img.resize(NORMALIZED_SIZE).convert("RGB"), dtype=np.float32) / 255.0
    return arr[MASK].reshape(-1)


def _hamming(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(a != b))


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(1.0 - (np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-6)))


def _mse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean((a - b) ** 2))


class Reference:
    def __init__(self, hero_id: str, reference_id: str, path: Path):
        self.hero_id = hero_id
        self.reference_id = reference_id
        self.path = path
        self.image = Image.open(path).convert("RGB").resize(NORMALIZED_SIZE, Image.Resampling.LANCZOS)
        self.dhash = _dhash_bits(self.image)
        self.phash = _phash_bits(self.image)
        self.hist = _histogram(self.image)
        self.edge = _edge_profile(self.image)
        self.vec = _masked_mse_vector(self.image)


def _load_references() -> List[Reference]:
    root = Path(os.getenv("MLBB_REFERENCE_ICON_DIR", "/app/reference_result_icons"))
    if not root.exists():
        # Local dev fallback: repo root.
        root = Path(__file__).resolve().parents[1] / "reference_result_icons"
    refs: List[Reference] = []
    for path in sorted(root.glob("*/*.png")):
        hero_id = path.parent.name
        reference_id = path.stem
        refs.append(Reference(hero_id=hero_id, reference_id=reference_id, path=path))
    return refs


REFERENCES = _load_references()
UNIQUE_HEROES = sorted({r.hero_id for r in REFERENCES})


def _distance_to_ref(img: Image.Image, ref: Reference) -> Tuple[float, Dict[str, float]]:
    q_dhash = _dhash_bits(img)
    q_phash = _phash_bits(img)
    q_hist = _histogram(img)
    q_edge = _edge_profile(img)
    q_vec = _masked_mse_vector(img)

    dh = _hamming(q_dhash, ref.dhash)
    ph = _hamming(q_phash, ref.phash)
    hd = _cosine_distance(q_hist, ref.hist)
    ed = _cosine_distance(q_edge, ref.edge)
    ms = _mse(q_vec, ref.vec)

    # Weighted distance. Lower is better.
    distance = 0.20 * dh + 0.20 * ph + 0.25 * hd + 0.20 * ed + 0.15 * min(ms * 4.0, 1.0)
    return float(distance), {
        "dhash": round(dh, 6),
        "phash": round(ph, 6),
        "histogram": round(hd, 6),
        "edge": round(ed, 6),
        "masked_mse": round(ms, 6),
    }


def _match_candidates(img: Image.Image, top_k: int) -> List[Candidate]:
    raw = []
    for ref in REFERENCES:
        dist, comps = _distance_to_ref(img, ref)
        raw.append((dist, ref, comps))
    raw.sort(key=lambda x: x[0])

    # Deduplicate by hero_id, keeping best reference per hero.
    best_by_hero: Dict[str, Tuple[float, Reference, Dict[str, float]]] = {}
    for dist, ref, comps in raw:
        if ref.hero_id not in best_by_hero:
            best_by_hero[ref.hero_id] = (dist, ref, comps)

    best = sorted(best_by_hero.values(), key=lambda x: x[0])[:top_k]
    out: List[Candidate] = []
    for rank, (dist, ref, comps) in enumerate(best, start=1):
        out.append(Candidate(
            hero_id=ref.hero_id,
            reference_id=ref.reference_id,
            rank=rank,
            distance=round(dist, 6),
            components=comps,
        ))
    return out


def _risk_flags(cands: List[Candidate]) -> List[str]:
    flags: List[str] = []
    if not cands:
        return ["no_reference_candidates"]
    if len(cands) >= 2:
        gap = cands[1].distance - cands[0].distance
        if gap < 0.035:
            flags.append("near_candidate_gap_small")
    if cands[0].distance > 0.30:
        flags.append("low_reference_similarity")
    flags.append("candidate_only_until_user_confirmation")
    return flags


@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html><body>
      <h1>MLBB External Image Matching Engine</h1>
      <p>Status: running</p>
      <ul>
        <li><a href="/health">/health</a></li>
        <li><a href="/privacy">/privacy</a></li>
        <li><a href="/docs">/docs</a></li>
      </ul>
    </body></html>
    """


@app.get("/privacy", response_class=HTMLResponse)
def privacy_policy():
    return """
    <html>
      <head><meta charset="utf-8"><title>Privacy Policy - MLBB Image Matching Engine</title></head>
      <body>
        <h1>Privacy Policy</h1>
        <p>Last updated: 2026-07-04</p>
        <h2>Overview</h2>
        <p>MLBB Image Matching Engine provides image analysis support for Mobile Legends: Bang Bang result screens.</p>
        <h2>Data We Process</h2>
        <p>The service may process uploaded result screen images, cropped hero icon regions, masked image features, hash data, histogram data, edge profile data, and request metadata required for API operation.</p>
        <h2>Purpose</h2>
        <p>Data is processed only for hero candidate support, image quality inspection, reference icon matching, and recognition stability.</p>
        <h2>Storage</h2>
        <p>Uploaded images are intended to be processed transiently during the request. The service is designed not to permanently store uploaded gameplay images.</p>
        <h2>Data Sharing</h2>
        <p>We do not sell uploaded images, extracted feature data, or user data.</p>
        <h2>Contact</h2>
        <p>Privacy contact: YOUR_CONTACT_EMAIL_HERE</p>
      </body>
    </html>
    """


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        engine=ENGINE_NAME,
        version=ENGINE_VERSION,
        reference_icon_count=len(REFERENCES),
        unique_hero_count=len(UNIQUE_HEROES),
        profile_id="HR-RESULT-SCREEN-PARTITION-V1.3",
    )


@app.post("/v1/mlbb/image-match/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> AnalyzeResponse:
    _check_api_key(x_api_key)
    img = _decode_image_base64(req.image_base64)

    slots: List[SlotResponse] = []
    for slot_name, team, row_index, box in _slot_boxes(img.size):
        icon = _normalize_crop(img, box)
        candidates = _match_candidates(icon, top_k=req.top_k)
        slots.append(SlotResponse(
            slot=slot_name,
            team=team,
            row_index=row_index,
            crop=CropBox(source_box=list(box), normalized_size=list(NORMALIZED_SIZE)),
            matched_candidates=candidates,
            risk_flags=_risk_flags(candidates),
            notes=[
                "v1.3 frozen test: result-screen native 125x125 crop matching.",
                "Flag and level regions are masked before comparison.",
                "Hero Lock is not allowed; GPT must ask user confirmation.",
            ],
        ))

    return AnalyzeResponse(
        engine=ENGINE_NAME,
        version=ENGINE_VERSION,
        screen_type=req.screen_type,
        profile_id="HR-RESULT-SCREEN-PARTITION-V1.3",
        reference_icon_count=len(REFERENCES),
        unique_hero_count=len(UNIQUE_HEROES),
        hero_lock_allowed=False,
        rule="candidate_only_until_user_confirmation",
        slots=slots,
    )

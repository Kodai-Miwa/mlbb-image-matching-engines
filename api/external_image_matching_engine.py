"""
MLBB External Image Matching Engine
Version: v1.2-action
Date: 2026-07-04

Purpose:
- FastAPI service for Custom GPT Actions.
- Receives a MLBB result screen image as base64.
- Extracts 10 hero icon crops using configurable result-screen slot boxes.
- Runs Feature-Zero contour inspection on normal crop and wide crop.
- Returns a structured JSON report.
- DOES NOT lock or finalize hero identity.

Install:
    pip install fastapi uvicorn pillow numpy opencv-python pydantic

Run:
    uvicorn external_image_matching_engine:app --host 0.0.0.0 --port 8000

Environment:
    MLBB_IMAGE_MATCHING_API_KEY=your-secret-key

Request:
    POST /v1/mlbb/image-match/analyze
    Header: X-API-Key: your-secret-key
"""

from __future__ import annotations
from fastapi.responses import HTMLResponse

import base64
import io
import os
from typing import Dict, List, Literal, Optional, Tuple

import numpy as np
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from PIL import Image, ImageFilter, ImageOps


ENGINE_NAME = "mlbb_external_image_matching_engine"
ENGINE_VERSION = "v1.2-action-20260704"

app = FastAPI(
    title="MLBB External Image Matching Engine",
    version=ENGINE_VERSION,
    description=(
        "Feature-Zero image matching report generator for MLBB result screens. "
        "This API returns contour and quality evidence only; it does not perform Hero Lock."
    ),

@app.get("/privacy", response_class=HTMLResponse)
def privacy_policy():
    return """
    <html>
      <head><title>Privacy Policy</title></head>
      <body>
        <h1>Privacy Policy</h1>
        ...
      </body>
    </html>
    """



)


class AnalyzeRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded screenshot image. Data URL prefix is allowed.")
    screen_type: Literal["result_screen"] = "result_screen"
    engine_version: str = "v1.2"
    slot_profile: Literal["default_720x1280_result", "auto"] = "default_720x1280_result"
    return_debug_samples: bool = False


class IconQuality(BaseModel):
    status: Literal["pass", "watch", "fail"]
    crop_alignment: Literal["ok", "watch", "unknown"]
    ui_interference: Literal["none", "possible", "unknown"]
    brightness: Literal["ok", "dark", "bright", "unknown"]
    compression_noise: Literal["low", "medium", "high", "unknown"]


class FeatureZero(BaseModel):
    mass_gravity: Literal["top_heavy", "middle_heavy", "bottom_heavy", "balanced", "unknown"]
    silhouette_symmetry: Literal["near_symmetric", "left_heavy", "right_heavy", "unknown"]
    contour_sharpness: Literal["smooth", "mixed", "spiky", "unknown"]
    top_projection: Literal["none", "low", "medium", "strong", "unknown"]
    bottom_projection: Literal["none", "low", "medium", "strong", "unknown"]
    side_projection: Literal["none", "low", "medium", "strong", "unknown"]
    row_width_curve_sample: Optional[List[int]] = None
    column_height_curve_sample: Optional[List[int]] = None


class CropReport(BaseModel):
    available: bool
    scale: float
    crop_box: List[int]
    feature_zero: FeatureZero


class SlotReport(BaseModel):
    slot: str
    icon_quality: IconQuality
    normal_crop: CropReport
    wide_crop: CropReport
    risk_flags: List[str]
    notes: List[str]


class AnalyzeResponse(BaseModel):
    engine: str
    version: str
    screen_type: str
    hero_lock_allowed: bool = False
    rule: str = "candidate_only_until_user_confirmation"
    slots: List[SlotReport]


def _check_api_key(x_api_key: Optional[str]) -> None:
    required = os.getenv("MLBB_IMAGE_MATCHING_API_KEY")
    if not required:
        # Development mode: allow no key if env is unset.
        return
    if not x_api_key or x_api_key != required:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


def _decode_image_base64(image_base64: str) -> Image.Image:
    raw = image_base64.strip()
    if "," in raw and raw.lower().startswith("data:"):
        raw = raw.split(",", 1)[1]
    try:
        data = base64.b64decode(raw, validate=False)
        img = Image.open(io.BytesIO(data)).convert("RGB")
        return img
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image: {exc}") from exc


def _resize_box(box: Tuple[int, int, int, int], img_size: Tuple[int, int], base_size: Tuple[int, int] = (720, 1280)) -> Tuple[int, int, int, int]:
    """Scale default 720x1280 boxes to uploaded screenshot size."""
    w, h = img_size
    bw, bh = base_size
    sx, sy = w / bw, h / bh
    x1, y1, x2, y2 = box
    return (int(round(x1 * sx)), int(round(y1 * sy)), int(round(x2 * sx)), int(round(y2 * sy)))


def _expand_box(box: Tuple[int, int, int, int], img_size: Tuple[int, int], pad_ratio: float = 0.28) -> Tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    px, py = int(w * pad_ratio), int(h * pad_ratio)
    iw, ih = img_size
    return (max(0, x1 - px), max(0, y1 - py), min(iw, x2 + px), min(ih, y2 + py))


def default_slot_boxes_720x1280() -> Dict[str, Tuple[int, int, int, int]]:
    """
    Default result-screen boxes for portrait screenshots close to 720x1280.
    These are intentionally approximate. Production should calibrate with more screenshots.
    """
    return {
        "ally_1": (35, 188, 121, 274),
        "ally_2": (35, 313, 121, 399),
        "ally_3": (35, 438, 121, 524),
        "ally_4": (35, 563, 121, 649),
        "ally_5": (35, 688, 121, 774),
        "enemy_1": (599, 188, 685, 274),
        "enemy_2": (599, 313, 685, 399),
        "enemy_3": (599, 438, 685, 524),
        "enemy_4": (599, 563, 685, 649),
        "enemy_5": (599, 688, 685, 774),
    }


def _crop_and_enhance(img: Image.Image, box: Tuple[int, int, int, int], scale: float) -> Image.Image:
    crop = img.crop(box)
    w, h = crop.size
    crop = crop.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)
    crop = ImageOps.autocontrast(crop)
    crop = crop.filter(ImageFilter.UnsharpMask(radius=1.2, percent=165, threshold=3))
    return crop


def _foreground_mask_feature_zero(icon: Image.Image) -> np.ndarray:
    """
    Feature-Zero foreground approximation.
    No semantic labels are used. Uses luminance deviation + saturation signal.
    """
    rgb = np.asarray(icon.convert("RGB")).astype(np.float32)
    gray = np.asarray(ImageOps.grayscale(icon)).astype(np.float32)

    # Robust edge/foreground signal: pixels far from median brightness, plus saturated pixels.
    med = np.median(gray)
    dev = np.abs(gray - med)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    maxc, minc = np.max(rgb, axis=2), np.min(rgb, axis=2)
    sat = maxc - minc

    signal = dev * 0.65 + sat * 0.35
    thr = np.percentile(signal, 58)
    mask = signal >= thr

    # Remove outer border bias lightly.
    h, w = mask.shape
    yy, xx = np.ogrid[:h, :w]
    cy, cx = h / 2, w / 2
    radius = min(h, w) * 0.51
    circle = (yy - cy) ** 2 + (xx - cx) ** 2 <= radius ** 2
    mask = mask & circle

    return mask


def _sample_curve(vals: List[int], n: int = 24) -> List[int]:
    if not vals:
        return []
    step = max(1, len(vals) // n)
    return [int(v) for v in vals[::step][:n]]


def _projection_strength(value: float, total: float) -> Literal["none", "low", "medium", "strong"]:
    ratio = value / max(total, 1.0)
    if ratio < 0.04:
        return "none"
    if ratio < 0.09:
        return "low"
    if ratio < 0.16:
        return "medium"
    return "strong"


def feature_zero_contour(icon: Image.Image, return_debug_samples: bool = False) -> FeatureZero:
    mask = _foreground_mask_feature_zero(icon)
    h, w = mask.shape

    row_widths: List[int] = []
    left_edges: List[int] = []
    right_edges: List[int] = []
    for y in range(h):
        xs = np.where(mask[y])[0]
        if len(xs) == 0:
            row_widths.append(0)
            left_edges.append(-1)
            right_edges.append(-1)
        else:
            row_widths.append(int(xs.max() - xs.min() + 1))
            left_edges.append(int(xs.min()))
            right_edges.append(int(xs.max()))

    col_heights: List[int] = []
    for x in range(w):
        ys = np.where(mask[:, x])[0]
        if len(ys) == 0:
            col_heights.append(0)
        else:
            col_heights.append(int(ys.max() - ys.min() + 1))

    top_mass = float(mask[: h // 3].sum())
    mid_mass = float(mask[h // 3 : (2 * h) // 3].sum())
    bottom_mass = float(mask[(2 * h) // 3 :].sum())
    masses = {"top_heavy": top_mass, "middle_heavy": mid_mass, "bottom_heavy": bottom_mass}
    max_label = max(masses, key=masses.get)
    if max(masses.values()) < 1:
        gravity = "unknown"
    elif max(masses.values()) <= (sum(masses.values()) / 3.0) * 1.12:
        gravity = "balanced"
    else:
        gravity = max_label

    left_mass = float(mask[:, : w // 2].sum())
    right_mass = float(mask[:, w // 2 :].sum())
    denom = max(left_mass + right_mass, 1.0)
    diff_ratio = abs(left_mass - right_mass) / denom
    if denom <= 1:
        symmetry = "unknown"
    elif diff_ratio < 0.08:
        symmetry = "near_symmetric"
    elif left_mass > right_mass:
        symmetry = "left_heavy"
    else:
        symmetry = "right_heavy"

    # Sharpness: row curve changes + edge jitter.
    row_diff = np.abs(np.diff(np.array(row_widths, dtype=np.float32)))
    edge_jitter = []
    valid_left = [v for v in left_edges if v >= 0]
    valid_right = [v for v in right_edges if v >= 0]
    if len(valid_left) > 2:
        edge_jitter.append(float(np.mean(np.abs(np.diff(valid_left)))))
    if len(valid_right) > 2:
        edge_jitter.append(float(np.mean(np.abs(np.diff(valid_right)))))
    sharpness_value = float(np.mean(row_diff)) + (float(np.mean(edge_jitter)) if edge_jitter else 0.0)
    norm_sharp = sharpness_value / max(w, 1) * 100.0
    if norm_sharp < 4.0:
        sharpness = "smooth"
    elif norm_sharp < 9.0:
        sharpness = "mixed"
    else:
        sharpness = "spiky"

    total_mass = float(mask.sum())
    top_proj = float(mask[: max(1, h // 8)].sum())
    bottom_proj = float(mask[h - max(1, h // 8) :].sum())
    side_proj = float(mask[:, : max(1, w // 8)].sum() + mask[:, w - max(1, w // 8) :].sum())

    return FeatureZero(
        mass_gravity=gravity,
        silhouette_symmetry=symmetry,
        contour_sharpness=sharpness,
        top_projection=_projection_strength(top_proj, total_mass),
        bottom_projection=_projection_strength(bottom_proj, total_mass),
        side_projection=_projection_strength(side_proj, total_mass),
        row_width_curve_sample=_sample_curve(row_widths) if return_debug_samples else None,
        column_height_curve_sample=_sample_curve(col_heights) if return_debug_samples else None,
    )


def icon_quality(icon: Image.Image) -> IconQuality:
    gray = np.asarray(ImageOps.grayscale(icon)).astype(np.float32)
    mean = float(gray.mean())
    std = float(gray.std())

    if mean < 45:
        brightness = "dark"
    elif mean > 220:
        brightness = "bright"
    else:
        brightness = "ok"

    # Very rough compression/noise proxy.
    if std < 18:
        noise = "medium"
    elif std > 75:
        noise = "high"
    else:
        noise = "low"

    status = "pass"
    if brightness != "ok" or noise == "high":
        status = "watch"

    return IconQuality(
        status=status,
        crop_alignment="ok",
        ui_interference="unknown",
        brightness=brightness,
        compression_noise=noise,
    )


def risk_flags_from_features(normal: FeatureZero, wide: FeatureZero) -> List[str]:
    flags: List[str] = []
    if normal.contour_sharpness != wide.contour_sharpness:
        flags.append("contour_crop_disagreement")
    if normal.silhouette_symmetry != wide.silhouette_symmetry:
        flags.append("symmetry_crop_disagreement")
    if normal.mass_gravity != wide.mass_gravity:
        flags.append("mass_balance_crop_disagreement")
    if normal.contour_sharpness == "smooth" and normal.mass_gravity in {"middle_heavy", "bottom_heavy"}:
        flags.append("blob_or_non_human_candidate")
    if normal.top_projection in {"medium", "strong"}:
        flags.append("top_projection_audit_required")
    if normal.side_projection in {"medium", "strong"}:
        flags.append("side_projection_audit_required")
    return flags


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "engine": ENGINE_NAME, "version": ENGINE_VERSION}
    
@app.get("/privacy", response_class=HTMLResponse)
def privacy_policy():
    return """
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>Privacy Policy - MLBB Image Matching Engine</title>
      </head>
      <body>
        <h1>Privacy Policy</h1>
        <p>Last updated: 2026-07-04</p>

        <h2>Overview</h2>
        <p>
          MLBB Image Matching Engine provides image analysis support for
          Mobile Legends: Bang Bang result screens. The service extracts visual
          feature data from uploaded result screen images and returns structured
          analysis data to the connected GPT for hero candidate generation.
        </p>

        <h2>Data We Process</h2>
        <p>
          When a user sends a MLBB result screen image to the GPT, the image may
          be sent to this API for processing. The API may process uploaded
          screenshots, cropped hero icon regions, contour data, silhouette data,
          mass balance data, image quality data, and request metadata required
          for API operation.
        </p>

        <h2>Purpose of Processing</h2>
        <p>
          Data is processed only for MLBB hero icon candidate support, image
          quality inspection, contour extraction, and recognition stability.
          The API does not make final hero identity decisions by itself.
        </p>

        <h2>Image Storage</h2>
        <p>
          Uploaded images are intended to be processed transiently during the
          request. The service is designed not to permanently store uploaded
          gameplay images.
        </p>

        <h2>Logs</h2>
        <p>
          Hosting providers may keep limited technical logs such as request
          time, status code, endpoint, IP address, and error logs for security,
          debugging, and service operation.
        </p>

        <h2>Data Sharing</h2>
        <p>
          We do not sell uploaded images, extracted feature data, or user data.
          Data may be processed by infrastructure providers used to host and
          operate the API.
        </p>

        <h2>Security</h2>
        <p>
          The API uses an API key to restrict access from authorized GPT Actions.
          Users should avoid uploading screenshots that contain sensitive
          personal information.
        </p>

        <h2>User Control</h2>
        <p>
          Users can choose not to upload images and may crop or mask personal
          information before uploading screenshots.
        </p>

        <h2>Contact</h2>
        <p>
          Privacy contact: YOUR_CONTACT_EMAIL_HERE
        </p>
      </body>
    </html>
    """

@app.post("/v1/mlbb/image-match/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> AnalyzeResponse:
    _check_api_key(x_api_key)
    img = _decode_image_base64(req.image_base64)

    boxes = default_slot_boxes_720x1280()
    slots: List[SlotReport] = []

    for slot, box720 in boxes.items():
        box = _resize_box(box720, img.size)
        wide_box = _expand_box(box, img.size, pad_ratio=0.30)

        normal_icon = _crop_and_enhance(img, box, scale=3.0)
        wide_icon = _crop_and_enhance(img, wide_box, scale=2.5)

        normal_fz = feature_zero_contour(normal_icon, return_debug_samples=req.return_debug_samples)
        wide_fz = feature_zero_contour(wide_icon, return_debug_samples=req.return_debug_samples)

        quality = icon_quality(normal_icon)
        flags = risk_flags_from_features(normal_fz, wide_fz)

        slots.append(
            SlotReport(
                slot=slot,
                icon_quality=quality,
                normal_crop=CropReport(
                    available=True,
                    scale=3.0,
                    crop_box=list(box),
                    feature_zero=normal_fz,
                ),
                wide_crop=CropReport(
                    available=True,
                    scale=2.5,
                    crop_box=list(wide_box),
                    feature_zero=wide_fz,
                ),
                risk_flags=flags,
                notes=[
                    "Feature-Zero only: no hair/eye/mouth semantic labels are assigned by API.",
                    "GPT/NexusOS must perform candidate-only interpretation and user confirmation.",
                ],
            )
        )

    return AnalyzeResponse(
        engine=ENGINE_NAME,
        version=ENGINE_VERSION,
        screen_type=req.screen_type,
        hero_lock_allowed=False,
        rule="candidate_only_until_user_confirmation",
        slots=slots,
    )

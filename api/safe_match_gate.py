"""
Safe Match Gate v1.3.2

Integrate this module into external_image_matching_engine.py.

Expected candidate input shape:
[
  {
    "hero_id": "lesley",
    "reference_id": "lesley_result_0001",
    "score": 0.91,
    "distance": 0.09,
    "rank": 1
  },
  ...
]
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel


MatchStatus = Literal["strong", "ambiguous", "weak", "unregistered"]


class SafeMatchConfig(BaseModel):
    strong_score_min: float = 0.84
    weak_score_max: float = 0.72
    strong_margin_min: float = 0.055
    ambiguous_margin_max: float = 0.055
    top_k_display: int = 5
    danger_pair_always_ambiguous: bool = True


DEFAULT_SAFE_MATCH_CONFIG = SafeMatchConfig()


DANGER_GROUPS_V1_3_2 = [
    {"group_id": "DG-LESLEY-GUINEVERE-IXIA", "heroes": {"lesley", "guinevere", "ixia"}},
    {"group_id": "DG-YIN-AULUS", "heroes": {"yin", "aulus"}},
    {"group_id": "DG-XBORG-ESMERALDA", "heroes": {"xborg", "x_borg", "esmeralda"}},
    {"group_id": "DG-FLORYN-RAFAELA-MATHILDA", "heroes": {"floryn", "rafaela", "mathilda"}},
    {"group_id": "DG-BEATRIX-CICI", "heroes": {"beatrix", "cici"}},
    {"group_id": "DG-AKAI-GROCK-BELERICK", "heroes": {"akai", "grock", "belerick"}},
    {"group_id": "DG-NANA-CHANGE-RUBY", "heroes": {"nana", "change", "chang_e", "ruby"}},
    {"group_id": "DG-CLINT-LAPULAPU", "heroes": {"clint", "lapu_lapu"}},
]


def _normalize_hero_id(hero_id: Optional[str]) -> str:
    if not hero_id:
        return "unknown"
    h = hero_id.strip().lower().replace(".", "").replace("-", "_").replace(" ", "_")
    aliases = {
        "x_borg": "xborg",
        "x.borg": "xborg",
        "chang'e": "change",
        "chang_e": "change",
        "popol_and_kupa": "popol_and_kupa",
        "lapu_lapu": "lapu_lapu",
    }
    return aliases.get(h, h)


def detect_danger_group(candidate_hero_ids: List[str]) -> Optional[str]:
    normalized = {_normalize_hero_id(h) for h in candidate_hero_ids}
    for group in DANGER_GROUPS_V1_3_2:
        if len(normalized.intersection(group["heroes"])) >= 2:
            return group["group_id"]
    return None


def apply_safe_match_gate(
    candidates: List[Dict],
    crop_confidence: str = "medium",
    reference_icon_count: int = 0,
    config: SafeMatchConfig = DEFAULT_SAFE_MATCH_CONFIG,
) -> Dict:
    """
    Return:
    {
      "match_status": "strong|ambiguous|weak|unregistered",
      "display_candidates": [...],
      "top_candidate_allowed": bool,
      "reason_flags": [...]
    }
    """

    reason_flags: List[str] = []

    if reference_icon_count <= 0:
        return {
            "match_status": "unregistered",
            "display_candidates": [],
            "top_candidate_allowed": False,
            "reason_flags": ["no_reference_registry"],
        }

    if not candidates:
        return {
            "match_status": "unregistered",
            "display_candidates": [],
            "top_candidate_allowed": False,
            "reason_flags": ["no_candidates_returned"],
        }

    sorted_candidates = sorted(candidates, key=lambda c: c.get("rank", 999))
    top = sorted_candidates[0]
    second = sorted_candidates[1] if len(sorted_candidates) > 1 else None

    top_score = float(top.get("score", 0.0))
    second_score = float(second.get("score", 0.0)) if second else 0.0
    margin = top_score - second_score

    hero_ids = [_normalize_hero_id(c.get("hero_id")) for c in sorted_candidates[: config.top_k_display]]
    danger_group_id = detect_danger_group(hero_ids)
    if danger_group_id:
        reason_flags.append(f"danger_group:{danger_group_id}")

    if crop_confidence == "low":
        reason_flags.append("low_crop_confidence")

    if top_score <= config.weak_score_max:
        reason_flags.append("top_score_weak")
        return {
            "match_status": "weak",
            "display_candidates": sorted_candidates[: config.top_k_display],
            "top_candidate_allowed": False,
            "reason_flags": reason_flags,
        }

    if crop_confidence == "low":
        return {
            "match_status": "weak",
            "display_candidates": sorted_candidates[: config.top_k_display],
            "top_candidate_allowed": False,
            "reason_flags": reason_flags,
        }

    if danger_group_id and config.danger_pair_always_ambiguous:
        return {
            "match_status": "ambiguous",
            "display_candidates": sorted_candidates[: config.top_k_display],
            "top_candidate_allowed": True,
            "reason_flags": reason_flags,
        }

    if margin <= config.ambiguous_margin_max:
        reason_flags.append("top_margin_small")
        return {
            "match_status": "ambiguous",
            "display_candidates": sorted_candidates[: config.top_k_display],
            "top_candidate_allowed": True,
            "reason_flags": reason_flags,
        }

    if top_score >= config.strong_score_min and margin >= config.strong_margin_min:
        return {
            "match_status": "strong",
            "display_candidates": sorted_candidates[: config.top_k_display],
            "top_candidate_allowed": True,
            "reason_flags": reason_flags,
        }

    reason_flags.append("score_between_strong_and_weak")
    return {
        "match_status": "ambiguous",
        "display_candidates": sorted_candidates[: config.top_k_display],
        "top_candidate_allowed": True,
        "reason_flags": reason_flags,
    }

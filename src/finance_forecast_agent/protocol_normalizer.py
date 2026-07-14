from __future__ import annotations

import re
from dataclasses import dataclass

SUPPORTED_SPLIT_TYPES = {"purged_walk_forward", "rolling_origin"}
CANONICAL_PROTOCOL_TYPES = {"purged_walk_forward", "rolling_origin", "blocked_backtest", "out_of_sample", "expanding_window", "unknown"}


@dataclass(frozen=True)
class ProtocolInfo:
    protocol_type: str
    description: str
    confidence: float

    def to_dict(self) -> dict[str, object]:
        return {"protocol_type": self.protocol_type, "description": self.description, "confidence": self.confidence}


def normalize_evaluation_protocol(value: object) -> ProtocolInfo:
    text = str(value or "").strip()
    lower = text.lower()
    if not lower or lower == "unknown":
        return ProtocolInfo("unknown", text or "unknown", 0.0)
    if lower in CANONICAL_PROTOCOL_TYPES:
        return ProtocolInfo(lower, text, 1.0)
    if "purged" in lower or "embargo" in lower:
        return ProtocolInfo("purged_walk_forward", text, 0.95)
    if "walk" in lower and "forward" in lower:
        return ProtocolInfo("purged_walk_forward", text, 0.80)
    if "rolling" in lower or "expanding" in lower:
        return ProtocolInfo("rolling_origin", text, 0.75)
    if "out-of-sample" in lower or "out of sample" in lower or "backtest" in lower or "back-test" in lower:
        return ProtocolInfo("purged_walk_forward", text, 0.55)
    if "non-overlapping" in lower or "non overlapping" in lower or "blocked" in lower:
        return ProtocolInfo("blocked_backtest", text, 0.70)
    if "chronological" in lower and any(
        token in lower for token in ("holdout", "train/validation/test", "train-validation-test", "split")
    ):
        return ProtocolInfo("out_of_sample", text, 0.85)
    return ProtocolInfo("unknown", text, 0.25)


def normalize_frequency(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text or text == "unknown":
        return "unknown"
    if any(token in text for token in ["minute", "min", "30 minutes", "intraday", "hour"]):
        return "intraday"
    if "day" in text or "daily" in text or "trading day" in text:
        return "daily"
    if "week" in text or "weekly" in text:
        return "weekly"
    if "month" in text or "monthly" in text:
        return "monthly"
    return text


def normalize_horizon(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text or text == "unknown":
        return "unknown"
    count_match = re.search(r"\b(\d+)\s*[- ]?(trading\s+)?(day|days|week|weeks|month|months|step|steps)\b", text)
    if count_match and int(count_match.group(1)) > 1:
        count = int(count_match.group(1))
        unit = count_match.group(3).rstrip("s")
        return f"{count}_{unit}"
    if "intraday" in text:
        return "intraday_direction"
    if "day" in text or "trading day" in text or "1d" in text:
        return "next_return"
    if "week" in text:
        return "next_week_return"
    if "month" in text:
        return "next_month_return"
    if "return" in text or "direction" in text:
        return "next_return"
    return text

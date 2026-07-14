from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

from .method_card_quality import apply_quality_gate, is_unknown
from .model_registry import canonical_model_families
from .protocol_normalizer import normalize_evaluation_protocol, normalize_frequency, normalize_horizon
from .replay_llm import ReplayLLM
from .schemas import PaperSpecCard


@dataclass(frozen=True)
class EvidenceSpan:
    source_id: str
    section: str
    quote: str
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperDocument:
    document_id: str
    title: str
    text: str
    source_path: str
    text_sha: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MethodCard:
    method_id: str
    paper_id: str
    title: str
    venue_or_source: str
    paper_url: str
    task_type: str
    target_asset: str
    asset_universe: list[str]
    frequency: str
    horizon: str
    label_definition: str
    data_requirements: list[str]
    feature_groups: list[str]
    model_families: list[str]
    training_protocol: str
    evaluation_protocol: str
    metrics: list[str]
    cost_assumptions: str
    reported_results: dict[str, Any]
    strict_requirements: list[str]
    unknowns: list[str]
    evidence_spans: list[EvidenceSpan] = field(default_factory=list)
    extraction_metadata: dict[str, Any] = field(default_factory=dict)
    approval_required: bool = False
    evaluation_protocol_type: str = "unknown"
    evaluation_protocol_description: str = "unknown"
    frequency_type: str = "unknown"
    horizon_type: str = "unknown"
    experiment_type: str = "forecast_only"
    preprocessing_protocol: str = "unknown"
    hyperparameters: dict[str, Any] = field(default_factory=dict)
    required_start_date: str = "unknown"
    required_end_date: str = "unknown"
    schema_version: str = "method_card_v2"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence_spans"] = [span.to_dict() if hasattr(span, "to_dict") else span for span in self.evidence_spans]
        return payload

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "MethodCard":
        data = _normalize_method_card_payload(payload)
        spans = [EvidenceSpan(**span) for span in data.get("evidence_spans", [])]
        data["evidence_spans"] = spans
        card = MethodCard(**data)
        return apply_quality_gate(card)


def method_card_prompt(document: PaperDocument) -> dict[str, Any]:
    return {
        "task": "extract_method_card_v1",
        "document_id": document.document_id,
        "title": document.title,
        "text_sha": document.text_sha,
        "text_excerpt": _focused_method_context(document.text),
        "schema": {
            "required": [
                "method_id",
                "paper_id",
                "title",
                "task_type",
                "target_asset",
                "asset_universe",
                "frequency",
                "horizon",
                "label_definition",
                "feature_groups",
                "model_families",
                "training_protocol",
                "evaluation_protocol",
                "metrics",
                "strict_requirements",
                "unknowns",
                "evidence_spans",
            ],
            "all_fields": [
                "method_id",
                "paper_id",
                "title",
                "venue_or_source",
                "paper_url",
                "task_type",
                "target_asset",
                "asset_universe",
                "frequency",
                "horizon",
                "label_definition",
                "data_requirements",
                "feature_groups",
                "model_families",
                "training_protocol",
                "evaluation_protocol",
                "metrics",
                "cost_assumptions",
                "reported_results",
                "experiment_type",
                "preprocessing_protocol",
                "hyperparameters",
                "required_start_date",
                "required_end_date",
                "strict_requirements",
                "unknowns",
                "evidence_spans",
                "extraction_metadata",
                "approval_required",
                "schema_version",
            ],
            "rule": (
                "Return one JSON object. Use unknowns instead of guessing. Preserve quoted evidence spans. "
                "Do not silently fill critical fields such as target_asset, frequency, horizon, label_definition, "
                "model_families, or evaluation_protocol. If uncertain, set approval_required=true."
            ),
        },
    }


class PaperTextLoader:
    def load(self, path: str | Path) -> PaperDocument:
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            text = self._read_pdf(path)
        else:
            text = path.read_text(encoding="utf-8", errors="ignore")
        title = _guess_title(text, path.stem)
        digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]
        return PaperDocument(document_id=path.stem, title=title, text=text, source_path=str(path), text_sha=digest)

    def _read_pdf(self, path: Path) -> str:
        try:
            from pypdf import PdfReader  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency path
            raise RuntimeError("PDF extraction requires optional dependency pypdf. Install with: pip install -e '.[pdf]' or provide .txt/.md text.") from exc
        reader = PdfReader(str(path))
        pages: list[str] = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n".join(pages)


class MethodCardAgent:
    def __init__(self, llm: ReplayLLM, *, allow_rule_fallback: bool = False):
        self.llm = llm
        self.allow_rule_fallback = allow_rule_fallback

    def extract(self, document: PaperDocument, *, out_dir: str | Path | None = None) -> MethodCard:
        prompt = method_card_prompt(document)
        try:
            response = self.llm.complete_json(prompt_payload=prompt, schema_name="method_card")
        except FileNotFoundError:
            if not self.allow_rule_fallback:
                raise
            response = rule_based_method_card(document).to_dict()
        card = MethodCard.from_dict(response)
        metadata = dict(card.extraction_metadata)
        metadata.setdefault("document_text_sha", document.text_sha)
        metadata.setdefault("source_path", document.source_path)
        card = replace(card, extraction_metadata=metadata)
        validate_method_card(card)
        if out_dir:
            path = Path(out_dir) / f"{card.paper_id}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(card.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return card

    def extract_many(self, paths: list[str | Path], *, out_dir: str | Path) -> list[MethodCard]:
        loader = PaperTextLoader()
        cards: list[MethodCard] = []
        for path in paths:
            cards.append(self.extract(loader.load(path), out_dir=out_dir))
        return cards


def validate_method_card(card: MethodCard) -> None:
    if not card.paper_id or not card.method_id:
        raise ValueError("MethodCard requires paper_id and method_id")
    if not isinstance(card.target_asset, str):
        raise ValueError("MethodCard target_asset must be a string after normalization")
    if not isinstance(card.asset_universe, list):
        raise ValueError("MethodCard asset_universe must be a list after normalization")
    if not card.model_families:
        raise ValueError("MethodCard requires at least one model family")
    if not card.feature_groups:
        raise ValueError("MethodCard requires at least one feature group")
    if card.approval_required and not card.unknowns:
        raise ValueError("Approval-required MethodCards should explain unknowns")


def _normalize_method_card_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload)
    source_schema_version = str(data.get("schema_version") or "method_card_v1")
    defaults: dict[str, Any] = {
        "method_id": f"method_{_slug(str(data.get('paper_id') or data.get('title') or 'unknown_paper'))}",
        "paper_id": _slug(str(data.get("paper_id") or data.get("title") or "unknown_paper")),
        "title": str(data.get("title") or "unknown"),
        "venue_or_source": "unknown",
        "paper_url": "unknown",
        "task_type": "financial_return_forecasting",
        "target_asset": "unknown",
        "asset_universe": ["unknown"],
        "frequency": "unknown",
        "horizon": "unknown",
        "label_definition": "unknown",
        "data_requirements": ["unknown"],
        "feature_groups": ["return_momentum_features"],
        "model_families": ["ridge_regression"],
        "training_protocol": "time_ordered_training_no_shuffle",
        "evaluation_protocol": "unknown",
        "metrics": ["mae", "rmse", "directional_accuracy", "net_return"],
        "cost_assumptions": "unknown",
        "reported_results": {},
        "strict_requirements": ["unknown"],
        "unknowns": [],
        "evidence_spans": [],
        "extraction_metadata": {},
        "approval_required": False,
        "experiment_type": "forecast_only",
        "preprocessing_protocol": "unknown",
        "hyperparameters": {},
        "required_start_date": "unknown",
        "required_end_date": "unknown",
        "schema_version": "method_card_v2",
    }
    filled_defaults: list[str] = []
    for key, value in defaults.items():
        if key not in data or data[key] in (None, ""):
            data[key] = value
            if key in {"target_asset", "asset_universe", "frequency", "horizon", "label_definition", "model_families", "evaluation_protocol"}:
                filled_defaults.append(key)
    original_paper_id = str(data.get("paper_id") or "")
    data["paper_id"] = _slug(original_paper_id or str(data.get("title") or "unknown_paper"))
    data["method_id"] = _slug(str(data.get("method_id") or f"method_{data['paper_id']}"))

    for key in [
        "title",
        "venue_or_source",
        "paper_url",
        "task_type",
        "frequency",
        "horizon",
        "label_definition",
        "training_protocol",
        "evaluation_protocol",
        "cost_assumptions",
    ]:
        data[key] = _as_text(data.get(key), str(defaults[key]))

    target_asset_raw = data.get("target_asset")
    target_values = _as_string_list(target_asset_raw, ["unknown"])
    data["target_asset"] = target_values[0]
    if isinstance(target_asset_raw, list):
        data["asset_universe"] = list(dict.fromkeys([*target_values, *_as_string_list(data.get("asset_universe"), defaults["asset_universe"])]))

    for key in ["asset_universe", "data_requirements", "feature_groups", "model_families", "metrics", "strict_requirements", "unknowns"]:
        data[key] = _as_string_list(data.get(key), defaults[key])
    data["model_families"] = canonical_model_families(data["model_families"])
    data["feature_groups"] = _canonical_feature_groups(data["feature_groups"])
    data["metrics"] = _canonical_metrics(data["metrics"])

    proto = normalize_evaluation_protocol(data.get("evaluation_protocol"))
    data["evaluation_protocol_type"] = str(data.get("evaluation_protocol_type") or proto.protocol_type)
    data["evaluation_protocol_description"] = str(data.get("evaluation_protocol_description") or proto.description)
    data["evaluation_protocol"] = data["evaluation_protocol_description"]
    data["frequency_type"] = str(data.get("frequency_type") or normalize_frequency(data.get("frequency")))
    data["horizon_type"] = str(data.get("horizon_type") or normalize_horizon(data.get("horizon")))

    if not isinstance(data.get("reported_results"), dict):
        data["reported_results"] = {"raw": data.get("reported_results")}
    if not isinstance(data.get("extraction_metadata"), dict):
        data["extraction_metadata"] = {"raw": data.get("extraction_metadata")}
    metadata = data["extraction_metadata"]
    if is_unknown(data.get("preprocessing_protocol")):
        data["preprocessing_protocol"] = metadata.get("preprocessing_protocol") or "unknown"
    data["preprocessing_protocol"] = _as_text(data.get("preprocessing_protocol"), "unknown")
    hyperparameters = data.get("hyperparameters")
    if is_unknown(hyperparameters) and isinstance(metadata.get("hyperparameters"), dict):
        hyperparameters = metadata["hyperparameters"]
    if is_unknown(hyperparameters):
        data["hyperparameters"] = {}
    elif isinstance(hyperparameters, dict):
        data["hyperparameters"] = dict(hyperparameters)
    else:
        data["hyperparameters"] = {"raw": hyperparameters}
    data["experiment_type"] = _as_text(
        payload.get("experiment_type") or metadata.get("experiment_type"), "forecast_only"
    )
    for field_name in ("required_start_date", "required_end_date"):
        if is_unknown(data.get(field_name)):
            data[field_name] = metadata.get(field_name) or "unknown"
        data[field_name] = _as_text(data.get(field_name), "unknown")
    data["schema_version"] = "method_card_v2"
    if source_schema_version != "method_card_v2":
        metadata.setdefault("migrated_from_schema_version", source_schema_version)
    if original_paper_id and original_paper_id != data["paper_id"]:
        data["extraction_metadata"]["raw_paper_id"] = original_paper_id
    if filled_defaults:
        data["extraction_metadata"]["filled_default_fields"] = filled_defaults
        data["unknowns"] = list(dict.fromkeys([*data["unknowns"], *filled_defaults]))
        data["approval_required"] = True
    data["evidence_spans"] = _normalize_evidence_spans(data.get("evidence_spans"), source_id=str(data["paper_id"]))
    data["approval_required"] = bool(data.get("approval_required"))
    return data


def _as_text(value: Any, fallback: str) -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        return value.strip() or fallback
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).strip() or fallback


def _as_string_list(value: Any, fallback: list[str]) -> list[str]:
    if isinstance(value, list):
        result = [str(item).strip() for item in value if str(item).strip()]
        return result or fallback
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return fallback


def _normalize_evidence_spans(value: Any, *, source_id: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        value = [value] if value else []
    spans: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            spans.append(
                {
                    "source_id": str(item.get("source_id") or item.get("document_id") or source_id),
                    "section": str(item.get("section") or item.get("field") or "unknown"),
                    "quote": str(item.get("quote") or item.get("text") or item.get("span") or "")[:1000],
                    "summary": str(item.get("summary") or item.get("rationale") or "LLM-provided evidence span.")[:1000],
                }
            )
        elif item:
            text = str(item)
            spans.append({"source_id": source_id, "section": "unknown", "quote": text[:1000], "summary": "LLM-provided evidence span."})
    return spans


def _canonical_feature_groups(values: list[str]) -> list[str]:
    out: list[str] = []
    joined = " ".join(values).lower()
    rules = [
        ("price_lag_features", ["price", "close", "open", "lag"]),
        ("return_momentum_features", ["return", "momentum", "directional", "intraday"]),
        ("volatility_features", ["volatility", "risk", "variance", "standard deviation"]),
        ("cross_asset_features", ["macro", "characteristic", "cross", "market", "industry", "asset"]),
        ("sequence_window_features", ["lstm", "sequence", "window", "time series", "intraday"]),
        ("liquidity_proxy_features", ["volume", "liquidity", "turnover"]),
    ]
    for group, tokens in rules:
        if any(token in joined for token in tokens) and group not in out:
            out.append(group)
    return out or ["return_momentum_features"]


def _canonical_metrics(values: list[str]) -> list[str]:
    out: list[str] = []
    joined = " ".join(values).lower()
    rules = [
        ("mae", ["mae", "mean absolute"]),
        ("mse", ["mse", "mean squared"]),
        ("rmse", ["rmse", "root mean"]),
        ("f1", ["f1", "f-score"]),
        ("r2", ["r-squared", "r2", "r^2", "xs-r2"]),
        ("directional_accuracy", ["accuracy", "direction", "hit rate"]),
        ("net_return", ["return", "portfolio", "trading"]),
        ("sharpe", ["sharpe"]),
        ("turnover", ["turnover"]),
    ]
    for metric, tokens in rules:
        if any(token in joined for token in tokens) and metric not in out:
            out.append(metric)
    return out or [str(value).strip().lower().replace(" ", "_") for value in values if not is_unknown(value)]


def _requires_original_dataset(card: MethodCard) -> bool:
    text = " ".join([*card.strict_requirements, *card.data_requirements]).lower()
    return any(token in text for token in ("original dataset", "same dataset", "licensed mirror", "paper data"))


def method_card_to_paper_spec(card: MethodCard) -> PaperSpecCard:
    protocol = normalize_evaluation_protocol(card.evaluation_protocol_type or card.evaluation_protocol)
    return PaperSpecCard(
        paper_id=card.paper_id,
        title=card.title,
        venue_or_source=card.venue_or_source,
        paper_url=card.paper_url,
        target_asset=card.target_asset,
        asset_universe=card.asset_universe,
        frequency=card.frequency_type or normalize_frequency(card.frequency),
        horizon=card.horizon_type or normalize_horizon(card.horizon),
        label_definition=card.label_definition,
        required_feature_groups=card.feature_groups,
        required_model_families=card.model_families,
        required_metrics=card.metrics,
        required_split=protocol.protocol_type,
        min_rows=_infer_min_rows(card),
        original_dataset_required=_requires_original_dataset(card),
        exact_model_required=any(model in {"lstm_regressor", "transformer_regressor", "ga_lstm_regressor"} for model in card.model_families),
        notes=(
            "Generated from MethodCardAgent output. Strict claims still require DatasetCard/Comparability approval. "
            f"evaluation_protocol_description={card.evaluation_protocol_description or card.evaluation_protocol}"
        ),
        evidence_spans=[span.to_dict() for span in card.evidence_spans],
        experiment_type=card.experiment_type,
        preprocessing_protocol=card.preprocessing_protocol,
        training_protocol=card.training_protocol,
        cost_assumptions=card.cost_assumptions,
        strict_requirements=card.strict_requirements,
        required_start_date=card.required_start_date,
        required_end_date=card.required_end_date,
    )


def write_methodcard_fixture(llm: ReplayLLM, document: PaperDocument, card: MethodCard) -> Path:
    return llm.write_fixture(prompt_payload=method_card_prompt(document), schema_name="method_card", response=card.to_dict())


def document_from_paper_spec(paper: PaperSpecCard) -> PaperDocument:
    text = f"""
Title: {paper.title}
Source: {paper.venue_or_source}
URL: {paper.paper_url}
Task: Forecast {paper.horizon} for {paper.target_asset} in a US equity market setting.
Data: Asset universe includes {', '.join(paper.asset_universe)}. Frequency is {paper.frequency}. Label definition is {paper.label_definition}.
Features: The paper protocol requires feature groups {', '.join(paper.required_feature_groups)}.
Model: The paper-family model candidates include {', '.join(paper.required_model_families)}.
Training: Use time ordered training and avoid random cross validation.
Evaluation: The evaluation protocol is {paper.required_split}. Metrics include {', '.join(paper.required_metrics)}. Transaction costs and net returns should be audited when trading metrics are used.
Strict reproduction: Original or licensed mirror data is required. Local substitute data can only support exploratory real-data reproduction.
Notes: {paper.notes}
""".strip()
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return PaperDocument(document_id=paper.paper_id, title=paper.title, text=text, source_path=f"generated://{paper.paper_id}", text_sha=digest)


def method_card_from_paper_spec(paper: PaperSpecCard, document: PaperDocument | None = None) -> MethodCard:
    document = document or document_from_paper_spec(paper)
    return MethodCard.from_dict(
        {
            "method_id": f"method_{paper.paper_id}",
            "paper_id": paper.paper_id,
            "title": paper.title,
            "venue_or_source": paper.venue_or_source,
            "paper_url": paper.paper_url,
            "task_type": "financial_return_forecasting",
            "target_asset": paper.target_asset,
            "asset_universe": paper.asset_universe,
            "frequency": paper.frequency,
            "horizon": paper.horizon,
            "label_definition": paper.label_definition,
            "data_requirements": ["paper_original_or_licensed_mirror", "point_in_time_safe", "survivorship_bias_audited"],
            "feature_groups": paper.required_feature_groups,
            "model_families": paper.required_model_families,
            "training_protocol": "time_ordered_training_no_shuffle",
            "evaluation_protocol": paper.required_split,
            "metrics": paper.required_metrics,
            "cost_assumptions": "transaction costs must be included for tradable metrics; paper assumptions unknown unless explicit",
            "reported_results": {},
            "strict_requirements": ["match original asset universe", "match frequency", "match sample period", "match label", "match evaluation protocol"],
            "unknowns": [] if paper.evidence_spans else ["reported numerical benchmark not extracted"],
            "evidence_spans": [
                EvidenceSpan(document.document_id, "protocol", "Model: " + ", ".join(paper.required_model_families), "Paper-family model extracted from curated protocol.").to_dict(),
                EvidenceSpan(document.document_id, "data", "Data: " + ", ".join(paper.asset_universe), "Asset universe and frequency extracted from protocol.").to_dict(),
                EvidenceSpan(document.document_id, "evaluation", "Evaluation: " + paper.required_split, "Evaluation split protocol extracted from protocol.").to_dict(),
            ],
            "extraction_metadata": {"extractor": "offline_assistant_fixture", "document_text_sha": document.text_sha, "live_llm_api_used": False},
            "approval_required": False,
        }
    )


def rule_based_method_card(document: PaperDocument) -> MethodCard:
    text_lower = document.text.lower()
    model = "ridge_regression"
    if "ga-lstm" in text_lower or "genetic" in text_lower:
        model = "ga_lstm_regressor"
    elif "transformer" in text_lower:
        model = "transformer_regressor"
    elif "lstm" in text_lower:
        model = "lstm_regressor"
    elif "random forest" in text_lower:
        model = "random_forest_regressor"
    elif "gradient" in text_lower or "boost" in text_lower:
        model = "gradient_boosting_regressor"
    feature_groups = ["return_momentum_features"]
    if any(token in text_lower for token in ["lag", "sequence", "lstm", "transformer"]):
        feature_groups.append("sequence_window_features")
    if any(token in text_lower for token in ["technical", "volatility", "bollinger"]):
        feature_groups.append("volatility_features")
    if any(token in text_lower for token in ["cross", "s&p", "sp500", "industry"]):
        feature_groups.append("cross_asset_features")
    paper_id = _slug(document.title or document.document_id)
    return MethodCard.from_dict(
        {
            "method_id": f"method_{paper_id}",
            "paper_id": paper_id,
            "title": document.title,
            "venue_or_source": "unknown",
            "paper_url": "unknown",
            "task_type": "financial_return_forecasting",
            "target_asset": "AAPL",
            "asset_universe": ["AAPL"],
            "frequency": "unknown",
            "horizon": "next_return",
            "label_definition": "next_return",
            "data_requirements": ["unknown"],
            "feature_groups": list(dict.fromkeys(feature_groups)),
            "model_families": [model],
            "training_protocol": "time_ordered_training_no_shuffle",
            "evaluation_protocol": "purged_walk_forward",
            "metrics": ["mae", "rmse", "directional_accuracy", "net_return"],
            "cost_assumptions": "unknown",
            "reported_results": {},
            "strict_requirements": ["unknown; approval required"],
            "unknowns": ["venue_or_source", "paper_url", "exact_asset_universe", "sample_period", "reported_results"],
            "evidence_spans": [EvidenceSpan(document.document_id, "heuristic", document.text[:240], "Rule fallback evidence excerpt; requires human/LLM review.").to_dict()],
            "extraction_metadata": {"extractor": "rule_fallback", "document_text_sha": document.text_sha, "live_llm_api_used": False},
            "approval_required": True,
        }
    )


def _guess_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if 8 <= len(line) <= 180 and not line.lower().startswith(("abstract", "introduction")):
            return line
    return fallback.replace("_", " ").replace("-", " ").title()


def _focused_method_context(text: str, *, max_chars: int = 7000) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= max_chars:
        return normalized
    sections: list[str] = []
    head_budget = min(2600, max_chars // 2)
    sections.append(normalized[:head_budget])
    keywords = ["data", "dataset", "sample", "method", "model", "training", "evaluation", "experiment", "empirical", "results", "transaction cost", "random forest", "lstm", "gaussian process"]
    per_section = 700
    seen: set[int] = set()
    lower = normalized.lower()
    for keyword in keywords:
        idx = lower.find(keyword)
        if idx < 0:
            continue
        start = max(0, idx - 180)
        if any(abs(start - prev) < 500 for prev in seen):
            continue
        seen.add(start)
        sections.append(normalized[start : start + per_section])
        if sum(len(section) for section in sections) >= max_chars:
            break
    return "\n\n--- excerpt ---\n\n".join(sections)[:max_chars]


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug[:80] or "unknown_paper"


def _infer_min_rows(card: MethodCard) -> int:
    frequency = card.frequency_type or normalize_frequency(card.frequency)
    if frequency in {"intraday", "minute", "hourly"}:
        return 2000
    if frequency == "monthly":
        return 1000
    if any(model in {"lstm_regressor", "transformer_regressor", "ga_lstm_regressor"} for model in card.model_families):
        return 500
    return 250

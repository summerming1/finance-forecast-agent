from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

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

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence_spans"] = [span.to_dict() if hasattr(span, "to_dict") else span for span in self.evidence_spans]
        return payload

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "MethodCard":
        spans = [EvidenceSpan(**span) for span in payload.get("evidence_spans", [])]
        data = dict(payload)
        data["evidence_spans"] = spans
        return MethodCard(**data)


def method_card_prompt(document: PaperDocument) -> dict[str, Any]:
    return {
        "task": "extract_method_card_v1",
        "document_id": document.document_id,
        "title": document.title,
        "text_sha": document.text_sha,
        "text_excerpt": document.text[:12000],
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
            "rule": "Use unknowns instead of guessing. Every key model/data/evaluation field should have an evidence span when possible.",
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
    if not card.model_families:
        raise ValueError("MethodCard requires at least one model family")
    if not card.feature_groups:
        raise ValueError("MethodCard requires at least one feature group")
    if card.approval_required and not card.unknowns:
        raise ValueError("Approval-required MethodCards should explain unknowns")


def method_card_to_paper_spec(card: MethodCard) -> PaperSpecCard:
    return PaperSpecCard(
        paper_id=card.paper_id,
        title=card.title,
        venue_or_source=card.venue_or_source,
        paper_url=card.paper_url,
        target_asset=card.target_asset,
        asset_universe=card.asset_universe,
        frequency=card.frequency,
        horizon=card.horizon,
        label_definition=card.label_definition,
        required_feature_groups=card.feature_groups,
        required_model_families=card.model_families,
        required_metrics=card.metrics,
        required_split=card.evaluation_protocol,
        min_rows=_infer_min_rows(card),
        original_dataset_required=True,
        exact_model_required=any(model in {"lstm_regressor", "transformer_regressor", "ga_lstm_regressor"} for model in card.model_families),
        notes="Generated from MethodCardAgent output. Strict claims still require DatasetCard/Comparability approval.",
        evidence_spans=[span.to_dict() for span in card.evidence_spans],
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
    return MethodCard(
        method_id=f"method_{paper.paper_id}",
        paper_id=paper.paper_id,
        title=paper.title,
        venue_or_source=paper.venue_or_source,
        paper_url=paper.paper_url,
        task_type="financial_return_forecasting",
        target_asset=paper.target_asset,
        asset_universe=paper.asset_universe,
        frequency=paper.frequency,
        horizon=paper.horizon,
        label_definition=paper.label_definition,
        data_requirements=["paper_original_or_licensed_mirror", "point_in_time_safe", "survivorship_bias_audited"],
        feature_groups=paper.required_feature_groups,
        model_families=paper.required_model_families,
        training_protocol="time_ordered_training_no_shuffle",
        evaluation_protocol=paper.required_split,
        metrics=paper.required_metrics,
        cost_assumptions="transaction costs must be included for tradable metrics; paper assumptions unknown unless explicit",
        reported_results={},
        strict_requirements=["match original asset universe", "match frequency", "match sample period", "match label", "match evaluation protocol"],
        unknowns=[] if paper.evidence_spans else ["reported numerical benchmark not extracted"],
        evidence_spans=[
            EvidenceSpan(document.document_id, "protocol", "Model: " + ", ".join(paper.required_model_families), "Paper-family model extracted from curated protocol."),
            EvidenceSpan(document.document_id, "data", "Data: " + ", ".join(paper.asset_universe), "Asset universe and frequency extracted from protocol."),
            EvidenceSpan(document.document_id, "evaluation", "Evaluation: " + paper.required_split, "Evaluation split protocol extracted from protocol."),
        ],
        extraction_metadata={"extractor": "offline_assistant_fixture", "document_text_sha": document.text_sha, "live_llm_api_used": False},
        approval_required=False,
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
    return MethodCard(
        method_id=f"method_{paper_id}",
        paper_id=paper_id,
        title=document.title,
        venue_or_source="unknown",
        paper_url="unknown",
        task_type="financial_return_forecasting",
        target_asset="AAPL",
        asset_universe=["AAPL"],
        frequency="unknown",
        horizon="next_return",
        label_definition="next_return",
        data_requirements=["unknown"],
        feature_groups=list(dict.fromkeys(feature_groups)),
        model_families=[model],
        training_protocol="time_ordered_training_no_shuffle",
        evaluation_protocol="purged_walk_forward",
        metrics=["mae", "rmse", "directional_accuracy", "net_return"],
        cost_assumptions="unknown",
        reported_results={},
        strict_requirements=["unknown; approval required"],
        unknowns=["venue_or_source", "paper_url", "exact_asset_universe", "sample_period", "reported_results"],
        evidence_spans=[EvidenceSpan(document.document_id, "heuristic", document.text[:240], "Rule fallback evidence excerpt; requires human/LLM review.")],
        extraction_metadata={"extractor": "rule_fallback", "document_text_sha": document.text_sha, "live_llm_api_used": False},
        approval_required=True,
    )


def _guess_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if 8 <= len(line) <= 180 and not line.lower().startswith(("abstract", "introduction")):
            return line
    return fallback.replace("_", " ").replace("-", " ").title()


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug[:80] or "unknown_paper"


def _infer_min_rows(card: MethodCard) -> int:
    if card.frequency in {"intraday", "minute", "hourly"}:
        return 2000
    if card.frequency == "monthly":
        return 1000
    if any(model in {"lstm_regressor", "transformer_regressor", "ga_lstm_regressor"} for model in card.model_families):
        return 500
    return 250

from __future__ import annotations

from pathlib import Path
from typing import Any

from .method_cards import MethodCard
from .p1_protocol import classify_experiment_type

UNKNOWN_VALUES = {"", "unknown", "n/a", "none", "not specified"}


def _text(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value if str(item).strip()) or "未提取"
    if isinstance(value, dict):
        return ", ".join(f"{key}={item}" for key, item in value.items()) or "未提取"
    text = str(value or "").strip()
    return "未提取" if text.lower() in UNKNOWN_VALUES else text


def paper_inventory(papers_dir: str | Path, cards: list[MethodCard]) -> list[dict[str, Any]]:
    papers_dir = Path(papers_dir)
    by_source_name: dict[str, MethodCard] = {}
    for card in cards:
        source_path = str(card.extraction_metadata.get("source_path") or "")
        if source_path:
            by_source_name[Path(source_path).name.lower()] = card

    rows: list[dict[str, Any]] = []
    for path in sorted(
        [*papers_dir.glob("*.pdf"), *papers_dir.glob("*.txt"), *papers_dir.glob("*.md")],
        key=lambda item: item.name.lower(),
    ):
        card = by_source_name.get(path.name.lower())
        rows.append(
            {
                "file_name": path.name,
                "path": str(path),
                "format": path.suffix.lower().lstrip(".").upper(),
                "status": "已提取" if card else "未提取",
                "paper_id": card.paper_id if card else None,
                "title": card.title if card else path.stem,
            }
        )
    return rows


def _evidence_purpose(quote: str) -> str:
    text = quote.lower()
    if any(token in text for token in ["return", "outdistanc", "top three", "result", "achieve"]):
        return "研究结果"
    if any(token in text for token in ["back-test", "backtest", "commission", "trading period", "compared"]):
        return "回测评估"
    if any(token in text for token in ["training", "learning", "memory", "reward", "batch"]):
        return "训练方法"
    if any(token in text for token in ["network", "lstm", "cnn", "rnn", "model", "framework", "softmax"]):
        return "模型结构"
    if any(token in text for token in ["dataset", "market", "asset", "price", "history", "cryptocurr"]):
        return "数据与特征"
    return "其他依据"


def evidence_rows(card: MethodCard) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for span in card.evidence_spans:
        section = str(span.section or "unknown").strip()
        has_section = section.lower() not in UNKNOWN_VALUES
        rows.append(
            {
                "用途": _evidence_purpose(span.quote),
                "原文章节": section if has_section else "未标注（旧提取结果）",
                "证据原文": span.quote,
                "说明": span.summary if span.summary != "LLM-provided evidence span." else "支持方法卡字段的原文摘录",
                "可追踪性": "完整" if has_section else "缺少章节位置",
            }
        )
    return rows


def method_summary_rows(card: MethodCard) -> list[dict[str, str]]:
    rows = [
        ("研究目标", "任务", card.task_type),
        ("研究目标", "目标资产", card.target_asset),
        ("数据", "资产范围", card.asset_universe),
        ("数据", "数据要求", card.data_requirements),
        ("数据", "频率", card.frequency),
        ("预测目标", "预测周期", card.horizon),
        ("预测目标", "标签定义", card.label_definition),
        ("方法", "特征组", card.feature_groups),
        ("方法", "数据预处理", "未单独结构化（当前 MethodCard schema 尚无 preprocessing_protocol）"),
        ("方法", "模型", card.model_families),
        ("训练", "训练协议", card.training_protocol),
        ("回测", "数据切分", card.evaluation_protocol_type),
        ("回测", "评估说明", card.evaluation_protocol),
        ("回测", "评价指标", card.metrics),
        ("回测", "成本假设", card.cost_assumptions),
    ]
    result: list[dict[str, str]] = []
    for group, field, value in rows:
        display = _text(value)
        needs_decision = display == "未提取" or field == "数据预处理"
        result.append(
            {
                "环节": group,
                "字段": field,
                "方法卡内容": display,
                "状态": "需要人工决定" if needs_decision else "已提取",
            }
        )
    return result


def report_item_for_paper(report: dict[str, Any] | None, paper_id: str) -> dict[str, Any] | None:
    if not report:
        return None
    return next(
        (item for item in report.get("reports", []) if item.get("paper_spec", {}).get("paper_id") == paper_id),
        None,
    )


def reproduction_readiness(card: MethodCard, report_item: dict[str, Any] | None) -> dict[str, Any]:
    dataset = report_item.get("dataset_card", {}) if report_item else {}
    comparability = report_item.get("comparability_report", {}) if report_item else {}
    candidates = report_item.get("candidate_reports", []) if report_item else []
    best_id = report_item.get("best_candidate_id") if report_item else None
    best = next((item for item in candidates if item.get("candidate", {}).get("candidate_id") == best_id), None)
    manifest = best.get("manifest", {}) if best else {}

    experiment_type = classify_experiment_type(card)
    preprocessing_required = any(
        token in str(model).lower()
        for model in card.model_families
        for token in ("lstm", "transformer", "neural")
    )
    rows = [
        {
            "环节": "数据集",
            "论文/方法卡要求": _text(card.data_requirements),
            "本地实际配置": _text(dataset.get("source_name")) if report_item else "运行时生成 DatasetCard 后确认",
            "状态": "不一致" if comparability.get("strict_allowed") is False else "待比较",
        },
        {
            "环节": "资产与频率",
            "论文/方法卡要求": f"{_text(card.asset_universe)} / {_text(card.frequency)}",
            "本地实际配置": (
                f"{_text(dataset.get('asset_universe'))} / {_text(dataset.get('frequency'))}"
                if report_item
                else "运行前待确认"
            ),
            "状态": "不一致" if comparability.get("strict_allowed") is False else "待比较",
        },
        {
            "环节": "特征与预处理",
            "论文/方法卡要求": f"特征组: {_text(card.feature_groups)}；预处理: 未单独结构化",
            "本地实际配置": (
                f"{len(manifest.get('feature_columns') or [])} 个实际特征；无独立 preprocessing manifest"
                if manifest
                else "需要在执行协议中补充"
            ),
            "状态": "需要人工决定",
        },
        {
            "环节": "模型",
            "论文/方法卡要求": _text(card.model_families),
            "本地实际配置": _text(manifest.get("model_family")) if manifest else "候选生成后确认",
            "状态": "已执行" if manifest else "待生成候选",
        },
        {
            "环节": "切分与回测",
            "论文/方法卡要求": _text(card.evaluation_protocol),
            "本地实际配置": _text(manifest.get("split_method")) if manifest else _text(card.evaluation_protocol_type),
            "状态": "已执行" if manifest else "待运行",
        },
        {
            "环节": "交易成本",
            "论文/方法卡要求": "不适用" if experiment_type == "forecast_only" else _text(card.cost_assumptions),
            "本地实际配置": (
                "不适用"
                if experiment_type == "forecast_only"
                else _text(manifest.get("cost_model")) if manifest else "候选协议默认成本模型"
            ),
            "状态": "不适用" if experiment_type == "forecast_only" else "已执行" if manifest else "待运行",
        },
    ]

    reasons = list(comparability.get("blockers") or [])
    reasons.extend(str(item) for item in card.unknowns)
    if not card.evidence_spans or any(str(span.section).lower() in UNKNOWN_VALUES for span in card.evidence_spans):
        reasons.append("evidence spans 缺少可定位的原文章节")
    if preprocessing_required and not card.extraction_metadata.get("preprocessing_protocol"):
        reasons.append("深度模型的数据预处理协议尚未由论文证据确定")
    reasons = list(dict.fromkeys(reason for reason in reasons if reason))

    strict_ready = bool(comparability.get("strict_allowed") and not reasons)
    if strict_ready:
        mode = "strict_reproduction"
    elif report_item:
        proposed = comparability.get("proposed_mode")
        mode = "exploratory_real_data_reproduction" if proposed == "strict_reproduction" else proposed or "exploratory_real_data_reproduction"
    else:
        mode = "pending_comparability_check"
    return {"mode": mode, "strict_ready": strict_ready, "reasons": reasons, "rows": rows}

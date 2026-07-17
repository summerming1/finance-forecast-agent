from __future__ import annotations

import hashlib
import json
import math
import re
import time
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests

OPENALEX_WORKS_URL = "https://api.openalex.org/works"
CROSSREF_WORKS_URL = "https://api.crossref.org/works"
ARXIV_QUERY_URL = "https://export.arxiv.org/api/query"

DEFAULT_DISCOVERY_QUERIES = [
    "machine learning asset pricing",
    "machine learning stock return prediction",
    "deep learning stock market forecasting",
    "financial time series forecasting neural network",
    "machine learning volatility forecasting",
    "machine learning portfolio optimization",
    "reinforcement learning portfolio management",
    "machine learning algorithmic trading",
    "deep learning limit order book prediction",
    "machine learning cryptocurrency price prediction",
    "machine learning foreign exchange forecasting",
    "machine learning bond return prediction",
    "machine learning option pricing",
    "machine learning credit risk prediction",
    "machine learning bankruptcy prediction",
    "financial news stock prediction machine learning",
    "deep learning asset pricing",
    "cross sectional stock returns machine learning",
    "transformer financial forecasting",
    "machine learning macroeconomic forecasting",
]

ARXIV_FINANCE_CATEGORIES = ["q-fin.ST", "q-fin.PM", "q-fin.TR", "q-fin.CP", "q-fin.RM"]

TOP_FINANCE_VENUES = {
    "Journal of Finance",
    "Journal of Financial Economics",
    "Review of Financial Studies",
    "Journal of Financial and Quantitative Analysis",
    "Management Science",
    "Journal of Econometrics",
    "Econometrica",
}
HIGH_IMPACT_VENUES = {
    "European Journal of Operational Research",
    "Expert Systems with Applications",
    "Decision Support Systems",
    "Information Processing & Management",
    "ACM Transactions on Information Systems",
    "Quantitative Finance",
    "Journal of Banking & Finance",
    "Journal of Empirical Finance",
    "Journal of Financial Markets",
    "Financial Analysts Journal",
    "Neurocomputing",
    "Applied Soft Computing",
    "IEEE Access",
    "PLoS ONE",
    "Neural Computing and Applications",
    "AAAI Conference on Artificial Intelligence",
    "International Joint Conference on Artificial Intelligence",
    "Knowledge Discovery and Data Mining",
    "Neural Information Processing Systems",
    "International Conference on Machine Learning",
    "International Conference on Learning Representations",
}
REPOSITORY_VENUES = {
    "arXiv (Cornell University)",
    "National Bureau of Economic Research",
    "SSRN Electronic Journal",
}

FINANCE_TERMS = {
    "asset pricing",
    "bankruptcy",
    "bitcoin",
    "bond market",
    "bond return",
    "corporate bond",
    "defaulted bond",
    "interbank bond",
    "credit risk",
    "cryptocurrency",
    "exchange rate",
    "financial",
    "foreign exchange",
    "hedging",
    "limit order book",
    "option pricing",
    "portfolio",
    "return prediction",
    "stock",
    "trading",
    "volatility",
}
METHOD_TERMS = {
    "artificial intelligence",
    "boosting",
    "deep learning",
    "forecast",
    "genetic algorithm",
    "gradient boosting",
    "lstm",
    "machine learning",
    "neural network",
    "prediction",
    "random forest",
    "reinforcement learning",
    "support vector",
    "transformer",
}
EXCLUDED_TITLE_TERMS = {
    "bibliometric",
    "literature review",
    "systematic review",
    "survey",
    "review of",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _abstract_from_inverted_index(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    positions = sorted((position, word) for word, values in index.items() for position in values)
    return " ".join(word for _, word in positions)


def _normalized_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return value[:96] or "paper"


def _matching_terms(text: str, terms: Iterable[str]) -> list[str]:
    lowered = text.lower()
    return sorted(
        term
        for term in terms
        if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", lowered)
    )


def classify_task(text: str) -> str:
    lowered = text.lower()
    routes = [
        ("portfolio_rl", ("reinforcement learning", "portfolio management", "portfolio allocation")),
        ("limit_order_book", ("limit order book", "high-frequency", "high frequency")),
        ("credit_default", ("credit risk", "default prediction", "bankruptcy")),
        ("derivative_pricing", ("option pricing", "derivative pricing")),
        ("volatility_forecast", ("volatility", "garch")),
        ("cross_sectional_asset_pricing", ("asset pricing", "cross-sectional", "cross sectional")),
        ("signal_backtest", ("algorithmic trading", "trading strategy", "market timing")),
        ("crypto_forecast", ("bitcoin", "cryptocurrency", "crypto")),
        ("fx_forecast", ("foreign exchange", "exchange rate", "forex")),
        ("forecast_only", ("forecast", "prediction", "predicting")),
    ]
    for route, tokens in routes:
        if any(token in lowered for token in tokens):
            return route
    return "financial_prediction_other"


def classify_methods(text: str) -> list[str]:
    aliases = [
        ("transformer", ("transformer", "attention")),
        ("reinforcement_learning", ("reinforcement learning", "policy gradient", "q-learning")),
        ("lstm", ("lstm", "long short-term memory")),
        ("cnn", ("convolutional neural", "cnn")),
        ("deep_neural_network", ("deep learning", "deep neural", "autoencoder")),
        ("gradient_boosting", ("gradient boosting", "xgboost", "lightgbm", "boosted tree")),
        ("random_forest", ("random forest",)),
        ("support_vector_machine", ("support vector", "svm", "svr")),
        ("genetic_algorithm", ("genetic algorithm",)),
        ("gaussian_process", ("gaussian process",)),
        ("linear_or_factor_model", ("linear regression", "factor model")),
    ]
    lowered = text.lower()
    return [family for family, tokens in aliases if any(token in lowered for token in tokens)]


def venue_tier(venue: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", venue.lower()).strip()
    top_names = {
        re.sub(r"[^a-z0-9]+", " ", item.lower()).strip()
        for item in TOP_FINANCE_VENUES
    }
    high_names = {
        re.sub(r"[^a-z0-9]+", " ", item.lower()).strip()
        for item in HIGH_IMPACT_VENUES
    }
    if normalized.removeprefix("the ") in {item.removeprefix("the ") for item in top_names}:
        return "top_finance_or_econometrics"
    if normalized in high_names or any(
        token in normalized
        for token in (
            "aaai conference on artificial intelligence",
            "journal of financial econometrics",
        )
    ):
        return "high_impact_peer_reviewed"
    if venue in REPOSITORY_VENUES:
        return "influential_working_paper_or_preprint"
    return "other_peer_reviewed_or_repository"


@dataclass
class LiteratureRecord:
    paper_id: str
    openalex_id: str
    title: str
    authors: list[str]
    publication_year: int | None
    venue: str
    venue_tier: str
    doi: str | None
    cited_by_count: int
    abstract: str
    task_category: str
    method_tags: list[str]
    landing_url: str | None
    pdf_candidates: list[str]
    oa_status: str
    license: str | None
    source_version: str | None
    relevance_score: float
    strict_feasibility: str
    feasibility_reasons: list[str]
    local_pdf: str | None = None
    pdf_sha256: str | None = None
    pdf_bytes: int | None = None
    download_status: str = "not_attempted"
    download_error: str | None = None
    downloaded_from: str | None = None
    acquired_at: str | None = None
    redistribution_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LiteratureRecord":
        return cls(**payload)


def _source(record: dict[str, Any]) -> dict[str, Any]:
    primary = record.get("primary_location") or {}
    return primary.get("source") or {}


def _candidate_pdf_urls(record: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    external = record.get("ids") or {}
    arxiv_id = external.get("arxiv")
    if arxiv_id:
        candidates.append(str(arxiv_id).replace("https://arxiv.org/abs/", "https://arxiv.org/pdf/"))
    for location in [record.get("best_oa_location"), *(record.get("locations") or [])]:
        location = location or {}
        if location.get("is_oa") and location.get("pdf_url"):
            candidates.append(str(location["pdf_url"]))
    return list(dict.fromkeys(candidates))


def record_from_openalex(work: dict[str, Any]) -> LiteratureRecord | None:
    title = str(work.get("display_name") or "").strip()
    abstract = _abstract_from_inverted_index(work.get("abstract_inverted_index"))
    searchable = f"{title} {abstract}"
    finance_hits = _matching_terms(searchable, FINANCE_TERMS)
    method_hits = _matching_terms(searchable, METHOD_TERMS)
    if not finance_hits or not method_hits:
        return None
    if _matching_terms(title, EXCLUDED_TITLE_TERMS):
        return None
    source = _source(work)
    venue = str(source.get("display_name") or "Unknown")
    tier = venue_tier(venue)
    title_finance_hits = _matching_terms(title, FINANCE_TERMS)
    title_method_hits = _matching_terms(title, METHOD_TERMS)
    if tier != "top_finance_or_econometrics" and (
        not title_finance_hits or not title_method_hits
    ):
        return None
    citations = int(work.get("cited_by_count") or 0)
    tier_score = {
        "top_finance_or_econometrics": 45,
        "high_impact_peer_reviewed": 25,
        "influential_working_paper_or_preprint": 16,
        "other_peer_reviewed_or_repository": 6,
    }[tier]
    pdf_candidates = _candidate_pdf_urls(work)
    score = round(
        tier_score
        + 8 * math.log10(citations + 1)
        + 2 * len(finance_hits)
        + len(method_hits)
        + (8 if pdf_candidates else 0),
        3,
    )
    best = work.get("best_oa_location") or {}
    license_name = best.get("license")
    reasons = []
    if pdf_candidates:
        reasons.append("open-access full-text candidate is available")
    else:
        reasons.append("no direct open-access PDF candidate")
    if citations >= 100:
        reasons.append("high citation signal")
    if tier == "top_finance_or_econometrics":
        reasons.append("top finance/econometrics venue")
    methods = classify_methods(searchable)
    if methods:
        reasons.append("machine-learning method family is identifiable")
    feasibility = "candidate_needs_source_audit" if pdf_candidates and methods else "metadata_only"
    openalex_id = str(work.get("id") or "")
    suffix = openalex_id.rsplit("/", 1)[-1] or hashlib.sha256(title.encode()).hexdigest()[:12]
    doi = str(work.get("doi") or "") or None
    return LiteratureRecord(
        paper_id=f"openalex_{suffix.lower()}",
        openalex_id=openalex_id,
        title=title,
        authors=[
            str((authorship.get("author") or {}).get("display_name") or "Unknown")
            for authorship in work.get("authorships") or []
        ],
        publication_year=work.get("publication_year"),
        venue=venue,
        venue_tier=tier,
        doi=doi,
        cited_by_count=citations,
        abstract=abstract,
        task_category=classify_task(searchable),
        method_tags=methods,
        landing_url=best.get("landing_page_url") or doi or openalex_id,
        pdf_candidates=pdf_candidates,
        oa_status=str((work.get("open_access") or {}).get("oa_status") or "unknown"),
        license=license_name,
        source_version=best.get("version"),
        relevance_score=score,
        strict_feasibility=feasibility,
        feasibility_reasons=reasons,
        redistribution_allowed=bool(license_name and str(license_name).lower().startswith("cc")),
    )


class OpenAlexLiteratureClient:
    def __init__(self, *, mailto: str | None = None, timeout: int = 30):
        self.mailto = mailto
        self.timeout = timeout

    def discover(
        self,
        queries: Iterable[str] = DEFAULT_DISCOVERY_QUERIES,
        *,
        per_query: int = 50,
    ) -> list[LiteratureRecord]:
        by_title: dict[str, LiteratureRecord] = {}
        for query in queries:
            params = {
                "filter": (
                    f"title_and_abstract.search:{query},"
                    "from_publication_date:2000-01-01,has_abstract:true"
                ),
                "sort": "cited_by_count:desc",
                "per-page": min(per_query, 100),
            }
            if self.mailto:
                params["mailto"] = self.mailto
            response = None
            for attempt in range(5):
                response = requests.get(
                    OPENALEX_WORKS_URL,
                    params=params,
                    headers={"User-Agent": "finance-forecast-agent/0.2"},
                    timeout=self.timeout,
                )
                if response.status_code != 429:
                    break
                retry_after = float(response.headers.get("retry-after") or 1)
                if retry_after > 60:
                    raise RuntimeError(
                        "OpenAlex daily anonymous budget is exhausted; use Crossref/arXiv fallback "
                        "or configure OPENALEX_API_KEY"
                    )
                time.sleep(max(retry_after, 0.5 * (attempt + 1)))
            assert response is not None
            response.raise_for_status()
            for work in response.json().get("results", []):
                record = record_from_openalex(work)
                if record is None:
                    continue
                key = _normalized_title(record.title)
                previous = by_title.get(key)
                if previous is None or record.relevance_score > previous.relevance_score:
                    by_title[key] = record
            time.sleep(0.15)
        return sorted(by_title.values(), key=lambda item: item.relevance_score, reverse=True)


def _published_year(item: dict[str, Any]) -> int | None:
    for key in ("published-print", "published-online", "published", "issued", "created"):
        parts = ((item.get(key) or {}).get("date-parts") or [[]])[0]
        if parts:
            return int(parts[0])
    return None


def record_from_crossref(item: dict[str, Any]) -> LiteratureRecord | None:
    title = str((item.get("title") or [""])[0]).strip()
    abstract = re.sub(r"<[^>]+>", " ", str(item.get("abstract") or ""))
    searchable = f"{title} {abstract}"
    finance_hits = _matching_terms(searchable, FINANCE_TERMS)
    method_hits = _matching_terms(searchable, METHOD_TERMS)
    if not finance_hits or not method_hits or _matching_terms(title, EXCLUDED_TITLE_TERMS):
        return None
    venue = str((item.get("container-title") or ["Unknown"])[0] or "Unknown")
    tier = venue_tier(venue)
    if tier != "top_finance_or_econometrics" and (
        not _matching_terms(title, FINANCE_TERMS) or not _matching_terms(title, METHOD_TERMS)
    ):
        return None
    doi_value = str(item.get("DOI") or "").strip() or None
    pdf_candidates = [
        str(link["URL"])
        for link in item.get("link") or []
        if link.get("URL")
        and (
            "pdf" in str(link.get("content-type") or "").lower()
            or str(link.get("URL")).lower().endswith(".pdf")
        )
    ]
    license_entries = item.get("license") or []
    license_url = str(license_entries[0].get("URL")) if license_entries else None
    citations = int(item.get("is-referenced-by-count") or 0)
    tier_score = {
        "top_finance_or_econometrics": 45,
        "high_impact_peer_reviewed": 25,
        "influential_working_paper_or_preprint": 16,
        "other_peer_reviewed_or_repository": 6,
    }[tier]
    score = round(
        tier_score
        + 8 * math.log10(citations + 1)
        + 2 * len(finance_hits)
        + len(method_hits)
        + (8 if pdf_candidates else 0),
        3,
    )
    methods = classify_methods(searchable)
    identifier = doi_value or hashlib.sha256(title.encode()).hexdigest()[:16]
    reasons = ["Crossref bibliographic metadata is available"]
    if pdf_candidates:
        reasons.append("publisher supplied a PDF link; access still requires validation")
    if methods:
        reasons.append("machine-learning method family is identifiable")
    return LiteratureRecord(
        paper_id=f"crossref_{_slug(identifier)}",
        openalex_id="",
        title=title,
        authors=[
            " ".join(filter(None, [str(author.get("given") or ""), str(author.get("family") or "")])).strip()
            for author in item.get("author") or []
        ],
        publication_year=_published_year(item),
        venue=venue,
        venue_tier=tier,
        doi=f"https://doi.org/{doi_value}" if doi_value else None,
        cited_by_count=citations,
        abstract=abstract.strip(),
        task_category=classify_task(searchable),
        method_tags=methods,
        landing_url=str(item.get("URL") or (f"https://doi.org/{doi_value}" if doi_value else "")) or None,
        pdf_candidates=list(dict.fromkeys(pdf_candidates)),
        oa_status="crossref_link_unverified" if pdf_candidates else "unknown",
        license=license_url,
        source_version="publishedVersion",
        relevance_score=score,
        strict_feasibility="candidate_needs_source_audit" if pdf_candidates and methods else "metadata_only",
        feasibility_reasons=reasons,
        redistribution_allowed=bool(license_url and "creativecommons.org" in license_url.lower()),
    )


class CrossrefLiteratureClient:
    def __init__(self, *, timeout: int = 30):
        self.timeout = timeout

    def discover(
        self,
        queries: Iterable[str] = DEFAULT_DISCOVERY_QUERIES,
        *,
        per_query: int = 50,
    ) -> list[LiteratureRecord]:
        by_title: dict[str, LiteratureRecord] = {}
        for query in queries:
            response = requests.get(
                CROSSREF_WORKS_URL,
                params={
                    "query.title": query,
                    "filter": "from-pub-date:2000-01-01",
                    "rows": min(per_query, 100),
                    "select": (
                        "DOI,title,author,published,published-print,published-online,"
                        "container-title,is-referenced-by-count,URL,link,type,abstract,license"
                    ),
                },
                headers={"User-Agent": "finance-forecast-agent/0.2"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            for item in response.json().get("message", {}).get("items", []):
                record = record_from_crossref(item)
                if record is None:
                    continue
                key = _normalized_title(record.title)
                previous = by_title.get(key)
                if previous is None or record.relevance_score > previous.relevance_score:
                    by_title[key] = record
            time.sleep(0.1)
        return sorted(by_title.values(), key=lambda item: item.relevance_score, reverse=True)


def _arxiv_text(entry: ET.Element, name: str) -> str:
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    node = entry.find(f"atom:{name}", namespace)
    return " ".join((node.text or "").split()) if node is not None else ""


class ArxivLiteratureClient:
    def __init__(self, *, timeout: int = 30):
        self.timeout = timeout

    def discover(self, *, per_category: int = 40) -> list[LiteratureRecord]:
        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        by_title: dict[str, LiteratureRecord] = {}
        for category in ARXIV_FINANCE_CATEGORIES:
            response = requests.get(
                ARXIV_QUERY_URL,
                params={
                    "search_query": f"cat:{category} AND (all:machine OR all:deep OR all:neural)",
                    "start": 0,
                    "max_results": per_category,
                    "sortBy": "relevance",
                },
                headers={"User-Agent": "finance-forecast-agent/0.2"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            root = ET.fromstring(response.content)
            for entry in root.findall("atom:entry", namespace):
                title = _arxiv_text(entry, "title")
                abstract = _arxiv_text(entry, "summary")
                searchable = f"{title} {abstract}"
                if not _matching_terms(searchable, FINANCE_TERMS) or not _matching_terms(
                    searchable, METHOD_TERMS
                ):
                    continue
                if _matching_terms(title, EXCLUDED_TITLE_TERMS):
                    continue
                if not _matching_terms(title, FINANCE_TERMS) or not _matching_terms(
                    title, METHOD_TERMS
                ):
                    continue
                entry_id = _arxiv_text(entry, "id")
                arxiv_id = entry_id.rsplit("/", 1)[-1]
                authors = [
                    _arxiv_text(author, "name")
                    for author in entry.findall("atom:author", namespace)
                ]
                published = _arxiv_text(entry, "published")
                methods = classify_methods(searchable)
                record = LiteratureRecord(
                    paper_id=f"arxiv_{_slug(arxiv_id)}",
                    openalex_id="",
                    title=title,
                    authors=authors,
                    publication_year=int(published[:4]) if published[:4].isdigit() else None,
                    venue="arXiv (Cornell University)",
                    venue_tier="influential_working_paper_or_preprint",
                    doi=None,
                    cited_by_count=0,
                    abstract=abstract,
                    task_category=classify_task(searchable),
                    method_tags=methods,
                    landing_url=entry_id,
                    pdf_candidates=[f"https://arxiv.org/pdf/{arxiv_id}"],
                    oa_status="green",
                    license=None,
                    source_version="submittedVersion",
                    relevance_score=round(30 + 2 * len(methods), 3),
                    strict_feasibility="candidate_needs_source_audit" if methods else "metadata_only",
                    feasibility_reasons=[
                        "open-access arXiv PDF is available",
                        "official code and original data still require audit",
                    ],
                    redistribution_allowed=False,
                )
                key = _normalized_title(record.title)
                by_title.setdefault(key, record)
            time.sleep(0.4)
        return sorted(by_title.values(), key=lambda item: item.relevance_score, reverse=True)


def discover_literature(
    *,
    queries: Iterable[str] = DEFAULT_DISCOVERY_QUERIES,
    per_query: int = 50,
    include_openalex: bool = True,
) -> tuple[list[LiteratureRecord], list[str]]:
    records: list[LiteratureRecord] = []
    errors: list[str] = []
    if include_openalex:
        try:
            records.extend(OpenAlexLiteratureClient().discover(queries, per_query=per_query))
        except Exception as exc:
            errors.append(f"OpenAlex: {exc}")
    for label, callback in (
        ("Crossref", lambda: CrossrefLiteratureClient().discover(queries, per_query=per_query)),
        ("arXiv", lambda: ArxivLiteratureClient().discover(per_category=per_query)),
    ):
        try:
            records.extend(callback())
        except Exception as exc:
            errors.append(f"{label}: {exc}")
    by_title: dict[str, LiteratureRecord] = {}
    for record in records:
        key = _normalized_title(record.title)
        previous = by_title.get(key)
        if previous is None:
            by_title[key] = record
            continue
        previous_has_pdf = bool(previous.pdf_candidates)
        record_has_pdf = bool(record.pdf_candidates)
        formal = record
        alternate = previous
        if previous.venue_tier == "top_finance_or_econometrics" or (
            previous.relevance_score >= record.relevance_score and previous.venue_tier != "influential_working_paper_or_preprint"
        ):
            formal, alternate = previous, record
        if formal.venue_tier == "influential_working_paper_or_preprint" and record_has_pdf and not previous_has_pdf:
            formal, alternate = record, previous
        formal.pdf_candidates = list(dict.fromkeys([*formal.pdf_candidates, *alternate.pdf_candidates]))
        formal.feasibility_reasons = list(
            dict.fromkeys([*formal.feasibility_reasons, *alternate.feasibility_reasons])
        )
        by_title[key] = formal
    return sorted(by_title.values(), key=lambda item: item.relevance_score, reverse=True), errors


def curate_literature_records(
    records: Iterable[LiteratureRecord],
) -> tuple[list[LiteratureRecord], list[LiteratureRecord]]:
    accepted: list[LiteratureRecord] = []
    rejected: list[LiteratureRecord] = []
    for record in records:
        searchable = f"{record.title} {record.abstract}"
        tier = venue_tier(record.venue)
        finance_hits = _matching_terms(searchable, FINANCE_TERMS)
        method_hits = _matching_terms(searchable, METHOD_TERMS)
        title_finance = _matching_terms(record.title, FINANCE_TERMS)
        title_method = _matching_terms(record.title, METHOD_TERMS)
        valid = bool(finance_hits and method_hits)
        if tier != "top_finance_or_econometrics":
            valid = valid and bool(title_finance and title_method)
        if not valid or _matching_terms(record.title, EXCLUDED_TITLE_TERMS):
            record.download_status = "excluded_irrelevant"
            record.download_error = "failed finance-prediction relevance audit"
            rejected.append(record)
            continue
        record.venue_tier = tier
        record.task_category = classify_task(searchable)
        record.method_tags = classify_methods(searchable)
        accepted.append(record)
    return accepted, rejected


def merge_literature_records(records: Iterable[LiteratureRecord]) -> list[LiteratureRecord]:
    by_title: dict[str, LiteratureRecord] = {}
    for record in records:
        key = _normalized_title(record.title)
        previous = by_title.get(key)
        if previous is None:
            by_title[key] = record
            continue
        downloaded = previous if previous.download_status == "downloaded_open_access" else None
        if record.download_status == "downloaded_open_access":
            downloaded = record
        formal = max(
            [previous, record],
            key=lambda item: (
                item.venue_tier == "top_finance_or_econometrics",
                item.venue_tier == "high_impact_peer_reviewed",
                item.relevance_score,
            ),
        )
        alternate = record if formal is previous else previous
        formal.pdf_candidates = list(dict.fromkeys([*formal.pdf_candidates, *alternate.pdf_candidates]))
        formal.feasibility_reasons = list(
            dict.fromkeys([*formal.feasibility_reasons, *alternate.feasibility_reasons])
        )
        if downloaded is not None and formal is not downloaded:
            formal.local_pdf = downloaded.local_pdf
            formal.pdf_sha256 = downloaded.pdf_sha256
            formal.pdf_bytes = downloaded.pdf_bytes
            formal.download_status = downloaded.download_status
            formal.download_error = downloaded.download_error
            formal.downloaded_from = downloaded.downloaded_from
            formal.acquired_at = downloaded.acquired_at
        by_title[key] = formal
    return sorted(by_title.values(), key=lambda item: item.relevance_score, reverse=True)


def download_open_access_pdf(
    record: LiteratureRecord,
    output_dir: str | Path,
    *,
    timeout: int = 45,
    max_bytes: int = 60_000_000,
) -> LiteratureRecord:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    for url in record.pdf_candidates:
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "finance-forecast-agent/0.2 research-reproduction"},
                timeout=timeout,
                stream=True,
                allow_redirects=True,
            )
            if response.status_code != 200:
                errors.append(f"{url}: HTTP {response.status_code}")
                continue
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(chunk_size=128 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError(f"PDF exceeds {max_bytes} bytes")
                chunks.append(chunk)
            content = b"".join(chunks)
            if not content.startswith(b"%PDF-"):
                content_type = response.headers.get("content-type", "unknown")
                errors.append(f"{url}: not a PDF ({content_type})")
                continue
            filename = f"{record.paper_id}_{_slug(record.title)[:48]}.pdf"
            path = output_dir / filename
            path.write_bytes(content)
            record.local_pdf = str(path)
            record.pdf_sha256 = hashlib.sha256(content).hexdigest()
            record.pdf_bytes = len(content)
            record.download_status = "downloaded_open_access"
            record.download_error = None
            record.downloaded_from = str(response.url)
            record.acquired_at = _utc_now()
            return record
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    record.download_status = "blocked_or_failed"
    record.download_error = " | ".join(errors) if errors else "no open-access PDF candidate"
    record.acquired_at = _utc_now()
    return record


def corpus_statistics(records: Iterable[LiteratureRecord]) -> dict[str, Any]:
    rows = list(records)
    downloaded = [row for row in rows if row.download_status == "downloaded_open_access"]
    return {
        "paper_count": len(rows),
        "downloaded_pdf_count": len(downloaded),
        "downloaded_bytes": sum(row.pdf_bytes or 0 for row in downloaded),
        "top_finance_or_econometrics_count": sum(
            row.venue_tier == "top_finance_or_econometrics" for row in rows
        ),
        "high_impact_peer_reviewed_count": sum(
            row.venue_tier == "high_impact_peer_reviewed" for row in rows
        ),
        "working_paper_or_preprint_count": sum(
            row.venue_tier == "influential_working_paper_or_preprint" for row in rows
        ),
        "total_citations_signal": sum(row.cited_by_count for row in rows),
        "median_publication_year": sorted(
            row.publication_year for row in rows if row.publication_year is not None
        )[len([row for row in rows if row.publication_year is not None]) // 2]
        if any(row.publication_year is not None for row in rows)
        else None,
        "task_categories": dict(Counter(row.task_category for row in rows).most_common()),
        "method_tags": dict(Counter(tag for row in rows for tag in row.method_tags).most_common()),
        "venue_tiers": dict(Counter(row.venue_tier for row in rows).most_common()),
        "oa_statuses": dict(Counter(row.oa_status for row in rows).most_common()),
        "download_statuses": dict(Counter(row.download_status for row in rows).most_common()),
        "downloaded_venue_tiers": dict(
            Counter(row.venue_tier for row in downloaded).most_common()
        ),
        "downloaded_task_categories": dict(
            Counter(row.task_category for row in downloaded).most_common()
        ),
    }


def save_corpus(root: str | Path, records: Iterable[LiteratureRecord]) -> tuple[Path, Path]:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    rows = list(records)
    manifest = root / "literature_corpus.json"
    stats = root / "literature_statistics.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "literature_corpus_v1",
                "generated_at": _utc_now(),
                "records": [row.to_dict() for row in rows],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    stats.write_text(
        json.dumps(corpus_statistics(rows), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest, stats


def load_corpus(path: str | Path) -> list[LiteratureRecord]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [LiteratureRecord.from_dict(row) for row in payload.get("records", [])]

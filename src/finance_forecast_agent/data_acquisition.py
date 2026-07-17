from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import requests

from .method_cards import MethodCard

SourceType = Literal[
    "direct_open_url",
    "fred_series",
    "fama_french_library",
    "yahoo_chart",
    "local_existing",
    "restricted_manual",
]

TRUSTED_DATA_HOSTS = {
    "fred.stlouisfed.org",
    "mba.tuck.dartmouth.edu",
    "query1.finance.yahoo.com",
    "raw.githubusercontent.com",
    "stooq.com",
}
RESTRICTED_DATA_TOKENS = {
    "bloomberg",
    "compustat",
    "crsp",
    "datastream",
    "optionmetrics",
    "refinitiv",
    "taq",
    "wrds",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _identifier(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()[:96]


@dataclass
class DataRequest:
    request_id: str
    dataset_id: str
    source_type: SourceType
    paper_id: str | None = None
    source_url: str | None = None
    symbol_or_series: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    frequency: str | None = None
    expected_fields: list[str] = field(default_factory=list)
    license_status: str = "unknown"
    requested_by: str = "user"
    rationale: str = ""
    status: str = "pending"
    blockers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DataRequest":
        return cls(**payload)


@dataclass
class DataAcquisitionResult:
    request: DataRequest
    status: str
    local_path: str | None
    sha256: str | None
    byte_count: int
    content_type: str | None
    detected_fields: list[str]
    missing_expected_fields: list[str]
    acquired_at: str
    source_final_url: str | None
    error: str | None = None
    schema_version: str = "data_acquisition_result_v1"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["request"] = self.request.to_dict()
        return payload


def _epoch(date_value: str | None, fallback: int) -> int:
    if not date_value:
        return fallback
    return int(datetime.fromisoformat(date_value).replace(tzinfo=timezone.utc).timestamp())


def resolved_source_url(request: DataRequest) -> str | None:
    if request.source_type == "fred_series" and request.symbol_or_series:
        return f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={request.symbol_or_series}"
    if request.source_type == "fama_french_library" and request.symbol_or_series:
        filename = request.symbol_or_series
        if not filename.lower().endswith(".zip"):
            filename += "_CSV.zip"
        return "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/" + filename
    if request.source_type == "yahoo_chart" and request.symbol_or_series:
        period1 = _epoch(request.start_date, 0)
        period2 = _epoch(request.end_date, int(datetime.now(timezone.utc).timestamp()))
        interval = request.frequency or "1d"
        return (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{request.symbol_or_series}"
            f"?period1={period1}&period2={period2}&interval={interval}&events=history"
        )
    return request.source_url


def _validate_remote_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Only HTTPS data sources are allowed")
    hostname = (parsed.hostname or "").lower()
    if hostname not in TRUSTED_DATA_HOSTS:
        raise ValueError(f"Data host is not allow-listed: {hostname}")


def _detected_fields(content: bytes, content_type: str | None, suffix: str) -> list[str]:
    lowered_type = str(content_type or "").lower()
    if "json" in lowered_type or suffix == ".json":
        try:
            payload = json.loads(content.decode("utf-8"))
            if isinstance(payload, dict):
                return sorted(str(key) for key in payload)
        except Exception:
            return []
    if "csv" in lowered_type or suffix in {".csv", ".txt"}:
        try:
            sample = content[:100_000].decode("utf-8-sig", errors="replace")
            dialect = csv.Sniffer().sniff(sample[:4096], delimiters=",;\t|")
            return [str(item).strip() for item in next(csv.reader(io.StringIO(sample), dialect))]
        except Exception:
            return []
    return []


def _extension(url: str, content_type: str | None) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".csv", ".json", ".txt", ".zip", ".gz", ".parquet"}:
        return suffix
    lowered = str(content_type or "").lower()
    if "json" in lowered:
        return ".json"
    if "csv" in lowered:
        return ".csv"
    if "zip" in lowered:
        return ".zip"
    return ".bin"


def acquire_data_request(
    request: DataRequest,
    project_dir: str | Path,
    *,
    timeout: int = 45,
    max_bytes: int = 250_000_000,
) -> DataAcquisitionResult:
    acquired_at = _utc_now()
    if request.source_type == "restricted_manual" or request.blockers:
        result = DataAcquisitionResult(
            request=request,
            status="blocked",
            local_path=None,
            sha256=None,
            byte_count=0,
            content_type=None,
            detected_fields=[],
            missing_expected_fields=list(request.expected_fields),
            acquired_at=acquired_at,
            source_final_url=request.source_url,
            error="; ".join(request.blockers) or "restricted data requires user-provided licensed access",
        )
        save_data_acquisition_result(project_dir, result)
        return result
    if request.source_type == "local_existing":
        path = Path(str(request.source_url or ""))
        if not path.exists():
            error = f"local source does not exist: {path}"
            result = DataAcquisitionResult(
                request, "failed", None, None, 0, None, [], request.expected_fields, acquired_at, None, error
            )
            save_data_acquisition_result(project_dir, result)
            return result
        content = path.read_bytes()
        fields = _detected_fields(content, None, path.suffix.lower())
        result = DataAcquisitionResult(
            request=request,
            status="available_local",
            local_path=str(path),
            sha256=hashlib.sha256(content).hexdigest(),
            byte_count=len(content),
            content_type=None,
            detected_fields=fields,
            missing_expected_fields=[field for field in request.expected_fields if field not in fields],
            acquired_at=acquired_at,
            source_final_url=str(path),
        )
        save_data_acquisition_result(project_dir, result)
        return result
    url = resolved_source_url(request)
    if not url:
        raise ValueError("Data request has no resolvable source URL")
    _validate_remote_url(url)
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "finance-forecast-agent/0.2 data-acquisition"},
            timeout=timeout,
            stream=True,
            allow_redirects=True,
        )
        response.raise_for_status()
        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_content(chunk_size=128 * 1024):
            if not chunk:
                continue
            size += len(chunk)
            if size > max_bytes:
                raise ValueError(f"dataset exceeds {max_bytes} bytes")
            chunks.append(chunk)
        content = b"".join(chunks)
        content_type = response.headers.get("content-type")
        if content.lstrip().lower().startswith((b"<!doctype html", b"<html")):
            raise ValueError("source returned HTML instead of a dataset")
        suffix = _extension(str(response.url), content_type)
        root = Path(project_dir) / "data" / "acquired" / _identifier(request.dataset_id)
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"snapshot{suffix}"
        path.write_bytes(content)
        fields = _detected_fields(content, content_type, suffix)
        missing = [field for field in request.expected_fields if field not in fields]
        status = "downloaded" if not missing else "downloaded_schema_review_required"
        result = DataAcquisitionResult(
            request=request,
            status=status,
            local_path=str(path),
            sha256=hashlib.sha256(content).hexdigest(),
            byte_count=len(content),
            content_type=content_type,
            detected_fields=fields,
            missing_expected_fields=missing,
            acquired_at=acquired_at,
            source_final_url=str(response.url),
        )
    except Exception as exc:
        result = DataAcquisitionResult(
            request=request,
            status="failed",
            local_path=None,
            sha256=None,
            byte_count=0,
            content_type=None,
            detected_fields=[],
            missing_expected_fields=list(request.expected_fields),
            acquired_at=acquired_at,
            source_final_url=url,
            error=str(exc),
        )
    save_data_acquisition_result(project_dir, result)
    return result


def save_data_acquisition_result(project_dir: str | Path, result: DataAcquisitionResult) -> Path:
    root = Path(project_dir) / "data_requests"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{_identifier(result.request.request_id)}.json"
    path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_data_acquisition_results(project_dir: str | Path) -> list[dict[str, Any]]:
    root = Path(project_dir) / "data_requests"
    if not root.exists():
        return []
    rows = []
    for path in sorted(root.glob("*.json")):
        try:
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return rows


def requests_from_method_card(card: MethodCard, project_dir: str | Path) -> list[DataRequest]:
    text = " ".join(
        [card.title, card.target_asset, *card.asset_universe, *card.data_requirements]
    ).lower()
    restricted = sorted(token for token in RESTRICTED_DATA_TOKENS if token in text)
    request_id = f"{card.paper_id}_auto_data"
    if restricted:
        return [
            DataRequest(
                request_id=request_id,
                dataset_id=f"{card.paper_id}_restricted_original",
                source_type="restricted_manual",
                paper_id=card.paper_id,
                expected_fields=list(card.feature_groups),
                license_status="paid_or_restricted",
                requested_by="method_card_auto",
                rationale="MethodCard names a restricted commercial dataset.",
                status="blocked",
                blockers=[
                    "licensed access required for: " + ", ".join(restricted),
                    "automatic download is prohibited",
                ],
            )
        ]
    if "exchange-rate" in text or "exchange rate" in text:
        path = Path(project_dir) / "data" / "external" / "exchange_rate" / "exchange_rate.txt"
        return [
            DataRequest(
                request_id=request_id,
                dataset_id="exchange_rate_official_snapshot",
                source_type="local_existing",
                paper_id=card.paper_id,
                source_url=str(path),
                frequency=card.frequency,
                license_status="research_dataset_local_snapshot",
                requested_by="method_card_auto",
                rationale="MethodCard requires the Exchange-Rate benchmark dataset.",
            )
        ]
    if "fama" in text and "french" in text:
        return [
            DataRequest(
                request_id=request_id,
                dataset_id=f"{card.paper_id}_fama_french_factors",
                source_type="fama_french_library",
                paper_id=card.paper_id,
                symbol_or_series="F-F_Research_Data_Factors",
                license_status="public_research_terms_review_required",
                requested_by="method_card_auto",
                rationale="MethodCard references Fama-French factors.",
            )
        ]
    symbol = "AAPL" if "aapl" in text or "apple" in text else "^GSPC"
    return [
        DataRequest(
            request_id=request_id,
            dataset_id=f"{card.paper_id}_{_identifier(symbol)}_exploratory",
            source_type="yahoo_chart",
            paper_id=card.paper_id,
            symbol_or_series=symbol,
            start_date=card.required_start_date,
            end_date=card.required_end_date,
            frequency="1d",
            expected_fields=["chart"],
            license_status="provider_terms_review_required",
            requested_by="method_card_auto",
            rationale=(
                "No original public dataset connector was identified; Yahoo market data is proposed "
                "for exploratory reproduction only."
            ),
        )
    ]

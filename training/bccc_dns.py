"""Safe BCCC DNS-EXF adapter using Custodian's shared runtime feature extractor."""

from __future__ import annotations

import ast
import hashlib
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from custodian.core.enums import ThreatClass
from custodian.core.schemas import CapabilityProfile
from custodian.features.dns import DNSFeatureExtractor
from training.colab import sha256_file
from training.prepare import feature_rows

BCCC_DATASET_HANDLE = "bcccdatasets/malicious-dns-and-attacks-bccc-cic-bell-dns-2024"
BCCC_EXF_PREFIX = "BCCC-CIC-Bell-DNS-2024/BCCC-CIC-Bell-DNS-EXF"
BCCC_REQUIRED_COLUMNS = (
    "flow_id",
    "timestamp",
    "src_ip",
    "dst_ip",
    "src_port",
    "dst_port",
    "dns_domain_name",
    "query_resource_record_type",
    "label",
)
BCCC_INVALID_DOMAIN_SENTINELS = frozenset({"malformed-packet", "not a dns flow"})


@dataclass(frozen=True, slots=True)
class BCCCAdaptationResult:
    """Prepared shared-feature rows plus non-payload dataset provenance."""

    table: pd.DataFrame
    sources: tuple[dict[str, Any], ...]


def _target_label(value: object) -> str:
    label = str(value).strip()
    folded = label.casefold()
    if folded == "benign":
        return ThreatClass.BENIGN_DNS.value
    if folded.startswith(("light-", "heavy-")):
        return ThreatClass.DNS_TUNNEL.value
    raise ValueError(f"unsupported BCCC DNS-EXF label: {label!r}")


def _query_type(value: object) -> int | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text or text in {"[]", "{}", "nan", "None"}:
        return None
    try:
        parsed = ast.literal_eval(text)
    except (SyntaxError, ValueError):
        parsed = text
    if isinstance(parsed, (list, tuple)):
        parsed = parsed[0] if len(parsed) == 1 else None
    try:
        return int(parsed) if parsed is not None else None
    except (TypeError, ValueError):
        return None


def _pseudonym(source_name: str, source_ip: str) -> str:
    digest = hashlib.sha256(f"{source_name}\0{source_ip}".encode()).hexdigest()
    return digest[:20]


def adapt_bccc_dns_sources(
    paths: list[str | Path],
    *,
    window_seconds: int = 60,
) -> BCCCAdaptationResult:
    """Convert labelled BCCC CSVs without executing or resolving DNS content.

    Only raw metadata needed by ``DNSFeatureExtractor`` is read. Third-party
    engineered columns are deliberately ignored so train/runtime feature definitions
    remain identical. Source IPs are used only in-memory for rolling windows and are
    replaced by stable per-file pseudonyms in the prepared table.
    """

    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive")
    extractor = DNSFeatureExtractor()
    items = []
    source_reports: list[dict[str, Any]] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.suffix.lower() != ".csv" or not path.is_file():
            raise ValueError(f"BCCC source must be an existing CSV: {path}")
        frame = pd.read_csv(path, usecols=list(BCCC_REQUIRED_COLUMNS), low_memory=False)
        if frame.empty:
            raise ValueError(f"BCCC source is empty: {path.name}")
        parsed_time = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
        usable = (
            parsed_time.notna()
            & frame["src_ip"].notna()
            & frame["dst_ip"].notna()
            & frame["dns_domain_name"].notna()
            & frame["label"].notna()
        )
        rejected_rows = int((~usable).sum())
        frame = frame.loc[usable].copy()
        frame["observed_at"] = parsed_time.loc[usable]
        frame.sort_values(["observed_at", "flow_id"], kind="stable", inplace=True)
        histories: dict[str, deque[tuple[pd.Timestamp, str]]] = defaultdict(deque)
        label_counts: Counter[str] = Counter()
        unavailable_query_types = 0
        for row in frame.itertuples(index=False):
            observed_at = row.observed_at.to_pydatetime()
            source_ip = str(row.src_ip)
            domain = str(row.dns_domain_name).strip().lower().rstrip(".")
            if not domain or domain in BCCC_INVALID_DOMAIN_SENTINELS:
                rejected_rows += 1
                continue
            history = histories[source_ip]
            cutoff = observed_at - timedelta(seconds=window_seconds)
            while history and history[0][0] < cutoff:
                history.popleft()
            history.append((row.observed_at, domain))
            query_type = _query_type(row.query_resource_record_type)
            if query_type is None:
                unavailable_query_types += 1
            source_id = _pseudonym(path.name, source_ip)
            vector = extractor.extract_metadata(
                observed_at=observed_at,
                source_id=source_id,
                domain=domain,
                query_type=query_type,
                recent_domains=tuple(item[1] for item in history),
                window_seconds=window_seconds,
                capabilities=CapabilityProfile(
                    has_packet_timestamps=True,
                    has_dns_query_name=True,
                    has_dns_query_type=query_type is not None,
                ),
            )
            target = _target_label(row.label)
            label_counts[target] += 1
            items.append((vector, target, f"{path.name}:{source_id}", path.name))
        source_reports.append(
            {
                "source_name": path.name,
                "sha256": sha256_file(path),
                "input_rows": int(len(usable)),
                "prepared_rows": int(sum(label_counts.values())),
                "rejected_rows": rejected_rows,
                "labels": dict(sorted(label_counts.items())),
                "unique_groups": len(histories),
                "query_type_unavailable_rows": unavailable_query_types,
                "third_party_engineered_columns_used": False,
                "domain_resolution_performed": False,
            }
        )
    table = feature_rows(items)
    return BCCCAdaptationResult(table=table, sources=tuple(source_reports))

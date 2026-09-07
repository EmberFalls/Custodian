"""DNS lexical and behavioural features from visible passive DNS metadata."""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from custodian.core.enums import FeatureFamily
from custodian.core.ids import make_window_id
from custodian.core.schemas import CapabilityProfile, FeatureVector, PacketObservation
from custodian.features.schema import DNS_SCHEMA_VERSION, shannon_entropy, stable_bucket
from custodian.state.windows import TemporalSnapshot


def _query(packet: PacketObservation) -> dict | None:
    if not packet.dns_metadata:
        return None
    for query in packet.dns_metadata.get("queries", []):
        if isinstance(query, dict):
            return query
    return None


def normalize_dns_name(value: object) -> str:
    """Normalize a visible DNS name identically for training and runtime."""

    if not isinstance(value, str):
        raise ValueError("domain must be a string")
    domain = value.strip().lower().rstrip(".")
    if not domain:
        raise ValueError("domain must not be empty")
    return domain


def dns_lexical_values(domain: str) -> dict[str, int | float]:
    """Return the runtime DNS lexical feature definitions for one normalized name."""

    normalized = normalize_dns_name(domain)
    labels = normalized.split(".")
    characters = list(normalized.replace(".", ""))
    counts = Counter(characters)
    values: dict[str, int | float] = {
        "domain_length": len(normalized),
        "subdomain_count": max(len(labels) - 2, 0),
        "mean_label_length": sum(len(label) for label in labels) / len(labels),
        "character_entropy": shannon_entropy(characters),
        "digit_ratio": sum(character.isdigit() for character in characters) / len(characters),
        "letter_ratio": sum(character.isalpha() for character in characters) / len(characters),
        "hyphen_ratio": characters.count("-") / len(characters),
        "repeated_character_ratio": (
            sum(count for count in counts.values() if count > 1) / len(characters)
        ),
    }
    buckets = [0] * DNSFeatureExtractor.NGRAM_BUCKETS
    for first, second in zip(normalized, normalized[1:], strict=False):
        buckets[stable_bucket(first + second, DNSFeatureExtractor.NGRAM_BUCKETS)] += 1
    values.update({f"bigram_bucket_{index}": count for index, count in enumerate(buckets)})
    return values


class DNSFeatureExtractor:
    """Create DNS features while explicitly marking hidden query text unavailable."""

    NGRAM_BUCKETS = 8

    def extract(
        self,
        packet: PacketObservation,
        state: TemporalSnapshot,
        capabilities: CapabilityProfile,
    ) -> FeatureVector:
        query = _query(packet)
        domain = query.get("name") if query else None
        query_type = query.get("type") if query else None
        return self.extract_metadata(
            observed_at=packet.timestamp,
            source_id=str(packet.src_ip),
            domain=domain,
            query_type=int(query_type) if query_type is not None else None,
            recent_domains=state.recent_domains,
            window_seconds=state.window_seconds,
            capabilities=capabilities,
        )

    def extract_metadata(
        self,
        *,
        observed_at: datetime,
        source_id: str,
        domain: str | None,
        query_type: int | None,
        recent_domains: tuple[str, ...],
        window_seconds: int,
        capabilities: CapabilityProfile,
        recent_history_available: bool = True,
    ) -> FeatureVector:
        """Extract the same DNS schema from an explicit passive-metadata boundary.

        Runtime packet handling delegates here, and approved tabular training adapters
        call this method directly. That prevents training from inventing packet fields
        or using source-only engineered columns that the runtime cannot reproduce.
        """

        domain = normalize_dns_name(domain) if isinstance(domain, str) and domain.strip() else None
        lexical = dns_lexical_values(domain) if domain else {}
        values: dict[str, int | float | None] = {
            **{
                name: lexical.get(name)
                for name in (
                    "domain_length",
                    "subdomain_count",
                    "mean_label_length",
                    "character_entropy",
                    "digit_ratio",
                    "letter_ratio",
                    "hyphen_ratio",
                    "repeated_character_ratio",
                )
            },
            "query_type": query_type,
            "query_frequency": recent_domains.count(domain) if domain else None,
            "unique_domain_ratio": len(set(recent_domains)) / max(len(recent_domains), 1)
            if recent_domains
            else None,
        }
        for bucket in range(self.NGRAM_BUCKETS):
            values[f"bigram_bucket_{bucket}"] = lexical.get(f"bigram_bucket_{bucket}")
        availability = {}
        for key in values:
            if key == "query_type":
                availability[key] = capabilities.has_dns_query_type
            elif key in {"query_frequency", "unique_domain_ratio"}:
                availability[key] = capabilities.has_dns_query_name and recent_history_available
            else:
                availability[key] = capabilities.has_dns_query_name
        for key, is_available in availability.items():
            if not is_available:
                values[key] = None
        return FeatureVector(
            family=FeatureFamily.DNS,
            schema_version=DNS_SCHEMA_VERSION,
            entity_id=f"dns:{source_id}",
            window_id=make_window_id(source_id, observed_at, window_seconds),
            values=values,
            availability=availability,
        )

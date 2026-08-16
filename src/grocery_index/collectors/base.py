from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class CollectorResult:
    """
    Result returned by a retailer collector.

    A result represents one collection attempt from one known source.
    Raw records are intentionally left unnormalized; normalization happens
    in the normalization layer.
    """

    retailer: str
    source_name: str
    records: list[dict[str, Any]] = field(default_factory=list)

    source_url: str | None = None

    status: str = "success"
    error: str | None = None

    collected_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def record_count(self) -> int:
        """Number of records returned by the collector."""
        return len(self.records)

    @property
    def ok(self) -> bool:
        """Whether the collection completed successfully."""
        return self.status == "success"


class BaseCollector(ABC):
    """
    Base class for retailer data collectors.

    Concrete collectors should retrieve publicly accessible data and return
    raw records through CollectorResult. They should not perform CAPTCHA,
    authentication, paywall, robots.txt, or other access-control bypasses.
    """

    retailer: str = ""
    source_name: str = ""

    def __init__(self, *, timeout: float = 30.0) -> None:
        self.timeout = timeout

    @abstractmethod
    def collect(self, **kwargs: Any) -> CollectorResult:
        """
        Collect data from the retailer.

        Concrete collectors implement this method.
        """
        raise NotImplementedError

    def make_result(
        self,
        *,
        source_name: str | None = None,
        source_url: str | None = None,
        records: list[dict[str, Any]] | None = None,
        status: str = "success",
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CollectorResult:
        """Convenience method for constructing a CollectorResult."""

        return CollectorResult(
            retailer=self.retailer,
            source_name=source_name or self.source_name,
            source_url=source_url,
            records=records or [],
            status=status,
            error=error,
            metadata=metadata or {},
        )

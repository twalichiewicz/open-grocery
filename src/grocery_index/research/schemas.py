from dataclasses import dataclass, field


@dataclass(frozen=True)
class Source:
    """A known data source for a retailer."""

    retailer: str
    source_url: str
    source_type: str
    name: str | None = None
    notes: str | None = None
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.retailer.strip():
            raise ValueError("retailer cannot be empty")

        if not self.source_url.strip():
            raise ValueError("source_url cannot be empty")

        if not self.source_type.strip():
            raise ValueError("source_type cannot be empty")


@dataclass(frozen=True)
class SourceCheck:
    """Result of inspecting whether a source is usable."""

    source: Source
    reachable: bool
    status_code: int | None = None
    robots_allowed: bool | None = None
    error: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def usable(self) -> bool:
        """Whether the source appears usable for collection."""
        if not self.reachable:
            return False

        if self.robots_allowed is False:
            return False

        return True

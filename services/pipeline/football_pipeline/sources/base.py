from collections.abc import Iterator
from typing import Protocol

from football_pipeline.raw import RawRecord


class SourceAdapter(Protocol):
    """Anything that can yield raw records for a scope. The rest of the pipeline only sees this."""

    name: str

    def fetch(self, **scope: int) -> Iterator[RawRecord]: ...

"""Test doubles for detection lanes."""

from picopike.detectors.base import LaneResult


class FakeDetector:
    """A lane that returns a fixed score without loading a model."""

    def __init__(
        self,
        name: str = "fake",
        languages: frozenset[str] = frozenset({"en"}),
        score: float = 0.5,
    ) -> None:
        self.name = name
        self.languages = languages
        self.score = score

    async def detect(self, text: str, *, lang: str | None) -> LaneResult:
        return LaneResult(
            lane=self.name,
            score=self.score,
            labels={"injection": self.score},
            category=None,
            latency_ms=0.1,
            cost_usd=0.0,
            error=None,
            raw={"chars": len(text)},
        )

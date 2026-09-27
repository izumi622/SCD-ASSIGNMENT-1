import re

from app.models.enums import Category, Priority
from app.providers.triage.base import TriageResult


class RuleBasedTriage:
    """Deterministic keyword fallback triage provider. Always available, never fails."""

    name: str = "rules"

    # Keywords for category determination
    CATEGORY_KEYWORDS = {
        Category.water: [
            "water",
            "leak",
            "pipe",
            "burst",
            "flood",
            "flooding",
            "sewer",
            "sewage",
            "drain",
            "drainage",
            "supply",
            "tap",
            "tanker",
            "pressure",
            "line",
            "overflow",
            "gutter",
        ],
        Category.electricity: [
            "electric",
            "electricity",
            "power",
            "wire",
            "transformer",
            "outage",
            "spark",
            "sparking",
            "voltage",
            "blackout",
            "load shedding",
            "short circuit",
            "meter",
        ],
        Category.sanitation: [
            "garbage",
            "trash",
            "waste",
            "dump",
            "smell",
            "filth",
            "cleaning",
            "sweep",
            "sweeper",
            "dustbin",
            "dead animal",
            "stench",
            "rubbish",
            "debris",
        ],
        Category.roads: [
            "pothole",
            "potholes",
            "road",
            "asphalt",
            "pavement",
            "street",
            "ditch",
            "crater",
            "broken road",
            "manhole",
            "footpath",
            "sidewalk",
            "divider",
        ],
        Category.streetlights: [
            "streetlight",
            "street light",
            "streetlights",
            "light",
            "lamp",
            "pole",
            "bulb",
            "dark",
            "darkness",
            "flicker",
            "flickering",
        ],
    }

    # Keywords for priority determination
    HIGH_PRIORITY_KEYWORDS = [
        "urgent",
        "danger",
        "dangerous",
        "emergency",
        "hazard",
        "spark",
        "sparking",
        "burst",
        "flood",
        "flooding",
        "fire",
        "injury",
        "injured",
        "risk",
        "hazard",
        "live wire",
        "collapse",
        "ground floor",
        "fajr",
        "critical",
        "children",
    ]
    LOW_PRIORITY_KEYWORDS = [
        "minor",
        "request",
        "suggestion",
        "slow",
        "repaint",
        "cosmetic",
        "eventually",
    ]

    def _determine_category(self, text_lower: str) -> Category:
        scores = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(
                1 for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", text_lower)
            )
            if score > 0:
                scores[category] = score

        if scores:
            return max(scores, key=lambda category: scores[category])
        return Category.other

    def _determine_priority(self, text_lower: str) -> Priority:
        for kw in self.HIGH_PRIORITY_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                return Priority.high
        for kw in self.LOW_PRIORITY_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                return Priority.low
        return Priority.normal

    def triage(self, text: str, location: str) -> TriageResult:
        text_lower = text.lower()
        category = self._determine_category(text_lower)
        priority = self._determine_priority(text_lower)

        # Create concise <= 140 character summary
        clean_text = " ".join(text.split())
        summary = f"{category.value.title()} issue at {location}: {clean_text}"
        if len(summary) > 137:
            summary = summary[:137] + "..."

        return TriageResult(
            category=category,
            priority=priority,
            summary=summary,
            confidence=0.85 if category != Category.other else 0.50,
        )

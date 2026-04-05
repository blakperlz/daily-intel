"""
IntelItem — the universal data model for all collected intelligence.
Every collector outputs a list of IntelItem objects.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid


class Domain(str, Enum):
    FINANCIAL = "financial"
    GEOPOLITICAL = "geopolitical"
    CYBER = "cyber"
    SOCIAL = "social"
    CORPORATE = "corporate"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class IntelItem:
    domain: Domain
    source: str
    title: str
    summary: str
    url: str
    published_at: datetime
    severity: Severity = Severity.INFO
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.8
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    collected_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "domain": self.domain.value,
            "source": self.source,
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "published_at": self.published_at.isoformat(),
            "collected_at": self.collected_at.isoformat(),
            "severity": self.severity.value,
            "tags": self.tags,
            "confidence": self.confidence,
        }

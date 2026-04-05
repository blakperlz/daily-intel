"""
BaseCollector — all collectors implement this interface.
Each collector returns a list of IntelItem objects.
"""
from abc import ABC, abstractmethod
from typing import List
from models.intel_item import IntelItem


class BaseCollector(ABC):
    name: str = "base"

    @abstractmethod
    def collect(self) -> List[IntelItem]:
        """Fetch data and return normalized IntelItem list."""
        ...

    def safe_collect(self) -> List[IntelItem]:
        """Wraps collect() with error handling so one bad source never kills the digest."""
        try:
            items = self.collect()
            print(f"[{self.name}] collected {len(items)} items")
            return items
        except Exception as e:
            print(f"[{self.name}] ERROR: {e}")
            return []

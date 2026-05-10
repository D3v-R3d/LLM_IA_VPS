from dataclasses import dataclass
from typing import List


@dataclass
class Plan:
    """
    Structured plan - no free text, no markdown.
    """
    steps: List[str]
    expected_tools: List[str]
from enum import Enum
from typing import List

class ConfidenceLevel(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    UNKNOWN = "UNKNOWN"

class EvidenceType(str, Enum):
    CODE = "CODE"
    DOC = "DOC"
    ISSUE = "ISSUE"

def compute_confidence(source_types: List[str]) -> ConfidenceLevel:
    """
    Computes confidence level based on distinct source TYPES.
    Must map to ChunkType (CODE, DOC, ISSUE).
    """
    unique_types = set([s.upper() for s in source_types])
    count = len(unique_types)
    
    if count >= 3:
        return ConfidenceLevel.STRONG
    elif count == 2:
        return ConfidenceLevel.MODERATE
    elif count == 1:
        return ConfidenceLevel.WEAK
    else:
        return ConfidenceLevel.UNKNOWN

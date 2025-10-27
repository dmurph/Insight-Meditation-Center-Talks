from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, computed_field


class SourceType(Enum):
    """Enum for the different types of primary content sources."""
    YOUTUBE_VIDEO = "youtube_video"
    # Future source types can be added here
    # PODCAST_EPISODE = "podcast_episode"

@dataclass
class SourceItem:
    """
    The central object representing the primary content to be mirrored.
    """
    source_id: str
    source_type: SourceType
    intrinsic_metadata: Dict[str, Any] = field(default_factory=dict)
    supplemental_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Ensure source_type is an enum member
        if not isinstance(self.source_type, SourceType):
            self.source_type = SourceType(self.source_type)


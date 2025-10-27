from pydantic import BaseModel, computed_field
from typing import Optional, List


class AudioDharmaSpeaker(BaseModel):
    id: int
    name: str

    @computed_field
    @property
    def url(self) -> str:
        return f"https://www.audiodharma.org/speakers/{self.id}"


class AudioDharmaTalk(BaseModel):
    id: int
    title: str
    date: str
    speaker_ids: List[int]
    start_time_seconds: Optional[int] = None
    mp3_url: Optional[str] = None
    youtube_id: Optional[str] = None

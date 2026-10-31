from pydantic import BaseModel, ConfigDict


class TranscriptionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str

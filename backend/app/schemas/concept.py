
from pydantic import BaseModel, ConfigDict, Field


class ConceptMasterySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    p_effective: float = Field(ge=0.0, le=1.0)
    status: str  # locked, unlocked, learning, mastered


class ConceptNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    chapter: str
    position: int
    mastery: ConceptMasterySummary | None = None


class ConceptEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")


class ConceptGraphResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nodes: list[ConceptNode]
    edges: list[ConceptEdge]


class ConceptDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    chapter: str
    description: str
    lesson_md: str
    prerequisites: list[str]
    misconception_count: int

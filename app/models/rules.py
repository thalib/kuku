from typing import Literal
from pydantic import BaseModel, Field


MatchType = Literal["contains", "equals"]
AppliesTo = Literal["both", "debit", "credit"]


class RuleCreate(BaseModel):
    search_text: str = Field(min_length=1, max_length=200)
    match_type: MatchType
    category_id: int = Field(gt=0)
    priority: int = Field(default=0, ge=0)
    applies_to: AppliesTo = "both"
    is_active: bool = True


class RuleUpdate(BaseModel):
    search_text: str | None = Field(default=None, min_length=1, max_length=200)
    match_type: MatchType | None = None
    category_id: int | None = Field(default=None, gt=0)
    priority: int | None = Field(default=None, ge=0)
    applies_to: AppliesTo | None = None
    is_active: bool | None = None

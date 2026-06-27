from typing import Literal

from pydantic import BaseModel, Field


CategoryType = Literal["Income", "Expense", "Transfer", "Asset", "Liability", "Equity"]

CATEGORY_TYPES: tuple[CategoryType, ...] = ("Income", "Expense", "Transfer", "Asset", "Liability", "Equity")


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: CategoryType
    description: str | None = Field(default=None, max_length=250)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: CategoryType | None = None
    description: str | None = Field(default=None, max_length=250)

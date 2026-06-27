from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class TransactionCreate(BaseModel):
    account_id: int
    txn_date: date
    value_date: date
    narration: Optional[str] = None
    reference: Optional[str] = None
    debit: float = Field(default=0, ge=0)
    credit: float = Field(default=0, ge=0)
    balance: float = 0
    category_id: Optional[int] = None


class TransactionUpdate(BaseModel):
    txn_date: Optional[date] = None
    value_date: Optional[date] = None
    narration: Optional[str] = None
    reference: Optional[str] = None
    debit: Optional[float] = Field(default=None, ge=0)
    credit: Optional[float] = Field(default=None, ge=0)
    balance: Optional[float] = None
    category_id: Optional[int] = None


class TransactionCategoryUpdate(BaseModel):
    category_id: int

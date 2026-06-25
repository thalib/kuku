from pydantic import BaseModel, Field
from typing import Optional


class BankAccountCreate(BaseModel):
    bank_name: str = Field(min_length=1, max_length=100)
    account_name: str = Field(min_length=1, max_length=100)
    account_number: str = Field(min_length=1, max_length=50)
    ifsc_code: str = Field(min_length=1, max_length=20)
    branch_name: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = Field(default=None)


class BankAccountUpdate(BaseModel):
    bank_name: Optional[str] = Field(default=None, max_length=100)
    account_name: Optional[str] = Field(default=None, max_length=100)
    account_number: Optional[str] = Field(default=None, max_length=50)
    ifsc_code: Optional[str] = Field(default=None, max_length=20)
    branch_name: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = Field(default=None)

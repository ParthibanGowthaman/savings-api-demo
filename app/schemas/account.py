from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class AccountCreate(BaseModel):
    owner_name: str = Field(..., min_length=1, max_length=100)
    initial_deposit: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))


class AccountResponse(BaseModel):
    id: UUID
    owner_name: str
    balance: Decimal
    created_at: datetime


class TransactionRequest(BaseModel):
    amount: Decimal = Field(..., gt=Decimal("0"))


class TransactionResponse(BaseModel):
    id: UUID
    owner_name: str
    balance: Decimal
    message: str

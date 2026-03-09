from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AccountCreate(BaseModel):
    owner_name: str = Field(..., min_length=1, max_length=100)
    initial_deposit: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    notes: str | None = Field(default=None, max_length=500)
    daily_withdrawal_limit: Decimal | None = Field(default=None, ge=Decimal("0"))


class AccountUpdate(BaseModel):
    notes: str | None = Field(default=None, max_length=500)


class AccountResponse(BaseModel):
    id: UUID
    owner_name: str
    balance: Decimal
    notes: str | None
    is_frozen: bool
    daily_withdrawal_limit: Decimal | None
    created_at: datetime


class TransactionRequest(BaseModel):
    amount: Decimal = Field(..., gt=Decimal("0"))


class TransactionResponse(BaseModel):
    id: UUID
    owner_name: str
    balance: Decimal
    message: str


class InterestRequest(BaseModel):
    rate: Decimal = Field(default=Decimal("0.05"), gt=Decimal("0"), le=Decimal("1"))


class InterestResponse(BaseModel):
    id: UUID
    owner_name: str
    balance: Decimal
    interest_earned: Decimal
    rate: Decimal
    message: str


class TransactionHistoryEntry(BaseModel):
    id: UUID
    type: str
    amount: Decimal
    balance_after: Decimal
    timestamp: datetime


class WithdrawalLimitUpdate(BaseModel):
    daily_withdrawal_limit: Decimal | None = Field(default=None, ge=Decimal("0"))


class WithdrawalUsageResponse(BaseModel):
    account_id: UUID
    daily_withdrawal_limit: Decimal | None
    used_today: Decimal
    remaining_today: Decimal | None


class AlertCreate(BaseModel):
    threshold: Decimal = Field(..., ge=Decimal("0"))
    direction: Literal["above", "below"]


class AlertResponse(BaseModel):
    id: UUID
    account_id: UUID
    threshold: Decimal
    direction: str
    created_at: datetime


class AlertCheckResponse(AlertResponse):
    triggered: bool

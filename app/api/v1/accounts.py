import asyncio
from typing import Any, Callable
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.schemas.account import (
    AccountCreate,
    AccountResponse,
    AccountUpdate,
    AlertCheckResponse,
    AlertCreate,
    AlertResponse,
    InterestRequest,
    InterestResponse,
    TransactionHistoryEntry,
    TransactionRequest,
    TransactionResponse,
    WithdrawalLimitUpdate,
    WithdrawalUsageResponse,
)
from app.services import account_service
from app.services.account_service import (
    AccountFrozenError,
    AccountNotFoundError,
    AlertNotFoundError,
    DailyWithdrawalLimitExceededError,
    InsufficientFundsError,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])


async def _call_service(func: Callable[..., Any], *args: Any) -> Any:
    """Run a sync service function in a thread, translating domain errors to HTTP errors."""
    try:
        return await asyncio.to_thread(func, *args)
    except (AccountNotFoundError, AlertNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except AccountFrozenError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except (InsufficientFundsError, DailyWithdrawalLimitExceededError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/", response_model=list[AccountResponse])
async def list_accounts() -> list[AccountResponse]:
    accounts = await _call_service(account_service.list_accounts)
    return [AccountResponse(**a) for a in accounts]


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(payload: AccountCreate) -> AccountResponse:
    account = await _call_service(
        account_service.create_account,
        payload.owner_name,
        payload.initial_deposit,
        payload.notes,
        payload.daily_withdrawal_limit,
    )
    return AccountResponse(**account)


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(account_id: UUID, payload: AccountUpdate) -> AccountResponse:
    account = await _call_service(account_service.update_account, account_id, payload.notes)
    return AccountResponse(**account)


@router.post("/{account_id}/freeze", response_model=AccountResponse)
async def freeze_account(account_id: UUID) -> AccountResponse:
    account = await _call_service(account_service.freeze_account, account_id)
    return AccountResponse(**account)


@router.post("/{account_id}/unfreeze", response_model=AccountResponse)
async def unfreeze_account(account_id: UUID) -> AccountResponse:
    account = await _call_service(account_service.unfreeze_account, account_id)
    return AccountResponse(**account)


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: UUID) -> AccountResponse:
    account = await _call_service(account_service.get_account, account_id)
    return AccountResponse(**account)


@router.post("/{account_id}/deposit", response_model=TransactionResponse)
async def deposit(account_id: UUID, payload: TransactionRequest) -> TransactionResponse:
    account = await _call_service(account_service.deposit, account_id, payload.amount)
    return TransactionResponse(**account, message=f"Deposited {payload.amount}")


@router.post("/{account_id}/interest", response_model=InterestResponse)
async def apply_interest(account_id: UUID, payload: InterestRequest) -> InterestResponse:
    result = await _call_service(account_service.apply_interest, account_id, payload.rate)
    return InterestResponse(
        **result,
        message=f"Applied {payload.rate * 100:.2f}% interest, earned {result['interest_earned']}",
    )


@router.post("/{account_id}/withdraw", response_model=TransactionResponse)
async def withdraw(account_id: UUID, payload: TransactionRequest) -> TransactionResponse:
    account = await _call_service(account_service.withdraw, account_id, payload.amount)
    return TransactionResponse(**account, message=f"Withdrew {payload.amount}")


@router.patch("/{account_id}/withdrawal-limit", response_model=AccountResponse)
async def update_withdrawal_limit(
    account_id: UUID, payload: WithdrawalLimitUpdate
) -> AccountResponse:
    account = await _call_service(
        account_service.update_withdrawal_limit, account_id, payload.daily_withdrawal_limit
    )
    return AccountResponse(**account)


@router.get("/{account_id}/withdrawal-usage", response_model=WithdrawalUsageResponse)
async def get_withdrawal_usage(account_id: UUID) -> WithdrawalUsageResponse:
    usage = await _call_service(account_service.get_withdrawal_usage, account_id)
    return WithdrawalUsageResponse(**usage)


@router.get("/{account_id}/transactions", response_model=list[TransactionHistoryEntry])
async def get_transactions(account_id: UUID) -> list[TransactionHistoryEntry]:
    transactions = await _call_service(account_service.get_transactions, account_id)
    return [TransactionHistoryEntry(**t) for t in transactions]


@router.post(
    "/{account_id}/alerts", response_model=AlertResponse, status_code=status.HTTP_201_CREATED
)
async def create_alert(account_id: UUID, payload: AlertCreate) -> AlertResponse:
    alert = await _call_service(
        account_service.create_alert, account_id, payload.threshold, payload.direction
    )
    return AlertResponse(**alert)


@router.get("/{account_id}/alerts/check", response_model=list[AlertCheckResponse])
async def check_alerts(account_id: UUID) -> list[AlertCheckResponse]:
    alerts = await _call_service(account_service.check_alerts, account_id)
    return [AlertCheckResponse(**a) for a in alerts]


@router.get("/{account_id}/alerts", response_model=list[AlertResponse])
async def list_alerts(account_id: UUID) -> list[AlertResponse]:
    alerts = await _call_service(account_service.list_alerts, account_id)
    return [AlertResponse(**a) for a in alerts]


@router.delete(
    "/{account_id}/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_alert(account_id: UUID, alert_id: UUID) -> None:
    await _call_service(account_service.delete_alert, account_id, alert_id)

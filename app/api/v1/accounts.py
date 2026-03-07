import asyncio
from functools import partial
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.schemas.account import (
    AccountCreate,
    AccountResponse,
    AccountUpdate,
    InterestRequest,
    InterestResponse,
    TransactionHistoryEntry,
    TransactionRequest,
    TransactionResponse,
)
from app.services import account_service
from app.services.account_service import AccountNotFoundError, InsufficientFundsError

router = APIRouter(prefix="/accounts", tags=["accounts"])


async def _run_sync(func, *args):
    """Run a sync service function in a thread pool to avoid blocking the event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(func, *args))


@router.get("/", response_model=list[AccountResponse])
async def list_accounts() -> list[AccountResponse]:
    accounts = await _run_sync(account_service.list_accounts)
    return [AccountResponse(**a) for a in accounts]


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(payload: AccountCreate) -> AccountResponse:
    account = await _run_sync(
        account_service.create_account, payload.owner_name, payload.initial_deposit, payload.notes
    )
    return AccountResponse(**account)


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(account_id: UUID, payload: AccountUpdate) -> AccountResponse:
    try:
        account = await _run_sync(account_service.update_account, account_id, payload.notes)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return AccountResponse(**account)


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: UUID) -> AccountResponse:
    try:
        account = await _run_sync(account_service.get_account, account_id)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return AccountResponse(**account)


@router.post("/{account_id}/deposit", response_model=TransactionResponse)
async def deposit(account_id: UUID, payload: TransactionRequest) -> TransactionResponse:
    try:
        account = await _run_sync(account_service.deposit, account_id, payload.amount)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return TransactionResponse(**account, message=f"Deposited {payload.amount}")


@router.post("/{account_id}/interest", response_model=InterestResponse)
async def apply_interest(account_id: UUID, payload: InterestRequest) -> InterestResponse:
    try:
        result = await _run_sync(account_service.apply_interest, account_id, payload.rate)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return InterestResponse(
        **result,
        message=f"Applied {payload.rate * 100:.2f}% interest, earned {result['interest_earned']}",
    )


@router.post("/{account_id}/withdraw", response_model=TransactionResponse)
async def withdraw(account_id: UUID, payload: TransactionRequest) -> TransactionResponse:
    try:
        account = await _run_sync(account_service.withdraw, account_id, payload.amount)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InsufficientFundsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return TransactionResponse(**account, message=f"Withdrew {payload.amount}")


@router.get("/{account_id}/transactions", response_model=list[TransactionHistoryEntry])
async def get_transactions(account_id: UUID) -> list[TransactionHistoryEntry]:
    try:
        transactions = await _run_sync(account_service.get_transactions, account_id)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return [TransactionHistoryEntry(**t) for t in transactions]

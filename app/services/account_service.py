import threading
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4


class AccountNotFoundError(Exception):
    def __init__(self, account_id: UUID) -> None:
        self.account_id = account_id
        super().__init__(f"Account {account_id} not found")


class InsufficientFundsError(Exception):
    pass


# In-memory store: dict of UUID -> account dict
_accounts: dict[UUID, dict] = {}
_transactions: dict[UUID, list[dict]] = {}
_lock = threading.Lock()


def _get_account(account_id: UUID) -> dict:
    account = _accounts.get(account_id)
    if account is None:
        raise AccountNotFoundError(account_id)
    return account


def create_account(owner_name: str, initial_deposit: Decimal, notes: str | None = None) -> dict:
    account_id = uuid4()
    account = {
        "id": account_id,
        "owner_name": owner_name,
        "balance": initial_deposit,
        "notes": notes,
        "created_at": datetime.now(timezone.utc),
    }
    with _lock:
        _accounts[account_id] = account
        _transactions[account_id] = []
    return account


def update_account(account_id: UUID, notes: str | None) -> dict:
    with _lock:
        account = _get_account(account_id)
        account["notes"] = notes
        return account


def list_accounts() -> list[dict]:
    with _lock:
        return list(_accounts.values())


def get_account(account_id: UUID) -> dict:
    with _lock:
        return _get_account(account_id)


def deposit(account_id: UUID, amount: Decimal) -> dict:
    with _lock:
        account = _get_account(account_id)
        account["balance"] += amount
        _transactions[account_id].append({
            "id": uuid4(),
            "type": "deposit",
            "amount": amount,
            "balance_after": account["balance"],
            "timestamp": datetime.now(timezone.utc),
        })
        return account


def apply_interest(account_id: UUID, rate: Decimal) -> dict:
    with _lock:
        account = _get_account(account_id)
        interest = (account["balance"] * rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        account["balance"] += interest
        _transactions[account_id].append({
            "id": uuid4(),
            "type": "interest",
            "amount": interest,
            "balance_after": account["balance"],
            "timestamp": datetime.now(timezone.utc),
        })
        return {**account, "interest_earned": interest, "rate": rate}


def withdraw(account_id: UUID, amount: Decimal) -> dict:
    with _lock:
        account = _get_account(account_id)
        if amount > account["balance"]:
            raise InsufficientFundsError("Insufficient funds")
        account["balance"] -= amount
        _transactions[account_id].append({
            "id": uuid4(),
            "type": "withdrawal",
            "amount": amount,
            "balance_after": account["balance"],
            "timestamp": datetime.now(timezone.utc),
        })
        return account


def get_transactions(account_id: UUID) -> list[dict]:
    with _lock:
        _get_account(account_id)
        return list(_transactions[account_id])

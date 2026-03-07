import threading
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4


class AccountNotFoundError(Exception):
    def __init__(self, account_id: UUID) -> None:
        self.account_id = account_id
        super().__init__(f"Account {account_id} not found")


class InsufficientFundsError(Exception):
    pass


# In-memory store: dict of UUID -> account dict
_accounts: dict[UUID, dict] = {}
_lock = threading.Lock()


def _get_account(account_id: UUID) -> dict:
    account = _accounts.get(account_id)
    if account is None:
        raise AccountNotFoundError(account_id)
    return account


def create_account(owner_name: str, initial_deposit: Decimal) -> dict:
    account_id = uuid4()
    account = {
        "id": account_id,
        "owner_name": owner_name,
        "balance": initial_deposit,
        "created_at": datetime.now(timezone.utc),
    }
    with _lock:
        _accounts[account_id] = account
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
        return account


def withdraw(account_id: UUID, amount: Decimal) -> dict:
    with _lock:
        account = _get_account(account_id)
        if amount > account["balance"]:
            raise InsufficientFundsError("Insufficient funds")
        account["balance"] -= amount
        return account

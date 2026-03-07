import pytest
import pytest_asyncio
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from uuid import uuid4

from app.main import app
from app.services import account_service


BASE_URL = "/api/v1/accounts"


@pytest.fixture(autouse=True)
def clear_accounts():
    """Clear in-memory store before each test."""
    account_service._accounts.clear()
    account_service._transactions.clear()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _create_account(client: AsyncClient, owner_name: str = "Alice", initial_deposit: str = "0") -> dict:
    """Helper to create an account and return the response."""
    payload = {"owner_name": owner_name, "initial_deposit": initial_deposit}
    resp = await client.post(f"{BASE_URL}/", json=payload)
    return resp


# ---------- Account Creation ----------


async def test_create_account_default_deposit(client: AsyncClient) -> None:
    """Create account without initial deposit; balance should be 0."""
    resp = await client.post(f"{BASE_URL}/", json={"owner_name": "Alice"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["owner_name"] == "Alice"
    assert Decimal(data["balance"]) == Decimal("0")
    assert "id" in data
    assert "created_at" in data


async def test_create_account_with_initial_deposit(client: AsyncClient) -> None:
    """Create account with an explicit initial deposit."""
    resp = await client.post(
        f"{BASE_URL}/",
        json={"owner_name": "Bob", "initial_deposit": "250.75"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["owner_name"] == "Bob"
    assert Decimal(data["balance"]) == Decimal("250.75")


# ---------- List Accounts ----------


async def test_list_accounts_empty(client: AsyncClient) -> None:
    """Listing accounts when none exist should return an empty list."""
    resp = await client.get(f"{BASE_URL}/")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_accounts_multiple(client: AsyncClient) -> None:
    """Listing accounts should return all created accounts."""
    await _create_account(client, owner_name="Alice", initial_deposit="100")
    await _create_account(client, owner_name="Bob", initial_deposit="200")

    resp = await client.get(f"{BASE_URL}/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    names = {a["owner_name"] for a in data}
    assert names == {"Alice", "Bob"}


# ---------- Get Account ----------


async def test_get_account_success(client: AsyncClient) -> None:
    """Retrieve an existing account by ID."""
    create_resp = await _create_account(client, owner_name="Carol", initial_deposit="100")
    account_id = create_resp.json()["id"]

    resp = await client.get(f"{BASE_URL}/{account_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == account_id
    assert data["owner_name"] == "Carol"
    assert Decimal(data["balance"]) == Decimal("100")


async def test_get_account_not_found(client: AsyncClient) -> None:
    """Requesting a non-existent account should return 404."""
    fake_id = str(uuid4())
    resp = await client.get(f"{BASE_URL}/{fake_id}")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ---------- Deposit ----------


async def test_deposit_success(client: AsyncClient) -> None:
    """Deposit money and verify balance increases."""
    create_resp = await _create_account(client, owner_name="Dave", initial_deposit="50")
    account_id = create_resp.json()["id"]

    resp = await client.post(
        f"{BASE_URL}/{account_id}/deposit",
        json={"amount": "25.00"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["balance"]) == Decimal("75.00")
    assert "message" in data


async def test_deposit_to_nonexistent_account(client: AsyncClient) -> None:
    """Depositing to a non-existent account should return 404."""
    fake_id = str(uuid4())
    resp = await client.post(
        f"{BASE_URL}/{fake_id}/deposit",
        json={"amount": "10"},
    )
    assert resp.status_code == 404


# ---------- Withdraw ----------


async def test_withdraw_success(client: AsyncClient) -> None:
    """Withdraw money and verify balance decreases."""
    create_resp = await _create_account(client, owner_name="Eve", initial_deposit="100")
    account_id = create_resp.json()["id"]

    resp = await client.post(
        f"{BASE_URL}/{account_id}/withdraw",
        json={"amount": "40"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["balance"]) == Decimal("60")
    assert "message" in data


async def test_withdraw_insufficient_funds(client: AsyncClient) -> None:
    """Withdrawing more than the balance should return 400."""
    create_resp = await _create_account(client, owner_name="Frank", initial_deposit="20")
    account_id = create_resp.json()["id"]

    resp = await client.post(
        f"{BASE_URL}/{account_id}/withdraw",
        json={"amount": "50"},
    )
    assert resp.status_code == 400
    assert "insufficient funds" in resp.json()["detail"].lower()


async def test_withdraw_exact_balance(client: AsyncClient) -> None:
    """Withdrawing the exact balance should succeed and leave 0."""
    create_resp = await _create_account(client, owner_name="Grace", initial_deposit="30")
    account_id = create_resp.json()["id"]

    resp = await client.post(
        f"{BASE_URL}/{account_id}/withdraw",
        json={"amount": "30"},
    )
    assert resp.status_code == 200
    assert Decimal(resp.json()["balance"]) == Decimal("0")


async def test_withdraw_from_nonexistent_account(client: AsyncClient) -> None:
    """Withdrawing from a non-existent account should return 404."""
    fake_id = str(uuid4())
    resp = await client.post(
        f"{BASE_URL}/{fake_id}/withdraw",
        json={"amount": "10"},
    )
    assert resp.status_code == 404


# ---------- Decimal Precision ----------


async def test_decimal_precision(client: AsyncClient) -> None:
    """Verify correct Decimal arithmetic: deposit 10.50, withdraw 3.33, expect 7.17."""
    create_resp = await _create_account(client, owner_name="Heidi", initial_deposit="0")
    account_id = create_resp.json()["id"]

    await client.post(
        f"{BASE_URL}/{account_id}/deposit",
        json={"amount": "10.50"},
    )

    resp = await client.post(
        f"{BASE_URL}/{account_id}/withdraw",
        json={"amount": "3.33"},
    )
    assert resp.status_code == 200
    assert Decimal(resp.json()["balance"]) == Decimal("7.17")


async def test_multiple_transactions_decimal_precision(client: AsyncClient) -> None:
    """Multiple deposits and withdrawals maintain correct Decimal precision."""
    create_resp = await _create_account(client, owner_name="Ivan", initial_deposit="100.00")
    account_id = create_resp.json()["id"]

    await client.post(f"{BASE_URL}/{account_id}/deposit", json={"amount": "0.01"})
    await client.post(f"{BASE_URL}/{account_id}/deposit", json={"amount": "0.02"})
    await client.post(f"{BASE_URL}/{account_id}/withdraw", json={"amount": "0.03"})

    resp = await client.get(f"{BASE_URL}/{account_id}")
    assert Decimal(resp.json()["balance"]) == Decimal("100.00")


# ---------- Validation Errors ----------


async def test_create_account_empty_owner_name(client: AsyncClient) -> None:
    """An empty owner_name should be rejected (min_length=1)."""
    resp = await client.post(f"{BASE_URL}/", json={"owner_name": ""})
    assert resp.status_code == 422


async def test_create_account_missing_owner_name(client: AsyncClient) -> None:
    """Missing owner_name field should be rejected."""
    resp = await client.post(f"{BASE_URL}/", json={})
    assert resp.status_code == 422


async def test_create_account_negative_initial_deposit(client: AsyncClient) -> None:
    """A negative initial deposit should be rejected (ge=0)."""
    resp = await client.post(
        f"{BASE_URL}/",
        json={"owner_name": "Judy", "initial_deposit": "-10"},
    )
    assert resp.status_code == 422


async def test_deposit_zero_amount(client: AsyncClient) -> None:
    """Depositing zero should be rejected (gt=0)."""
    create_resp = await _create_account(client, owner_name="Karl", initial_deposit="50")
    account_id = create_resp.json()["id"]

    resp = await client.post(
        f"{BASE_URL}/{account_id}/deposit",
        json={"amount": "0"},
    )
    assert resp.status_code == 422


async def test_deposit_negative_amount(client: AsyncClient) -> None:
    """Depositing a negative amount should be rejected."""
    create_resp = await _create_account(client, owner_name="Liam", initial_deposit="50")
    account_id = create_resp.json()["id"]

    resp = await client.post(
        f"{BASE_URL}/{account_id}/deposit",
        json={"amount": "-5"},
    )
    assert resp.status_code == 422


async def test_withdraw_zero_amount(client: AsyncClient) -> None:
    """Withdrawing zero should be rejected (gt=0)."""
    create_resp = await _create_account(client, owner_name="Mia", initial_deposit="50")
    account_id = create_resp.json()["id"]

    resp = await client.post(
        f"{BASE_URL}/{account_id}/withdraw",
        json={"amount": "0"},
    )
    assert resp.status_code == 422


async def test_withdraw_negative_amount(client: AsyncClient) -> None:
    """Withdrawing a negative amount should be rejected."""
    create_resp = await _create_account(client, owner_name="Noah", initial_deposit="50")
    account_id = create_resp.json()["id"]

    resp = await client.post(
        f"{BASE_URL}/{account_id}/withdraw",
        json={"amount": "-10"},
    )
    assert resp.status_code == 422


async def test_create_account_owner_name_too_long(client: AsyncClient) -> None:
    """Owner name exceeding max_length=100 should be rejected."""
    long_name = "A" * 101
    resp = await client.post(f"{BASE_URL}/", json={"owner_name": long_name})
    assert resp.status_code == 422


# ---------- Interest ----------


async def test_apply_interest_success(client: AsyncClient) -> None:
    """Apply 5% interest to 1000 balance; expect 1050 balance and 50 earned."""
    create_resp = await _create_account(client, owner_name="Olivia", initial_deposit="1000")
    account_id = create_resp.json()["id"]

    resp = await client.post(
        f"{BASE_URL}/{account_id}/interest",
        json={"rate": "0.05"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["balance"]) == Decimal("1050.00")
    assert Decimal(data["interest_earned"]) == Decimal("50.00")
    assert Decimal(data["rate"]) == Decimal("0.05")
    assert "message" in data


async def test_apply_interest_default_rate(client: AsyncClient) -> None:
    """Omitting rate should use the default 5%."""
    create_resp = await _create_account(client, owner_name="Paul", initial_deposit="200")
    account_id = create_resp.json()["id"]

    resp = await client.post(f"{BASE_URL}/{account_id}/interest", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["interest_earned"]) == Decimal("10.00")
    assert Decimal(data["balance"]) == Decimal("210.00")


async def test_apply_interest_custom_rate(client: AsyncClient) -> None:
    """Apply 10% interest to 200 balance; expect 220 balance."""
    create_resp = await _create_account(client, owner_name="Quinn", initial_deposit="200")
    account_id = create_resp.json()["id"]

    resp = await client.post(
        f"{BASE_URL}/{account_id}/interest",
        json={"rate": "0.10"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["balance"]) == Decimal("220.00")
    assert Decimal(data["interest_earned"]) == Decimal("20.00")


async def test_apply_interest_zero_balance(client: AsyncClient) -> None:
    """Interest on zero balance should earn 0 and stay at 0."""
    create_resp = await _create_account(client, owner_name="Rita", initial_deposit="0")
    account_id = create_resp.json()["id"]

    resp = await client.post(
        f"{BASE_URL}/{account_id}/interest",
        json={"rate": "0.05"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["balance"]) == Decimal("0")
    assert Decimal(data["interest_earned"]) == Decimal("0")


async def test_apply_interest_not_found(client: AsyncClient) -> None:
    """Applying interest to a non-existent account should return 404."""
    fake_id = str(uuid4())
    resp = await client.post(
        f"{BASE_URL}/{fake_id}/interest",
        json={"rate": "0.05"},
    )
    assert resp.status_code == 404


async def test_apply_interest_decimal_precision(client: AsyncClient) -> None:
    """100.10 * 0.03 = 3.003 should round to 3.00 (ROUND_HALF_UP)."""
    create_resp = await _create_account(client, owner_name="Sam", initial_deposit="100.10")
    account_id = create_resp.json()["id"]

    resp = await client.post(
        f"{BASE_URL}/{account_id}/interest",
        json={"rate": "0.03"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["interest_earned"]) == Decimal("3.00")
    assert Decimal(data["balance"]) == Decimal("103.10")


async def test_apply_interest_negative_rate(client: AsyncClient) -> None:
    """A negative rate should be rejected (gt=0)."""
    create_resp = await _create_account(client, owner_name="Tina", initial_deposit="100")
    account_id = create_resp.json()["id"]

    resp = await client.post(
        f"{BASE_URL}/{account_id}/interest",
        json={"rate": "-0.05"},
    )
    assert resp.status_code == 422


async def test_apply_interest_zero_rate(client: AsyncClient) -> None:
    """A zero rate should be rejected (gt=0)."""
    create_resp = await _create_account(client, owner_name="Uma", initial_deposit="100")
    account_id = create_resp.json()["id"]

    resp = await client.post(
        f"{BASE_URL}/{account_id}/interest",
        json={"rate": "0"},
    )
    assert resp.status_code == 422


async def test_apply_interest_rate_exceeds_one(client: AsyncClient) -> None:
    """A rate above 1 (100%) should be rejected (le=1)."""
    create_resp = await _create_account(client, owner_name="Vera", initial_deposit="100")
    account_id = create_resp.json()["id"]

    resp = await client.post(
        f"{BASE_URL}/{account_id}/interest",
        json={"rate": "1.5"},
    )
    assert resp.status_code == 422


async def test_apply_interest_multiple_times(client: AsyncClient) -> None:
    """Applying interest twice should compound correctly."""
    create_resp = await _create_account(client, owner_name="Walt", initial_deposit="1000")
    account_id = create_resp.json()["id"]

    # First application: 1000 * 0.10 = 100 -> balance 1100
    await client.post(f"{BASE_URL}/{account_id}/interest", json={"rate": "0.10"})

    # Second application: 1100 * 0.10 = 110 -> balance 1210
    resp = await client.post(f"{BASE_URL}/{account_id}/interest", json={"rate": "0.10"})
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["balance"]) == Decimal("1210.00")
    assert Decimal(data["interest_earned"]) == Decimal("110.00")


# ---------- Transaction History ----------


async def test_transaction_history_empty(client: AsyncClient) -> None:
    """New account with no transactions returns empty list."""
    create_resp = await _create_account(client, owner_name="Alice", initial_deposit="0")
    account_id = create_resp.json()["id"]

    resp = await client.get(f"{BASE_URL}/{account_id}/transactions")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_transaction_history_after_deposit(client: AsyncClient) -> None:
    """Deposit records a 'deposit' transaction with correct amount and balance_after."""
    create_resp = await _create_account(client, owner_name="Bob", initial_deposit="100")
    account_id = create_resp.json()["id"]

    await client.post(f"{BASE_URL}/{account_id}/deposit", json={"amount": "50"})

    resp = await client.get(f"{BASE_URL}/{account_id}/transactions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    txn = data[0]
    assert txn["type"] == "deposit"
    assert Decimal(txn["amount"]) == Decimal("50")
    assert Decimal(txn["balance_after"]) == Decimal("150")


async def test_transaction_history_after_withdrawal(client: AsyncClient) -> None:
    """Withdrawal records a 'withdrawal' transaction."""
    create_resp = await _create_account(client, owner_name="Carol", initial_deposit="200")
    account_id = create_resp.json()["id"]

    await client.post(f"{BASE_URL}/{account_id}/withdraw", json={"amount": "75"})

    resp = await client.get(f"{BASE_URL}/{account_id}/transactions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    txn = data[0]
    assert txn["type"] == "withdrawal"
    assert Decimal(txn["amount"]) == Decimal("75")
    assert Decimal(txn["balance_after"]) == Decimal("125")


async def test_transaction_history_after_interest(client: AsyncClient) -> None:
    """Interest records an 'interest' transaction."""
    create_resp = await _create_account(client, owner_name="Dave", initial_deposit="1000")
    account_id = create_resp.json()["id"]

    await client.post(f"{BASE_URL}/{account_id}/interest", json={"rate": "0.05"})

    resp = await client.get(f"{BASE_URL}/{account_id}/transactions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    txn = data[0]
    assert txn["type"] == "interest"
    assert Decimal(txn["amount"]) == Decimal("50")
    assert Decimal(txn["balance_after"]) == Decimal("1050")


async def test_transaction_history_multiple(client: AsyncClient) -> None:
    """Deposit then withdraw; verify 2 entries in chronological order."""
    create_resp = await _create_account(client, owner_name="Eve", initial_deposit="500")
    account_id = create_resp.json()["id"]

    await client.post(f"{BASE_URL}/{account_id}/deposit", json={"amount": "100"})
    await client.post(f"{BASE_URL}/{account_id}/withdraw", json={"amount": "50"})

    resp = await client.get(f"{BASE_URL}/{account_id}/transactions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    # First entry should be the deposit (chronological order)
    assert data[0]["type"] == "deposit"
    assert Decimal(data[0]["amount"]) == Decimal("100")

    # Second entry should be the withdrawal
    assert data[1]["type"] == "withdrawal"
    assert Decimal(data[1]["amount"]) == Decimal("50")

    # Timestamps should be in chronological order
    assert data[0]["timestamp"] <= data[1]["timestamp"]


async def test_transaction_history_not_found(client: AsyncClient) -> None:
    """Non-existent account returns 404."""
    fake_id = str(uuid4())
    resp = await client.get(f"{BASE_URL}/{fake_id}/transactions")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_transaction_history_entry_fields(client: AsyncClient) -> None:
    """Verify all expected fields exist (id, type, amount, balance_after, timestamp)."""
    create_resp = await _create_account(client, owner_name="Frank", initial_deposit="100")
    account_id = create_resp.json()["id"]

    await client.post(f"{BASE_URL}/{account_id}/deposit", json={"amount": "25"})

    resp = await client.get(f"{BASE_URL}/{account_id}/transactions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    txn = data[0]

    assert "id" in txn
    assert "type" in txn
    assert "amount" in txn
    assert "balance_after" in txn
    assert "timestamp" in txn

    # Verify id is a valid UUID
    from uuid import UUID
    UUID(txn["id"])  # raises ValueError if invalid


async def test_transaction_history_balance_tracking(client: AsyncClient) -> None:
    """Multiple operations; verify each entry's balance_after is correct."""
    create_resp = await _create_account(client, owner_name="Grace", initial_deposit="1000")
    account_id = create_resp.json()["id"]

    # Deposit 200 -> balance 1200
    await client.post(f"{BASE_URL}/{account_id}/deposit", json={"amount": "200"})
    # Withdraw 150 -> balance 1050
    await client.post(f"{BASE_URL}/{account_id}/withdraw", json={"amount": "150"})
    # Apply 10% interest -> 1050 * 0.10 = 105 -> balance 1155
    await client.post(f"{BASE_URL}/{account_id}/interest", json={"rate": "0.10"})
    # Deposit 45 -> balance 1200
    await client.post(f"{BASE_URL}/{account_id}/deposit", json={"amount": "45"})

    resp = await client.get(f"{BASE_URL}/{account_id}/transactions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 4

    assert data[0]["type"] == "deposit"
    assert Decimal(data[0]["balance_after"]) == Decimal("1200")

    assert data[1]["type"] == "withdrawal"
    assert Decimal(data[1]["balance_after"]) == Decimal("1050")

    assert data[2]["type"] == "interest"
    assert Decimal(data[2]["amount"]) == Decimal("105")
    assert Decimal(data[2]["balance_after"]) == Decimal("1155")

    assert data[3]["type"] == "deposit"
    assert Decimal(data[3]["balance_after"]) == Decimal("1200")


# ---------- Account Notes ----------


async def test_create_account_without_notes(client: AsyncClient) -> None:
    """Create account without notes; notes should be None in response."""
    resp = await client.post(
        f"{BASE_URL}/", json={"owner_name": "Alice", "initial_deposit": "100"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["notes"] is None


async def test_create_account_with_notes(client: AsyncClient) -> None:
    """Create account with notes; notes should appear in response."""
    resp = await client.post(
        f"{BASE_URL}/",
        json={"owner_name": "Bob", "initial_deposit": "50", "notes": "My savings"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["notes"] == "My savings"


async def test_create_account_notes_too_long(client: AsyncClient) -> None:
    """Notes exceeding max_length=500 should be rejected with 422."""
    long_notes = "N" * 501
    resp = await client.post(
        f"{BASE_URL}/",
        json={"owner_name": "Carol", "notes": long_notes},
    )
    assert resp.status_code == 422


async def test_create_account_empty_notes(client: AsyncClient) -> None:
    """Empty string notes should be allowed."""
    resp = await client.post(
        f"{BASE_URL}/",
        json={"owner_name": "Dave", "initial_deposit": "0", "notes": ""},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["notes"] == ""


async def test_get_account_includes_notes(client: AsyncClient) -> None:
    """GET single account should return the notes field."""
    create_resp = await client.post(
        f"{BASE_URL}/",
        json={"owner_name": "Eve", "initial_deposit": "100", "notes": "Emergency fund"},
    )
    account_id = create_resp.json()["id"]

    resp = await client.get(f"{BASE_URL}/{account_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["notes"] == "Emergency fund"


async def test_list_accounts_includes_notes(client: AsyncClient) -> None:
    """Listing accounts should include the notes field."""
    await client.post(
        f"{BASE_URL}/",
        json={"owner_name": "Frank", "initial_deposit": "10", "notes": "Vacation fund"},
    )

    resp = await client.get(f"{BASE_URL}/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["notes"] == "Vacation fund"


async def test_update_notes_success(client: AsyncClient) -> None:
    """PATCH account with new notes should update and return them."""
    create_resp = await _create_account(client, owner_name="Grace", initial_deposit="100")
    account_id = create_resp.json()["id"]

    resp = await client.patch(
        f"{BASE_URL}/{account_id}",
        json={"notes": "Updated notes"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["notes"] == "Updated notes"
    assert data["id"] == account_id


async def test_update_notes_to_null(client: AsyncClient) -> None:
    """PATCH account with notes=null should clear the notes."""
    create_resp = await client.post(
        f"{BASE_URL}/",
        json={"owner_name": "Heidi", "initial_deposit": "50", "notes": "Some notes"},
    )
    account_id = create_resp.json()["id"]

    resp = await client.patch(
        f"{BASE_URL}/{account_id}",
        json={"notes": None},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["notes"] is None


async def test_update_notes_account_not_found(client: AsyncClient) -> None:
    """PATCH a non-existent account should return 404."""
    fake_id = str(uuid4())
    resp = await client.patch(
        f"{BASE_URL}/{fake_id}",
        json={"notes": "Does not matter"},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_update_notes_too_long(client: AsyncClient) -> None:
    """PATCH with notes exceeding max_length=500 should return 422."""
    create_resp = await _create_account(client, owner_name="Ivan", initial_deposit="10")
    account_id = create_resp.json()["id"]

    long_notes = "X" * 501
    resp = await client.patch(
        f"{BASE_URL}/{account_id}",
        json={"notes": long_notes},
    )
    assert resp.status_code == 422

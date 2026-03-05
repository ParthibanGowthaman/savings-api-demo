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

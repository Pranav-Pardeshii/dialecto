import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_users(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users")
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 2
    names = [u["display_name"] for u in users]
    assert "Aarav" in names
    assert "Ms. Rao" in names


@pytest.mark.asyncio
async def test_get_me_student(client: AsyncClient) -> None:
    response = await client.get("/api/v1/me", headers={"X-Demo-User-Id": "1"})
    assert response.status_code == 200
    user = response.json()
    assert user["id"] == 1
    assert user["display_name"] == "Aarav"
    assert user["role"] == "student"


@pytest.mark.asyncio
async def test_get_me_missing_header(client: AsyncClient) -> None:
    response = await client.get("/api/v1/me")
    assert response.status_code == 401
    err = response.json()
    assert err["error"]["code"] == "unknown_user"
    assert "request_id" in err["error"]


import pytest

from app.models.enums import Status, is_valid_transition


def test_transition_table_unit_logic():
    # Valid transitions
    assert is_valid_transition(Status.open, Status.in_progress) is True
    assert is_valid_transition(Status.open, Status.rejected) is True
    assert is_valid_transition(Status.in_progress, Status.resolved) is True
    assert is_valid_transition(Status.in_progress, Status.rejected) is True

    # Invalid / forbidden transitions
    assert is_valid_transition(Status.open, Status.resolved) is False
    assert is_valid_transition(Status.resolved, Status.open) is False
    assert is_valid_transition(Status.resolved, Status.in_progress) is False
    assert is_valid_transition(Status.rejected, Status.open) is False
    assert is_valid_transition(Status.rejected, Status.resolved) is False


@pytest.mark.asyncio
async def test_api_status_state_machine_transitions(client):
    # 1. Create a complaint (starts as 'open')
    create_res = await client.post(
        "/api/complaints",
        json={"text": "Water leakage in front of school entrance", "location": "Sector G-8/1"},
    )
    assert create_res.status_code == 201
    cid = create_res.json()["id"]
    assert create_res.json()["status"] == "open"

    # 2. Advance open -> in_progress (valid)
    p1 = await client.patch(f"/api/complaints/{cid}/status", json={"status": "in_progress"})
    assert p1.status_code == 200
    assert p1.json()["status"] == "in_progress"

    # 3. Try in_progress -> open (invalid, must return 409)
    p_invalid = await client.patch(f"/api/complaints/{cid}/status", json={"status": "open"})
    assert p_invalid.status_code == 409
    assert "Invalid transition from in_progress to open" in p_invalid.json()["detail"]

    # 4. Advance in_progress -> resolved (valid)
    p2 = await client.patch(f"/api/complaints/{cid}/status", json={"status": "resolved"})
    assert p2.status_code == 200
    assert p2.json()["status"] == "resolved"

    # 5. Try resolved -> in_progress (resolved is terminal, 409)
    p_terminal = await client.patch(f"/api/complaints/{cid}/status", json={"status": "in_progress"})
    assert p_terminal.status_code == 409
    assert "Invalid transition from resolved to in_progress" in p_terminal.json()["detail"]


@pytest.mark.asyncio
async def test_api_rejection_from_open(client):
    create_res = await client.post(
        "/api/complaints",
        json={"text": "Spam complaint message testing rejection", "location": "Test Area"},
    )
    cid = create_res.json()["id"]

    # Advance open -> rejected (valid)
    rej = await client.patch(f"/api/complaints/{cid}/status", json={"status": "rejected"})
    assert rej.status_code == 200
    assert rej.json()["status"] == "rejected"

    # Try rejected -> open (rejected is terminal, 409)
    rej_invalid = await client.patch(f"/api/complaints/{cid}/status", json={"status": "open"})
    assert rej_invalid.status_code == 409
    assert "Invalid transition from rejected to open" in rej_invalid.json()["detail"]

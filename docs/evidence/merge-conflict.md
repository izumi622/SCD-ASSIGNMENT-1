# Merge Conflict Demonstration & Resolution Scenario

This document simulates a real-world merge conflict scenario encountered during the development of CivicPulse, detailing the conflict cause, git commands, conflict markers, resolution methodology, and validation steps.

---

## 1. Conflict Scenario Context

Two engineers work concurrently on complaint status transition handling in `app/services/complaint.py`:

- **Engineer A (`feat/state-machine-logging`)**: Modifies `update_status` to log structured audit events whenever a status changes.
- **Engineer B (`fix/status-transition-409`)**: Modifies the exact same `update_status` function to enforce the state machine table and raise an `HTTPException(409)` with a descriptive error string.

Because both branches modified identical lines of the `update_status` method before merging to `develop`, Git cannot resolve the change automatically and flags a merge conflict.

---

## 2. Reproduction Script

The following Git commands reproduce the conflict:

```bash
# 1. Base branch
git checkout develop
git pull origin develop

# 2. Engineer A creates branch and adds audit logging
git checkout -b feat/state-machine-logging
# Edit app/services/complaint.py: add logger.info("Status transition audit...")
git commit -am "feat(complaint): add audit logging to status update"
git push origin feat/state-machine-logging

# 3. Meanwhile, Engineer B creates branch and modifies status transition validation
git checkout develop
git checkout -b fix/status-transition-409
# Edit app/services/complaint.py: add is_valid_transition check and 409 exception
git commit -am "fix(state-machine): enforce transition table with 409 conflict"
git push origin fix/status-transition-409

# 4. Engineer B merges first into develop
git checkout develop
git merge fix/status-transition-409
git push origin develop

# 5. Engineer A attempts to rebase or merge develop into their branch
git checkout feat/state-machine-logging
git merge develop
# ---> CONFLICT (content): Merge conflict in app/services/complaint.py
# Automatic merge failed; fix conflicts and then commit the result.
```

---

## 3. Conflict Markers in Code

Opening `app/services/complaint.py` reveals the Git conflict markers:

```python
<<<<<<< HEAD (feat/state-machine-logging)
        # Engineer A's modification: audit logging
        logger.info(
            f"AUDIT: Status transition requested for {complaint.id} to {update.status.value}"
        )
        updated = await self.repository.update_status(complaint, update.status.value)
=======
        # Engineer B's modification: state machine enforcement
        current_status = Status(complaint.status)
        target_status = update.status
        if not is_valid_transition(current_status, target_status):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Invalid transition from {current_status.value} to {target_status.value}",
            )
        updated = await self.repository.update_status(complaint, target_status.value)
>>>>>>> develop (fix/status-transition-409)
```

---

## 4. Conflict Resolution Strategy

### Rationale
Both changes are valuable and non-contradictory:
1. **Validation must occur first**: The state machine must reject invalid transitions with HTTP 409 before any state changes or logging.
2. **Audit logging occurs upon validation success**: Once validated, the audit log should record the transition.
3. **Repository update and cache invalidation execute together**.

### Resolved Code
```python
        complaint = await self.get_complaint(complaint_id)
        current_status = Status(complaint.status)
        target_status = update.status

        # 1. Enforce transition table (§2.2)
        if not is_valid_transition(current_status, target_status):
            error_message = (
                f"Invalid transition from {current_status.value} to {target_status.value}"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_message,
            )

        # 2. Audit log valid transition
        logger.info(
            f"AUDIT: Status transition for {complaint.id} from {current_status.value} to {target_status.value}",
            extra={"complaint_id": str(complaint.id), "from": current_status.value, "to": target_status.value},
        )

        # 3. Update database and invalidate stats cache
        updated = await self.repository.update_status(complaint, target_status.value)
        await self.cache_provider.invalidate_stats_cache()
        return updated
```

---

## 5. Verification Commands

Following resolution, the engineer verifies that no syntax errors were introduced and that all tests pass:

```bash
# Mark conflict resolved and complete merge
git add app/services/complaint.py
git commit -m "chore(merge): resolve conflict between status audit logging and 409 validation"

# Run backend tests to verify state machine integrity
pytest tests/test_state_machine.py -v
pytest tests/ -v --cov=app

# Output:
# ================= 35 passed in 2.15s =================
```

Both tests for invalid state transition 409 exceptions and happy-path transitions succeed with 100% pass rate.

from pathlib import Path
from datetime import datetime, timezone
import shutil
import os

root = Path.cwd()
scheduler = root / "backend" / "app" / "scheduler.py"
module = root / "backend" / "app" / "ceo_orchestration.py"

source = scheduler.read_text(encoding="utf-8")

anchor1 = (
    "    next_idea_at = time.monotonic() + initial_idea_delay\n"
    "    idea_retry_delay = max(120, min(600, interval_seconds * 3))"
)

anchor2 = "            if time.monotonic() >= next_idea_at:\n"

if "run_ceo_planning_cycle" in source:
    print("CEO scheduler integration already exists. No scheduler changes made.")
else:
    if source.count(anchor1) != 1 or source.count(anchor2) != 1:
        raise SystemExit(
            "Source did not match the expected scheduler structure. "
            "No files were changed."
        )

    backup_dir = root / "upgrade_backups"
    backup_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(scheduler, backup_dir / f"scheduler_{stamp}.py.bak")

    source = source.replace(
        anchor1,
        anchor1 + "\n"
        "    next_ceo_at = time.monotonic() + _env_int("
        '"AI_MONEY_TOWN_CEO_INTERVAL_SECONDS", 900, 300, 86400)\n',
        1,
    )

    hook = '''            if time.monotonic() >= next_ceo_at:
                try:
                    from .ceo_orchestration import run_ceo_planning_cycle
                    ceo_report = await asyncio.to_thread(
                        run_ceo_planning_cycle, database, ollama, model_lock
                    )
                    logger.info(
                        "CEO planning cycle: %s task(s) delegated.",
                        ceo_report.get("delegated_count", 0),
                    )
                except Exception:
                    logger.exception("CEO planning cycle failed; it will retry later.")
                next_ceo_at = time.monotonic() + _env_int(
                    "AI_MONEY_TOWN_CEO_INTERVAL_SECONDS", 900, 300, 86400
                )

'''
    source = source.replace(anchor2, hook + anchor2, 1)

    temp = scheduler.with_suffix(".py.tmp")
    temp.write_text(source, encoding="utf-8")
    temp.replace(scheduler)
    print("Scheduler integration installed.")

module_source = r'''
from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import time
from datetime import datetime, timezone


EMPLOYEE_MISSIONS = {
    "researcher": "research",
    "strategist": "strategy",
    "builder": "development",
    "marketer": "marketing",
    "finance-analyst": "town_management",
    "operations": "quality",
    "community-manager": "community",
}

BLOCKED_ACTIONS = (
    "send email", "send emails", "contact customers", "contact a customer",
    "message customers", "purchase", "buy advertising", "spend money",
    "make payment", "withdraw money", "public launch", "launch publicly",
    "publish publicly", "sign contract", "hire someone", "place an order",
)


def validate_plan(payload):
    """Validate an AI-generated plan before it can create work."""
    if not isinstance(payload, dict):
        return {"summary": "Invalid plan format.", "delegations": []}

    summary = str(payload.get("summary", "")).strip()[:1200]
    raw = payload.get("delegations", [])
    if not isinstance(raw, list):
        raw = []

    clean = []
    seen = set()

    for item in raw:
        if not isinstance(item, dict):
            continue

        employee = str(item.get("employee_id", "")).strip()
        if employee not in EMPLOYEE_MISSIONS:
            continue

        title = re.sub(r"\s+", " ", str(item.get("title", ""))).strip()
        description = re.sub(
            r"\s+", " ", str(item.get("description", ""))
        ).strip()

        if not title or not description:
            continue
        if len(title) > 140 or len(description) > 1800:
            continue

        combined = (title + " " + description).lower()
        if any(term in combined for term in BLOCKED_ACTIONS):
            continue

        mission = EMPLOYEE_MISSIONS[employee]
        identity = (employee, title.lower(), description.lower())
        if identity in seen:
            continue
        seen.add(identity)

        try:
            priority = int(item.get("priority", 0))
        except (TypeError, ValueError):
            priority = 0

        clean.append({
            "employee_id": employee,
            "title": title,
            "description": description,
            "mission_type": mission,
            "priority": max(-10, min(10, priority)),
        })

        if len(clean) >= 3:
            break

    return {"summary": summary, "delegations": clean}


def _call_local_model(ollama, prompt):
    method = getattr(ollama, "chat_json", None)
    if not callable(method):
        raise RuntimeError("Ollama JSON chat method is unavailable.")

    signature = inspect.signature(method)
    params = signature.parameters
    kwargs = {}

    messages = [
        {
            "role": "system",
            "content": (
                "You are Mayor Wafflebeard, CEO of AI Money Town. "
                "Plan internal work only. Never claim unverified research, "
                "customers, sales, revenue, or completed work. Never authorize "
                "spending, public launches, external outreach, contracts, or "
                "withdrawals. Return valid JSON only."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    if "messages" in params:
        kwargs["messages"] = messages
    elif "prompt" in params:
        kwargs["prompt"] = prompt
    elif "user_prompt" in params:
        kwargs["user_prompt"] = prompt
    elif "content" in params:
        kwargs["content"] = prompt
    else:
        raise RuntimeError(
            "Unsupported Ollama chat_json signature; no model call was made."
        )

    if "model" in params:
        kwargs["model"] = os.getenv(
            "AI_MONEY_TOWN_CEO_MODEL", "qwen3:4b"
        )
    if "temperature" in params:
        kwargs["temperature"] = 0.2
    if "timeout" in params:
        kwargs["timeout"] = 180

    for name, parameter in params.items():
        if (
            name not in kwargs
            and name != "self"
            and parameter.default is inspect.Parameter.empty
            and parameter.kind not in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            )
        ):
            raise RuntimeError(
                f"Unsupported required Ollama argument: {name}"
            )

    result = method(**kwargs)

    if isinstance(result, dict):
        return result
    if isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", result, re.DOTALL)
            if match:
                return json.loads(match.group(0))
    raise RuntimeError("Ollama returned no valid JSON plan.")


def run_ceo_planning_cycle(database, ollama, model_lock=None):
    """Create a bounded, validated, auditable set of internal tasks."""
    lock_acquired = False
    if model_lock is not None:
        lock_acquired = model_lock.acquire(timeout=2)
        if not lock_acquired:
            return {"delegated_count": 0, "status": "model_busy"}

    try:
        with database.connect() as connection:
            employees = [
                dict(row)
                for row in connection.execute(
                    "SELECT id, name, role, specialty FROM employees "
                    "WHERE id != 'town-manager' ORDER BY rowid"
                )
            ]

            active = {
                row["employee_id"]: row["count"]
                for row in connection.execute(
                    """
                    SELECT employee_id, COUNT(*) AS count
                    FROM tasks
                    WHERE status IN ('pending', 'in_progress')
                    GROUP BY employee_id
                    """
                )
            }

            task_rows = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT employee_id, title, status, mission_type
                    FROM tasks ORDER BY id DESC LIMIT 35
                    """
                )
            ]

            business_rows = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT b.id, i.title, b.stage
                    FROM businesses b
                    JOIN business_ideas i ON i.id = b.idea_id
                    ORDER BY b.id DESC LIMIT 15
                    """
                )
            ]

            finance_row = connection.execute(
                """
                SELECT COALESCE(SUM(
                    CASE WHEN transaction_type = 'payment_settled'
                    THEN amount_cents ELSE 0 END
                ), 0) AS settled_receipts
                FROM transactions
                """
            ).fetchone()

        prompt = (
            "Prepare the next internal work plan for AI Money Town.\n"
            "Return JSON with exactly these keys: summary, delegations.\n"
            "delegations must be an array of objects with employee_id, title, "
            "description, priority.\n"
            "Use only these employee IDs: "
            + ", ".join(e["id"] for e in employees)
            + ". Assign work matching their specialties. Do not assign "
            "more than three tasks total. Prefer useful, testable work. "
            "Do not repeat existing active tasks. Do not request spending, "
            "external outreach, public launches, publishing, purchases, "
            "contracts, hiring, payments, or withdrawals. Research must be "
            "labelled as hypotheses unless independently verified. "
            "Do not describe estimates as actual revenue.\n\n"
            "Employee roster:\n" + json.dumps(employees)
            + "\nCurrent active task counts:\n" + json.dumps(active)
            + "\nRecent task history:\n" + json.dumps(task_rows)
            + "\nBusiness portfolio:\n" + json.dumps(business_rows)
            + "\nSettled ledger receipts in cents (not profit): "
            + str(int(finance_row["settled_receipts"]))
        )

        payload = _call_local_model(ollama, prompt)
        plan = validate_plan(payload)

        now = datetime.now(timezone.utc).isoformat()
        bucket = int(time.time() // 900)
        created_ids = []

        with database.connect() as connection:
            for task in plan["delegations"]:
                employee_id = task["employee_id"]

                active_count = connection.execute(
                    """
                    SELECT COUNT(*) FROM tasks
                    WHERE employee_id = ?
                    AND status IN ('pending', 'in_progress')
                    """,
                    (employee_id,),
                ).fetchone()[0]

                if active_count >= 3:
                    continue

                fingerprint = hashlib.sha256(
                    (
                        employee_id + "|" + task["title"].lower()
                        + "|" + task["description"].lower()
                    ).encode("utf-8")
                ).hexdigest()[:20]

                dedupe_key = (
                    f"ceo:{employee_id}:{fingerprint}:{bucket}"
                )

                existing = connection.execute(
                    "SELECT id FROM tasks WHERE dedupe_key = ?",
                    (dedupe_key,),
                ).fetchone()
                if existing:
                    continue

                cursor = connection.execute(
                    """
                    INSERT INTO tasks (
                        title, description, employee_id, status,
                        created_at, updated_at, task_kind, mission_type,
                        dedupe_key, priority
                    )
                    VALUES (?, ?, ?, 'pending', ?, ?, 'owner', ?, ?, ?)
                    """,
                    (
                        task["title"], task["description"], employee_id,
                        now, now, task["mission_type"], dedupe_key,
                        task["priority"],
                    ),
                )
                created_ids.append(cursor.lastrowid)

            report = {
                "created_at": now,
                "summary": plan["summary"],
                "delegated_count": len(created_ids),
                "delegated_task_ids": created_ids,
                "status": "completed",
                "safety": {
                    "internal_tasks_only": True,
                    "owner_approval_required_for_external_actions": True,
                    "estimates_are_not_verified_revenue": True,
                },
            }

            connection.execute(
                """
                INSERT INTO management_reports
                    (report_type, content, created_at)
                VALUES (?, ?, ?)
                """,
                (
                    "ceo_plan",
                    json.dumps(report, separators=(",", ":")),
                    now,
                ),
            )

            connection.execute(
                """
                DELETE FROM management_reports
                WHERE id NOT IN (
                    SELECT id FROM management_reports
                    ORDER BY id DESC LIMIT 500
                )
                """
            )

        return report

    finally:
        if lock_acquired:
            model_lock.release()
'''

module.write_text(module_source.lstrip(), encoding="utf-8")
print("CEO orchestration module installed.")

tests = root / "backend" / "tests" / "test_ceo_orchestration.py"
test_source = r'''
from backend.app.ceo_orchestration import validate_plan


def test_plan_limits_delegations_to_three():
    plan = validate_plan({
        "summary": "A plan",
        "delegations": [
            {"employee_id": "researcher", "title": f"Task {i}",
             "description": "Investigate an internal product question."}
            for i in range(8)
        ],
    })
    assert len(plan["delegations"]) == 3


def test_unknown_employee_is_rejected():
    plan = validate_plan({
        "delegations": [
            {"employee_id": "unknown", "title": "Task",
             "description": "Do useful internal work."}
        ]
    })
    assert plan["delegations"] == []


def test_external_actions_are_rejected():
    plan = validate_plan({
        "delegations": [
            {"employee_id": "marketer", "title": "Send email",
             "description": "Send email to customers today."}
        ]
    })
    assert plan["delegations"] == []


def test_duplicate_delegations_are_removed():
    item = {
        "employee_id": "researcher",
        "title": "Investigate a product problem",
        "description": "Study an internal product question."
    }
    plan = validate_plan({"delegations": [item, item]})
    assert len(plan["delegations"]) == 1


def test_invalid_and_empty_tasks_are_rejected():
    plan = validate_plan({
        "delegations": [
            {"employee_id": "builder", "title": "", "description": "Build it"},
            {"employee_id": "builder", "title": "Build it", "description": ""}
        ]
    })
    assert plan["delegations"] == []


def test_mission_type_is_assigned_by_employee_role():
    plan = validate_plan({
        "delegations": [
            {"employee_id": "operations", "title": "Review prototype",
             "description": "Check the prototype for reproducible bugs."}
        ]
    })
    assert plan["delegations"][0]["mission_type"] == "quality"
'''
tests.write_text(test_source.lstrip(), encoding="utf-8")
print("CEO validation tests installed.")

runner = root / "TEST_AUTONOMOUS_TOWN.ps1"
runner_source = r'''
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (!(Test-Path $Python)) {
    throw "Project virtual environment not found."
}

Write-Host "`n[1/4] Checking Python syntax..." -ForegroundColor Cyan
& $Python -m compileall -q backend
if ($LASTEXITCODE -ne 0) { throw "Python compilation failed." }

Write-Host "`n[2/4] Running CEO planning validation tests..." -ForegroundColor Cyan
& $Python -m pytest backend\tests\test_ceo_orchestration.py -q
if ($LASTEXITCODE -ne 0) { throw "CEO planning tests failed." }

Write-Host "`n[3/4] Running the complete backend regression suite..." -ForegroundColor Cyan
& $Python -m pytest backend\tests -q
if ($LASTEXITCODE -ne 0) { throw "Backend regression tests failed." }

Write-Host "`n[4/4] Checking scheduler integration..." -ForegroundColor Cyan
$Scheduler = Get-Content "backend\app\scheduler.py" -Raw
$Module = Test-Path "backend\app\ceo_orchestration.py"
$Hook = $Scheduler.Contains("run_ceo_planning_cycle")
$Report = $Scheduler.Contains("AI_MONEY_TOWN_CEO_INTERVAL_SECONDS")

if (!$Module -or !$Hook -or !$Report) {
    throw "CEO integration check failed."
}

Write-Host "`nALL LOCAL TESTS PASSED." -ForegroundColor Green
Write-Host "No cloud deployment was performed."
'''
runner.write_text(runner_source.lstrip(), encoding="utf-8")
print("Comprehensive local test runner created.")

print("\nUpgrade files created successfully.")

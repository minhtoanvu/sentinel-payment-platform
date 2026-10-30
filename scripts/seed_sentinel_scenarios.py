import asyncio
import io
import os
import re
import sys
from datetime import datetime, timezone

# Ensure stdout and stderr support UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from payment_lab.db.session import async_session_factory, init_db
from sentinelqa.db.models import (
    QASeededDefect,
    Requirement,
    RequirementTestLink,
    RequirementVersion,
    TestCase,
    TestCaseVersion,
)


def parse_scenarios(markdown_path: str):
    with open(markdown_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Match test scenario table rows
    # | TS-001 | Kịch bản | Kỹ thuật | Mức | Ưu tiên | Requirement | Business rule | Kết quả mong đợi | Lỗi cài sẵn |
    scenario_pattern = re.compile(
        r"^\|\s*(TS-\d{3})\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]*)\s*\|$",
        re.MULTILINE,
    )

    scenarios = []
    for match in scenario_pattern.finditer(content):
        ts_id = match.group(1).strip()
        title = match.group(2).strip()
        technique = match.group(3).strip()
        level = match.group(4).strip()
        priority = match.group(5).strip()
        reqs = [r.strip() for r in match.group(6).split(",") if r.strip() and r.strip() != "—"]
        rules = [b.strip() for b in match.group(7).split(",") if b.strip() and b.strip() != "—"]
        expected = match.group(8).strip()
        defects = [d.strip() for d in match.group(9).split(",") if d.strip() and d.strip() != "—"]

        scenarios.append({
            "id": ts_id,
            "title": title,
            "technique": technique,
            "level": level,
            "priority": priority,
            "requirements": reqs,
            "rules": rules,
            "expected": expected,
            "defects": defects,
        })

    # Match seeded defects table rows
    # | BUG-001 | Refund | Kiểm tra refund dùng < thay <= | Cao | TS-036 |
    defect_pattern = re.compile(
        r"^\|\s*(BUG-\d{3})\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|$",
        re.MULTILINE,
    )

    defects = []
    for match in defect_pattern.finditer(content):
        bug_id = match.group(1).strip()
        category = match.group(2).strip()
        description = match.group(3).strip()
        severity = match.group(4).strip()
        scenarios_linked = [s.strip() for s in match.group(5).split(",") if s.strip()]

        defects.append({
            "code": bug_id,
            "category": category,
            "description": description,
            "severity": severity,
            "scenarios": scenarios_linked,
        })

    return scenarios, defects


async def seed_data():
    print("Initializing Database tables...")
    await init_db()

    # Search for test-scenarios.md
    possible_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "test-scenarios.md")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test-scenarios.md")),
    ]
    md_path = next((p for p in possible_paths if os.path.exists(p)), None)
    if not md_path:
        raise FileNotFoundError(f"Could not find test-scenarios.md in {possible_paths}")

    print(f"Reading scenarios from: {md_path}")
    scenarios, defects = parse_scenarios(md_path)
    print(f"Parsed {len(scenarios)} test scenarios and {len(defects)} seeded defects.")

    now = datetime.now(timezone.utc)

    async with async_session_factory() as session:
        # Collect all unique requirements
        unique_req_ids = set()
        for sc in scenarios:
            for r in sc["requirements"]:
                unique_req_ids.add(r)

        print(f"Discovered {len(unique_req_ids)} unique requirements.")

        # Seed Requirements
        req_map = {}
        for req_id in sorted(list(unique_req_ids)):
            existing = (await session.execute(select(Requirement).where(Requirement.public_id == req_id))).scalar_one_or_none()
            if not existing:
                req = Requirement(
                    public_id=req_id,
                    title=f"Requirement {req_id}",
                    priority="Must" if "PAY" in req_id or "REF" in req_id or "WH" in req_id else "Should",
                    severity="Critical" if "PAY" in req_id or "SEC" in req_id else "High",
                    created_at=now,
                )
                session.add(req)
                await session.flush()
                req_ver = RequirementVersion(
                    requirement_id=req.id,
                    version=1,
                    description=f"Specification for {req_id}",
                    acceptance_criteria=[f"Criteria for {req_id}"],
                    created_at=now,
                )
                session.add(req_ver)
                req_map[req_id] = req
            else:
                req_map[req_id] = existing

        # Seed Test Cases
        tc_map = {}
        for sc in scenarios:
            existing_tc = (await session.execute(select(TestCase).where(TestCase.public_id == sc["id"]))).scalar_one_or_none()
            if not existing_tc:
                tc = TestCase(
                    public_id=sc["id"],
                    title=sc["title"],
                    level=sc["level"],
                    priority=sc["priority"],
                    status="APPROVED",
                    origin="HUMAN",
                    created_at=now,
                )
                session.add(tc)
                await session.flush()

                tc_ver = TestCaseVersion(
                    test_case_id=tc.id,
                    version=1,
                    steps=[f"Execute technique: {sc['technique']}", f"Verify business rules: {', '.join(sc['rules'])}"],
                    expected_result=sc["expected"],
                    approved_by="qa_architect",
                    created_at=now,
                )
                session.add(tc_ver)
                tc_map[sc["id"]] = tc
            else:
                tc_map[sc["id"]] = existing_tc

        await session.flush()

        # Seed Requirement-Test Links
        link_count = 0
        for sc in scenarios:
            tc = tc_map[sc["id"]]
            for r_id in sc["requirements"]:
                req = req_map.get(r_id)
                if req:
                    existing_link = (await session.execute(
                        select(RequirementTestLink).where(
                            RequirementTestLink.requirement_id == req.id,
                            RequirementTestLink.test_case_id == tc.id,
                        )
                    )).scalar_one_or_none()
                    if not existing_link:
                        link = RequirementTestLink(
                            requirement_id=req.id,
                            test_case_id=tc.id,
                        )
                        session.add(link)
                        link_count += 1

        # Seed Defects
        for bug in defects:
            existing_bug = (await session.execute(
                select(QASeededDefect).where(QASeededDefect.seeded_code == bug["code"])
            )).scalar_one_or_none()
            if not existing_bug:
                # Map to first linked scenario requirement if available
                req_id_fk = None
                if bug["scenarios"]:
                    first_sc_id = bug["scenarios"][0]
                    first_sc = next((s for s in scenarios if s["id"] == first_sc_id), None)
                    if first_sc and first_sc["requirements"]:
                        mapped_req = req_map.get(first_sc["requirements"][0])
                        if mapped_req:
                            req_id_fk = mapped_req.id

                d = QASeededDefect(
                    seeded_code=bug["code"],
                    severity=bug["severity"],
                    description=f"[{bug['category']}] {bug['description']}",
                    status="ACTIVE",
                    requirement_id=req_id_fk,
                )
                session.add(d)

        await session.commit()
        print(f"Successfully seeded {len(tc_map)} Test Cases, {len(req_map)} Requirements, {link_count} Links, and {len(defects)} Defects into SentinelQA!")


if __name__ == "__main__":
    asyncio.run(seed_data())

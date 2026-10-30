import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from payment_lab.db.models import Base, ensure_utc, gen_uuid, now_utc


class Requirement(Base):
    __tablename__ = "qa_requirements"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    public_id = Column(String(64), unique=True, nullable=False, index=True)  # FR-PAY-001
    title = Column(String(255), nullable=False)
    priority = Column(String(50), nullable=False, default="Must")  # Must, Should, Could
    severity = Column(String(50), nullable=False, default="High")  # Critical, High, Medium, Low
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    versions = relationship("RequirementVersion", back_populates="requirement", cascade="all, delete-orphan", lazy="selectin")
    test_links = relationship("RequirementTestLink", back_populates="requirement", cascade="all, delete-orphan", lazy="selectin")


class RequirementVersion(Base):
    __tablename__ = "qa_requirement_versions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    requirement_id = Column(String(36), ForeignKey("qa_requirements.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    description = Column(Text, nullable=False)
    acceptance_criteria = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    requirement = relationship("Requirement", back_populates="versions", lazy="selectin")


class TestCase(Base):
    __tablename__ = "qa_test_cases"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    public_id = Column(String(64), unique=True, nullable=False, index=True)  # TS-001
    title = Column(String(255), nullable=False)
    level = Column(String(50), nullable=False, default="API")  # UNIT, API, INT, CONC, UI, SEC, AI
    priority = Column(String(50), nullable=False, default="P0")  # P0, P1, P2
    status = Column(String(50), nullable=False, default="APPROVED")  # DRAFT, APPROVED, DEPRECATED
    origin = Column(String(50), nullable=False, default="HUMAN")  # HUMAN, AI
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    versions = relationship("TestCaseVersion", back_populates="test_case", cascade="all, delete-orphan", lazy="selectin")
    requirement_links = relationship("RequirementTestLink", back_populates="test_case", cascade="all, delete-orphan", lazy="selectin")
    results = relationship("TestResult", back_populates="test_case", cascade="all, delete-orphan", lazy="selectin")


class TestCaseVersion(Base):
    __tablename__ = "qa_test_case_versions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    test_case_id = Column(String(36), ForeignKey("qa_test_cases.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    steps = Column(JSON, nullable=True)
    expected_result = Column(Text, nullable=True)
    approved_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    test_case = relationship("TestCase", back_populates="versions", lazy="selectin")


class RequirementTestLink(Base):
    __tablename__ = "qa_requirement_test_links"
    __table_args__ = (
        UniqueConstraint("requirement_id", "test_case_id", name="uq_req_test_link"),
    )

    id = Column(String(36), primary_key=True, default=gen_uuid)
    requirement_id = Column(String(36), ForeignKey("qa_requirements.id"), nullable=False, index=True)
    test_case_id = Column(String(36), ForeignKey("qa_test_cases.id"), nullable=False, index=True)

    requirement = relationship("Requirement", back_populates="test_links", lazy="selectin")
    test_case = relationship("TestCase", back_populates="requirement_links", lazy="selectin")


class TestRun(Base):
    __tablename__ = "qa_test_runs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    commit_sha = Column(String(64), nullable=False, index=True)
    environment = Column(String(50), nullable=False, default="test")
    runner_version = Column(String(50), nullable=False, default="pytest-9.0")
    trigger = Column(String(50), nullable=False, default="CI")
    started_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    results = relationship("TestResult", back_populates="run", cascade="all, delete-orphan", lazy="selectin")
    decision = relationship("ReleaseDecision", back_populates="run", uselist=False, lazy="selectin")


class TestResult(Base):
    __tablename__ = "qa_test_results"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    run_id = Column(String(36), ForeignKey("qa_test_runs.id"), nullable=False, index=True)
    test_case_id = Column(String(36), ForeignKey("qa_test_cases.id"), nullable=False, index=True)
    outcome = Column(String(50), nullable=False)  # PASS, FAIL, ERROR, SKIPPED
    failure_class = Column(String(50), nullable=False, default="UNKNOWN")  # ASSERTION, APPLICATION_ERROR, TIMEOUT, ENVIRONMENT, UNKNOWN
    duration_ms = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)

    run = relationship("TestRun", back_populates="results", lazy="selectin")
    test_case = relationship("TestCase", back_populates="results", lazy="selectin")


class ReleaseDecision(Base):
    __tablename__ = "qa_release_decisions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    run_id = Column(String(36), ForeignKey("qa_test_runs.id"), unique=True, nullable=False, index=True)
    decision = Column(String(50), nullable=False)  # PASS, WARN, BLOCK
    rule_ids = Column(JSON, nullable=False)
    input_snapshot = Column(JSON, nullable=False)
    thresholds = Column(JSON, nullable=False)
    ruleset_version = Column(String(50), nullable=False, default="1.0.0")
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    run = relationship("TestRun", back_populates="decision", lazy="selectin")


class QASeededDefect(Base):
    __tablename__ = "qa_seeded_defects"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    requirement_id = Column(String(36), ForeignKey("qa_requirements.id"), nullable=True)
    seeded_code = Column(String(50), unique=True, nullable=False)  # BUG-001..018
    severity = Column(String(50), nullable=False)  # Critical, High, Medium, Low
    description = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="ACTIVE")


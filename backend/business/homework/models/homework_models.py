"""Homework module — ORM models (D2, D4, D5)."""

from __future__ import annotations
import uuid
from datetime import date, datetime
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from kernel.db import Base


class Homework(Base):
    __tablename__ = "homework"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("client.id"), nullable=False)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institution.id"), nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    subject = Column(Text, nullable=True)
    grade_level = Column(Text, nullable=True)
    section = Column(Text, nullable=True)
    due_date = Column(Date, nullable=False)
    max_score = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="active")
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("app_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Submission(Base):
    __tablename__ = "submission"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("client.id"), nullable=False)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institution.id"), nullable=False)
    homework_id = Column(UUID(as_uuid=True), ForeignKey("homework.id"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("app_user.id"), nullable=False)
    content = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="submitted")
    submitted_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Grade(Base):
    __tablename__ = "grade"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("client.id"), nullable=False)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institution.id"), nullable=False)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("submission.id"), nullable=False)
    score = Column(Integer, nullable=False)
    max_score = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)
    graded_by = Column(UUID(as_uuid=True), ForeignKey("app_user.id"), nullable=True)
    graded_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

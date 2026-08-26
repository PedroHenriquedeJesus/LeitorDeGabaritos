from datetime import date, datetime
from enum import Enum

from sqlalchemy import Date, DateTime, Enum as SqlEnum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, Enum):
    admin = "admin"
    teacher = "teacher"


class AssignmentStatus(str, Enum):
    draft = "draft"
    active = "active"
    corrected = "corrected"
    archived = "archived"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole), default=UserRole.teacher)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    students: Mapped[list["Student"]] = relationship(back_populates="owner")
    classes: Mapped[list["Classroom"]] = relationship(back_populates="owner")
    exams: Mapped[list["Exam"]] = relationship(back_populates="owner")
    auth_sessions: Mapped[list["AuthSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)

    user: Mapped["User"] = relationship(back_populates="auth_sessions")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    email: Mapped[str | None] = mapped_column(String(160))
    enrollment_code: Mapped[str | None] = mapped_column(String(80), index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    owner: Mapped["User"] = relationship(back_populates="students")
    classrooms: Mapped[list["ClassroomStudent"]] = relationship(back_populates="student", cascade="all, delete-orphan")


class Classroom(Base):
    __tablename__ = "classrooms"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), index=True)
    course_name: Mapped[str | None] = mapped_column(String(120))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    owner: Mapped["User"] = relationship(back_populates="classes")
    students: Mapped[list["ClassroomStudent"]] = relationship(back_populates="classroom", cascade="all, delete-orphan")
    assignments: Mapped[list["ExamAssignment"]] = relationship(back_populates="classroom")


class ClassroomStudent(Base):
    __tablename__ = "classroom_students"
    __table_args__ = (UniqueConstraint("classroom_id", "student_id", name="uq_classroom_student"),)

    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id"), primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), primary_key=True)

    classroom: Mapped["Classroom"] = relationship(back_populates="students")
    student: Mapped["Student"] = relationship(back_populates="classrooms")


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(String(500))
    exam_date: Mapped[date | None] = mapped_column(Date)
    question_count: Mapped[int] = mapped_column(Integer)
    option_count: Mapped[int] = mapped_column(Integer)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    owner: Mapped["User"] = relationship(back_populates="exams")
    answer_key: Mapped[list["AnswerKeyItem"]] = relationship(back_populates="exam", cascade="all, delete-orphan")
    assignments: Mapped[list["ExamAssignment"]] = relationship(back_populates="exam", cascade="all, delete-orphan")


class AnswerKeyItem(Base):
    __tablename__ = "answer_key_items"

    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), primary_key=True)
    question_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    option_index: Mapped[int] = mapped_column(Integer)
    weight: Mapped[int] = mapped_column(Integer, default=1)

    exam: Mapped["Exam"] = relationship(back_populates="answer_key")


class ExamAssignment(Base):
    __tablename__ = "exam_assignments"
    __table_args__ = (UniqueConstraint("exam_id", "classroom_id", name="uq_exam_classroom"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"))
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id"))
    status: Mapped[AssignmentStatus] = mapped_column(SqlEnum(AssignmentStatus), default=AssignmentStatus.active)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    exam: Mapped["Exam"] = relationship(back_populates="assignments")
    classroom: Mapped["Classroom"] = relationship(back_populates="assignments")
    correction_results: Mapped[list["CorrectionResult"]] = relationship(back_populates="assignment", cascade="all, delete-orphan")


class CorrectionResult(Base):
    __tablename__ = "correction_results"
    __table_args__ = (UniqueConstraint("assignment_id", "student_id", name="uq_assignment_student_result"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("exam_assignments.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    score: Mapped[float] = mapped_column(Float, default=0)
    max_score: Mapped[float] = mapped_column(Float, default=0)
    source_filename: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    assignment: Mapped["ExamAssignment"] = relationship(back_populates="correction_results")
    student: Mapped["Student"] = relationship()
    answers: Mapped[list["CorrectionAnswer"]] = relationship(back_populates="result", cascade="all, delete-orphan")


class CorrectionAnswer(Base):
    __tablename__ = "correction_answers"

    result_id: Mapped[int] = mapped_column(ForeignKey("correction_results.id"), primary_key=True)
    question_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    selected_option: Mapped[int] = mapped_column(Integer)
    correct_option: Mapped[int] = mapped_column(Integer)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    awarded: Mapped[float] = mapped_column(Float, default=0)

    result: Mapped["CorrectionResult"] = relationship(back_populates="answers")

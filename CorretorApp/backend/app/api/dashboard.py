from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.api.exams import to_assignment_read, to_exam_read
from app.core.database import get_db
from app.models import AssignmentStatus, Classroom, Exam, ExamAssignment, Student, User
from app.schemas import DashboardRead

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardRead)
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> DashboardRead:
    student_count = db.scalar(select(func.count(Student.id)).where(Student.owner_id == user.id)) or 0
    classroom_count = db.scalar(select(func.count(Classroom.id)).where(Classroom.owner_id == user.id)) or 0
    exam_count = db.scalar(select(func.count(Exam.id)).where(Exam.owner_id == user.id)) or 0
    active_assignment_count = (
        db.scalar(
            select(func.count(ExamAssignment.id))
            .join(Exam)
            .where(Exam.owner_id == user.id, ExamAssignment.status == AssignmentStatus.active)
        )
        or 0
    )
    recent_exams = db.scalars(
        select(Exam)
        .options(selectinload(Exam.answer_key), selectinload(Exam.assignments))
        .where(Exam.owner_id == user.id)
        .order_by(Exam.created_at.desc())
        .limit(4)
    )
    recent_assignments = db.scalars(
        select(ExamAssignment)
        .join(Exam)
        .options(selectinload(ExamAssignment.exam), selectinload(ExamAssignment.classroom))
        .where(Exam.owner_id == user.id)
        .order_by(ExamAssignment.assigned_at.desc())
        .limit(5)
    )
    return DashboardRead(
        students=student_count,
        classrooms=classroom_count,
        exams=exam_count,
        active_assignments=active_assignment_count,
        recent_exams=[to_exam_read(exam) for exam in recent_exams],
        recent_assignments=[to_assignment_read(assignment) for assignment in recent_assignments],
    )

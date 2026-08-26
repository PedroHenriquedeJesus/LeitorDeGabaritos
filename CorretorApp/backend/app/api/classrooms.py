from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Classroom, ClassroomStudent, CorrectionResult, ExamAssignment, Student, User
from app.schemas import ClassroomCreate, ClassroomRead, ClassroomUpdate

router = APIRouter(prefix="/classrooms", tags=["classrooms"])


def to_classroom_read(classroom: Classroom) -> ClassroomRead:
    return ClassroomRead(
        id=classroom.id,
        name=classroom.name,
        course_name=classroom.course_name,
        student_count=len(classroom.students),
        created_at=classroom.created_at,
    )


@router.get("", response_model=list[ClassroomRead])
def list_classrooms(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ClassroomRead]:
    classrooms = db.scalars(
        select(Classroom).options(selectinload(Classroom.students)).where(Classroom.owner_id == user.id).order_by(Classroom.name)
    )
    return [to_classroom_read(classroom) for classroom in classrooms]


@router.post("", response_model=ClassroomRead, status_code=status.HTTP_201_CREATED)
def create_classroom(payload: ClassroomCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ClassroomRead:
    valid_student_ids = set(
        db.scalars(select(Student.id).where(Student.owner_id == user.id, Student.id.in_(payload.student_ids))).all()
    )
    classroom = Classroom(name=payload.name, course_name=payload.course_name, owner_id=user.id)
    db.add(classroom)
    db.flush()
    db.add_all([ClassroomStudent(classroom_id=classroom.id, student_id=student_id) for student_id in valid_student_ids])
    db.commit()
    db.refresh(classroom)
    classroom = db.scalars(
        select(Classroom).options(selectinload(Classroom.students)).where(Classroom.id == classroom.id)
    ).one()
    return to_classroom_read(classroom)


@router.put("/{classroom_id}", response_model=ClassroomRead)
def update_classroom(
    classroom_id: int,
    payload: ClassroomUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ClassroomRead:
    classroom = db.get(Classroom, classroom_id)
    if not classroom or classroom.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Turma nao encontrada")

    classroom.name = payload.name
    classroom.course_name = payload.course_name
    if payload.student_ids is not None:
        valid_student_ids = set(
            db.scalars(select(Student.id).where(Student.owner_id == user.id, Student.id.in_(payload.student_ids))).all()
        )
        db.query(ClassroomStudent).filter(ClassroomStudent.classroom_id == classroom.id).delete(synchronize_session=False)
        db.add_all([ClassroomStudent(classroom_id=classroom.id, student_id=student_id) for student_id in valid_student_ids])
    db.commit()
    classroom = db.scalars(
        select(Classroom).options(selectinload(Classroom.students)).where(Classroom.id == classroom.id)
    ).one()
    return to_classroom_read(classroom)


@router.delete("/{classroom_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_classroom(classroom_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    classroom = db.get(Classroom, classroom_id)
    if not classroom or classroom.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Turma nao encontrada")
    assignments = list(db.scalars(select(ExamAssignment).where(ExamAssignment.classroom_id == classroom.id)))
    for assignment in assignments:
        results = list(db.scalars(select(CorrectionResult).where(CorrectionResult.assignment_id == assignment.id)))
        for result in results:
            db.delete(result)
        db.delete(assignment)
    db.flush()
    db.delete(classroom)
    db.commit()

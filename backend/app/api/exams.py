from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import AnswerKeyItem, Classroom, ClassroomStudent, CorrectionResult, Exam, ExamAssignment, User
from app.schemas import ExamAssignmentCreate, ExamAssignmentRead, ExamCreate, ExamRead, ExamUpdate
from app.services.answer_sheets import build_answer_sheet_pdf

router = APIRouter(prefix="/exams", tags=["exams"])


def to_exam_read(exam: Exam) -> ExamRead:
    return ExamRead(
        id=exam.id,
        title=exam.title,
        description=exam.description,
        exam_date=exam.exam_date,
        question_count=exam.question_count,
        option_count=exam.option_count,
        assignment_count=len(exam.assignments),
        created_at=exam.created_at,
        answer_key=sorted(exam.answer_key, key=lambda item: item.question_number),
    )


def to_assignment_read(assignment: ExamAssignment) -> ExamAssignmentRead:
    return ExamAssignmentRead(
        id=assignment.id,
        exam_id=assignment.exam_id,
        classroom_id=assignment.classroom_id,
        classroom_name=assignment.classroom.name,
        exam_title=assignment.exam.title,
        status=assignment.status,
        assigned_at=assignment.assigned_at,
    )


def delete_assignment_tree(db: Session, assignment: ExamAssignment) -> None:
    results = list(db.scalars(select(CorrectionResult).where(CorrectionResult.assignment_id == assignment.id)))
    for result in results:
        db.delete(result)
    db.delete(assignment)


@router.get("", response_model=list[ExamRead])
def list_exams(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ExamRead]:
    exams = db.scalars(
        select(Exam)
        .options(selectinload(Exam.answer_key), selectinload(Exam.assignments))
        .where(Exam.owner_id == user.id)
        .order_by(Exam.created_at.desc())
    )
    return [to_exam_read(exam) for exam in exams]


@router.post("", response_model=ExamRead, status_code=status.HTTP_201_CREATED)
def create_exam(payload: ExamCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ExamRead:
    if len(payload.answer_key) != payload.question_count:
        raise HTTPException(status_code=422, detail="O gabarito deve conter uma resposta por questao")

    exam = Exam(
        title=payload.title,
        description=payload.description,
        exam_date=payload.exam_date,
        question_count=payload.question_count,
        option_count=payload.option_count,
        owner_id=user.id,
    )
    db.add(exam)
    db.flush()
    db.add_all(
        [
            AnswerKeyItem(
                exam_id=exam.id,
                question_number=item.question_number,
                option_index=item.option_index,
                weight=item.weight,
            )
            for item in payload.answer_key
        ]
    )
    db.commit()
    exam = db.scalars(
        select(Exam).options(selectinload(Exam.answer_key), selectinload(Exam.assignments)).where(Exam.id == exam.id)
    ).one()
    return to_exam_read(exam)


@router.put("/{exam_id}", response_model=ExamRead)
def update_exam(
    exam_id: int,
    payload: ExamUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExamRead:
    if len(payload.answer_key) != payload.question_count:
        raise HTTPException(status_code=422, detail="O gabarito deve conter uma resposta por questao")
    exam = db.scalars(
        select(Exam)
        .options(selectinload(Exam.answer_key), selectinload(Exam.assignments))
        .where(Exam.id == exam_id, Exam.owner_id == user.id)
    ).first()
    if exam is None:
        raise HTTPException(status_code=404, detail="Prova nao encontrada")

    exam.title = payload.title
    exam.description = payload.description
    exam.exam_date = payload.exam_date
    exam.question_count = payload.question_count
    exam.option_count = payload.option_count
    assignment_ids = [assignment.id for assignment in exam.assignments]
    if assignment_ids:
        results = list(db.scalars(select(CorrectionResult).where(CorrectionResult.assignment_id.in_(assignment_ids))))
        for result in results:
            db.delete(result)
        db.flush()
    db.query(AnswerKeyItem).filter(AnswerKeyItem.exam_id == exam.id).delete(synchronize_session=False)
    db.flush()
    db.add_all(
        [
            AnswerKeyItem(
                exam_id=exam.id,
                question_number=item.question_number,
                option_index=item.option_index,
                weight=item.weight,
            )
            for item in payload.answer_key
        ]
    )
    db.commit()
    exam = db.scalars(
        select(Exam).options(selectinload(Exam.answer_key), selectinload(Exam.assignments)).where(Exam.id == exam.id)
    ).one()
    return to_exam_read(exam)


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(exam_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    exam = db.scalars(
        select(Exam)
        .options(selectinload(Exam.assignments))
        .where(Exam.id == exam_id, Exam.owner_id == user.id)
    ).first()
    if exam is None:
        raise HTTPException(status_code=404, detail="Prova nao encontrada")
    for assignment in list(exam.assignments):
        delete_assignment_tree(db, assignment)
    db.delete(exam)
    db.commit()


@router.post("/{exam_id}/assignments", response_model=list[ExamAssignmentRead], status_code=status.HTTP_201_CREATED)
def assign_exam(
    exam_id: int,
    payload: ExamAssignmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ExamAssignmentRead]:
    exam = db.get(Exam, exam_id)
    if not exam or exam.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Prova nao encontrada")

    classroom_ids = payload.classroom_ids or ([payload.classroom_id] if payload.classroom_id else [])
    if not classroom_ids:
        raise HTTPException(status_code=422, detail="Selecione pelo menos uma turma")

    classrooms = list(
        db.scalars(select(Classroom).where(Classroom.owner_id == user.id, Classroom.id.in_(classroom_ids)))
    )
    if len(classrooms) != len(set(classroom_ids)):
        raise HTTPException(status_code=404, detail="Uma ou mais turmas nao foram encontradas")

    existing_ids = set(
        db.scalars(
            select(ExamAssignment.classroom_id).where(
                ExamAssignment.exam_id == exam.id,
                ExamAssignment.classroom_id.in_([classroom.id for classroom in classrooms]),
            )
        )
    )
    created_ids: list[int] = []
    for classroom in classrooms:
        if classroom.id in existing_ids:
            continue
        assignment = ExamAssignment(exam_id=exam.id, classroom_id=classroom.id)
        db.add(assignment)
        db.flush()
        created_ids.append(assignment.id)

    db.commit()
    if not created_ids:
        raise HTTPException(status_code=409, detail="A prova ja esta atribuida para as turmas selecionadas")

    assignments = db.scalars(
        select(ExamAssignment)
        .options(selectinload(ExamAssignment.exam), selectinload(ExamAssignment.classroom))
        .where(ExamAssignment.id.in_(created_ids))
    )
    return [to_assignment_read(assignment) for assignment in assignments]


@router.get("/assignments", response_model=list[ExamAssignmentRead])
def list_assignments(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ExamAssignmentRead]:
    assignments = db.scalars(
        select(ExamAssignment)
        .join(Exam)
        .options(selectinload(ExamAssignment.exam), selectinload(ExamAssignment.classroom))
        .where(Exam.owner_id == user.id)
        .order_by(ExamAssignment.assigned_at.desc())
    )
    return [to_assignment_read(assignment) for assignment in assignments]


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    assignment = db.scalars(
        select(ExamAssignment)
        .join(Exam)
        .where(ExamAssignment.id == assignment_id, Exam.owner_id == user.id)
    ).first()
    if assignment is None:
        raise HTTPException(status_code=404, detail="Atribuicao nao encontrada")
    delete_assignment_tree(db, assignment)
    db.commit()


@router.get("/assignments/{assignment_id}/answer-sheets")
def download_answer_sheets(
    assignment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    assignment = db.scalars(
        select(ExamAssignment)
        .join(Exam)
        .options(
            selectinload(ExamAssignment.exam).selectinload(Exam.answer_key),
            selectinload(ExamAssignment.classroom).selectinload(Classroom.students).selectinload(ClassroomStudent.student),
        )
        .where(ExamAssignment.id == assignment_id, Exam.owner_id == user.id)
    ).first()
    if assignment is None:
        raise HTTPException(status_code=404, detail="Atribuicao nao encontrada")
    if not assignment.classroom.students:
        raise HTTPException(status_code=422, detail="A turma nao possui alunos")

    pdf = build_answer_sheet_pdf(assignment, user.full_name, user.id)
    filename = f"gabaritos-prova-{assignment.exam_id}-turma-{assignment.classroom_id}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

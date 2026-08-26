from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import sys
import tempfile
from configparser import ConfigParser
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Classroom, ClassroomStudent, CorrectionAnswer, CorrectionResult, Exam, ExamAssignment, Student, User
from app.schemas import (
    CorrectionJobRead,
    CorrectionManualCreate,
    CorrectionResultRead,
    ExamAssignmentRead,
    ExamRead,
    GradeAssignmentRead,
    GradeStudentRead,
)

router = APIRouter(prefix="/corrections", tags=["corrections"])


def _to_result_read(result: CorrectionResult) -> CorrectionResultRead:
    return CorrectionResultRead(
        id=result.id,
        assignment_id=result.assignment_id,
        student_id=result.student_id,
        student_name=result.student.name,
        enrollment_code=result.student.enrollment_code,
        score=result.score,
        max_score=result.max_score,
        source_filename=result.source_filename,
        created_at=result.created_at,
        answers=sorted(result.answers, key=lambda answer: answer.question_number),
    )


def _to_exam_read(exam: Exam) -> ExamRead:
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


def _to_assignment_read(assignment: ExamAssignment) -> ExamAssignmentRead:
    return ExamAssignmentRead(
        id=assignment.id,
        exam_id=assignment.exam_id,
        classroom_id=assignment.classroom_id,
        classroom_name=assignment.classroom.name,
        exam_title=assignment.exam.title,
        status=assignment.status,
        assigned_at=assignment.assigned_at,
    )


def _load_assignment(db: Session, assignment_id: int, user: User) -> ExamAssignment:
    assignment = db.scalars(
        select(ExamAssignment)
        .join(Exam)
        .options(
            selectinload(ExamAssignment.exam).selectinload(Exam.answer_key),
            selectinload(ExamAssignment.exam).selectinload(Exam.assignments),
            selectinload(ExamAssignment.classroom)
            .selectinload(Classroom.students)
            .selectinload(ClassroomStudent.student),
        )
        .where(ExamAssignment.id == assignment_id, Exam.owner_id == user.id)
    ).first()
    if assignment is None:
        raise HTTPException(status_code=404, detail="Atribuicao nao encontrada")
    return assignment


def _score_answers(assignment: ExamAssignment, selected_options: list[int]) -> tuple[float, float, list[CorrectionAnswer]]:
    answer_key = sorted(assignment.exam.answer_key, key=lambda item: item.question_number)
    max_score = float(sum(item.weight for item in answer_key))
    score = 0.0
    answers: list[CorrectionAnswer] = []
    for item in answer_key:
        selected = selected_options[item.question_number - 1] if item.question_number <= len(selected_options) else -1
        awarded = float(item.weight if selected == item.option_index else 0)
        score += awarded
        answers.append(
            CorrectionAnswer(
                question_number=item.question_number,
                selected_option=selected,
                correct_option=item.option_index,
                weight=item.weight,
                awarded=awarded,
            )
        )
    return score, max_score, answers


def _save_result(
    db: Session,
    assignment: ExamAssignment,
    student: Student,
    selected_options: list[int],
    source_filename: str | None,
) -> CorrectionResult:
    existing = db.scalar(
        select(CorrectionResult).where(
            CorrectionResult.assignment_id == assignment.id,
            CorrectionResult.student_id == student.id,
        )
    )
    if existing is not None:
        existing_answers = {
            answer.question_number: answer.selected_option
            for answer in db.scalars(select(CorrectionAnswer).where(CorrectionAnswer.result_id == existing.id))
        }
        selected_options = [
            selected if selected != -1 else existing_answers.get(index + 1, -1)
            for index, selected in enumerate(selected_options)
        ]
    if existing is not None:
        db.delete(existing)
        db.flush()

    score, max_score, answers = _score_answers(assignment, selected_options)
    result = CorrectionResult(
        assignment_id=assignment.id,
        student_id=student.id,
        score=score,
        max_score=max_score,
        source_filename=source_filename,
    )
    result.answers = answers
    db.add(result)
    db.flush()
    return result


def _save_score_result(
    db: Session,
    assignment: ExamAssignment,
    student: Student,
    score: float,
    source_filename: str | None,
) -> CorrectionResult:
    existing = db.scalar(
        select(CorrectionResult).where(
            CorrectionResult.assignment_id == assignment.id,
            CorrectionResult.student_id == student.id,
        )
    )
    if existing is not None:
        db.delete(existing)
        db.flush()

    answer_key = sorted(assignment.exam.answer_key, key=lambda item: item.question_number)
    max_score = float(sum(item.weight for item in answer_key))
    remaining = max(0.0, min(float(score), max_score))
    answers: list[CorrectionAnswer] = []
    for item in answer_key:
        awarded = min(float(item.weight), remaining)
        remaining -= awarded
        answers.append(
            CorrectionAnswer(
                question_number=item.question_number,
                selected_option=item.option_index if awarded > 0 else -1,
                correct_option=item.option_index,
                weight=item.weight,
                awarded=awarded,
            )
        )

    result = CorrectionResult(
        assignment_id=assignment.id,
        student_id=student.id,
        score=sum(answer.awarded for answer in answers),
        max_score=max_score,
        source_filename=source_filename,
    )
    result.answers = answers
    db.add(result)
    db.flush()
    return result


def _parse_option(value: str) -> int:
    normalized = value.strip().upper()
    if not normalized:
        return -1
    if normalized in ["A", "B", "C", "D", "E", "F", "G"]:
        return ["A", "B", "C", "D", "E", "F", "G"].index(normalized)
    try:
        numeric = int(normalized)
    except ValueError:
        return -1
    return numeric - 1 if numeric > 0 else numeric


def _normalize_manual_options(assignment: ExamAssignment, selected_options: list[int]) -> list[int]:
    normalized = [int(value) for value in selected_options[: assignment.exam.question_count]]
    if len(normalized) < assignment.exam.question_count:
        normalized.extend([-1] * (assignment.exam.question_count - len(normalized)))
    return [
        selected if -1 <= selected < assignment.exam.option_count else -1
        for selected in normalized
    ]


def _options_from_manual_score(assignment: ExamAssignment, score: float) -> list[int]:
    answer_key = sorted(assignment.exam.answer_key, key=lambda item: item.question_number)
    max_score = float(sum(item.weight for item in answer_key))
    remaining = max(0.0, min(float(score), max_score))
    selected: list[int] = []
    for item in answer_key:
        if remaining >= item.weight:
            selected.append(item.option_index)
            remaining -= item.weight
        else:
            selected.append(-1)
    return selected


def _manual_selected_options(assignment: ExamAssignment, payload: CorrectionManualCreate) -> list[int]:
    if payload.score is not None:
        return _options_from_manual_score(assignment, payload.score)
    return _normalize_manual_options(assignment, payload.selected_options or [])


def _load_result(db: Session, result_id: int, user: User) -> CorrectionResult:
    result = db.scalars(
        select(CorrectionResult)
        .join(ExamAssignment)
        .join(Exam)
        .options(selectinload(CorrectionResult.student), selectinload(CorrectionResult.answers))
        .where(CorrectionResult.id == result_id, Exam.owner_id == user.id)
    ).first()
    if result is None:
        raise HTTPException(status_code=404, detail="Nota nao encontrada")
    return result


def _build_legacy_grade_csv(assignment: ExamAssignment, results: list[CorrectionResult]) -> tuple[str, bytes]:
    answer_key = sorted(assignment.exam.answer_key, key=lambda item: item.question_number)
    headers = ["Nome da Prova", "Id do Aluno", "Nome"] + [f"Q{item.question_number}" for item in answer_key]
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
    writer.writerow(headers)

    results_by_student = {result.student_id: result for result in results}
    classroom_students = sorted(
        (link.student for link in assignment.classroom.students),
        key=lambda student: student.name.lower(),
    )
    for student in classroom_students:
        result = results_by_student.get(student.id)
        answers = {answer.question_number: answer for answer in result.answers} if result else {}
        row: list[str | int] = [assignment.exam.title, student.id, student.name]
        for item in answer_key:
            answer = answers.get(item.question_number)
            row.append(1 if answer and answer.selected_option == item.option_index else 0)
        writer.writerow(row)

    filename_title = assignment.exam.title.replace("/", "_").replace(" ", "_")
    filename = f"Notas_Alunos_{filename_title}.csv"
    return filename, output.getvalue().encode("utf-8")


async def _process_csv(
    file: UploadFile,
    assignment: ExamAssignment,
    db: Session,
    user: User,
) -> tuple[int, int]:
    raw = await file.read()
    text = raw.decode("utf-8-sig", errors="replace")
    first_line = text.splitlines()[0] if text.splitlines() else ""
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise HTTPException(status_code=422, detail="CSV de correcao vazio ou sem cabecalho")

    fields = [field.strip() for field in reader.fieldnames]
    field_map = {field.lower(): field for field in fields}
    student_field = field_map.get("matricula") or field_map.get("enrollment") or field_map.get("enrollment_code")
    if student_field is None:
        raise HTTPException(status_code=422, detail="CSV de correcao deve conter a coluna matricula")

    question_fields = [
        field for field in fields if field.lower().startswith("q") or field.lower().isdigit()
    ]
    if not question_fields:
        question_fields = [field for field in fields if field != student_field]

    imported = 0
    skipped = 0
    for row in reader:
        enrollment = (row.get(student_field) or "").strip()
        if not enrollment:
            skipped += 1
            continue
        student = db.scalar(
            select(Student).where(Student.owner_id == user.id, Student.enrollment_code == enrollment)
        )
        if student is None:
            skipped += 1
            continue
        selected = [_parse_option(row.get(field) or "") for field in question_fields]
        _save_result(db, assignment, student, selected, file.filename)
        imported += 1
    return imported, skipped


def _extract_legacy_value(lines: list[str], prefix: str) -> str | None:
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


async def _process_image(file: UploadFile, assignment: ExamAssignment, db: Session, user: User) -> bool:
    project_root = Path(__file__).resolve().parents[3]
    script = project_root / "src" / "test_core" / "correct_from_payload.py"
    if not script.exists():
        return False

    python_bin = sys.executable
    settings_path = project_root / "src" / "settings.ini"
    if settings_path.exists():
        config = ConfigParser()
        config.read(settings_path, encoding="utf-8")
        configured = config.get("SYSTEM", "python_windows_path", fallback="")
        candidate = project_root / configured.strip('"')
        if candidate.exists():
            try:
                subprocess.run([str(candidate), "--version"], capture_output=True, timeout=5, check=True)
                python_bin = str(candidate)
            except Exception:
                python_bin = sys.executable

    payload = {
        "question_count": assignment.exam.question_count,
        "option_count": assignment.exam.option_count,
        "answer_key": [
            {
                "question_number": item.question_number,
                "option_index": item.option_index + 1,
                "weight": item.weight,
            }
            for item in sorted(assignment.exam.answer_key, key=lambda answer: answer.question_number)
        ],
    }

    suffix = Path(file.filename or "upload.png").suffix or ".png"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp:
        temp.write(await file.read())
        temp_path = temp.name
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(script.parent)
        process = subprocess.run(
            [python_bin, str(script), temp_path, json.dumps(payload)],
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
        )
    finally:
        os.unlink(temp_path)

    lines = (process.stdout + "\n" + process.stderr).splitlines()
    student_id = _extract_legacy_value(lines, "id_aluno:")
    answers_raw = _extract_legacy_value(lines, "resposta:")
    exam_id = _extract_legacy_value(lines, "id_prova:")
    if not student_id or not answers_raw or str(assignment.exam_id) != str(exam_id):
        return False

    student = db.get(Student, int(student_id))
    if student is None or student.owner_id != user.id:
        return False
    selected = [int(value) for value in answers_raw.split(",") if value.strip()]
    _save_result(db, assignment, student, selected, file.filename)
    return True


@router.get("/{assignment_id}", response_model=list[CorrectionResultRead])
def list_correction_results(
    assignment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CorrectionResultRead]:
    _load_assignment(db, assignment_id, user)
    results = db.scalars(
        select(CorrectionResult)
        .options(selectinload(CorrectionResult.student), selectinload(CorrectionResult.answers))
        .where(CorrectionResult.assignment_id == assignment_id)
        .order_by(CorrectionResult.created_at.desc())
    )
    return [_to_result_read(result) for result in results]


@router.get("/{assignment_id}/grades", response_model=GradeAssignmentRead)
def list_assignment_grades(
    assignment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GradeAssignmentRead:
    assignment = _load_assignment(db, assignment_id, user)
    results = list(
        db.scalars(
            select(CorrectionResult)
            .options(selectinload(CorrectionResult.student), selectinload(CorrectionResult.answers))
            .where(CorrectionResult.assignment_id == assignment.id)
        )
    )
    results_by_student = {result.student_id: result for result in results}
    students = [
        GradeStudentRead(
            student_id=link.student.id,
            student_name=link.student.name,
            enrollment_code=link.student.enrollment_code,
            result=_to_result_read(results_by_student[link.student.id]) if link.student.id in results_by_student else None,
        )
        for link in sorted(assignment.classroom.students, key=lambda item: item.student.name.lower())
    ]
    return GradeAssignmentRead(
        assignment=_to_assignment_read(assignment),
        exam=_to_exam_read(assignment.exam),
        students=students,
    )


@router.post("/{assignment_id}/students/{student_id}", response_model=CorrectionResultRead, status_code=status.HTTP_201_CREATED)
def save_manual_grade(
    assignment_id: int,
    student_id: int,
    payload: CorrectionManualCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CorrectionResultRead:
    assignment = _load_assignment(db, assignment_id, user)
    student = db.get(Student, student_id)
    classroom_student_ids = {link.student_id for link in assignment.classroom.students}
    if student is None or student.owner_id != user.id or student.id not in classroom_student_ids:
        raise HTTPException(status_code=404, detail="Aluno nao encontrado nesta turma")

    if payload.score is not None:
        result = _save_score_result(db, assignment, student, payload.score, payload.source_filename)
    else:
        result = _save_result(db, assignment, student, _manual_selected_options(assignment, payload), payload.source_filename)
    db.commit()
    result = _load_result(db, result.id, user)
    return _to_result_read(result)


@router.put("/results/{result_id}", response_model=CorrectionResultRead)
def update_manual_grade(
    result_id: int,
    payload: CorrectionManualCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CorrectionResultRead:
    existing = _load_result(db, result_id, user)
    assignment = _load_assignment(db, existing.assignment_id, user)
    if payload.score is not None:
        result = _save_score_result(db, assignment, existing.student, payload.score, payload.source_filename)
    else:
        result = _save_result(db, assignment, existing.student, _manual_selected_options(assignment, payload), payload.source_filename)
    db.commit()
    result = _load_result(db, result.id, user)
    return _to_result_read(result)


@router.delete("/results/{result_id}")
def delete_grade(
    result_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    result = _load_result(db, result_id, user)
    db.delete(result)
    db.commit()
    return {"message": "Nota excluida."}


@router.get("/{assignment_id}/grades-report")
def download_grades_report(
    assignment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    assignment = _load_assignment(db, assignment_id, user)
    results = list(
        db.scalars(
            select(CorrectionResult)
            .options(selectinload(CorrectionResult.student), selectinload(CorrectionResult.answers))
            .where(CorrectionResult.assignment_id == assignment.id)
        )
    )
    filename, content = _build_legacy_grade_csv(assignment, results)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("", response_model=CorrectionJobRead)
async def create_correction_job(
    assignment_id: int = Form(...),
    files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CorrectionJobRead:
    assignment = _load_assignment(db, assignment_id, user)
    imported = 0
    skipped = 0

    for file in files:
        extension = Path(file.filename or "").suffix.lower()
        if extension == ".csv":
            file_imported, file_skipped = await _process_csv(file, assignment, db, user)
            imported += file_imported
            skipped += file_skipped
        else:
            if await _process_image(file, assignment, db, user):
                imported += 1
            else:
                skipped += 1

    db.commit()
    return CorrectionJobRead(
        id=str(uuid4()),
        status="finished",
        message=f"{imported} resultado(s) corrigido(s); {skipped} arquivo(s)/linha(s) ignorado(s).",
    )

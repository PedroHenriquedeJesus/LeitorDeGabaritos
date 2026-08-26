import csv
import io
import re
import unicodedata

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models import Classroom, ClassroomStudent, CorrectionResult, Student, User
from app.schemas import BulkDeleteRead, StudentCreate, StudentImportRead, StudentRead, StudentUpdate

router = APIRouter(prefix="/students", tags=["students"])


def normalize_csv_header(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", without_accents).strip()


def find_csv_field(fields: dict[str, str], aliases: set[str]) -> str | None:
    for alias in aliases:
        if alias in fields:
            return fields[alias]
    return None


def decode_csv_bytes(raw: bytes) -> str:
    text = raw.decode("utf-8-sig", errors="surrogateescape")
    repaired: list[str] = []
    for char in text:
        codepoint = ord(char)
        if 0xDC80 <= codepoint <= 0xDCFF:
            repaired.append(bytes([codepoint - 0xDC00]).decode("cp1252", errors="replace"))
        else:
            repaired.append(char)
    return "".join(repaired)


@router.get("", response_model=list[StudentRead])
def list_students(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[StudentRead]:
    students = db.scalars(
        select(Student)
        .options(selectinload(Student.classrooms).selectinload(ClassroomStudent.classroom))
        .where(Student.owner_id == user.id)
        .order_by(Student.name)
    )
    return [to_student_read(student) for student in students]


def to_student_read(student: Student) -> StudentRead:
    links = sorted(student.classrooms, key=lambda link: link.classroom.name.lower())
    return StudentRead(
        id=student.id,
        name=student.name,
        email=student.email,
        enrollment_code=student.enrollment_code,
        classroom_ids=[link.classroom_id for link in links],
        classroom_names=[link.classroom.name for link in links],
        created_at=student.created_at,
    )


def sync_student_classrooms(db: Session, student: Student, classroom_ids: list[int], user: User) -> None:
    valid_ids = set(
        db.scalars(select(Classroom.id).where(Classroom.owner_id == user.id, Classroom.id.in_(classroom_ids))).all()
    )
    db.query(ClassroomStudent).filter(ClassroomStudent.student_id == student.id).delete(synchronize_session=False)
    db.add_all([ClassroomStudent(classroom_id=classroom_id, student_id=student.id) for classroom_id in valid_ids])


@router.post("", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> StudentRead:
    student = Student(**payload.model_dump(exclude={"classroom_ids"}), owner_id=user.id)
    db.add(student)
    db.flush()
    sync_student_classrooms(db, student, payload.classroom_ids, user)
    db.commit()
    student = db.scalars(
        select(Student)
        .options(selectinload(Student.classrooms).selectinload(ClassroomStudent.classroom))
        .where(Student.id == student.id)
    ).one()
    return to_student_read(student)


@router.put("/{student_id}", response_model=StudentRead)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StudentRead:
    student = db.get(Student, student_id)
    if not student or student.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Aluno nao encontrado")
    student.name = payload.name
    student.email = payload.email
    student.enrollment_code = payload.enrollment_code
    sync_student_classrooms(db, student, payload.classroom_ids, user)
    db.commit()
    student = db.scalars(
        select(Student)
        .options(selectinload(Student.classrooms).selectinload(ClassroomStudent.classroom))
        .where(Student.id == student.id)
    ).one()
    return to_student_read(student)


@router.post("/import-csv", response_model=StudentImportRead)
async def import_students_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StudentImportRead:
    raw = await file.read()
    text = decode_csv_bytes(raw)
    first_line = text.splitlines()[0] if text.splitlines() else ""
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise HTTPException(status_code=422, detail="CSV vazio ou sem cabecalho")

    normalized_fields = {normalize_csv_header(field): field for field in reader.fieldnames if field}
    name_field = find_csv_field(normalized_fields, {"nome", "aluno", "nome aluno", "nome do aluno"})
    classroom_field = find_csv_field(normalized_fields, {"turma", "classe", "sala"})
    enrollment_field = find_csv_field(
        normalized_fields,
        {
            "matricula",
            "n matricula",
            "no matricula",
            "numero matricula",
            "numero de matricula",
            "matricula numero",
        },
    )
    if not name_field or not classroom_field or not enrollment_field:
        raise HTTPException(status_code=422, detail="CSV deve conter colunas equivalentes a nome, turma e matricula")

    created_students = 0
    updated_students = 0
    created_classrooms = 0
    linked_students = 0
    skipped_rows = 0

    for row in reader:
        name = (row.get(name_field) or "").strip()
        classroom_name = (row.get(classroom_field) or "").strip()
        enrollment = (row.get(enrollment_field) or "").strip()
        if not name or not classroom_name or not enrollment:
            skipped_rows += 1
            continue

        classroom = db.scalar(
            select(Classroom).where(Classroom.owner_id == user.id, Classroom.name == classroom_name)
        )
        if classroom is None:
            classroom = Classroom(name=classroom_name, course_name=None, owner_id=user.id)
            db.add(classroom)
            db.flush()
            created_classrooms += 1

        student = db.scalar(
            select(Student).where(Student.owner_id == user.id, Student.enrollment_code == enrollment)
        )
        if student is None:
            student = Student(name=name, email=None, enrollment_code=enrollment, owner_id=user.id)
            db.add(student)
            db.flush()
            created_students += 1
        elif student.name != name:
            student.name = name
            updated_students += 1

        existing_link = db.get(ClassroomStudent, {"classroom_id": classroom.id, "student_id": student.id})
        if existing_link is None:
            db.add(ClassroomStudent(classroom_id=classroom.id, student_id=student.id))
            linked_students += 1

    db.commit()
    return StudentImportRead(
        created_students=created_students,
        updated_students=updated_students,
        created_classrooms=created_classrooms,
        linked_students=linked_students,
        skipped_rows=skipped_rows,
        message=(
            f"{created_students} aluno(s) criado(s), {updated_students} atualizado(s), "
            f"{created_classrooms} turma(s) criada(s), {linked_students} vinculo(s) realizado(s)."
        ),
    )


@router.delete("/all", response_model=BulkDeleteRead)
def delete_all_students(db: Session = Depends(get_db), user: User = Depends(require_admin)) -> BulkDeleteRead:
    student_ids = list(db.scalars(select(Student.id).where(Student.owner_id == user.id)))
    if not student_ids:
        return BulkDeleteRead(deleted=0, message="Nenhum aluno para excluir.")
    results = list(db.scalars(select(CorrectionResult).where(CorrectionResult.student_id.in_(student_ids))))
    for result in results:
        db.delete(result)
    db.query(ClassroomStudent).filter(ClassroomStudent.student_id.in_(student_ids)).delete(synchronize_session=False)
    deleted = db.query(Student).filter(Student.owner_id == user.id).delete(synchronize_session=False)
    db.commit()
    return BulkDeleteRead(deleted=deleted, message=f"{deleted} aluno(s) excluido(s).")


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    student = db.get(Student, student_id)
    if not student or student.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Aluno nao encontrado")
    results = list(db.scalars(select(CorrectionResult).where(CorrectionResult.student_id == student.id)))
    for result in results:
        db.delete(result)
    db.delete(student)
    db.commit()

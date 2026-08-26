from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import AssignmentStatus, UserRole


class UserRead(BaseModel):
    id: int
    username: str
    full_name: str
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class MessageRead(BaseModel):
    message: str


class StudentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr | None = None
    enrollment_code: str | None = Field(default=None, max_length=80)
    classroom_ids: list[int] = []


class StudentUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr | None = None
    enrollment_code: str | None = Field(default=None, max_length=80)
    classroom_ids: list[int] = []


class StudentRead(BaseModel):
    id: int
    name: str
    email: EmailStr | None = None
    enrollment_code: str | None = None
    classroom_ids: list[int] = []
    classroom_names: list[str] = []
    created_at: datetime


class ClassroomCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    course_name: str | None = Field(default=None, max_length=120)
    student_ids: list[int] = []


class ClassroomUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    course_name: str | None = Field(default=None, max_length=120)
    student_ids: list[int] | None = None


class ClassroomRead(BaseModel):
    id: int
    name: str
    course_name: str | None
    student_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnswerKeyItemCreate(BaseModel):
    question_number: int = Field(ge=1)
    option_index: int = Field(ge=0, le=6)
    weight: int = Field(default=1, ge=1, le=10)


class ExamCreate(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    exam_date: date | None = None
    question_count: int = Field(ge=1)
    option_count: int = Field(ge=2, le=7)
    answer_key: list[AnswerKeyItemCreate]


class ExamUpdate(ExamCreate):
    pass


class AnswerKeyItemRead(AnswerKeyItemCreate):
    model_config = ConfigDict(from_attributes=True)


class ExamRead(BaseModel):
    id: int
    title: str
    description: str | None
    exam_date: date | None
    question_count: int
    option_count: int
    assignment_count: int
    created_at: datetime
    answer_key: list[AnswerKeyItemRead]

    model_config = ConfigDict(from_attributes=True)


class ExamAssignmentCreate(BaseModel):
    classroom_id: int | None = None
    classroom_ids: list[int] = []


class ExamAssignmentRead(BaseModel):
    id: int
    exam_id: int
    classroom_id: int
    classroom_name: str
    exam_title: str
    status: AssignmentStatus
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardRead(BaseModel):
    students: int
    classrooms: int
    exams: int
    active_assignments: int
    recent_exams: list[ExamRead]
    recent_assignments: list[ExamAssignmentRead]


class CorrectionJobRead(BaseModel):
    id: str
    status: str
    message: str


class StudentImportRead(BaseModel):
    created_students: int
    updated_students: int
    created_classrooms: int
    linked_students: int
    skipped_rows: int
    message: str


class BulkDeleteRead(BaseModel):
    deleted: int
    message: str


class GeneratedAnswerSheetRead(BaseModel):
    assignment_id: int
    filename: str
    student_count: int


class CorrectionAnswerRead(BaseModel):
    question_number: int
    selected_option: int
    correct_option: int
    weight: int
    awarded: float

    model_config = ConfigDict(from_attributes=True)


class CorrectionResultRead(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    student_name: str
    enrollment_code: str | None
    score: float
    max_score: float
    source_filename: str | None
    created_at: datetime
    answers: list[CorrectionAnswerRead]

    model_config = ConfigDict(from_attributes=True)


class CorrectionManualCreate(BaseModel):
    selected_options: list[int] | None = None
    score: float | None = Field(default=None, ge=0)
    source_filename: str | None = "Lancamento manual"


class GradeStudentRead(BaseModel):
    student_id: int
    student_name: str
    enrollment_code: str | None
    result: CorrectionResultRead | None = None


class GradeAssignmentRead(BaseModel):
    assignment: ExamAssignmentRead
    exam: ExamRead
    students: list[GradeStudentRead]

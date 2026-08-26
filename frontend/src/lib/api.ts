export type Student = {
  id: number;
  name: string;
  email?: string;
  enrollment_code?: string;
  classroom_ids: number[];
  classroom_names: string[];
  created_at: string;
};

export type CurrentUser = {
  id: number;
  username: string;
  full_name: string;
  role: "admin" | "teacher";
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  user: CurrentUser;
};

export type Classroom = {
  id: number;
  name: string;
  course_name?: string;
  student_count: number;
  created_at: string;
};

export type AnswerKeyItem = {
  question_number: number;
  option_index: number;
  weight: number;
};

export type Exam = {
  id: number;
  title: string;
  description?: string;
  exam_date?: string;
  question_count: number;
  option_count: number;
  assignment_count: number;
  created_at: string;
  answer_key: AnswerKeyItem[];
};

export type Assignment = {
  id: number;
  exam_id: number;
  classroom_id: number;
  classroom_name: string;
  exam_title: string;
  status: "draft" | "active" | "corrected" | "archived";
  assigned_at: string;
};

export type StudentImport = {
  created_students: number;
  updated_students: number;
  created_classrooms: number;
  linked_students: number;
  skipped_rows: number;
  message: string;
};

export type BulkDelete = {
  deleted: number;
  message: string;
};

export type CorrectionAnswer = {
  question_number: number;
  selected_option: number;
  correct_option: number;
  weight: number;
  awarded: number;
};

export type CorrectionResult = {
  id: number;
  assignment_id: number;
  student_id: number;
  student_name: string;
  enrollment_code?: string;
  score: number;
  max_score: number;
  source_filename?: string;
  created_at: string;
  answers: CorrectionAnswer[];
};

export type GradeStudent = {
  student_id: number;
  student_name: string;
  enrollment_code?: string;
  result: CorrectionResult | null;
};

export type GradeAssignment = {
  assignment: Assignment;
  exam: Exam;
  students: GradeStudent[];
};

export type Dashboard = {
  students: number;
  classrooms: number;
  exams: number;
  active_assignments: number;
  recent_exams: Exam[];
  recent_assignments: Assignment[];
};

const API_URL = import.meta.env.VITE_API_URL ?? "/api";
const TOKEN_KEY = "corretorapp.auth-token";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

function accessToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

async function performRequest(path: string, init?: RequestInit): Promise<Response> {
  const isFormData = init?.body instanceof FormData;
  const headers = new Headers(init?.headers);
  if (!isFormData && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const token = accessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    let message = "Nao foi possivel concluir a solicitacao.";
    try {
      const payload = (await response.clone().json()) as { detail?: string };
      if (payload.detail) message = payload.detail;
    } catch {
      message = (await response.text()) || message;
    }
    if (response.status === 401 && path !== "/auth/login") sessionStorage.removeItem(TOKEN_KEY);
    throw new ApiError(message, response.status);
  }
  return response;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await performRequest(path, init);
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

async function download(path: string): Promise<Blob> {
  return (await performRequest(path)).blob();
}

export const api = {
  hasSession: () => Boolean(accessToken()),
  clearSession: () => sessionStorage.removeItem(TOKEN_KEY),
  login: async (username: string, password: string) => {
    const response = await request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    sessionStorage.setItem(TOKEN_KEY, response.access_token);
    return response.user;
  },
  logout: async () => {
    try {
      if (accessToken()) await request<{ message: string }>("/auth/logout", { method: "POST" });
    } finally {
      sessionStorage.removeItem(TOKEN_KEY);
    }
  },
  me: () => request<CurrentUser>("/users/me"),
  changePassword: (currentPassword: string, newPassword: string) =>
    request<{ message: string }>("/users/me/password", {
      method: "PUT",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }),
  dashboard: () => request<Dashboard>("/dashboard"),
  students: () => request<Student[]>("/students"),
  createStudent: (payload: Pick<Student, "name" | "email" | "enrollment_code" | "classroom_ids">) =>
    request<Student>("/students", { method: "POST", body: JSON.stringify(payload) }),
  updateStudent: (studentId: number, payload: Pick<Student, "name" | "email" | "enrollment_code" | "classroom_ids">) =>
    request<Student>(`/students/${studentId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteStudent: (studentId: number) => request<void>(`/students/${studentId}`, { method: "DELETE" }),
  deleteAllStudents: () => request<BulkDelete>("/students/all", { method: "DELETE" }),
  importStudentsCsv: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<StudentImport>("/students/import-csv", { method: "POST", body });
  },
  classrooms: () => request<Classroom[]>("/classrooms"),
  createClassroom: (payload: { name: string; course_name?: string; student_ids: number[] }) =>
    request<Classroom>("/classrooms", { method: "POST", body: JSON.stringify(payload) }),
  updateClassroom: (classroomId: number, payload: { name: string; course_name?: string; student_ids?: number[] }) =>
    request<Classroom>(`/classrooms/${classroomId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteClassroom: (classroomId: number) => request<void>(`/classrooms/${classroomId}`, { method: "DELETE" }),
  exams: () => request<Exam[]>("/exams"),
  createExam: (payload: {
    title: string;
    description?: string;
    exam_date?: string;
    question_count: number;
    option_count: number;
    answer_key: AnswerKeyItem[];
  }) => request<Exam>("/exams", { method: "POST", body: JSON.stringify(payload) }),
  updateExam: (
    examId: number,
    payload: {
      title: string;
      description?: string;
      exam_date?: string;
      question_count: number;
      option_count: number;
      answer_key: AnswerKeyItem[];
    },
  ) => request<Exam>(`/exams/${examId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteExam: (examId: number) => request<void>(`/exams/${examId}`, { method: "DELETE" }),
  assignments: () => request<Assignment[]>("/exams/assignments"),
  assignExam: (examId: number, classroomIds: number[]) =>
    request<Assignment[]>(`/exams/${examId}/assignments`, {
      method: "POST",
      body: JSON.stringify({ classroom_ids: classroomIds }),
    }),
  deleteAssignment: (assignmentId: number) => request<void>(`/exams/assignments/${assignmentId}`, { method: "DELETE" }),
  answerSheets: (assignmentId: number) => download(`/exams/assignments/${assignmentId}/answer-sheets`),
  correctionResults: (assignmentId: number) => request<CorrectionResult[]>(`/corrections/${assignmentId}`),
  assignmentGrades: (assignmentId: number) => request<GradeAssignment>(`/corrections/${assignmentId}/grades`),
  saveManualGrade: (assignmentId: number, studentId: number, score: number, sourceFilename = "Lancamento manual") =>
    request<CorrectionResult>(`/corrections/${assignmentId}/students/${studentId}`, {
      method: "POST",
      body: JSON.stringify({ score, source_filename: sourceFilename }),
    }),
  updateManualGrade: (resultId: number, score: number, sourceFilename = "Lancamento manual") =>
    request<CorrectionResult>(`/corrections/results/${resultId}`, {
      method: "PUT",
      body: JSON.stringify({ score, source_filename: sourceFilename }),
    }),
  deleteGrade: (resultId: number) => request<void>(`/corrections/results/${resultId}`, { method: "DELETE" }),
  gradesReport: (assignmentId: number) => download(`/corrections/${assignmentId}/grades-report`),
  correctAssignment: (assignmentId: number, files: File[]) => {
    const body = new FormData();
    body.append("assignment_id", String(assignmentId));
    files.forEach((file) => body.append("files", file));
    return request<{ id: string; status: string; message: string }>("/corrections", { method: "POST", body });
  },
};

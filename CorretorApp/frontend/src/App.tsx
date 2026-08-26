import {
  BookOpenCheck,
  CheckCircle2,
  ClipboardCheck,
  Download,
  FileUp,
  GraduationCap,
  KeyRound,
  LoaderCircle,
  Pencil,
  Plus,
  Save,
  School,
  Search,
  Send,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";

import { MetricCard } from "./components/MetricCard";
import { SectionHeader } from "./components/SectionHeader";
import { Shell, type PageKey } from "./components/Shell";
import { StatusBadge } from "./components/StatusBadge";
import {
  api,
  ApiError,
  type Assignment,
  type Classroom,
  type CorrectionResult,
  type CurrentUser,
  type Dashboard,
  type Exam,
  type GradeAssignment,
  type Student,
} from "./lib/api";

const optionLabels = ["A", "B", "C", "D", "E", "F", "G"];

export function App() {
  const [authenticated, setAuthenticated] = useState(api.hasSession());
  const [activePage, setActivePage] = useState<PageKey>("dashboard");
  const [students, setStudents] = useState<Student[]>([]);
  const [classrooms, setClassrooms] = useState<Classroom[]>([]);
  const [exams, setExams] = useState<Exam[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loginMessage, setLoginMessage] = useState("");

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [userData, dashboardData, studentData, classroomData, examData, assignmentData] = await Promise.all([
        api.me(),
        api.dashboard(),
        api.students(),
        api.classrooms(),
        api.exams(),
        api.assignments(),
      ]);
      setCurrentUser(userData);
      setDashboard(dashboardData);
      setStudents(studentData);
      setClassrooms(classroomData);
      setExams(examData);
      setAssignments(assignmentData);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        api.clearSession();
        setAuthenticated(false);
        setCurrentUser(null);
        setLoginMessage("Sua sessao expirou. Entre novamente.");
        return;
      }
      setError(err instanceof Error ? err.message : "Nao foi possivel carregar os dados.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (authenticated) void loadData();
    else setLoading(false);
  }, [authenticated]);

  async function handleLogin(username: string, password: string) {
    const user = await api.login(username, password);
    setCurrentUser(user);
    setLoginMessage("");
    setAuthenticated(true);
  }

  async function handleLogout(message = "") {
    try {
      await api.logout();
    } finally {
      setAuthenticated(false);
      setCurrentUser(null);
      setActivePage("dashboard");
      setLoginMessage(message);
    }
  }

  if (!authenticated) {
    return <LoginPage message={loginMessage} onLogin={handleLogin} />;
  }

  return (
    <Shell
      activePage={activePage}
      currentUser={currentUser}
      onLogout={() => void handleLogout()}
      onNavigate={setActivePage}
    >
      {error ? <div className="alert">{error}</div> : null}
      {loading ? <div className="loading-card">Carregando ambiente CorretorApp...</div> : null}
      {!loading && activePage === "dashboard" ? (
        <DashboardPage dashboard={dashboard} onNewExam={() => setActivePage("exams")} />
      ) : null}
      {!loading && activePage === "students" ? (
        <StudentsPage
          students={students}
          classrooms={classrooms}
          allStudents={students}
          isMaster={currentUser?.role === "admin"}
          onChanged={loadData}
        />
      ) : null}
      {!loading && activePage === "grades" ? (
        <GradesPage assignments={assignments} onChanged={loadData} />
      ) : null}
      {!loading && activePage === "exams" ? (
        <ExamsPage
          exams={exams}
          assignments={assignments}
          classrooms={classrooms}
          onChanged={loadData}
        />
      ) : null}
      {!loading && activePage === "corrections" ? (
        <CorrectionsPage assignments={assignments} onChanged={loadData} />
      ) : null}
      {!loading && activePage === "users" && currentUser?.role === "admin" ? (
        <UsersPage currentUser={currentUser} onPasswordChanged={(message) => void handleLogout(message)} />
      ) : null}
    </Shell>
  );
}

function LoginPage({ message, onLogin }: { message: string; onLogin: (username: string, password: string) => Promise<void> }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await onLogin(username, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel entrar.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <form className="login-card" onSubmit={submit}>
        <div className="brand login-brand">
          <div className="brand-mark"><BookOpenCheck size={23} /></div>
          <div><strong>CorretorApp</strong><span>Acesso seguro</span></div>
        </div>
        <div>
          <h1>Entrar</h1>
          <p>Informe suas credenciais para acessar provas e resultados.</p>
        </div>
        {message ? <div className="inline-message">{message}</div> : null}
        {error ? <div className="alert compact-alert">{error}</div> : null}
        <label>
          Usuario
          <input autoComplete="username" autoFocus required value={username} onChange={(event) => setUsername(event.target.value)} />
        </label>
        <label>
          Senha
          <input autoComplete="current-password" required type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        <button className="primary-button" disabled={submitting} type="submit">
          {submitting ? <LoaderCircle className="spin" size={18} /> : <KeyRound size={18} />}
          {submitting ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </main>
  );
}

function UsersPage({
  currentUser,
  onPasswordChanged,
}: {
  currentUser: CurrentUser;
  onPasswordChanged: (message: string) => void;
}) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (newPassword !== confirmation) {
      setError("A confirmacao nao corresponde a nova senha.");
      return;
    }
    setSaving(true);
    try {
      const result = await api.changePassword(currentPassword, newPassword);
      api.clearSession();
      onPasswordChanged(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel alterar a senha.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <SectionHeader title="Controle de usuarios" subtitle="Gerencie as credenciais da conta administrativa." />
      <div className="split-layout wide-left">
        <section className="panel">
          <div className="panel-title"><h2>Administrador atual</h2></div>
          <div className="stack-list">
            <div className="list-row"><span>Nome</span><strong>{currentUser.full_name}</strong></div>
            <div className="list-row"><span>Usuario</span><strong>{currentUser.username}</strong></div>
            <div className="list-row"><span>Perfil</span><strong>Administrador</strong></div>
          </div>
        </section>
        <form className="panel form-panel" onSubmit={submit}>
          <div className="panel-title"><h2>Trocar senha</h2></div>
          <p className="hint">A troca encerra todas as sessoes abertas. A nova senha deve ter pelo menos 8 caracteres.</p>
          {error ? <div className="alert compact-alert">{error}</div> : null}
          <label>Senha atual<input autoComplete="current-password" required type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} /></label>
          <label>Nova senha<input autoComplete="new-password" minLength={8} required type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label>
          <label>Confirmar nova senha<input autoComplete="new-password" minLength={8} required type="password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} /></label>
          <button className="primary-button" disabled={saving} type="submit">
            {saving ? <LoaderCircle className="spin" size={18} /> : <KeyRound size={18} />}
            {saving ? "Salvando..." : "Alterar senha"}
          </button>
        </form>
      </div>
    </>
  );
}

function DashboardPage({ dashboard, onNewExam }: { dashboard: Dashboard | null; onNewExam: () => void }) {
  if (!dashboard) return null;
  return (
    <>
      <SectionHeader
        eyebrow="Visao geral"
        title="Painel de controle"
        subtitle="Acompanhe provas, turmas, alunos e correcoes em um unico lugar."
        actions={
          <button className="primary-button" onClick={onNewExam} type="button">
            <Plus size={18} />
            Nova prova
          </button>
        }
      />
      <section className="metrics-grid">
        <MetricCard label="Alunos" value={dashboard.students} detail="cadastrados" icon={<GraduationCap />} />
        <MetricCard label="Turmas" value={dashboard.classrooms} detail="ativas" icon={<School />} tone="green" />
        <MetricCard label="Provas" value={dashboard.exams} detail="criadas" icon={<BookOpenCheck />} tone="amber" />
        <MetricCard
          label="Atribuicoes"
          value={dashboard.active_assignments}
          detail="em andamento"
          icon={<ClipboardCheck />}
          tone="violet"
        />
      </section>
    </>
  );
}

function LocalSearch({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}) {
  return (
    <div className="local-search">
      <Search size={18} />
      <input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
    </div>
  );
}

function StudentsPage({
  students,
  classrooms,
  allStudents,
  isMaster,
  onChanged,
}: {
  students: Student[];
  classrooms: Classroom[];
  allStudents: Student[];
  isMaster: boolean;
  onChanged: () => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [enrollment, setEnrollment] = useState("");
  const [classroomId, setClassroomId] = useState<number>(0);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const csvInputRef = useRef<HTMLInputElement | null>(null);
  const [message, setMessage] = useState("");
  const [importing, setImporting] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [editEnrollment, setEditEnrollment] = useState("");
  const [editClassroomId, setEditClassroomId] = useState<number>(0);
  const [studentSearch, setStudentSearch] = useState("");
  const [classroomSearch, setClassroomSearch] = useState("");
  const [showClassrooms, setShowClassrooms] = useState(false);
  const classroomPanelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!showClassrooms) return;
    classroomPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [showClassrooms]);

  const visibleStudents = useMemo(() => {
    const query = studentSearch.trim().toLowerCase();
    if (!query) return students;
    return students.filter((student) =>
      [student.name, student.email ?? "", student.enrollment_code ?? "", ...student.classroom_names].some((value) =>
        value.toLowerCase().includes(query),
      ),
    );
  }, [studentSearch, students]);

  const visibleClassrooms = useMemo(() => {
    const query = classroomSearch.trim().toLowerCase();
    if (!query) return classrooms;
    return classrooms.filter((classroom) =>
      [classroom.name, classroom.course_name ?? ""].some((value) => value.toLowerCase().includes(query)),
    );
  }, [classroomSearch, classrooms]);

  async function submit() {
    if (!name.trim()) return;
    await api.createStudent({
      name,
      email: email || undefined,
      enrollment_code: enrollment || undefined,
      classroom_ids: classroomId ? [classroomId] : [],
    });
    setName("");
    setEmail("");
    setEnrollment("");
    setClassroomId(0);
    await onChanged();
  }

  async function importCsv() {
    if (!csvFile) return;
    setImporting(true);
    try {
      const result = await api.importStudentsCsv(csvFile);
      setCsvFile(null);
      setMessage(result.message);
      await onChanged();
    } finally {
      setImporting(false);
    }
  }

  function startEdit(student: Student) {
    setEditingId(student.id);
    setEditName(student.name);
    setEditEmail(student.email ?? "");
    setEditEnrollment(student.enrollment_code ?? "");
    setEditClassroomId(student.classroom_ids[0] ?? 0);
  }

  function cancelEdit() {
    setEditingId(null);
    setEditName("");
    setEditEmail("");
    setEditEnrollment("");
    setEditClassroomId(0);
  }

  async function saveEdit(studentId: number) {
    if (!editName.trim()) return;
    await api.updateStudent(studentId, {
      name: editName,
      email: editEmail || undefined,
      enrollment_code: editEnrollment || undefined,
      classroom_ids: editClassroomId ? [editClassroomId] : [],
    });
    cancelEdit();
    await onChanged();
  }

  async function deleteStudent(student: Student) {
    if (!window.confirm(`Deseja excluir o aluno "${student.name}"?`)) return;
    await api.deleteStudent(student.id);
    await onChanged();
  }

  async function deleteAllStudents() {
    if (!window.confirm("Deseja excluir todos os alunos? Esta acao tambem remove vinculos com turmas e resultados de correcao.")) {
      return;
    }
    const result = await api.deleteAllStudents();
    setMessage(result.message);
    await onChanged();
  }

  return (
    <>
      <SectionHeader
        title="Alunos e turmas"
        subtitle="Cadastre estudantes, importe CSV e organize as turmas em uma unica area."
        actions={
          <>
            <button
              className={showClassrooms ? "ghost-button active" : "ghost-button"}
              onClick={() => setShowClassrooms((current) => !current)}
              type="button"
            >
              <School size={18} />
              {showClassrooms ? "Fechar turmas" : "Turmas"}
            </button>
            {isMaster ? (
              <button className="danger-button" onClick={deleteAllStudents} type="button">
                <Trash2 size={18} />
                Excluir todos
              </button>
            ) : null}
          </>
        }
      />
      {showClassrooms ? (
        <div className="section-spacer first" ref={classroomPanelRef}>
          <ClassroomsPage
            classrooms={visibleClassrooms}
            students={allStudents}
            onChanged={onChanged}
            embedded
            search={classroomSearch}
            onSearch={setClassroomSearch}
          />
        </div>
      ) : null}
      <div className="split-layout">
        <form className="panel form-panel" onSubmit={(event) => event.preventDefault()}>
          <h2>Novo aluno</h2>
          <label>
            Nome
            <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Ex: Ana Beatriz" />
          </label>
          <label>
            Email
            <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="ana@escola.com" />
          </label>
          <label>
            Matricula
            <input value={enrollment} onChange={(event) => setEnrollment(event.target.value)} placeholder="2026001" />
          </label>
          <label>
            Turma
            <select value={classroomId} onChange={(event) => setClassroomId(Number(event.target.value))}>
              <option value={0}>Sem turma</option>
              {classrooms.map((classroom) => (
                <option key={classroom.id} value={classroom.id}>
                  {classroom.name}
                </option>
              ))}
            </select>
          </label>
          <button className="primary-button" onClick={submit} type="button">
            <Plus size={18} />
            Cadastrar aluno
          </button>

          <div className="divider" />
          <h2>Importar CSV</h2>
          <p className="hint">Use colunas: nome, turma, matricula.</p>
          <input
            ref={csvInputRef}
            className="sr-only-file"
            accept=".csv,text/csv"
            onChange={(event) => setCsvFile(event.target.files?.[0] ?? null)}
            type="file"
          />
          <button className="file-button" onClick={() => csvInputRef.current?.click()} type="button">
            <span className="file-button-inner">
              <FileUp size={18} />
              <span>Escolher arquivo</span>
            </span>
          </button>
          <span className="file-name">{csvFile?.name ?? "Nenhum arquivo escolhido"}</span>
          <button className="ghost-button" disabled={importing || !csvFile} onClick={importCsv} type="button">
            {importing ? <LoaderCircle className="spin" size={18} /> : <Upload size={18} />}
            {importing ? "Importando..." : "Importar alunos"}
          </button>
          {message ? <div className="inline-message">{message}</div> : null}
        </form>
        <div className="panel table-panel">
          <div className="panel-title">
            <h2>Lista de alunos</h2>
            <span>{visibleStudents.length} registros</span>
          </div>
          <LocalSearch value={studentSearch} onChange={setStudentSearch} placeholder="Buscar aluno, matricula ou turma..." />
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>Email</th>
                <th>Matricula</th>
                <th>Turma</th>
                <th>Acoes</th>
              </tr>
            </thead>
            <tbody>
              {visibleStudents.map((student) => {
                const isEditing = editingId === student.id;
                return (
                  <tr key={student.id}>
                    <td>
                      {isEditing ? <input value={editName} onChange={(event) => setEditName(event.target.value)} /> : student.name}
                    </td>
                    <td>
                      {isEditing ? <input value={editEmail} onChange={(event) => setEditEmail(event.target.value)} /> : student.email ?? "-"}
                    </td>
                    <td>
                      {isEditing ? (
                        <input value={editEnrollment} onChange={(event) => setEditEnrollment(event.target.value)} />
                      ) : (
                        student.enrollment_code ?? "-"
                      )}
                    </td>
                    <td>
                      {isEditing ? (
                        <select value={editClassroomId} onChange={(event) => setEditClassroomId(Number(event.target.value))}>
                          <option value={0}>Sem turma</option>
                          {classrooms.map((classroom) => (
                            <option key={classroom.id} value={classroom.id}>
                              {classroom.name}
                            </option>
                          ))}
                        </select>
                      ) : (
                        student.classroom_names.join(", ") || "-"
                      )}
                    </td>
                    <td>
                      <div className="row-actions">
                        {isEditing ? (
                          <>
                            <button className="icon-button small" aria-label="Salvar aluno" onClick={() => saveEdit(student.id)} type="button">
                              <Save size={16} />
                            </button>
                            <button className="icon-button small" aria-label="Cancelar edicao" onClick={cancelEdit} type="button">
                              <X size={16} />
                            </button>
                          </>
                        ) : (
                          <>
                            <button className="icon-button small" aria-label="Editar aluno" onClick={() => startEdit(student)} type="button">
                              <Pencil size={16} />
                            </button>
                            <button className="icon-button small danger" aria-label="Excluir aluno" onClick={() => deleteStudent(student)} type="button">
                              <Trash2 size={16} />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {!visibleStudents.length ? <div className="empty-state">Nenhum registro encontrado.</div> : null}
        </div>
      </div>
    </>
  );
}

function ClassroomsPage({
  classrooms,
  students,
  onChanged,
  embedded = false,
  search = "",
  onSearch,
}: {
  classrooms: Classroom[];
  students: Student[];
  onChanged: () => Promise<void>;
  embedded?: boolean;
  search?: string;
  onSearch?: (value: string) => void;
}) {
  const [name, setName] = useState("");
  const [course, setCourse] = useState("");
  const [selected, setSelected] = useState<number[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editCourse, setEditCourse] = useState("");

  async function submit() {
    if (!name.trim()) return;
    await api.createClassroom({ name, course_name: course || undefined, student_ids: selected });
    setName("");
    setCourse("");
    setSelected([]);
    await onChanged();
  }

  function toggleStudent(studentId: number) {
    setSelected((current) => (current.includes(studentId) ? current.filter((id) => id !== studentId) : [...current, studentId]));
  }

  function startEdit(classroom: Classroom) {
    setEditingId(classroom.id);
    setEditName(classroom.name);
    setEditCourse(classroom.course_name ?? "");
  }

  function cancelEdit() {
    setEditingId(null);
    setEditName("");
    setEditCourse("");
  }

  async function saveEdit(classroomId: number) {
    if (!editName.trim()) return;
    await api.updateClassroom(classroomId, { name: editName, course_name: editCourse || undefined });
    cancelEdit();
    await onChanged();
  }

  async function deleteClassroom(classroom: Classroom) {
    if (!window.confirm(`Deseja excluir a turma "${classroom.name}"?`)) return;
    await api.deleteClassroom(classroom.id);
    await onChanged();
  }

  return (
    <>
      {embedded ? null : <SectionHeader title="Turmas" subtitle="Agrupe alunos por curso, serie ou periodo letivo." />}
      <div className="split-layout">
        <form className="panel form-panel" onSubmit={(event) => event.preventDefault()}>
          <h2>Nova turma</h2>
          <label>
            Nome da turma
            <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Ex: 1 Ano A" />
          </label>
          <label>
            Curso
            <input value={course} onChange={(event) => setCourse(event.target.value)} placeholder="Ex: Ensino Medio" />
          </label>
          <div className="check-grid">
            {students.map((student) => (
              <label className="check-card" key={student.id}>
                <input checked={selected.includes(student.id)} onChange={() => toggleStudent(student.id)} type="checkbox" />
                <span>{student.name}</span>
              </label>
            ))}
          </div>
          <button className="primary-button" onClick={submit} type="button">
            <Plus size={18} />
            Criar turma
          </button>
        </form>
        <div className="panel table-panel">
          <div className="panel-title">
            <h2>Turmas cadastradas</h2>
            <span>{classrooms.length} registros</span>
          </div>
          {onSearch ? <LocalSearch value={search} onChange={onSearch} placeholder="Buscar turma ou curso..." /> : null}
          <table>
            <thead>
              <tr>
                <th>Turma</th>
                <th>Curso</th>
                <th>Alunos</th>
                <th>Acoes</th>
              </tr>
            </thead>
            <tbody>
              {classrooms.map((classroom) => {
                const isEditing = editingId === classroom.id;
                return (
                  <tr key={classroom.id}>
                    <td>
                      {isEditing ? <input value={editName} onChange={(event) => setEditName(event.target.value)} /> : classroom.name}
                    </td>
                    <td>
                      {isEditing ? <input value={editCourse} onChange={(event) => setEditCourse(event.target.value)} /> : classroom.course_name ?? "-"}
                    </td>
                    <td>{classroom.student_count}</td>
                    <td>
                      <div className="row-actions">
                        {isEditing ? (
                          <>
                            <button className="icon-button small" aria-label="Salvar turma" onClick={() => saveEdit(classroom.id)} type="button">
                              <Save size={16} />
                            </button>
                            <button className="icon-button small" aria-label="Cancelar edicao" onClick={cancelEdit} type="button">
                              <X size={16} />
                            </button>
                          </>
                        ) : (
                          <>
                            <button className="icon-button small" aria-label="Editar turma" onClick={() => startEdit(classroom)} type="button">
                              <Pencil size={16} />
                            </button>
                            <button className="icon-button small danger" aria-label="Excluir turma" onClick={() => deleteClassroom(classroom)} type="button">
                              <Trash2 size={16} />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {!classrooms.length ? <div className="empty-state">Nenhuma turma encontrada.</div> : null}
        </div>
      </div>
    </>
  );
}

function ExamsPage({
  exams,
  assignments,
  classrooms,
  onChanged,
}: {
  exams: Exam[];
  assignments: Assignment[];
  classrooms: Classroom[];
  onChanged: () => Promise<void>;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [questionCount, setQuestionCount] = useState(5);
  const [optionCount, setOptionCount] = useState(5);
  const [answers, setAnswers] = useState<number[]>([0, 0, 0, 0, 0]);
  const [examId, setExamId] = useState<number>(0);
  const [selectedClassrooms, setSelectedClassrooms] = useState<number[]>([]);
  const [editingExamId, setEditingExamId] = useState<number | null>(null);
  const [examSearch, setExamSearch] = useState("");

  const normalizedAnswers = useMemo(
    () => Array.from({ length: questionCount }, (_, index) => Math.min(answers[index] ?? 0, optionCount - 1)),
    [answers, optionCount, questionCount],
  );
  const visibleExams = useMemo(() => {
    const query = examSearch.trim().toLowerCase();
    if (!query) return exams;
    return exams.filter((exam) =>
      [exam.title, exam.description ?? ""].some((value) => value.toLowerCase().includes(query)),
    );
  }, [examSearch, exams]);
  const visibleAssignments = useMemo(() => {
    const query = examSearch.trim().toLowerCase();
    if (!query) return assignments;
    return assignments.filter((assignment) =>
      [assignment.exam_title, assignment.classroom_name].some((value) => value.toLowerCase().includes(query)),
    );
  }, [assignments, examSearch]);
  const assignedClassroomIds = useMemo(
    () =>
      new Set(
        assignments
          .filter((assignment) => assignment.exam_id === examId)
          .map((assignment) => assignment.classroom_id),
      ),
    [assignments, examId],
  );

  useEffect(() => {
    if (!examId && exams[0]) setExamId(exams[0].id);
  }, [examId, exams]);

  useEffect(() => {
    setSelectedClassrooms((current) => current.filter((classroomId) => !assignedClassroomIds.has(classroomId)));
  }, [assignedClassroomIds]);

  async function submit() {
    if (!title.trim()) return;
    const payload = {
      title,
      description: description || undefined,
      question_count: questionCount,
      option_count: optionCount,
      answer_key: normalizedAnswers.map((optionIndex, index) => ({
        question_number: index + 1,
        option_index: optionIndex,
        weight: 1,
      })),
    };
    const exam = editingExamId ? await api.updateExam(editingExamId, payload) : await api.createExam(payload);
    setTitle("");
    setDescription("");
    setQuestionCount(5);
    setOptionCount(5);
    setAnswers([0, 0, 0, 0, 0]);
    setEditingExamId(null);
    setExamId(exam.id);
    await onChanged();
  }

  function startExamEdit(exam: Exam) {
    setEditingExamId(exam.id);
    setTitle(exam.title);
    setDescription(exam.description ?? "");
    setQuestionCount(exam.question_count);
    setOptionCount(exam.option_count);
    setAnswers(
      Array.from({ length: exam.question_count }, (_, index) => {
        const item = exam.answer_key.find((answer) => answer.question_number === index + 1);
        return item?.option_index ?? 0;
      }),
    );
  }

  function cancelExamEdit() {
    setEditingExamId(null);
    setTitle("");
    setDescription("");
    setQuestionCount(5);
    setOptionCount(5);
    setAnswers([0, 0, 0, 0, 0]);
  }

  async function deleteExam(exam: Exam) {
    if (!window.confirm(`Deseja excluir a prova "${exam.title}"? As atribuicoes e resultados relacionados tambem serao excluidos.`)) {
      return;
    }
    await api.deleteExam(exam.id);
    if (editingExamId === exam.id) cancelExamEdit();
    await onChanged();
  }

  async function assign() {
    if (!examId || selectedClassrooms.length === 0) return;
    await api.assignExam(examId, selectedClassrooms);
    setSelectedClassrooms([]);
    await onChanged();
  }

  function updateAnswer(index: number, optionIndex: number) {
    setAnswers((current) => {
      const next = [...current];
      next[index] = optionIndex;
      return next;
    });
  }

  function toggleClassroom(classroomId: number) {
    setSelectedClassrooms((current) =>
      current.includes(classroomId) ? current.filter((id) => id !== classroomId) : [...current, classroomId],
    );
  }

  return (
    <>
      <SectionHeader title="Provas" subtitle="Crie prova, defina gabarito, atribua turmas e gere cartoes-resposta." />
      <div className="split-layout wide-left">
        <form className="panel form-panel exam-builder" onSubmit={(event) => event.preventDefault()}>
          <div className="panel-title flush">
            <h2>{editingExamId ? "Editar prova" : "Criar prova"}</h2>
            {editingExamId ? (
              <button className="ghost-button compact" onClick={cancelExamEdit} type="button">
                <X size={16} />
                Cancelar
              </button>
            ) : null}
          </div>
          <label>
            Nome da prova
            <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Ex: Simulado de Biologia" />
          </label>
          <label>
            Descricao
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Opcional: observacoes para o professor"
            />
          </label>
          <div className="field-row">
            <label>
              Questoes
              <input
                min={1}
                type="number"
                value={questionCount}
                onChange={(event) => setQuestionCount(Number(event.target.value))}
              />
            </label>
            <label>
              Alternativas
              <input
                max={7}
                min={2}
                type="number"
                value={optionCount}
                onChange={(event) => setOptionCount(Number(event.target.value))}
              />
            </label>
          </div>
          <div className="answer-grid">
            {normalizedAnswers.map((answer, questionIndex) => (
              <div className="answer-row" key={questionIndex}>
                <span>{questionIndex + 1}</span>
                <div className="segmented">
                  {optionLabels.slice(0, optionCount).map((label, optionIndex) => (
                    <button
                      className={answer === optionIndex ? "selected" : ""}
                      key={label}
                      onClick={() => updateAnswer(questionIndex, optionIndex)}
                      type="button"
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <button className="primary-button" onClick={submit} type="button">
            {editingExamId ? <Save size={18} /> : <CheckCircle2 size={18} />}
            {editingExamId ? "Atualizar prova" : "Salvar prova"}
          </button>
        </form>

        <div className="stack-list">
          <div className="panel compact-panel">
            <LocalSearch value={examSearch} onChange={setExamSearch} placeholder="Buscar prova ou turma atribuida..." />
          </div>
          <form className="panel form-panel" onSubmit={(event) => event.preventDefault()}>
            <h2>Atribuir prova a turmas</h2>
            <label>
              Prova
              <select value={examId} onChange={(event) => setExamId(Number(event.target.value))}>
                {exams.map((exam) => (
                  <option key={exam.id} value={exam.id}>
                    {exam.title}
                  </option>
                ))}
              </select>
            </label>
            <div className="check-grid compact">
              {classrooms.map((classroom) => (
                <label className={assignedClassroomIds.has(classroom.id) ? "check-card assigned" : "check-card"} key={classroom.id}>
                  <input
                    checked={assignedClassroomIds.has(classroom.id) || selectedClassrooms.includes(classroom.id)}
                    disabled={assignedClassroomIds.has(classroom.id)}
                    onChange={() => toggleClassroom(classroom.id)}
                    type="checkbox"
                  />
                  <span>{classroom.name}</span>
                  {assignedClassroomIds.has(classroom.id) ? <small>Atribuida</small> : null}
                </label>
              ))}
            </div>
            <button className="primary-button" onClick={assign} type="button">
              <Send size={18} />
              Atribuir prova
            </button>
          </form>

          <ExamsTable exams={visibleExams} onEdit={startExamEdit} onDelete={deleteExam} />

          <AssignmentsPanel assignments={visibleAssignments} onChanged={onChanged} />
        </div>
      </div>
    </>
  );
}

function ExamsTable({
  exams,
  onEdit,
  onDelete,
}: {
  exams: Exam[];
  onEdit: (exam: Exam) => void;
  onDelete: (exam: Exam) => void;
}) {
  return (
    <div className="panel table-panel">
      <div className="panel-title">
        <h2>Provas criadas</h2>
        <span>{exams.length} registros</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>Prova</th>
            <th>Questoes</th>
            <th>Atribuicoes</th>
            <th>Acoes</th>
          </tr>
        </thead>
        <tbody>
          {exams.map((exam) => (
            <tr key={exam.id}>
              <td>{exam.title}</td>
              <td>{exam.question_count}</td>
              <td>{exam.assignment_count} turma(s)</td>
              <td>
                <div className="row-actions">
                  <button className="icon-button small" aria-label="Editar prova" onClick={() => onEdit(exam)} type="button">
                    <Pencil size={16} />
                  </button>
                  <button className="icon-button small danger" aria-label="Excluir prova" onClick={() => onDelete(exam)} type="button">
                    <Trash2 size={16} />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!exams.length ? <div className="empty-state">Nenhuma prova encontrada.</div> : null}
    </div>
  );
}

function AssignmentsPanel({ assignments, onChanged }: { assignments: Assignment[]; onChanged: () => Promise<void> }) {
  const [downloadingId, setDownloadingId] = useState<number | null>(null);

  async function downloadAnswerSheets(assignment: Assignment) {
    setDownloadingId(assignment.id);
    try {
      const blob = await api.answerSheets(assignment.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `gabaritos-${assignment.exam_title}-${assignment.classroom_name}.pdf`.replace(/[\\/:*?"<>|]+/g, "-");
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } finally {
      setDownloadingId(null);
    }
  }

  async function deleteAssignment(assignment: Assignment) {
    if (!window.confirm(`Deseja excluir a atribuicao de "${assignment.exam_title}" para "${assignment.classroom_name}"?`)) {
      return;
    }
    await api.deleteAssignment(assignment.id);
    await onChanged();
  }

  return (
    <div className="panel table-panel">
      <div className="panel-title">
        <h2>Turmas atribuidas</h2>
        <span>{assignments.length} registros</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>Prova</th>
            <th>Turma</th>
            <th>Status</th>
            <th>Gabaritos</th>
            <th>Acoes</th>
          </tr>
        </thead>
        <tbody>
          {assignments.map((assignment) => (
            <tr key={assignment.id}>
              <td>{assignment.exam_title}</td>
              <td>{assignment.classroom_name}</td>
              <td>
                <StatusBadge status={assignment.status} />
              </td>
              <td>
                <button
                  className="table-action"
                  disabled={downloadingId === assignment.id}
                  onClick={() => downloadAnswerSheets(assignment)}
                  type="button"
                >
                  {downloadingId === assignment.id ? <LoaderCircle className="spin" size={16} /> : <Download size={16} />}
                  {downloadingId === assignment.id ? "Baixando" : "PDF"}
                </button>
              </td>
              <td>
                <button className="icon-button small danger" aria-label="Excluir atribuicao" onClick={() => deleteAssignment(assignment)} type="button">
                  <Trash2 size={16} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!assignments.length ? <div className="empty-state">Nenhuma atribuicao encontrada.</div> : null}
    </div>
  );
}

function GradesPage({ assignments, onChanged }: { assignments: Assignment[]; onChanged: () => Promise<void> }) {
  const [assignmentId, setAssignmentId] = useState<number>(assignments[0]?.id ?? 0);
  const [gradeData, setGradeData] = useState<GradeAssignment | null>(null);
  const [loadingGrades, setLoadingGrades] = useState(false);
  const [editingStudentId, setEditingStudentId] = useState<number | null>(null);
  const [draftScore, setDraftScore] = useState("");
  const [uploadingStudentId, setUploadingStudentId] = useState<number | null>(null);
  const [gradeSearch, setGradeSearch] = useState("");
  const gradeInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!assignmentId && assignments[0]) setAssignmentId(assignments[0].id);
  }, [assignmentId, assignments]);

  async function loadGrades(nextAssignmentId = assignmentId) {
    if (!nextAssignmentId) {
      setGradeData(null);
      return;
    }
    setLoadingGrades(true);
    try {
      setGradeData(await api.assignmentGrades(nextAssignmentId));
    } finally {
      setLoadingGrades(false);
    }
  }

  useEffect(() => {
    void loadGrades();
  }, [assignmentId]);

  function startGradeEdit(studentId: number, result: CorrectionResult | null) {
    setEditingStudentId(studentId);
    setDraftScore(result ? String(result.score) : "");
  }

  async function saveGrade(studentId: number, result: CorrectionResult | null) {
    if (!assignmentId) return;
    const score = Number(draftScore.replace(",", "."));
    if (!Number.isFinite(score) || score < 0) return;
    if (result) {
      await api.updateManualGrade(result.id, score);
    } else {
      await api.saveManualGrade(assignmentId, studentId, score);
    }
    setEditingStudentId(null);
    setDraftScore("");
    await loadGrades();
    await onChanged();
  }

  async function deleteGrade(result: CorrectionResult) {
    if (!window.confirm(`Deseja excluir a nota de "${result.student_name}"?`)) return;
    await api.deleteGrade(result.id);
    await loadGrades();
    await onChanged();
  }

  async function downloadReport() {
    if (!assignmentId || !gradeData) return;
    const blob = await api.gradesReport(assignmentId);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `Notas_Alunos_${gradeData.exam.title}.csv`.replace(/[\\/:*?"<>| ]+/g, "_");
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  async function correctStudentSheet(file: File | null) {
    if (!file || !assignmentId) return;
    await api.correctAssignment(assignmentId, [file]);
    setUploadingStudentId(null);
    if (gradeInputRef.current) gradeInputRef.current.value = "";
    await loadGrades();
    await onChanged();
  }

  const selectedAssignment = assignments.find((assignment) => assignment.id === assignmentId);
  const visibleGradeStudents = useMemo(() => {
    const query = gradeSearch.trim().toLowerCase();
    const rows = gradeData?.students ?? [];
    if (!query) return rows;
    return rows.filter((student) =>
      [
        student.student_name,
        student.enrollment_code ?? "",
        student.result?.source_filename ?? "",
        student.result ? String(student.result.score) : "sem nota",
      ].some((value) => value.toLowerCase().includes(query)),
    );
  }, [gradeData, gradeSearch]);
  const gradeMaxScore = gradeData?.exam.answer_key.reduce((total, item) => total + item.weight, 0) ?? 0;

  return (
    <>
      <SectionHeader
        title="Notas"
        subtitle="Acompanhe notas por turma, edite resultados individuais e gere o relatorio de acertos e erros."
        actions={
          <button className="primary-button" disabled={!gradeData} onClick={downloadReport} type="button">
            <Download size={18} />
            Gerar relatorio
          </button>
        }
      />
      <div className="grades-layout">
        <div className="panel grades-filter">
          <label>
            Turma e prova
            <select value={assignmentId} onChange={(event) => setAssignmentId(Number(event.target.value))}>
              {assignments.map((assignment) => (
                <option key={assignment.id} value={assignment.id}>
                  {assignment.classroom_name} - {assignment.exam_title}
                </option>
              ))}
            </select>
          </label>
          {selectedAssignment ? (
            <div className="grade-summary">
              <strong>{selectedAssignment.classroom_name}</strong>
              <span>{selectedAssignment.exam_title}</span>
              <small>{gradeData?.students.filter((student) => student.result).length ?? 0} nota(s) lancada(s)</small>
            </div>
          ) : (
            <div className="empty-state">Nenhuma turma atribuida a uma prova.</div>
          )}
        </div>

        <div className="panel table-panel">
          <div className="panel-title">
            <h2>Notas da turma</h2>
            <span>{loadingGrades ? "Carregando" : `${visibleGradeStudents.length} alunos`}</span>
          </div>
          <LocalSearch value={gradeSearch} onChange={setGradeSearch} placeholder="Buscar aluno, matricula ou nota..." />
          <input
            ref={gradeInputRef}
            className="sr-only-file"
            accept=".csv,image/*"
            onChange={(event) => void correctStudentSheet(event.target.files?.[0] ?? null)}
            type="file"
          />
          <table>
            <thead>
              <tr>
                <th>Aluno</th>
                <th>Matricula</th>
                <th>Nota</th>
                <th>Origem</th>
                <th>Acoes</th>
              </tr>
            </thead>
            <tbody>
              {visibleGradeStudents.map((student) => {
                const isEditing = editingStudentId === student.student_id;
                const result = student.result;
                return (
                  <tr key={student.student_id}>
                    <td>{student.student_name}</td>
                    <td>{student.enrollment_code ?? "-"}</td>
                    <td>
                      {isEditing ? (
                        <label className="inline-grade-field">
                          Nota
                          <input
                            max={result?.max_score ?? gradeMaxScore}
                            min={0}
                            step="0.01"
                            type="number"
                            value={draftScore}
                            onChange={(event) => setDraftScore(event.target.value)}
                          />
                        </label>
                      ) : result ? (
                        `${result.score}/${result.max_score}`
                      ) : (
                        "Sem nota"
                      )}
                    </td>
                    <td>{result?.source_filename ?? "-"}</td>
                    <td>
                      <div className="row-actions">
                        {isEditing ? (
                          <>
                            <button className="icon-button small" aria-label="Salvar nota" onClick={() => saveGrade(student.student_id, result)} type="button">
                              <Save size={16} />
                            </button>
                            <button
                              className="icon-button small"
                              aria-label="Cancelar edicao"
                              onClick={() => {
                                setEditingStudentId(null);
                                setDraftScore("");
                              }}
                              type="button"
                            >
                              <X size={16} />
                            </button>
                          </>
                        ) : result ? (
                          <>
                            <button className="icon-button small" aria-label="Editar nota" onClick={() => startGradeEdit(student.student_id, result)} type="button">
                              <Pencil size={16} />
                            </button>
                            <button className="icon-button small danger" aria-label="Excluir nota" onClick={() => deleteGrade(result)} type="button">
                              <Trash2 size={16} />
                            </button>
                          </>
                        ) : (
                          <>
                            <button className="icon-button small" aria-label="Adicionar nota" onClick={() => startGradeEdit(student.student_id, null)} type="button">
                              <Plus size={16} />
                            </button>
                            <button
                              className="table-action"
                              onClick={() => {
                                setUploadingStudentId(student.student_id);
                                gradeInputRef.current?.click();
                              }}
                              type="button"
                            >
                              {uploadingStudentId === student.student_id ? <LoaderCircle className="spin" size={16} /> : <FileUp size={16} />}
                              Corrigir
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {!visibleGradeStudents.length ? <div className="empty-state">Nenhum aluno encontrado para esta turma.</div> : null}
        </div>
      </div>
    </>
  );
}

function CorrectionsPage({ assignments, onChanged }: { assignments: Assignment[]; onChanged: () => Promise<void> }) {
  const [assignmentId, setAssignmentId] = useState<number>(assignments[0]?.id ?? 0);
  const [files, setFiles] = useState<File[]>([]);
  const correctionInputRef = useRef<HTMLInputElement | null>(null);
  const [message, setMessage] = useState("");
  const [results, setResults] = useState<CorrectionResult[]>([]);
  const [correcting, setCorrecting] = useState(false);

  useEffect(() => {
    if (!assignmentId && assignments[0]) setAssignmentId(assignments[0].id);
  }, [assignmentId, assignments]);

  useEffect(() => {
    if (!assignmentId) {
      setResults([]);
      return;
    }
    void api.correctionResults(assignmentId).then(setResults);
  }, [assignmentId]);

  async function submit() {
    if (!assignmentId || files.length === 0) return;
    setCorrecting(true);
    try {
      const result = await api.correctAssignment(assignmentId, files);
      setMessage(result.message);
      setFiles([]);
      setResults(await api.correctionResults(assignmentId));
      await onChanged();
    } finally {
      setCorrecting(false);
    }
  }

  return (
    <>
      <SectionHeader title="Correcao" subtitle="Envie imagens digitalizadas ou CSV de respostas para corrigir gabaritos." />
      <div className="split-layout">
        <div className="panel upload-panel">
          <div className="upload-icon">
            <FileUp size={28} />
          </div>
          <h2>Corrigir gabaritos</h2>
          <div className="field-row">
            <label>
              Atribuicao
              <select value={assignmentId} onChange={(event) => setAssignmentId(Number(event.target.value))}>
                {assignments.map((assignment) => (
                  <option key={assignment.id} value={assignment.id}>
                    {assignment.exam_title} - {assignment.classroom_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Arquivos
              <input
                ref={correctionInputRef}
                className="sr-only-file"
                accept=".csv,image/*"
                multiple
                onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
                type="file"
              />
              <button className="file-button" onClick={() => correctionInputRef.current?.click()} type="button">
                <span className="file-button-inner">
                  <FileUp size={18} />
                  <span>Escolher arquivos</span>
                </span>
              </button>
              <span className="file-name">
                {files.length ? `${files.length} arquivo(s) selecionado(s)` : "Nenhum arquivo escolhido"}
              </span>
            </label>
          </div>
          <p>CSV de respostas: coluna matricula e colunas q1, q2, q3... com A-G ou 1-7.</p>
          <button className="primary-button" disabled={correcting || files.length === 0} onClick={submit} type="button">
            {correcting ? <LoaderCircle className="spin" size={18} /> : <FileUp size={18} />}
            {correcting ? "Enviando..." : "Corrigir arquivos"}
          </button>
          {message ? <div className="inline-message">{message}</div> : null}
        </div>

        <DataTable
          title="Resultados"
          columns={["Aluno", "Matricula", "Nota", "Arquivo"]}
          rows={results.map((result) => [
            result.student_name,
            result.enrollment_code ?? "-",
            `${result.score}/${result.max_score}`,
            result.source_filename ?? "-",
          ])}
        />
      </div>
    </>
  );
}

function DataTable({ title, columns, rows }: { title: string; columns: string[]; rows: string[][] }) {
  return (
    <div className="panel table-panel">
      <div className="panel-title">
        <h2>{title}</h2>
        <span>{rows.length} registros</span>
      </div>
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`${row[0]}-${rowIndex}`}>
              {row.map((cell, cellIndex) => (
                <td key={`${cell}-${cellIndex}`}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {!rows.length ? <div className="empty-state">Nenhum registro encontrado.</div> : null}
    </div>
  );
}

import {
  BarChart3,
  BookOpenCheck,
  ClipboardCheck,
  GraduationCap,
  LayoutGrid,
  LogOut,
  TableProperties,
  Users,
} from "lucide-react";
import type { ReactNode } from "react";
import type { CurrentUser } from "../lib/api";

export type PageKey = "dashboard" | "students" | "grades" | "exams" | "corrections" | "users";

const navItems: Array<{ key: PageKey; label: string; icon: ReactNode; adminOnly?: boolean }> = [
  { key: "dashboard", label: "Painel", icon: <LayoutGrid size={18} /> },
  { key: "students", label: "Alunos e turmas", icon: <GraduationCap size={18} /> },
  { key: "grades", label: "Notas", icon: <TableProperties size={18} /> },
  { key: "exams", label: "Provas", icon: <BookOpenCheck size={18} /> },
  { key: "corrections", label: "Correcao", icon: <ClipboardCheck size={18} /> },
  { key: "users", label: "Controle de usuarios", icon: <Users size={18} />, adminOnly: true },
];

type ShellProps = {
  activePage: PageKey;
  onNavigate: (page: PageKey) => void;
  currentUser: CurrentUser | null;
  onLogout: () => void;
  children: ReactNode;
};

export function Shell({ activePage, onNavigate, currentUser, onLogout, children }: ShellProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <BarChart3 size={23} />
          </div>
          <div>
            <strong>CorretorApp</strong>
            <span>Correcao de provas</span>
          </div>
        </div>

        <nav className="nav-list">
          {navItems.filter((item) => !item.adminOnly || currentUser?.role === "admin").map((item) => (
            <button
              className={item.key === activePage ? "nav-item active" : "nav-item"}
              key={item.key}
              onClick={() => onNavigate(item.key)}
              type="button"
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
      </aside>

      <div className="main-frame">
        <header className="topbar">
          <div className="topbar-actions">
            <button
              className="ghost-button"
              onClick={currentUser?.role === "admin" ? () => onNavigate("users") : undefined}
              type="button"
            >
              <Users size={18} />
              {currentUser?.full_name ?? "Usuario"}
            </button>
            <button className="icon-button" aria-label="Sair" onClick={onLogout} type="button">
              <LogOut size={18} />
            </button>
          </div>
        </header>

        <main className="content">{children}</main>
      </div>
    </div>
  );
}

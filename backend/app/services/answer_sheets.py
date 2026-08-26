from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import hashlib
from configparser import ConfigParser
from pathlib import Path

from app.models import ExamAssignment


ANSWER_SHEET_CACHE_VERSION = "compact-professional-header-v7"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _legacy_python_bin() -> str:
    project_root = _project_root()
    settings_path = project_root / "src" / "settings.ini"
    if settings_path.exists():
        config = ConfigParser()
        config.read(settings_path, encoding="utf-8")
        configured = config.get("SYSTEM", "python_windows_path", fallback="")
        candidate = project_root / configured.strip('"')
        if candidate.exists():
            try:
                subprocess.run([str(candidate), "--version"], capture_output=True, timeout=5, check=True)
                return str(candidate)
            except Exception:
                pass
    return sys.executable


def build_answer_sheet_pdf(assignment: ExamAssignment, teacher_name: str, user_id: int) -> bytes:
    project_root = _project_root()
    script = project_root / "src" / "test_core" / "generate_from_payload.py"
    if not script.exists():
        raise RuntimeError("Gerador legado de gabaritos nao encontrado.")

    exam_date = assignment.exam.exam_date.isoformat() if assignment.exam.exam_date else assignment.assigned_at.date().isoformat()
    payload = {
        "exam_id": assignment.exam_id,
        "exam_title": assignment.exam.title,
        "teacher_name": teacher_name,
        "classroom_name": assignment.classroom.name,
        "exam_date": exam_date,
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
        "students": [{"id": link.student.id, "name": link.student.name} for link in assignment.classroom.students],
        "user_id": user_id,
    }
    cache_root = project_root / "backend" / ".answer_sheet_cache"
    cache_root.mkdir(exist_ok=True)
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    cache_payload = json.dumps(
        {"version": ANSWER_SHEET_CACHE_VERSION, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
    )
    cache_key = hashlib.sha256(cache_payload.encode("utf-8")).hexdigest()[:24]
    cache_path = cache_root / f"assignment-{assignment.id}-{cache_key}.pdf"
    if cache_path.exists():
        return cache_path.read_bytes()

    with tempfile.TemporaryDirectory() as tempdir:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(script.parent)
        process = subprocess.run(
            [_legacy_python_bin(), str(script), payload_json, tempdir],
            cwd=tempdir,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        if process.returncode != 0:
            raise RuntimeError(process.stdout + process.stderr)
        pdf_path = Path(tempdir) / f"prova{user_id}.pdf"
        if not pdf_path.exists():
            raise RuntimeError(process.stdout + process.stderr or "Gerador legado nao retornou PDF.")
        pdf_bytes = pdf_path.read_bytes()
        cache_path.write_bytes(pdf_bytes)
        return pdf_bytes

from fastapi import APIRouter

from app.api import auth, classrooms, corrections, dashboard, exams, students, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(students.router)
api_router.include_router(classrooms.router)
api_router.include_router(exams.router)
api_router.include_router(corrections.router)
api_router.include_router(users.router)

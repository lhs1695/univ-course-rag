from fastapi import FastAPI

from app.api.admin_courses import router as admin_courses_router
from app.api.ask import router as ask_router
from app.api.auth import router as auth_router
from app.api.courses import router as courses_router
from app.api.documents import router as documents_router
from app.api.insights import router as insights_router
from app.api.search import router as search_router
from app.api.users import router as admin_users_router

app = FastAPI()
app.include_router(auth_router)
app.include_router(admin_users_router)
app.include_router(admin_courses_router)
app.include_router(courses_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(ask_router)
app.include_router(insights_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

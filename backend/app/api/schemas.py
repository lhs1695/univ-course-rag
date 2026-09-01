from datetime import datetime

from pydantic import BaseModel, Field

from app.models.course import CourseMemberRole
from app.models.user import UserRole


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class UserOut(BaseModel):
    id: str
    username: str
    role: str


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)
    role: UserRole


class CourseCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class CourseUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class CourseOut(BaseModel):
    id: str
    title: str


class AdminAddMemberRequest(BaseModel):
    user_id: str
    role: CourseMemberRole


class TeacherAddStudentRequest(BaseModel):
    user_id: str


class CourseMemberOut(BaseModel):
    user_id: str
    username: str
    role: str


class DocumentOut(BaseModel):
    id: str
    filename: str
    job_status: str
    error_message: str | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class SearchHitOut(BaseModel):
    chunk_id: str
    document_id: str
    page: int | None
    snippet: str
    score: float


class SearchResponse(BaseModel):
    hits: list[SearchHitOut]


class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class CitationOut(BaseModel):
    chunk_id: str
    document_id: str
    page: int | None
    snippet: str


class AskResponse(BaseModel):
    error_code: str | None = None
    message: str | None = None
    answer: str | None = None
    citations: list[CitationOut]


class FrequentQuestionOut(BaseModel):
    query: str
    count: int


class NoEvidenceQuestionOut(BaseModel):
    query: str
    count: int
    last_asked_at: datetime


class InsightsResponse(BaseModel):
    frequent: list[FrequentQuestionOut]
    no_evidence: list[NoEvidenceQuestionOut]

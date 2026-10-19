from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field, model_validator

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


class CourseCapabilities(BaseModel):
    can_manage_documents: bool = False
    can_manage_members: bool = False
    can_view_insights: bool = False


class CourseOut(BaseModel):
    id: str
    title: str
    membership_role: CourseMemberRole | None = None
    capabilities: CourseCapabilities = Field(default_factory=CourseCapabilities)


class AdminAddMemberRequest(BaseModel):
    user_id: str
    role: CourseMemberRole


class TeacherAddStudentRequest(BaseModel):
    user_id: str | None = None
    username: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def require_student_identity(self) -> "TeacherAddStudentRequest":
        has_id = bool(self.user_id and self.user_id.strip())
        has_name = bool(self.username and self.username.strip())
        if not has_id and not has_name:
            raise ValueError("user_id or username is required")
        return self


class CourseMemberOut(BaseModel):
    user_id: str
    username: str
    role: str


class DocumentOut(BaseModel):
    id: str
    filename: str
    job_status: str
    error_message: str | None = None
    source_unit_count: int | None = None
    extracted_char_count: int | None = None
    chunk_count: int | None = None
    quality_warning: str | None = None
    chunking_version: str | None = None


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
    previous_question: str | None = Field(default=None, max_length=2000)
    previous_answer: str | None = Field(default=None, max_length=6000)


class CitationOut(BaseModel):
    chunk_id: str
    document_id: str
    page: int | None
    snippet: str  # Exact bounded body supplied in this generation, not a search excerpt.
    content_url: str


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


class InsightsSummary(BaseModel):
    recorded_attempts: int
    student_attempts: int
    cited_answer: int
    no_evidence: int
    failure: int
    unknown_outcome: int
    non_student_attempts: int
    unknown_role_attempts: int
    knowledge_attempts: int
    no_evidence_rate: float | None


class InsightsTrendPoint(BaseModel):
    bucket_start: datetime
    cited_answer: int
    no_evidence: int
    failure: int
    unknown_outcome: int


class InsightsResponse(BaseModel):
    retention_days: int
    window_start: datetime
    window_end: datetime
    summary: InsightsSummary
    trend: list[InsightsTrendPoint]
    frequent: list[FrequentQuestionOut]
    no_evidence: list[NoEvidenceQuestionOut]


class QuestionGroupingRequest(BaseModel):
    min_similarity: float = Field(gt=0, le=1, allow_inf_nan=False)
    start_at: AwareDatetime | None = None
    end_at: AwareDatetime | None = None
    confirm_external_processing: bool = False


class GroupQuestionOut(BaseModel):
    query: str
    count: int
    cited_answer: int
    no_evidence: int
    similarity_to_representative: float
    last_asked_at: datetime


class QuestionGroupOut(BaseModel):
    kind: Literal["candidate", "singleton"]
    representative: str
    count: int
    distinct_questions: int
    min_pair_similarity: float | None
    members: list[GroupQuestionOut]


class QuestionGroupingResponse(BaseModel):
    window_start: datetime
    window_end: datetime
    grouping_contract: str
    min_similarity: float
    threshold_calibrated: Literal[False]
    embedding_called: bool
    embedding_model: str
    embedding_identity: str
    eligible_attempts: int
    excluded_attempts: int
    distinct_questions: int
    grouped_questions: int
    singleton_questions: int
    singleton_attempts: int
    groups: list[QuestionGroupOut]


class QueryLogRetentionRequest(BaseModel):
    mode: Literal["dry_run", "delete"] = "dry_run"


class QueryLogRetentionResponse(BaseModel):
    mode: Literal["dry_run", "delete"]
    retention_days: int
    batch_limit: int
    matched_count: int
    deleted_count: int
    has_more: bool
    cutoff: datetime

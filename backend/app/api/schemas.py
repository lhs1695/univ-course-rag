from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    Field,
    StrictBool,
    field_validator,
    model_validator,
)

from app.models.course import CourseMemberRole
from app.models.user import UserRole


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class UserOut(BaseModel):
    id: str
    username: str
    role: str
    full_name: str | None = None
    student_number: str | None = None


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)
    role: UserRole
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    student_number: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")

    @field_validator("full_name", "student_number", mode="before")
    @classmethod
    def strip_profile_fields(cls, value):
        return value.strip() if isinstance(value, str) else value


class CourseCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    semester_id: UUID | None = None


class CourseUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    semester_id: UUID | None = None

    @model_validator(mode="after")
    def reject_null_title(self):
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("title cannot be null")
        return self


class CourseCapabilities(BaseModel):
    can_manage_documents: bool = False
    can_manage_members: bool = False
    can_view_insights: bool = False


class CourseOut(BaseModel):
    id: str
    title: str
    semester_id: UUID | None = None
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
    full_name: str | None = None
    student_number: str | None = None
    class_id: UUID | None = None
    class_name: str | None = None


class DocumentUpdateRequest(BaseModel):
    retrieval_enabled: StrictBool


class DocumentOut(BaseModel):
    id: str
    filename: str
    job_status: str
    retrieval_enabled: bool
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
    distinct_student_questions: int
    cited_answer_rate: float | None = None
    no_evidence_rate: float | None
    failure_rate: float | None = None
    rate_denominator: str = "student_attempts"
    sample_limited: bool = False


class InsightsTrendPoint(BaseModel):
    bucket_start: datetime
    cited_answer: int
    no_evidence: int
    failure: int
    unknown_outcome: int


class InsightThemeOut(BaseModel):
    label: str
    source: Literal["exact_normalize"]
    status: Literal["candidate"]
    kind: Literal["no_evidence", "cited_repeat"]
    ask_count: int
    distinct_questions: int
    sort_reason: str
    sort_reason_label: str


class InsightClueOut(BaseModel):
    title: str
    trigger: str
    trigger_label: str
    ask_count: int
    status: Literal["pending_review", "pending_ops"]


class InsightsResponse(BaseModel):
    retention_days: int
    window_start: datetime
    window_end: datetime
    metric_contract: str = "metrics-v1"
    summary: InsightsSummary
    trend: list[InsightsTrendPoint]
    frequent: list[FrequentQuestionOut]
    no_evidence: list[NoEvidenceQuestionOut]
    themes: list[InsightThemeOut] = []
    clues: list[InsightClueOut] = []


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
    intent_code: Literal["concept", "procedure", "example", "compare", "admin_oor", "other_uncertain"] = "other_uncertain"
    intent_status: Literal["candidate"] = "candidate"
    intent_source: str = "rule_v1"


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


class InsightReviewCreate(BaseModel):
    subject_type: Literal["group", "clue", "query_text"]
    subject_key: str = Field(min_length=1, max_length=512)
    intent_code: Literal["concept", "procedure", "example", "compare", "admin_oor", "other_uncertain"] | None = None
    knowledge_point: str | None = Field(default=None, max_length=256)
    review_status: Literal["confirmed", "rejected", "deferred", "split"] = "deferred"
    cause_code: Literal["coverage_gap", "retrieval_citation", "question_wording", "normal_review", "undecidable"] | None = None
    action_code: Literal["update_material", "clarify_in_class", "add_regression", "no_action", "investigate_system"] | None = None
    note: str | None = None


class InsightReviewUpdate(BaseModel):
    intent_code: Literal["concept", "procedure", "example", "compare", "admin_oor", "other_uncertain"] | None = None
    knowledge_point: str | None = Field(default=None, max_length=256)
    review_status: Literal["confirmed", "rejected", "deferred", "split"] | None = None
    cause_code: Literal["coverage_gap", "retrieval_citation", "question_wording", "normal_review", "undecidable"] | None = None
    action_code: Literal["update_material", "clarify_in_class", "add_regression", "no_action", "investigate_system"] | None = None
    note: str | None = None


class InsightReviewOut(BaseModel):
    id: str
    course_id: str
    teacher_id: str
    subject_type: str
    subject_key: str
    intent_code: str | None
    knowledge_point: str | None
    review_status: str
    cause_code: str | None
    action_code: str | None
    note: str | None
    created_at: datetime
    updated_at: datetime


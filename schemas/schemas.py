from pydantic import BaseModel, EmailStr, ConfigDict, Field
from uuid import UUID
from typing import Optional, List
from datetime import datetime

PLAN_CREDITS = {
    "free": 10,
    "starter": 100,
    "pro": 500,
    "business": 2000,
    "enterprise": 99999,
}

PACK_CREDITS = {
    "credits_50": 50,
    "credits_100": 100,
    "credits_250": 250,
    "credits_500": 500,
    "credits_1000": 1000,
}


# ── Users ───────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    verification_otp: int
    name: str
    password: str
    is_verified: bool = False


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    status: str
    user_id: UUID
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    success: bool
    user_id: Optional[UUID] = None
    email: Optional[EmailStr] = None
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    role: Optional[str] = None
    message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class GoogleAuthRequest(BaseModel):
    token: str


class OTPRequest(BaseModel):
    email: EmailStr
    otp: int


class AuthResponse(BaseModel):
    status: str
    user_id: UUID
    email: str
    name: Optional[str] = None
    access_token: Optional[str] = None


# ── Visuals ─────────────────────────────────────────────────────────────────
class Visual_In(BaseModel):
    topic: str
    detail: str
    item: Optional[str] = None  # None = Lecture, "PPT" = presentation
    slides: Optional[list[dict]] = None  # for PPT with manual slides


class SplitSlidesRequest(BaseModel):
    topic: str
    content: str  # raw pasted PPT content


class Visual_Out(BaseModel):
    status: str
    visual_id: Optional[UUID] = None
    path: Optional[str] = None


# ── Payments ────────────────────────────────────────────────────────────────
class CreatePaymentRequest(BaseModel):
    user_id: UUID
    type: str  # "subscription" | "credits"
    item_id: str  # plan name or credit pack id
    amount_usd: float
    description: str


# ── Profile ─────────────────────────────────────────────────────────────────
class ProfileResponse(BaseModel):
    user_id: UUID
    name: str
    email: str
    plan: str
    credits: int
    role: Optional[str] = "student"
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UpdateNameRequest(BaseModel):
    user_id: UUID
    name: str


class ChangePasswordRequest(BaseModel):
    user_id: UUID
    current_password: str
    new_password: str


# ── Class Plans ─────────────────────────────────────────────────────────────
class GeneratePlanRequest(BaseModel):
    user_id: UUID
    class_name: str
    subject: str
    outline: str
    total_lectures: int
    hours_per_lecture: float
    age_min: int
    age_max: int
    education_level: str
    book_name: Optional[str] = ""


class SavePlanRequest(BaseModel):
    user_id: UUID
    plan_id: Optional[UUID] = None
    class_name: str
    subject: str
    outline: str
    total_lectures: int
    hours_per_lecture: float
    age_min: int
    age_max: int
    education_level: str
    books_names: Optional[str] = None
    generated_plan: list


# ── Groups ──────────────────────────────────────────────────────────────────
class CreateGroupRequest(BaseModel):
    created_by: UUID
    name: str
    description: Optional[str] = ""
    privacy: str = "private"
    subject: Optional[str] = None


class AddMemberRequest(BaseModel):
    group_id: UUID
    created_by: UUID
    email: str


class SendMessageRequest(BaseModel):
    group_id: UUID
    sender_id: UUID
    content: str


class ShareContentRequest(BaseModel):
    group_id: UUID
    shared_by: UUID
    content_type: str  # "visualization" | "class_plan"
    content_id: UUID


# ── Quiz ───────────────────────────────────────────────────────────────────
class GenerateQuizRequest(BaseModel):
    topic: str
    content: Optional[str] = None
    difficulty: str = "medium"  # easy, medium, hard
    question_count: int = Field(default=10, ge=1, le=50)
    question_types: Optional[List[str]] = None  # multiple_choice, true_false, short_answer
    source_type: Optional[str] = None  # lecture, class_plan, custom
    source_id: Optional[UUID] = None


class SubmitQuizRequest(BaseModel):
    quiz_id: UUID
    answers: dict  # {question_id: user_answer}


class QuizQuestionOut(BaseModel):
    id: UUID
    question_type: str
    question_text: str
    options: Optional[list] = None
    points: int
    order_index: int

    model_config = ConfigDict(from_attributes=True)


class QuizOut(BaseModel):
    id: UUID
    title: str
    topic: str
    description: Optional[str] = None
    difficulty: str
    question_count: int
    is_published: bool
    created_at: Optional[datetime] = None
    questions: Optional[List[QuizQuestionOut]] = None

    model_config = ConfigDict(from_attributes=True)


class QuizAttemptOut(BaseModel):
    id: UUID
    quiz_id: UUID
    score: Optional[float] = None
    total_points: Optional[int] = None
    earned_points: Optional[int] = None
    completed_at: Optional[datetime] = None
    answers: dict
    corrections: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


# ── Content Summarization ──────────────────────────────────────────────────
class SummarizeRequest(BaseModel):
    title: str
    content: str
    summary_type: str = "standard"  # brief, standard, detailed
    language: str = "english"


class SummaryOut(BaseModel):
    id: UUID
    title: str
    summary: str
    summary_type: str
    key_points: Optional[list] = None
    word_count_original: Optional[int] = None
    word_count_summary: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Research / Google Scholar ──────────────────────────────────────────────
class ScholarSearchRequest(BaseModel):
    query: str
    num_results: int = Field(default=10, ge=1, le=20)


# ── Feedback ───────────────────────────────────────────────────────────────
class FeedbackRequest(BaseModel):
    content_type: str  # visualization, class_plan, quiz
    content_id: UUID
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None


class FeedbackOut(BaseModel):
    id: UUID
    user_id: UUID
    content_type: str
    content_id: UUID
    rating: int
    comment: Optional[str] = None
    created_at: Optional[datetime] = None
    user_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ── Lecture Customization ──────────────────────────────────────────────────
class CustomizeLectureRequest(BaseModel):
    topic: str
    content: str
    customization_type: str  # simplify, detailed, visual_heavy, interactive, age_appropriate
    target_audience: Optional[str] = None  # e.g. "high school", "university", "professional"
    language: Optional[str] = "english"
    additional_instructions: Optional[str] = None


# ── Study Notes ────────────────────────────────────────────────────────────
class CreateStudyNoteRequest(BaseModel):
    title: str
    content: str
    subject: Optional[str] = None
    tags: Optional[List[str]] = None
    group_id: Optional[UUID] = None
    is_shared: bool = False


class StudyNoteOut(BaseModel):
    id: UUID
    title: str
    content: str
    subject: Optional[str] = None
    tags: Optional[list] = None
    is_shared: bool
    group_id: Optional[UUID] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── User Reviews ─────────────────────────────────────────────────────────
class SubmitReviewRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    review_text: Optional[str] = None


class ReviewOut(BaseModel):
    id: UUID
    user_id: UUID
    rating: int
    review_text: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReviewModerationRequest(BaseModel):
    action: str  # "approve" or "archive"


# ── Admin API Service Config ─────────────────────────────────────────────
class APIServiceConfigOut(BaseModel):
    id: UUID
    service_name: str
    display_name: str
    is_active: bool
    category: str
    last_toggled_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ToggleServiceRequest(BaseModel):
    is_active: bool


# ── User Profiles ─────────────────────────────────────────────────────────
class UpdateProfileRequest(BaseModel):
    designation: Optional[str] = None
    bio: Optional[str] = None
    profile_photo: Optional[str] = None
    achievements: Optional[List[dict]] = None
    interests: Optional[List[str]] = None


class UserProfileOut(BaseModel):
    user_id: UUID
    name: str
    email: str
    designation: Optional[str] = None
    bio: Optional[str] = None
    profile_photo: Optional[str] = None
    achievements: Optional[list] = None
    interests: Optional[list] = None
    connection_count: int = 0
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Connections ───────────────────────────────────────────────────────────
class ConnectionRequestSchema(BaseModel):
    receiver_id: UUID


class ConnectionRespondRequest(BaseModel):
    connection_id: UUID
    action: str  # accept or reject


class ConnectionOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    email: str
    designation: Optional[str] = None
    bio: Optional[str] = None
    interests: Optional[list] = None
    status: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Direct Messaging ─────────────────────────────────────────────────────
class SendDirectMessageRequest(BaseModel):
    receiver_id: UUID
    content: str


class DirectMessageOut(BaseModel):
    id: UUID
    sender_id: UUID
    receiver_id: UUID
    sender_name: Optional[str] = None
    content: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ConversationOut(BaseModel):
    user_id: UUID
    name: str
    email: str
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# ── Study Rooms ──────────────────────────────────────────────────────────
class CreateStudyRoomRequest(BaseModel):
    name:        str
    description: Optional[str] = None
    room_type:   str = "text"
    type:        Optional[str] = None    
    persistence: Optional[str] = "temporary"
    is_persistent: Optional[bool] = None
    subject:     Optional[str] = "Other"
    goal:        Optional[str] = None
    group_id:    Optional[str] = None


class StudyRoomOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    room_type: str
    is_persistent: bool
    created_by: UUID
    creator_name: Optional[str] = None
    group_id: Optional[UUID] = None
    is_active: bool
    participant_count: int = 0
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StudyRoomMessageOut(BaseModel):
    id: UUID
    room_id: UUID
    sender_id: UUID
    sender_name: Optional[str] = None
    content: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SendRoomMessageRequest(BaseModel):
    content: str


# ── Research Documents ───────────────────────────────────────────────────
class SaveResearchDocRequest(BaseModel):
    title: str = "Untitled Document"
    content: Optional[str] = None
    template_type: Optional[str] = None
    citation_style: Optional[str] = "apa"
    references: Optional[list] = None
    doc_id: Optional[UUID] = None


class ResearchDocOut(BaseModel):
    id: UUID
    title: str
    content: Optional[str] = None
    template_type: Optional[str] = None
    citation_style: Optional[str] = None
    references: Optional[list] = None
    is_public: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── AI Writing Assistant ─────────────────────────────────────────────────
class AIAssistRequest(BaseModel):
    text: str
    action: str  # improve, expand, simplify, rewrite


# ── Analytics ────────────────────────────────────────────────────────────
class ContentViewRequest(BaseModel):
    content_type: str
    content_id: UUID
    time_spent_seconds: int = 0


# ── Subscription Plans (Admin-managed) ──────────────────────────────────
FEATURE_KEYS = [
    "feature_lectures", "feature_quiz", "feature_summarize", "feature_research",
    "feature_groups", "feature_connections", "feature_messaging",
    "feature_study_rooms", "feature_analytics", "feature_3d_visuals",
    "feature_4d_animations", "feature_ppt", "feature_content_library",
    "feature_collaboration", "feature_api_access", "feature_batch_generation",
    "feature_hd_quality", "feature_priority_queue",
]


class CreatePlanRequest(BaseModel):
    plan_key: str
    name: str
    description: Optional[str] = None
    price_monthly: float = 0
    price_yearly: float = 0
    credits_per_month: int = 0
    is_active: bool = True
    sort_order: int = 0
    is_popular: bool = False
    feature_lectures: bool = True
    feature_quiz: bool = True
    feature_summarize: bool = True
    feature_research: bool = False
    feature_groups: bool = False
    feature_connections: bool = False
    feature_messaging: bool = False
    feature_study_rooms: bool = False
    feature_analytics: bool = False
    feature_3d_visuals: bool = True
    feature_4d_animations: bool = False
    feature_ppt: bool = True
    feature_content_library: bool = True
    feature_collaboration: bool = False
    feature_api_access: bool = False
    feature_batch_generation: bool = False
    feature_hd_quality: bool = False
    feature_priority_queue: bool = False
    max_exports_per_day: int = 1
    rate_limit: str = "10/hour"


class UpdatePlanRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price_monthly: Optional[float] = None
    price_yearly: Optional[float] = None
    credits_per_month: Optional[int] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    is_popular: Optional[bool] = None
    feature_lectures: Optional[bool] = None
    feature_quiz: Optional[bool] = None
    feature_summarize: Optional[bool] = None
    feature_research: Optional[bool] = None
    feature_groups: Optional[bool] = None
    feature_connections: Optional[bool] = None
    feature_messaging: Optional[bool] = None
    feature_study_rooms: Optional[bool] = None
    feature_analytics: Optional[bool] = None
    feature_3d_visuals: Optional[bool] = None
    feature_4d_animations: Optional[bool] = None
    feature_ppt: Optional[bool] = None
    feature_content_library: Optional[bool] = None
    feature_collaboration: Optional[bool] = None
    feature_api_access: Optional[bool] = None
    feature_batch_generation: Optional[bool] = None
    feature_hd_quality: Optional[bool] = None
    feature_priority_queue: Optional[bool] = None
    max_exports_per_day: Optional[int] = None
    rate_limit: Optional[str] = None


class PlanOut(BaseModel):
    id: UUID
    plan_key: str
    name: str
    description: Optional[str] = None
    price_monthly: float
    price_yearly: float
    credits_per_month: int
    is_active: bool
    sort_order: int
    is_popular: bool
    feature_lectures: bool
    feature_quiz: bool
    feature_summarize: bool
    feature_research: bool
    feature_groups: bool
    feature_connections: bool
    feature_messaging: bool
    feature_study_rooms: bool
    feature_analytics: bool
    feature_3d_visuals: bool
    feature_4d_animations: bool
    feature_ppt: bool
    feature_content_library: bool
    feature_collaboration: bool
    feature_api_access: bool
    feature_batch_generation: bool
    feature_hd_quality: bool
    feature_priority_queue: bool
    max_exports_per_day: int
    rate_limit: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class UpdateStatusRequest(BaseModel):
    status: str  # studying | break | done

class UpdateGoalRequest(BaseModel):
    goal: str

class UpdateNotesRequest(BaseModel):
    notes: str
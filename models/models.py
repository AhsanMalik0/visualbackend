import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Text, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(100), default="student", nullable=False)
    plan = Column(String(255), default="free", nullable=False)
    credits = Column(Integer, default=0, nullable=False)
    is_verified = Column(String(255), default="False", nullable=False)
    verification_otp = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    password = Column(String, nullable=True)
    auth_method = Column(String(50), nullable=False, default="email")

    # New fields for production
    stripe_customer_id = Column(String, nullable=True)
    api_key = Column(String, nullable=True, unique=True)
    api_key_created_at = Column(DateTime(timezone=True), nullable=True)
    total_generations = Column(Integer, default=0)
    last_generation_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    visualizations = relationship("Visual", back_populates="user")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    plan = Column(String, nullable=False, default="free")
    status = Column(String, nullable=False, default="active")  # active, cancelled, past_due
    stripe_subscription_id = Column(String, nullable=True)
    stripe_customer_id = Column(String, nullable=True)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="subscription")


class Visual(Base):
    __tablename__ = "visualizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    detail = Column(Text)
    html_code = Column(Text)
    topic = Column(String(255), nullable=True)
    is_favorite = Column(String(255), default="False", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    item = Column(String(255), default="Lecture", nullable=True)

    # New fields
    generation_type = Column(String(50), default="3d_visual")  # 3d_visual, 4d_animation, model_3d
    quality = Column(String(20), default="standard")  # standard, hd
    export_format = Column(String(20), nullable=True)  # glb, gltf, obj, mp4
    export_url = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)

    user = relationship("User", back_populates="visualizations")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String, nullable=False)  # "subscription" | "credits"
    item_id = Column(String, nullable=False)  # plan name or credit pack id
    amount_usd = Column(Float, nullable=False)
    status = Column(String, default="pending")  # pending | confirmed | failed | refunded
    nowpay_id = Column(String, nullable=True, index=True)
    stripe_payment_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class Template(Base):
    __tablename__ = "templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(100), nullable=False)  # education, marketing, gaming, architecture, science
    thumbnail_url = Column(Text, nullable=True)
    html_template = Column(Text, nullable=False)
    parameters = Column(JSON, nullable=True)  # customizable parameters
    is_premium = Column(Boolean, default=False)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class APIUsageLog(Base):
    __tablename__ = "api_usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    endpoint = Column(String, nullable=False)
    method = Column(String(10), nullable=False)
    credits_used = Column(Integer, default=0)
    response_status = Column(Integer)
    generation_type = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ClassPlan(Base):
    __tablename__ = "class_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    class_name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    outline = Column(Text, nullable=False)
    total_lectures = Column(Integer, nullable=False)
    hours_per_lecture = Column(Float, nullable=False)
    age_min = Column(Integer, nullable=False)
    age_max = Column(Integer, nullable=False)
    education_level = Column(String, nullable=False)
    books_names = Column(String, nullable=True)
    generated_plan = Column(JSON, nullable=True)
    visual_id = Column(String, nullable=True)
    visual_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class Group(Base):
    __tablename__ = "groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(150), nullable=False)
    description = Column(Text)
    privacy = Column(String(20), default="private")
    subject = Column(String(150), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    members = relationship("GroupMember", backref="group", cascade="all, delete-orphan")
    messages = relationship("GroupMessage", backref="group", cascade="all, delete-orphan")
    shares = relationship("GroupShare", backref="group", cascade="all, delete-orphan")
    posts = relationship("GroupPost", backref="group", cascade="all, delete-orphan")


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    email = Column(String, ForeignKey("users.email"), nullable=False, index=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())


class GroupMessage(Base):
    __tablename__ = "group_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GroupShare(Base):
    __tablename__ = "group_shares"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True)
    shared_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content_type = Column(String, nullable=False)  # "visualization" | "class_plan"
    content_id = Column(UUID(as_uuid=True), nullable=False)
    title = Column(String, nullable=True)
    url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    topic = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    difficulty = Column(String(50), default="medium")  # easy, medium, hard
    question_count = Column(Integer, default=0)
    source_type = Column(String(50), nullable=True)  # lecture, class_plan, custom
    source_id = Column(UUID(as_uuid=True), nullable=True)
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    questions = relationship("QuizQuestion", backref="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", backref="quiz", cascade="all, delete-orphan")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id"), nullable=False, index=True)
    question_type = Column(String(50), nullable=False)  # multiple_choice, true_false, short_answer
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)  # list of options for multiple_choice
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    points = Column(Integer, default=1)
    order_index = Column(Integer, default=0)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    answers = Column(JSON, nullable=False)  # {question_id: user_answer}
    score = Column(Float, nullable=True)
    total_points = Column(Integer, nullable=True)
    earned_points = Column(Integer, nullable=True)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    content_type = Column(String(50), nullable=False)  # visualization, class_plan, quiz
    content_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ContentSummary(Base):
    __tablename__ = "content_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    original_content = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    summary_type = Column(String(50), default="standard")  # brief, standard, detailed
    key_points = Column(JSON, nullable=True)
    word_count_original = Column(Integer, nullable=True)
    word_count_summary = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class StudyNote(Base):
    __tablename__ = "study_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    subject = Column(String(100), nullable=True)
    tags = Column(JSON, nullable=True)
    is_shared = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UserReview(Base):
    __tablename__ = "user_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1-5
    review_text = Column(Text, nullable=True)
    status = Column(String(20), default="pending")  # pending, approved, archived
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class APIServiceConfig(Base):
    __tablename__ = "api_service_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_name = Column(String(100), nullable=False, unique=True)  # stripe, nowpayments, gemini, kimi
    display_name = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    category = Column(String(50), nullable=False)  # payment, ai, search
    last_toggled_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    last_toggled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    designation = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    profile_photo = Column(Text, nullable=True)
    achievements = Column(JSON, nullable=True)
    interests = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Connection(Base):
    __tablename__ = "connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requester_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    receiver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DirectMessage(Base):
    __tablename__ = "direct_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    receiver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class StudyRoom(Base):
    __tablename__ = "study_rooms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    room_type = Column(String(20), nullable=False, default="text")
    is_persistent = Column(Boolean, default=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    subject = Column(String(100), nullable=True, default="Other")
    goal    = Column(Text, nullable=True)
    notes   = Column(Text, nullable=True)


class StudyRoomParticipant(Base):
    __tablename__ = "study_room_participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("study_rooms.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(20), nullable=True, default="studying")  # studying | break | done
    goal   = Column(Text, nullable=True)


class StudyRoomMessage(Base):
    __tablename__ = "study_room_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("study_rooms.id"), nullable=False, index=True)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ResearchDocument(Base):
    __tablename__ = "research_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False, default="Untitled Document")
    content = Column(Text, nullable=True)
    template_type = Column(String(50), nullable=True)
    citation_style = Column(String(20), nullable=True, default="apa")
    references = Column(JSON, nullable=True)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ContentView(Base):
    __tablename__ = "content_views"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_type = Column(String(50), nullable=False)
    content_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    viewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    time_spent_seconds = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_key = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price_monthly = Column(Float, default=0)
    price_yearly = Column(Float, default=0)
    credits_per_month = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    is_popular = Column(Boolean, default=False)

    # Feature flags
    feature_lectures = Column(Boolean, default=True)
    feature_quiz = Column(Boolean, default=True)
    feature_summarize = Column(Boolean, default=True)
    feature_research = Column(Boolean, default=False)
    feature_groups = Column(Boolean, default=False)
    feature_connections = Column(Boolean, default=False)
    feature_messaging = Column(Boolean, default=False)
    feature_study_rooms = Column(Boolean, default=False)
    feature_analytics = Column(Boolean, default=False)
    feature_3d_visuals = Column(Boolean, default=True)
    feature_4d_animations = Column(Boolean, default=False)
    feature_ppt = Column(Boolean, default=True)
    feature_content_library = Column(Boolean, default=True)
    feature_collaboration = Column(Boolean, default=False)
    feature_api_access = Column(Boolean, default=False)
    feature_batch_generation = Column(Boolean, default=False)
    feature_hd_quality = Column(Boolean, default=False)
    feature_priority_queue = Column(Boolean, default=False)

    max_exports_per_day = Column(Integer, default=1)
    rate_limit = Column(String(50), default="10/hour")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
# =======
class GroupPost(Base):
    __tablename__ = "group_posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content_type = Column(String(50), nullable=False)  # lecture, quiz, summary, research, visual, text
    content_id = Column(UUID(as_uuid=True), nullable=True)
    text = Column(Text, nullable=True)
    title = Column(String(500), nullable=True)
    is_restricted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    likes = relationship("GroupPostLike", backref="post", cascade="all, delete-orphan")
    comments = relationship("GroupPostComment", backref="post", cascade="all, delete-orphan")


class GroupPostLike(Base):
    __tablename__ = "group_post_likes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("group_posts.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GroupPostComment(Base):
    __tablename__ = "group_post_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("group_posts.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

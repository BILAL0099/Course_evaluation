"""
Pydantic models for the AI Course Reviewer.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ReviewStatus(str, Enum):
    """Status of a course review."""
    PENDING = "pending"
    EXTRACTING = "extracting"
    PARSING = "parsing"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"


class IssueType(str, Enum):
    """Type of issue found during review."""
    NAVIGATION = "navigation"
    BUTTON = "button"
    MEDIA = "media"
    TIMER = "timer"
    SPELLING = "spelling"
    GRAMMAR = "grammar"
    SCORM_ERROR = "scorm_error"
    STUCK = "stuck"
    ACCESSIBILITY = "accessibility"
    # AI-detected issues
    CLARITY = "clarity"           # Content is unclear or confusing
    ACCURACY = "accuracy"         # Potential factual issues
    TONE = "tone"                 # Inappropriate tone
    CONSISTENCY = "consistency"   # Inconsistent terminology/style
    READABILITY = "readability"   # Difficult to read
    STRUCTURE = "structure"       # Poor content structure
    ENGAGEMENT = "engagement"     # Low engagement quality


class IssueSeverity(str, Enum):
    """Severity level of an issue."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Issue(BaseModel):
    """An issue found during review."""
    issue_type: IssueType
    severity: IssueSeverity
    message: str
    slide_number: int
    element_selector: Optional[str] = None
    details: Optional[dict] = None
    screenshot: Optional[str] = None


class SlideResult(BaseModel):
    """Results for a single slide."""
    slide_number: int
    title: Optional[str] = None
    url: Optional[str] = None
    screenshot_path: Optional[str] = None
    text_content: str = ""
    issues: list[Issue] = Field(default_factory=list)
    navigation_method: Optional[str] = None  # "button", "next", "skip"
    scorm_calls: list[dict] = Field(default_factory=list)
    load_time_ms: Optional[float] = None
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)


class SCORMManifest(BaseModel):
    """Parsed SCORM manifest information."""
    identifier: str
    title: str
    version: Optional[str] = None
    launch_file: str
    resources: list[dict] = Field(default_factory=list)
    organizations: list[dict] = Field(default_factory=list)
    scorm_version: str = "1.2"  # or "2004"


class ReviewRequest(BaseModel):
    """Request to start a review."""
    review_id: str


class ReviewProgress(BaseModel):
    """Progress information for an ongoing review."""
    review_id: str
    status: ReviewStatus
    current_slide: int = 0
    total_slides: int = 0
    issues_found: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ReviewReport(BaseModel):
    """Complete review report."""
    review_id: str
    course_title: str
    scorm_version: str
    status: ReviewStatus
    total_slides: int
    total_issues: int
    issues_by_type: dict[str, int] = Field(default_factory=dict)
    issues_by_severity: dict[str, int] = Field(default_factory=dict)
    slides: list[SlideResult] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    summary: Optional[str] = None


class UploadResponse(BaseModel):
    """Response after uploading a SCORM package."""
    review_id: str
    filename: str
    file_size: int
    message: str


class StatusResponse(BaseModel):
    """Response for status check."""
    review_id: str
    status: ReviewStatus
    progress: ReviewProgress


class FunctionalCheckResult(BaseModel):
    """Result of functional checks on a slide."""
    navigation_working: bool = True
    buttons_found: list[str] = Field(default_factory=list)
    buttons_working: list[str] = Field(default_factory=list)
    media_elements: list[dict] = Field(default_factory=list)
    media_errors: list[str] = Field(default_factory=list)
    timers_found: list[dict] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)


class ContentCheckResult(BaseModel):
    """Result of content checks on a slide."""
    text_content: str = ""
    word_count: int = 0
    spelling_errors: list[dict] = Field(default_factory=list)
    grammar_errors: list[dict] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)


class AIAnalysisResult(BaseModel):
    """Result from AI agent analysis."""
    agent_name: str
    analysis_type: str
    score: Optional[float] = None  # 0-100 score if applicable
    summary: str = ""
    issues: list[Issue] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    raw_response: Optional[str] = None
    tokens_used: int = 0
    

class SlideAIAnalysis(BaseModel):
    """Complete AI analysis for a slide."""
    slide_number: int
    clarity_analysis: Optional[AIAnalysisResult] = None
    accuracy_analysis: Optional[AIAnalysisResult] = None
    tone_analysis: Optional[AIAnalysisResult] = None
    accessibility_analysis: Optional[AIAnalysisResult] = None
    overall_score: Optional[float] = None
    overall_summary: str = ""
    all_issues: list[Issue] = Field(default_factory=list)
    all_suggestions: list[str] = Field(default_factory=list)

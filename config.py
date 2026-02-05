"""
Configuration settings for the AI Course Reviewer.
"""

from pathlib import Path
from typing import Optional, Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # API Settings
    app_name: str = "AI Course Reviewer"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # File Storage
    upload_dir: Path = Path("./uploads")
    extract_dir: Path = Path("./extracted")
    reports_dir: Path = Path("./reports")
    screenshots_dir: Path = Path("./screenshots")
    
    # Browser Settings
    headless: bool = True
    browser_timeout: int = 30000  # milliseconds
    screenshot_quality: int = 80
    
    # Review Settings
    max_slides: int = 500
    slide_wait_time: float = 2.0  # seconds to wait between slides
    stuck_timeout: float = 10.0  # seconds before considering navigation stuck
    skip_key_combo: str = "Control+Shift+S"
    
    # Content Check Settings
    min_word_length: int = 2
    ignore_words: list[str] = ["lorem", "ipsum", "scorm", "lms"]
    
    # LLM Settings
    llm_provider: Literal["openai", "anthropic"] = "openai"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-haiku-20240307"
    
    # AI Agent Settings
    enable_ai_agents: bool = True
    ai_content_analysis: bool = True  # Analyze content quality
    ai_clarity_check: bool = True     # Check clarity and readability
    ai_accuracy_check: bool = True    # Check factual consistency
    ai_tone_check: bool = True        # Check tone appropriateness
    ai_accessibility_check: bool = True  # Check accessibility
    ai_max_tokens: int = 2000
    ai_temperature: float = 0.1
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Create directories if they don't exist
for directory in [settings.upload_dir, settings.extract_dir, 
                  settings.reports_dir, settings.screenshots_dir]:
    directory.mkdir(parents=True, exist_ok=True)

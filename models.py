"""
KZBIT Automation - Data Models

Pydantic models for strict validation and type safety.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum


class PopupStatus(str, Enum):
    """Classification of popup message."""
    SUCCESS = "success"
    ERROR = "error"
    UNKNOWN = "unknown"


class Account(BaseModel):
    """Account credentials model."""
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=1)
    
    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v.strip()


class CodeCommand(BaseModel):
    """
    Validated command from Telegram.
    
    Format: /code <clicks>f <code>
    Example: /code 2f j2f4ffjb
    """
    clicks: int = Field(..., ge=1, le=50, description="Number of submissions (stripped of 'f' during parsing)")
    code: str = Field(..., min_length=4, max_length=32, description="BTC order code")
    
    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        # Remove any whitespace
        return v.strip()


class SubmitResult(BaseModel):
    """Result of a single code submission."""
    success: bool
    popup_text: str
    status: PopupStatus
    duration_ms: int


class AccountResult(BaseModel):
    """Result of processing one account."""
    email: str
    success: bool
    total_submits: int
    successful_submits: int
    failed_submits: int
    duration_seconds: float
    results: list[SubmitResult] = Field(default_factory=list)
    error: Optional[str] = None


class WorkflowResult(BaseModel):
    """Final result of the entire workflow."""
    total_accounts: int
    processed_accounts: int
    successful_accounts: int
    total_duration_seconds: float
    timed_out: bool
    account_results: list[AccountResult] = Field(default_factory=list)

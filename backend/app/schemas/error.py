from typing import Any, Optional
from pydantic import BaseModel, Field

class ErrorDetail(BaseModel):
    code: str = Field(..., description="Stable application error code")
    message: str = Field(..., description="Safe public error message")
    details: Optional[Any] = Field(default=None, description="Optional detailed error context")

class ErrorResponse(BaseModel):
    error: ErrorDetail

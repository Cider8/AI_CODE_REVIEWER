from datetime import datetime
from typing import List, Optional
from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field

from app.schemas.base import CamelCaseModel

class bug(CamelCaseModel):
    line_number: Optional[int] = None
    description: str
    severity: List["low", "medium", "high", "critical"] 
    suggestion: str
    # Define severity as a list of allowed values
    
class securityIssue(CamelCaseModel):
    line_number: int
    type: str
    description: str
    fix: str
    
class Performance(CamelCaseModel):
    description: str
    suggestion: str
    impact: List["low", "medium", "high"]  # Define impact as a list of allowed values
    
class Complexity(CamelCaseModel):
    time_complexity: str
    space_complexity: str
    
class review(Document):
    user_id: Indexed(PydanticObjectId)  # Reference to the user who created the review
    
    #input
    title: str = "Untitled Review"
    original_code: str
    language: str
    
    #AI analysis results
    summary: Optional[str] = None
    overall_score: Optional[int] = Field(default=None, ge=0, le=100)  # Score between 0 and 100
    
    bugs: Optional[List[bug]] = Field(default_factory=list)
    security_issues: Optional[List[securityIssue]] = Field(default_factory = list)
    performance_issues: Optional[List[Performance]] = Field(default_factory = list)
    improvements: Optional[List[str]] = Field(default_factory = list)
    refactored_code: Optional[list[str]] = Field(default_factory = list)
    
    complexity: Optional[List[Complexity]] = Field(default_factory = list)
    tags: List[str] = Field(default_factory = list)
    
    created_at: datetime = Field(default_factory = datetime.utcnow) 
    
    class Settings:
        name: "review"
    
    
    

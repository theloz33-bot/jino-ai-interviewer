import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

# Pydantic 모델로 정의
class Settings(BaseModel):
    max_questions: int = 5
    difficulty: str = "medium"

class State(BaseModel):
    phase: str = "interview"
    current_q_index: int = 0
    followup_used_for_current_q: bool = False
    completed: bool = False

class InterviewerOutput(BaseModel):
    type: str
    prompt: Dict[str, str] # {ko:..., vi:...}
    q_index: int
    category: str

class EvaluationOutput(BaseModel):
    report_markdown: Dict[str, str] # {ko:..., vi:...}

class QAItem(BaseModel):
    q_index: int
    category: str
    question: Dict[str, str]
    answer: str = ""
    followup: Optional[Dict[str, Any]] = None

class InterviewSession(BaseModel):
    session_id: str
    user_id: str
    settings: Settings = Field(default_factory=Settings)
    state: State = Field(default_factory=State)
    qa_log: List[Dict[str, Any]] = Field(default_factory=list)

class OrchestratorResponse(BaseModel):
    session: InterviewSession
    output: Any 

import uuid
from typing import Dict, Any, List
from utils.schemas import InterviewSession, InterviewerOutput, EvaluationOutput

class SessionManager:
    """
    단순한 메모리 기반 세션 관리 (실제 서비스에서는 DB/Redis 권장)
    """
    def __init__(self):
        self.sessions: Dict[str, InterviewSession] = {}

    def create_new_session(self, user_id: str, role_context: Dict[str, Any] = None) -> InterviewSession:
        session_id = str(uuid.uuid4())
        
        # 기본 설정 (진오님 설계 반영)
        default_role = {
            "industry": "태양광 인버터 유통",
            "job": "기술영업",
            "interview_scope": ["기본소양", "업무지식", "입사 후 포부"],
            "ui_languages": ["ko", "vi"]
        }
        
        default_settings = {
            "max_questions": 9,
            "allow_followup_once_per_question": True,
            "scoring_enabled": True,
            "weights": {
                "basic_competency": 0.35,
                "job_knowledge": 0.45,
                "aspiration": 0.2
            }
        }
        
        new_session = InterviewSession(
            session_id=session_id,
            role_context=role_context if role_context else default_role,
            settings=default_settings,
            state={
                "phase": "interview",
                "current_q_index": 1,
                "followup_used_for_current_q": False,
                "completed": False
            },
            qa_log=[]
        )
        
        self.sessions[session_id] = new_session
        return new_session

    def get_session(self, session_id: str) -> InterviewSession:
        return self.sessions.get(session_id)

    def update_session(self, session_id: str, new_state: InterviewSession):
        self.sessions[session_id] = new_state

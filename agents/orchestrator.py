import uuid
from typing import Dict, Any, List, Optional
from utils.schemas import InterviewSession, InterviewerOutput, EvaluationOutput, OrchestratorResponse, QAItem
from agents.interviewer import InterviewerAgent
from agents.evaluator import EvaluatorAgent

class Orchestrator:
    def __init__(self, session_manager, interviewer_agent: InterviewerAgent, evaluator_agent: EvaluatorAgent):
        self.session_manager = session_manager
        self.interviewer = interviewer_agent
        self.evaluator = evaluator_agent

    def process_message(self, session_id: str, user_message: str) -> Optional[OrchestratorResponse]:
        # 세션 조회
        session = self.session_manager.get_session(session_id)
        if not session:
            return None

        # 1. 초기 상태: 질문이 하나도 없을 때 -> 첫 질문 생성
        if not session.qa_log:
            output = self.interviewer.generate_question(session, is_followup=False)
            
            # QA 로그에 첫 질문 추가 (dict 형태로)
            new_qa = {
                "q_index": output.q_index,
                "category": output.category,
                "question": output.prompt, 
                "answer": "",
                "followup": None
            }
            session.qa_log.append(new_qa)
            
            # 상태 업데이트
            session.state.current_q_index = output.q_index
            self.session_manager.save_session(session)
            
            return OrchestratorResponse(session=session, output=output)

        # 2. 사용자 답변 처리 (이미 질문이 나간 상태)
        last_qa = session.qa_log[-1]
        
        # (A) 꼬리질문 답변 대기 중이었나?
        if last_qa.get("followup") and last_qa["followup"].get("asked") and not last_qa["followup"].get("answer"):
             last_qa["followup"]["answer"] = user_message
             # 꼬리질문 완료 -> 다음 질문으로 넘어갈 준비
             session.state.followup_used_for_current_q = False 
             session.state.current_q_index += 1
        
        # (B) 본 질문 답변이었나?
        else:
             last_qa["answer"] = user_message
             
             # 답변 모호성 체크 (간단히 길이로: 10자 미만이면 모호)
             is_ambiguous = len(user_message) < 10 and len(user_message) > 0
             
             need_followup = False
             # 아직 꼬리질문 안 했고, 답변이 모호하면 -> 꼬리질문 결정
             if is_ambiguous and not session.state.followup_used_for_current_q:
                 need_followup = True
                 session.state.followup_used_for_current_q = True
             else:
                 # 꼬리질문 안 함 -> 다음 질문으로
                 session.state.current_q_index += 1
                 session.state.followup_used_for_current_q = False

        # 3. 면접 종료 체크
        if session.state.current_q_index > session.settings.max_questions:
            # 마지막 질문에 대한 답변이었고, 꼬리질문 예정이 없으면 -> 평가
            if not session.state.followup_used_for_current_q:
                session.state.phase = "evaluation"
                return self._run_evaluation(session)

        # 4. 다음 질문 생성 (Interviewer 호출)
        # 꼬리질문 필요하면 is_followup=True
        is_followup_needed = session.state.followup_used_for_current_q
        
        output = self.interviewer.generate_question(
            session_data=session,
            is_followup=is_followup_needed
        )
        
        # 5. QA 로그 업데이트
        if is_followup_needed:
            # 꼬리질문 정보 추가 (기존 last_qa에 추가)
            if session.qa_log:
                session.qa_log[-1]["followup"] = {
                    "question": output.prompt,
                    "answer": "",
                    "asked": True
                }
        else:
            # 새 질문 추가 (평가 단계가 아니면)
            if session.state.phase != "evaluation":
                new_qa = {
                    "q_index": output.q_index,
                    "category": output.category,
                    "question": output.prompt,
                    "answer": "",
                    "followup": None
                }
                session.qa_log.append(new_qa)
            
        # 세션 저장
        self.session_manager.save_session(session)

        return OrchestratorResponse(session=session, output=output)

    def _run_evaluation(self, session: InterviewSession) -> OrchestratorResponse:
        output = self.evaluator.evaluate_interview(session)
        session.state.phase = "done"
        session.state.completed = True
        self.session_manager.save_session(session)
        return OrchestratorResponse(session=session, output=output)

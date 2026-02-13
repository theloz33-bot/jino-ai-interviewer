import streamlit as st
import os
import json
import uuid
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

# ==========================================
# 1. Schemas & Config
# ==========================================
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
    prompt: Dict[str, str]
    q_index: int
    category: str

class EvaluationOutput(BaseModel):
    report_markdown: Dict[str, str]

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

# ==========================================
# 2. Prompts
# ==========================================
INTERVIEWER_PROMPT_TEMPLATE = """
당신은 태양광 인버터 기술영업 직무 면접관입니다.
지원자는 한국인이며, 베트남 시장 진출을 목표로 하는 회사의 영업 담당자 후보입니다.
현재 면접 진행 상황은 아래와 같습니다.

[면접 설정]
- 총 질문 수: {max_questions}
- 현재 질문 순서: {current_q_index}번째 질문 (이제 생성해야 함)

[이전 대화 기록]
{qa_history}

[마지막 답변]
{last_answer}

[지시사항]
1. 꼬리질문 요청(Follow-up Request)이 "YES"라면, 마지막 답변에 대해 구체적으로 파고드는 꼬리질문을 하세요.
2. "NO"라면, 다음 주제로 넘어가서 새로운 질문을 하세요.
3. 질문은 반드시 **한국어(ko)**와 **베트남어(vi)** 두 가지로 제공해야 합니다.
4. 질문의 의도(Category)를 명시하세요.
5. 출력은 반드시 **JSON 포맷**이어야 합니다.

[JSON 출력 예시]
{{
  "type": "question",  // 또는 "followup"
  "q_index": {current_q_index},
  "category": "직무 적합성",
  "prompt": {{
    "ko": "베트남 시장에서 우리 회사의 인버터가 경쟁사 대비 어떤 강점을 가질 수 있다고 생각하시나요?",
    "vi": "Theo bạn, biến tần của công ty chúng tôi có những điểm mạnh gì so với đối thủ cạnh tranh tại thị trường Việt Nam?"
  }}
}}

Follow-up Request: {followup_request}
JSON Output:
"""

EVALUATOR_PROMPT_TEMPLATE = """
당신은 면접 평가관입니다. 아래 면접 기록을 바탕으로 지원자를 평가해주세요.

[면접 기록]
{qa_history}

[평가 기준]
1. 직무 이해도 (태양광 인버터, 기술영업)
2. 문제 해결 능력
3. 의사소통 능력 (논리성)
4. 태도 및 열정

[출력 형식]
반드시 **JSON 포맷**으로 출력하세요.
{{
  "report_markdown": {{
    "ko": "# 면접 평가 리포트\\n\\n## 1. 총평\\n...\\n\\n## 2. 항목별 점수\\n- 직무 이해도: 80/100\\n...",
    "vi": "..."
  }}
}}

JSON Output:
"""

# ==========================================
# 3. Agents
# ==========================================
class InterviewerAgent:
    def __init__(self):
        # API Key 직접 주입 (사용자 제공)
        api_key = "AIzaSyDwZsm-JRXLdwCocXGVVdKRfld5m5dC-TQ"
        if not os.environ.get("GOOGLE_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = api_key

        self.llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.7)
        self.prompt_template = PromptTemplate(
            input_variables=["current_q_index", "max_questions", "qa_history", "last_answer", "followup_request"],
            template=INTERVIEWER_PROMPT_TEMPLATE
        )

    def generate_question(self, session_data, is_followup: bool = False) -> InterviewerOutput:
        state = session_data.state
        qa_log = session_data.qa_log
        settings = session_data.settings

        history_text = ""
        for item in qa_log:
            q_idx = item.get("q_index") if isinstance(item, dict) else item.q_index
            question = item.get("question") if isinstance(item, dict) else item.question
            answer = item.get("answer", "") if isinstance(item, dict) else item.answer
            history_text += f"Q{q_idx}: {question['ko']}\nA: {answer}\n"
            
            followup = item.get("followup") if isinstance(item, dict) else getattr(item, "followup", None)
            if followup and followup.get("asked"):
                history_text += f"  (Follow-up Q): {followup['question']['ko']}\n  (Follow-up A): {followup.get('answer', '')}\n"

        last_answer = ""
        if qa_log:
             last_qa = qa_log[-1]
             l_answer = last_qa.get("answer", "") if isinstance(last_qa, dict) else last_qa.answer
             l_followup = last_qa.get("followup") if isinstance(last_qa, dict) else getattr(last_qa, "followup", None)
             
             if is_followup: 
                 last_answer = l_answer
             elif l_followup and l_followup.get("answer"):
                 last_answer = l_followup["answer"]
             else:
                 last_answer = l_answer

        final_prompt = self.prompt_template.format(
            current_q_index=state.current_q_index,
            max_questions=settings.max_questions,
            qa_history=history_text,
            last_answer=last_answer,
            followup_request="YES" if is_followup else "NO"
        )
        
        try:
            response = self.llm.invoke(final_prompt)
            content = response.content
            cleaned_content = content.strip()
            if cleaned_content.startswith("```"):
                lines = cleaned_content.splitlines()
                if lines[0].strip().startswith("```"): lines = lines[1:]
                if lines[-1].strip().startswith("```"): lines = lines[:-1]
                cleaned_content = "\n".join(lines)
            data = json.loads(cleaned_content)
            return InterviewerOutput(
                type=data.get("type", "question"),
                prompt=data.get("prompt", {"ko": "질문 생성 오류", "vi": "Lỗi tạo câu hỏi"}),
                q_index=data.get("q_index", state.current_q_index),
                category=data.get("category", "General")
            )
        except Exception as e:
            return InterviewerOutput(
                type="error",
                prompt={"ko": "오류가 발생했습니다.", "vi": "Error"},
                q_index=state.current_q_index,
                category="Error"
            )

class EvaluatorAgent:
    def __init__(self):
        # API Key 직접 주입
        api_key = "AIzaSyDwZsm-JRXLdwCocXGVVdKRfld5m5dC-TQ"
        if not os.environ.get("GOOGLE_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = api_key

        self.llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.7)
        self.prompt_template = PromptTemplate(
            input_variables=["qa_history"],
            template=EVALUATOR_PROMPT_TEMPLATE
        )

    def evaluate_interview(self, session_data) -> EvaluationOutput:
        qa_log = session_data.qa_log
        history_text = ""
        for item in qa_log:
            q_idx = item.get("q_index") if isinstance(item, dict) else item.q_index
            question = item.get("question") if isinstance(item, dict) else item.question
            answer = item.get("answer", "") if isinstance(item, dict) else item.answer
            history_text += f"Q{q_idx}: {question['ko']}\nA: {answer}\n"
            
            followup = item.get("followup") if isinstance(item, dict) else getattr(item, "followup", None)
            if followup and followup.get("asked"):
                history_text += f"  (Follow-up Q): {followup['question']['ko']}\n  (Follow-up A): {followup.get('answer', '')}\n"
        
        final_prompt = self.prompt_template.format(qa_history=history_text)
        
        try:
            response = self.llm.invoke(final_prompt)
            content = response.content
            cleaned_content = content.strip()
            if cleaned_content.startswith("```"):
                lines = cleaned_content.splitlines()
                if lines[0].strip().startswith("```"): lines = lines[1:]
                if lines[-1].strip().startswith("```"): lines = lines[:-1]
                cleaned_content = "\n".join(lines)
            data = json.loads(cleaned_content)
            return EvaluationOutput(
                report_markdown=data.get("report_markdown", {"ko": "평가 실패", "vi": "Fail"})
            )
        except Exception:
            return EvaluationOutput(report_markdown={"ko": "오류 발생", "vi": "Error"})

# ==========================================
# 4. Session Manager
# ==========================================
class SessionManager:
    def __init__(self):
        if "sessions" not in st.session_state:
            st.session_state.sessions = {}
        self.sessions = st.session_state.sessions

    def create_new_session(self, user_id: str) -> InterviewSession:
        session_id = str(uuid.uuid4())
        new_session = InterviewSession(session_id=session_id, user_id=user_id)
        self.sessions[session_id] = new_session
        return new_session

    def get_session(self, session_id: str) -> Optional[InterviewSession]:
        return self.sessions.get(session_id)

    def save_session(self, session: InterviewSession):
        self.sessions[session.session_id] = session

# ==========================================
# 5. Orchestrator
# ==========================================
class Orchestrator:
    def __init__(self, session_manager, interviewer_agent: InterviewerAgent, evaluator_agent: EvaluatorAgent):
        self.session_manager = session_manager
        self.interviewer = interviewer_agent
        self.evaluator = evaluator_agent

    def process_message(self, session_id: str, user_message: str) -> Optional[OrchestratorResponse]:
        session = self.session_manager.get_session(session_id)
        if not session: return None

        # 1. Start
        if user_message == "" and not session.qa_log:
            output = self.interviewer.generate_question(session, is_followup=False)
            new_qa = {"q_index": output.q_index, "category": output.category, "question": output.prompt, "answer": "", "followup": None}
            session.qa_log.append(new_qa)
            session.state.current_q_index = output.q_index
            self.session_manager.save_session(session)
            return OrchestratorResponse(session=session, output=output)

        # 2. Answer
        last_qa = session.qa_log[-1]
        if last_qa.get("followup") and last_qa["followup"].get("asked") and not last_qa["followup"].get("answer"):
             last_qa["followup"]["answer"] = user_message
             session.state.followup_used_for_current_q = False 
             session.state.current_q_index += 1
        else:
             last_qa["answer"] = user_message
             is_ambiguous = len(user_message) < 10 and len(user_message) > 0
             need_followup = False
             if is_ambiguous and not session.state.followup_used_for_current_q:
                 need_followup = True
                 session.state.followup_used_for_current_q = True
             else:
                 session.state.current_q_index += 1
                 session.state.followup_used_for_current_q = False

        # 3. End
        if session.state.current_q_index > session.settings.max_questions:
            if not session.state.followup_used_for_current_q:
                session.state.phase = "evaluation"
                return self._run_evaluation(session)

        # 4. Next Question
        is_followup_needed = session.state.followup_used_for_current_q
        output = self.interviewer.generate_question(session_data=session, is_followup=is_followup_needed)
        
        if is_followup_needed:
            if session.qa_log:
                session.qa_log[-1]["followup"] = {"question": output.prompt, "answer": "", "asked": True}
        else:
            if session.state.phase != "evaluation":
                new_qa = {"q_index": output.q_index, "category": output.category, "question": output.prompt, "answer": "", "followup": None}
                session.qa_log.append(new_qa)
            
        self.session_manager.save_session(session)
        return OrchestratorResponse(session=session, output=output)

    def _run_evaluation(self, session: InterviewSession) -> OrchestratorResponse:
        output = self.evaluator.evaluate_interview(session)
        session.state.phase = "done"
        session.state.completed = True
        self.session_manager.save_session(session)
        return OrchestratorResponse(session=session, output=output)

# ==========================================
# 6. Streamlit App UI
# ==========================================
load_dotenv()
st.set_page_config(page_title="AI 면접관", layout="wide")

def init_session():
    if "session_manager" not in st.session_state:
        st.session_state.session_manager = SessionManager()
        st.session_state.interviewer = InterviewerAgent()
        st.session_state.evaluator = EvaluatorAgent()
        st.session_state.orchestrator = Orchestrator(
            st.session_state.session_manager,
            st.session_state.interviewer,
            st.session_state.evaluator
        )
    if "messages" not in st.session_state:
        st.session_state.messages = []

init_session()

st.title("☀️ 태양광 인버터 기술영업 - AI 면접")

with st.sidebar:
    if st.button("🔄 초기화"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

if "current_session_id" not in st.session_state:
    st.info("👇 면접을 시작하려면 아래 입력창에 '시작'을 입력하고 엔터를 누르세요.")
    start_input = st.text_input("입력:", value="", key="start_input")
    if start_input:
        with st.spinner("면접관 준비 중..."):
            new_session = st.session_state.session_manager.create_new_session("user1")
            st.session_state.current_session_id = new_session.session_id
            st.session_state.messages = []
            response = st.session_state.orchestrator.process_message(new_session.session_id, "")
            if response:
                output = response.output
                bot_msg = f"**[Q{output.q_index}] {output.prompt['ko']}**\n\n_{output.prompt['vi']}_"
                st.session_state.messages.append({"role": "assistant", "content": bot_msg})
        st.rerun()
else:
    for msg in st.session_state.messages:
        role = "🤖 면접관" if msg["role"] == "assistant" else "👤 지원자"
        st.markdown(f"**{role}:**")
        st.markdown(msg["content"])
        st.markdown("---")

    user_input = st.text_input("답변을 입력하세요:", key="user_answer_input")
    if user_input:
        if not st.session_state.messages or st.session_state.messages[-1]["content"] != user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.spinner("생각 중..."):
                response = st.session_state.orchestrator.process_message(
                    st.session_state.current_session_id, 
                    user_input
                )
            if response:
                output = response.output
                if output.type in ["question", "followup"]:
                    bot_msg = f"**[Q{output.q_index}] {output.prompt['ko']}**\n\n_{output.prompt['vi']}_"
                    st.session_state.messages.append({"role": "assistant", "content": bot_msg})
                elif hasattr(output, "report_markdown"):
                    st.success("면접 종료!")
                    report = output.report_markdown["ko"]
                    st.session_state.messages.append({"role": "assistant", "content": report})
            st.rerun()

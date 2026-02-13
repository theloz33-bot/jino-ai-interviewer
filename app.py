import streamlit as st
import os
import sys

# 경로 문제 해결 (Streamlit Cloud에서 utils, agents 폴더 인식)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from utils.state_manager import SessionManager
from agents.interviewer import InterviewerAgent
from agents.evaluator import EvaluatorAgent
from agents.orchestrator import Orchestrator

# 환경 변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(page_title="AI 면접관", layout="wide")

# 세션 초기화
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

# 사이드바
with st.sidebar:
    if st.button("🔄 초기화"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# 1. 시작 전 상태
if "current_session_id" not in st.session_state:
    st.info("👇 면접을 시작하려면 아래 입력창에 '시작'을 입력하고 엔터를 누르세요.")
    
    start_input = st.text_input("입력:", value="", key="start_input")
    
    if start_input:
        with st.spinner("면접관 준비 중..."):
            new_session = st.session_state.session_manager.create_new_session("user1")
            st.session_state.current_session_id = new_session.session_id
            st.session_state.messages = []
            
            # 첫 질문 생성
            response = st.session_state.orchestrator.process_message(new_session.session_id, "")
            
            if response:
                output = response.output
                bot_msg = f"**[Q{output.q_index}] {output.prompt['ko']}**\n\n_{output.prompt['vi']}_"
                st.session_state.messages.append({"role": "assistant", "content": bot_msg})
        st.rerun()

# 2. 면접 진행 중
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

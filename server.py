from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import uvicorn
from contextlib import asynccontextmanager

from utils.state_manager import SessionManager
from agents.interviewer import InterviewerAgent
from agents.evaluator import EvaluatorAgent
from agents.orchestrator import Orchestrator

# 환경 변수 로드
load_dotenv()

# 전역 변수로 관리
session_manager = None
interviewer = None
evaluator = None
orchestrator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 초기화
    global session_manager, interviewer, evaluator, orchestrator
    print("Initializing AI Agents...")  # 이모지 제거 (인코딩 문제 방지)
    session_manager = SessionManager()
    interviewer = InterviewerAgent()
    evaluator = EvaluatorAgent()
    orchestrator = Orchestrator(session_manager, interviewer, evaluator)
    print("AI Agents Ready!") # 이모지 제거
    yield
    # 종료 시 정리 (필요하면)

app = FastAPI(lifespan=lifespan)

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    global orchestrator, session_manager
    
    try:
        current_session_id = request.session_id
        user_msg = request.message
        
        # 1. 새 세션 시작 (세션ID 없거나 'start' 입력 시)
        if not current_session_id or user_msg.lower() in ["start", "시작"]:
            new_session = session_manager.create_new_session("user1")
            current_session_id = new_session.session_id
            
            # 첫 질문 생성 (빈 문자열 입력으로 트리거)
            response = orchestrator.process_message(current_session_id, "")
            
            if response:
                output = response.output
                return {
                    "session_id": current_session_id,
                    "type": "question",
                    "ko": f"[Q{output.q_index}] {output.prompt['ko']}",
                    "vi": output.prompt['vi']
                }
            else:
                return {"error": "Failed to start session"}

        # 2. 기존 세션 진행
        response = orchestrator.process_message(current_session_id, user_msg)
        
        if not response:
             return {"session_id": current_session_id, "type": "wait", "ko": "...", "vi": ""}

        output = response.output
        
        # 질문/꼬리질문
        if output.type in ["question", "followup"]:
            return {
                "session_id": current_session_id,
                "type": "question",
                "ko": f"[Q{output.q_index}] {output.prompt['ko']}",
                "vi": output.prompt['vi']
            }
        
        # 평가 리포트
        elif hasattr(output, "report_markdown"):
            return {
                "session_id": current_session_id,
                "type": "report",
                "ko": output.report_markdown["ko"],
                "vi": "" # 리포트는 한국어만
            }
            
        return {"error": "Unknown response type"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# 정적 파일 서빙 (HTML)
# 주의: API 엔드포인트 정의 후 mount 해야 함
# static 폴더가 없으면 에러 나므로 예외 처리
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8503)

import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from utils.prompts import INTERVIEWER_PROMPT_TEMPLATE
from utils.schemas import InterviewerOutput
import os

class InterviewerAgent:
    def __init__(self):
        # Gemini Pro 사용
        self.llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.7)
        self.prompt_template = PromptTemplate(
            input_variables=["current_q_index", "max_questions", "qa_history", "last_answer", "followup_request"],
            template=INTERVIEWER_PROMPT_TEMPLATE
        )

    def generate_question(self, session_data, is_followup: bool = False) -> InterviewerOutput:
        state = session_data.state
        qa_log = session_data.qa_log
        settings = session_data.settings

        # QA 기록 포맷팅
        history_text = ""
        for item in qa_log:
            # item이 dict인지 객체인지 확인 (안전하게 dict 접근)
            q_idx = item.get("q_index") if isinstance(item, dict) else item.q_index
            question = item.get("question") if isinstance(item, dict) else item.question
            answer = item.get("answer", "") if isinstance(item, dict) else item.answer
            
            history_text += f"Q{q_idx}: {question['ko']}\nA: {answer}\n"
            
            # Follow-up 체크
            followup = item.get("followup") if isinstance(item, dict) else getattr(item, "followup", None)
            if followup and followup.get("asked"):
                history_text += f"  (Follow-up Q): {followup['question']['ko']}\n  (Follow-up A): {followup.get('answer', '')}\n"

        # 마지막 답변 추출
        last_answer = ""
        if qa_log:
             last_qa = qa_log[-1]
             # dict vs object 처리
             l_answer = last_qa.get("answer", "") if isinstance(last_qa, dict) else last_qa.answer
             l_followup = last_qa.get("followup") if isinstance(last_qa, dict) else getattr(last_qa, "followup", None)
             
             if is_followup: 
                 last_answer = l_answer
             elif l_followup and l_followup.get("answer"):
                 last_answer = l_followup["answer"]
             else:
                 last_answer = l_answer

        # 프롬프트 완성
        final_prompt = self.prompt_template.format(
            current_q_index=state.current_q_index,
            max_questions=settings.max_questions,
            qa_history=history_text,
            last_answer=last_answer,
            followup_request="YES" if is_followup else "NO"
        )
        
        # LLM 호출
        try:
            response = self.llm.invoke(final_prompt)
            content = response.content
            
            # JSON 파싱 (Gemini는 마크다운 코드 블록을 자주 포함함)
            cleaned_content = content.strip()
            if cleaned_content.startswith("```"):
                lines = cleaned_content.splitlines()
                if lines[0].strip().startswith("```"):
                    lines = lines[1:]
                if lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                cleaned_content = "\n".join(lines)
            
            data = json.loads(cleaned_content)
            
            return InterviewerOutput(
                type=data.get("type", "question"),
                prompt=data.get("prompt", {"ko": "질문 생성 오류", "vi": "Lỗi tạo câu hỏi"}),
                q_index=data.get("q_index", state.current_q_index),
                category=data.get("category", "General")
            )
            
        except Exception as e:
            print(f"Error generating question: {e}")
            return InterviewerOutput(
                type="error",
                prompt={"ko": "죄송합니다. 잠시 문제가 발생했습니다. 다시 시도해주세요.", "vi": "Xin lỗi, đã xảy ra lỗi."},
                q_index=state.current_q_index,
                category="Error"
            )

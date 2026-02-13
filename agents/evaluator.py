import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from utils.prompts import EVALUATOR_PROMPT_TEMPLATE
from utils.schemas import EvaluationOutput
import os

class EvaluatorAgent:
    def __init__(self):
        # Gemini Pro 사용
        # 임시 Key 하드코딩
        api_key = "AIzaSy..."
        if not os.environ.get("GOOGLE_API_KEY"):
             os.environ["GOOGLE_API_KEY"] = api_key

        self.llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.7)
        self.prompt_template = PromptTemplate(
            input_variables=["qa_history"],
            template=EVALUATOR_PROMPT_TEMPLATE
        )

    def evaluate_interview(self, session_data) -> EvaluationOutput:
        qa_log = session_data.qa_log
        
        # QA 로그 포맷팅
        history_text = ""
        for item in qa_log:
            q_idx = item.get("q_index") if isinstance(item, dict) else item.q_index
            question = item.get("question") if isinstance(item, dict) else item.question
            answer = item.get("answer", "") if isinstance(item, dict) else item.answer
            
            history_text += f"Q{q_idx}: {question['ko']}\nA: {answer}\n"
            
            followup = item.get("followup") if isinstance(item, dict) else getattr(item, "followup", None)
            if followup and followup.get("asked"):
                history_text += f"  (Follow-up Q): {followup['question']['ko']}\n  (Follow-up A): {followup.get('answer', '')}\n"
        
        # 프롬프트 완성
        final_prompt = self.prompt_template.format(qa_history=history_text)
        
        # LLM 호출
        try:
            response = self.llm.invoke(final_prompt)
            content = response.content
            
            # JSON 파싱
            cleaned_content = content.strip()
            if cleaned_content.startswith("```"):
                lines = cleaned_content.splitlines()
                if lines[0].strip().startswith("```"):
                    lines = lines[1:]
                if lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                cleaned_content = "\n".join(lines)
                
            data = json.loads(cleaned_content)
            
            return EvaluationOutput(
                report_markdown=data.get("report_markdown", {"ko": "평가 결과 생성 실패", "vi": "Tạo kết quả đánh giá thất bại"})
            )
            
        except Exception as e:
            print(f"Evaluation Error: {e}")
            return EvaluationOutput(
                report_markdown={"ko": "죄송합니다. 평가 결과를 생성하는 중 오류가 발생했습니다.", "vi": "Xin lỗi, đã xảy ra lỗi khi tạo kết quả đánh giá."}
            )

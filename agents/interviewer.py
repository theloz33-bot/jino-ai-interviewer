import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from utils.schemas import InterviewerOutput
from utils.prompts import INTERVIEWER_PROMPT

class InterviewerAgent:
    def __init__(self, model_name="gpt-4o"):
        self.llm = ChatOpenAI(model=model_name, temperature=0.7)
        self.output_parser = PydanticOutputParser(pydantic_object=InterviewerOutput)

    def generate_question(self, session_data: dict, followup_request: bool = False, last_answer: str = ""):
        """
        면접관 에이전트: 다음 질문 또는 꼬리질문 생성
        """
        prompt = ChatPromptTemplate.from_template(INTERVIEWER_PROMPT)
        
        # 입력 변수 준비
        role_context = session_data.get("role_context", {})
        current_q_index = session_data["state"]["current_q_index"]
        
        # LLM 호출
        formatted_prompt = prompt.format_messages(
            role_context=role_context,
            current_q_index=current_q_index,
            followup_request=followup_request,
            last_answer_raw=last_answer
        )
        
        # Pydantic 파싱
        # (실제로는 LLM이 JSON을 잘 뱉도록 강제하거나, 재시도 로직이 필요할 수 있음)
        # 여기서는 간단히 invoke 후 파싱 시도
        
        response = self.llm.invoke(formatted_prompt)
        
        # JSON 포맷팅 보정 (간혹 마크다운 ```json ... ``` 으로 감싸서 줄 때가 있음)
        content = response.content.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "")
        elif content.startswith("```"):
            content = content.replace("```", "")
            
        try:
            return self.output_parser.parse(content)
        except Exception as e:
            # 파싱 실패 시 로깅 후 기본값 또는 재시도 (여기선 에러 출력)
            print(f"Interviewer JSON Parsing Error: {e}")
            print(f"Raw Content: {content}")
            return None

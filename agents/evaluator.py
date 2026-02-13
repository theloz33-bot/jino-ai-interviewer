import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from utils.schemas import EvaluationOutput
from utils.prompts import EVALUATOR_PROMPT

class EvaluatorAgent:
    def __init__(self, model_name="gpt-4o"):
        self.llm = ChatOpenAI(model=model_name, temperature=0.7)
        self.output_parser = PydanticOutputParser(pydantic_object=EvaluationOutput)

    def evaluate_interview(self, session_data: dict):
        """
        평가관 에이전트: 면접 종료 후 평가 리포트 생성
        """
        prompt = ChatPromptTemplate.from_template(EVALUATOR_PROMPT)
        
        # 입력 변수 준비
        role_context = session_data.get("role_context", {})
        qa_log = session_data.get("qa_log", [])
        weights = session_data.get("settings", {}).get("weights", {})
        
        # LLM 호출
        formatted_prompt = prompt.format_messages(
            role_context=role_context,
            weights=weights,
            qa_log=qa_log
        )
        
        response = self.llm.invoke(formatted_prompt)
        
        # JSON 포맷팅 보정
        content = response.content.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "")
        elif content.startswith("```"):
            content = content.replace("```", "")
            
        try:
            return self.output_parser.parse(content)
        except Exception as e:
            print(f"Evaluator JSON Parsing Error: {e}")
            print(f"Raw Content: {content}")
            return None

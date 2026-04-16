"""
Ollama 로컬 LLM 클라이언트

Ollama 설치: https://ollama.com
추천 모델 (한국어):
  ollama pull exaone3.5:8b   ← LG AI, 한국어 특화
  ollama pull qwen2.5:7b     ← 알리바바, 한국어 우수
  ollama pull llama3.1:8b    ← Meta, 무난한 성능
"""

import json
import requests
from config import Config

SYSTEM_PROMPT = """당신은 사내 정책 Wiki 검색 도우미입니다.
주어진 Wiki 문서를 바탕으로 사용자의 질문에 정확하고 간결하게 답변해 주세요.

답변 규칙:
1. 반드시 제공된 Wiki 문서 내용을 기반으로 답변하세요.
2. 답변 끝에 참고한 페이지 제목을 [출처: 페이지명] 형식으로 표시하세요.
3. Wiki에서 관련 내용을 찾지 못한 경우 "해당 내용을 Wiki에서 찾을 수 없습니다."라고 답변하세요.
4. 명확하고 간결하게 답변하세요. 불필요한 서론은 생략하세요."""


class OllamaClient:
    def __init__(self, config: Config):
        self.config = config

    @property
    def base_url(self) -> str:
        return self.config.get("ollama_url", "http://localhost:11434").rstrip("/")

    @property
    def model(self) -> str:
        return self.config.get("ollama_model", "")

    # 페이지당 최대 글자 수 (길수록 느림)
    MAX_CONTENT_CHARS = 1500

    def _build_user_message(self, question: str, context_pages: list[dict]) -> str:
        if context_pages:
            sections = []
            for page in context_pages:
                title = page.get("subject", "제목 없음")
                body = page.get("body", {})
                content = body.get("content", "") if isinstance(body, dict) else ""
                # 내용이 너무 길면 앞부분만 사용
                if len(content) > self.MAX_CONTENT_CHARS:
                    content = content[:self.MAX_CONTENT_CHARS] + "...(이하 생략)"
                sections.append(f"## {title}\n\n{content}")
            context_text = "\n\n---\n\n".join(sections)
            return (
                f"다음 Wiki 문서를 참고하여 질문에 답변해 주세요.\n\n"
                f"[Wiki 문서]\n{context_text}\n\n"
                f"[질문]\n{question}"
            )
        else:
            return (
                f"Wiki에서 관련 문서를 찾지 못했습니다. "
                f"일반 지식으로 답변 가능한 경우 답변하고, "
                f"그렇지 않으면 찾을 수 없다고 안내해 주세요.\n\n"
                f"[질문]\n{question}"
            )

    def ask(
        self,
        question: str,
        context_pages: list[dict],
        on_chunk=None,
    ) -> str:
        user_message = self._build_user_message(question, context_pages)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "stream": True,
        }

        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            stream=True,
            timeout=180,
        )
        response.raise_for_status()

        full_text = ""
        for line in response.iter_lines():
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            chunk = data.get("message", {}).get("content", "")
            if chunk:
                full_text += chunk
                if on_chunk:
                    on_chunk(chunk)

            if data.get("done"):
                break

        if not full_text:
            raise RuntimeError("모델이 빈 응답을 반환했습니다. 모델 설정을 확인하세요.")

        return full_text

    def get_models(self) -> list[str]:
        """설치된 모델 목록을 반환합니다."""
        response = requests.get(f"{self.base_url}/api/tags", timeout=10)
        response.raise_for_status()
        models = response.json().get("models", [])
        return [m["name"] for m in models]

    def test_connection(self) -> tuple[bool, str]:
        try:
            models = self.get_models()
            if not models:
                return False, "Ollama가 실행 중이지만 설치된 모델이 없습니다.\n터미널에서 'ollama pull qwen2.5:7b' 를 실행해 주세요."
            if not self.model:
                return False, f"모델을 선택해 주세요. 설치된 모델: {', '.join(models)}"
            if self.model not in models:
                return False, f"선택한 모델 '{self.model}'이 없습니다.\n설치된 모델: {', '.join(models)}"
            return True, f"연결 성공  (모델: {self.model})"
        except requests.exceptions.ConnectionError:
            return False, (
                "Ollama가 실행되지 않고 있습니다.\n"
                "① ollama.com에서 설치\n"
                "② 터미널에서 'ollama serve' 실행"
            )
        except Exception as e:
            return False, f"오류: {str(e)}"

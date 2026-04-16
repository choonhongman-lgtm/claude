from typing import Callable
import anthropic
from config import Config

SYSTEM_PROMPT = """당신은 사내 정책 Wiki 검색 도우미입니다.
주어진 Wiki 문서를 바탕으로 사용자의 질문에 정확하고 간결하게 답변해 주세요.

답변 규칙:
1. 반드시 제공된 Wiki 문서 내용을 기반으로 답변하세요.
2. 답변 끝에 참고한 페이지 제목을 "[출처: 페이지명]" 형식으로 표시하세요.
3. Wiki에서 관련 내용을 찾지 못한 경우 "해당 내용을 Wiki에서 찾을 수 없습니다."라고 답변하세요.
4. 명확하고 간결하게 답변하세요. 불필요한 서론은 생략하세요."""


class ClaudeClient:
    def __init__(self, config: Config):
        self.config = config

    def _client(self):
        return anthropic.Anthropic(api_key=self.config.get("claude_api_key"))

    def _build_user_message(self, question: str, context_pages: list[dict]) -> str:
        if context_pages:
            sections = []
            for page in context_pages:
                title = page.get("subject", "제목 없음")
                body = page.get("body", {})
                content = body.get("content", "") if isinstance(body, dict) else ""
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
        on_chunk: Callable[[str], None] | None = None,
    ) -> str:
        """
        Wiki 컨텍스트와 함께 Claude에 질문합니다.
        on_chunk가 제공되면 스트리밍으로 응답합니다.
        """
        user_message = self._build_user_message(question, context_pages)

        if on_chunk:
            with self._client().messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            ) as stream:
                full_text = ""
                for chunk in stream.text_stream:
                    full_text += chunk
                    on_chunk(chunk)
                return full_text
        else:
            response = self._client().messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text

    def test_connection(self) -> tuple[bool, str]:
        try:
            self._client().messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=10,
                messages=[{"role": "user", "content": "hi"}],
            )
            return True, "Claude API 연결 성공"
        except anthropic.AuthenticationError:
            return False, "API 키가 올바르지 않습니다"
        except anthropic.APIConnectionError:
            return False, "Claude 서버에 연결할 수 없습니다"
        except Exception as e:
            return False, f"오류: {str(e)}"

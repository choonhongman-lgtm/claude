"""
두레이 Wiki API 클라이언트

인증: Authorization: dooray-token {token}
Base URL 예시: https://nhn.dooray.com
"""

import requests
from config import Config


class WikiClient:
    def __init__(self, config: Config):
        self.config = config

    # ── 공통 ────────────────────────────────────────────────────────────────────

    @property
    def headers(self):
        token = self.config.get("wiki_token", "")
        return {"Authorization": f"dooray-api {token}"}

    @property
    def base_url(self):
        return self.config.get("wiki_url", "").rstrip("/")

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _ok(body: dict) -> bool:
        return body.get("header", {}).get("isSuccessful", False)

    # ── Wiki 목록 ────────────────────────────────────────────────────────────────

    def get_wikis(self) -> list[dict]:
        """접근 가능한 위키 목록을 반환합니다. GET /wiki/v1/wikis"""
        body = self._get("/wiki/v1/wikis", params={"size": 100})
        return body.get("result", [])

    # ── 페이지 목록 (1 depth) ────────────────────────────────────────────────────

    def get_pages(self, wiki_id: str, parent_page_id: str | None = None) -> list[dict]:
        """
        위키의 한 depth 페이지 목록을 반환합니다.
        GET /wiki/v1/wikis/{wiki-id}/pages
        parent_page_id=None 이면 최상위 페이지 목록
        """
        params = {}
        if parent_page_id:
            params["parentPageId"] = parent_page_id
        body = self._get(f"/wiki/v1/wikis/{wiki_id}/pages", params=params)
        return body.get("result", [])

    # ── 페이지 상세 ──────────────────────────────────────────────────────────────

    def get_page_detail(self, wiki_id: str, page_id: str) -> dict:
        """
        페이지 상세 조회 (제목 + 본문 포함)
        GET /wiki/v1/wikis/{wiki-id}/pages/{page-id}
        """
        body = self._get(f"/wiki/v1/wikis/{wiki_id}/pages/{page_id}")
        return body.get("result", {})

    # ── 전체 페이지 재귀 수집 ─────────────────────────────────────────────────────

    def _collect_pages(
        self,
        wiki_id: str,
        parent_page_id: str | None,
        on_progress=None,
        collected: list | None = None,
    ) -> list[dict]:
        """재귀적으로 모든 하위 페이지를 수집합니다."""
        if collected is None:
            collected = []

        pages = self.get_pages(wiki_id, parent_page_id)
        for page in pages:
            page_id = page.get("id")
            if not page_id:
                continue
            try:
                detail = self.get_page_detail(wiki_id, page_id)
                collected.append(detail)
                if on_progress:
                    on_progress(len(collected), detail.get("subject", page_id))
            except Exception:
                collected.append(page)

            # 하위 페이지 재귀 탐색
            self._collect_pages(wiki_id, page_id, on_progress, collected)

        return collected

    def get_all_pages(self, on_progress=None) -> list[dict]:
        """
        설정에서 선택된 Wiki ID의 모든 페이지를 가져옵니다.
        선택된 Wiki가 없으면 접근 가능한 전체 Wiki를 수집합니다.
        on_progress(count, title) — 진행 상황 콜백 (선택)
        """
        selected_ids = self.config.get("selected_wiki_ids", [])

        if selected_ids:
            wikis = [{"id": wid} for wid in selected_ids]
        else:
            wikis = self.get_wikis()

        all_pages: list[dict] = []
        for wiki in wikis:
            wiki_id = wiki.get("id")
            if not wiki_id:
                continue
            self._collect_pages(wiki_id, None, on_progress, all_pages)
        return all_pages

    # ── 연결 테스트 ──────────────────────────────────────────────────────────────

    def test_connection(self) -> tuple[bool, str]:
        try:
            url = f"{self.base_url}/wiki/v1/wikis"
            response = requests.get(url, headers=self.headers,
                                    params={"size": 1}, timeout=30,
                                    allow_redirects=True)

            status = response.status_code
            content_type = response.headers.get("Content-Type", "")
            text = response.text.strip()

            # 빈 응답
            if not text:
                return False, f"빈 응답 수신 (HTTP {status}). 토큰 또는 URL을 확인하세요."

            # HTML 응답 → 로그인 페이지로 리다이렉트된 경우
            if "text/html" in content_type or text.lstrip().startswith("<"):
                return False, (
                    f"HTML 응답 수신 (HTTP {status}). "
                    "API 토큰 인증에 실패했거나 URL이 잘못됐습니다.\n"
                    "첫 번째 URL(두레이 API 활용가이드)에서 인증 방식을 확인해 주세요."
                )

            response.raise_for_status()

            try:
                body = response.json()
            except Exception:
                preview = text[:150].replace("\n", " ")
                return False, f"JSON 파싱 실패 (HTTP {status}): {preview}"

            if self._ok(body):
                count = body.get("totalCount", "?")
                return True, f"연결 성공 — 접근 가능한 위키: {count}개"

            msg = body.get("header", {}).get("resultMessage", "알 수 없는 오류")
            return False, f"서버 오류: {msg}"

        except requests.exceptions.ConnectionError:
            return False, "Wiki 서버에 연결할 수 없습니다. URL을 확인하세요."
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            body_text = e.response.text[:200].replace("\n", " ")
            if status == 401:
                return False, "인증 실패 (401): 토큰을 확인하세요."
            elif status == 403:
                return False, "접근 권한 없음 (403)"
            elif status == 404:
                return False, "엔드포인트 없음 (404): URL을 확인하세요."
            return False, f"HTTP {status}: {body_text}"
        except Exception as e:
            return False, f"오류: {str(e)}"

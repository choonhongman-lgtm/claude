"""
BM25 기반 로컬 검색 엔진

두레이 Wiki 응답 구조:
  - 제목: result.subject
  - 내용: result.body.content  (마크다운)
  - ID  : result.id
"""

import json
import re
from config import Config


def extract_text(page: dict) -> tuple[str, str]:
    """두레이 페이지 dict에서 (제목, 본문 텍스트)를 추출합니다."""
    title = page.get("subject", "")
    body = page.get("body", {})
    content = body.get("content", "") if isinstance(body, dict) else ""
    return title, content


class WikiSearch:
    def __init__(self, config: Config):
        self.config = config
        self._pages: list[dict] = []
        self._bm25 = None
        self._load_cache()

    # ── 토크나이저 ──────────────────────────────────────────────────────────────

    def _tokenize(self, text: str) -> list[str]:
        """한국어/영어 혼용 토크나이저 (형태소 분석 없이 2-gram 보강)"""
        text = re.sub(r"[^\w\s가-힣]", " ", text.lower())
        tokens = text.split()
        bigrams = []
        for token in tokens:
            if len(token) >= 2 and any("\uAC00" <= c <= "\uD7A3" for c in token):
                bigrams.extend(token[i : i + 2] for i in range(len(token) - 1))
        return tokens + bigrams

    # ── 캐시 관리 ───────────────────────────────────────────────────────────────

    def _load_cache(self):
        if self.config.CACHE_FILE.exists():
            with open(self.config.CACHE_FILE, "r", encoding="utf-8") as f:
                self._pages = json.load(f)
            self._build_index()

    def _build_index(self):
        if not self._pages:
            return
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            self._bm25 = None
            return

        corpus = []
        for page in self._pages:
            title, content = extract_text(page)
            corpus.append(self._tokenize(f"{title} {content}"))

        self._bm25 = BM25Okapi(corpus)

    def update_cache(self, pages: list[dict]):
        self._pages = pages
        with open(self.config.CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(pages, f, ensure_ascii=False, indent=2)
        self._build_index()

    # ── 검색 ────────────────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        if not self._bm25 or not self._pages:
            return []
        tokens = self._tokenize(query)
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [self._pages[i] for i in ranked[:top_k] if scores[i] > 0]

    def get_cache_size(self) -> int:
        return len(self._pages)

"""
이미지 OCR 처리기

EasyOCR을 사용하여 이미지에서 한국어/영어 텍스트를 추출합니다.
처음 실행 시 모델 다운로드 (~1.5GB) 가 필요합니다.

설치:
  py -m pip install easyocr
"""

import json
from pathlib import Path

OCR_CACHE_FILE = Path.home() / ".wiki-chat" / "ocr_cache.json"


class OCRProcessor:
    def __init__(self):
        self._reader = None
        self._cache: dict[str, str] = self._load_cache()

    # ── 캐시 ────────────────────────────────────────────────────────────────────

    def _load_cache(self) -> dict:
        if OCR_CACHE_FILE.exists():
            with open(OCR_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_cache(self):
        with open(OCR_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)

    def is_cached(self, key: str) -> bool:
        return key in self._cache

    # ── OCR 리더 (지연 초기화) ───────────────────────────────────────────────────

    def _get_reader(self):
        if self._reader is None:
            try:
                import easyocr
            except ImportError:
                raise ImportError(
                    "easyocr가 설치되지 않았습니다.\n"
                    "터미널에서 다음 명령어를 실행하세요:\n"
                    "  py -m pip install easyocr"
                )
            # gpu=False: CPU 사용 (GPU 없어도 동작)
            self._reader = easyocr.Reader(["ko", "en"], gpu=False, verbose=False)
        return self._reader

    # ── 텍스트 추출 ─────────────────────────────────────────────────────────────

    def extract(self, image_bytes: bytes, cache_key: str = "") -> str:
        """
        이미지 바이트에서 텍스트를 추출합니다.
        cache_key가 있으면 캐시를 먼저 확인하고, 결과를 캐시에 저장합니다.
        """
        if cache_key and cache_key in self._cache:
            return self._cache[cache_key]

        try:
            reader = self._get_reader()
            results = reader.readtext(image_bytes, detail=0, paragraph=True)
            text = " ".join(r.strip() for r in results if r.strip())
        except Exception:
            text = ""

        if cache_key:
            self._cache[cache_key] = text
            self._save_cache()

        return text

    def cache_size(self) -> int:
        return len(self._cache)

import threading
import tkinter as tk
from typing import Callable
import customtkinter as ctk


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, config, wiki_client, on_save: Callable | None = None):
        super().__init__(parent)
        self.config = config
        self.wiki_client = wiki_client
        self.on_save = on_save

        self._wiki_vars: dict[str, tk.BooleanVar] = {}
        self._wiki_data: list[dict] = []

        self.title("설정")
        self.geometry("520x660")
        self.resizable(False, False)
        self.grab_set()
        self.focus_set()

        self._build_ui()
        self._load_values()

        if self.config.get("wiki_url") and self.config.get("wiki_token"):
            self.after(400, self._load_wiki_list)

    # ── UI ──────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # ── 두레이 접속 정보 ──
        self._section(scroll, "두레이 접속 정보")

        self._lbl(scroll, "두레이 API URL")
        self.wiki_url = self._entry(scroll, placeholder="https://api.dooray.com")

        self._lbl(scroll, "두레이 웹 URL  (페이지 링크 생성에 사용)")
        self.wiki_web_url = self._entry(scroll, placeholder="https://nhnent.dooray.com")

        self._lbl(scroll, "API 토큰  (두레이 → 개인 설정 → API 토큰)")
        self.wiki_token = self._entry(scroll, show="*", placeholder="두레이 API 토큰")

        # ── Wiki 프로젝트 선택 ──
        ctk.CTkFrame(scroll, height=2, fg_color="gray50").pack(fill="x", pady=10)
        self._section(scroll, "Wiki 프로젝트 선택")

        top_row = ctk.CTkFrame(scroll, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 6))
        self.load_btn = ctk.CTkButton(
            top_row, text="목록 불러오기", width=130, height=32,
            command=self._load_wiki_list,
        )
        self.load_btn.pack(side="left")
        self.wiki_list_status = ctk.CTkLabel(
            top_row, text="", font=ctk.CTkFont(size=11), text_color="gray"
        )
        self.wiki_list_status.pack(side="left", padx=10)

        self.wiki_list_frame = ctk.CTkScrollableFrame(scroll, height=160)
        self.wiki_list_frame.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(
            self.wiki_list_frame,
            text="[목록 불러오기]를 눌러 Wiki 목록을 가져오세요.",
            text_color="gray", font=ctk.CTkFont(size=12),
        ).pack(pady=20)

        self.wiki_test_btn = ctk.CTkButton(
            scroll, text="Wiki 연결 테스트", command=self._test_wiki
        )
        self.wiki_test_btn.pack(pady=(8, 2))
        self.wiki_test_label = ctk.CTkLabel(scroll, text="", wraplength=470)
        self.wiki_test_label.pack(pady=(0, 6))

        # ── 저장 ──
        ctk.CTkFrame(scroll, height=2, fg_color="gray50").pack(fill="x", pady=10)
        ctk.CTkButton(scroll, text="저장", width=200, height=40,
                      command=self._save).pack(pady=12)

    # ── 헬퍼 ────────────────────────────────────────────────────────────────────

    def _section(self, parent, text):
        ctk.CTkLabel(parent, text=text,
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0, 8))

    def _lbl(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=12)).pack(anchor="w")

    def _entry(self, parent, placeholder="", show=""):
        e = ctk.CTkEntry(parent, width=470, placeholder_text=placeholder, show=show)
        e.pack(pady=(0, 10))
        return e

    # ── 초기값 ──────────────────────────────────────────────────────────────────

    def _load_values(self):
        self.wiki_url.insert(0, self.config.get("wiki_url", ""))
        self.wiki_web_url.insert(0, self.config.get("wiki_web_url", ""))
        self.wiki_token.insert(0, self.config.get("wiki_token", ""))

    # ── Wiki 목록 ────────────────────────────────────────────────────────────────

    def _load_wiki_list(self):
        self._apply()
        self.load_btn.configure(state="disabled")
        self.wiki_list_status.configure(text="불러오는 중...", text_color="gray")

        def run():
            try:
                wikis = self.wiki_client.get_wikis()
                self.after(0, lambda: self._populate_wiki_list(wikis))
            except Exception as e:
                msg = f"불러오기 실패: {e}"
                self.after(0, lambda: self.wiki_list_status.configure(
                    text=msg, text_color="#e74c3c"
                ))
            finally:
                self.after(0, lambda: self.load_btn.configure(state="normal"))

        threading.Thread(target=run, daemon=True).start()

    def _populate_wiki_list(self, wikis: list[dict]):
        for w in self.wiki_list_frame.winfo_children():
            w.destroy()

        self._wiki_vars.clear()
        self._wiki_data = wikis
        selected_ids: list = self.config.get("selected_wiki_ids", [])

        if not wikis:
            ctk.CTkLabel(self.wiki_list_frame, text="접근 가능한 Wiki가 없습니다.",
                         text_color="gray").pack(pady=10)
            self.wiki_list_status.configure(text="Wiki 없음", text_color="orange")
            return

        for wiki in wikis:
            wiki_id = wiki.get("id", "")
            wiki_name = wiki.get("name", wiki_id)
            var = tk.BooleanVar(value=(wiki_id in selected_ids))
            self._wiki_vars[wiki_id] = var
            ctk.CTkCheckBox(
                self.wiki_list_frame, text=wiki_name,
                variable=var, font=ctk.CTkFont(size=13),
            ).pack(anchor="w", padx=8, pady=3)

        self.wiki_list_status.configure(text=f"총 {len(wikis)}개 Wiki", text_color="gray")

    # ── 저장 ────────────────────────────────────────────────────────────────────

    def _apply(self):
        self.config.set("wiki_url", self.wiki_url.get().strip())
        self.config.set("wiki_web_url", self.wiki_web_url.get().strip().rstrip("/"))
        self.config.set("wiki_token", self.wiki_token.get().strip())

        selected_ids = [wid for wid, var in self._wiki_vars.items() if var.get()]
        selected_names = [
            w.get("name", w.get("id", ""))
            for w in self._wiki_data
            if w.get("id") in selected_ids
        ]
        self.config.set("selected_wiki_ids", selected_ids)
        self.config.set("selected_wiki_names", selected_names)

    def _save(self):
        self._apply()
        self.config.save()
        if self.on_save:
            self.on_save()
        self.destroy()

    # ── 연결 테스트 ─────────────────────────────────────────────────────────────

    def _test_wiki(self):
        self._apply()
        self.wiki_test_label.configure(text="테스트 중...", text_color="gray")
        self.wiki_test_btn.configure(state="disabled")

        def run():
            success, msg = self.wiki_client.test_connection()
            color = "#2ecc71" if success else "#e74c3c"
            self.after(0, lambda: self.wiki_test_label.configure(text=msg, text_color=color))
            self.after(0, lambda: self.wiki_test_btn.configure(state="normal"))

        threading.Thread(target=run, daemon=True).start()

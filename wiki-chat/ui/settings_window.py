import threading
from typing import Callable
import customtkinter as ctk


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, config, wiki_client, claude_client, on_save: Callable | None = None):
        super().__init__(parent)
        self.config = config
        self.wiki_client = wiki_client
        self.claude_client = claude_client
        self.on_save = on_save

        self.title("설정")
        self.geometry("500x480")
        self.resizable(False, False)
        self.grab_set()
        self.focus_set()

        self._build_ui()
        self._load_values()

    # ── UI ──────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=24, pady=24)

        # ── 두레이 설정 ──
        ctk.CTkLabel(frame, text="두레이 Wiki 설정",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(0, 12))

        ctk.CTkLabel(frame, text="두레이 도메인 URL").pack(anchor="w")
        self.wiki_url = ctk.CTkEntry(frame, width=450,
                                     placeholder_text="https://api.dooray.com")
        self.wiki_url.pack(pady=(0, 12))

        ctk.CTkLabel(frame, text="API 토큰  (두레이 → 개인 설정 → API 토큰)").pack(anchor="w")
        self.wiki_token = ctk.CTkEntry(frame, width=450, show="*",
                                       placeholder_text="두레이 API 토큰")
        self.wiki_token.pack(pady=(0, 12))

        self.wiki_test_btn = ctk.CTkButton(frame, text="Wiki 연결 테스트",
                                           command=self._test_wiki)
        self.wiki_test_btn.pack(pady=(0, 4))
        self.wiki_test_label = ctk.CTkLabel(frame, text="", wraplength=440)
        self.wiki_test_label.pack(pady=(0, 16))

        # ── 구분선 ──
        ctk.CTkFrame(frame, height=2, fg_color="gray50").pack(fill="x", pady=8)

        # ── Claude 설정 ──
        ctk.CTkLabel(frame, text="Claude API 설정",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(8, 12))

        ctk.CTkLabel(frame, text="Claude API 키").pack(anchor="w")
        self.claude_key = ctk.CTkEntry(frame, width=450, show="*",
                                       placeholder_text="sk-ant-...")
        self.claude_key.pack(pady=(0, 12))

        self.claude_test_btn = ctk.CTkButton(frame, text="Claude API 연결 테스트",
                                             command=self._test_claude)
        self.claude_test_btn.pack(pady=(0, 4))
        self.claude_test_label = ctk.CTkLabel(frame, text="", wraplength=440)
        self.claude_test_label.pack(pady=(0, 16))

        # ── 저장 ──
        ctk.CTkButton(frame, text="저장", width=200, height=40,
                      command=self._save).pack(pady=4)

    # ── 초기값 ──────────────────────────────────────────────────────────────────

    def _load_values(self):
        self.wiki_url.insert(0, self.config.get("wiki_url", ""))
        self.wiki_token.insert(0, self.config.get("wiki_token", ""))
        self.claude_key.insert(0, self.config.get("claude_api_key", ""))

    # ── 저장 ────────────────────────────────────────────────────────────────────

    def _apply(self):
        self.config.set("wiki_url", self.wiki_url.get().strip())
        self.config.set("wiki_token", self.wiki_token.get().strip())
        self.config.set("claude_api_key", self.claude_key.get().strip())

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

    def _test_claude(self):
        self._apply()
        self.claude_test_label.configure(text="테스트 중...", text_color="gray")
        self.claude_test_btn.configure(state="disabled")

        def run():
            success, msg = self.claude_client.test_connection()
            color = "#2ecc71" if success else "#e74c3c"
            self.after(0, lambda: self.claude_test_label.configure(text=msg, text_color=color))
            self.after(0, lambda: self.claude_test_btn.configure(state="normal"))

        threading.Thread(target=run, daemon=True).start()

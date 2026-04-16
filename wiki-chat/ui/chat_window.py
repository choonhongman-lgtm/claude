import threading
from datetime import datetime
import customtkinter as ctk

from config import Config
from wiki_client import WikiClient
from claude_client import ClaudeClient
from search import WikiSearch
from ui.settings_window import SettingsWindow


class ChatWindow:
    def __init__(self, root: ctk.CTk, config: Config):
        self.root = root
        self.config = config
        self._init_clients()
        self._build_ui()
        self._welcome()

    # ── 클라이언트 초기화 ────────────────────────────────────────────────────────

    def _init_clients(self):
        self.wiki_client = WikiClient(self.config)
        self.claude_client = ClaudeClient(self.config)
        self.wiki_search = WikiSearch(self.config)

    # ── UI 구성 ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.root.geometry("860x700")
        self.root.minsize(600, 500)
        self.root.title("Wiki Chat")
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_chat_area()
        self._build_input_area()

    def _build_header(self):
        header = ctk.CTkFrame(self.root, height=56, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        # 로고 + 제목
        ctk.CTkLabel(
            header,
            text="  Wiki Chat",
            font=ctk.CTkFont(size=17, weight="bold"),
        ).grid(row=0, column=0, padx=10, pady=15, sticky="w")

        # 캐시 상태 라벨
        self.cache_label = ctk.CTkLabel(
            header, text="", font=ctk.CTkFont(size=11), text_color="gray"
        )
        self.cache_label.grid(row=0, column=1, padx=10, sticky="e")

        # 버튼 영역
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=10, pady=8)

        self.sync_btn = ctk.CTkButton(
            btn_frame, text="Wiki 동기화", width=110, height=36, command=self._sync_wiki
        )
        self.sync_btn.pack(side="left", padx=4)

        ctk.CTkButton(
            btn_frame, text="설정", width=70, height=36, command=self._open_settings,
            fg_color="gray40", hover_color="gray30",
        ).pack(side="left", padx=4)

        self._refresh_cache_label()

    def _build_chat_area(self):
        self.chat_frame = ctk.CTkScrollableFrame(self.root, corner_radius=0)
        self.chat_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.chat_frame.grid_columnconfigure(0, weight=1)

    def _build_input_area(self):
        input_frame = ctk.CTkFrame(self.root, height=76, corner_radius=0)
        input_frame.grid(row=2, column=0, sticky="ew")
        input_frame.grid_propagate(False)
        input_frame.grid_columnconfigure(0, weight=1)

        self.input_box = ctk.CTkTextbox(input_frame, height=52, wrap="word", font=ctk.CTkFont(size=13))
        self.input_box.grid(row=0, column=0, padx=(12, 6), pady=12, sticky="ew")
        self.input_box.bind("<Return>", self._on_enter)

        self.send_btn = ctk.CTkButton(
            input_frame, text="전송", width=84, height=52, command=self._send_message,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.send_btn.grid(row=0, column=1, padx=(0, 12), pady=12)

    # ── 캐시 라벨 ───────────────────────────────────────────────────────────────

    def _refresh_cache_label(self):
        size = self.wiki_search.get_cache_size()
        if size:
            self.cache_label.configure(text=f"Wiki {size}페이지 캐시됨", text_color="gray")
        else:
            self.cache_label.configure(text="Wiki 미동기화 — [Wiki 동기화] 버튼을 눌러 주세요", text_color="orange")

    # ── 시스템 메시지 ────────────────────────────────────────────────────────────

    def _welcome(self):
        if not self.config.is_configured():
            self._add_system("설정이 필요합니다. 우측 상단 [설정] 버튼을 클릭하여 Wiki URL, 토큰, Claude API 키를 입력해 주세요.")
        else:
            size = self.wiki_search.get_cache_size()
            hint = f"Wiki {size}페이지가 캐시되어 있습니다." if size else "Wiki 동기화 버튼을 눌러 페이지를 가져와 주세요."
            self._add_system(f"안녕하세요! 정책에 대해 궁금한 것을 물어보세요.\n{hint}")

    # ── 메시지 버블 ─────────────────────────────────────────────────────────────

    def _add_system(self, text: str):
        row = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        row.pack(fill="x", padx=30, pady=6)
        ctk.CTkLabel(
            row, text=text, wraplength=720, justify="center",
            text_color="gray", font=ctk.CTkFont(size=12),
        ).pack()

    def _add_user_bubble(self, text: str):
        row = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)

        bubble = ctk.CTkFrame(row, fg_color="#2D7DD2", corner_radius=16)
        bubble.pack(side="right", anchor="n")
        ctk.CTkLabel(
            bubble, text=text, wraplength=520, justify="left",
            text_color="white", padx=14, pady=10, font=ctk.CTkFont(size=13),
        ).pack()

        ctk.CTkLabel(
            row, text=datetime.now().strftime("%H:%M"),
            font=ctk.CTkFont(size=10), text_color="gray",
        ).pack(side="right", anchor="se", padx=6)

        self._scroll_bottom()

    def _add_assistant_bubble(self) -> ctk.CTkLabel:
        """빈 버블을 생성하고 내용 라벨을 반환합니다 (스트리밍용)."""
        row = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)

        # W 아이콘
        ctk.CTkLabel(
            row, text="W", width=32, height=32,
            fg_color="#27AE60", corner_radius=16,
            text_color="white", font=ctk.CTkFont(weight="bold"),
        ).pack(side="left", anchor="n", pady=4, padx=(0, 6))

        bubble = ctk.CTkFrame(row, fg_color=("#ECECEC", "#2A2A2A"), corner_radius=16)
        bubble.pack(side="left", anchor="nw")

        label = ctk.CTkLabel(
            bubble, text="", wraplength=560, justify="left",
            padx=14, pady=10, font=ctk.CTkFont(size=13), anchor="w",
        )
        label.pack()

        ctk.CTkLabel(
            row, text=datetime.now().strftime("%H:%M"),
            font=ctk.CTkFont(size=10), text_color="gray",
        ).pack(side="left", anchor="s", padx=6)

        return label

    def _scroll_bottom(self):
        self.root.after(80, lambda: self.chat_frame._parent_canvas.yview_moveto(1.0))

    # ── 메시지 전송 ─────────────────────────────────────────────────────────────

    def _on_enter(self, event):
        if not (event.state & 0x1):  # Shift 없이 Enter → 전송
            self._send_message()
            return "break"

    def _send_message(self):
        text = self.input_box.get("1.0", "end-1c").strip()
        if not text:
            return
        if not self.config.is_configured():
            self._add_system("설정을 먼저 완료해 주세요.")
            return

        self.input_box.delete("1.0", "end")
        self._add_user_bubble(text)
        self.send_btn.configure(state="disabled")

        def run():
            try:
                # 로컬 캐시에서 BM25 검색 (두레이 검색 API 미제공)
                context_pages = self.wiki_search.search(text, top_k=3)

                # 3) 응답 버블 생성
                label = self._add_assistant_bubble()
                accumulated = ""

                def on_chunk(chunk: str):
                    nonlocal accumulated
                    accumulated += chunk
                    snapshot = accumulated
                    self.root.after(0, lambda: label.configure(text=snapshot))
                    self.root.after(0, self._scroll_bottom)

                self.claude_client.ask(text, context_pages, on_chunk=on_chunk)

            except Exception as e:
                self.root.after(0, lambda: self._add_system(f"오류 발생: {e}"))
            finally:
                self.root.after(0, lambda: self.send_btn.configure(state="normal"))

        threading.Thread(target=run, daemon=True).start()

    # ── Wiki 동기화 ─────────────────────────────────────────────────────────────

    def _sync_wiki(self):
        if not self.config.is_configured():
            self._add_system("설정을 먼저 완료해 주세요.")
            return

        self.sync_btn.configure(state="disabled", text="동기화 중...")
        self._add_system("Wiki 동기화를 시작합니다. 페이지 수에 따라 시간이 걸릴 수 있습니다...")

        def on_progress(count: int, title: str):
            self.root.after(
                0,
                lambda c=count, t=title: self.cache_label.configure(
                    text=f"수집 중... {c}페이지  ({t[:20]})",
                    text_color="gray",
                ),
            )

        def run():
            try:
                pages = self.wiki_client.get_all_pages(on_progress=on_progress)
                self.wiki_search.update_cache(pages)
                msg = f"동기화 완료! {len(pages)}개 페이지를 캐시했습니다."
            except Exception as e:
                msg = f"동기화 실패: {e}"

            self.root.after(0, lambda: self._add_system(msg))
            self.root.after(0, self._refresh_cache_label)
            self.root.after(0, lambda: self.sync_btn.configure(state="normal", text="Wiki 동기화"))

        threading.Thread(target=run, daemon=True).start()

    # ── 설정 창 ─────────────────────────────────────────────────────────────────

    def _open_settings(self):
        SettingsWindow(
            self.root, self.config,
            self.wiki_client, self.claude_client,
            on_save=self._on_settings_saved,
        )

    def _on_settings_saved(self):
        self._init_clients()
        self._add_system("설정이 저장되었습니다.")
        self._refresh_cache_label()

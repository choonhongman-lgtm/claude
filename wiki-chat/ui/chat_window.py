import threading
import webbrowser
from datetime import datetime
import customtkinter as ctk

from config import Config
from wiki_client import WikiClient
from search import WikiSearch
from ui.settings_window import SettingsWindow


class ChatWindow:
    def __init__(self, root: ctk.CTk, config: Config):
        self.root = root
        self.config = config
        self._init_clients()
        self._build_ui()
        self._on_startup()

    # ── 초기화 ──────────────────────────────────────────────────────────────────

    def _init_clients(self):
        self.wiki_client = WikiClient(self.config)
        self.wiki_search = WikiSearch(self.config)

    # ── UI ──────────────────────────────────────────────────────────────────────

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

        ctk.CTkLabel(
            header, text="  Wiki Chat",
            font=ctk.CTkFont(size=17, weight="bold"),
        ).grid(row=0, column=0, padx=10, pady=15, sticky="w")

        self.cache_label = ctk.CTkLabel(
            header, text="", font=ctk.CTkFont(size=11), text_color="gray"
        )
        self.cache_label.grid(row=0, column=1, padx=10, sticky="e")

        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=10, pady=8)

        self.sync_btn = ctk.CTkButton(
            btn_frame, text="Wiki 업데이트", width=110, height=36,
            command=self._sync_wiki,
        )
        self.sync_btn.pack(side="left", padx=4)

        ctk.CTkButton(
            btn_frame, text="설정", width=70, height=36,
            command=self._open_settings,
            fg_color="gray40", hover_color="gray30",
        ).pack(side="left", padx=4)

        self._refresh_cache_label()

    def _build_chat_area(self):
        self.chat_frame = ctk.CTkScrollableFrame(self.root, corner_radius=0)
        self.chat_frame.grid(row=1, column=0, sticky="nsew")
        self.chat_frame.grid_columnconfigure(0, weight=1)

    def _build_input_area(self):
        input_frame = ctk.CTkFrame(self.root, height=76, corner_radius=0)
        input_frame.grid(row=2, column=0, sticky="ew")
        input_frame.grid_propagate(False)
        input_frame.grid_columnconfigure(0, weight=1)

        self.input_box = ctk.CTkTextbox(
            input_frame, height=52, wrap="word", font=ctk.CTkFont(size=13)
        )
        self.input_box.grid(row=0, column=0, padx=(12, 6), pady=12, sticky="ew")
        self.input_box.bind("<Return>", self._on_enter)

        self.send_btn = ctk.CTkButton(
            input_frame, text="검색", width=84, height=52,
            command=self._send_message,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.send_btn.grid(row=0, column=1, padx=(0, 12), pady=12)

    # ── 시작 ────────────────────────────────────────────────────────────────────

    def _on_startup(self):
        if not self.config.is_configured():
            self._add_system("처음 실행되었습니다. 설정 창이 열립니다.")
            self.root.after(300, self._open_settings)
            return

        size = self.wiki_search.get_cache_size()
        if size:
            self._add_system("궁금한 정책을 입력하면 관련 Wiki 페이지를 찾아드립니다.")
        else:
            self._add_system("Wiki 데이터가 없습니다. [Wiki 업데이트] 버튼을 눌러 동기화해 주세요.")

    # ── 캐시 라벨 ───────────────────────────────────────────────────────────────

    def _refresh_cache_label(self):
        size = self.wiki_search.get_cache_size()
        names = self.config.get("selected_wiki_names", [])
        wiki_label = "·".join(names) if names else "전체 Wiki"
        if size:
            self.cache_label.configure(
                text=f"[{wiki_label}]  {size}페이지 로드됨", text_color="gray"
            )
        else:
            self.cache_label.configure(
                text="Wiki 미동기화", text_color="orange"
            )

    # ── 메시지 추가 ─────────────────────────────────────────────────────────────

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

    def _add_result_cards(self, pages: list[dict]):
        """검색 결과를 카드 형태로 표시합니다."""
        web_url = self.config.get("wiki_web_url", "").rstrip("/")

        wrapper = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        wrapper.pack(fill="x", padx=16, pady=4, anchor="w")

        # W 아이콘
        icon_row = ctk.CTkFrame(wrapper, fg_color="transparent")
        icon_row.pack(fill="x")
        ctk.CTkLabel(
            icon_row, text="W", width=32, height=32,
            fg_color="#27AE60", corner_radius=16,
            text_color="white", font=ctk.CTkFont(weight="bold"),
        ).pack(side="left", anchor="n", pady=(4, 4), padx=(0, 8))

        ctk.CTkLabel(
            icon_row,
            text=f"관련 Wiki 페이지 {len(pages)}건을 찾았습니다.",
            font=ctk.CTkFont(size=13),
        ).pack(side="left", anchor="w")

        # 결과 카드
        for page in pages:
            page_id = page.get("id", "")
            wiki_id = page.get("wikiId", "")
            title = page.get("subject", "제목 없음")
            body = page.get("body", {})
            content = body.get("content", "") if isinstance(body, dict) else ""
            snippet = content[:150].replace("\n", " ").strip()
            if len(content) > 150:
                snippet += "..."

            url = f"{web_url}/wiki/{wiki_id}/{page_id}" if web_url and wiki_id else ""

            card = ctk.CTkFrame(
                wrapper,
                fg_color=("#F0F0F0", "#2A2A2A"),
                corner_radius=10,
            )
            card.pack(fill="x", pady=4, padx=(40, 0))

            # 제목
            ctk.CTkLabel(
                card, text=title,
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w", padx=12, pady=8,
            ).pack(fill="x")

            # URL (클릭 가능)
            if url:
                url_label = ctk.CTkLabel(
                    card, text=url,
                    font=ctk.CTkFont(size=11),
                    text_color="#4A90D9",
                    anchor="w", padx=12, cursor="hand2",
                )
                url_label.pack(fill="x")
                url_label.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))

            # 내용 미리보기
            if snippet:
                ctk.CTkLabel(
                    card, text=snippet,
                    font=ctk.CTkFont(size=11),
                    text_color="gray",
                    wraplength=680, justify="left",
                    anchor="w", padx=12, pady=6,
                ).pack(fill="x")

        ctk.CTkLabel(
            wrapper,
            text=datetime.now().strftime("%H:%M"),
            font=ctk.CTkFont(size=10), text_color="gray",
        ).pack(anchor="w", padx=42)

        self._scroll_bottom()

    def _add_no_result(self):
        row = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(
            row, text="W", width=32, height=32,
            fg_color="#27AE60", corner_radius=16,
            text_color="white", font=ctk.CTkFont(weight="bold"),
        ).pack(side="left", anchor="n", pady=4, padx=(0, 8))

        ctk.CTkLabel(
            row,
            text="관련 Wiki 페이지를 찾지 못했습니다. 다른 키워드로 검색해 보세요.",
            font=ctk.CTkFont(size=13), text_color="gray",
        ).pack(side="left", anchor="w")

        self._scroll_bottom()

    def _scroll_bottom(self):
        self.root.after(80, lambda: self.chat_frame._parent_canvas.yview_moveto(1.0))

    # ── 검색 ────────────────────────────────────────────────────────────────────

    def _on_enter(self, event):
        if not (event.state & 0x1):
            self._send_message()
            return "break"

    def _send_message(self):
        text = self.input_box.get("1.0", "end-1c").strip()
        if not text:
            return
        if not self.config.is_configured():
            self._add_system("설정을 먼저 완료해 주세요.")
            return
        if self.wiki_search.get_cache_size() == 0:
            self._add_system("Wiki 업데이트를 먼저 실행해 주세요.")
            return

        self.input_box.delete("1.0", "end")
        self._add_user_bubble(text)

        pages = self.wiki_search.search(text, top_k=5)
        if pages:
            self._add_result_cards(pages)
        else:
            self._add_no_result()

    # ── Wiki 업데이트 ────────────────────────────────────────────────────────────

    def _sync_wiki(self):
        if not self.config.is_configured():
            self._add_system("설정을 먼저 완료해 주세요.")
            return

        self.sync_btn.configure(state="disabled", text="업데이트 중...")
        self._add_system("Wiki 데이터를 가져오는 중입니다...")

        def on_progress(count: int, title: str):
            self.root.after(0, lambda c=count, t=title: self.cache_label.configure(
                text=f"수집 중... {c}페이지  ({t[:20]})", text_color="gray"
            ))

        def run():
            try:
                pages = self.wiki_client.get_all_pages(on_progress=on_progress)
                self.wiki_search.update_cache(pages)
                msg = f"업데이트 완료! {len(pages)}개 페이지를 불러왔습니다."
            except Exception as e:
                msg = f"업데이트 실패: {e}"

            self.root.after(0, lambda: self._add_system(msg))
            self.root.after(0, self._refresh_cache_label)
            self.root.after(0, lambda: self.sync_btn.configure(state="normal", text="Wiki 업데이트"))

        threading.Thread(target=run, daemon=True).start()

    # ── 설정 ────────────────────────────────────────────────────────────────────

    def _open_settings(self):
        SettingsWindow(
            self.root, self.config, self.wiki_client,
            on_save=self._on_settings_saved,
        )

    def _on_settings_saved(self):
        self._init_clients()
        self._add_system("설정이 저장되었습니다.")
        self._refresh_cache_label()
        if self.wiki_search.get_cache_size() == 0:
            self._add_system("Wiki 데이터가 없습니다. [Wiki 업데이트] 버튼을 눌러 동기화해 주세요.")

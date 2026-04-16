import customtkinter as ctk
from config import Config
from ui.chat_window import ChatWindow


def main():
    ctk.set_appearance_mode("system")   # "light" / "dark" / "system"
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    config = Config()
    ChatWindow(root, config)
    root.mainloop()


if __name__ == "__main__":
    main()

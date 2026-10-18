"""Local masked credential entry. Never prints the key."""
from pathlib import Path
import os
import tempfile
import tkinter as tk
from tkinter import messagebox

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def save_key(key):
    if not key or any(c.isspace() for c in key) or not key.isascii():
        raise ValueError("请粘贴完整的 API key，不要包含空格或换行。")
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    lines = [line for line in lines if not line.strip().startswith("ASSEMBLYAI_API_KEY=")]
    lines.append("ASSEMBLYAI_API_KEY=" + key)
    handle, temporary = tempfile.mkstemp(prefix=".env.", dir=ENV_PATH.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write("\n".join(lines) + "\n")
        os.replace(temporary, ENV_PATH)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    window = tk.Tk()
    window.title("CallGate · 配置语音服务")
    window.geometry("560x240")
    window.resizable(False, False)
    tk.Label(window, text="把 AssemblyAI API key 粘贴到下面", font=("Microsoft YaHei UI", 14)).pack(pady=(22, 12))
    entry = tk.Entry(window, show="●", width=52, font=("Segoe UI", 12))
    entry.pack(padx=24)
    tk.Label(window, text="密钥将保存在本机项目的 .env 文件（明文），已排除在 Git 提交之外。\n此步骤不会上传密钥、录音或开启麦克风。", font=("Microsoft YaHei UI", 9)).pack(pady=12)

    def submit():
        try:
            save_key(entry.get().strip())
        except ValueError as error:
            messagebox.showerror("请检查输入", str(error), parent=window)
            return
        except OSError:
            messagebox.showerror("保存失败", "无法写入配置文件，请回到聊天告诉我。", parent=window)
            return
        entry.delete(0, tk.END)
        messagebox.showinfo("配置已保存", "已保存。回到聊天回复「保存好了」，我们继续测试连接。", parent=window)
        window.destroy()

    tk.Button(window, text="保存配置", command=submit, width=18).pack()
    window.bind("<Return>", lambda _: submit())
    window.lift()
    window.attributes("-topmost", True)
    window.after(1500, lambda: window.attributes("-topmost", False))
    entry.focus_force()
    window.mainloop()


if __name__ == "__main__":
    main()

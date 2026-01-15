import os
import json
import time
import shutil
import threading
import sys
import multiprocessing
from datetime import datetime

# --- 核心修复：防止打包后 Playwright 进程无限重启 ---
if __name__ == "__main__":
    multiprocessing.freeze_support()

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
import pystray
from pystray import MenuItem as item
from playwright.sync_api import sync_playwright

# 设置主题
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class XiaohongshuUploader(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("小红书助手 v2.0")
        self.geometry("500x600")
        
        # 路径初始化
        if getattr(sys, 'frozen', False):
            self.base_path = os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))
            
        # --- 图标路径定义 ---
        # 建议在程序同级目录下放置 logo.png 或 logo.ico
        self.icon_path = os.path.join(self.base_path, "logo.png") 
        self.window_icon_path = os.path.join(self.base_path, "logo.ico")

        # 设置窗口左上角图标
        if os.path.exists(self.window_icon_path):
            try:
                self.after(200, lambda: self.iconbitmap(self.window_icon_path))
            except: pass
            
        self.config_path = os.path.join(self.base_path, "config.json")
        self.edge_user_data = os.path.join(self.base_path, "edge_profile_data")
        
        if not os.path.exists(self.edge_user_data):
            os.makedirs(self.edge_user_data)
            
        self.config = self.load_config()
        self.has_run_today = False 

        self.create_widgets()
        
        self.protocol('WM_DELETE_WINDOW', self.hide_window)
        threading.Thread(target=self.setup_tray, daemon=True).start()
        threading.Thread(target=self.run_schedule, daemon=True).start()

    def get_edge_path(self):
        """核心：自动寻找 Edge 安装路径"""
        possible_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Edge\Application\msedge.exe"),
            r"D:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    def load_config(self):
        default = {"h": "08", "m": "00", "title": "旧日好时光。Good old days.", "caption": "写字。Graffiti.", "tags": "旧日好时光 Graffiti", "image_folder": "", "enable_schedule": True, "autostart": True}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    default.update(json.load(f))
            except: pass
        return default

    def save_config(self):
        try:
            self.config.update({
                "h": self.hour_cb.get(), "m": self.min_cb.get(),
                "title": self.title_entry.get(), "caption": self.caption_text.get("1.0", "end-1c"),
                "tags": self.tags_entry.get(), "enable_schedule": bool(self.enable_var.get()),
                "autostart": bool(self.autostart_var.get()),
                "image_folder": self.path_label.cget("text")
            })
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            self.refresh_timer_ui()
        except: pass

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="小红书图文定时发布助手", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)

        f1 = ctk.CTkFrame(self)
        f1.pack(pady=10, padx=20, fill="x")
        self.path_label = ctk.CTkLabel(f1, text=self.config.get("image_folder") or "未选择文件夹", text_color="#3399FF")
        self.path_label.pack(side="left", padx=10, expand=True)
        ctk.CTkButton(f1, text="浏览", width=80, command=self.select_folder).pack(side="right", padx=10)

        self.title_entry = ctk.CTkEntry(self, placeholder_text="输入标题")
        self.title_entry.pack(padx=20, pady=5, fill="x")
        self.title_entry.insert(0, str(self.config.get("title")))

        self.caption_text = ctk.CTkTextbox(self, height=150)
        self.caption_text.pack(padx=20, pady=5, fill="x")
        self.caption_text.insert("1.0", str(self.config.get("caption")))

        self.tags_entry = ctk.CTkEntry(self, placeholder_text="标签 (逗号分隔)")
        self.tags_entry.pack(padx=20, pady=5, fill="x")
        self.tags_entry.insert(0, str(self.config.get("tags")))

        ctrl = ctk.CTkFrame(self)
        ctrl.pack(pady=15, padx=20, fill="x")
        self.hour_cb = ctk.CTkOptionMenu(ctrl, values=[f"{i:02d}" for i in range(24)], width=80)
        self.hour_cb.pack(side="left", padx=5)
        self.hour_cb.set(self.config.get("h"))

        self.min_cb = ctk.CTkOptionMenu(ctrl, values=[f"{i:02d}" for i in range(60)], width=80)
        self.min_cb.pack(side="left", padx=5)
        self.min_cb.set(self.config.get("m"))

        self.enable_var = ctk.BooleanVar(value=self.config.get("enable_schedule"))
        ctk.CTkCheckBox(ctrl, text="定时任务", variable=self.enable_var, command=self.save_config).pack(side="left", padx=10)

        self.autostart_var = ctk.BooleanVar(value=self.config.get("autostart"))
        ctk.CTkCheckBox(ctrl, text="自启动指引", variable=self.autostart_var, command=self.handle_autostart_click).pack(side="left")

        btn_f = ctk.CTkFrame(self, fg_color="transparent")
        btn_f.pack(pady=10, padx=20, fill="x")
        ctk.CTkButton(btn_f, text="保存配置", command=self.save_config, fg_color="#555555").pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_f, text="立即发布", fg_color="#FF2442", command=self.upload_now).pack(side="left", expand=True, padx=5)

        self.timer_label = ctk.CTkLabel(self, text="状态：待命")
        self.timer_label.pack()

        self.log_box = ctk.CTkTextbox(self, height=200, state='disabled')
        self.log_box.pack(padx=20, pady=10, fill="both", expand=True)

    def log(self, message):
        now = datetime.now().strftime("%H:%M:%S")
        self.after(0, lambda: [self.log_box.configure(state='normal'), self.log_box.insert('end', f"[{now}] {message}\n"), self.log_box.see('end'), self.log_box.configure(state='disabled')])

    def refresh_timer_ui(self):
        status = f"● 监控中：{self.hour_cb.get()}:{self.min_cb.get()}" if self.enable_var.get() else "○ 定时关闭"
        self.timer_label.configure(text=status, text_color="#4CAF50" if self.enable_var.get() else "gray")

    def select_folder(self):
        path = filedialog.askdirectory()
        if path: self.path_label.configure(text=path); self.save_config()

    def handle_autostart_click(self):
        if self.autostart_var.get(): os.startfile("shell:startup")
        self.save_config()

    def upload_now(self):
        self.save_config()
        threading.Thread(target=self.upload_process, daemon=True).start()

    def upload_process(self):
        folder = self.config.get("image_folder")
        if not folder or not os.path.exists(folder): self.log("错误：路径无效"); return
        
        imgs = [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg')) and not f.startswith("已发布")]
        if not imgs: self.log("通知：无待发布图片"); return
        target = os.path.join(folder, sorted(imgs)[0])

        edge_exe = self.get_edge_path()
        if not edge_exe: self.log("错误：未找到系统 Edge 浏览器"); return

        with sync_playwright() as p:
            try:
                self.log(f"任务启动: {os.path.basename(target)}")
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=self.edge_user_data,
                    executable_path=edge_exe,
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = browser.pages[0] if browser.pages else browser.new_page()
                page.goto("https://creator.xiaohongshu.com/publish/publish?source=official&target=image")
                
                if "login" in page.url:
                    self.log("等待扫码登录..."); page.wait_for_url("**/publish/**", timeout=0)
                
                page.locator("input[type='file']").set_input_files(target)
                page.get_by_placeholder("填写标题").fill(self.config.get("title"))
                page.keyboard.press("Tab"); time.sleep(1)
                page.keyboard.type(self.config.get("caption"))
                
                tags = [t.strip() for t in self.config.get("tags", "").replace("，", ",").split(",") if t.strip()]
                for tag in tags:
                    page.keyboard.press("Enter"); page.keyboard.type(f"#{tag}"); time.sleep(1.5); page.keyboard.press("Enter")
                
                time.sleep(2); page.get_by_role("button", name="发布").click()
                self.log("成功：已点击发布")
                time.sleep(8); browser.close()
                
                new_name = f"已发布_{datetime.now().strftime('%m%d_%H%M')}{os.path.splitext(target)[1]}"
                os.rename(target, os.path.join(folder, new_name))
            except Exception as e: self.log(f"异常: {str(e)[:50]}")

    def run_schedule(self):
        self.after(100, self.refresh_timer_ui)
        while True:
            if self.enable_var.get() and not self.has_run_today:
                n = datetime.now()
                if n.hour == int(self.hour_cb.get()) and n.minute == int(self.min_cb.get()):
                    self.upload_process(); self.has_run_today = True; time.sleep(65)
            elif datetime.now().second == 0: self.has_run_today = False
            time.sleep(1)

    # --- 托盘图标加载优化 ---
    def setup_tray(self):
        try:
            # 优先加载 logo.png，否则画红方块
            if os.path.exists(self.icon_path):
                image = Image.open(self.icon_path)
            else:
                image = Image.new('RGB', (64, 64), (255, 36, 66))

            menu = (item('显示', self.show_window), item('退出', self.quit_app))
            self.icon = pystray.Icon("xhs_bot", image, "小红书助手", menu)
            self.icon.run()
        except: pass

    def show_window(self): self.after(0, self.deiconify)
    def hide_window(self): self.withdraw()
    def quit_app(self): 
        if hasattr(self, 'icon'): self.icon.stop()
        self.quit(); os._exit(0)

if __name__ == "__main__":
    app = XiaohongshuUploader()
    app.mainloop()
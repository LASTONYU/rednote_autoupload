import os
import json
import time
import shutil
import threading
import sys
import multiprocessing
from datetime import datetime

# --- 防止打包后进程无限重启 ---
if __name__ == "__main__":
    multiprocessing.freeze_support()

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
import pystray
from pystray import MenuItem as item
from playwright.sync_api import sync_playwright

# 尝试导入快捷方式创建工具
try:
    import win32com.client
    import pythoncom
except:
    pass

class XiaohongshuUploader(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- 颜色定义 ---
        self.xhs_red = "#FF2442"
        self.white = "#FFFFFF"
        self.black = "#333333"
        self.pure_black = "#000000"
        
        self.title("小红书助手 v2.4")
        self.geometry("500x600") # 稍微增加高度，给下拉框留出内部空间
        self.configure(fg_color=self.white)
        
        # 路径处理
        if getattr(sys, 'frozen', False):
            self.base_path = os.path.dirname(sys.executable)
            self.res_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else self.base_path
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))
            self.res_path = self.base_path
            
        self.icon_path = os.path.join(self.res_path, "logo.png") 
        self.window_icon_path = os.path.join(self.res_path, "logo.ico")

        self.init_window_icon()
            
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

    def init_window_icon(self):
        try:
            if os.path.exists(self.window_icon_path):
                self.iconbitmap(self.window_icon_path)
        except: pass

    def load_config(self):
        default = {
            "h": "08", "m": "00", 
            "title": "旧日好时光。Good old days.", 
            "caption": "写字。Graffiti.", 
            "tags": "旧日好时光,Graffiti", 
            "image_folder": "", "enable_schedule": True, "autostart": True
        }
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    default.update(json.load(f))
            except: pass
        return default

    def create_shortcut(self):
        if not getattr(sys, 'frozen', False): return
        try:
            pythoncom.CoInitialize()
            shell = win32com.client.Dispatch("WScript.Shell")
            startup_path = shell.SpecialFolders("Startup")
            shortcut_path = os.path.join(startup_path, "小红书助手.lnk")
            target = sys.executable
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.TargetPath = target
            shortcut.WorkingDirectory = os.path.dirname(target)
            shortcut.IconLocation = target
            shortcut.save()
            self.log("✨ 已自动设为开机启动")
        except: pass

    def remove_shortcut(self):
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut_path = os.path.join(shell.SpecialFolders("Startup"), "小红书助手.lnk")
            if os.path.exists(shortcut_path): os.remove(shortcut_path)
            self.log("🚫 已取消开机启动")
        except: pass

    def save_config(self):
        try:
            self.config.update({
                "h": self.hour_cb.get(), "m": self.min_cb.get(),
                "title": self.title_entry.get(), "caption": self.caption_text.get("1.0", "end-1c"),
                "tags": self.tags_entry.get(), "enable_schedule": bool(self.enable_var.get()),
                "autostart": bool(self.autostart_var.get()),
                "image_folder": self.path_label.cget("text")
            })
            if self.config["autostart"]: self.create_shortcut()
            else: self.remove_shortcut()
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            self.refresh_timer_ui()
            self.log("💾 配置保存成功")
        except Exception as e: self.log(f"❌ 错误: {e}")

    def create_widgets(self):
        # 红色顶部导航栏
        header = ctk.CTkFrame(self, fg_color=self.white, height=50, corner_radius=0)
        header.pack(fill="x", pady=0)
        ctk.CTkLabel(header, text="小红书图文发布助手", font=ctk.CTkFont(size=20, weight="bold"), text_color=self.xhs_red).place(relx=0.5, rely=0.5, anchor="center")

        # 主内容包裹框
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(pady=10, padx=25, fill="both", expand=True)

        # 路径选择区
        path_f = ctk.CTkFrame(container, fg_color="transparent")
        path_f.pack(pady=5, fill="x")
        self.path_label = ctk.CTkLabel(path_f, text=self.config.get("image_folder") or "请选择图片目录", 
                                      text_color=self.xhs_red, font=ctk.CTkFont(size=12))
        self.path_label.pack(side="left", padx=5, expand=True)
        ctk.CTkButton(path_f, text="浏览", width=80, height=28, command=self.select_folder, 
                      fg_color=self.xhs_red, text_color=self.white).pack(side="right")

        input_style = {"fg_color": self.white, "text_color": self.black, "border_color": self.xhs_red, "border_width": 2}

        # 输入框区
        self.title_entry = ctk.CTkEntry(container, placeholder_text="输入标题...", **input_style)
        self.title_entry.pack(pady=5, fill="x")
        self.title_entry.insert(0, str(self.config.get("title")))

        self.caption_text = ctk.CTkTextbox(container, height=120, **input_style)
        self.caption_text.pack(pady=5, fill="x")
        self.caption_text.insert("1.0", str(self.config.get("caption")))

        self.tags_entry = ctk.CTkEntry(container, placeholder_text="话题标签...", **input_style)
        self.tags_entry.pack(pady=5, fill="x")
        self.tags_entry.insert(0, str(self.config.get("tags")))

        # --- 控制区：黑底白字时间选择 ---
        ctrl = ctk.CTkFrame(container, fg_color="#FFF0F0", border_color=self.xhs_red, border_width=1)
        ctrl.pack(pady=10, fill="x")
        
        # 黑底白字样式
        menu_style = {
            "fg_color": self.white,            # 按钮背景：白色
            "text_color": self.pure_black,     # 按钮文字：黑色
            "button_color": self.xhs_red,      # 箭头区域：红色
            "button_hover_color": "#ffffff",
            "dropdown_fg_color": self.white,   # 下拉菜单背景：白色
            "dropdown_text_color": self.black, # 下拉菜单文字：黑色
            "dropdown_hover_color": "#EEEEEE",
            "width": 90
        }

        self.hour_cb = ctk.CTkOptionMenu(ctrl, values=[f"{i:02d}" for i in range(24)], **menu_style)
        self.hour_cb.pack(side="left", padx=10, pady=10)
        self.hour_cb.set(self.config.get("h"))

        self.min_cb = ctk.CTkOptionMenu(ctrl, values=[f"{i:02d}" for i in range(60)], **menu_style)
        self.min_cb.pack(side="left", padx=5, pady=10)
        self.min_cb.set(self.config.get("m"))

        checkbox_style = {"text_color": self.xhs_red, "fg_color": self.xhs_red, "border_color": self.xhs_red}
        self.enable_var = ctk.BooleanVar(value=self.config.get("enable_schedule"))
        ctk.CTkCheckBox(ctrl, text="定时", variable=self.enable_var, command=self.save_config, **checkbox_style).pack(side="left", padx=10)

        self.autostart_var = ctk.BooleanVar(value=self.config.get("autostart"))
        ctk.CTkCheckBox(ctrl, text="自启", variable=self.autostart_var, command=self.save_config, **checkbox_style).pack(side="left")

        # 按钮区
        btn_f = ctk.CTkFrame(container, fg_color="transparent")
        btn_f.pack(pady=5, fill="x")
        ctk.CTkButton(btn_f, text="保存配置", command=self.save_config, fg_color="#444444", hover_color="#333333").pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_f, text="立即发布", command=self.upload_now, fg_color=self.xhs_red, font=ctk.CTkFont(weight="bold")).pack(side="left", expand=True, padx=5)

        self.timer_label = ctk.CTkLabel(container, text="状态：等待任务", text_color=self.xhs_red, font=ctk.CTkFont(weight="bold"))
        self.timer_label.pack()

        # 日志区
        self.log_box = ctk.CTkTextbox(container, height=130, **input_style)
        self.log_box.pack(pady=(5, 10), fill="both", expand=True)

    def log(self, message):
        now = datetime.now().strftime("%H:%M:%S")
        self.after(0, lambda: [self.log_box.configure(state='normal'), self.log_box.insert('end', f"[{now}] {message}\n"), self.log_box.see('end'), self.log_box.configure(state='disabled')])

    def refresh_timer_ui(self):
        status = f"● 监控中：{self.hour_cb.get()}:{self.min_cb.get()}" if self.enable_var.get() else "○ 定时任务未开启"
        self.timer_label.configure(text=status)

    def select_folder(self):
        path = filedialog.askdirectory()
        if path: 
            self.path_label.configure(text=path)
            self.save_config()

    def upload_now(self):
        self.log("🚀 启动手动发布...")
        self.save_config()
        threading.Thread(target=self.upload_process, daemon=True).start()

    def upload_process(self):
        folder = self.config.get("image_folder")
        if not folder or not os.path.exists(folder): self.log("❌ 请选择目录"); return
        imgs = [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg')) and not f.startswith("已发布")]
        if not imgs: self.log("⚠️ 目录无待发图片"); return
        target = os.path.join(folder, sorted(imgs)[0])
        edge_exe = self.get_edge_path()
        if not edge_exe: self.log("❌ 未找到Edge"); return

        with sync_playwright() as p:
            try:
                self.log(f"📦 处理中: {os.path.basename(target)}")
                browser = p.chromium.launch_persistent_context(user_data_dir=self.edge_user_data, executable_path=edge_exe, headless=False)
                page = browser.pages[0] if browser.pages else browser.new_page()
                page.goto("https://creator.xiaohongshu.com/publish/publish?source=official&target=image")
                if "login" in page.url:
                    self.log("🔑 请完成扫码登录..."); page.wait_for_url("**/publish/**", timeout=0)
                page.locator("input[type='file']").set_input_files(target)
                page.get_by_placeholder("填写标题").fill(self.config.get("title"))
                page.keyboard.press("Tab"); time.sleep(1)
                page.keyboard.type(self.config.get("caption"))
                tags = [t.strip() for t in self.config.get("tags", "").replace("，",",").split(",") if t.strip()]
                for tag in tags:
                    page.keyboard.press("Enter"); page.keyboard.type(f"#{tag}"); time.sleep(1.2); page.keyboard.press("Enter")
                time.sleep(2); page.get_by_role("button", name="发布").click()
                self.log("🎉 发布成功！")
                time.sleep(5); browser.close()
                os.rename(target, os.path.join(folder, f"已发布_{datetime.now().strftime('%m%d_%H%M')}{os.path.splitext(target)[1]}"))
            except Exception as e: self.log(f"❌ 运行异常: {str(e)[:40]}")

    def get_edge_path(self):
        ps = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Edge\Application\msedge.exe")]
        for p in ps: 
            if os.path.exists(p): return p
        return None

    def run_schedule(self):
        self.after(100, self.refresh_timer_ui)
        while True:
            if self.enable_var.get() and not self.has_run_today:
                n = datetime.now()
                if n.hour == int(self.hour_cb.get()) and n.minute == int(self.min_cb.get()):
                    self.upload_process(); self.has_run_today = True; time.sleep(65)
            elif datetime.now().second == 0: self.has_run_today = False
            time.sleep(1)

    def setup_tray(self):
        try:
            icon_img = Image.open(self.icon_path) if os.path.exists(self.icon_path) else Image.new('RGB', (64, 64), (255, 36, 66))
            menu = (item('显示', self.show_window), item('退出', self.quit_app))
            self.icon = pystray.Icon("xhs_bot", icon_img, "小红书助手", menu)
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
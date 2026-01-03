import os
import json
import time
import shutil
import threading
import sys
from datetime import datetime
from tkinter import Tk, Label, Button, Entry, Text, filedialog, Checkbutton, IntVar, Frame, scrolledtext, ttk, messagebox

# 图标与托盘相关库
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item
from playwright.sync_api import sync_playwright

class XiaohongshuUploader:
    def __init__(self, root):
        self.root = root
        self.root.title("小红书助手 v1.0 - 精简稳定版")
        self.root.geometry("620x900")
        
        # 1. 路径兼容性核心逻辑
        if getattr(sys, 'frozen', False):
            self.base_path = os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))
            
        self.icon_file = os.path.join(self.base_path, "app.ico")
        
        # 2. 设置窗口图标 (左上角)
        if os.path.exists(self.icon_file):
            try:
                self.root.iconbitmap(self.icon_file)
            except: pass

        self.root.protocol('WM_DELETE_WINDOW', self.hide_window)
        
        # 配置文件与数据目录
        self.config_path = os.path.join(self.base_path, "config.json")
        self.edge_user_data = os.path.join(self.base_path, "edge_profile_data")
        
        if not os.path.exists(self.edge_user_data):
            os.makedirs(self.edge_user_data)
            
        self.config = self.load_config()
        self.has_run_today = False 
        self.create_widgets()
        
        # 启动托盘图标与监控逻辑
        threading.Thread(target=self.setup_tray, daemon=True).start()
        threading.Thread(target=self.run_schedule, daemon=True).start()

    # --- 托盘与显示逻辑 ---
    def create_tray_image(self):
        """加载自定义图标"""
        if os.path.exists(self.icon_file):
            try:
                return Image.open(self.icon_file)
            except: pass
        # 兜底画红块
        image = Image.new('RGB', (64, 64), (255, 36, 66))
        return image

    def setup_tray(self):
        menu = (item('打开主界面', self.show_window), item('彻底退出', self.quit_app))
        self.icon = pystray.Icon("xhs_bot", self.create_tray_image(), "小红书助手运行中", menu)
        self.icon.run()

    def show_window(self):
        self.root.after(0, self.root.deiconify)
        self.root.after(0, self.root.lift)

    def hide_window(self):
        self.root.withdraw()

    def quit_app(self):
        self.icon.stop()
        self.root.quit()
        os._exit(0)

    # --- 配置与自启动逻辑 (避嫌版) ---
    def handle_autostart_click(self):
        """改为提示模式，不再直接修改注册表，防止杀毒软件误报"""
        if self.autostart_var.get():
            msg = "为了您的电脑安全，程序不会强制修改注册表。\n\n" \
                  "如需开机自启动，请点击‘确定’，在弹出的文件夹中：\n" \
                  "1. 右键点击本程序的 EXE 文件选择‘创建快捷方式’\n" \
                  "2. 将该快捷方式剪切并粘贴到刚才打开的文件夹中。"
            messagebox.showinfo("自启动设置指引", msg)
            os.startfile("shell:startup") # 自动打开系统的“启动”文件夹
        self.save_config()

    def load_config(self):
        default = {"h": "08", "m": "00", "title": "今日分享", "caption": "", "tags": "", "image_folder": "", "enable_schedule": False, "autostart": False}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    default.update(json.load(f))
            except: pass
        return default

    def save_config(self):
        self.config.update({
            "h": self.hour_cb.get(), "m": self.min_cb.get(),
            "title": self.title_entry.get(), "caption": self.caption_text.get(1.0, "end-1c"),
            "tags": self.tags_entry.get(), "enable_schedule": bool(self.enable_var.get()),
            "autostart": bool(self.autostart_var.get()),
            "image_folder": self.path_label.cget("text") if self.path_label.cget("text") != "未选择" else ""
        })
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
        self.refresh_timer_ui()

    def log(self, message):
        now = datetime.now().strftime("%H:%M:%S")
        self.root.after(0, lambda: [self.log_box.configure(state='normal'), self.log_box.insert('end', f"[{now}] {message}\n"), self.log_box.see('end'), self.log_box.configure(state='disabled')])

    # --- UI 构造 ---
    def create_widgets(self):
        Frame(self.root, height=10).pack()
        f1 = Frame(self.root); f1.pack(pady=5, padx=20, fill="x")
        Label(f1, text="图片文件夹:").pack(side="left")
        self.path_label = Label(f1, text=self.config.get("image_folder") or "未选择", fg="blue", wraplength=350)
        self.path_label.pack(side="left", padx=10)
        Button(f1, text="浏览", command=self.select_folder).pack(side="right")

        Label(self.root, text="发布标题:").pack(anchor="w", padx=20)
        self.title_entry = Entry(self.root); self.title_entry.pack(padx=20, pady=5, fill="x")
        self.title_entry.insert(0, str(self.config.get("title")))

        Label(self.root, text="详情正文:").pack(anchor="w", padx=20)
        self.caption_text = Text(self.root, height=8); self.caption_text.pack(padx=20, pady=5, fill="x")
        self.caption_text.insert("1.0", str(self.config.get("caption")))

        Label(self.root, text="话题标签 (用逗号分隔):").pack(anchor="w", padx=20)
        self.tags_entry = Entry(self.root); self.tags_entry.pack(padx=20, pady=5, fill="x")
        self.tags_entry.insert(0, str(self.config.get("tags")))

        ctrl_frame = Frame(self.root); ctrl_frame.pack(pady=10, padx=20, fill="x")
        Label(ctrl_frame, text="发布时间:").pack(side="left")
        self.hour_cb = ttk.Combobox(ctrl_frame, values=[f"{i:02d}" for i in range(24)], width=5, state="readonly")
        self.hour_cb.set(self.config.get("h", "08")); self.hour_cb.pack(side="left", padx=2)
        self.min_cb = ttk.Combobox(ctrl_frame, values=[f"{i:02d}" for i in range(60)], width=5, state="readonly")
        self.min_cb.set(self.config.get("m", "00")); self.min_cb.pack(side="left", padx=2)

        chk_frame = Frame(self.root); chk_frame.pack(pady=5, padx=20, fill="x")
        self.enable_var = IntVar(value=1 if self.config.get("enable_schedule") else 0)
        Checkbutton(chk_frame, text="开启自动定时", variable=self.enable_var, command=self.save_config).pack(side="left")
        self.autostart_var = IntVar(value=1 if self.config.get("autostart") else 0)
        Checkbutton(chk_frame, text="开机自启动指引", variable=self.autostart_var, command=self.handle_autostart_click).pack(side="right")

        btn_frame = Frame(self.root); btn_frame.pack(pady=10, padx=20, fill="x")
        Button(btn_frame, text="保存配置", command=self.save_config, height=2).pack(side="left", expand=True, fill="x", padx=5)
        Button(btn_frame, text="立即发布一次", command=self.upload_now, height=2, bg="#ffebee").pack(side="left", expand=True, fill="x", padx=5)

        self.timer_label = Label(self.root, text="状态：待机", font=("微软雅黑", 10, "bold"))
        self.timer_label.pack(pady=5)
        self.log_box = scrolledtext.ScrolledText(self.root, height=12, state='disabled', font=("Consolas", 9))
        self.log_box.pack(padx=20, pady=5, fill="both")

    def refresh_timer_ui(self):
        if self.enable_var.get():
            self.timer_label.config(text=f"● 监控中：目标时间 {self.hour_cb.get()}:{self.min_cb.get()}", fg="#2e7d32")
        else:
            self.timer_label.config(text="○ 定时任务：未开启", fg="gray")

    def upload_process(self):
        folder = self.config.get("image_folder")
        if not folder or not os.path.exists(folder):
            self.log("错误：文件夹路径无效"); return
        imgs = [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not imgs:
            self.log("通知：文件夹内没有可发布的图片"); return
        target_img = os.path.join(folder, sorted(imgs)[0])

        with sync_playwright() as p:
            try:
                self.log(f"任务启动：{os.path.basename(target_img)}")
                context = p.chromium.launch_persistent_context(
                    user_data_dir=self.edge_user_data,
                    executable_path="C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                page = context.pages[0] if context.pages else context.new_page()
                page.goto("https://creator.xiaohongshu.com/publish/publish?source=official&target=image")
                
                if "login" in page.url:
                    self.log("等待扫码登录...")
                    page.wait_for_url("**/publish/**", timeout=0)

                page.locator("input[type='file']").set_input_files(target_img)
                title_box = page.get_by_placeholder("填写标题")
                title_box.wait_for(state="visible", timeout=20000)
                title_box.fill(self.config.get("title"))

                page.keyboard.press("Tab")
                time.sleep(1)
                page.keyboard.type(self.config.get("caption"))
                page.keyboard.press("Enter")
                
                tags = self.config.get("tags", "").replace("，", ",").split(",")
                for tag in tags:
                    t = tag.strip()
                    if t:
                        page.keyboard.type(f"#{t}")
                        time.sleep(1.2)
                        page.keyboard.press("Enter")
                        time.sleep(0.5)
                        page.keyboard.press("Space")
                        time.sleep(0.5)

                btn_ok = False
                for _ in range(60):
                    btn = page.get_by_role("button", name="发布")
                    if btn.count() > 0 and btn.is_enabled():
                        btn.click(); btn_ok = True; break
                    time.sleep(1)
                
                if btn_ok:
                    self.log("成功：发布完成")
                    time.sleep(10)
                    self.move_and_rename_file(target_img)
                context.close()
            except Exception as e:
                self.log(f"发布故障: {str(e)[:50]}")

    def move_and_rename_file(self, file_path):
        try:
            folder_path = os.path.dirname(file_path)
            parent_path = os.path.dirname(folder_path)
            new_name = f"已发布_{datetime.now().strftime('%m%d_%H%M')}{os.path.splitext(file_path)[1]}"
            shutil.move(file_path, os.path.join(parent_path, new_name))
        except: pass

    def select_folder(self):
        path = filedialog.askdirectory()
        if path: self.path_label.config(text=path); self.save_config()

    def upload_now(self):
        self.save_config()
        threading.Thread(target=self.upload_process, daemon=True).start()

    def run_schedule(self):
        self.root.after(100, self.refresh_timer_ui)
        while True:
            if self.enable_var.get():
                now = datetime.now()
                if now.hour == int(self.hour_cb.get()) and now.minute == int(self.min_cb.get()):
                    if not self.has_run_today:
                        self.upload_process()
                        self.has_run_today = True
                        time.sleep(65)
                else:
                    if self.has_run_today: self.has_run_today = False
            time.sleep(1)

# --- 实例锁与入口 ---
if __name__ == "__main__":
    # 使用锁文件防止多开
    lock_file = os.path.join(os.path.expanduser("~"), "xhs_uploader_v1.lock")
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
        except OSError:
            # 弹窗提示
            rt = Tk(); rt.withdraw()
            messagebox.showwarning("运行中", "小红书助手已在后台运行中，请在右下角托盘查找图标。")
            sys.exit(0)
    try:
        f = open(lock_file, 'w')
        f.write("locked")
    except: pass

    root = Tk()
    app = XiaohongshuUploader(root)
    root.mainloop()
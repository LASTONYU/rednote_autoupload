import os
import json
import schedule
import time
import threading
from tkinter import Tk, Label, Button, Entry, Text, filedialog, Checkbutton, IntVar, Frame, messagebox
from datetime import datetime
from PIL import Image
from playwright.sync_api import sync_playwright

class XiaohongshuUploader:
    def __init__(self, root):
        self.root = root
        self.root.title("小红书定时上传工具")
        self.root.geometry("600x500")
        
        # 配置文件路径
        self.config_path = "config.json"
        
        # 加载配置
        self.config = self.load_config()
        
        # 图片文件夹路径
        self.image_folder = self.config.get("image_folder", "")
        
        # 初始化界面
        self.create_widgets()
        
        # 启动定时任务线程
        self.schedule_thread = threading.Thread(target=self.run_schedule)
        self.schedule_thread.daemon = True
        self.schedule_thread.start()
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "upload_time": "08:00",
            "caption": "",
            "tags": "",
            "enable_schedule": False,
            "image_folder": "",
            "current_image_index": 0
        }
    
    def save_config(self):
        """保存配置文件"""
        self.config["upload_time"] = self.time_entry.get()
        self.config["caption"] = self.caption_text.get(1.0, "end-1c")
        self.config["tags"] = self.tags_entry.get()
        self.config["enable_schedule"] = bool(self.enable_var.get())
        self.config["image_folder"] = self.image_folder
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
        
        messagebox.showinfo("提示", "配置已保存")
    
    def create_widgets(self):
        """创建GUI组件"""
        # 图片文件夹选择
        image_frame = Frame(self.root)
        image_frame.pack(pady=10, padx=10, fill="x")
        
        Label(image_frame, text="选择图片文件夹:", font=("Arial", 12)).pack(anchor="w")
        
        image_select_frame = Frame(image_frame)
        image_select_frame.pack(fill="x", pady=5)
        
        self.image_label = Label(image_select_frame, text="未选择文件夹" if not self.image_folder else os.path.basename(self.image_folder))
        self.image_label.pack(side="left", expand=True)
        
        Button(image_select_frame, text="浏览", command=self.select_folder).pack(side="right")
        
        # 文案设置
        caption_frame = Frame(self.root)
        caption_frame.pack(pady=10, padx=10, fill="x")
        
        Label(caption_frame, text="文案:", font=("Arial", 12)).pack(anchor="w")
        self.caption_text = Text(caption_frame, height=5, width=50)
        self.caption_text.insert(1.0, self.config.get("caption", ""))
        self.caption_text.pack(fill="x", pady=5)
        
        # 标签设置
        tags_frame = Frame(self.root)
        tags_frame.pack(pady=10, padx=10, fill="x")
        
        Label(tags_frame, text="标签(用逗号分隔):", font=("Arial", 12)).pack(anchor="w")
        self.tags_entry = Entry(tags_frame, width=50)
        self.tags_entry.insert(0, self.config.get("tags", ""))
        self.tags_entry.pack(fill="x", pady=5)
        
        # 定时设置
        schedule_frame = Frame(self.root)
        schedule_frame.pack(pady=10, padx=10, fill="x")
        
        Label(schedule_frame, text="定时设置:", font=("Arial", 12)).pack(anchor="w")
        
        time_select_frame = Frame(schedule_frame)
        time_select_frame.pack(fill="x", pady=5)
        
        Label(time_select_frame, text="每天上传时间: HH:MM").pack(side="left")
        self.time_entry = Entry(time_select_frame, width=10)
        self.time_entry.insert(0, self.config.get("upload_time", "08:00"))
        self.time_entry.pack(side="left", padx=10)
        
        self.enable_var = IntVar(value=self.config.get("enable_schedule", False))
        Checkbutton(time_select_frame, text="启用定时上传", variable=self.enable_var).pack(side="right")
        
        # 操作按钮
        button_frame = Frame(self.root)
        button_frame.pack(pady=20, padx=10, fill="x")
        
        Button(button_frame, text="立即上传", command=self.upload_now, width=15).pack(side="left", padx=10)
        Button(button_frame, text="保存配置", command=self.save_config, width=15).pack(side="left", padx=10)
        Button(button_frame, text="退出", command=self.root.quit, width=15).pack(side="right", padx=10)
        
        # 状态显示
        self.status_label = Label(self.root, text="当前状态: 就绪", font=("Arial", 10), fg="gray")
        self.status_label.pack(pady=10)
    
    def select_folder(self):
        """选择图片文件夹"""
        folder_path = filedialog.askdirectory(
            title="选择图片文件夹"
        )
        if folder_path:
            self.image_folder = folder_path
            self.image_label.config(text=os.path.basename(folder_path))
    
    def get_image_list(self):
        """获取文件夹中的图片列表"""
        if not self.image_folder or not os.path.exists(self.image_folder):
            return []
        
        # 支持的图片格式
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif']
        image_list = []
        
        # 遍历文件夹中的文件，筛选出图片
        for file in os.listdir(self.image_folder):
            file_path = os.path.join(self.image_folder, file)
            if os.path.isfile(file_path):
                ext = os.path.splitext(file)[1].lower()
                if ext in image_extensions:
                    image_list.append(file_path)
        
        # 按文件名排序
        image_list.sort()
        return image_list
    
    def get_next_image(self):
        """获取下一张要上传的图片"""
        image_list = self.get_image_list()
        if not image_list:
            return None
        
        # 获取当前图片索引，默认为0
        current_index = self.config.get("current_image_index", 0)
        
        # 如果索引超出范围，重置为0
        if current_index >= len(image_list):
            current_index = 0
        
        # 获取当前图片
        image_path = image_list[current_index]
        
        # 更新索引，准备下次上传
        current_index += 1
        self.config["current_image_index"] = current_index
        
        # 保存更新后的索引
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
        
        return image_path
    
    def upload_image(self):
        """使用浏览器自动化上传图片到小红书"""
        # 获取下一张要上传的图片
        image_path = self.get_next_image()
        if not image_path:
            self.status_label.config(text="当前状态: 错误 - 未选择图片文件夹或文件夹中没有图片", fg="red")
            return False
        
        try:
            self.status_label.config(text="当前状态: 正在启动浏览器...", fg="blue")
            
            with sync_playwright() as p:
                # 启动Edge浏览器，使用用户系统默认的Edge数据目录，继承登录状态
                try:
                    # 使用系统默认的Edge浏览器数据目录，这样可以继承用户已有的登录状态
                    self.status_label.config(text="当前状态: 正在启动Edge浏览器...", fg="blue")
                    
                    # 获取Edge浏览器的默认用户数据目录
                    edge_user_data_dir = os.path.join(os.environ['LOCALAPPDATA'], 'Microsoft', 'Edge', 'User Data')
                    self.status_label.config(text=f"当前状态: 使用Edge数据目录 - {edge_user_data_dir}", fg="blue")
                    
                    # 检查Edge数据目录是否存在
                    if not os.path.exists(edge_user_data_dir):
                        self.status_label.config(text=f"当前状态: Edge数据目录不存在 - {edge_user_data_dir}", fg="orange")
                        # 使用另一种方式获取Edge路径
                        import subprocess
                        try:
                            # 尝试从注册表获取Edge的安装路径
                            import winreg
                            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Edge\Application") as key:
                                edge_path = winreg.QueryValueEx(key, "LauncherExePath")[0]
                            self.status_label.config(text=f"当前状态: 从注册表获取Edge路径 - {edge_path}", fg="blue")
                        except Exception as e:
                            self.status_label.config(text=f"当前状态: 无法从注册表获取Edge路径 - {str(e)}", fg="orange")
                    
                    # 尝试使用不同的启动策略
                    try:
                        # 策略1: 尝试使用p.chromium.launch_persistent_context与channel="msedge"，但不使用user_data_dir
                        # 这样会创建一个新的Edge配置文件，用户需要登录一次，但后续会保持登录状态
                        self.status_label.config(text="当前状态: 尝试使用新的Edge配置文件...", fg="blue")
                        
                        # 创建一个专用的数据目录
                        edge_custom_data_dir = os.path.join(os.path.expanduser("~"), ".xiaohongshu_uploader_edge")
                        os.makedirs(edge_custom_data_dir, exist_ok=True)
                        
                        context = p.chromium.launch_persistent_context(
                            user_data_dir=edge_custom_data_dir,
                            headless=False,
                            slow_mo=500,
                            channel="msedge",
                            viewport=None,
                            args=[
                                "--start-maximized",
                                "--disable-blink-features=AutomationControlled",
                                "--disable-popup-blocking",
                                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
                            ],
                            permissions=["clipboard-read", "clipboard-write"],
                            bypass_csp=True,
                            accept_downloads=True,
                            java_script_enabled=True
                        )
                        self.status_label.config(text="当前状态: 成功使用新的Edge配置文件", fg="green")
                    except Exception as e:
                        # 策略1失败，尝试策略2: 直接使用p.chromium.launch，不使用persistent context
                        self.status_label.config(text=f"当前状态: 尝试策略1失败，使用策略2: 直接启动Edge... {str(e)}", fg="orange")
                        
                        browser = p.edge.launch(
                            headless=False,
                            slow_mo=500,
                            channel="msedge",
                            args=[
                                "--start-maximized",
                                "--disable-blink-features=AutomationControlled",
                                "--disable-popup-blocking"
                            ]
                        )
                        context = browser.new_context()
                        self.status_label.config(text="当前状态: 成功直接启动Edge浏览器", fg="green")
                    
                    # 获取当前页面，如果没有则创建新页面
                    if context.pages:
                        page = context.pages[0]
                    else:
                        page = context.new_page()
                    
                    # 关闭其他可能打开的页面
                    for extra_page in context.pages[1:]:
                        extra_page.close()
                        
                except Exception as e:
                    # 如果Edge浏览器不可用，记录详细错误信息
                    error_msg = f"Edge启动失败: {str(e)}"
                    self.status_label.config(text=f"当前状态: {error_msg}", fg="red")
                    
                    # 保存错误日志到文件，便于调试
                    with open("xiaohongshu_edge_error.log", "w", encoding="utf-8") as f:
                        f.write(f"Edge启动失败: {str(e)}\n")
                        f.write(f"Edge数据目录: {edge_user_data_dir}\n")
                        f.write(f"数据目录存在: {os.path.exists(edge_user_data_dir)}\n")
                        
                        # 尝试获取更多系统信息
                        import platform
                        f.write(f"操作系统: {platform.system()} {platform.release()}\n")
                        f.write(f"Python版本: {platform.python_version()}\n")
                    
                    # 弹出对话框提示用户
                    import tkinter.messagebox
                    tkinter.messagebox.showerror("Edge浏览器启动失败", 
                                               f"无法启动Edge浏览器: {str(e)}\n\n"+
                                               f"Edge数据目录: {edge_user_data_dir}\n"+
                                               f"数据目录存在: {os.path.exists(edge_user_data_dir)}\n\n"+
                                               "请检查Edge浏览器是否正确安装，或尝试手动登录后再运行程序。")
                    
                    # 仍然尝试使用chromium，但让用户知道
                    self.status_label.config(text="当前状态: 正在尝试使用Chrome浏览器...", fg="orange")
                    
                    # 使用chromium的persistent context
                    user_data_dir = os.path.join(os.path.expanduser("~"), ".xiaohongshu_uploader_chromium")
                    os.makedirs(user_data_dir, exist_ok=True)
                    
                    context = p.chromium.launch_persistent_context(
                        user_data_dir=user_data_dir,
                        headless=False, 
                        slow_mo=500,
                        viewport=None,
                        args=[
                            "--start-maximized",
                            "--disable-blink-features=AutomationControlled",
                            "--disable-popup-blocking"
                        ]
                    )
                    self.status_label.config(text="当前状态: 已启动Chrome浏览器，建议使用Edge浏览器以获得最佳体验", fg="orange")
                    
                    if context.pages:
                        page = context.pages[0]
                    else:
                        page = context.new_page()
                    
                    for extra_page in context.pages[1:]:
                        extra_page.close()
                
                try:
                    # 1. 直接访问用户提供的图文上传页面URL
                    user_specified_url = "https://creator.xiaohongshu.com/publish/publish?source=official&from=menu&target=image"
                    self.status_label.config(text=f"当前状态: 正在访问用户指定的图文上传页面 {user_specified_url}...", fg="blue")
                    
                    # 访问图文上传页面
                    page.goto(user_specified_url, wait_until="networkidle")
                    page.wait_for_timeout(5000)  # 等待页面完全加载
                    
                    # 显示当前页面信息，用于调试
                    self.status_label.config(text=f"当前状态: 已进入 {page.title()} - {page.url}", fg="blue")
                    
                    # 等待页面完全加载，确保所有元素都已渲染
                    self.status_label.config(text="当前状态: 等待页面元素加载完成...", fg="blue")
                    page.wait_for_timeout(5000)
                    
                    # 2. 直接寻找上传元素，不进行复杂的发布按钮点击和页面导航
                    self.status_label.config(text="当前状态: 正在寻找上传元素...", fg="blue")
                    
                    # 定义上传元素选择器，优先使用最可靠的文件输入框
                    upload_selectors = [
                        # 文件输入框（最可靠）
                        "input[type='file']",
                        "//input[@type='file']",
                        
                        # 上传按钮
                        ".upload-btn",
                        "[class*='upload']",
                        "button:has-text('上传')",
                        "//button[contains(text(), '上传')]",
                        
                        # 图片选择区域
                        "[class*='image-upload']",
                        "[class*='photo-upload']",
                        "//div[contains(@class, 'image-upload')]",
                        
                        # 编辑器容器
                        ".editor-container",
                        "[class*='editor']",
                        
                        # 拖放区域
                        ".drop-zone",
                        "[class*='drop']",
                        "[data-role*='drop']"
                    ]
                    
                    upload_ready = False
                    upload_element = None
                    
                    # 遍历所有上传选择器，寻找可用的上传元素
                    for selector in upload_selectors:
                        try:
                            self.status_label.config(text=f"当前状态: 正在尝试使用选择器 {selector} 寻找上传元素...", fg="blue")
                            elements = page.locator(selector).all()
                            
                            if elements:
                                for elem in elements:
                                    try:
                                        # 检查元素是否可用
                                        if elem.is_visible() or "input" in selector:
                                            upload_ready = True
                                            upload_element = elem
                                            self.status_label.config(text=f"当前状态: 找到上传元素 - {selector}", fg="green")
                                            break
                                    except Exception:
                                        continue
                                if upload_ready:
                                    break
                        except Exception as e:
                            self.status_label.config(text=f"当前状态: 使用选择器 {selector} 查找失败 - {str(e)}", fg="orange")
                    
                    # 如果找不到上传元素，尝试滚动页面寻找
                    if not upload_ready:
                        self.status_label.config(text="当前状态: 正在滚动页面寻找上传区域...", fg="blue")
                        
                        # 滚动页面，寻找可能在下方的上传区域
                        for _ in range(5):
                            page.mouse.wheel(0, 100)  # 向下滚动
                            page.wait_for_timeout(1000)
                            
                            for selector in upload_selectors:
                                try:
                                    elements = page.locator(selector).all()
                                    if elements:
                                        for elem in elements:
                                            if elem.is_visible() or "input" in selector:
                                                upload_ready = True
                                                upload_element = elem
                                                self.status_label.config(text=f"当前状态: 找到上传元素 - {selector}", fg="green")
                                                break
                                        if upload_ready:
                                            break
                                except Exception:
                                    continue
                            if upload_ready:
                                break
                    
                    if not upload_ready:
                        # 保存调试信息
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        screenshot_path = f"xiaohongshu_debug_{timestamp}.png"
                        page.screenshot(path=screenshot_path, full_page=True)
                        
                        html_path = f"xiaohongshu_debug_{timestamp}.html"
                        with open(html_path, "w", encoding="utf-8") as f:
                            f.write(page.content())
                        
                        self.status_label.config(text=f"当前状态: 上传失败 - 无法找到上传元素，截图和HTML已保存到 {screenshot_path} 和 {html_path}", fg="red")
                        raise Exception(f"无法找到上传元素，当前页面: {page.title()} - {page.url}")
                    
                    self.status_label.config(text="当前状态: 发布页面已准备就绪...", fg="green")
                    
                    # 3. 直接上传图片
                    self.status_label.config(text="当前状态: 正在上传图片...", fg="blue")
                    
                    # 优先使用input[type='file']选择器，因为它最可靠
                    try:
                        upload_input = page.locator("input[type='file']").first
                        upload_input.set_input_files(image_path)
                    except Exception as e:
                        # 如果直接使用input[type='file']失败，尝试点击上传元素
                        self.status_label.config(text=f"当前状态: 尝试直接点击上传元素... {str(e)}", fg="blue")
                        upload_element.click()
                        page.wait_for_timeout(2000)
                        
                        # 再次尝试找到文件输入框
                        upload_input = page.locator("input[type='file']").first
                        upload_input.set_input_files(image_path)
                    
                    # 6. 等待图片上传完成
                    page.wait_for_timeout(5000)  # 等待5秒让图片上传
                    
                    # 7. 输入文案
                    self.status_label.config(text="当前状态: 正在输入文案...", fg="blue")
                    caption = self.caption_text.get(1.0, "end-1c")
                    if caption:
                        # 尝试多种不同的文案编辑器定位器，特别针对小红书发布页面
                        caption_selectors = [
                            # 小红书发布页面的正文内容输入框
                            "textarea[placeholder*='正文内容']",
                            "textarea[placeholder*='输入正文']",
                            "input[placeholder*='正文内容']",
                            "input[placeholder*='输入正文']",
                            
                            # 通用文本输入框
                            "textarea",
                            "input[type='text']",
                            
                            # 基于类名的定位器
                            ".content-input",
                            ".note-content",
                            ".post-content",
                            "[class*='input']",
                            "[class*='textarea']",
                            
                            # 基于内容可编辑的元素
                            "[contenteditable='true']",
                            "//div[@contenteditable='true']",
                            
                            # 旧的编辑器容器
                            ".editor-container",
                            ".note-editor",
                            ".content-editor",
                            ".post-editor"
                        ]
                        
                        caption_editor_found = False
                        for selector in caption_selectors:
                            try:
                                self.status_label.config(text=f"当前状态: 尝试使用定位器 {selector} 查找文案编辑器...", fg="blue")
                                
                                # 尝试查找元素并选择第一个匹配项
                                editors = page.locator(selector).all()
                                if editors:
                                    # 选择第一个可见且可交互的编辑器
                                    for editor in editors:
                                        if editor.is_visible() and editor.is_enabled():
                                            # 滚动到元素位置
                                            editor.scroll_into_view_if_needed()
                                            # 清空现有内容（如果需要）
                                            editor.clear()
                                            # 输入文案内容
                                            editor.fill(caption)
                                            self.status_label.config(text=f"当前状态: 已成功输入文案 - {selector}", fg="green")
                                            caption_editor_found = True
                                            break
                                    if caption_editor_found:
                                        break
                            except Exception as e:
                                self.status_label.config(text=f"当前状态: 定位器 {selector} 失败 - {str(e)}", fg="orange")
                                continue
                        
                        if not caption_editor_found:
                            self.status_label.config(text="当前状态: 无法找到文案编辑器，跳过文案输入", fg="orange")
                    
                    # 8. 输入标签
                    self.status_label.config(text="当前状态: 正在处理标签...", fg="blue")
                    tags = self.tags_entry.get()
                    if tags:
                        # 尝试多种不同的标签输入框定位器
                        tag_selectors = [
                            "input[placeholder*='添加标签']",
                            "input[placeholder*='标签']",
                            "textarea[placeholder*='标签']",
                            "[class*='tag-input']",
                            "[data-role*='tag']",
                            "//input[contains(@class, 'tag')]",
                            "//div[contains(@class, 'tag')]//input"
                        ]
                        
                        tag_input_found = False
                        for selector in tag_selectors:
                            try:
                                tag_input = page.locator(selector).first
                                if tag_input.is_visible() and tag_input.is_enabled():
                                    # 滚动到元素位置
                                    tag_input.scroll_into_view_if_needed()
                                    # 输入标签，使用逗号分隔
                                    tag_input.fill(tags)
                                    # 按回车键确认标签
                                    tag_input.press("Enter")
                                    self.status_label.config(text=f"当前状态: 已成功输入标签 - {selector}", fg="green")
                                    tag_input_found = True
                                    break
                            except Exception as e:
                                self.status_label.config(text=f"当前状态: 标签定位器 {selector} 失败 - {str(e)}", fg="orange")
                                continue
                        
                        if not tag_input_found:
                            self.status_label.config(text="当前状态: 无法找到标签输入框，跳过标签输入", fg="orange")
                    
                    # 9. 点击发布按钮
                    self.status_label.config(text="当前状态: 正在寻找并点击发布按钮...", fg="blue")
                    
                    # 定义发布按钮选择器
                    publish_button_selectors = [
                        "button:has-text('发布')",
                        "button:has-text('立即发布')",
                        "button:has-text('确认发布')",
                        "//button[contains(text(), '发布')]",
                        "[class*='publish-btn']",
                        "[class*='submit-btn']",
                        "#publish-button",
                        ".publish-button",
                        "[data-role*='publish']"
                    ]
                    
                    publish_button_found = False
                    for selector in publish_button_selectors:
                        try:
                            publish_button = page.locator(selector).first
                            if publish_button.is_visible() and publish_button.is_enabled():
                                # 滚动到发布按钮位置
                                publish_button.scroll_into_view_if_needed()
                                # 点击发布按钮
                                publish_button.click()
                                self.status_label.config(text=f"当前状态: 已成功点击发布按钮 - {selector}", fg="green")
                                publish_button_found = True
                                break
                        except Exception as e:
                            self.status_label.config(text=f"当前状态: 发布按钮定位器 {selector} 失败 - {str(e)}", fg="orange")
                            continue
                    
                    if not publish_button_found:
                        self.status_label.config(text="当前状态: 无法找到发布按钮，请手动点击发布", fg="orange")
                        # 等待用户手动点击发布
                        page.wait_for_timeout(60000)  # 等待60秒
                    else:
                        # 等待发布完成
                        page.wait_for_timeout(10000)  # 等待10秒让发布完成
                    
                    # 移动上传成功的图片到上一级文件夹
                    self.status_label.config(text="当前状态: 正在将上传的图片移动到上一级文件夹...", fg="blue")
                    try:
                        # 获取当前图片文件夹的上一级文件夹路径
                        parent_folder = os.path.dirname(self.image_folder)
                        if not os.path.exists(parent_folder):
                            # 如果上一级文件夹不存在，创建它
                            os.makedirs(parent_folder)
                        
                        # 获取图片文件名
                        image_filename = os.path.basename(image_path)
                        # 构建目标路径
                        destination_path = os.path.join(parent_folder, image_filename)
                        
                        # 检查目标文件是否已存在，如果存在则添加时间戳避免覆盖
                        if os.path.exists(destination_path):
                            # 添加时间戳到文件名
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            name, ext = os.path.splitext(image_filename)
                            unique_filename = f"{name}_{timestamp}{ext}"
                            destination_path = os.path.join(parent_folder, unique_filename)
                        
                        # 移动文件
                        os.rename(image_path, destination_path)
                        self.status_label.config(text=f"当前状态: 图片上传成功，并已移动到 {parent_folder}！", fg="green")
                    except Exception as e:
                        self.status_label.config(text=f"当前状态: 图片上传成功，但移动到上一级文件夹失败: {str(e)}", fg="orange")
                    
                    # 自动退出逻辑：如果是定时任务触发的上传，上传完成后自动退出
                    if hasattr(self, 'is_scheduled_upload') and self.is_scheduled_upload:
                        self.status_label.config(text="当前状态: 上传完成，程序将在3秒后自动退出...", fg="green")
                        # 等待3秒让用户看到状态信息
                        page.wait_for_timeout(3000)
                        # 关闭浏览器
                        context.close()
                        # 退出程序
                        self.root.quit()
                    
                    return True
                except Exception as e:
                    error_msg = f"上传失败: {str(e)}"
                    self.status_label.config(text=f"当前状态: {error_msg}", fg="red")
                    
                    # 保存错误日志到文件，便于调试
                    with open("xiaohongshu_upload_error.log", "w", encoding="utf-8") as f:
                        f.write(f"上传失败: {str(e)}\n")
                        f.write(f"当前页面: {page.title()} - {page.url}\n")
                        f.write(f"图片路径: {image_path}\n")
                        f.write(f"上传时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    
                    return False
        except Exception as e:
            error_msg = f"上传失败: {str(e)}"
            self.status_label.config(text=f"当前状态: {error_msg}", fg="red")
            return False
    
    def upload_now(self):
        """立即上传图片"""
        self.save_config()  # 保存当前配置
        threading.Thread(target=self.upload_image).start()
    
    def run_schedule(self):
        """运行定时任务"""
        while True:
            # 检查是否启用了定时上传
            if self.config.get("enable_schedule", False):
                current_time = datetime.now().strftime("%H:%M")
                upload_time = self.config.get("upload_time", "08:00")
                
                if current_time == upload_time:
                    # 设置标志，表明这是定时任务触发的上传
                    self.is_scheduled_upload = True
                    self.upload_image()
                    # 等待1分钟，避免重复执行
                    time.sleep(60)
            
            # 每分钟检查一次
            time.sleep(60)

if __name__ == "__main__":
    root = Tk()
    app = XiaohongshuUploader(root)
    root.mainloop()
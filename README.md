# 小红书图片一键发布助手 (Edge 驱动版)

这是一个基于 Python 和 Playwright 开发的自动化工具，旨在帮助创作者通过桌面端快速、定时地发布小红书图文内容。

## ✨ 功能特点

- **现代化界面**：采用 CustomTkinter 构建的深色模式 UI，简洁美观。
- **智能环境适配**：自动扫描系统中的 Microsoft Edge 浏览器，无需手动安装浏览器内核。
- **定时发布**：支持设定每日固定时间自动检测并发布内容。
- **文件自动管理**：发布成功后自动重命名图片，防止重复发布。
- **托盘运行**：支持最小化到系统托盘，不占用任务栏空间。

## 🛠️ 开发环境

项目使用 [Pixi](https://pixi.sh/) 进行包管理。

### 安装依赖
```bash
pixi install

### 运行程序
Bash
pixi run python xiaohongshu_uploader.py

### 编译打包 (Windows)
Bash
pixi run pyinstaller --noconsole --onefile --clean \
--collect-all customtkinter \
--hidden-import "pystray._win32" \
--icon="logo.ico" \
--add-data "logo.png;." \
--name "小红书发布助手" xiaohongshu_uploader.py
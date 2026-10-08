# Diffusion Studio 简体中文版 (Windows)

基于官方 [diffusionstudio/editor](https://github.com/diffusionstudio/editor) v0.209.1
Windows x64 制作的简体中文版。

## 下载

到 [Releases](../../releases) 页面下载
`Diffusion-Studio-v0.209.1-zh-CN-x64-Setup.exe`，中文安装向导，
带开始菜单、可选桌面快捷方式、卸载程序。

## 汉化内容

- 主界面菜单、工具栏、面板、时间线、字幕、导出等全部 UI 文案
- 主进程原生对话框（选择项目文件夹、云同步目录警告等）
- 新建默认命名：组 / 场景 / 序列 / 图层

## 与官方版的区别

- 已关闭官方自动更新，避免中文版被英文版覆盖。如需更新请手动下载新版本。
- 其余与官方版本一致。

## 构建方式

本仓库只存放汉化脚本与安装脚本，不存放官方程序文件。
GitHub Actions 在 Windows 上自动完成：下载官方安装包 → 解包 →
运行 `work/apply_zh.py` 汉化 → Inno Setup 打包 → 发布到 Release。

```text
work/apply_zh.py      汉化补丁脚本（字符串扫描 + 安全替换）
work/dict_zh.json     英→简体中文词典（1152 条）
installer/diffusion-studio-zh.iss   Inno Setup 脚本（中文向导）
```

# Tauri 系统托盘设计

> 日期: 2026-08-10
> 状态: 已批准
> 父文档: `docs/superpowers/specs/2026-08-05-tauri-react-fastapi-architecture-design.md`

## 1. 目标

为 LLM Router 桌面应用添加系统托盘功能，实现：
- 关闭窗口时最小化到托盘（而非退出应用）
- 通过托盘菜单恢复窗口或退出
- 退出时正确清理 Python 后端进程

## 2. 行为定义

| 事件 | 行为 |
|------|------|
| 启动应用 | 显示主窗口（1280×800），同时显示托盘图标 |
| 点击窗口 ✕ | 窗口隐藏，应用继续在后台运行 |
| 任务栏点击图标 | 呼出已隐藏的窗口 |
| 双击托盘图标 | 显示/恢复窗口 |
| 托盘右键 → "显示窗口" | 显示/恢复窗口 |
| 托盘右键 → "退出" | 清理 Python 后端 → 退出应用 |

## 3. 技术方案

### 3.1 依赖

- `tauri-plugin-tray` — Tauri 2 官方托盘插件

### 3.2 托盘菜单结构

```
显示窗口
─────────
退出
```

### 3.3 关键实现

**窗口关闭拦截**: 在 `on_window_event` 中捕获 `CloseRequested` 事件，调用 `prevent_close()` 阻止销毁，然后 `hide()` 隐藏窗口。

**退出流程**: 托盘菜单"退出" → `app.exit(0)` → 现有 `Destroyed` 事件处理逻辑触发 `kill_backend()`。

**图标**: 复用现有 `src-tauri/icons/icon.ico`（多尺寸：16/32/48/256）。

### 3.4 文件修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src-tauri/Cargo.toml` | 修改 | 添加 `tauri-plugin-tray` 依赖 |
| `src-tauri/tauri.conf.json` | 修改 | 添加 `trayIcon` 配置 |
| `src-tauri/src/lib.rs` | 修改 | `.setup()` 中初始化托盘 + 修改窗口关闭事件 |

## 4. 与现有逻辑的兼容

- `#![windows_subsystem = "windows"]` 保持不变（隐藏 CMD 窗口）
- `PythonBackend` 生命周期管理不变（`Destroyed` 事件触发 `kill_backend`）
- 退出时 tray 菜单调用 `app.exit(0)` 自然触发 `Destroyed`，后端清理逻辑无需改动

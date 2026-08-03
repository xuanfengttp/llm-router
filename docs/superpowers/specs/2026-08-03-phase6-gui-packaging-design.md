# Phase 6: GUI 管理面板 + 运行载体 设计规格

> 创建日期：2026-08-03

**目标：** 构建 NiceGUI 可视化管理面板和 PyInstaller 打包方案——5 个功能页面 + 系统托盘 + 单文件 exe。

**架构：** NiceGUI 内嵌 Web 服务器直接调用后端 Python 模块（同进程，无 API 层），pystray 系统托盘并行运行。

**技术栈：** NiceGUI + ECharts CDN + pystray + PyInstaller

---

## 1. 文件结构

```
src/gui/
├── __init__.py
├── app.py              # NiceGUI app 入口 + 页面路由
├── pages/
│   ├── __init__.py
│   ├── config_page.py      # 连接配置页
│   ├── dashboard.py        # 监控仪表板
│   ├── tasks_page.py       # 任务管理页
│   ├── settings_page.py    # 设置页
│   └── logs_page.py        # 日志/审计页
├── tray.py             # pystray 系统托盘
└── launch.py           # 启动入口：GUI + 后端服务 + 托盘

main.py                 # 项目根入口：python main.py
llm_router.spec         # PyInstaller spec 文件
```

---

## 2. 页面功能

### 2.1 连接配置页 (config_page.py)

- Provider/模型列表展示（从 ConfigManager 读取）
- 添加/编辑/删除 Provider（调用 ConfigManager）
- 连通性测试按钮 → 实时显示延迟
- 模型 CRUD（添加/删除模型到 Provider）

### 2.2 监控仪表板 (dashboard.py)

- ECharts 折线图：延迟曲线（最近 N 条记录）
- 预测面板：p50/p90 预测值 + 可预测性评分
- Provider 状态指示灯（绿/黄/红）
- 定时刷新（5s 间隔）

### 2.3 任务管理页 (tasks_page.py)

- 三列队列：待分发 / 执行中 / 失败+暂停
- 新建任务：输入 prompt + 选择模型
- 自动模式开关
- 分发日志（最近 20 条操作记录）

### 2.4 设置页 (settings_page.py)

- 路由策略切换（baseline/cost_first/quality_first/latency_aware/task_specific）
- 时间窗口配置（工作日夜间/周末/白天）
- 延迟红线 + 可预测性阈值
- 模型评分拉取频率

### 2.5 日志页 (logs_page.py)

- 审计日志表格（来自 AuditLog）
- 任务操作日志：分发/重试/失败/成功
- 模型切换记录

---

## 3. 系统托盘 (tray.py)

- pystray 图标（用文本/简单图标）
- 右键菜单：显示窗口 / 切换自动模式 / 退出
- 鼠标悬停提示：当前活跃任务数 + 整体状态
- 点击左键：显示窗口

---

## 4. 启动流程 (launch.py / main.py)

```python
# main.py
import asyncio
from src.gui.launch import run

asyncio.run(run())
```

`launch.run()` 流程：
1. 加载配置
2. 可选启动后端服务（监控、预测、控制器）——通过命令行参数控制
3. 启动 NiceGUI（内嵌浏览器或指定端口）
4. 启动系统托盘

---

## 5. 打包方案

- PyInstaller，单文件模式
- 入口：`main.py`
- Hidden imports：nicegui、pystray、aiosqlite、yaml、cryptography、jsonschema
- 目标 < 120MB
- Rust 监控模块暂不包含（Rust 编译在 Phase 2 计划中但未实现——当前监控用 Python aiohttp）

---

## 6. 全局约束

- 所有新文件 `from __future__ import annotations`
- GUI 层不做业务逻辑——只调用已有模块的 public API
- 所有 GUI 组件为无状态函数式（输入数据 → 渲染）
- NiceGUI 使用 `ui.run()` 内嵌模式（native=True 或 port=指定端口）
- 打包 spec 列入 .gitignore 排除项生成文件

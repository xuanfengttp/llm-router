# LLM Router 架构设计报告

> 本文档描述 LLM Router v2.0 的系统架构，包含从 NiceGUI 单体架构迁移到 Tauri + React + FastAPI 三层架构的完整设计。

**日期：** 2026-08-05
**版本：** 2.0.0
**前一版本：** v1.x（NiceGUI 单体 GUI，见 `docs/superpowers/specs/2026-07-31-llm-router-design.md`）

---

## 1. 概述

LLM Router 是一个智能 Agent 任务调度与 LLM 路由控制系统。它管理多个 LLM 提供商（OpenAI、Anthropic、Google 等），通过延迟探测、预测引擎和路由策略将任务调度到最优模型。

### 1.1 迁移动机

| 维度 | v1.x (NiceGUI) | v2.x (Tauri+React+FastAPI) |
|------|----------------|---------------------------|
| 架构 | Python 单体（GUI + 业务混合） | 三层分离（桌面/前端/后端） |
| UI 框架 | NiceGUI（Python → HTML 翻译层） | React + shadcn/ui（原生 Web 组件） |
| 桌面能力 | PyInstaller + pystray | Tauri 2（Rust 原生窗口 + 系统托盘） |
| 图表 | NiceGUI 内置 | ECharts 6（原生 JS，高性能） |
| 类型安全 | 无 | TypeScript（前端）+ Pydantic v2（后端） |
| 开发体验 | Python 全栈，UI 调试困难 | 前后端分离，独立调试，热更新 |
| 打包体积 | ~200MB（含 Python 运行时） | ~10MB（Tauri shell）+ ~50MB（Python sidecar） |

### 1.2 设计目标

1. **关注点分离**：展示层（React）、API 层（FastAPI）、业务逻辑（Python modules）各自独立
2. **类型安全**：前后端接口通过 Pydantic 模型和 TypeScript 接口对齐
3. **可测试性**：每个层独立可测（API 测试、前端构建验证、Rust 类型检查）
4. **安全打包**：Tauri 作为原生桌面壳，Python 作为 sidecar 子进程

---

## 2. 系统架构

### 2.1 三层架构图

```
┌─────────────────────────────────────────────────┐
│                   Tauri 2 (Rust)                  │
│  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  WebView 窗口 │  │  子进程管理 (Sidecar)     │  │
│  │  (React SPA) │  │  - spawn Python backend   │  │
│  │              │  │  - health check 轮询      │  │
│  │              │  │  - 窗口关闭 → kill 子进程  │  │
│  └──────────────┘  └───────────┬──────────────┘  │
└─────────────────────────────────┼─────────────────┘
                                  │ spawn
┌─────────────────────────────────▼─────────────────┐
│              Python FastAPI (:19876)               │
│  ┌───────────┐ ┌───────────┐ ┌──────────────────┐ │
│  │ Config API│ │Dashboard  │ │ Tasks / Settings │ │
│  │ Provider  │ │  REST+WS  │ │      API         │ │
│  │ Model CRUD│ │ Probe+延迟│ │                  │ │
│  └───────────┘ └───────────┘ └──────────────────┘ │
│  ┌──────────────────────────────────────────────┐  │
│  │            CORS 中间件 + Lifespan             │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────┬─────────────────────────┘
                          │ SQLite
┌─────────────────────────▼─────────────────────────┐
│               业务逻辑模块 (src/)                    │
│  config │ controller │ guard │ monitor │ network   │
│  prediction │ routing │ scoring │ a2a              │
└───────────────────────────────────────────────────┘
```

### 2.2 数据流

```
用户操作 → React SPA
              │ fetch('/api/...')
              ▼
         FastAPI REST API
              │
              ▼
         ConfigManager / Controller / Probe
              │
              ▼
         SQLite (router_state.db + providers.yaml)
```

### 2.3 WebSocket 实时数据流

```
定时探测 (30s) ──────────────────────┐
                                    ▼
React useWebSocket ←─ FastAPI WS endpoint (/api/ws/dashboard)
     │                          ▲
     │  subscribe({providers})  │
     └──────────────────────────┘
```

---

## 3. 组件设计

### 3.1 Tauri 桌面壳

**文件：** `src-tauri/src/lib.rs`、`src-tauri/src/main.rs`

- **子进程启动**：`Command::new("python").args(["-m", "uvicorn", "backend.src.server:app", ...])`
- **生命周期**：窗口创建时 spawn，`WindowEvent::Destroyed` 时 kill
- **CSP 策略**：`script-src 'self' 'unsafe-inline'; connect-src 'self' http://localhost:19876 ws://localhost:19876`
- **错误处理**：通过 `eprintln!` 输出诊断信息到控制台

### 3.2 FastAPI 后端

**入口：** `backend/src/server.py`
**引导：** `backend/src/bootstrap.py`

| 端点 | 方法 | 功能 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/providers` | GET/POST | 提供商列表/创建 |
| `/api/providers/{name}` | DELETE | 删除提供商 |
| `/api/providers/{name}/api-key` | PUT | 更新 API Key |
| `/api/providers/{name}/models` | POST/DELETE | 模型添加/删除 |
| `/api/dashboard/status` | GET | 仪表板状态 |
| `/api/dashboard/probe` | POST | 触发延迟探测 |
| `/api/dashboard/latency` | GET | 查询历史延迟 |
| `/api/ws/dashboard` | WebSocket | 实时延迟推送 |
| `/api/tasks` | GET/POST | 任务列表/创建 |
| `/api/tasks/{id}/cancel` | POST | 取消任务 |
| `/api/tasks/{id}/retry` | POST | 重试任务 |
| `/api/settings` | GET/PUT | 设置读写 |

### 3.3 React 前端

**5 个业务页面：**

| 页面 | 路由 | 功能 |
|------|------|------|
| Dashboard | `/` | ECharts 延迟图表（K 线/折线切换）、WebSocket 实时更新、KPI 统计卡、模型延迟表 |
| Config | `/config` | Provider 侧边栏（预置 8 种）、Provider 详情面板、模型 CRUD 表格、API Key 管理 |
| Tasks | `/tasks` | 任务创建表单（prompt + 目标模型）、任务列表（状态彩色标记）、取消/重试按钮 |
| Logs | `/logs` | 三个标签页（操作/模型切换/审计）、模拟日志表格 |
| Settings | `/settings` | 6 个设置面板（策略/参数/时间/外观/数据/关于）、侧边栏导航 |

**状态管理：** Zustand store（providers、selectedModels、latencyCache、settings、theme）

---

## 4. 安全设计

| 层次 | 措施 |
|------|------|
| CSP | `src-tauri/tauri.conf.json` 中配置，限制脚本/样式/连接的来源 |
| CORS | 开发阶段 `allow_origins=["*"]`，生产应收紧为 `tauri://localhost` |
| API Key | 经 `cryptography` 加密存储于 providers.yaml，前端仅显示掩码 |
| 子进程 | Tauri 严格管理 Python 进程生命周期，窗口关闭即终止 |

---

## 5. 构建与发布

### 5.1 构建流程

```
前端: npm run build → frontend/dist/
后端: python -m uvicorn backend.src.server:app
桌面: cargo build --release → llm-router.exe
```

### 5.2 自动化脚本

`release/build.sh`：

1. 前端构建（`npm run build`）
2. Python 打包（可选，`--python` 启用 PyInstaller）
3. Tauri 构建（`cargo build --release`）
4. 产物汇集到 `release/llm-router/`

### 5.3 产出结构

```
release/llm-router/
├── llm-router.exe          # Tauri 桌面应用
├── frontend/dist/          # 前端静态文件
├── backend/                # Python 后端
└── src/                    # 业务逻辑模块
```

---

## 6. 迁移记录

### 6.1 已删除的旧文件

| 文件 | 原因 |
|------|------|
| `src/gui/pages/*` | NiceGUI 页面已废弃 |
| `src/gui/app.py` | NiceGUI 应用创建 |
| `src/gui/tray.py` | 依赖已删除的 pystray/pillow |
| `src/gui/launch.py` | 工具函数已提取至 `backend/src/bootstrap.py` |
| `main.py` | 旧 NiceGUI 主入口 |
| `llm_router.spec` | PyInstaller 配置（nicegui/pystray 依赖） |
| `tests/gui/*` | NiceGUI 页面测试 |

### 6.2 依赖变更

| 移除 | 新增 |
|------|------|
| `nicegui>=2.0` | `fastapi>=0.115` |
| `pystray>=0.19` | `uvicorn[standard]>=0.30` |
| `pillow>=10.0` | （Tauri 原生日志替代） |

### 6.3 迁移计划

详见 `docs/superpowers/plans/` 目录，共 11 个任务，18 个 commit：

1. FastAPI 后端骨架
2. Config REST API
3. Dashboard REST + WebSocket API
4. Tasks + Settings API
5. 前端项目脚手架
6. 基础 UI 组件
7. ConfigPage
8. DashboardPage（含 ECharts + WebSocket）
9. TasksPage + LogsPage + SettingsPage
10. Tauri 集成
11. 验收测试 + 清理

---

## 7. 未来规划

- [ ] Tauri 系统托盘（`tauri-plugin-tray` 替代 pystray）
- [ ] 预测模型准入（EWMA 基线 → RL 迭代）
- [ ] 生产 CORS/CSP 收紧
- [ ] CI/CD 流水线自动构建
- [ ] macOS / Linux 平台测试

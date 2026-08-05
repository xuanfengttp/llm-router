# LLM Router

智能 Agent 任务调度与 LLM 路由控制系统。

## 架构

```
┌─────────────────────────────────────────────┐
│              Tauri 2 (Rust)                  │
│      桌面窗口 + Python 子进程管理              │
└──────────────┬──────────────────────────────┘
               │ spawn
┌──────────────▼──────────────────────────────┐
│          Python FastAPI (:19876)             │
│    REST API + WebSocket + SQLite 持久化       │
└──────────────┬──────────────────────────────┘
               │ HTTP/WS
┌──────────────▼──────────────────────────────┐
│      React 19 + TypeScript + TailwindCSS     │
│    shadcn/ui + ECharts + Zustand + Vite      │
└─────────────────────────────────────────────┘
```

- **Tauri 2**：Rust 桌面 shell，管理 Python sidecar 子进程生命周期
- **FastAPI**：异步 REST API + WebSocket，Pydantic v2 数据验证
- **React 19**：TypeScript SPA，5 个业务页面，VS Code 深色主题

## 项目结构

```
├── backend/src/             # FastAPI 后端
│   ├── server.py            # 应用入口 + lifespan
│   ├── bootstrap.py         # 启动引导（ConfigManager 构建）
│   └── api/                 # 4 个路由模块
│       ├── config_api.py    # Provider / Model CRUD
│       ├── dashboard_api.py # 状态 + 探测 + WebSocket
│       ├── tasks_api.py     # 任务提交 / 取消 / 重试
│       └── settings_api.py  # 设置读写
├── frontend/                # React 前端
│   ├── src/
│   │   ├── pages/           # 5 个业务页面
│   │   │   ├── DashboardPage.tsx  # ECharts 图表 + KPI 卡片
│   │   │   ├── ConfigPage.tsx     # Provider + Model 管理
│   │   │   ├── TasksPage.tsx      # 任务创建 + 列表
│   │   │   ├── LogsPage.tsx       # 操作/切换/审计日志
│   │   │   └── SettingsPage.tsx   # 6 面板设置
│   │   ├── components/      # 通用组件（AppShell, NavBar, StatusDot 等）
│   │   ├── hooks/           # useWebSocket 等自定义 Hook
│   │   ├── lib/             # API 客户端 + TypeScript 类型
│   │   └── store/           # Zustand 全局状态
│   └── vite.config.ts       # Vite 配置 + API/WS 代理
├── src-tauri/               # Tauri 2 Rust 项目
│   ├── src/
│   │   ├── main.rs          # Windows 入口（console visible）
│   │   └── lib.rs           # Python 子进程管理 + 窗口逻辑
│   └── tauri.conf.json      # Tauri 配置 + CSP 安全策略
├── src/                     # Python 业务逻辑模块
│   ├── config/              # 配置管理（YAML + SQLite）
│   ├── controller/          # 任务控制器 + 分发器
│   ├── guard/               # 文件守护 + 规则矩阵
│   ├── monitor/             # 监控调度器
│   ├── network/             # 网络探测
│   ├── prediction/          # 延迟预测引擎
│   ├── routing/             # 路由策略引擎
│   └── scoring/             # 评分 + Profile
├── tests/                   # 测试套件（pytest）
├── release/                 # 发布产物 + 构建脚本
│   ├── build.sh             # 自动化构建脚本
│   └── README.md            # release 使用说明
├── docs/                    # 文档 + 设计报告 + 研究
│   └── superpowers/         # 规格说明 + 实现计划
└── pyproject.toml           # Python 项目配置
```

## 快速开始

### 开发环境

```bash
# 安装 Python 依赖
pip install -e ".[dev]"

# 启动后端
python -m uvicorn backend.src.server:app --host 127.0.0.1 --port 19876 --reload

# 安装前端依赖
cd frontend && npm install

# 启动前端开发服务器
npm run dev            # → http://localhost:5173

# 启动 Tauri 桌面应用
npm run tauri dev
```

### 运行测试

```bash
# 后端测试
pytest tests/ -x -q

# 前端构建验证
cd frontend && npm run build

# Tauri 类型检查
cd src-tauri && cargo check
```

### 发布构建

```bash
bash release/build.sh           # 前端 + Tauri
bash release/build.sh --python  # 含 PyInstaller 后端打包
```

产物输出到 `release/llm-router/`。

## 技术栈

| 层 | 技术 | 版本 |
|---|------|------|
| 桌面框架 | Tauri | 2.x |
| 前端框架 | React | 19.x |
| 构建工具 | Vite | 8.x |
| UI 组件 | shadcn/ui + TailwindCSS | 4.x |
| 图表 | ECharts | 6.x |
| 状态管理 | Zustand | 5.x |
| 路由 | React Router | 7.x |
| 后端框架 | FastAPI + Pydantic | 2.x |
| 数据库 | SQLite (aiosqlite) | - |
| 打包 | PyInstaller + Tauri Bundler | - |

## 迁移历史

本项目从 **NiceGUI (Python Monolithic GUI)** 迁移至 **Tauri + React + FastAPI** 三层架构。

迁移计划见 `docs/superpowers/plans/`，提交记录见 git log（18 commits, 11 tasks）。

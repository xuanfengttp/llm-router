# LLM Router

智能 LLM 多模型路由延迟监控桌面应用。

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
│    ECharts 延迟图表 + Zustand 状态管理        │
└─────────────────────────────────────────────┘
```

- **Tauri 2**：Rust 桌面 shell，管理 Python sidecar 子进程生命周期，隐藏 CMD 窗口，日志写入文件
- **FastAPI**：异步 REST API + WebSocket 实时推送，Pydantic v2 数据验证
- **React 19**：TypeScript SPA，5 个业务页面，浅色/暗色双主题，中英文双语界面

## 项目结构

```
├── backend/src/             # FastAPI 后端
│   ├── server.py            # 应用入口 + lifespan（日志配置）
│   ├── bootstrap.py         # 启动引导
│   ├── schemas.py           # Pydantic 数据模型
│   └── api/                 # 4 个路由模块
│       ├── config_api.py    # Provider / Model CRUD
│       ├── dashboard_api.py # 延迟查询 + 探测 + WebSocket
│       ├── tasks_api.py     # 任务提交 / 取消 / 重试
│       └── settings_api.py  # 设置读写
├── frontend/                # React 前端
│   ├── src/
│   │   ├── pages/           # 5 个业务页面
│   │   │   ├── DashboardPage.tsx      # 延迟图表（折线/K线/日线）+ KPI
│   │   │   ├── ConfigPage.tsx         # Provider + Model 管理
│   │   │   ├── TasksPage.tsx          # 任务创建 + 列表
│   │   │   ├── LogsPage.tsx           # 操作/切换/审计日志
│   │   │   └── SettingsPage.tsx       # 6 面板设置
│   │   ├── components/      # 通用组件
│   │   ├── hooks/           # useWebSocket
│   │   ├── lib/             # API 客户端 + 类型定义
│   │   ├── locales/         # 中英文 i18n（useT hook）
│   │   └── store/           # Zustand 全局状态
│   └── index.css            # 全局样式 + CSS 变量主题
├── src/                     # Python 业务逻辑
│   ├── config/              # 配置管理（YAML + SQLite + 加密）
│   ├── controller/          # 任务控制器 + 分发器
│   ├── guard/               # 文件守护 + 规则矩阵
│   ├── monitor/             # 监控调度器
│   ├── network/             # 网络延迟探测
│   ├── prediction/          # 延迟预测引擎
│   ├── routing/             # 路由策略引擎
│   └── scoring/             # 评分 + Profile
├── src-tauri/               # Tauri 2 Rust 项目
│   ├── src/
│   │   ├── main.rs          # Windows GUI 入口（隐藏控制台）
│   │   └── lib.rs           # Python 子进程管理 + 日志重定向
│   └── tauri.conf.json      # Tauri 配置 + CSP
├── tests/                   # pytest 测试
├── release/                 # EXE 发布产物
│   └── llm-router/          # 双击即用的桌面应用
├── docs/                    # 设计文档 + 研究 + 规格说明
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

# 启动 Tauri 桌面应用（开发模式）
npx tauri dev
```

### 运行测试

```bash
# 后端测试
python -m pytest tests/ -x -q

# 前端类型检查
cd frontend && npx tsc --noEmit
```

### 发布构建

```bash
# 一键构建（前端 + Tauri EXE + 部署）
npx @tauri-apps/cli@2 build --config src-tauri/tauri.conf.json
cp src-tauri/target/release/llm-router.exe release/llm-router/

# 双击 release/llm-router/llm-router.exe 运行
```

## 功能特性

- **延迟监控**：30 秒自动探测 + 手动触发，折线图 / K线图 / 日线聚合三种视图
- **实时推送**：WebSocket 广播探测结果，图表实时更新
- **多 Provider**：OpenAI / Anthropic / DeepSeek / Ollama / Groq 等，预置模板一键添加
- **双主题**：浅色 / 暗色切换，CSS 变量驱动
- **双语界面**：中文 / English，轻量 useT() hook
- **日志持久化**：Python 后端日志写入 `logs/llm-router.log` + `data/logs/server.log`

## 技术栈

| 层 | 技术 | 版本 |
|---|------|------|
| 桌面框架 | Tauri | 2.x |
| 前端框架 | React | 19.x |
| 构建工具 | Vite | 8.x |
| 图表 | ECharts | 6.x |
| 状态管理 | Zustand | 5.x |
| 路由 | React Router | 7.x |
| 后端框架 | FastAPI + Pydantic | 2.x |
| 数据库 | SQLite (aiosqlite) | - |
| 样式 | TailwindCSS + CSS 变量 | 4.x |

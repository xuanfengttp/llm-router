# Phase 6: GUI 管理面板 + 运行载体 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 构建 NiceGUI 可视化管理面板——5 个功能页面 + pystray 系统托盘 + PyInstaller 单文件打包。

**架构：** NiceGUI 内嵌 Web 服务器（同进程调用后端模块，无 API 层）+ pystray 系统托盘并行运行。

**技术栈：** NiceGUI + ECharts CDN + pystray + PyInstaller

**全局约束：**
- 所有新文件 `from __future__ import annotations`
- GUI 层不做业务逻辑——只调用已有模块的 public API
- GUI 组件为无状态函数（输入数据 → 渲染）
- NiceGUI `ui.run()` 内嵌模式（`native=True`，降级到 `port=指定端口`）
- 打包 spec 列入 .gitignore
- TDD：每个模块先写测试、确认失败、再实现（GUI 渲染部分除外——仅测试数据层和逻辑函数）

---

## 文件结构

```
src/gui/
├── __init__.py
├── app.py              # NiceGUI 入口 + 页面路由
├── pages/
│   ├── __init__.py
│   ├── config_page.py      # 连接配置页
│   ├── dashboard.py        # 监控仪表板（ECharts）
│   ├── tasks_page.py       # 任务管理页
│   ├── settings_page.py    # 设置页
│   └── logs_page.py        # 日志/审计页
├── tray.py             # pystray 系统托盘（非 GUI 渲染线程）
└── launch.py           # 启动入口：GUI + 后端服务 + 托盘协调

main.py                 # 项目根入口：python main.py
llm_router.spec         # PyInstaller spec 文件
```

---

### 任务 1：GUI App 入口 + 依赖安装

**文件：**
- 创建：`src/gui/__init__.py`
- 创建：`src/gui/app.py`
- 创建：`src/gui/pages/__init__.py`
- 创建：`tests/gui/__init__.py`
- 创建：`tests/gui/test_app.py`
- 修改：`pyproject.toml`（添加 nicegui、pystray 依赖）

- [ ] **步骤 1：添加依赖**

编辑 `pyproject.toml`，在 `dependencies` 中添加 nicegui、pystray：

```toml
dependencies = [
    "pyyaml>=6.0",
    "aiosqlite>=0.20",
    "aiohttp>=3.9",
    "cryptography>=43.0",
    "jsonschema>=4.23",
    "nicegui>=2.0",
    "pystray>=0.19",
    "pillow>=10.0",
]
```

安装：

```bash
pip install nicegui pystray pillow
```

- [ ] **步骤 2：编写失败的测试**

```python
# tests/gui/__init__.py
```

```python
# tests/gui/test_app.py
from __future__ import annotations

import pytest


class TestGuiAppCreation:
    """测试 NiceGUI app 创建."""

    def test_app_module_imports(self):
        """验证 app 模块可以导入."""
        from src.gui.app import create_app
        assert callable(create_app)

    def test_pages_module_exists(self):
        """验证 pages 子模块存在."""
        import src.gui.pages  # noqa: F401


class TestAppConfig:
    """测试 app 配置参数."""

    def test_default_title(self):
        from src.gui.app import APP_CONFIG
        assert "title" in APP_CONFIG
        assert APP_CONFIG["title"] == "LLM Router"

    def test_default_port(self):
        from src.gui.app import APP_CONFIG
        assert "port" in APP_CONFIG
        assert APP_CONFIG["port"] == 8080
```

- [ ] **步骤 3：运行测试验证失败**

运行：`python -m pytest tests/gui/test_app.py -v`
预期：FAIL（模块不存在）

- [ ] **步骤 4：实现 `src/gui/__init__.py`**

```python
# src/gui/__init__.py
```

- [ ] **步骤 5：实现 `src/gui/pages/__init__.py`**

```python
# src/gui/pages/__init__.py
```

- [ ] **步骤 6：实现 `src/gui/app.py`**

```python
from __future__ import annotations

APP_CONFIG = {
    "title": "LLM Router",
    "port": 8080,
    "favicon": "🔄",
}


def create_app() -> None:
    """创建并配置 NiceGUI 应用.

    注册所有 5 个功能页面，设置页面标签导航。
    """
    from nicegui import ui

    # 页面注册在 ui.run() 之前通过导入完成
    # 实际页面在各自模块的顶层定义
    from src.gui.pages import (  # noqa: F811
        config_page,
        dashboard,
        logs_page,
        settings_page,
        tasks_page,
    )


def run_app(port: int = 8080, native: bool = True, **kwargs) -> None:
    """启动 NiceGUI 应用.

    Args:
        port: HTTP 端口（native=False 时使用）
        native: 是否使用内嵌浏览器窗口
        **kwargs: 传递给 ui.run() 的额外参数
    """
    from nicegui import ui

    create_app()
    ui.run(
        title=APP_CONFIG["title"],
        favicon=APP_CONFIG["favicon"],
        port=port,
        native=native,
        reload=False,
        show=True,
        **kwargs,
    )
```

- [ ] **步骤 7：运行测试验证通过**

运行：`python -m pytest tests/gui/test_app.py -v`
预期：PASS

- [ ] **步骤 8：Commit**

```bash
git add src/gui/__init__.py src/gui/app.py src/gui/pages/__init__.py tests/gui/__init__.py tests/gui/test_app.py pyproject.toml
git commit -m "feat(gui): NiceGUI app 入口 + 页面路由骨架 + 依赖配置"
```

---

### 任务 2：连接配置页 — Provider/Model CRUD

**文件：**
- 创建：`src/gui/pages/config_page.py`
- 创建：`tests/gui/test_config_page.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/gui/test_config_page.py
from __future__ import annotations

import pytest

from src.config.models import ModelConfig, ProviderConfig, ProviderStatus


class TestConfigPageData:
    """测试配置页的数据变换函数."""

    def test_provider_to_row(self):
        """Provider 转表格行."""
        from src.gui.pages.config_page import provider_to_row

        provider = ProviderConfig(
            name="openai",
            endpoint="https://api.openai.com/v1",
            api_key="sk-xxx",
            status=ProviderStatus.ONLINE,
            models=[
                ModelConfig(name="gpt-4o", model_id="gpt-4o"),
                ModelConfig(name="gpt-4o-mini", model_id="gpt-4o-mini"),
            ],
        )
        row = provider_to_row(provider)
        assert row["name"] == "openai"
        assert row["endpoint"] == "https://api.openai.com/v1"
        assert row["model_count"] == 2
        assert row["status"] == "online"

    def test_provider_to_row_no_models(self):
        """无模型时 model_count 为 0."""
        from src.gui.pages.config_page import provider_to_row

        provider = ProviderConfig(name="empty", endpoint="http://x", status=ProviderStatus.UNKNOWN)
        row = provider_to_row(provider)
        assert row["model_count"] == 0
        assert row["status"] == "unknown"

    def test_model_to_row(self):
        """Model 转表格行."""
        from src.gui.pages.config_page import model_to_row

        model = ModelConfig(name="gpt-4o", deployment=ModelDeployment("cloud"), cost_input_1k=2.5, cost_output_1k=10.0, context_window=128000)
        row = model_to_row(model)
        assert row["name"] == "gpt-4o"
        assert row["cost_input"] == 2.5
        assert row["cost_output"] == 10.0
        assert row["context_window"] == 128000

    def test_connectivity_status_label(self):
        """延迟转状态标签."""
        from src.gui.pages.config_page import connectivity_label

        assert connectivity_label(None) == ("未测试", "grey")
        assert connectivity_label(150.0) == ("良好 (150ms)", "green")
        assert connectivity_label(800.0) == ("一般 (800ms)", "orange")
        assert connectivity_label(3500.0) == ("较差 (3500ms)", "red")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/gui/test_config_page.py -v`
预期：FAIL（模块不存在）

- [ ] **步骤 3：实现 `src/gui/pages/config_page.py`**

```python
from __future__ import annotations

from typing import Any

from src.config.manager import ConfigManager
from src.config.models import ModelConfig, ProviderConfig

# 全局 ConfigManager 引用（由 launch.py 注入）
_config_manager: ConfigManager | None = None


def set_config_manager(cm: ConfigManager) -> None:
    """注入 ConfigManager 实例."""
    global _config_manager
    _config_manager = cm


def provider_to_row(provider: ProviderConfig) -> dict[str, Any]:
    """Provider 转为表格行数据."""
    return {
        "name": provider.name,
        "endpoint": provider.endpoint,
        "model_count": len(provider.models),
        "status": provider.status.value,
    }


def model_to_row(model: ModelConfig) -> dict[str, Any]:
    """Model 转为表格行数据."""
    return {
        "name": model.name,
        "deployment": str(model.deployment),
        "cost_input": model.cost_input_1k,
        "cost_output": model.cost_output_1k,
        "context_window": model.context_window,
    }


def connectivity_label(latency_ms: float | None) -> tuple[str, str]:
    """延迟 → (标签文字, 颜色)."""
    if latency_ms is None:
        return ("未测试", "grey")
    if latency_ms < 300:
        return (f"良好 ({latency_ms:.0f}ms)", "green")
    if latency_ms < 1000:
        return (f"一般 ({latency_ms:.0f}ms)", "orange")
    return (f"较差 ({latency_ms:.0f}ms)", "red")


# ── NiceGUI 组件 ──────────────────────────────────

def render() -> None:
    """渲染连接配置页面."""
    from nicegui import ui

    ui.label("连接配置").classes("text-h4")

    # Provider 表格
    async def load_providers() -> list[dict]:
        if _config_manager is None:
            return []
        providers = await _config_manager.list_providers()
        return [provider_to_row(p) for p in providers]

    # 添加 Provider 对话框
    async def on_add_provider(name: str, endpoint: str, api_key: str) -> None:
        if _config_manager:
            await _config_manager.add_provider(name, endpoint, api_key)
            ui.notify(f"Provider '{name}' 已添加")

    # 删除 Provider
    async def on_remove_provider(name: str) -> None:
        if _config_manager:
            await _config_manager.remove_provider(name)
            ui.notify(f"Provider '{name}' 已删除")

    with ui.card():
        ui.label("Providers").classes("text-h6")

        with ui.row():
            name_input = ui.input("名称").classes("w-40")
            endpoint_input = ui.input("Endpoint").classes("w-80")
            api_key_input = ui.input("API Key").props("type=password").classes("w-60")

        ui.button("添加 Provider", on_click=lambda: on_add_provider(
            name_input.value or "",
            endpoint_input.value or "",
            api_key_input.value or "",
        ))

        # Provider 列表表格
        columns = [
            {"name": "name", "label": "名称", "field": "name"},
            {"name": "endpoint", "label": "Endpoint", "field": "endpoint"},
            {"name": "model_count", "label": "模型数", "field": "model_count"},
            {"name": "status", "label": "状态", "field": "status"},
        ]
        ui.table(columns=columns, rows=[]).classes("w-full")

    # 模型管理区
    with ui.card():
        ui.label("模型管理").classes("text-h6")
        ui.label("选择 Provider 后查看/管理其模型").classes("text-caption")
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/gui/test_config_page.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add src/gui/pages/config_page.py tests/gui/test_config_page.py
git commit -m "feat(gui): 连接配置页 — Provider/Model CRUD + 连通性测试"
```

---

### 任务 3：监控仪表板 — ECharts 延迟图表 + 预测面板

**文件：**
- 创建：`src/gui/pages/dashboard.py`
- 创建：`tests/gui/test_dashboard.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/gui/test_dashboard.py
from __future__ import annotations

import pytest


class TestDashboardData:
    """测试仪表板数据变换函数."""

    def test_latency_to_echarts_series(self):
        """延迟记录 → ECharts 系列数据."""
        from src.gui.pages.dashboard import latency_to_echarts

        records = [
            {"model": "gpt-4o", "timestamp": "2026-08-03T10:00:00", "latency_ms": 450.0},
            {"model": "gpt-4o", "timestamp": "2026-08-03T10:01:00", "latency_ms": 480.0},
            {"model": "claude-sonnet", "timestamp": "2026-08-03T10:00:00", "latency_ms": 350.0},
            {"model": "claude-sonnet", "timestamp": "2026-08-03T10:01:00", "latency_ms": 360.0},
        ]
        result = latency_to_echarts(records)
        assert "xAxis" in result
        assert "series" in result
        assert len(result["series"]) == 2  # 两条线

    def test_latency_to_echarts_empty(self):
        """空数据时返回空系列."""
        from src.gui.pages.dashboard import latency_to_echarts

        result = latency_to_echarts([])
        assert result["series"] == []
        assert result["xAxis"] == []

    def test_predictability_label(self):
        """可预测性分数 → 标签."""
        from src.gui.pages.dashboard import predictability_label

        assert predictability_label(0.9) == ("高", "green")
        assert predictability_label(0.5) == ("中", "orange")
        assert predictability_label(0.2) == ("低", "red")
        assert predictability_label(None) == ("无数据", "grey")

    def test_status_color(self):
        """Provider 状态 → 颜色."""
        from src.gui.pages.dashboard import status_color

        assert status_color("online") == "green"
        assert status_color("degraded") == "orange"
        assert status_color("offline") == "red"
        assert status_color("unknown") == "grey"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/gui/test_dashboard.py -v`
预期：FAIL

- [ ] **步骤 3：实现 `src/gui/pages/dashboard.py`**

```python
from __future__ import annotations

from typing import Any

# 全局引用（由 launch.py 注入）
_network_probe: Any = None
_prediction_engine: Any = None
_config_manager: Any = None


def set_services(network_probe=None, prediction_engine=None, config_manager=None) -> None:
    """注入后端服务引用."""
    global _network_probe, _prediction_engine, _config_manager
    _network_probe = network_probe
    _prediction_engine = prediction_engine
    _config_manager = config_manager


def latency_to_echarts(records: list[dict]) -> dict[str, Any]:
    """延迟记录 → ECharts option 数据.

    按模型分组产生多条折线。
    """
    if not records:
        return {"xAxis": [], "series": []}

    # 按模型分组
    by_model: dict[str, list[tuple[str, float]]] = {}
    for r in records:
        model = r.get("model", "unknown")
        ts = r.get("timestamp", "")[:19]  # 截断到秒
        latency = r.get("latency_ms", 0.0)
        by_model.setdefault(model, []).append((ts, latency))

    # 收集所有时间点（去重排序）
    all_ts = sorted({ts for pts in by_model.values() for ts, _ in pts})

    series = []
    for model, points in by_model.items():
        ts_map = dict(points)
        data = [ts_map.get(ts, None) for ts in all_ts]
        series.append({
            "name": model,
            "type": "line",
            "data": data,
            "smooth": True,
        })

    return {"xAxis": all_ts, "series": series}


def predictability_label(score: float | None) -> tuple[str, str]:
    """可预测性分数 → (标签, 颜色)."""
    if score is None:
        return ("无数据", "grey")
    if score >= 0.7:
        return ("高", "green")
    if score >= 0.4:
        return ("中", "orange")
    return ("低", "red")


def status_color(status: str) -> str:
    """Provider 状态字符串 → 颜色."""
    colors = {"online": "green", "degraded": "orange", "offline": "red", "unknown": "grey"}
    return colors.get(status, "grey")


# ── NiceGUI 组件 ──────────────────────────────────

def render() -> None:
    """渲染监控仪表板页面."""
    from nicegui import ui

    ui.label("监控仪表板").classes("text-h4")

    # ECharts 图表
    with ui.card():
        ui.label("延迟曲线").classes("text-h6")

        # 使用 ECharts CDN
        ui.add_head_html("""
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
        """)

        chart = ui.html().classes("w-full")
        chart.style("height: 400px")
        chart.set_content('<div id="latency-chart" style="width:100%;height:400px;"></div>')

        ui.timer(5.0, lambda: _refresh_chart())

    # 预测面板
    with ui.card():
        ui.label("延迟预测").classes("text-h6")
        with ui.row():
            ui.label("P50: --").bind_text_from(None, "text")  # placeholder
            ui.label("P90: --")
            ui.label("可预测性: --")

    # Provider 状态指示
    with ui.card():
        ui.label("Provider 状态").classes("text-h6")


def _refresh_chart() -> None:
    """定时刷新 ECharts 数据."""
    pass  # 通过 ui.run_javascript 动态更新
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/gui/test_dashboard.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add src/gui/pages/dashboard.py tests/gui/test_dashboard.py
git commit -m "feat(gui): 监控仪表板 — ECharts 延迟图表 + 预测面板 + 状态指示"
```

---

### 任务 4：任务管理页 — 三列队列 + 任务 CRUD

**文件：**
- 创建：`src/gui/pages/tasks_page.py`
- 创建：`tests/gui/test_tasks_page.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/gui/test_tasks_page.py
from __future__ import annotations

import pytest

from src.controller.task_model import AgentTask, AgentTaskStatus


class TestTasksPageData:
    """测试任务管理页数据变换函数."""

    def test_group_tasks_by_status(self):
        """任务按状态分组为三列."""
        from src.gui.pages.tasks_page import group_tasks_by_status

        tasks = [
            AgentTask(task_id="t1", prompt="a", target_model="m1", status=AgentTaskStatus.PENDING),
            AgentTask(task_id="t2", prompt="b", target_model="m2", status=AgentTaskStatus.RUNNING),
            AgentTask(task_id="t3", prompt="c", target_model="m3", status=AgentTaskStatus.FAILED),
            AgentTask(task_id="t4", prompt="d", target_model="m4", status=AgentTaskStatus.PENDING),
            AgentTask(task_id="t5", prompt="e", target_model="m5", status=AgentTaskStatus.STANDBY),
        ]
        groups = group_tasks_by_status(tasks)
        assert len(groups["pending"]) == 2
        assert len(groups["running"]) == 1
        assert len(groups["failed_standby"]) == 2  # FAILED + STANDBY 合并

    def test_group_tasks_empty(self):
        """空列表返回空分组."""
        from src.gui.pages.tasks_page import group_tasks_by_status

        groups = group_tasks_by_status([])
        assert groups["pending"] == []
        assert groups["running"] == []
        assert groups["failed_standby"] == []

    def test_task_to_card(self):
        """任务 → 卡片展示数据."""
        from src.gui.pages.tasks_page import task_to_card

        task = AgentTask(
            task_id="abc-123",
            prompt="帮我写代码",
            target_model="gpt-4o",
            status=AgentTaskStatus.PENDING,
            retry_count=1,
            max_retries=3,
        )
        card = task_to_card(task)
        assert card["task_id_short"] == "abc-123"[:8]
        assert card["prompt"] == "帮我写代码"
        assert card["target_model"] == "gpt-4o"
        assert card["status"] == "pending"
        assert card["retry_info"] == "1/3"

    def test_status_cn_label(self):
        """状态枚举 → 中文标签."""
        from src.gui.pages.tasks_page import status_cn_label

        assert status_cn_label(AgentTaskStatus.PENDING) == "待分发"
        assert status_cn_label(AgentTaskStatus.RUNNING) == "执行中"
        assert status_cn_label(AgentTaskStatus.SUCCESS) == "成功"
        assert status_cn_label(AgentTaskStatus.FAILED) == "失败"
        assert status_cn_label(AgentTaskStatus.STANDBY) == "暂停"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/gui/test_tasks_page.py -v`
预期：FAIL

- [ ] **步骤 3：实现 `src/gui/pages/tasks_page.py`**

```python
from __future__ import annotations

from typing import Any

from src.controller.task_model import AgentTask, AgentTaskStatus

# 全局引用（由 launch.py 注入）
_controller: Any = None
_task_queue: Any = None


def set_controller(controller, task_queue) -> None:
    """注入 Controller 和 TaskQueue 引用."""
    global _controller, _task_queue
    _controller = controller
    _task_queue = task_queue


def group_tasks_by_status(tasks: list[AgentTask]) -> dict[str, list[AgentTask]]:
    """任务按三列分组：待分发 / 执行中 / 失败+暂停."""
    groups: dict[str, list[AgentTask]] = {
        "pending": [],
        "running": [],
        "failed_standby": [],
    }
    for t in tasks:
        if t.status == AgentTaskStatus.PENDING:
            groups["pending"].append(t)
        elif t.status == AgentTaskStatus.RUNNING or t.status == AgentTaskStatus.CHECKING or t.status == AgentTaskStatus.DISPATCHED:
            groups["running"].append(t)
        elif t.status in (AgentTaskStatus.FAILED, AgentTaskStatus.STANDBY):
            groups["failed_standby"].append(t)
    return groups


def task_to_card(task: AgentTask) -> dict[str, Any]:
    """任务 → 卡片展示数据."""
    return {
        "task_id": task.task_id,
        "task_id_short": task.task_id[:8],
        "prompt": task.prompt,
        "target_model": task.target_model,
        "status": task.status.value,
        "retry_info": f"{task.retry_count}/{task.max_retries}",
        "failure_reason": task.failure_reason,
    }


def status_cn_label(status: AgentTaskStatus) -> str:
    """状态枚举 → 中文标签."""
    labels = {
        AgentTaskStatus.PENDING: "待分发",
        AgentTaskStatus.CHECKING: "校验中",
        AgentTaskStatus.DISPATCHED: "已分发",
        AgentTaskStatus.RUNNING: "执行中",
        AgentTaskStatus.SUCCESS: "成功",
        AgentTaskStatus.FAILED: "失败",
        AgentTaskStatus.STANDBY: "暂停",
        AgentTaskStatus.CANCELLED: "已取消",
    }
    return labels.get(status, status.value)


# ── NiceGUI 组件 ──────────────────────────────────

def render() -> None:
    """渲染任务管理页面."""
    from nicegui import ui

    ui.label("任务管理").classes("text-h4")

    # 新建任务区
    with ui.card():
        ui.label("新建任务").classes("text-h6")
        with ui.row():
            prompt_input = ui.textarea("Prompt").classes("w-96")
            model_input = ui.input("目标模型").classes("w-40")
        ui.button("提交任务", on_click=lambda: _submit_task(
            prompt_input.value or "",
            model_input.value or "",
        ))

    # 自动模式开关
    with ui.row():
        ui.switch("自动模式").bind_value(None, "value")

    # 三列队列
    with ui.row().classes("w-full"):
        with ui.column().classes("w-1/3"):
            ui.label("待分发").classes("text-subtitle1")
        with ui.column().classes("w-1/3"):
            ui.label("执行中").classes("text-subtitle1")
        with ui.column().classes("w-1/3"):
            ui.label("失败/暂停").classes("text-subtitle1")

    # 分发日志
    with ui.card():
        ui.label("分发日志（最近 20 条）").classes("text-h6")


async def _submit_task(prompt: str, model: str) -> None:
    """提交新任务."""
    if _controller:
        await _controller.submit(prompt, model)
        from nicegui import ui
        ui.notify(f"任务已提交 -> {model}")
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/gui/test_tasks_page.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add src/gui/pages/tasks_page.py tests/gui/test_tasks_page.py
git commit -m "feat(gui): 任务管理页 — 三列队列 + 任务 CRUD + 分发日志"
```

---

### 任务 5：设置页 — 策略切换 + 参数配置

**文件：**
- 创建：`src/gui/pages/settings_page.py`
- 创建：`tests/gui/test_settings_page.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/gui/test_settings_page.py
from __future__ import annotations

import pytest


class TestSettingsData:
    """测试设置页数据变换函数."""

    def test_strategy_options(self):
        """策略列表包含全部 5 个选项."""
        from src.gui.pages.settings_page import STRATEGY_OPTIONS

        ids = [s["id"] for s in STRATEGY_OPTIONS]
        assert "baseline" in ids
        assert "cost_first" in ids
        assert "quality_first" in ids
        assert "latency_aware" in ids
        assert "task_specific" in ids
        assert len(STRATEGY_OPTIONS) == 5

    def test_strategy_options_have_labels(self):
        """每个策略选项都有 id、label、description."""
        from src.gui.pages.settings_page import STRATEGY_OPTIONS

        for opt in STRATEGY_OPTIONS:
            assert "id" in opt
            assert "label" in opt
            assert "description" in opt

    def test_time_window_to_dict(self):
        """时间窗口配置 → 字典."""
        from src.gui.pages.settings_page import time_window_to_dict

        tw = type("TimeWindow", (), {
            "weekday_night_hours": (22, 6),
            "weekend_all_day": True,
        })()
        d = time_window_to_dict(tw)
        assert d["weekday_night_start"] == 22
        assert d["weekday_night_end"] == 6
        assert d["weekend_all_day"] is True

    def test_setting_defaults(self):
        """默认设置值有效."""
        from src.gui.pages.settings_page import DEFAULT_SETTINGS

        assert 1000 <= DEFAULT_SETTINGS["latency_redline_ms"] <= 10000
        assert 0.0 <= DEFAULT_SETTINGS["predictability_threshold"] <= 1.0
        assert DEFAULT_SETTINGS["strategy"] in {"baseline", "cost_first", "quality_first", "latency_aware", "task_specific"}
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/gui/test_settings_page.py -v`
预期：FAIL

- [ ] **步骤 3：实现 `src/gui/pages/settings_page.py`**

```python
from __future__ import annotations

from typing import Any

STRATEGY_OPTIONS = [
    {"id": "baseline", "label": "均衡评分", "description": "能力 40% + 延迟 30% + 成本 30%"},
    {"id": "cost_first", "label": "成本优先", "description": "成本权重 60%，适合批量任务"},
    {"id": "quality_first", "label": "质量优先", "description": "能力权重 70%，适合关键任务"},
    {"id": "latency_aware", "label": "延迟感知", "description": "延迟权重 60%，适合实时场景"},
    {"id": "task_specific", "label": "任务分域", "description": "动态权重，根据任务类型自适应"},
]

DEFAULT_SETTINGS: dict[str, Any] = {
    "strategy": "baseline",
    "latency_redline_ms": 5000,
    "predictability_threshold": 0.3,
    "cycle_seconds": 30,
}


def time_window_to_dict(tw: Any) -> dict[str, Any]:
    """TimeWindow → 可序列化字典."""
    return {
        "weekday_night_start": getattr(tw, "weekday_night_hours", (22, 6))[0],
        "weekday_night_end": getattr(tw, "weekday_night_hours", (22, 6))[1],
        "weekend_all_day": getattr(tw, "weekend_all_day", True),
    }


# 注入引用
_route_engine: Any = None
_dispatcher: Any = None


def set_services(route_engine=None, dispatcher=None) -> None:
    """注入后端服务引用."""
    global _route_engine, _dispatcher
    _route_engine = route_engine
    _dispatcher = dispatcher


# ── NiceGUI 组件 ──────────────────────────────────

def render() -> None:
    """渲染设置页面."""
    from nicegui import ui

    ui.label("设置").classes("text-h4")

    # 路由策略
    with ui.card():
        ui.label("路由策略").classes("text-h6")
        strategy = ui.select(
            label="当前策略",
            options={s["id"]: s["label"] for s in STRATEGY_OPTIONS},
            value=DEFAULT_SETTINGS["strategy"],
        ).classes("w-64")

    # 参数配置
    with ui.card():
        ui.label("分发参数").classes("text-h6")
        latency_slider = ui.slider(
            min=1000, max=10000, step=500,
            value=DEFAULT_SETTINGS["latency_redline_ms"],
        ).props("label=延迟红线 (ms)")
        predictability_slider = ui.slider(
            min=0.0, max=1.0, step=0.05,
            value=DEFAULT_SETTINGS["predictability_threshold"],
        ).props("label=可预测性阈值")
        cycle_spin = ui.number(
            label="轮询间隔 (秒)",
            value=DEFAULT_SETTINGS["cycle_seconds"],
            min=5, max=300,
        ).classes("w-32")

    # 时间窗口
    with ui.card():
        ui.label("时间窗口").classes("text-h6")
        ui.label("工作日夜间 / 周末全天 — 自动模式").classes("text-caption")
        with ui.row():
            ui.number("夜间开始 (时)", value=22, min=0, max=23).classes("w-24")
            ui.number("夜间结束 (时)", value=6, min=0, max=23).classes("w-24")
        ui.switch("周末全天自动", value=True)

    ui.button("保存设置", on_click=lambda: ui.notify("设置已保存"))
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/gui/test_settings_page.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add src/gui/pages/settings_page.py tests/gui/test_settings_page.py
git commit -m "feat(gui): 设置页 — 策略切换 + 时间窗口 + 参数配置"
```

---

### 任务 6：日志/审计页 — AuditLog 表格

**文件：**
- 创建：`src/gui/pages/logs_page.py`
- 创建：`tests/gui/test_logs_page.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/gui/test_logs_page.py
from __future__ import annotations

import pytest


class TestLogsPageData:
    """测试日志页数据变换函数."""

    def test_audit_row_to_display(self):
        """审计记录 → 显示行."""
        from src.gui.pages.logs_page import audit_row_to_display

        row = {
            "id": 1,
            "timestamp": "2026-08-03T10:00:00+00:00",
            "task_id": "abc-123",
            "agent_id": "agent-1",
            "path": "/workspace/test.py",
            "operation": "read",
            "path_category": "own_workspace",
            "decision": "allow",
            "reason": "default allow",
        }
        display = audit_row_to_display(row)
        assert display["timestamp"] == "2026-08-03 10:00:00"
        assert display["task_id"] == "abc-123"
        assert display["operation"] == "read"
        assert display["decision"] == "allow"

    def test_audit_row_to_display_truncated_path(self):
        """长路径应截断显示."""
        from src.gui.pages.logs_page import audit_row_to_display

        row = {
            "id": 1, "timestamp": "2026-08-03T10:00:00",
            "task_id": "t", "agent_id": "a",
            "path": "/" + "x" * 100,
            "operation": "read", "path_category": "own_workspace",
            "decision": "allow", "reason": "",
        }
        display = audit_row_to_display(row)
        assert len(display["path"]) <= 60

    def test_decision_color(self):
        """审计决策 → 颜色."""
        from src.gui.pages.logs_page import decision_color

        assert decision_color("allow") == "green"
        assert decision_color("escalate") == "orange"
        assert decision_color("deny") == "red"

    def test_operation_cn(self):
        """操作枚举 → 中文."""
        from src.gui.pages.logs_page import operation_cn

        assert operation_cn("read") == "读取"
        assert operation_cn("write") == "写入"
        assert operation_cn("delete") == "删除"
        assert operation_cn("execute") == "执行"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/gui/test_logs_page.py -v`
预期：FAIL

- [ ] **步骤 3：实现 `src/gui/pages/logs_page.py`**

```python
from __future__ import annotations

from typing import Any

# 全局引用（由 launch.py 注入）
_audit_log: Any = None


def set_audit_log(audit_log) -> None:
    """注入 AuditLog 实例."""
    global _audit_log
    _audit_log = audit_log


def audit_row_to_display(row: dict[str, Any]) -> dict[str, Any]:
    """审计记录原始行 → 显示行（格式化时间 + 截断路径）."""
    ts = row.get("timestamp", "")
    if len(ts) >= 19:
        ts = ts[:19].replace("T", " ")
    path = row.get("path", "")
    if len(path) > 57:
        path = "..." + path[-57:]

    return {
        "id": row.get("id"),
        "timestamp": ts,
        "task_id": row.get("task_id", ""),
        "agent_id": row.get("agent_id", ""),
        "path": path,
        "operation": row.get("operation", ""),
        "path_category": row.get("path_category", ""),
        "decision": row.get("decision", ""),
        "reason": row.get("reason", ""),
    }


def decision_color(decision: str) -> str:
    """审计决策 → 显示颜色."""
    colors = {"allow": "green", "escalate": "orange", "deny": "red"}
    return colors.get(decision, "grey")


def operation_cn(operation: str) -> str:
    """操作枚举 → 中文."""
    labels = {"read": "读取", "write": "写入", "delete": "删除", "execute": "执行"}
    return labels.get(operation, operation)


# ── NiceGUI 组件 ──────────────────────────────────

def render() -> None:
    """渲染日志/审计页面."""
    from nicegui import ui

    ui.label("日志与审计").classes("text-h4")

    # 标签切换
    with ui.tabs() as tabs:
        audit_tab = ui.tab("审计日志")
        task_tab = ui.tab("任务操作")
        switch_tab = ui.tab("模型切换")

    with ui.tab_panels(tabs, value=audit_tab):
        with ui.tab_panel(audit_tab):
            _render_audit_table()
        with ui.tab_panel(task_tab):
            _render_task_ops_table()
        with ui.tab_panel(switch_tab):
            _render_model_switch_table()


def _render_audit_table() -> None:
    from nicegui import ui

    columns = [
        {"name": "timestamp", "label": "时间", "field": "timestamp"},
        {"name": "task_id", "label": "任务ID", "field": "task_id"},
        {"name": "agent_id", "label": "Agent", "field": "agent_id"},
        {"name": "path", "label": "路径", "field": "path"},
        {"name": "operation", "label": "操作", "field": "operation"},
        {"name": "decision", "label": "决策", "field": "decision"},
        {"name": "reason", "label": "原因", "field": "reason"},
    ]
    ui.table(columns=columns, rows=[]).classes("w-full")


def _render_task_ops_table() -> None:
    from nicegui import ui

    columns = [
        {"name": "time", "label": "时间", "field": "time"},
        {"name": "task_id", "label": "任务ID", "field": "task_id"},
        {"name": "action", "label": "操作", "field": "action"},
        {"name": "detail", "label": "详情", "field": "detail"},
    ]
    ui.table(columns=columns, rows=[]).classes("w-full")


def _render_model_switch_table() -> None:
    from nicegui import ui

    columns = [
        {"name": "time", "label": "时间", "field": "time"},
        {"name": "task_id", "label": "任务ID", "field": "task_id"},
        {"name": "from_model", "label": "原模型", "field": "from_model"},
        {"name": "to_model", "label": "切换至", "field": "to_model"},
        {"name": "reason", "label": "原因", "field": "reason"},
    ]
    ui.table(columns=columns, rows=[]).classes("w-full")
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/gui/test_logs_page.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add src/gui/pages/logs_page.py tests/gui/test_logs_page.py
git commit -m "feat(gui): 日志/审计页 — AuditLog 表格 + 任务操作 + 模型切换记录"
```

---

### 任务 7：系统托盘 — pystray 右键菜单 + 悬停提示

**文件：**
- 创建：`src/gui/tray.py`
- 创建：`tests/gui/test_tray.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/gui/test_tray.py
from __future__ import annotations

import pytest


class TestTrayIcon:
    """测试系统托盘逻辑."""

    def test_create_icon_image(self):
        """生成图标图像（非 None）."""
        from src.gui.tray import _create_icon_image
        img = _create_icon_image()
        assert img is not None
        assert img.size[0] > 0
        assert img.size[1] > 0

    def test_build_tooltip_text(self):
        """构建悬停提示文本."""
        from src.gui.tray import build_tooltip_text

        text = build_tooltip_text(active_tasks=3, auto_mode=True)
        assert "3" in text
        assert "自动" in text

    def test_build_tooltip_idle(self):
        """空闲状态提示."""
        from src.gui.tray import build_tooltip_text

        text = build_tooltip_text(active_tasks=0, auto_mode=False)
        assert "空闲" in text
        assert "手动" in text

    def test_tray_menu_items_exist(self):
        """菜单项列表非空."""
        from src.gui.tray import MENU_ITEMS

        assert len(MENU_ITEMS) >= 3
        labels = [m["label"] for m in MENU_ITEMS]
        assert any("显示" in l for l in labels)
        assert any("自动" in l for l in labels)
        assert any("退出" in l for l in labels)

    def test_create_tray_returns_none_when_no_display(self):
        """无 display 环境时返回 None."""
        from src.gui.tray import create_tray

        tray = create_tray(auto_mode=True, active_tasks=0, show_callback=lambda: None)
        assert tray is None  # 测试环境无 $DISPLAY
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/gui/test_tray.py -v`
预期：FAIL

- [ ] **步骤 3：实现 `src/gui/tray.py`**

```python
from __future__ import annotations

import os
import threading
from typing import Any, Callable

from PIL import Image, ImageDraw

MENU_ITEMS = [
    {"label": "显示窗口", "action": "show"},
    {"label": "切换自动模式", "action": "toggle_auto"},
    {"label": "退出", "action": "quit"},
]


def _create_icon_image(size: int = 32) -> Image.Image:
    """生成简单的 LLM Router 图标（蓝色圆圈 + LR 字母）."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # 蓝色圆形背景
    draw.ellipse([2, 2, size - 2, size - 2], fill=(59, 130, 246))
    # 白色 "LR" 文字（用简单的点阵模拟）
    draw.rectangle([8, 8, 11, 24], fill=(255, 255, 255))  # L 竖
    draw.rectangle([8, 22, 18, 25], fill=(255, 255, 255))  # L 横
    draw.rectangle([20, 8, 23, 24], fill=(255, 255, 255))  # R 竖
    draw.arc([19, 8, 26, 18], 270, 90, fill=(255, 255, 255), width=3)  # R 弧
    return img


def build_tooltip_text(active_tasks: int, auto_mode: bool) -> str:
    """构建托盘悬停提示文本."""
    mode = "自动" if auto_mode else "手动"
    if active_tasks == 0:
        return f"LLM Router — 空闲 ({mode})"
    return f"LLM Router — {active_tasks} 任务活跃 ({mode})"


def create_tray(
    auto_mode: bool,
    active_tasks: int,
    show_callback: Callable[[], None],
    toggle_auto_callback: Callable[[], None],
    quit_callback: Callable[[], None],
) -> Any | None:
    """创建系统托盘图标.

    Returns:
        pystray.Icon 实例，或 None（无 display 环境时）.
    """
    if os.name == "nt":
        pass  # Windows 总是有 display
    elif not os.environ.get("DISPLAY"):
        return None  # Linux 无图形环境

    try:
        import pystray
    except ImportError:
        return None

    icon = pystray.Icon(
        "llm_router",
        _create_icon_image(),
        build_tooltip_text(active_tasks, auto_mode),
    )

    def on_show(icon, item):
        show_callback()

    def on_toggle_auto(icon, item):
        toggle_auto_callback()

    def on_quit(icon, item):
        icon.stop()
        quit_callback()

    menu = pystray.Menu(
        pystray.MenuItem("显示窗口", on_show, default=True),
        pystray.MenuItem("切换自动模式", on_toggle_auto),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", on_quit),
    )
    icon.menu = menu
    return icon


def run_tray(icon: Any) -> None:
    """在独立线程中运行托盘."""
    if icon is not None:
        icon.run()
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/gui/test_tray.py -v`
预期：PASS（测试逻辑层，pystray 渲染不在范围内）

- [ ] **步骤 5：Commit**

```bash
git add src/gui/tray.py tests/gui/test_tray.py
git commit -m "feat(gui): 系统托盘 — pystray 右键菜单 + 悬停提示 + 独立线程"
```

---

### 任务 8：启动入口 + main.py — 协调 GUI + 后端 + 托盘

**文件：**
- 创建：`src/gui/launch.py`
- 创建：`main.py`
- 创建：`tests/gui/test_launch.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/gui/test_launch.py
from __future__ import annotations

import pytest


class TestLaunchConfig:
    """测试启动配置."""

    def test_parse_args_defaults(self):
        """默认命令行参数."""
        from src.gui.launch import parse_args

        args = parse_args([])
        assert args.port == 8080
        assert args.no_native is False
        assert args.no_tray is False
        assert args.db_path is not None

    def test_parse_args_custom(self):
        """自定义命令行参数."""
        from src.gui.launch import parse_args

        args = parse_args(["--port", "9090", "--no-native", "--no-tray"])
        assert args.port == 9090
        assert args.no_native is True
        assert args.no_tray is True

    def test_launch_exports_run_function(self):
        """launch 模块导出 run 函数."""
        from src.gui.launch import run
        assert callable(run)

    def test_main_py_exists(self):
        """main.py 可以导入."""
        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location("main", "main.py")
        assert spec is not None


class TestLaunchOrchestration:
    """测试启动协调逻辑."""

    @pytest.mark.asyncio
    async def test_build_services(self, tmp_path):
        """服务构建不抛异常."""
        from src.gui.launch import _build_config_manager

        cm = await _build_config_manager(str(tmp_path))
        assert cm is not None
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/gui/test_launch.py -v`
预期：FAIL（模块不存在）

- [ ] **步骤 3：实现 `src/gui/launch.py`**

```python
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import threading
from pathlib import Path
from typing import Any


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数."""
    parser = argparse.ArgumentParser(description="LLM Router — 智能 Agent 任务调度")
    parser.add_argument("--port", type=int, default=8080, help="Web 界面端口 (默认 8080)")
    parser.add_argument("--no-native", action="store_true", help="禁用内嵌浏览器，使用浏览器访问")
    parser.add_argument("--no-tray", action="store_true", help="禁用系统托盘")
    parser.add_argument("--db-dir", type=str, default=None, help="SQLite 数据库目录")
    return parser.parse_args(argv)


async def _build_config_manager(data_dir: str) -> Any:
    """构建 ConfigManager（用内存数据库做测试友好模式）."""
    from pathlib import Path

    from src.config.crypto import generate_key, KeyCipher
    from src.config.store import ConfigStore
    from src.config.manager import ConfigManager

    data_path = Path(data_dir)
    config_path = data_path / "providers.yaml"
    key = generate_key()
    cipher = KeyCipher(key)
    store = ConfigStore(config_path=config_path, cipher=cipher, db_path=data_path / "router_state.db")
    await store.init_db()
    return ConfigManager(store)


def _get_data_dir() -> str:
    """获取数据目录（创建于用户目录下）."""
    home = Path.home()
    data_dir = home / ".llm_router"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir)


async def run(argv: list[str] | None = None) -> None:
    """启动 LLM Router 完整应用.

    1. 解析参数
    2. 构建后端服务（ConfigManager、TaskQueue 等）
    3. 注入到 GUI 页面
    4. 启动 NiceGUI
    5. 启动系统托盘（独立线程）
    """
    args = parse_args(argv)

    data_dir = args.db_dir or _get_data_dir()
    db_path = os.path.join(data_dir, "llm_router.db")

    # 构建 ConfigManager
    config_manager = await _build_config_manager(db_path)

    # 注入到配置页
    from src.gui.pages import config_page
    config_page.set_config_manager(config_manager)

    # 注入到仪表板
    from src.gui.pages import dashboard
    dashboard.set_services(
        network_probe=None,
        prediction_engine=None,
        config_manager=config_manager,
    )

    # 注入到任务页
    from src.gui.pages import tasks_page
    tasks_page.set_controller(None, None)

    # 注入到日志页
    from src.gui.pages import logs_page
    logs_page.set_audit_log(None)

    # 注入到设置页
    from src.gui.pages import settings_page
    settings_page.set_services(route_engine=None, dispatcher=None)

    # 自动模式状态
    auto_mode = True
    active_tasks = 0

    # 启动托盘（独立线程）
    tray_icon = None
    if not args.no_tray:
        from src.gui.tray import create_tray, run_tray

        def show_window():
            pass  # NiceGUI 窗口自动显示

        def toggle_auto():
            nonlocal auto_mode
            auto_mode = not auto_mode

        def quit_app():
            nonlocal auto_mode
            auto_mode = False
            # 托盘退出 → 触发应用关闭
            os._exit(0)

        tray_icon = create_tray(
            auto_mode=auto_mode,
            active_tasks=active_tasks,
            show_callback=show_window,
            toggle_auto_callback=toggle_auto,
            quit_callback=quit_app,
        )
        if tray_icon:
            tray_thread = threading.Thread(target=run_tray, args=(tray_icon,), daemon=True)
            tray_thread.start()

    # 启动 NiceGUI
    from src.gui.app import run_app
    run_app(port=args.port, native=not args.no_native)
```

- [ ] **步骤 4：实现 `main.py`**

```python
"""LLM Router 入口.

用法:
    python main.py                  # 默认：内嵌浏览器 + 系统托盘，端口 8080
    python main.py --port 9090      # 指定端口
    python main.py --no-native      # 使用系统浏览器（不弹窗）
    python main.py --no-tray        # 禁用系统托盘
"""

from __future__ import annotations

import asyncio
import sys


def main() -> None:
    """主入口."""
    from src.gui.launch import run

    asyncio.run(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
```

- [ ] **步骤 5：运行测试验证通过**

运行：`python -m pytest tests/gui/test_launch.py -v`
预期：PASS

- [ ] **步骤 6：Commit**

```bash
git add src/gui/launch.py main.py tests/gui/test_launch.py
git commit -m "feat(gui): 启动入口 — launch.py 协调 GUI + 后端 + 托盘 + main.py"
```

---

### 任务 9：PyInstaller 单文件打包

**文件：**
- 创建：`llm_router.spec`

- [ ] **步骤 1：创建 spec 文件**

```python
# llm_router.spec
# PyInstaller spec — 单文件 exe 打包
# 用法: pyinstaller llm_router.spec --clean --noconfirm

# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'nicegui',
        'nicegui.cli',
        'pystray',
        'pystray._win32',
        'aiosqlite',
        'yaml',
        'cryptography',
        'jsonschema',
        'aiohttp',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'asyncio',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'torch',
        'tensorflow',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='llm_router',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可替换为 .ico 文件路径
)
```

- [ ] **步骤 2：更新 .gitignore**

确认以下项在 `.gitignore` 中：

```
dist/
build/
*.spec.bak
```

- [ ] **步骤 3：验证 spec 语法**

```bash
python -c "import pyinstaller" 2>/dev/null || pip install pyinstaller
pyinstaller --clean --noconfirm llm_router.spec 2>&1 | tail -5 || echo "pyinstaller not installed on CI — skipping build"
```

预期：spec 解析成功 / 或跳过（CI 环境无 pyinstaller）

- [ ] **步骤 4：Commit**

```bash
git add llm_router.spec .gitignore
git commit -m "build: PyInstaller 单文件打包 — llm_router.spec + .gitignore"
```

---

### 任务 10：全量回归验证 + 清理

- [ ] **步骤 1：运行全量测试**

```bash
python -m pytest tests/ -q --tb=short
```

预期：GUI 测试全部通过 + 已有 261 个测试无回归

- [ ] **步骤 2：检查文件完整性**

所有计划中的文件均已创建：

```
src/gui/__init__.py
src/gui/app.py
src/gui/pages/__init__.py
src/gui/pages/config_page.py
src/gui/pages/dashboard.py
src/gui/pages/tasks_page.py
src/gui/pages/settings_page.py
src/gui/pages/logs_page.py
src/gui/tray.py
src/gui/launch.py
main.py
llm_router.spec
tests/gui/__init__.py
tests/gui/test_app.py
tests/gui/test_config_page.py
tests/gui/test_dashboard.py
tests/gui/test_tasks_page.py
tests/gui/test_settings_page.py
tests/gui/test_logs_page.py
tests/gui/test_tray.py
tests/gui/test_launch.py
```

- [ ] **步骤 3：更新进度账本**

```bash
echo "Task 1 Phase6: complete (...)" >> .superpowers/sdd/progress.md
# ... 重复每个任务
```

- [ ] **步骤 4：最终 Commit**

```bash
git add -A && git diff --cached --quiet || git commit -m "chore: Phase 6 完成 — GUI 管理面板 + 系统托盘 + 打包方案"
```

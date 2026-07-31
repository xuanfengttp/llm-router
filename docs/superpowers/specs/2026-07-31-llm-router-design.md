# LLM Router 架构设计文档

> 版本：v0.1.0-draft
> 日期：2026-07-31
> 状态：设计中

---

## 1. 项目概述

智能 Agent 任务调度与 LLM 路由控制系统。核心能力：

1. 多模型连接配置管理与连通性监控
2. LLM API 延迟时序预测（潮汐+随机+可预测性）
3. Agent 任务自动调度控制器（决策+裁判）
4. 安全红线沙箱系统
5. 多 Agent A2A 通信桥接

---

## 2. 架构风格：控制面 + 数据面分离

```
GUI 层 (NiceGUI + pystray)
     │ WebSocket / HTTP
控制平面 (Python asyncio)
     任务调度 │ 路由决策 │ 自动模式 │ 安全审查
     │ 内部 IPC (Unix Socket / localhost TCP)
数据平面 (Python 模型 + Rust 高性能层)
     连接监控(Rust) │ 延迟预测(Py) │ A2A Gateway │ 模型评分DB
```

### 2.1 控制平面（决策中枢）

- 任务调度引擎：优先级队列，根据延迟预测结果和自动模式时间窗口决定任务启动/停止
- 路由决策引擎：根据任务类型和模型评分，匹配最佳模型
- 自动模式时间窗口：工作日晚 9 点到早 9 点 + 周末/节假日全天自动运行
- 安全红线审查器：规则矩阵自动放行 + 可疑操作升级人工审核

### 2.2 数据平面（监控与预测）

- 连接监控器（Rust）：高频延迟探测、连通性检测、吞吐量采集
- 延迟预测引擎（Python）：TFT + Conformal Prediction，输出预测值和可预测性得分
- A2A Gateway：协议适配、子进程管理、Agent 间通信桥接
- 模型评分数据库（SQLite）：公开 benchmark 自动拉取 + 本地实测数据融合

### 2.3 GUI 层

- NiceGUI (Quasar/Material Design)：配置面板、监控仪表板、任务管理、安全审计
- pystray：系统托盘常驻
- WebSocket 实时数据推送

---

## 3. 技术栈

| 组件 | 技术选型 |
|------|----------|
| 主语言 | Python 3.12+ |
| 高性能网络层 | Rust (PyO3 绑定) |
| GUI | NiceGUI + pystray |
| 预测模型 | NeuralForecast (TFT) + Conformal Prediction |
| 通信协议 | A2A + MCP |
| 数据库 | SQLite (本地) + JSON (配置) |
| Agent 进程管理 | asyncio.subprocess |
| 打包发布 | PyInstaller → Windows exe |

---

## 4. 子系统清单

| # | 子系统 | 职责 | 依赖 |
|---|--------|------|------|
| 1 | 连接配置与模型注册中心 | API Key/端点/模型名 CRUD + 连通性测试 | 无 |
| 2 | 延迟监控与预测模型 | 时序数据采集 + TFT 预测 + 可预测性评分 | #1 |
| 3 | 模型评分数据库 | 公开 benchmark 拉取 + 本地实测融合 | #1 |
| 4 | 智能路由引擎 | 任务类型 → 模型匹配 + 实时分发 | #2, #3 |
| 5 | Agent 任务控制器 | 任务队列 + 自动决策 + 裁判 + 时间窗口 | #2, #4 |
| 6 | 安全沙箱/红线系统 | 文件权限矩阵 + 自动放行 + 升级审核 | #5 |
| 7 | A2A 通信层 | 协议适配 + 子进程管理 + Agent 桥接 | #5 |
| 8 | GUI 管理面板 | 配置/监控/任务/审计 + 系统托盘 | 全部 |
| 9 | 运行载体 | PyInstaller 打包 → exe | 全部 |

---

## 5. 数据流

```
[模型 Provider API] ──延迟探测──→ [连接监控器(Rust)] ──时序数据──→ [预测引擎(Py)]
                                                                       │
                                                              ┌─── 预测值(快/慢)
                                                              └─── 可预测性得分(0-1)
                                                                       │
[公开 Benchmark] ──定期拉取──→ [模型评分DB] ◄───────────────────────────┤
                                    │                                  │
                              ┌─── 模型能力分                          │
                              └─── 模型延迟分                          │
                                    │                                  │
[用户任务清单] ────────────────────→ [路由决策引擎] ◄────────────────────┘
                                        │
                                  ┌── 匹配最佳模型
                                  └── 决定启动/停止/等待
                                        │
[Agent 执行层] ◄── A2A Gateway ────────┘
     │
     ├── Claude Code (subprocess)
     ├── Codex CLI (subprocess)
     ├── Gemini CLI (原生 A2A)
     ├── OpenClaw (Gateway Bridge)
     └── Hermes (delegation tool)
```

---

## 6. 模型能力画像与量化路由

### 6.1 模型能力画像 (ModelProfile)

每个模型维护数值能力向量，不使用定性标签：

```yaml
gpt-4o:
  公开Benchmark (自动拉取):
    arena_elo: 1287.5
    coding_swebench: 38.4
    reasoning_mmlu: 88.7
    math_math: 76.6
    instruction_follow: 91.2
    multilingual: 85.3
    tool_use: 89.1
  
  本地监控 (持续采集):
    latency_p50_ms: 320
    latency_p95_ms: 850
    latency_p99_ms: 1800
    predicted_latency_ms: 380
    predictability: 0.82   # 可预测性得分
    throughput_rpm: 120
    error_rate: 0.003
    cost_input_1k: 0.0025
    cost_output_1k: 0.0100
  
  元信息:
    provider: OpenAI
    deployment: cloud
    context_window: 128000
```

### 6.2 任务需求模板 (TaskProfile)

```yaml
代码审查任务:
  需求权重:
    coding: 0.8
    reasoning: 0.6
    instruction: 0.4
  硬约束:
    max_latency_ms: 500
    max_cost_1k: 0.005
    min_context: 64000
```

### 6.3 路由匹配算法

```
Step 1: 硬约束过滤 → 候选模型集
Step 2: Σ(模型能力_i × 任务权重_i) / Σ(权重_i) → 能力得分
Step 3: + 延迟性价比修正 - 成本惩罚 → 最终得分
Step 4: 排序输出最佳匹配
```

---

## 7. 路由决策策略引擎

### 7.1 可插拔策略框架

所有策略实现统一接口 `RoutingStrategy`，GUI 设置页即时切换。

### 7.2 内置策略

| 策略ID | 名称 | 权重分配 (能力:延迟:成本) | 适用场景 |
|--------|------|--------------------------|----------|
| `baseline` | 均衡评分 | 0.4 : 0.3 : 0.3 | 默认通用 |
| `cost_first` | 成本优先 | 0.2 : 0.2 : 0.6 | 预算敏感 |
| `quality_first` | 质量优先 | 0.7 : 0.1 : 0.2 | 关键任务 |
| `latency_aware` | 延迟感知 | 0.3 : 0.6 : 0.1 | 交互式实时任务 |
| `task_specific` | 任务分域 | 按任务类型动态调整 | 混合任务流 |
| `learned` | 学习模型 | ML 模型直接输出 (Phase 3) | 长期演进 |

### 7.3 策略接口

```python
class RoutingStrategy(Protocol):
    strategy_id: str
    display_name: str

    def score(
        self,
        task: TaskProfile,
        candidates: list[ModelProfile],
        predictions: dict[str, LatencyPrediction],
    ) -> list[tuple[ModelProfile, float]]: ...

    def explain(self, task, model, score) -> str: ...
```

---

## 8. 延迟预测模型

### 8.1 数据采集层

- 连接监控器(Rust)每 N 秒对各 Provider 发送探测请求
- 支持 HTTP ping / 小请求实测 / TTFB 三种探测模式
- 时序数据存入 SQLite timeseries 表

### 8.2 特征工程

| 类别 | 特征 |
|------|------|
| 时间特征 | hour_of_day, day_of_week, is_weekend, is_business_hour |
| 统计特征 | rolling_mean/std, lag_1/lag_7/lag_1440, ema_trend |
| 潮汐特征 | is_holiday, time_block, peak_flag, provider |

### 8.3 模型层（三阶段演进）

| 阶段 | 模型 | 输出 |
|------|------|------|
| Phase 1 | TFT (NeuralForecast) | 分位数预测 [p10, p25, p50, p75, p90] |
| Phase 2 | + Conformal Prediction 校准 | 自适应置信区间 |
| Phase 3 | TimesFM/MOIRAI 微调 | 零样本+微调高精度 |

### 8.4 可预测性评分

```
predictability = 1 - (残差方差 / 总方差)
```
按时间段分组计算，输出各时段的规律性/随机性评价。

### 8.5 自学习机制

- **定时重训练**：每天凌晨 3 点取 14 天数据重训练 TFT
- **A/B 切换**：新模型精度优于旧模型才切换
- **漂移检测**：连续 1 小时预测误差 > 3σ → 紧急重训练

---

## 9. Agent 任务控制器

### 9.1 核心职责（仅三件事）

| 职责 | 说明 |
|------|------|
| **分发决策** | 根据延迟预测 + 时间窗口 + 模型匹配，决定何时分发任务 |
| **失败恢复** | 观察任务是否失败(超时/网络/API异常)，决定重试或切换模型 |
| **人工兜底** | 连续失败 N 次 → 暂停等待人工介入 |

> 控制器**不评估任务输出质量**——那是用户/上层系统的职责。

### 9.2 分发决策逻辑

每个决策周期(30s)：
1. 检查延迟预测：目标模型 p50 < 延迟红线 且 可预测性 > 阈值
2. 检查时间窗口：当前是否在自动模式时段内
3. 路由引擎匹配：任务 → 最佳模型
4. 满足全部条件 → 分发执行

### 9.3 失败恢复策略

| 失败类型 | 恢复动作 |
|----------|----------|
| 超时(timeout) | 切换模型重试，最多 3 次 |
| 网络错误 | 等待 30s 重试，同模型 |
| API 限流(429) | 等待 Retry-After 后重试 |
| 认证错误(401/403) | 不重试，立即暂停告警 |
| 连续失败 3 次 | 任务回 standby，等待人工 |

### 9.4 自动模式时间窗口

- 工作日晚 9:00 - 早 9:00：自动运行
- 周末/节假日：全天自动运行
- 白天时段：需人工确认才能分发
- 用户可配置所有时间段

---

## 10. 安全沙箱/红线系统

### 10.1 规则矩阵

| Agent/任务 | 自有文件夹 | 其他任务文件夹 | 系统目录 | 网络 |
|------------|-----------|---------------|---------|------|
| 自有文件夹内 | 全权读写 | 需审核 | 拒绝 | 允许 |
| 跨任务操作 | — | 读写均需审核 | 拒绝 | 允许 |

### 10.2 审核升级机制

- **自动放行**：规则矩阵内明确允许的操作
- **升级人工**：跨文件夹操作、批量删除、可执行文件写入
- **硬拒绝**：系统目录写入、敏感文件访问
- 所有操作记录审计日志

---

## 11. A2A 通信层

### 11.1 三层架构

```
任务控制器 → A2A Gateway
               ├── A2A Server (原生 A2A → Gemini CLI 等)
               ├── CLI Driver (子进程 → Claude Code / Codex)
               └── Bridge Adapter (WebSocket → OpenClaw)
```

### 11.2 三阶段路径

| 阶段 | 方案 | 覆盖 Agent |
|------|------|-----------|
| 短期 | asyncio.subprocess + stdin/stdout | Claude Code, Codex |
| 中期 | + A2A SDK + OpenClaw Gateway | + Gemini, OpenClaw |
| 长期 | 全 A2A 原生 | 全部 |

---

## 12. GUI 管理面板 (NiceGUI)

### 12.1 页面结构

| 页面 | 功能 |
|------|------|
| 连接配置 | Provider/模型 CRUD、连通性测试、延迟实时显示 |
| 监控仪表板 | ECharts 延迟曲线、预测面板、Provider 状态指示灯 |
| 任务管理 | 三队列(待分发/执行中/失败)、分发日志、自动模式开关 |
| 设置 | 路由策略切换、时间窗口配置、红线规则矩阵、模型评分拉取频率 |
| 日志/审计 | 安全审计日志、任务分发/重试/失败记录、模型切换记录 |

### 12.2 系统托盘

- pystray 实现，常驻 Windows 托盘
- 右键菜单：显示主窗口 / 切换自动模式 / 退出
- 状态提示：当前活跃任务数 + 延迟总体状态

---

## 13. 运行载体

### 13.1 打包方案

- PyInstaller 打包为单个 Windows exe
- Rust 监控模块编译为 .pyd/.dll，随包分发
- 目标：单文件 < 120MB

### 13.2 启动流程

```
LLMRouter.exe 启动
  → 加载配置文件 (config.yaml)
  → 启动数据平面 (监控采集 + 预测模型加载)
  → 启动控制平面 (任务调度 + 安全审查)
  → 启动 A2A Gateway
  → 启动 GUI (NiceGUI 内嵌浏览器)
  → 系统托盘就绪
```

---

## 14. 完整子系统总览

| # | 子系统 | 职责 | 输入 | 输出 | 技术 |
|---|--------|------|------|------|------|
| 1 | 连接配置中心 | Provider/模型 CRUD + 连通测试 | 用户配置 | 模型注册表 | YAML + SQLite |
| 2 | 延迟监控 | 高频延迟探测 | Provider API | 时序数据 | Rust + HTTP ping |
| 3 | 延迟预测 | 时序建模 + 可预测性评分 | 时序数据 | 预测值 + 得分 | TFT + Conformal |
| 4 | 模型评分 | benchmark 拉取 + 本地融合 | 公开数据+实测 | 能力向量 | 爬虫 + SQLite |
| 5 | 路由引擎 | 任务→模型匹配分发 | 任务+模型画像 | 最优模型 | 可插拔策略 |
| 6 | 任务控制器 | 分发决策 + 失败恢复 | 预测+任务列表 | 分发/重试指令 | asyncio 状态机 |
| 7 | 安全沙箱 | 文件权限审核 | Agent 操作请求 | 放行/审核/拒绝 | 规则矩阵 |
| 8 | A2A Gateway | Agent 通信桥接 | 任务指令 | Agent 状态 | a2a-sdk + subprocess |
| 9 | GUI 面板 | 可视化管理 | 用户操作 | UI 渲染 | NiceGUI + ECharts |
| 10 | 运行载体 | 打包分发 | 源码 | exe | PyInstaller |

---

## 15. 构建顺序

| 阶段 | 子系统 | 理由 |
|------|--------|------|
| Phase 1 | #1 连接配置 | 数据基础，其他模块都依赖它 |
| Phase 2 | #2 延迟监控+预测 | 核心差异化能力，需要先行验证 |
| Phase 3 | #3 模型评分 + #4 路由引擎 | 基于 #1 #2 的智能层 |
| Phase 4 | #5 任务控制器 + #6 安全红线 | 核心业务逻辑 |
| Phase 5 | #7 A2A 通信层 | 连接外部 Agent |
| Phase 6 | #8 GUI + #9 打包 | 对外交付形态 |

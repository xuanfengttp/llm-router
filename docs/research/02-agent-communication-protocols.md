# Agent 间通信协议与互通方案调研

> 日期：2026-07-31
> 调研范围：A2A、MCP、ACP 协议及各主流 Agent 通信接口

---

## 1. 核心协议对比

| 协议 | 定位 | 成熟度 | 主导方 |
|------|------|--------|--------|
| **A2A** | Agent-to-Agent 任务委托 | v1.0 生产就绪 | Google |
| **MCP** | Agent-to-Tool 能力扩展 | 广泛采用 | Anthropic |
| **ACP** | 联邦式 A2A 编排 | 研究阶段 | 学术界 |
| **ANP** | Agent Network Protocol | 早期 | 社区 |

> **结论**：A2A + MCP 组合正在成为事实标准，互补而非竞争。

---

## 2. 各 Agent 通信接口现状

| Agent | 可编程控制 | 通信方式 |
|-------|-----------|----------|
| **OpenClaw** | 最好 | Gateway Bridge Protocol (WebSocket) |
| **Claude Code** | 中等 | Hooks 系统 + subprocess stdin/stdout |
| **Codex CLI** | 中等 | `codex exec` 非交互模式 |
| **Gemini CLI** | 开发中 | headless daemon (PR 未合并) |
| **Hermes** | 有限 | delegation tool，A2A 计划中 |

---

## 3. 推荐方案：三层控制平面

```
LLM Router Controller
    ├── Scheduler（任务分发）
    ├── Monitor（状态监控）
    └── Result Collector（结果收集）
            │
    Agent Control Plane
    ├── A2A Bridge（原生 A2A Agent）
    ├── CLI Driver（子进程管理）
    └── Hook Router（事件桥接）
            │
    Agent 层
    ├── Gemini CLI（原生 A2A）
    ├── Claude Code（subprocess + hooks）
    ├── Codex CLI（subprocess + exec）
    ├── OpenClaw（Gateway Bridge）
    └── Hermes（delegation tool）
```

---

## 4. 三阶段实施路径

| 阶段 | 方案 | 说明 |
|------|------|------|
| **短期** | 子进程管理 + CLI 管道 | asyncio.subprocess 管理，进程信号控制终止 |
| **中期** | A2A + MCP 双协议 | a2a-sdk 标准分发 + A2A Bridge 包装非 A2A Agent |
| **长期** | 全 A2A 原生 | 等待 Claude Code/Codex 原生支持 A2A |

---

## 5. Python 可用框架

| 框架 | 成熟度 | 说明 |
|------|--------|------|
| **a2a-sdk** | 高 | A2A 官方 Python SDK，v1.x 稳定 |
| **AG2 (原 AutoGen)** | 高 | 原生集成 A2A，完整编排框架 |
| **Aegis** | 中 | 多 Agent meta-harness，MCP inbox 机制 |

---

## 6. 关键风险

1. Claude Code 进程级控制不够精细（只能 stdin/stdout + hooks）
2. A2A cancel 语义依赖 Agent 配合
3. Gemini CLI headless 模式尚未稳定
4. Codex App Server API 未完全公开

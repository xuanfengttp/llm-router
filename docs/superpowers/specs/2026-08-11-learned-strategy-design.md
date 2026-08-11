# Phase 6: Learned 路由策略 — 设计

日期: 2026-08-11

## 1. 核心定位

Learned 策略与预测引擎**完全解耦**。预测引擎负责延迟预测（已有完整闭环），
Learned 策略负责**消费预测数据做路由决策**。

与现有 5 种策略的关键区别：
- 延迟输入：用预测引擎的 **p50（动态 + RL 修正）**，而非静态 `local_metrics.latency_p50_ms`
- 可信度感知：`predictability` 低时降权延迟维度
- 风险惩罚：`p90 - p50` 差距大时对模型扣分
- 能力匹配：全维度 capability_vector + task.weights 精准匹配

**不需要训练，不需要任务反馈，模型文件不存在。**

## 2. 评分算法

```
score = w_cap × cap_score + w_lat × lat_score + w_cost × cost_score
```

### 2.1 能力得分（cap_score）

```
cap_score = Σ(task.weights[dim] × model.capability[dim]) / Σ(weights) / 100
```

- 如果 task 无权重，默认用 arena_elo 单一维度
- 全维度支持：coding / reasoning / math / instruction / multilingual / tool_use / arena_elo

### 2.2 延迟得分（lat_score）

```
lat_score = 1.0 - min(p50 / max_latency, 1.0)    # 延迟越低越好
```

- p50 来自 predictions dict（预测引擎输出），不是 static 快照
- 如果 predictions 中无此模型数据，回退到 local_metrics.latency_p50_ms

### 2.3 成本得分（cost_score）

```
cost_score = 1.0 - min(avg_cost / max_cost, 1.0)
```

- 与现有策略一致

### 2.4 可信度调整

```
lat_weight_effective = w_lat × predictability
risk_penalty = min((p90 - p50) / p50, 1.0) × 0.15   # 最多扣 0.15
cap_weight_effective = w_cap + (w_lat - lat_weight_effective)  # 延迟降权转给能力

final_score = cap_weight_effective × cap_score
            + lat_weight_effective × lat_score
            + w_cost × cost_score
            - risk_penalty
```

### 2.5 权重配置

| 维度 | 权重 |
|------|------|
| w_cap | 0.4 |
| w_lat | 0.35 |
| w_cost | 0.25 |

权重固定，动态性来自**输入数据的实时变化**（预测引擎不断更新）。

## 3. 模块

| 文件 | 类 | 说明 |
|------|-----|------|
| `src/routing/strategy.py` | `LearnedStrategy` | 实现 RoutingStrategy 协议 |
| `tests/routing/test_strategy.py` | `TestLearnedStrategy` | 测试 |

## 4. 接口

```python
class LearnedStrategy:
    strategy_id = "learned"
    display_name = "智能路由"

    def score(task, candidates, predictions) -> list[tuple[ModelProfile, float]]:
        # predictions: dict[str, LatencyPrediction]
        # key = f"{provider}/{model}"
```

## 5. 回退

- predictions 为空 → 等价 BaselineStrategy 行为（用 local_metrics）
- 单个模型无预测数据 → 延迟维度回退到 local_metrics，零可信度

## 6. 测试策略

- test_predictions_used: 有预测数据时用 p50 而非 static latency
- test_fallback_no_predictions: 无预测数据时回退到 local_metrics
- test_predictability_discount: predictability=0 → 延迟权重接近 0
- test_risk_penalty: p90-p50 大 → 扣分
- test_task_weights_used: 任务权重影响能力得分排序
- test_strategy_id_and_name: 基本协议
- test_score_returns_sorted_list: 分数降序

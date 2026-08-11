# 预测引擎升级设计

日期: 2026-08-11
状态: 设计中

## 1. 概述

将当前"每模型独立 TFT"架构升级为**单一通用预测模型**，支持：
- 短期预测（EWMA，10-30min 路由决策）
- 长期预测（TFT 多序列，日/周潮汐模式）
- RL 在线修正（实测 vs 预测残差反馈）
- 数据门槛保护（不足时不预测）
- 模型持久化（训练后即存盘，启动时加载）

## 2. 架构

```
PredictionEngine (orchestrator)
├── DataGate          ← 每序列独立检查数据门槛
├── ShortTermPredictor ← EWMA 自适应平滑 + 趋势分量
├── LongTermPredictor  ← TFT 多序列训练（NeuralForecast optional）
├── RLCorrector        ← 实测 vs 预测残差 → 修正输出
└── ModelStore         ← 持久化/加载 ~/.llm_router/data/models/
```

### 2.1 数据流

```
latency_history (ALL provider/model combos)
  → DataGate: 每个序列独立检查 ≥ min_data_points (默认 100)
     ├─ < 阈值: 返回 None（不预测）
     └─ ≥ 阈值: 继续
  → FeatureExtractor.extract() → 纯时间序列特征（无 model identity 特征）
  → ShortTermPredictor.predict(): 每序列 EWMA 短期预测
  → LongTermPredictor.train(all_sequences): 多序列 TFT 训练
     unique_id = f"{provider}/{model}" 仅用作序列分隔符
  → RLCorrector.correct(): 拿 latency_history 最新实测 vs 上次预测
  → ModelStore.save(): 训练完成后持久化
```

## 3. 模块设计

### 3.1 DataGate

职责：每个序列独立检查数据量是否达标。

```python
class DataGate:
    def __init__(self, min_data_points: int = 100):
        self.min = min_data_points

    def check(self, records: list) -> bool:
        """单序列是否满足预测阈值"""
        return len(records) >= self.min

    def check_multi(
        self, data: dict[str, dict[str, list]]
    ) -> dict[str, dict[str, bool]]:
        """批量检查，返回每个序列是否可以预测"""
```

逻辑：
- `check()` 返回 True/False，调用方据此决定是否传递到预测器
- 不满足阈值的序列会被跳过，返回 None

### 3.2 ShortTermPredictor (EWMA)

职责：轻量短期预测，不依赖 neuralforecast，始终可用。

**公式**：
```
EWMA(t) = α * y(t) + (1-α) * EWMA(t-1)
趋势(t) = β * slope(recent_N_observations)
预测(t+h) = EWMA(t) + 趋势(t) * h
```

**参数**：
- `alpha`: 平滑系数，默认 0.3（30% 权重给最新观测）
- `trend_window`: 趋势计算窗口，默认 6（最近 6 个观测点）
- `horizon`: 预测步长，默认 2（短期 1-2 步，30-60min）

**分位数估计**：
- p50 = 预测值
- p25/p75 = 预测值 ± 0.674 * 残差 std
- p10/p90 = 预测值 ± 1.282 * 残差 std

**无需持久化**：EWMA 状态极轻（几个浮点数），每次从数据重新计算即可。

### 3.3 LongTermPredictor (TFT)

职责：捕捉日/周潮汐模式，多序列训练一个通用模型。

**多序列训练**：
```python
class LongTermPredictor:
    def train(self, data: pd.DataFrame) -> None:
        """
        data 包含多序列：
        - unique_id: "openai/gpt-4o", "anthropic/claude-3", ...
        - ds: 时间戳
        - y: 延迟值
        - 时间特征: hour_of_day, day_of_week, is_weekend
        - 统计特征: rolling_mean_6, rolling_std_6
        - lag 特征: lag_1, lag_2, lag_12
        """
        # unique_id 仅传递给 NeuralForecast 做序列分割
        # 不在特征中编码 model identity
```

**参数**：
- `horizon`: 48（24 小时，30min 间隔）
- `lookback`: 96（48 小时）
- `hidden_size`: 32
- `n_head`: 4
- `dropout`: 0.1
- `max_steps`: 100
- `learning_rate`: 1e-3

**兼容性**：neuralforecast 是可选依赖 `[predict]`。未安装时 LongTermPredictor 创建为 None，仅使用 ShortTermPredictor。

### 3.4 RLCorrector

职责：利用最近实测数据修正预测偏差。

**触发时机**：每次 `latency_history` 中有新的实测数据时（用户发请求 → 获得实际延迟 → 与之前预测对比）。

**公式**：
```
最近 K 次残差: residuals[i] = actual_i - predicted_i  (i = last K probes)
平均偏差:      bias = mean(residuals)
趋势分量:      alpha = linear_regression_slope(residuals)

修正预测: y_corrected[h] = y_pred[h] + bias + alpha * h
```

**修正策略**：
- K 默认 10（最近 10 次探测的残差）
- 残差太旧会被忽略（超过 30 分钟的观测不用）
- `clamp(y_corrected, 0, None)` — 延迟不能为负

**状态**：每个序列维护独立的 `RLCorrector` 实例，存储最近 K 个残差。不持久化（重启后重新积累）。

### 3.5 ModelStore

职责：TFT 模型的持久化与加载。

**存储位置**：`~/.llm_router/data/models/long_term_predictor.pkl`

**操作**：
- `save()`: 调用 `LatencyPredictor.save()`
- `load()`: 调用 `LatencyPredictor.load()`，文件不存在返回 None
- 训练完成后自动调用 `save()`
- 启动时自动调用 `load()`

**文件结构**：
```python
{
    "horizon": int,
    "lookback": int,
    "model": NeuralForecast,  # pickle
    "trained_at": str,         # ISO datetime
    "data_points_total": int,  # 训练时使用的总数据点数
}
```

## 4. PredictionEngine 重构

对外 API 保持兼容，内部使用新模块。

```python
class PredictionEngine:
    def __init__(self, ...):
        self._gate = DataGate(min_data_points=100)
        self._short_term = ShortTermPredictor(horizon=2, alpha=0.3)
        self._long_term = None  # 延迟初始化
        self._corrector = RLCorrector()
        self._store = ModelStore()

    def predict_for_model(
        self, provider, model, records
    ) -> LatencyPrediction | None:
        if not self._gate.check(records):
            return None

        # 短期: EWMA
        short = self._short_term.predict(records)

        # 长期: TFT（如果可用）
        long = self._long_term.predict(...) if self._long_term else None

        # RL 修正
        corrected = self._corrector.correct(provider, model, short, long)

        return LatencyPrediction(...)

    def update_from_observation(
        self, provider, model, actual_latency, predicted_at
    ):
        """收到实测延迟后，更新 RL 修正器"""
        self._corrector.feed(provider, model, actual_latency, predicted_at)
```

## 5. 兼容性

| 组件 | 变更 | 对外影响 |
|------|------|---------|
| `LatencyPrediction` dataclass | 不变 | 无 |
| `PredictionEngine.predict_for_model()` | 签名不变，内部重构 | 无 |
| `PredictionEngine.predict_all()` | 签名不变 | 无 |
| `PredictabilityScore` | 不变 | 无 |
| `FeatureExtractor` | 不变（已经是纯时间序列特征） | 无 |
| `LatencyPredictor` | 保留，增加多序列训练支持 | 内部 |
| `LatencyRecord` | 不变 | 无 |

## 6. 测试策略

| 测试 | 内容 |
|------|------|
| `test_data_gate` | 阈值边界（99/100/101），空序列 |
| `test_short_term_predictor` | EWMA 计算正确性，分位数单调性 |
| `test_long_term_predictor` | 多序列训练/预测，无 neuralforecast 降级 |
| `test_rl_corrector` | 残差计算，修正偏差，clamp 逻辑 |
| `test_model_store` | 保存/加载/文件不存在 |
| `test_engine_integration` | 端到端：低数据量不预测，正常流程，RL 修正 |

## 7. 风险与缓解

| 风险 | 缓解 |
|------|------|
| TFT 多序列训练时间随模型数增长 | 限制 unique_id 数量（默认最多 20 个序列），超量采样 |
| RL 修正器误修正（某次异常延迟） | 残差窗口 + 中位数鲁棒估计（后续优化） |
| pickle 跨版本不兼容 | 加载失败时丢弃旧模型，重新训练 |
| neuralforecast 版本升级破坏 API | `[predict]` 依赖固定版本范围 |

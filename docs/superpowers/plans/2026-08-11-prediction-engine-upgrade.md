# 预测引擎升级 — 实现计划

规格: `docs/superpowers/specs/2026-08-11-prediction-engine-upgrade-design.md`
分支: `feature/prediction-engine-upgrade`

## 目标

将"每模型独立 TFT"升级为"单一通用预测模型"：短期 EWMA + 长期 TFT 多序列 + RL 在线修正 + 数据门槛 + 持久化。对外 API 保持兼容。

## 任务清单

### 任务 1: DataGate — 数据门槛检查 [TDD]

**文件**: `src/prediction/data_gate.py`

**测试**: `tests/prediction/test_data_gate.py`
- `test_check_below_threshold` — 99 点 → False
- `test_check_at_threshold` — 100 点 → True
- `test_check_above_threshold` — 101 点 → True
- `test_check_empty` — 0 点 → False
- `test_check_multi` — 批量返回每序列布尔值

**实现**:
```python
class DataGate:
    def __init__(self, min_data_points: int = 100): ...
    def check(self, records: list) -> bool: ...
    def check_multi(self, data) -> dict[str, dict[str, bool]]: ...
```

**验证**: `pytest tests/prediction/test_data_gate.py -v`

---

### 任务 2: ShortTermPredictor — EWMA 短期预测 [TDD]

**文件**: `src/prediction/short_term.py`

**测试**: `tests/prediction/test_short_term.py`
- `test_predict_returns_quantiles` — 返回 5 个分位数且单调递增
- `test_predict_positive` — 所有分位数 > 0
- `test_predict_follows_trend` — 上升趋势数据 → 预测值 > 末值
- `test_insufficient_data` — < 2 点 → None
- `test_predict_horizon_length` — 输出与 horizon 步数一致

**实现**:
```python
class ShortTermPredictor:
    def __init__(self, horizon=2, alpha=0.3, trend_window=6): ...
    def predict(self, records: list[LatencyRecord]) -> dict[str, list[float]] | None:
        # EWMA + 线性趋势; p50=pred, p25/75=pred±0.674σ, p10/90=pred±1.282σ
```

**验证**: `pytest tests/prediction/test_short_term.py -v`

---

### 任务 3: RLCorrector — RL 在线修正 [TDD]

**文件**: `src/prediction/rl_corrector.py`

**测试**: `tests/prediction/test_rl_corrector.py`
- `test_feed_and_correct` — feed 残差后修正值偏移
- `test_correct_clamp_negative` — 修正后不出现负数
- `test_correct_empty` — 无残差数据 → 返回原值
- `test_correct_stale_residual_ignored` — 超时残差不计入
- `test_per_series_isolation` — 不同 (provider, model) 残差互不影响

**实现**:
```python
class RLCorrector:
    def __init__(self, window=10, max_age_seconds=1800): ...
    def feed(self, provider, model, actual, predicted): ...
    def correct(self, provider, model, predictions: list[float]) -> list[float]:
        # bias=mean(residuals), alpha=lr_slope(residuals)
        # y_corr[h] = y_pred[h] + bias + alpha*h; clamp≥0
```

**验证**: `pytest tests/prediction/test_rl_corrector.py -v`

---

### 任务 4: ModelStore — 持久化 [TDD]

**文件**: `src/prediction/store.py`

**测试**: `tests/prediction/test_model_store.py`
- `test_save_and_load_roundtrip` — 存再取，模型可用
- `test_load_nonexistent` — 文件不存在 → None
- `test_save_creates_file` — 保存后文件存在
- `test_corrupt_file_returns_none` — 损坏 pickle → None（不抛异常）

**实现**:
```python
class ModelStore:
    def __init__(self, base_dir=None):  # 默认 ~/.llm_router/data/models/
        ...
    def save(self, predictor) -> None: ...
    def load(self) -> LatencyPredictor | None: ...
```

**验证**: `pytest tests/prediction/test_model_store.py -v`

---

### 任务 5: LongTermPredictor — TFT 多序列训练 [TDD]

**文件**: 修改 `src/prediction/model.py`（增加多序列训练方法）

**测试**: `tests/prediction/test_model.py`（新增）
- `test_train_multi_series` — 多 unique_id 数据可训练并预测
- `test_predict_returns_quantiles` — 单序列预测返回 5 分位数
- `test_predictability_range` — 评分 ∈ [0, 1]
- `test_no_neuralforecast_graceful` — 未安装时 LongTermPredictor 可用性降级标记

**实现**: 在 `LatencyPredictor` 增加 `train_multi(df)` 接受多 unique_id DataFrame；保持单序列 `train()` 向后兼容。LongTermPredictor 作为 `LatencyPredictor` 的薄包装（封装 horizon=48, lookback=96 默认值 + multi-series API）。

**验证**: `pytest tests/prediction/test_model.py -v`（需 `[predict]` 依赖；CI 无依赖时该测试 skip）

---

### 任务 6: PredictionEngine 重构 — 串联所有模块 [TDD]

**文件**: 修改 `src/prediction/engine.py`

**测试**: 修改 `tests/prediction/test_engine.py`
- 保留现有 `test_insufficient_data_returns_none`（DataGate 接管）
- 保留 `test_predict_for_model`（短期路径必须通过，无需 neuralforecast）
- 保留 `test_predict_providers`
- 新增 `test_predict_uses_short_term_only_when_no_neuralforecast` — 验证降级
- 新增 `test_update_from_observation_feeds_rl` — feed 实测后修正偏移
- 新增 `test_persistence_save_after_train` — 训练后 ModelStore 文件存在

**实现**:
```python
class PredictionEngine:
    def __init__(self, horizon=2, lookback=96, min_data_points=100,
                 enable_long_term=True):
        self._gate = DataGate(min_data_points)
        self._short = ShortTermPredictor(horizon=horizon)
        self._long = LongTermPredictor() if enable_long_term and neuralforecast_available() else None
        self._rl = RLCorrector()
        self._store = ModelStore()
        self._long = self._store.load() or self._long  # 启动加载

    def predict_for_model(self, provider, model, records) -> LatencyPrediction | None:
        if not self._gate.check(records): return None
        short_q = self._short.predict(records)  # 始终可用
        long_q = self._long.predict_multi(...) if self._long else short_q
        corrected = self._rl.correct(provider, model, primary_q)
        return LatencyPrediction(...)

    def predict_all(self, data) -> dict[...]: ...  # 签名不变

    def update_from_observation(self, provider, model, actual, predicted):
        self._rl.feed(provider, model, actual, predicted)

    def train_long_term(self, data) -> None:
        """多序列训练并持久化"""
        ...
        self._store.save(self._long)
```

**验证**: `pytest tests/prediction/test_engine.py -v`

---

### 任务 7: 全量验证

```bash
pytest tests/prediction/ -v
pytest tests/ -v  # 确保未破坏其他模块
ruff check src/prediction/
```

**完成标准**:
- 所有预测测试通过
- 全量测试无回归
- 无 neuralforecast 时短期预测路径仍工作
- 模型文件正确持久化与加载

---

## 执行顺序

1 → 2 → 3 → 4 → 5 → 6 → 7（严格顺序，每步 TDD: 先红后绿）

## 风险控制

- 任务 5 依赖 `neuralforecast`（可选），CI 无依赖时该测试 skip，不阻塞主流程
- 任务 6 重构必须保持 `predict_for_model` / `predict_all` 签名不变，避免影响 `routing/` 调用方
- 每个任务完成后立即跑该任务测试 + ruff，不过夜

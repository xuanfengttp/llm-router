# LLM API 延迟预测 SOTA 深度模型方案调研

> 日期：2026-07-31
> 调研范围：时序预测 SOTA 模型、基础模型、不确定性量化

---

## 1. 时序预测 SOTA 模型全景

### 1.1 专用 Transformer 模型（需训练）

| 模型 | 论文/会议 | 核心思路 | 优点 | 缺点 |
|------|-----------|----------|------|------|
| **PatchTST** | ICLR 2023 | 将时序切分成 patch 作为 Transformer token，自监督预训练 | 长序列建模强；Channel-independent 简单高效 | 忽略变量间交互；非原生概率输出 |
| **iTransformer** | ICLR 2024 Spotlight | 倒置 Transformer：变量维度作为 token | 多变量交互建模极强 | 长序列计算量大 |
| **TimesNet** | ICLR 2023 | 1D 时序 reshape 为 2D 张量，CNN 捕捉多周期 | 多周期建模强（潮汐特征） | 计算开销比 PatchTST 大 |
| **DLinear** | AAAI 2023 Oral | 简单线性层+分解超越 Transformer | 极简单、极快 | 表达能力有限 |

仓库：https://github.com/thuml/Time-Series-Library（清华，一站集成）

### 1.2 时序基础模型（零样本/微调）

| 模型 | 发布方 | 规模 | 概率输出 | 关键特征 |
|------|--------|------|----------|----------|
| **TimesFM 2.5** | Google | 200M | 点预测 | 最新版，长上下文，零样本极强 |
| **Chronos** | Amazon | 8M-710M | 多分位数 | T5 架构，tokenize 时序 |
| **MOIRAI 2.0** | Salesforce | 多尺寸 | 任意分布 | uni2ts 框架，masked encoder |
| **Lag-Llama** | 学术联合 | 基础 | Student-t 分布 | 首个开源时序基础模型 |
| **MOMENT** | CMU | 多尺寸 | 多任务 | 通用时序表示学习 |

---

## 2. "多变量 + 潮汐周期 + 在线学习"最佳匹配

- **多变量**：iTransformer 天然支持（每 Provider 一变量）
- **潮汐周期**：TimesNet（2D 周期建模）、Lag-Llama（显式 lag features）
- **在线学习**：滚动窗口重训练（最实用），OnsitNet/ODEStream 做真在线学习

---

## 3. 不确定性输出方案

**推荐**：TFT 分位数回归 + Conformal Prediction 层做自适应校准

可预测性得分 = 1 - (残差方差 / 总方差)

---

## 4. LLM API 延迟预测相关工作

| 工作 | 出处 | 相关性 |
|------|------|--------|
| **PreServe** | ICSE 2026 Distinguished Paper | 最高——直接做 LLM 服务延迟预测 |
| **RouteLLM** | arXiv:2406.18665 | LLM 路由器延迟感知调度 |
| **SEISMOGRAPH** | GitHub 开源 | LLM provider drift 预警系统 |

---

## 5. Python 生态成熟度

| 库 | 成熟度 | pip install | 概率预测 |
|----|--------|-------------|----------|
| **NeuralForecast (Nixtla)** | 极高 | ✅ | 部分（TFT, DeepAR） |
| **Darts (Unit8)** | 极高 | ✅ | 部分 |
| **GluonTS (Amazon)** | 高 | ✅ | **原生支持最好** |
| **chronos-forecasting** | 中 | HuggingFace | 多分位数 |
| **timesfm** | 中 | ✅ | 点预测 |
| **uni2ts** | 中 | ✅ | 任意分布 |
| **Lag-Llama** | 中 | HuggingFace | 概率 |

---

## 6. 推荐技术路线（三阶段）

| 阶段 | 内容 | 周期 |
|------|------|------|
| **Phase 1: Baseline** | TFT (NeuralForecast) + 分位数回归 + 可预测性指标 | 1-2 周 |
| **Phase 2: 增强** | Conformal Prediction + 多 Provider 联合建模 | 2-4 周 |
| **Phase 3: 前沿** | TimesFM/MOIRAI 微调 + 协变量注入 | 持续演进 |

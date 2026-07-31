from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class BenchmarkData:
    """公开 Benchmark 数值，从 Chatbot Arena / OpenRouter 自动拉取.

    所有分数归一化到 0-100 或标准 ELO 尺度。
    """

    arena_elo: float = 0.0
    coding_swebench: float = 0.0
    reasoning_mmlu: float = 0.0
    math_math: float = 0.0
    instruction_follow: float = 0.0
    multilingual: float = 0.0
    tool_use: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "arena_elo": self.arena_elo,
            "coding_swebench": self.coding_swebench,
            "reasoning_mmlu": self.reasoning_mmlu,
            "math_math": self.math_math,
            "instruction_follow": self.instruction_follow,
            "multilingual": self.multilingual,
            "tool_use": self.tool_use,
        }


@dataclass(frozen=True, slots=True)
class LocalMetrics:
    """本地持续监控指标."""

    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    predicted_latency_ms: float = 0.0
    predictability: float = 0.0
    throughput_rpm: float = 0.0
    error_rate: float = 0.0

    def with_latency(
        self, p50_ms: float, p95_ms: float, p99_ms: float
    ) -> LocalMetrics:
        return LocalMetrics(
            latency_p50_ms=p50_ms,
            latency_p95_ms=p95_ms,
            latency_p99_ms=p99_ms,
            predicted_latency_ms=self.predicted_latency_ms,
            predictability=self.predictability,
            throughput_rpm=self.throughput_rpm,
            error_rate=self.error_rate,
        )


@dataclass(frozen=True, slots=True)
class ModelProfile:
    """模型能力画像：公开 benchmark + 本地监控 + 元信息."""

    provider: str
    model: str
    deployment: str  # "cloud" | "local" | "hybrid"
    context_window: int
    cost_input_1k: float
    cost_output_1k: float
    benchmark: BenchmarkData = field(default_factory=BenchmarkData)
    local_metrics: LocalMetrics = field(default_factory=LocalMetrics)

    def capability_vector(self) -> dict[str, float]:
        """提取能力向量，用于路由匹配."""
        bm = self.benchmark
        return {
            "coding": bm.coding_swebench,
            "reasoning": bm.reasoning_mmlu,
            "math": bm.math_math,
            "instruction": bm.instruction_follow,
            "multilingual": bm.multilingual,
            "tool_use": bm.tool_use,
            "arena_elo": bm.arena_elo,
        }

    def with_local_metrics(self, metrics: LocalMetrics) -> ModelProfile:
        return ModelProfile(
            provider=self.provider,
            model=self.model,
            deployment=self.deployment,
            context_window=self.context_window,
            cost_input_1k=self.cost_input_1k,
            cost_output_1k=self.cost_output_1k,
            benchmark=self.benchmark,
            local_metrics=metrics,
        )


class BenchmarkFetcher:
    """公开 Benchmark 数据拉取器.

    数据源：Chatbot Arena (lmsys) + OpenRouter rankings.
    支持本地缓存，避免频繁拉取。

    用法:
        fetcher = BenchmarkFetcher()
        benchmarks = await fetcher.fetch_all()
        # benchmarks: dict[str, BenchmarkData]
    """

    def __init__(self) -> None:
        self.sources = [
            "https://storage.googleapis.com/lmsys-arena-data/arena_ranking.json",
            "https://openrouter.ai/api/v1/rankings",
        ]

    def _parse_arena_data(self, raw: dict) -> dict[str, BenchmarkData]:
        """解析 Chatbot Arena JSON 格式."""
        results: dict[str, BenchmarkData] = {}
        for model_name, data in raw.items():
            results[model_name] = BenchmarkData(
                arena_elo=float(data.get("arena_score", 0)),
                coding_swebench=float(data.get("coding", 0)),
                math_math=float(data.get("math", 0)),
                reasoning_mmlu=float(data.get("reasoning", 0)),
            )
        return results

    def _parse_openrouter_data(self, raw: dict) -> dict[str, BenchmarkData]:
        """解析 OpenRouter rankings JSON 格式."""
        results: dict[str, BenchmarkData] = {}
        for item in raw.get("data", []):
            slug = item.get("slug", "")
            if not slug:
                continue
            metrics = item.get("metrics", {})
            results[slug] = BenchmarkData(
                coding_swebench=float(metrics.get("coding", 0)),
                reasoning_mmlu=float(metrics.get("reasoning", 0)),
                instruction_follow=float(metrics.get("instruction_following", 0)),
            )
        return results

    def _merge_benchmarks(
        self, sources: list[dict[str, BenchmarkData]]
    ) -> dict[str, BenchmarkData]:
        """多数据源融合：同字段取平均，独有字段保留."""
        merged: dict[str, dict[str, list[float]]] = {}
        for source in sources:
            for model_name, bm in source.items():
                if model_name not in merged:
                    merged[model_name] = {}
                for key, value in bm.to_dict().items():
                    if value > 0:  # 只累加有值的字段
                        merged[model_name].setdefault(key, []).append(value)

        result: dict[str, BenchmarkData] = {}
        for model_name, fields in merged.items():
            averaged = {
                k: sum(v) / len(v) for k, v in fields.items()
            }
            result[model_name] = BenchmarkData(**averaged)
        return result

    async def fetch_all(self) -> dict[str, BenchmarkData]:
        """拉取所有数据源并融合."""
        import aiohttp
        results: list[dict[str, BenchmarkData]] = []
        async with aiohttp.ClientSession() as session:
            for url in self.sources:
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        if resp.status == 200:
                            raw = await resp.json()
                            if "arena_score" in str(raw) or "arena_elo" in str(raw):
                                results.append(self._parse_arena_data(raw))
                            else:
                                results.append(self._parse_openrouter_data(raw))
                except Exception:
                    continue  # 单个源失败不影响其他源
        return self._merge_benchmarks(results) if results else {}

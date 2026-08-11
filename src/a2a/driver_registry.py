from __future__ import annotations

from typing import TYPE_CHECKING, Union

from src.a2a.cli_driver import CLIDriver, DriverConfig

if TYPE_CHECKING:
    from src.a2a.card_resolver import AgentCard
    from src.a2a.http_driver import A2ADriver

# Both CLIDriver and A2ADriver share the same launch() interface and
# implement a ``config: DriverConfig`` attribute.
DriverType = Union[CLIDriver, "A2ADriver"]


class DriverRegistry:
    def __init__(self) -> None:
        self._drivers: dict[str, DriverType] = {}

    def register(self, driver: DriverType) -> None:
        self._drivers[driver.config.name] = driver

    def get(self, name: str) -> DriverType | None:
        return self._drivers.get(name)

    def list_all(self) -> list[str]:
        return list(self._drivers.keys())

    def remove(self, name: str) -> None:
        if name not in self._drivers:
            raise KeyError(f"Driver '{name}' not registered")
        del self._drivers[name]

    def register_remote(self, card: AgentCard) -> None:
        """根据 AgentCard 创建 A2ADriver 并注册到 registry。

        AgentCard.url 作为 A2A 服务的 base_url，
        DriverConfig.command 填入 card.url（用于标识来源）。
        """
        from src.a2a.http_driver import A2ADriver

        driver_config = DriverConfig(
            name=card.name,
            command=card.url,
        )
        self.register(A2ADriver(config=driver_config, base_url=card.url))

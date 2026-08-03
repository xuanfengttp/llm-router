from __future__ import annotations

from src.a2a.cli_driver import CLIDriver


class DriverRegistry:
    def __init__(self) -> None:
        self._drivers: dict[str, CLIDriver] = {}

    def register(self, driver: CLIDriver) -> None:
        self._drivers[driver.config.name] = driver

    def get(self, name: str) -> CLIDriver | None:
        return self._drivers.get(name)

    def list_all(self) -> list[str]:
        return list(self._drivers.keys())

    def remove(self, name: str) -> None:
        if name not in self._drivers:
            raise KeyError(f"Driver '{name}' not registered")
        del self._drivers[name]

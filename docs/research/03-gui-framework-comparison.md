# 桌面 GUI 框架选型调研

> 日期：2026-07-31
> 调研范围：Python 跨平台桌面 GUI 方案

---

## 1. 方案对比总览

| 方案 | 开发效率 | UI 美观度 | 实时图表 | 打包体积 | Web 扩展 |
|------|:---:|:---:|:---:|:---:|:---:|
| Electron + Python | 中 | 优 | 优 | 差(300MB+) | 天然 |
| Tauri + Python | 中低 | 优 | 优 | 优(50-80MB) | 天然 |
| PyWebView | 高 | 良 | 良 | 良(40-80MB) | 需适配 |
| **NiceGUI** | **极高** | **良+** | **良** | **良(80-120MB)** | **天然** |
| Streamlit | 极高 | 中 | 差 | 良 | 天然 |
| Flet | 中 | 良 | 中 | 中(80-150MB) | 支持 |
| PySide6/PyQt6 | 低 | 良 | 优 | 良(80-120MB) | 不支持 |

---

## 2. 推荐：NiceGUI

**理由**：

1. **开发效率碾压**：纯 Python，`ui.button()`, `ui.chart()`, `ui.table()` 即可构建 UI
2. **UI 外观达标**：基于 Quasar (Material Design)，暗色模式，ECharts 嵌入可达 Chatbox 水平
3. **实时推送原生支持**：内置 WebSocket，`ui.timer()` + `ui.chart()` 实现实时监控面板
4. **Web 扩展零成本**：同一份代码既是桌面应用又是 Web 服务
5. **打包成熟**：PyInstaller 一键打包，文档完善
6. **社区活跃**：GitHub 12k+ stars，中文教程多

**不足与对策**：

- 系统托盘：NiceGUI 不内置，用 `pystray` 配合
- 服务端往返：对管理面板影响不大（非 60fps 场景）

---

## 3. 备选：Electron + Python FastAPI

适用于 UI 精致度要求极高或有前端工程师的情况。代价是打包体积大（300MB+）和两套技术栈。

---

## 4. 不推荐

- **Streamlit**：每次交互全页刷新，不适合管理面板
- **Flet**：API 不稳定，复杂定制反而麻烦
- **PyWebView**：跨平台兼容性不稳，商业项目风险高
- **PySide6/Qt**：开发效率低，Web 扩展需重写

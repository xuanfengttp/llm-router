# release/

LLM Router 发布产物目录。

## 安装包

在 `release/installers/` 下直接下载安装：

| 安装包 | 说明 |
|--------|------|
| `LLM Router_0.1.0_x64-setup.exe` | NSIS 安装器（推荐） |
| `LLM Router_0.1.0_x64_en-US.msi` | MSI 安装器 |

安装后即可开箱即用，**无需安装 Python 或任何依赖**。

## 构建命令

```bash
# 完整构建（前端 + PyInstaller 后端 + Tauri 安装包）
bash release/build.sh --python

# 仅前端 + Tauri（后端用源码复制，需 Python 环境）
bash release/build.sh
```

## 构建原理

1. **PyInstaller** 将 Python 后端及所有依赖打包为单个 `llm-router-backend.exe`（~25 MB，自包含）
2. **Tauri externalBin** 将该 exe 嵌入 NSIS/MSI 安装包
3. 用户安装后，`llm-router.exe` 自动检测同目录下的 `llm-router-backend.exe` 并启动

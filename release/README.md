# release/

LLM Router 发布产物目录。

每次构建时，`build.sh` 会先清空 `release/llm-router/` 再重新生成，确保发布产物与代码同步。

## 构建命令

```bash
# 完整构建（前端 + Tauri，后端源码复制）
bash release/build.sh

# 附加 Python 打包（前端 + PyInstaller 后端 + Tauri）
bash release/build.sh --python
```

## 产物结构

```
release/
├── build.sh                  # 自动化构建脚本
└── llm-router/
    ├── llm-router.exe         # Tauri 桌面应用（Windows）
    ├── frontend/
    │   └── dist/              # Vite 构建的前端静态文件
    ├── backend/               # Uvicorn + FastAPI 后端
    └── src/                   # 业务逻辑模块
```

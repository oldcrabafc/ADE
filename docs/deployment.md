# 部署与运行

## 安装依赖

```bash
uv sync
```

## 运行

运行统一入口（推荐）：

```bash
uv run python apps/main_app.py
```

运行导入模块（低频，直达）：

```bash
uv run python apps/ingest_app.py
```

运行查询模块（高频）：

```bash
uv run python apps/query_app.py
```

运行固定回归验证：

```bash
uv run python scripts/verify_ade_pro.py
```

## 打包

推荐优先打包统一入口（减少重复依赖打包）：

```bash
pyinstaller apps/main_app.py --onefile --name ADE --noconfirm --clean --exclude-module pyarrow
```

如果偏好目录模式（启动更快，通常更稳定）：

```bash
pyinstaller apps/main_app.py --onedir --name ADE --noconfirm --clean --exclude-module pyarrow
```

打包导入模块（可选）：

```bash
pyinstaller apps/ingest_app.py --onefile --name ADE-Ingest --noconfirm --clean --exclude-module pyarrow
```

打包查询模块：

```bash
pyinstaller apps/query_app.py --onefile --name ADE-Query --noconfirm --clean --exclude-module pyarrow
```

产物：

- ADE.exe（推荐）
- ADE-Ingest.exe（可选）
- ADE-Query.exe（可选）

## 体积优化建议

1. 当前 Parquet 读写走 DuckDB，不依赖 `pyarrow`。
2. 优先单入口打包（`apps/main_app.py`），避免两个 exe 各自携带一份 Qt 依赖。
3. `--onefile` 体积通常更小但启动稍慢；`--onedir` 体积更大但启动更快。
4. DuckDB Excel extension 的离线分发方式仍需在正式 exe 打包前验证。

团队使用建议：

- 普通用户使用 ADE.exe
- 若角色固定，可按需分发 ADE-Ingest.exe / ADE-Query.exe

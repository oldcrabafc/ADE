# ADE Pro

ADE Pro 是面向审计人员的本地数据导入、清洗、查询与规则分析工具。它使用 PySide6 构建桌面界面，以 DuckDB 完成本地清洗和查询，以 Parquet 固化标准 `ledger` 数据集。

核心流程：

```text
Excel 原始数据
  -> 字段映射 / 金额规则 / TOML 配置清洗
  -> DuckDB 清洗生成标准 ledger
  -> Parquet 标准数据集包
  -> DuckDB 连接 Parquet 查询
  -> 可视化查询 / SQL 查询 / 审计规则
  -> 导出
```

## 字段标准

ADE Pro 以 `ledger` 作为主数据模型。字段统一使用英文 `snake_case`，不使用空格、中文或特殊符号，便于 SQL 输入和数据集交换。

最小必填字段：

- `posting_date`
- `voucher_id`
- `ac_code`
- `ac_caption`
- `rc_amount`
- `description`

如果金额依赖借贷标识计算，则 `drcr` 也必须存在。

导入清洗的无效行过滤规则（当前实现）：

- `voucher_id` 为空（去空格后）
- `ac_code` 为空（去空格后）
- `ac_caption` 为空（去空格后）
- `rc_amount` 为空（金额无法转换或借贷标识无法识别）

`posting_date` 和 `description` 当前不作为无效行过滤条件。

## 文档导航

- 项目概览: [docs/overview.md](docs/overview.md)
- 架构与目录: [docs/architecture.md](docs/architecture.md)
- ADE Pro 当前架构说明: [docs/ade-pro-integration.md](docs/ade-pro-integration.md)
- 数据导入规范: [docs/ingest.md](docs/ingest.md)
- 客户导入规则: [docs/client-import-rules.md](docs/client-import-rules.md)
- 查询与导出: [docs/query.md](docs/query.md)
- 部署与运行: [docs/deployment.md](docs/deployment.md)

## 模块定位

- Ingest Module（低频）：Excel/CSV 导入、预览、字段映射、配置清洗、金额标准化、导入报告。
- Dataset Module：生成、注册、打开和分享标准 `ledger` Parquet 数据集包。
- Query Module（高频）：连接已注册数据集，标准账本浏览、可视化查询、SQL 编辑、规则分析、导出。
- Ledger Cleaning Engine：TOML 配置驱动清洗、借贷方向处理、标准字段输出。

## 快速启动

安装依赖：

```bash
uv sync
```

运行导入模块：

```bash
uv run python apps/ingest_app.py
```

运行查询模块：

```bash
uv run python apps/query_app.py
```

运行固定回归验证：

```bash
uv run python scripts/verify_ade_pro.py
```

程序主入口（`apps/main_app.py`）为两个大按钮直达：

- `进入数据导入模块`
- `进入数据查询模块`

导入模块支持两种配置方式：

- 使用配置文件：从项目 `profile/` 目录选择 baseline profile 预填映射
- 不使用配置：默认加载 `profile/ingest_profiles_baseline_不使用配置.toml` 作为 baseline，并允许手动映射调整

无论是否使用配置，开始转换前都必须完成 `required_field`（非金额）与 `amount_rules`（金额）映射。
导入执行仅接受最终确认后的 `IngestProfile`；baseline 仅用于预填，不参与回退执行。

建议在 profile 中使用 `required_field` 声明“非金额必填映射字段”；金额相关字段由 `amount_rules` 按模式独立校验。

当前 UI 行为：

- Step1、Step2、预览映射行、映射弹窗（含金额规则）下拉默认禁用滚轮改值，避免误触
- 映射弹窗右侧纵向滚动条常显并加宽；点击 `OK` 后映射会回写到预览行，再次打开保留上次确认结果
- 导入前校验分开提示 `required_field` 缺失项与 `amount_rules` 缺失项

## 当前原则

- 配置统一使用 TOML，不使用 JSON 作为客户配置格式。
- Excel 导入和清洗主链路使用 DuckDB，不使用 pandas 作为导入和清洗主路径。
- Python 运行环境使用 uv 管理，当前目标为 CPython 3.12。
- Parquet 是 ADE Pro 的标准可交换 `ledger` 数据格式；本机工作时是固化结果，对外协作时是可分享数据包。
- DuckDB 是本地查询和分析引擎，可连接 Parquet 创建 `ledger` 查询入口。
- `rc_amount` 转换后统一为一列金额，借方为正、贷方为负；GUI 中应独立选择金额处理方式。
- 支持字段级前缀规则：`field_rules.<field>.prefix`（例如 `voucher_id/ac_code/vendor_id/customer_id`）。
- `company_id` 表示公司代码、核算主体或法人实体编码，不替代 `client_name`。
- `client_name` 仍表示审计项目或客户名称，仅用于展示和客户隔离路由，不直接作为物理路径。

# License

MIT License

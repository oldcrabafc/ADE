# ADE Pro 当前架构说明

## 产品定位

ADE Pro 是本地优先的财务数据工作台。它把导出的 Excel、CSV 数据转换为标准 `ledger` Parquet 数据集包，再用 DuckDB 连接数据集完成查询、基础规则分析、结果浏览、导出和分享。

```text
原始数据
  -> 预览 / 字段映射 / 金额规则
  -> DuckDB 清洗生成标准 ledger
  -> ledger.parquet + dataset.toml
  -> DuckDB 创建 ledger 查询视图
  -> 可视化查询 / SQL 查询 / 基础规则 / 导出 / 分享
```

## 当前模块

| 模块 | 职责 |
| --- | --- |
| `apps` | 主入口、导入入口、查询入口 |
| `ingest` | 来源预览、字段映射、客户 profile、DuckDB 清洗、导入报告 |
| `dataset` | manifest 读写、最近数据集 registry、Parquet 连接、数据集 ZIP 打包 |
| `query` | SQL 构建、DuckDB 查询、SQL 历史、Excel 导出 |
| `analysis` | 基础规则 SQL 和规则执行服务 |
| `ui_ingest` | 导入页、字段映射对话框、导入报告展示 |
| `ui_query` | 查询页、SQL 编辑器、表格浏览、基础图表占位 |
| `shared` | 数据模型、客户路由、错误类型、常量 |
| `scripts` | 固定回归验证脚本 |

## 标准数据模型

ADE Pro 以 `ledger` 作为主分析表。字段统一使用英文 `snake_case`。原始文件中的中文列名或客户自定义列名只保存在 profile 映射配置里，不进入标准字段命名。

Required 最小字段：

- `posting_date`
- `voucher_id`
- `ac_code`
- `ac_caption`
- `rc_amount`
- `description`

金额依赖借贷标识计算时，来源中还必须能映射出借贷标识字段。

常用 optional 字段：

- `voucher_header`
- `company_id`
- `drcr`
- `lc_amount`
- `vendor_id`
- `vendor_name`
- `customer_id`
- `customer_name`
- `department`
- `employee_id`
- `employee_name`
- `currency`
- `document_type`
- `posting_period`
- `source_system`

`client_name` 表示审计客户或项目，用于展示和客户隔离。`company_id` 表示账本数据内部的公司代码、核算主体或法人实体，两者不能互相替代。

## 数据集包

标准数据集结构：

```text
ABC_2024_Ledger/
  dataset.toml
  ledger.parquet
```

`dataset.toml` 记录：

```toml
schema_version = 1
dataset_name = "ABC 2024 Ledger"
client_name = "ABC Company"
fiscal_year = 2024
row_count = 123456
posting_date_min = "2024-01-01"
posting_date_max = "2024-12-31"
created_at = "2026-05-12T10:30:00"
import_batch_id = "auto-xxxx"
profile_name = "default"
ledger_parquet = "ledger.parquet"
source_file = "raw_ledger.xlsx"
```

查询页可以打开 `dataset.toml` 或裸 `ledger.parquet`。打开 `dataset.toml` 时直接读取 manifest 信息；打开裸 Parquet 时扫描 schema、行数和期间，并在文件内存在 `client_name`、`fiscal_year` 时展示这些信息。

## 查询视图

打开数据集后，DuckDB 会创建 `ledger` 视图：

```sql
CREATE OR REPLACE VIEW ledger AS
SELECT * FROM read_parquet('ledger.parquet');
```

新查询、新模板和新规则使用 `ledger` 字段。`ledger.parquet` 是标准查询数据源，不再把旧账本字段作为主模型。

## 导入链路

当前导入链路不使用 pandas。Excel、CSV 来源统一走 DuckDB 读取和清洗。
导入执行只使用“用户最终确认后的 `IngestProfile`”；baseline 与匹配信息仅用于预填。

导入流程：

1. 选择来源类型和文件。
2. Excel 来源选择 worksheet。
3. 读取前 10 行预览。
4. 在预览表第一行选择标准字段映射。
5. 打开字段映射对话框确认 `required_field`（非金额）、optional 字段和金额规则。
6. 可选择保存为客户 `ingest_profiles.toml`。
7. 输入或确认数据集名称。
8. DuckDB 清洗生成标准 `ledger`。
9. 输出 `ledger.parquet` 和 `dataset.toml`。
10. 注册到最近数据集 registry。
11. 导入报告展示行数、期间、输出路径、字段映射和行级错误明细。

## 金额规则

`rc_amount` 是统一分析金额，借方为正、贷方为负。当前支持三种模式：

| 模式 | 来源结构 | 处理方式 |
| --- | --- | --- |
| `direct_signed_amount` | 一列金额已带方向 | 直接转换为 `rc_amount` |
| `amount_with_drcr` | 借贷标识 + 正数金额 | 借方值转正，贷方值转负 |
| `debit_credit_columns` | 借方金额列 + 贷方金额列 | 借方金额减贷方金额 |

以下情况会进入 `ImportResult.import_errors` 并在导入报告中展示：`voucher_id` 为空、`ac_code` 为空、`ac_caption` 为空、金额无法转换或借贷标识无法识别（即 `rc_amount` 为空）。
`posting_date` 和 `description` 当前不作为无效行过滤条件。

## 客户 Profile

客户 profile 保存在客户隔离目录：

```text
data/clients/client_xxxxxxxx/ingest_profiles.toml
```

profile 保存：

- 来源类型和 Excel sheet。
- 标准字段到来源列名的映射。
- 金额模式和金额字段配置。
- 借方值、贷方值配置。

导入页会按 `required_field`（非金额）和金额规则字段匹配 profile。optional 字段不作为匹配必需列。

## 查询与导出

查询页当前提供：

- 打开 `dataset.toml` 或 `ledger.parquet`。
- 最近数据集列表。
- 当前数据集信息展示。
- 可视化条件生成 `ledger` SQL。
- SQL 编辑器、模板和历史。
- 结果表筛选、分页和列头排序。
- 基础规则：大额、周末、摘要为空。
- 查询结果导出 Excel。
- 数据集 ZIP 分享。

本版不扩展更多规则，也不增强 `ChartViewer`。这两项保留给后续版本。

## 数据集分享

查询页“分享数据集”会生成 ZIP 包：

- 标准数据集：`README.txt`、`dataset.toml`、`ledger.parquet`
- 裸 Parquet：`README.txt`、原 `.parquet` 文件

接收方可直接在 ADE Pro Query 中打开 `dataset.toml` 或 `.parquet` 查询。

## 回归验证

固定验证入口：

```bash
uv run python scripts/verify_ade_pro.py
```

覆盖导入、三种金额模式、错误明细、profile、查询、裸 Parquet、SQL 历史和数据集 ZIP 打包。

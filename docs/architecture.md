# 系统架构与技术选型

## 架构总览

```text
+-------------------------+          +---------------------------+
|   Ingest Module         |          |   Query Module            |
|-------------------------|          |---------------------------|
| File Preview            |          | Ledger Viewer             |
| Header Dropdown Mapping |          | Visual Query              |
| Config Cleaning         |          | SQL Editor                |
| Amount Normalize        |          | Rule Analysis             |
| Import Report           |          | Export                    |
| Dataset Package         |          | Recent Datasets           |
+-----------+-------------+          +------------+--------------+
            |                                     |
            | create/register                     | connect / analyze
            v                                     v
      +-----+-------------------------------------+-----+
      |       Standard Ledger Dataset Package      |
      |       dataset.toml + ledger.parquet        |
      +-----+-------------------------------------+-----+
            |                                     ^
            | queried by DuckDB                   |
            v                                     |
      +-----+-------------------------------------+-----+
      | DuckDB query engine: ledger + journal views|
      +-----+-------------------------------------+-----+
            ^
            |
      +---------+---------+---------+
      |         |         |         |
    Excel      CSV      Existing Dataset
```

模块定位：

- Ingest Module：低频使用，负责导入、预览、字段映射、金额规则、标准化、校验和发布
- Ledger Cleaning Engine：负责配置驱动字段映射、借贷符号处理、金额标准化和标准账本输出
- Dataset Module：负责生成、注册、打开、分享标准 `ledger` Parquet 数据集包
- Query Module：高频使用，负责查询、导出和规则执行
- Shared：统一模型、客户路由、错误码、TOML 配置、数据集 manifest 和 schema 定义

## 技术栈决策

| 主题 | 决策 |
| --- | --- |
| 配置格式 | 统一使用 TOML，不使用 JSON 作为客户配置和数据集 manifest 格式 |
| Excel 导入 | DuckDB 优先，不使用 pandas 作为导入和清洗主路径 |
| 清洗计算 | 优先使用 DuckDB SQL 完成字段映射、类型转换、金额规则和质量统计 |
| 固化格式 | Parquet 是标准 `ledger` 数据的固化和交换格式 |
| 查询引擎 | DuckDB 连接 Parquet，创建 `ledger` 查询视图 |
| 打包约束 | 控制依赖体积，避免 pandas/numpy 成为导入链路的必需依赖 |
| 字段命名 | 标准字段统一使用英文 `snake_case`，不使用空格、中文或特殊符号 |

如果 DuckDB Excel 读取能力在离线打包时存在扩展分发问题，可评估轻量 Excel reader 作为 fallback，但主清洗和查询仍应回到 DuckDB。

## 标准数据模型

ADE Pro 主分析表为 `ledger`。字段统一使用英文 `snake_case`，不使用空格、中文或特殊符号。

标准字段命名规则：

- 英文小写
- 单词之间使用下划线
- 不使用空格
- 不使用中文字段名
- 原始 Excel 中文列名只保存在 TOML 映射配置中，不进入标准 `ledger` schema

建议 `ledger` 表字段：

| 字段 | 说明 |
| --- | --- |
| `posting_date` | 入账日期 / 记账日期 |
| `voucher_id` | 凭证号 |
| `voucher_header` | 凭证抬头 |
| `company_id` | 公司代码 / 核算主体 / 法人实体编码 |
| `ac_code` | 科目编码 |
| `ac_caption` | 科目名称 |
| `drcr` | 借贷标识 |
| `rc_amount` | 记账本位币或分析口径金额 |
| `lc_amount` | 原币金额 |
| `vendor_id` | 供应商编码 |
| `vendor_name` | 供应商名称 |
| `customer_id` | 客户编码 |
| `customer_name` | 客户名称 |
| `description` | 摘要 / 描述 |
| `client_name` | 审计客户或项目名称 |
| `fiscal_year` | 会计年度 |
| `source_file` | 来源文件 |
| `import_batch_id` | 导入批次号 |
| `created_at` | 创建时间 |

最小必填字段：

- `posting_date`
- `voucher_id`
- `ac_code`
- `ac_caption`
- `rc_amount`
- `description`

如果 `rc_amount` 需要依赖借贷标识计算，则 `drcr` 也必须存在。

## 兼容视图

为了兼容 ADE 现有 SQL、规则和界面，DuckDB 查询会话可基于 `ledger` 创建 `journal` 兼容视图：

```sql
CREATE OR REPLACE VIEW journal AS
SELECT
    posting_date AS book_date,
    voucher_id AS voucher_no,
    ac_code,
    ac_caption AS ac_name,
    description AS summary,
    rc_amount,
    lc_amount,
    client_name,
    fiscal_year,
    source_file,
    import_batch_id,
    created_at
FROM ledger;
```

新功能应优先面向 `ledger` 表开发；旧查询和旧规则可通过 `journal` 视图平滑迁移。

## 标准数据集包

Parquet 是 ADE Pro 的标准可交换 `ledger` 数据格式。本机工作时它是固化结果；对外协作时它是可分享数据包。

推荐数据集包结构：

```text
ABC_2024_ledger_dataset/
  dataset.toml
  ledger.parquet
```

`dataset.toml` 至少记录：

```toml
schema_version = 1
dataset_name = "ABC 2024 Ledger"
client_name = "ABC Company"
fiscal_year = 2024
row_count = 123456
posting_date_min = "2024-01-01"
posting_date_max = "2024-12-31"
created_at = "2026-05-12T10:30:00"
import_batch_id = "20260512_001"
profile_name = "default"
ledger_parquet = "ledger.parquet"
```

同事收到数据集包后，可以在 ADE Pro 中选择 `dataset.toml` 或 `ledger.parquet` 打开。程序校验 required 字段后，用 DuckDB 创建查询入口：

```sql
CREATE OR REPLACE VIEW ledger AS
SELECT * FROM read_parquet('ledger.parquet');
```

## 导入模块流程

目标交互采用“Excel 预览 + 表头下拉映射”：

1. 用户选择来源文件
2. Excel 来源先选择 worksheet
3. 系统读取前几行并展示预览
4. 每个源 Excel 列下方提供下拉框
5. 用户选择“不导入”或映射到标准字段，例如 `posting_date`、`voucher_id`、`ac_code`、`ac_caption`、`description`
6. 用户在独立的金额规则区域选择 `rc_amount` 生成方式
7. 系统展示金额转换预览，确保转换后借方为正、贷方为负
8. 系统校验 required 字段和金额规则
9. 用户选择或确认输出数据集位置
10. 用户确认后执行全量转换
11. 系统生成 `ledger.parquet` 和 `dataset.toml`
12. 本机注册为最近数据集
13. 映射结果和金额规则可保存为客户或模板配置

说明：

- 预览读取在后台线程执行，主界面保持响应
- 新导入模式会覆盖该客户该年度历史数据
- 追加导入模式会保留历史数据并应用重复处理策略
- 下一次启动时优先读取已注册数据集，不重新导入原始 Excel

## 金额规则交互

GUI 中金额处理应独立于普通字段映射，支持三种模式：

| 模式 | 源 Excel 结构 | 输出 |
| --- | --- | --- |
| 已是借正贷负净额 | 一列金额，正数借方、负数贷方 | 直接作为 `rc_amount` |
| 借贷标识 + 正数金额 | 一列借贷标识 + 一列正数金额 | 借方转正数，贷方转负数 |
| 借方金额列 + 贷方金额列 | 两列金额，均为正数 | 借方金额减贷方金额 |

该区域应包含列选择、借方/贷方标识值配置、转换预览和异常提示。Ledger Analysis 已有的借贷标识处理可优先复用到第二种模式。

## GUI 影响

启动页或查询页应提供“最近数据集”列表：

| 字段 | 说明 |
| --- | --- |
| 客户 | `client_name` |
| 年度 | `fiscal_year` |
| 行数 | `row_count` |
| 期间 | `posting_date_min` 至 `posting_date_max` |
| 最近转换 | `created_at` |
| 状态 | 可查询 / 文件缺失 / schema 不匹配 |

当前查询页入口：

- 打开已有 Parquet 数据集
- 分享数据集
- 运行基础规则
- 导出当前结果

导入页已支持输出数据集名称，并在导入报告中展示 `ledger.parquet`、`dataset.toml`、期间和数据集名称。

## 技术选型

| 模块 | 技术 |
| --- | --- |
| 编程语言 | Python |
| GUI 框架 | PySide6 |
| 配置 | TOML |
| Excel 读取与清洗 | DuckDB 优先，复用 Ledger Analysis 方法 |
| 数据处理 | DuckDB SQL |
| 固化与交换 | Parquet |
| 查询引擎 | DuckDB |
| 图表 | 当前为基础占位，后续版本增强 |
| 打包 | PyInstaller |

## 目录结构

```text
audit-data-explorer
├─ apps
│  ├─ main_app.py
│  ├─ ingest_app.py
│  └─ query_app.py
├─ ingest
│  ├─ import_service.py
│  ├─ mapping_service.py
│  ├─ report_service.py
│  ├─ client_profile_service.py
│  ├─ duckdb_cleaning_service.py
│  ├─ excel_importer.py
│  ├─ csv_importer.py
│  ├─ parquet_importer.py
│  └─ duckdb_importer.py
├─ dataset
│  ├─ manifest_service.py
│  ├─ package_service.py
│  ├─ query_dataset.py
│  └─ registry_service.py
├─ query
│  ├─ query_service.py
│  ├─ query_builder.py
│  ├─ sql_runner.py
│  ├─ sql_history_service.py
│  └─ export_service.py
├─ analysis
│  ├─ rule_service.py
│  ├─ journal_analysis.py
│  └─ anomaly_detection.py
├─ ui_ingest
│  ├─ ingest_window.py
│  ├─ mapping_dialog.py
│  └─ import_report_view.py
├─ ui_query
│  ├─ query_window.py
│  ├─ table_viewer.py
│  ├─ sql_editor.py
│  ├─ visual_query.py
│  └─ chart_viewer.py
├─ shared
│  ├─ client_router.py
│  ├─ db.py
│  ├─ schema.py
│  ├─ errors.py
│  └─ constants.py
├─ scripts
│  └─ verify_ade_pro.py
├─ data
│  ├─ clients
│  │  ├─ client_9f3a2c10
│  │  │  ├─ ingest_profiles.toml
│  │  │  └─ datasets
│  │  │     └─ ABC_2024_ledger_dataset
│  │  │        ├─ dataset.toml
│  │  │        └─ ledger.parquet
│  │  └─ client_2ad4e8b7
│  │     └─ datasets
│  ├─ registry.toml
│  └─ sql_history.toml
└─ utils
```

## 分层补充

```text
UI Layer (PySide6)
  ↓
Application Service Layer
  ↓
Ledger Cleaning / Rule Engine
  ↓
Dataset Layer (Parquet + TOML)
  ↓
Query Layer (DuckDB)
```

说明：

- UI 层只负责交互，不直接拼接复杂 SQL
- Service 层负责参数校验、流程编排、事务边界
- Cleaning 层负责字段映射、类型转换、金额口径和清洗规则
- Dataset 层负责 Parquet 输出、manifest、数据集注册和分享
- Query 层统一管理 DuckDB 连接、`ledger` 视图和 `journal` 兼容视图
- `client_name` 仅用于展示和客户隔离，物理路径使用安全标识
- `company_id` 表示公司代码、核算主体或法人实体编码，不替代 `client_name`

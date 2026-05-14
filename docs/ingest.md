# 数据导入规范

## 导入目标

ADE Pro 的导入模块负责把 Excel、CSV、DuckDB 或已有 Parquet 来源数据转换为标准 `ledger` Parquet 数据集包。导入过程必须完成字段映射、类型清洗、金额口径标准化、客户隔离校验、数据集固化和导入报告生成。

标准流程：

```text
Source File
  ↓
Preview
  ↓
Header Dropdown Mapping
  ↓
Amount Rule Selection
  ↓
Config Cleaning
  ↓
Amount Normalize
  ↓
DuckDB SQL Cleaning
  ↓
ledger.parquet + dataset.toml
  ↓
Register Recent Dataset
  ↓
DuckDB ledger / journal views
```

## 分步导入

1. 选择来源文件（Excel/CSV/DuckDB/Parquet）
2. 若为 Excel，先确认 worksheet
3. 输入客户、会计年度、导入方式（新导入/追加导入）与重复处理策略
4. 读取前几行预览
5. 在每个源列下方用下拉框选择目标标准字段
6. 在金额规则区域选择源 Excel 的金额结构
7. 系统生成 `rc_amount` 转换预览
8. 校验 required 字段、金额字段和借贷标识规则
9. 用户确认输出数据集名称和位置
10. 用户确认后执行全量转换
11. 生成 `ledger.parquet` 和 `dataset.toml`
12. 注册为本机最近数据集
13. 生成导入报告
14. 可将映射、金额规则和清洗规则保存为客户配置或模板配置

说明：

- 预览读取采用后台线程，避免界面卡顿
- 预览与全量导入使用同一 worksheet，保证一致性
- 表头下拉交互参考 excel-converter，但实现仍放在 ADE Pro 的 PySide6 体系内
- Excel 导入和清洗主链路优先复用 Ledger Analysis 的 DuckDB 方法，不使用 pandas 作为导入和清洗主路径

## 字段映射交互

用户选择 Excel 后，系统展示前几行预览。每个源 Excel 列下面提供一个下拉框，选项包括：

- 不导入
- `posting_date`
- `voucher_id`
- `ac_code`
- `ac_caption`
- `rc_amount`
- `description`
- `drcr`
- optional 字段

映射要求：

1. 必须确认“源字段 -> 标准 ledger 字段”后才能导入
2. 非必填字段可留空
3. 必填字段未映射时禁止提交
4. 同一标准字段默认不允许被多个源列重复映射，除非该字段明确支持合并
5. 映射结果可保存为客户或模板配置，供下次自动匹配

标准字段名称必须使用英文 `snake_case`。原始 Excel 中文列名只作为来源列名保存在 TOML 配置里，不进入 `ledger` schema。

导入页在确认字段与金额规则时提供“保存为客户导入 profile”开关。默认保存到当前客户的 `ingest_profiles.toml`，用户也可以取消，只在本次导入使用当前映射和金额规则。

## 标准字段

### Required 最小字段

| 字段 | 类型建议 | 说明 |
| --- | --- | --- |
| `posting_date` | DATE | 入账日期 / 记账日期 |
| `voucher_id` | TEXT | 凭证号 |
| `ac_code` | TEXT | 科目编码 |
| `ac_caption` | TEXT | 科目名称 |
| `rc_amount` | DECIMAL(18,2) | 记账本位币或统一分析金额 |
| `description` | TEXT | 摘要 / 描述 |

如果金额依赖借贷标识计算，则 `drcr` 也必须存在。

### Optional 字段

| 字段 | 说明 |
| --- | --- |
| `voucher_header` | 凭证抬头 |
| `lc_amount` | 原币金额 |
| `vendor_id` | 供应商编码 |
| `vendor_name` | 供应商名称 |
| `customer_id` | 客户编码 |
| `customer_name` | 客户名称 |
| `company_id` | 公司代码 / 核算主体 / 法人实体编码 |
| `department` | 部门 |
| `employee_id` | 员工编码 |
| `employee_name` | 员工名称 |
| `currency` | 币种 |
| `document_type` | 单据类型 |
| `posting_period` | 会计期间 |
| `source_system` | 来源系统 |

`company_id` 不替代 `client_name`。`client_name` 表示审计客户或项目，用于客户隔离、展示和导入报告；`company_id` 表示账本数据内部的公司代码、核算主体或法人实体。

## 建议 ledger schema

```sql
-- DuckDB 查询视图或临时表 schema。最终固化为 ledger.parquet。
CREATE TABLE ledger (
    posting_date DATE NOT NULL,
    voucher_id TEXT NOT NULL,
    voucher_header TEXT,
    company_id TEXT,
    ac_code TEXT NOT NULL,
    ac_caption TEXT NOT NULL,
    drcr TEXT,
    rc_amount DECIMAL(18, 2) NOT NULL,
    lc_amount DECIMAL(18, 2),
    vendor_id TEXT,
    vendor_name TEXT,
    customer_id TEXT,
    customer_name TEXT,
    description TEXT NOT NULL,
    client_name TEXT NOT NULL,
    fiscal_year INTEGER NOT NULL,
    source_file TEXT NOT NULL,
    import_batch_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL
);
```

## journal 兼容视图

为了兼容 ADE 现有 SQL 和规则，DuckDB 查询会话可基于 `ledger` 建立 `journal` 兼容视图：

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

新导入逻辑应生成标准 `ledger.parquet`，不直接把 `journal` 作为主表。

## 数据集输出

Parquet 是 ADE Pro 的标准可交换 `ledger` 数据格式。每次成功转换应输出一个数据集包：

```text
ABC_2024_ledger_dataset/
  dataset.toml
  ledger.parquet
```

`dataset.toml` 至少包含：

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
source_file = "raw_ledger.xlsx"
```

`posting_date_min` 和 `posting_date_max` 在导入完成后通过 DuckDB 统计：

```sql
SELECT
    MIN(posting_date) AS posting_date_min,
    MAX(posting_date) AS posting_date_max,
    COUNT(*) AS row_count
FROM ledger;
```

这些信息用于启动页或查询页展示“最近数据集”，避免每次启动都扫描 Parquet。

## 金额规则

`rc_amount` 是统一分析金额，转换后必须是一列：借方为正数，贷方为负数。金额规则不应只作为普通字段映射处理，而应在 GUI 中独立成“金额处理方式”配置区。

### 支持的金额来源

| 模式 | 适用情况 | 用户需要选择 | 转换规则 |
| --- | --- | --- | --- |
| `direct_signed_amount` | 源 Excel 已经是一列净额，正数为借方、负数为贷方 | 金额列 | `rc_amount = amount` |
| `amount_with_drcr` | 源 Excel 有借贷标识列，金额列均为正数 | 借贷标识列、金额列、借方值、贷方值 | 借方 `abs(amount)`，贷方 `-abs(amount)` |
| `debit_credit_columns` | 源 Excel 借方金额一列、贷方金额一列，金额均为正数 | 借方金额列、贷方金额列 | `rc_amount = abs(debit_amount) - abs(credit_amount)` |

默认方向为借正贷负。`amount_with_drcr` 可复用 Ledger Analysis 已有的借贷标识处理逻辑。

### GUI 建议

金额处理区应独立于普通字段映射区，使用单选按钮或分段控件选择模式：

```text
金额处理方式

( ) 已是借正贷负净额
    金额列：[下拉选择]

( ) 借贷标识 + 正数金额
    借贷标识列：[下拉选择]
    金额列：[下拉选择]
    借方值：[借, D, Debit]
    贷方值：[贷, C, Credit]

( ) 借方金额列 + 贷方金额列
    借方金额列：[下拉选择]
    贷方金额列：[下拉选择]
```

普通字段映射区可以不强制用户直接映射 `rc_amount`。系统应根据金额规则生成标准 `rc_amount`。如果用户选择 `direct_signed_amount`，所选金额列等价于 `rc_amount` 来源。

### 转换预览

金额规则配置后，GUI 应显示转换预览，至少包含：

| 源借贷标识 | 源金额 | 源借方金额 | 源贷方金额 | 转换后 `rc_amount` |
| --- | --- | --- | --- | --- |
| 借 | 100.00 |  |  | 100.00 |
| 贷 | 200.00 |  |  | -200.00 |
|  |  | 300.00 |  | 300.00 |
|  |  |  | 400.00 | -400.00 |

预览只需使用前几行数据，但校验应在全量导入时重新执行。

### 校验要求

`direct_signed_amount`：

- 金额列必须存在且可解析为数字
- 如果样本中金额全部为正数或全部为负数，应提醒用户确认源数据是否已经带方向

`amount_with_drcr`：

- 借贷标识列和金额列必须存在
- 借方值、贷方值不能为空
- 无法识别的借贷标识应计入错误明细
- 标准字段 `drcr` 应保存源借贷标识或标准化后的借贷标识

`debit_credit_columns`：

- 借方金额列和贷方金额列必须存在
- 同一行不应同时存在借方金额和贷方金额
- 同一行不应借方金额和贷方金额都为空
- 如果源金额已经带负号，应提示用户确认

### 导入报告要求

导入报告必须记录：

- 金额处理模式
- 参与转换的源列
- 借方值、贷方值配置
- 转换成功行数
- 金额为空行数
- 借贷标识无法识别行数
- 借贷双列同时有值行数
- 转换后借方合计、贷方合计、净额
- 按 `voucher_id` 的借贷平衡检查结果

## DuckDB 清洗与 Parquet 固化

导入主链路优先使用 DuckDB SQL 完成读取、字段映射、类型转换、金额转换和质量统计，避免 pandas 成为导入路径的必需依赖，以提高读取速度并控制打包体积。

推荐实现：

1. 使用 Ledger Analysis 已有 DuckDB 方法读取 Excel 或中间数据
2. 在 SQL 中完成字段映射、类型转换和金额转换
3. 生成标准 `ledger` 临时表或视图
4. 用 `COPY` 或等价方式输出 `ledger.parquet`
5. 写入 `dataset.toml`
6. 注册到本机最近数据集
7. 全流程事务或阶段性原子写入，失败时不发布半成品数据集

示例查询入口：

```sql
CREATE OR REPLACE VIEW ledger AS
SELECT * FROM read_parquet('ledger.parquet');
```

## 导入约束

- 单任务单客户
- 每次导入必须显式指定 `client_name`
- 新导入支持按客户和会计年度覆盖
- 追加导入保留历史数据并执行重复检测
- DuckDB 来源优先作为追加导入处理
- 导入前校验输出数据集目录与 `client_name` 一致
- 导入过程中禁止跨客户写入
- 发布数据集前必须校验 `ledger.parquet` required 字段

## 导入报告

每次导入至少输出：

- 总行数、成功行数、失败行数
- 来源类型、来源路径、来源表或 worksheet
- `fiscal_year`、`client_name`、`import_mode`
- 字段缺失统计
- 字段映射结果
- 类型转换失败统计
- 重复凭证提示
- 借贷平衡检查结果
- `rc_amount` 统计（正/负/零）
- `posting_date` 最早和最晚日期
- 日期为空或无法解析行数
- 行级错误明细，至少包含来源行号、错误原因、关键字段和转换后的金额
- 金额方向规则
- 重复处理模式（strict/skip/mark）及处理结果
- 导入批次号 `import_batch_id`
- 输出数据集路径

## 数据质量与异常策略

- 失败数据写入错误明细表，不丢弃原始记录
- 支持下载错误明细修复后重导
- 新导入模式会覆盖该客户该年度历史数据
- 追加导入模式会保留历史数据并做重复检测
- 清洗规则必须可追溯到客户配置或导入批次
- 原始 Excel 不作为查询依赖；成功转换后，后续查询直接连接固化后的 Parquet 数据集

## 导入模式策略

1. 新导入：生成新的数据集包，并可替换该客户该年度当前数据集指针
2. 追加导入：保留历史数据集或合并生成新的数据集包，按重复处理策略处理新增记录
3. DuckDB 来源默认追加导入
4. 系统保留内部 `import_batch_id` 用于审计追踪与问题定位
5. UI 不要求用户输入批次号

重复处理模式：strict / skip / mark（默认 mark）。

## GUI 输出与复用

导入页支持输入输出数据集名称。转换完成后，导入报告展示输出数据集信息：

```text
数据集名称：ABC 2024 Ledger
输出目录：data/clients/client_xxxxxxxx/datasets/ABC_2024_ledger_dataset
ledger 文件：ledger.parquet
manifest：dataset.toml
注册到最近数据集：自动注册
```

转换完成后，结果页显示：

```text
行数：123,456
期间：2024-01-01 至 2024-12-31
输出：ledger.parquet
状态：可查询
```

下一次启动程序时，ADE Pro 应读取最近数据集 registry，直接连接上次已经转换后的数据进行查询，不要求用户重新导入原始 Excel。

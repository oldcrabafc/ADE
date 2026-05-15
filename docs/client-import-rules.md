# 客户导入规则配置

## 概述

不同客户的 Excel/CSV 文件字段结构各不相同，包括列名、日期格式、金额格式、借贷标识和辅助核算字段。ADE Pro 允许为每个客户保存字段映射、金额规则和清洗规则，下次导入同一客户时自动匹配并预填映射，减少重复配置。

配置统一使用 TOML，不使用 JSON。规则目标是把来源字段映射到标准 `ledger` 字段。

## 配置文件位置

导入 baseline 配置文件放在项目目录 `profile/` 下，例如：

```text
profile/ingest_profiles_baseline_供应链集团.toml
profile/ingest_profiles_baseline_不使用配置.toml
```

其中 `profile/ingest_profiles_baseline_不使用配置.toml` 为默认 baseline。用户在导入页选择“不使用配置”时，系统加载该文件作为基线配置，随后允许用户在 UI 中手动调整映射。

客户目录下仍可维护一个 `ingest_profiles.toml` 作为客户持久配置：

```text
data/clients/client_{sha1[:8]}/ingest_profiles.toml
```

客户目录由 `shared/client_router.py::resolve_client_dir(client_name)` 解析。

## 配置文件结构

```toml
version = 2

[[profiles]]
profile_name = "default"
# required_field 为必填的非金额相关字段。
# 系统必须在数据转换前检查这些字段是否已完成映射，缺失则报错并禁止转换。
# 金额相关字段不在此列出；金额字段的校验由 amount_rules 单独执行。
required_field = [
  "posting_date",
  "voucher_id",
  "ac_code",
  "ac_caption",
  "description",
]

[profiles.match]
source_type = "excel"
source_sheet = "Sheet1"

# field_mapping 定义了系统需要识别的标准字段与源数据字段的对应关系。
# 这个只是在进入UI后系统预设的默认映射，用户可以根据实际情况在UI里修改这些映射关系。
[profiles.field_mapping]
posting_date = "记账日期"
voucher_id = "凭证号"
voucher_header = "凭证抬头"
company_id = "公司代码"
ac_code = "科目编码"
ac_caption = "科目名称"
drcr = ""
rc_amount = ""
lc_amount = "原币金额"
vendor_id = "供应商编码"
vendor_name = "供应商名称"
customer_id = "客户编码"
customer_name = "客户名称"
description = "摘要"
department = "部门"
employee_id = "员工编码"
employee_name = "员工名称"
currency = "币种"
document_type = "单据类型"
posting_period = "期间"
source_system = "来源系统"

# amount_rules 用于金额字段校验与 rc_amount 转换，独立于 required_field。
# required_field 只校验“非金额字段是否已映射”。

# mode 取值：
# 1) direct_signed_amount
#    - 必须映射：direct_amount_field（或 field_mapping.rc_amount）
#    - 规则：源金额已带方向，直接写入 rc_amount
#
# 2) amount_with_drcr
#    - 必须映射：amount_field + drcr_field（或 field_mapping.drcr）
#    - 规则：借方值 -> +abs(amount)；贷方值 -> -abs(amount)
#    - debit_values / credit_values 必须配置，且应覆盖源数据实际标识（如 S/H、借/贷、D/C）
#
# 3) debit_credit_columns
#    - 必须映射：debit_field + credit_field
#    - 规则：rc_amount = abs(debit) - abs(credit)
#
# 校验失败处理：
# - 缺少 mode 对应必需字段 -> 转换前报错并禁止转换
# - 借贷标识无法识别 / 金额无法解析 -> 该行 rc_amount 为空，进入错误明细

[profiles.amount_rules]
mode = "amount_with_drcr"
amount_field = "发生额"
direct_amount_field = ""
debit_field = ""
credit_field = ""
drcr_field = "借贷方向"
debit_values = ["借", "D", "Debit"]
credit_values = ["贷", "C", "Credit"]
sign_rule = "debit_positive"

[profiles.clean_rules]
empty_tokens = ["", "NULL", "N/A", "-"]
date_dayfirst = false
amount_remove_commas = true
```

## 匹配条件

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `source_type` | string | `excel` / `csv` |
| `source_sheet` | string | Excel sheet 名称；非 Excel 时可为空字符串 |
| `required_columns` | string[] | 源文件必须包含这些列名，才视为匹配成功 |

匹配逻辑：

- `source_type` 必须相等
- Excel 来源要求 `source_sheet` 相等
- `required_columns` 使用子集判断，源文件允许有额外列
- 多个 profile 命中时，优先选择 `required_columns` 数量最多的 profile

说明：`required_columns` 仅用于 profile 匹配，不等于转换前必填映射字段。

## 字段映射

`field_mapping` 保存“标准 ledger 字段 -> 来源列名”的映射。未映射的 optional 字段可为空字符串或省略。

金额字段有特殊规则：`rc_amount` 可以由 `amount_rules` 生成，不要求一定出现在普通 `field_mapping` 中。GUI 应把金额处理从普通字段映射中独立出来，避免用户同时把金额列映射到 `rc_amount` 又选择另一套金额转换规则。

`required_field` 用于定义“非金额字段的转换前必填映射”。这些字段可以由 baseline 预填，也可以由用户在界面手动补齐；在点击开始转换前必须完成映射。

在映射弹窗中，`Required ledger 字段` 的显示顺序按 TOML 中 `required_field` 原顺序展示。

Required 字段：

| 键 | 说明 |
| --- | --- |
| `posting_date` | 入账日期 / 记账日期 |
| `voucher_id` | 凭证号 |
| `ac_code` | 科目编码 |
| `ac_caption` | 科目名称 |
| `description` | 摘要 / 描述 |

`rc_amount` 是标准必填字段，但它通常由 `amount_rules` 生成。只有在源数据已经是一列借正贷负净额时，才可把来源金额列作为 `rc_amount` 的直接来源。

Optional 字段：

| 键 | 说明 |
| --- | --- |
| `voucher_header` | 凭证抬头 |
| `lc_amount` | 原币金额 |
| `vendor_id` / `vendor_name` | 供应商信息 |
| `customer_id` / `customer_name` | 客户信息 |
| `company_id` | 公司代码 / 核算主体 / 法人实体编码 |
| `department` | 部门 |
| `employee_id` / `employee_name` | 员工信息 |
| `currency` | 币种 |
| `document_type` | 单据类型 |
| `posting_period` | 会计期间 |
| `source_system` | 来源系统 |

`company_id` 不替代 `client_name`。前者来自账本数据，后者来自导入任务和客户隔离路由。

标准字段名称必须统一使用英文 `snake_case`，不使用空格、中文或特殊符号。原始 Excel 列名只作为配置值保存。

## 金额规则

`amount_rules` 用于说明如何得到 `rc_amount`。转换后的 `rc_amount` 必须是一列金额：借方为正，贷方为负。

金额校验与 `required_field` 分离：`required_field` 只管非金额字段，金额字段由 `amount_rules` 按模式校验。

| 键 | 说明 |
| --- | --- |
| `mode` | `direct_signed_amount` / `amount_with_drcr` / `debit_credit_columns` |
| `direct_amount_field` | 已经是借正贷负净额口径的来源字段 |
| `amount_field` | 配合借贷标识使用的正数金额列 |
| `debit_field` | 借方金额列 |
| `credit_field` | 贷方金额列 |
| `drcr_field` | 借贷标识列 |
| `debit_values` | 识别为借方的值 |
| `credit_values` | 识别为贷方的值 |
| `sign_rule` | 默认 `debit_positive`，即借正贷负 |

规则要求：

- `mode=direct_signed_amount` 时，`direct_amount_field` 或 `field_mapping.rc_amount` 必须存在
- `mode=amount_with_drcr` 时，必须存在 `amount_field` 和 `drcr_field`
- `mode=debit_credit_columns` 时，必须存在 `debit_field` 和 `credit_field`
- 如果金额依赖借贷标识，则标准字段 `drcr` 必须存在或可由 `drcr_field` 生成
- 缺少当前模式必需金额字段时，必须在转换前报错并禁止转换

三种模式的含义：

| 模式 | 源数据结构 | 转换结果 |
| --- | --- | --- |
| `direct_signed_amount` | 一列金额，已是借正贷负 | `rc_amount = amount` |
| `amount_with_drcr` | 一列借贷标识 + 一列正数金额 | 借方 `abs(amount)`，贷方 `-abs(amount)` |
| `debit_credit_columns` | 借方金额列 + 贷方金额列，均为正数 | `rc_amount = abs(debit) - abs(credit)` |

## 无效行过滤规则（当前实现）

导入清洗阶段会在生成 `ledger` 前过滤无效行。当前仅在以下条件命中时过滤：

- `voucher_id` 为空（去空格后）
- `ac_code` 为空（去空格后）
- `ac_caption` 为空（去空格后）
- `rc_amount` 为空（金额无法转换，或借贷标识无法识别）

`posting_date` 和 `description` 当前不作为无效行过滤条件。

## UI 行为说明（当前实现）

- 映射下拉支持 `不导入`、`其他输入`、标准字段集合；选择 `其他输入` 时可手工输入目标字段名
- Step1、Step2、预览映射行、映射弹窗（含金额规则）下拉默认禁用滚轮改值，避免误触
- 映射弹窗右侧纵向滚动条常显并加宽，便于小屏操作
- 点击映射弹窗 `OK` 后，会把映射结果回写到预览行；再次打开弹窗保留上次确认内容
- 金额模式为 `amount_with_drcr` 时，预览映射显示目标字段为 `rc_amount`
- 转换前校验分开提示：
  - 非金额必需字段缺失（`required_field`）
  - 金额规则缺失（`amount_rules`）

### 金额规则示例

源数据已经是借正贷负：

```toml
[profiles.amount_rules]
mode = "direct_signed_amount"
direct_amount_field = "发生额"
sign_rule = "debit_positive"
```

借贷标识 + 正数金额：

```toml
[profiles.amount_rules]
mode = "amount_with_drcr"
amount_field = "金额"
drcr_field = "借贷方向"
debit_values = ["借", "D"]
credit_values = ["贷", "C"]
sign_rule = "debit_positive"
```

借方金额列 + 贷方金额列：

```toml
[profiles.amount_rules]
mode = "debit_credit_columns"
debit_field = "借方发生额"
credit_field = "贷方发生额"
sign_rule = "debit_positive"
```

## 清洗规则

| 键 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `empty_tokens` | string[] | `["", "NULL", "N/A", "-"]` | 识别为空值的字符串 |
| `date_dayfirst` | bool | `false` | 日期解析时日优先 |
| `amount_remove_commas` | bool | `true` | 金额解析前去除千位分隔符 |

后续可继续吸收 Ledger Analysis 的清洗配置，例如字段别名、类型转换、借贷标识字典和输出 Parquet 配置。

## 数据集 Manifest

每个转换结果应生成 `dataset.toml`，与 `ledger.parquet` 一起构成标准可交换数据集包：

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

`posting_date_min` 和 `posting_date_max` 来自转换后 `ledger.posting_date` 的最早和最晚日期，用于最近数据集展示和期间检查。

## 最近数据集 Registry

本机可维护一个 `registry.toml`，记录最近打开或生成的数据集：

```toml
[[datasets]]
dataset_name = "ABC 2024 Ledger"
client_name = "ABC Company"
fiscal_year = 2024
dataset_manifest = "data/clients/client_xxxxxxxx/datasets/ABC_2024_ledger_dataset/dataset.toml"
last_opened_at = "2026-05-12T11:00:00"
```

启动页和查询页读取 registry 展示最近数据集，不需要重新导入原始 Excel。

## 交互流程

```text
用户选择文件 / Sheet
       ↓
选择配置方式（使用配置文件 / 不使用配置）
       ↓
读取前几行预览
       ↓
加载 baseline profile（可选）
       ↓
表头下拉框预填映射
       ↓
用户修正普通字段映射
       ↓
用户选择金额处理方式
       ↓
生成 rc_amount 转换预览
       ↓
校验 required_field（非金额） + amount_rules（金额）
       ↓
保存 profile
       ↓
DuckDB 清洗并生成 ledger
       ↓
输出 ledger.parquet + dataset.toml
       ↓
注册最近数据集
```

补充：导入执行只接受最终确认后的 `IngestProfile`。`field_mapping` 作为 profile 内部字段配置存在，但不存在独立旧接口回退路径。

## 实现文件建议

### `ingest/client_profile_service.py`

负责读写 `ingest_profiles.toml`，对外暴露：

```python
def load_client_profiles(client_name: str) -> dict:
    """读取客户 ingest_profiles.toml，不存在则返回空 profiles。"""

def save_profile(client_name: str, profile: dict) -> None:
    """写入或更新一条 profile，按 profile_name 去重。"""

def find_profile(
    client_name: str,
    source_type: str,
    source_sheet: str | None,
    columns: list[str],
) -> dict | None:
    """根据 match 条件查找最佳匹配 profile。"""
```

### `ui_ingest/mapping_dialog.py`

支持 initial profile，并以表头下拉框方式完成源字段到标准字段的映射。

下拉框应包含：

- 不导入
- required 字段
- optional 字段

金额处理应作为单独区域，不只依赖表头下拉框。界面建议提供三种单选模式：

- 已是借正贷负净额
- 借贷标识 + 正数金额
- 借方金额列 + 贷方金额列

选择后显示对应的列选择控件和 `rc_amount` 转换预览。

### `ingest/duckdb_cleaning_service.py`

负责通过 DuckDB 把来源数据标准化为 `ledger`：

- 字段重命名
- required 字段校验
- 日期、金额、文本清洗
- `rc_amount` 计算
- 金额规则校验和转换预览数据生成
- `client_name`、`fiscal_year`、`source_file`、`import_batch_id`、`created_at` 补齐
- `posting_date_min`、`posting_date_max`、`row_count` 统计

该服务优先复用 Ledger Analysis 已有 DuckDB 清洗方法，不使用 pandas 作为主路径。

### `dataset/manifest_service.py`

负责写入和读取 `dataset.toml`。

### `dataset/registry_service.py`

负责本机最近数据集 registry 的读写、数据集路径校验和打开记录更新。

### `ingest/import_service.py`

负责导入流程编排：

- 加载 profile
- 调用 DuckDB cleaning service
- 输出 `ledger.parquet`
- 写入 `dataset.toml`
- 注册最近数据集
- 生成导入报告

## 多 Profile 支持

一个客户可以有多个 profile，对应不同 sheet、不同系统导出格式或不同公司账套：

```toml
version = 2

[[profiles]]
profile_name = "总账"

[profiles.match]
source_sheet = "总账"

[[profiles]]
profile_name = "明细账"

[profiles.match]
source_sheet = "明细账"
```

## 兼容迁移

现有 ADE 可能仍保存旧字段映射，例如 `book_date`、`voucher_no`、`ac_name`、`summary`。迁移时可做一次字段别名转换：

| 旧字段 | 新 ledger 字段 |
| --- | --- |
| `book_date` | `posting_date` |
| `voucher_no` | `voucher_id` |
| `ac_name` | `ac_caption` |
| `summary` | `description` |
| `rc_amount` | `rc_amount` |

新 profile 应保存为 `version=2` 并使用标准 `ledger` 字段。

## 注意事项

- `ingest_profiles.toml` 由程序自动创建或更新，高级用户可直接修改 TOML 文件
- 保存 profile 时应记录标准字段，不保存界面显示名
- 导入报告必须记录实际使用的 profile 和金额规则
- `field_mapping.rc_amount` 与 `amount_rules` 冲突时，应以 `amount_rules` 为准并要求用户确认
- 客户配置属于客户隔离目录，不跨客户自动复用，除非用户明确保存为模板
- 标准 `ledger.parquet` 可分享给同事；同事使用 ADE Pro 打开后可直接查询

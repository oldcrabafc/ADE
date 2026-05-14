# 查询与导出

## 查询流程

查询模块默认连接已经生成或打开的标准 `ledger` Parquet 数据集。DuckDB 是查询引擎，Parquet 是标准数据资产。

### 打开数据集

```text
选择 dataset.toml 或 ledger.parquet
  ↓
校验 required 字段
  ↓
DuckDB 创建 ledger view
  ↓
创建 journal 兼容视图
  ↓
进入查询页
```

打开 `dataset.toml` 时，ADE Pro 可直接读取客户、年度、行数和期间信息。只打开 `ledger.parquet` 时，程序会扫描 Parquet schema、行数和 `posting_date` 期间；如果文件内包含 `client_name`、`fiscal_year` 等元字段，也会展示这些信息。裸 Parquet 不会写入最近数据集 registry，除非旁边存在 `dataset.toml`。

### 可视化查询

```
用户输入条件
  ↓
Query Builder
  ↓
生成 SQL
  ↓
DuckDB 执行
  ↓
返回结果
```

### SQL 查询

```
SQL Editor
  ↓
DuckDB
  ↓
QueryResult
  ↓
UI 表格展示
```

## 典型审计 SQL

新 SQL 应优先使用 `ledger` 字段：

```sql
SELECT *
FROM ledger
WHERE ac_caption = '银行存款';
```

查询某科目发生额：

```sql
SELECT *
FROM ledger
WHERE ac_caption = '银行存款';
```

查询大额凭证：

```sql
SELECT *
FROM ledger
WHERE ABS(rc_amount) >= 1000000;
```

查询借款相关凭证：

```sql
SELECT *
FROM ledger
WHERE description LIKE '%借款%';
```

查询某凭证：

```sql
SELECT *
FROM ledger
WHERE voucher_id = '2024-00125';
```

`journal` 是兼容视图，服务旧 SQL 和旧规则。新增查询模板应使用 `ledger` 的英文 `snake_case` 字段。

### SQL 模板与历史

SQL 编辑器提供内置 `ledger` 查询模板，并把执行成功的 SQL 写入 `data/sql_history.toml`。历史只保存 SQL 文本、执行时间和数据集路径，不保存查询结果。

## 查询模式边界

可视化查询用于高频标准场景：

- 科目筛选
- 日期区间
- 金额阈值
- 摘要关键词

SQL 查询用于高级场景：

- 多表联查
- 聚合分析
- 自定义审计口径

协同原则：

1. 可视化条件可一键转换为 SQL
2. SQL 结果可回填筛选条件（能回填尽量回填）
3. 两种模式共享历史记录与导出能力

## 表浏览

查询结果表支持结果内筛选、列头排序和分页浏览。分页只作用于当前已返回的 `QueryResult`，不会重新执行 SQL；需要更大结果集时应调整 SQL 中的 `LIMIT` 或筛选条件。

## 最近数据集

启动页或查询页应展示最近数据集：

```text
客户：ABC Company
年度：2024
最近转换：2026-05-12 10:30
行数：123,456
期间：2024-01-01 至 2024-12-31
状态：可查询
```

字段来源：

| 展示 | Manifest 字段 |
| --- | --- |
| 客户 | `client_name` |
| 年度 | `fiscal_year` |
| 行数 | `row_count` |
| 期间 | `posting_date_min` 至 `posting_date_max` |
| 最近转换 | `created_at` |

当前查询页入口：

- 打开已有 Parquet 数据集
- 分享数据集
- 运行基础规则
- 导出当前结果

“分享数据集”会生成 ZIP 包。标准数据集会包含 `dataset.toml`、`ledger.parquet` 和说明文件；裸 Parquet 会打包 Parquet 和说明文件。接收方可在 ADE Pro Query 中打开 `dataset.toml` 或 `.parquet` 使用。

## Excel 导出规范

1. 单次导出最大 10000 行
2. 超过 10000 行按顺序拆分多个 sheet（每个最多 10000 行）
3. 默认文件名：sql_export_{client_name}_{yyyyMMdd_HHmmss}.xlsx
4. 保留日期与数值类型，不以文本写金额字段

我会先快速扫描代码与 docs 下文档的关键约定（模块职责、入口、数据流、命名、配置），对照检查不一致项并整理成问题清单；这一轮只做读取和比对，不改任何文件。

我先读取核心文档（readme + docs）建立“应有行为”基线，然后再去对照代码实现，输出可追踪到文件位置的问题列表。

Read [](file:///d%3A/Projects/ADE/readme.md)

Read [](file:///d%3A/Projects/ADE/docs/overview.md)

Read [](file:///d%3A/Projects/ADE/docs/architecture.md#1-1), lines 1 to 320

Read [](file:///d%3A/Projects/ADE/docs/ingest.md#1-1), lines 1 to 320

Read [](file:///d%3A/Projects/ADE/docs/query.md)

我已经拿到文档基线，下一步会读取核心实现（导入、数据集、查询、共享常量/UI）并逐条对照文档承诺，重点找“文档写了但代码没有”或“代码行为与文档冲突”的地方。

Read [](file:///d%3A/Projects/ADE/docs/client-import-rules.md#1-1), lines 1 to 320

Read [](file:///d%3A/Projects/ADE/docs/deployment.md)

Read [](file:///d%3A/Projects/ADE/pyproject.toml)

Read [](file:///d%3A/Projects/ADE/docs/ade-pro-integration.md)

我已经补齐了部署与集成文档，现在开始对照核心实现文件（shared/dataset/ingest/query），先核对数据模型与主流程是否一致，再看 UI 交互和文档承诺是否落地。

Read [](file:///d%3A/Projects/ADE/shared/schema.py)

Read [](file:///d%3A/Projects/ADE/shared/constants.py)

Read [](file:///d%3A/Projects/ADE/dataset/manifest_service.py)

Read [](file:///d%3A/Projects/ADE/dataset/registry_service.py)

Read [](file:///d%3A/Projects/ADE/dataset/package_service.py)

Read [](file:///d%3A/Projects/ADE/dataset/query_dataset.py)

Read [](file:///d%3A/Projects/ADE/ingest/import_service.py)

Read [](file:///d%3A/Projects/ADE/ingest/client_profile_service.py)

Read [](file:///d%3A/Projects/ADE/ingest/duckdb_cleaning_service.py)

Read [](file:///d%3A/Projects/ADE/ingest/mapping_service.py)

目前已确认数据层里仍有旧 journal 命名与新 ledger 并存，接下来我会检查 UI 和应用入口是否与文档中的“统一入口、最近数据集、金额规则交互”一致，再汇总差异。

Read [](file:///d%3A/Projects/ADE/apps/ingest_app.py)

Read [](file:///d%3A/Projects/ADE/apps/query_app.py)

Read [](file:///d%3A/Projects/ADE/apps/main_app.py)

Read [](file:///d%3A/Projects/ADE/ui_ingest/ingest_window.py#1-1), lines 1 to 460

Read [](file:///d%3A/Projects/ADE/ui_ingest/mapping_dialog.py)

Read [](file:///d%3A/Projects/ADE/ui_ingest/ingest_window.py#460-460), lines 460 to 747

Read [](file:///d%3A/Projects/ADE/ui_query/query_window.py)

Read [](file:///d%3A/Projects/ADE/query/query_service.py)

Read [](file:///d%3A/Projects/ADE/query/sql_runner.py)

Read [](file:///d%3A/Projects/ADE/query/export_service.py)

Read [](file:///d%3A/Projects/ADE/query/sql_history_service.py)

Read [](file:///d%3A/Projects/ADE/analysis/rule_service.py)

Read [](file:///d%3A/Projects/ADE/analysis/anomaly_detection.py)

Read [](file:///d%3A/Projects/ADE/analysis/journal_analysis.py)

Read [](file:///d%3A/Projects/ADE/ui_query/visual_query.py)

Read [](file:///d%3A/Projects/ADE/scripts/verify_ade_pro.py)

Read [](file:///d%3A/Projects/ADE/query/query_builder.py)

Read [](file:///d%3A/Projects/ADE/shared/client_router.py)

Read [](file:///d%3A/Projects/ADE/shared/db.py)

Read [](file:///d%3A/Projects/ADE/shared/errors.py)

Read [](file:///d%3A/Projects/ADE/ui_query/chart_viewer.py)

Read [](file:///d%3A/Projects/ADE/ui_ingest/import_report_view.py)

Read [](file:///d%3A/Projects/ADE/ui_query/sql_editor.py)

我已完成主流程与 UI 对照，下一步会检查其余模块文件（importer、utils、README 中提及脚本）是否存在“文档有描述但代码未实现/接口仍旧式”的情况，然后给出完整问题列表。

Read [](file:///d%3A/Projects/ADE/query/export_service.py)

Read [](file:///d%3A/Projects/ADE/ingest/excel_importer.py)

Read [](file:///d%3A/Projects/ADE/ingest/csv_importer.py)

Read [](file:///d%3A/Projects/ADE/ingest/duckdb_importer.py)

Read [](file:///d%3A/Projects/ADE/ingest/parquet_importer.py)

Read [](file:///d%3A/Projects/ADE/ui_query/table_viewer.py)

Searched for regex `import_mode=\"dataset\"|duplicate_rows=0|ImportRequest\(|duplicate_mode` (`**/*.py`), 10 results

Searched for regex `required_columns|clean_rules|\[profiles.match\]|version = 2` (`**/ingest/client_profile_service.py`), 2 results

Searched for regex `All Supported \(\*\.xlsx \*\.csv \*\.duckdb\)|source_type_combo.addItems` (`**/ui_ingest/ingest_window.py`), 2 results

Searched for regex `recent_table.setColumnCount\(7\)|HorizontalHeaderLabels\(|last_opened_at|status` (`**/ui_query/query_window.py`), 6 results

Searched for regex `default file name|sql_export|query_export\.xlsx|getSaveFileName` (`**/ui_query/query_window.py`), 3 results

Searched for regex `required_columns|clean_rules|find_profile\(|导入报告必须记录|新导入|追加导入|每次导入必须显式指定` (`**/docs/client-import-rules.md`), 9 results

Searched for regex `导入模式|重复处理策略|最近数据集|最近转换|默认文件名|sql_export` (`**/docs/*.md`), 34 results

Searched for regex `source_file =|dataset\.toml|ledger\.parquet` (`**/docs/*.md`), 71 results

Searched for regex `source_file=str\(source_path\)|source_file=|DatasetManifest\(` (`**/ingest/duckdb_cleaning_service.py`), 2 results

Searched for regex `resolve_manifest_path|candidate = path.parent / "dataset.toml"` (`**/dataset/query_dataset.py`), 3 results

Searched for regex `source_type=str\(match.get\("source_type"|source_sheet=str\(match\["source_sheet"\]|required_sources = \[|\[profiles.amount_rules\]` (`**/ingest/client_profile_service.py`), 5 results

Searched for regex `amount_mode|debit_values|credit_values|import_errors|field_mapping_report|show_result` (`**/ui_ingest/import_report_view.py`), 5 results

Searched for regex `导入报告必须记录|金额处理模式|借贷标识无法识别行数|借贷双列同时有值行数` (`**/docs/ingest.md`), 4 results

Searched for regex `debit_credit_columns|同一行不应同时存在借方金额和贷方金额|都为空` (`**/docs/ingest.md`), 4 results

Searched for regex `_invalid_row_condition\(|rc_amount IS NULL|NULLIF\(TRIM\(description\)|debit|credit` (`**/ingest/duckdb_cleaning_service.py`), 24 results

Searched for regex `SELECT \* FROM ledger LIMIT 200|兼容示例|旧 journal` (`**/query/sql_history_service.py`), 3 results

Searched for regex `Excel/CSV/DuckDB/Parquet|来源类型|parquet|duckdb` (`**/docs/ingest.md`), 33 results

Searched for regex `status = "可查询" if parquet_path.exists\(\) else "Parquet 缺失"|Manifest 错误|文件缺失|inspect_ledger_parquet` (`**/dataset/registry_service.py`), 3 results

Searched for regex `if request.import_mode not in \{"new", "append"\}|build_dataset\(|duplicate_mode|import_mode` (`**/ingest/import_service.py`), 2 results

Searched for regex `def build_dataset\(|import_mode|duplicate_mode` (`**/ingest/duckdb_cleaning_service.py`), 2 results

Searched for regex `source_table: str = "journal"|"journal",\n\s*self\._selected_sheet\(\),\n\s*10|source_table="journal"|source_table=request.source_table` (`**/ui_ingest/ingest_window.py`), 1 result

Searched for regex `source_table: str = "journal"|target_table: str = "journal"|class ImportRequest` (`**/shared/schema.py`), 3 results

已完成静态对照检查（代码与文档），本轮未修改任何代码。以下是发现的问题，按严重程度排序。

1. 高：导入模式与重复策略在实现上基本未落地  
文档要求支持“新导入覆盖该客户该年度”和“追加导入+重复策略处理”，但代码中仅校验了模式值，后续流程未使用该语义，返回结果也固定为 dataset、duplicate_rows 固定为 0。  
证据：  
ingest.md  
ingest.md  
ingest.md  
import_service.py  
import_service.py  
duckdb_cleaning_service.py  
duckdb_cleaning_service.py  
duckdb_cleaning_service.py

2. 高：导入页面宣称支持 Parquet 来源，但文件选择器未包含 parquet 扩展名  
来源类型下拉有 parquet，但打开文件过滤器没有 *.parquet，实际用户路径上会造成功能不可达或不直观。  
证据：  
ingest.md  
ingest.md  
ingest_window.py  
ingest_window.py

3. 高：客户 profile 规范与实现不一致（required_columns、clean_rules 缺失）  
文档定义了 profiles.match.required_columns 和 profiles.clean_rules，并要求基于 required_columns 做匹配优先级；代码仅处理 source_type/source_sheet 和映射字段推断，未读写 clean_rules。  
证据：  
client-import-rules.md  
client-import-rules.md  
client-import-rules.md  
client-import-rules.md  
client_profile_service.py  
client_profile_service.py  
client_profile_service.py  
client_profile_service.py  
client_profile_service.py  
client_profile_service.py

4. 中高：导入报告字段不满足文档约定；金额校验规则也不完整  
文档要求报告包含金额模式、无法识别借贷标识行数、借贷双列冲突行数等；当前报告主要是 field_mapping_report 和 import_errors。  
同时文档要求 debit_credit_columns 场景下“同一行不能借贷同时有值/同时为空”，当前 SQL 通过 COALESCE 计算，未显式拦截这两类冲突。  
证据：  
ingest.md  
ingest.md  
ingest.md  
ingest.md  
ingest.md  
ingest.md  
import_report_view.py  
import_report_view.py  
import_report_view.py  
duckdb_cleaning_service.py  
duckdb_cleaning_service.py  
duckdb_cleaning_service.py

5. 中：最近数据集展示字段与文档不一致（缺少最近转换 created_at）  
文档要求展示“最近转换 created_at”；当前表头没有该列。  
证据：  
query.md  
query.md  
architecture.md  
architecture.md  
query_window.py  
query_window.py

6. 中：最近数据集状态未覆盖“schema 不匹配”判定  
文档将状态包含 schema 不匹配；当前 registry 摘要状态主要为文件缺失、Parquet 缺失、Manifest 错误、可查询，未进行 schema 校验。  
证据：  
architecture.md  
registry_service.py  
registry_service.py  
registry_service.py

7. 中：导出默认文件名与文档规范不一致  
文档约定默认名为 sql_export_{client}_{timestamp}.xlsx，当前默认为 query_export.xlsx。  
证据：  
query.md  
query_window.py

8. 低：manifest 的 source_file 内容与文档示例口径不一致  
文档示例是源文件名（如 raw_ledger.xlsx）；实现写入的是完整路径字符串。功能可用，但与文档示例和可分享性口径有偏差。  
证据：  
ingest.md  
client-import-rules.md  
duckdb_cleaning_service.py

如果你愿意，我下一步可以按以上问题给一版“最小改动修复清单”（先只出方案不改代码，或直接按优先级逐项修）。

1. 高：导入模式与重复策略在实现上基本未落地  
文档要求支持“新导入覆盖该客户该年度”和“追加导入+重复策略处理”，但代码中仅校验了模式值，后续流程未使用该语义，返回结果也固定为 dataset、duplicate_rows 固定为 0。  
证据：  
ingest.md  
ingest.md  
ingest.md  
import_service.py  
import_service.py  
duckdb_cleaning_service.py  
duckdb_cleaning_service.py  
duckdb_cleaning_service.py

2. 高：导入页面宣称支持 Parquet 来源，但文件选择器未包含 parquet 扩展名  
来源类型下拉有 parquet，但打开文件过滤器没有 *.parquet，实际用户路径上会造成功能不可达或不直观。  
证据：  
ingest.md  
ingest.md  
ingest_window.py  
ingest_window.py

3. 高：客户 profile 规范与实现不一致（required_columns、clean_rules 缺失）  
文档定义了 profiles.match.required_columns 和 profiles.clean_rules，并要求基于 required_columns 做匹配优先级；代码仅处理 source_type/source_sheet 和映射字段推断，未读写 clean_rules。  
证据：  
client-import-rules.md  
client-import-rules.md  
client-import-rules.md  
client-import-rules.md  
client_profile_service.py  
client_profile_service.py  
client_profile_service.py  
client_profile_service.py  
client_profile_service.py  
client_profile_service.py

4. 中高：导入报告字段不满足文档约定；金额校验规则也不完整  
文档要求报告包含金额模式、无法识别借贷标识行数、借贷双列冲突行数等；当前报告主要是 field_mapping_report 和 import_errors。  
同时文档要求 debit_credit_columns 场景下“同一行不能借贷同时有值/同时为空”，当前 SQL 通过 COALESCE 计算，未显式拦截这两类冲突。  
证据：  
ingest.md  
ingest.md  
ingest.md  
ingest.md  
ingest.md  
ingest.md  
import_report_view.py  
import_report_view.py  
import_report_view.py  
duckdb_cleaning_service.py  
duckdb_cleaning_service.py  
duckdb_cleaning_service.py

5. 中：最近数据集展示字段与文档不一致（缺少最近转换 created_at）  
文档要求展示“最近转换 created_at”；当前表头没有该列。  
证据：  
query.md  
query.md  
architecture.md  
architecture.md  
query_window.py  
query_window.py

6. 中：最近数据集状态未覆盖“schema 不匹配”判定  
文档将状态包含 schema 不匹配；当前 registry 摘要状态主要为文件缺失、Parquet 缺失、Manifest 错误、可查询，未进行 schema 校验。  
证据：  
architecture.md  
registry_service.py  
registry_service.py  
registry_service.py

7. 中：导出默认文件名与文档规范不一致  
文档约定默认名为 sql_export_{client}_{timestamp}.xlsx，当前默认为 query_export.xlsx。  
证据：  
query.md  
query_window.py

8. 低：manifest 的 source_file 内容与文档示例口径不一致  
文档示例是源文件名（如 raw_ledger.xlsx）；实现写入的是完整路径字符串。功能可用，但与文档示例和可分享性口径有偏差。  
证据：  
ingest.md  
client-import-rules.md  
duckdb_cleaning_service.py

如果你愿意，我下一步可以按以上问题给一版“最小改动修复清单”（先只出方案不改代码，或直接按优先级逐项修）。


好的，下面给你一版 最小改动修复清单（先作为实施方案，不改代码）。

**优先级 P0（先做）**
1. 补齐导入模式与重复策略的真实语义
目标：
- new：按 client_name + fiscal_year 覆盖已有数据集（至少覆盖最近同名或同年度数据包）
- append：保留历史并执行重复策略（mark/skip/strict）
最小改动建议：
- 在 import_service.py 之后把 import_mode/duplicate_mode 继续传入清洗层
- 在 duckdb_cleaning_service.py 增加对应参数并落地逻辑
- 修正返回值中的 import_mode、duplicate_rows，不再固定值（目前见 duckdb_cleaning_service.py）
验收：
- new/append 导入结果差异可观察
- duplicate_mode 三种策略行为可复现且写入报告

2. 导入文件选择器补上 parquet
目标：
- UI 与文档一致支持 Excel/CSV/DuckDB/Parquet
最小改动建议：
- 修改 ingest_window.py 的 QFileDialog 过滤器，加上 *.parquet
验收：
- 选择来源类型为 parquet 时可以直接选 .parquet 文件

3. profile 结构与匹配规则对齐文档
目标：
- 支持 profiles.match.required_columns 与 profiles.clean_rules
最小改动建议：
- 在 client_profile_service.py 扩展 load/save 结构
- 在 client_profile_service.py 的匹配逻辑优先使用 required_columns 子集匹配与数量优先
验收：
- 同一客户多 profile 时能按 required_columns 最长命中
- clean_rules 可持久化读写

**优先级 P1（第二批）**
4. 导入报告补齐金额规则统计字段
目标：
- 报告包含金额模式、借贷识别失败行数、借贷双列冲突行数等文档要求
最小改动建议：
- 在 duckdb_cleaning_service.py 增加统计 SQL
- 在 schema.py 扩展 ImportResult 字段
- 在 import_report_view.py 展示新字段
验收：
- 报告 JSON 中可见文档要求的关键统计项

5. debit_credit_columns 增加行级一致性校验
目标：
- 拦截“借贷同有值”与“借贷同为空”
最小改动建议：
- 在 duckdb_cleaning_service.py 的 invalid 条件补充双列规则
验收：
- 两类异常行进入 import_errors，不落入 ledger

6. 最近数据集列表补“最近转换”
目标：
- 对齐 created_at 展示要求
最小改动建议：
- query_window.py 增加列并渲染 last_opened_at 或 manifest created_at（建议显示 manifest created_at，last_opened_at 另列）
验收：
- 列表可见“最近转换”时间字段

**优先级 P2（收口）**
7. 最近数据集状态补 schema 不匹配
目标：
- 状态覆盖可查询/文件缺失/schema 不匹配
最小改动建议：
- 在 registry_service.py 对每个 manifest 的 parquet 调用 schema 校验（可复用 query_dataset.py 的 required 集合）
验收：
- required 缺失时状态显示 schema 不匹配而非可查询

8. 导出默认命名改为文档规范
目标：
- 默认导出名 sql_export_{client}_{yyyyMMdd_HHmmss}.xlsx
最小改动建议：
- 调整 query_window.py 默认路径构造
验收：
- 导出对话框默认文件名符合规范

9. source_file 统一为文件名而非绝对路径（可选）
目标：
- 减少跨机路径噪音，贴近文档
最小改动建议：
- duckdb_cleaning_service.py 改为 source_path.name（或保留完整路径另存 source_path 字段）
验收：
- 新生成 manifest 中 source_file 为文件名

**建议执行顺序**
1. P0 三项  
2. P1 三项  
3. P2 三项  
每完成一批就跑一次 verify_ade_pro.py 并补对应回归用例。

如果你同意，我下一步可以直接按这个顺序开始改代码并逐项回报结果。
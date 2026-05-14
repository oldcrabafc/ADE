from __future__ import annotations

from math import ceil

import xlsxwriter

from shared.schema import ExportRequest, ExportResult, QueryResult


def export_query_result_to_excel(result: QueryResult, request: ExportRequest) -> ExportResult:
    request.output_path.parent.mkdir(parents=True, exist_ok=True)
    total_rows = len(result)
    rows_per_sheet = max(1, request.max_rows_per_sheet)
    sheet_count = max(1, ceil(total_rows / rows_per_sheet))

    workbook = xlsxwriter.Workbook(str(request.output_path))
    try:
        if total_rows == 0:
            worksheet = workbook.add_worksheet("sheet1")
            for col_index, column in enumerate(result.columns):
                worksheet.write(0, col_index, column)
        else:
            for sheet_index in range(sheet_count):
                worksheet = workbook.add_worksheet(f"sheet{sheet_index + 1}")
                for col_index, column in enumerate(result.columns):
                    worksheet.write(0, col_index, column)
                start = sheet_index * rows_per_sheet
                end = min(start + rows_per_sheet, total_rows)
                for row_offset, row in enumerate(result.rows[start:end], start=1):
                    for col_index, value in enumerate(row):
                        worksheet.write(row_offset, col_index, "" if value is None else value)
    finally:
        workbook.close()

    return ExportResult(
        client_name=request.client_name,
        file_path=str(request.output_path),
        sheet_count=sheet_count,
        total_rows=total_rows,
        split_applied=sheet_count > 1,
    )

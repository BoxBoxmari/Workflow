---
name: xlsx
description: "Creates, edits, and analyzes spreadsheets (.xlsx, .xlsm, .csv, .tsv) with formulas, formatting, and data analysis. Use when creating Excel files, reading or analyzing sheet data, modifying workbooks while preserving formulas, building financial models, or recalculating formulas."
---

# XLSX Creation, Editing, and Analysis

## Output Requirements

### All Excel files

- **Zero formula errors**: Deliver with no #REF!, #DIV/0!, #VALUE!, #N/A, #NAME?
- **Preserve templates**: Match existing format, style, and conventions exactly. Never overwrite established patterns with generic formatting.

### Financial models (defaults unless user or template says otherwise)

| Element | Convention |
| --- | --- |
| **Blue text** (0,0,255) | Hardcoded inputs, scenario inputs |
| **Black** (0,0,0) | All formulas and calculations |
| **Green** (0,128,0) | Links to other sheets (same workbook) |
| **Red** (255,0,0) | External links to other files |
| **Yellow fill** (255,255,0) | Key assumptions / cells to update |

**Number formatting**: Years as text ("2024"); currency with $#,##0 and units in headers ("Revenue ($mm)"); zeros as "-" via format e.g. `$#,##0;($#,##0);-`; percentages 0.0%; multiples 0.0x; negatives in parentheses.

**Formulas**: Put assumptions in separate cells; reference cells, no hardcoded numbers in formulas (e.g. `=B5*(1+$B$6)` not `=B5*1.05`). Document hardcoded sources in comments or adjacent cells: "Source: [System/Document], [Date], [Reference], [URL]".

---

## CRITICAL: Use Formulas, Not Hardcoded Values

**Always use Excel formulas so the sheet stays dynamic.** Do not compute in Python and write a single number.

**Wrong** – hardcoding calculated values:

```python
sheet['B10'] = df['Sales'].sum()           # Hardcodes result
sheet['C5'] = (c4 - c2) / c2               # Hardcodes growth
sheet['D20'] = sum(values) / len(values)   # Hardcodes average
```

**Correct** – Excel formulas:

```python
sheet['B10'] = '=SUM(B2:B9)'
sheet['C5'] = '=(C4-C2)/C2'
sheet['D20'] = '=AVERAGE(D2:D19)'
```

Use formulas for totals, percentages, ratios, differences, and any value that should update when inputs change.

---

## Workflow Overview

1. **Tool choice**: pandas for data/analysis; openpyxl for formulas and formatting.
2. **Create or load**: New workbook or `load_workbook('file.xlsx')`.
3. **Edit**: Data, formulas, formatting.
4. **Save**: `wb.save('output.xlsx')`.
5. **Recalculate (required when using formulas)**: `python recalc.py output.xlsx [timeout_seconds]`.
6. **Verify**: Fix any errors reported by recalc.py; rerun until clean.

**LibreOffice**: Assume LibreOffice is available for formula recalculation. The `recalc.py` script configures it on first run.

---

## Reading and Analyzing

```python
import pandas as pd

df = pd.read_excel('file.xlsx')                    # First sheet
all_sheets = pd.read_excel('file.xlsx', sheet_name=None)  # All sheets as dict

df.head()
df.info()
df.describe()

# Write back
df.to_excel('output.xlsx', index=False)
```

For large files: `usecols`, `dtype`, `parse_dates`. Use `read_only=True` / `write_only=True` in openpyxl when appropriate.

---

## Creating New Excel Files

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

wb = Workbook()
sheet = wb.active

sheet['A1'] = 'Hello'
sheet['B1'] = 'World'
sheet.append(['Row', 'of', 'data'])
sheet['B2'] = '=SUM(A1:A10)'

sheet['A1'].font = Font(bold=True, color='FF0000')
sheet['A1'].fill = PatternFill('solid', start_color='FFFF00')
sheet['A1'].alignment = Alignment(horizontal='center')
sheet.column_dimensions['A'].width = 20

wb.save('output.xlsx')
```

---

## Editing Existing Excel Files

```python
from openpyxl import load_workbook

wb = load_workbook('existing.xlsx')
sheet = wb.active  # or wb['SheetName']

for name in wb.sheetnames:
    ws = wb[name]
    # ...

sheet['A1'] = 'New Value'
sheet.insert_rows(2)
sheet.delete_cols(3)
new_sheet = wb.create_sheet('NewSheet')
new_sheet['A1'] = 'Data'

wb.save('modified.xlsx')
```

**Warning**: `load_workbook('file.xlsx', data_only=True)` reads calculated values; saving then **replaces formulas with values**. Use `data_only=True` only for read-only analysis.

---

## Recalculating Formulas

openpyxl does not evaluate formulas. After writing or editing, run:

```bash
python recalc.py output.xlsx [timeout_seconds]
# Example: python recalc.py output.xlsx 30
```

The script uses LibreOffice to recalculate all formulas and scan for errors. Example JSON output:

```json
{
  "status": "success",
  "total_errors": 0,
  "total_formulas": 42
}
```

If errors exist: `"status": "errors_found"`, `"error_summary"` lists types (#REF!, #DIV/0!, #VALUE!, #NAME?) and locations (e.g. Sheet1!B5). Fix those cells and run recalc again until status is success.

---

## Formula Verification Checklist

- [ ] Spot-check 2–3 references; confirm columns (e.g. 64 = BL).
- [ ] Excel rows are 1-based (DataFrame row 5 → Excel row 6).
- [ ] Handle NaN; check far-right columns (e.g. FY in cols 50+).
- [ ] Avoid division by zero; validate all referenced cells exist.
- [ ] Cross-sheet refs: use `Sheet1!A1` format.
- [ ] Test on a few cells first; then apply to full range.

---

## Library Usage

| Task                                | Prefer   |
| ----------------------------------- | -------- |
| Data analysis, bulk read/write, CSV | pandas   |
| Formulas, formatting, structure     | openpyxl |

**openpyxl**: 1-based rows/columns; `data_only=True` loses formulas on save; use read_only/write_only for large workbooks.

**pandas**: Set `dtype`, `usecols`, `parse_dates` as needed to avoid inference issues.

---

## Code Style

- Minimal, concise Python; no redundant comments or prints.
- In the Excel file: add cell comments for complex formulas and key assumptions; document sources for hardcoded values.

---

## Dependencies

- **openpyxl**: `pip install openpyxl` – create/edit .xlsx with formulas and formatting.
- **pandas**: `pip install pandas openpyxl` – read/write and analyze.
- **LibreOffice**: Required for `recalc.py` (formula recalculation and error scan).

Assume `recalc.py` is available in the project; path may vary (e.g. `scripts/recalc.py`). Adjust the command if your repo uses a different location.

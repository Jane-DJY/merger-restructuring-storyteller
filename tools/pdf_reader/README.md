# 公告文件读取工具

用于读取公告、报告书、预案或说明书文件内容，支持读取全文、页码范围或单页。

## 使用示例

```bash
python3 pdf_reader.py "公告说明书.pdf"
python3 pdf_reader.py "公告说明书.pdf" --start-page 1 --end-page 5
python3 pdf_reader.py "公告说明书.pdf" --page 3
```

## 参数

| 参数 | 说明 |
|---|---|
| `pdf_path` | 公告文件路径 |
| `--start-page` | 起始页码，从 1 开始，包含该页 |
| `--end-page` | 结束页码，从 1 开始，包含该页 |
| `--page` | 只读取指定页码 |

工具会自动尝试可用的本地解析库。若读取失败，先安装 `pymupdf`；复杂字体文件也可补充安装 `pdfplumber` 或 `PyPDF2`。

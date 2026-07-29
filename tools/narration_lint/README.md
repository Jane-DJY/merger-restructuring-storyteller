# 旁白稿检查工具

检查最终 Markdown 旁白稿是否包含必要栏目，以及是否出现不宜使用的解释腔或夸张表达。`html chart` 段落还会检查 `【画面数据】` 是否紧跟 `【画面】`，并包含主体、指标、期间、数值和单位。

```bash
python3 tools/narration_lint/narration_lint.py "并购重组旁白稿.md"
```

除非提醒内容只出现在用户原始要求或引用材料中，否则通常需要修改。

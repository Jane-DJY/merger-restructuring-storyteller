# 研报搜索工具

用于按关键词搜索研报片段，辅助补充并购重组标的公司的业务背景、行业地位或交易原因。该工具需要联网，并且需要提前配置授权环境变量。

## 授权

```bash
export AICUBES_AUTHORIZATION="你的授权令牌"
```

## 使用示例

```bash
python3 report_search.py --query "浙建集团 建筑施工"
python3 report_search.py --query "多喜爱 重大资产重组"
```

## 参数

| 参数 | 说明 |
|---|---|
| `--query` | 查询关键词 |

输出为 Markdown 表格，包含日期、标题、摘要、全文片段和溯源地址。

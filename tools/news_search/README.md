# 财联社资讯搜索工具

用于按关键词查询财联社电报、文章或视频，辅助了解并购重组事项相关的近期报道和重要事件。该工具需要联网。

## 使用示例

```bash
python3 news_search.py --keyword "浙建集团"
python3 news_search.py --keyword "多喜爱 重大资产重组" --type article
python3 news_search.py --keyword "浙江建投" --page 1 --rn 50
python3 news_search.py --keyword "浙江建投" --start-date "2024-01-01" --end-date "2024-12-31"
```

## 常用参数

| 参数 | 说明 |
|---|---|
| `--keyword` | 查询关键词 |
| `--type` | 查询类型，可选电报、文章、视频对应的接口值 |
| `--page` | 页码 |
| `--rn` | 每页数量 |
| `--start-date` | 开始日期 |
| `--end-date` | 结束日期 |
| `--sign` | 签名参数，通常不需要手动填写 |

输出为 Markdown 表格，列为作者、内容和发布时间。

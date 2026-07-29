# 画面数据检查工具

从画面数据 `.txt` 或 `.rtf` 文件中抽取按顺序排列的交易步骤。

```bash
python3 tools/transaction_data_inspector/transaction_data_inspector.py "浙江建投原始数据.txt"
python3 tools/transaction_data_inspector/transaction_data_inspector.py "浙江建投原始数据.txt" --output 交易步骤核对.md
```

写旁白前，先用输出结果锁定步骤数量、步骤名称和步骤顺序。

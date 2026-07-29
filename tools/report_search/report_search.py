#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
研报搜索工具
用于搜索股票研报信息，支持流式输出
"""

import requests
import json
import os
import sys
from typing import Optional


def run_model(query: str) -> Optional[str]:
    """
    运行研报搜索模型（流式输出）
    
    Args:
        query: 查询内容
        
    Returns:
        完整结果字符串，如果出错返回None
    """
    authorization = os.environ.get("AICUBES_AUTHORIZATION")
    if not authorization:
        print(
            "缺少环境变量 AICUBES_AUTHORIZATION，无法调用研报搜索服务。",
            file=sys.stderr,
        )
        return None

    # Headers
    headers = {
        'Content-Type': 'application/json',
        "Authorization": authorization,
    }

    # Request payload
    data = {
        "mode": "WORK_FLOW",
        "inputVariableValue": {
            "query": query,
        },
        "releaseState": "1",
        "flowId": "23652"
    }

    # URL
    url = "http://vtuber.aicubes.cn/agent-studio/flow/run_by_flux"

    try:
        # 流式输出模式
        response = requests.post(url, headers=headers, json=data, stream=True, timeout=300)
        response.raise_for_status()
        
        # 处理流式响应，找到最后一个 type=result 的 JSON
        # 每个 message 都是一个完整的 JSON，格式为 data: {...}
        result_text = None
        
        for line in response.iter_lines():
            if line:
                try:
                    line_str = line.decode('utf-8')
                    
                    # 跳过空行
                    if not line_str.strip():
                        continue
                    
                    # 处理 data: {...} 格式
                    json_str = line_str
                    if line_str.startswith('data: '):
                        json_str = line_str[6:]  # 去掉 'data: ' 前缀
                    elif line_str.startswith('data:'):
                        json_str = line_str[5:]  # 去掉 'data:' 前缀
                    
                    # 跳过可能的空格
                    json_str = json_str.strip()
                    if not json_str:
                        continue
                    
                    try:
                        json_data = json.loads(json_str)
                        # 检查是否是 result 类型
                        if json_data.get('type') == 'result':
                            # 提取 response.text
                            # 路径：data.response.text
                            if 'data' in json_data and isinstance(json_data['data'], dict):
                                data_obj = json_data['data']
                                if 'response' in data_obj and isinstance(data_obj['response'], dict):
                                    response_obj = data_obj['response']
                                    if 'text' in response_obj:
                                        result_text = response_obj['text']
                    except json.JSONDecodeError:
                        # 忽略无法解析的 JSON（可能是非 JSON 行）
                        continue
                            
                except Exception as e:
                    # 忽略处理错误，继续处理下一行
                    continue
        
        # 输出最终结果
        if result_text:
            print(result_text)
            return result_text
        else:
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"发生错误: {e}", file=sys.stderr)
        return None


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='研报搜索工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  python3 report_search.py --query "财务分析" 
        '''
    )
    
    parser.add_argument('--query', type=str, required=True, help='查询内容')
    
    args = parser.parse_args()
    
    print(f"正在搜索研报...")
    print(f"查询内容: {args.query}")
    print("-" * 80)
    
    result = run_model(query=args.query)
    
    if result:
        print("\n" + "=" * 80)
        print("搜索完成！")
    else:
        print("\n搜索失败或无结果返回", file=sys.stderr)
        sys.exit(1)

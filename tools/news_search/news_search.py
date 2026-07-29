#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社搜索工具
通过财联社的搜索接口，查询电报和资讯内容。
用于了解某个主题或话题最近一段时间相关的报道和重要事件。
"""

import argparse
import requests
from datetime import datetime
import sys
import json
import hashlib
import time


def generate_sign(params_dict, keyword="", timestamp=None):
    """
    生成sign参数（如果需要）
    尝试多种可能的签名算法
    
    Args:
        params_dict: 参数字典
        keyword: 搜索关键词
        timestamp: 时间戳
        
    Returns:
        sign字符串
    """
    # 如果API需要特定的签名算法，在这里实现
    # 尝试1: 使用时间戳
    if timestamp is None:
        timestamp = int(time.time())
    
    # 尝试不同的签名算法
    # 方法1: MD5(app+os+sv+timestamp)
    sign_str1 = f"CailianpressWebweb8.4.6{timestamp}"
    sign1 = hashlib.md5(sign_str1.encode()).hexdigest()
    
    # 方法2: MD5(keyword+timestamp)
    sign_str2 = f"{keyword}{timestamp}"
    sign2 = hashlib.md5(sign_str2.encode()).hexdigest()
    
    # 方法3: 默认固定值
    sign3 = "9f8797a1f4de66c2370f7a03990d2737"
    
    print(f"\n--- Sign生成调试 ---")
    print(f"方法1 (app+os+sv+timestamp): {sign1}")
    print(f"方法2 (keyword+timestamp): {sign2}")
    print(f"方法3 (固定值): {sign3}")
    print(f"--- Sign调试结束 ---\n")
    
    # 目前返回默认值
    return sign3


def timestamp_to_beijing_time(timestamp_s):
    """
    将时间戳（秒）转换为北京时间字符串
    
    Args:
        timestamp_s: 秒级时间戳
        
    Returns:
        格式化的时间字符串 yyyy-mm-dd HH:MM:SS
    """
    dt = datetime.fromtimestamp(timestamp_s)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def search_news(keyword='碳酸锂',
                search_type='telegram',
                page=0,
                rn=20,
                sign=None,
                start_date=None,
                end_date=None):
    """
    搜索财联社资讯信息
    
    Args:
        keyword: 搜索关键词（支持包含空格和特殊字符）
        search_type: 搜索类型，telegram(电报)、article(文章)、video(视频)（默认: telegram）
        page: 页码，从0开始（默认: 0，表示第一页）
        rn: 每页数量（默认: 20）
        sign: 签名参数，如果不提供则使用默认值
        start_date: 开始日期，格式为 YYYY-MM-DD（可选）
        end_date: 结束日期，格式为 YYYY-MM-DD，默认为当天（可选）
        
    Returns:
        查询结果字典，包含电报、文章或视频信息
    """
    # 构建URL参数
    url_params = {
        'app': 'CailianpressWeb',
        'os': 'web',
        'sv': '8.4.6'
    }
    
    # 如果提供了sign，添加到URL参数中
    if sign and sign != 'NO_SIGN':
        url_params['sign'] = sign
        print(f"使用提供的sign: {sign}")
    elif sign == 'NO_SIGN':
        # 不添加sign参数进行测试
        print("不使用sign参数进行测试")
    else:
        # 使用默认sign（实际使用时可能需要动态计算）
        url_params['sign'] = generate_sign(url_params, keyword=keyword)
        print(f"使用生成的sign: {url_params['sign']}")
    
    # 构建URL
    url = "https://www.cls.cn/api/sw"
    
    # 构建请求载荷
    payload = {
        "type": search_type,
        "keyword": keyword,  # JSON payload中直接使用原始字符串，不需要URL编码
        "page": page,
        "rn": rn,
        "os": "web",
        "sv": "8.4.6",
        "app": "CailianpressWeb"
    }
    
    # 添加日期参数（如果提供）
    if start_date:
        payload["startDate"] = start_date
    if end_date:
        payload["endDate"] = end_date
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://www.cls.cn',
        'Referer': 'https://www.cls.cn/'
    }
    
    try:
        # 打印调试信息
        print(f"\n--- 请求调试信息 ---")
        print(f"URL: {url}")
        print(f"URL参数: {url_params}")
        print(f"请求载荷: {json.dumps(payload, ensure_ascii=False)}")
        print(f"--- 调试信息结束 ---\n")
        
        # 发送POST请求，URL参数和JSON载荷
        response = requests.post(
            url,
            params=url_params,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        # 打印响应信息
        response_data = response.json()
        print(f"\n--- 响应调试信息 ---")
        print(f"状态码: {response.status_code}")
        print(f"响应体(前500字符): {json.dumps(response_data, ensure_ascii=False)[:500]}")
        print(f"--- 响应调试信息结束 ---\n")
        
        return response_data
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}", file=sys.stderr)
        return None
    except ValueError as e:
        print(f"JSON解析失败: {e}", file=sys.stderr)
        return None


def format_news_data(data, search_type='telegram'):
    """
    格式化资讯数据
    
    Args:
        data: API返回的原始数据
        search_type: 搜索类型
        
    Returns:
        格式化后的数据列表
    """
    if not data or 'data' not in data:
        return []
    
    data_section = data['data']
    
    # 根据搜索类型获取对应的数据
    news_list = None
    
    if search_type == 'telegram' and 'telegram' in data_section:
        telegram_data = data_section['telegram']
        if isinstance(telegram_data, dict):
            news_list = telegram_data.get('data', [])
    elif search_type == 'article' and 'article' in data_section:
        article_data = data_section['article']
        if isinstance(article_data, dict):
            news_list = article_data.get('data', [])
    elif search_type == 'video' and 'video' in data_section:
        video_data = data_section['video']
        if isinstance(video_data, dict):
            news_list = video_data.get('data', [])
    
    # 如果还没有找到数据，尝试从data中查找第一个非空的数据列表
    if news_list is None:
        for key in ['telegram', 'article', 'video', 'depth', 'featured']:
            if key in data_section:
                section_data = data_section[key]
                if isinstance(section_data, dict) and section_data.get('data'):
                    news_list = section_data.get('data', [])
                    if news_list:  # 确保列表不为空
                        break
    
    # 如果仍然没有找到数据，返回空列表
    if news_list is None or not isinstance(news_list, list):
        return []
    
    formatted_data = []
    for item in news_list:
        if not isinstance(item, dict):
            continue
            
        # 处理描述文本，移除HTML标签
        descr = item.get('descr', '')
        if descr:
            # 移除<em>标签但保留内容
            descr = descr.replace('<em>', '').replace('</em>', '')
        
        # 格式化时间
        time_str = ''
        if item.get('time'):
            try:
                time_str = timestamp_to_beijing_time(item.get('time', 0))
            except (ValueError, OSError):
                time_str = ''
        
        formatted_item = {
            'author': item.get('author', ''),
            'descr': descr,
            'time': time_str
        }
        formatted_data.append(formatted_item)
    
    return formatted_data


def display_results(data, search_type='telegram'):
    """
    显示查询结果
    
    Args:
        data: API返回的数据
        search_type: 搜索类型
    """
    if not data:
        print("查询失败或无数据返回")
        return
    
    if data.get('errno') != 0:
        print(f"查询失败: {data.get('msg', '未知错误')}")
        return
    
    data_section = data.get('data', {})
    
    # 获取对应类型的数据统计
    if search_type == 'telegram' and 'telegram' in data_section:
        result_info = data_section['telegram']
    elif search_type == 'article' and 'article' in data_section:
        result_info = data_section['article']
    elif search_type == 'video' and 'video' in data_section:
        result_info = data_section['video']
    else:
        # 尝试查找第一个非空的结果
        for key in ['telegram', 'article', 'video', 'depth', 'featured']:
            if key in data_section and data_section[key]:
                result_info = data_section[key]
                break
        else:
            print("没有找到相关资讯")
            return
    
    total_num = result_info.get('total_num', 0)
    rn = result_info.get('rn', 0)
    
    if total_num == 0:
        print("没有找到相关资讯")
        return
    
    formatted_data = format_news_data(data, search_type)
    
    if formatted_data:
        # 使用Markdown表格形式展示
        print("| 作者 | 内容 | 时间 |")
        print("|--------|-------|------|")
        
        for item in formatted_data:
            author = item['author'] or ''
            descr = item['descr'] or ''
            time_val = item['time'] or ''
            
            # 转义表格中的特殊字符
            descr = descr.replace('|', '\\|').replace('\n', ' ')
            
            print(f"| {author} | {descr} | {time_val} |")
    else:
        # 添加调试信息，帮助诊断问题
        print("数据格式异常，无法显示")
        print(f"\n调试信息：")
        print(f"  - errno: {data.get('errno', 'N/A')}")
        print(f"  - msg: {data.get('msg', 'N/A')}")
        if 'data' in data:
            data_section = data['data']
            print(f"  - data中的键: {list(data_section.keys())}")
            if search_type in data_section:
                section = data_section[search_type]
                print(f"  - {search_type}类型: {type(section)}")
                if isinstance(section, dict):
                    print(f"  - {search_type}中的键: {list(section.keys())}")
                    print(f"  - {search_type}.data类型: {type(section.get('data'))}")
                    if section.get('data') is not None:
                        print(f"  - {search_type}.data长度: {len(section.get('data', []))}")


def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(
        description='财联社搜索工具 - 查询电报和资讯，了解某个主题或话题最近一段时间相关的报道和重要事件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  # 使用默认参数查询（自动使用当天作为结束日期）
  python3 news_search.py
  
  # 指定关键词查询（支持包含空格）
  python3 news_search.py --keyword "碳酸锂"
  
  # 指定页码和每页数量（注意：page从0开始，0=第一页，1=第二页）
  python3 news_search.py --keyword "英伟达" --page 1 --rn 50
  
  # 指定日期范围查询
  python3 news_search.py --keyword "碳酸锂" --start-date "2024-01-01" --end-date "2024-12-31"
  
  # 只指定开始日期，结束日期默认为当天
  python3 news_search.py --keyword "核聚变" --start-date "2024-11-01"
  
  # 多词关键词可以直接使用空格
  python3 news_search.py --keyword "核聚变 招标"
  
  # 指定sign参数（如果需要）
  python3 news_search.py --keyword "碳酸锂价格" --sign "your_sign_value"

注意事项:
  - 关键词支持包含空格和特殊字符
  - 页码从0开始：0=第一页，1=第二页，以此类推
  - 支持查询类型：telegram(电报)、article(文章)、video(视频)
  - 结束日期默认为当天，可以通过 --end-date 自定义
  - 日期格式为 YYYY-MM-DD（如：2024-12-05）
        '''
    )
    
    parser.add_argument(
        '--keyword',
        type=str,
        default='碳酸锂',
        help='搜索关键词（默认: 碳酸锂）支持包含空格和特殊字符'
    )
    
    parser.add_argument(
        '--type',
        type=str,
        default='telegram',
        choices=['telegram', 'article', 'video'],
        help='搜索类型：telegram(电报)、article(文章)、video(视频)（默认: telegram）'
    )
    
    parser.add_argument(
        '--page',
        type=int,
        default=0,
        help='页码，从0开始（默认: 0，表示第一页）'
    )
    
    parser.add_argument(
        '--rn',
        type=int,
        default=20,
        help='每页数量（默认: 20）'
    )
    
    parser.add_argument(
        '--sign',
        type=str,
        default=None,
        help='签名参数（可选，如果不提供则使用默认值）'
    )
    
    parser.add_argument(
        '--no-sign',
        action='store_true',
        help='不使用sign参数进行测试'
    )
    
    parser.add_argument(
        '--start-date',
        type=str,
        default=None,
        help='开始日期，格式为 YYYY-MM-DD（可选，如：2024-01-01）'
    )
    
    parser.add_argument(
        '--end-date',
        type=str,
        default=None,
        help='结束日期，格式为 YYYY-MM-DD，默认为当天（可选）'
    )
    
    args = parser.parse_args()
    
    # 如果指定了--no-sign，则将sign设置为特殊值
    if args.no_sign:
        args.sign = 'NO_SIGN'
        print("⚠️  测试模式：不使用sign参数")
    
    # 如果没有提供end_date，默认使用当天日期
    if not args.end_date:
        args.end_date = datetime.now().strftime('%Y-%m-%d')
    
    # 执行查询
    print(f"正在查询财联社...")
    print(f"关键词: {args.keyword}")
    print(f"查询类型: {args.type}")
    print(f"页码: {args.page}, 每页数量: {args.rn}")
    if args.start_date:
        print(f"开始日期: {args.start_date}")
    if args.end_date:
        print(f"结束日期: {args.end_date}")
    
    result = search_news(
        keyword=args.keyword,
        search_type=args.type,
        page=args.page,
        rn=args.rn,
        sign=args.sign,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    # 显示结果
    display_results(result, args.type)


if __name__ == '__main__':
    main()

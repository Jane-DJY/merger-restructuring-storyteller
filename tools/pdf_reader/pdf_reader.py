#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 阅读器
用于读取 PDF 文件内容，支持指定页面范围
优先级：pymupdf > pdfplumber > PyPDF2
"""

import sys
import os
from typing import Optional, Tuple


def read_pdf_pymupdf(pdf_path: str, start_page: Optional[int] = None, end_page: Optional[int] = None) -> bool:
    """
    使用 pymupdf (fitz) 读取 PDF
    
    Args:
        pdf_path: PDF 文件路径
        start_page: 起始页码（从1开始，包含）
        end_page: 结束页码（从1开始，包含）
        
    Returns:
        成功返回 True，失败返回 False
    """
    try:
        import fitz  # pymupdf
        
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
        
        print(f"PDF总页数: {total_pages}\n")
        print("=" * 80)
        
        # 确定要读取的页面范围
        if start_page is None:
            start_page = 1
        if end_page is None:
            end_page = total_pages
        
        # 验证页面范围
        start_page = max(1, min(start_page, total_pages))
        end_page = max(start_page, min(end_page, total_pages))
        
        # 读取指定页面
        for i in range(start_page - 1, end_page):
            page_num = i + 1
            print(f"\n第{page_num}页内容：\n")
            page = doc[i]
            text = page.get_text()
            print(text)
            print("\n" + "=" * 80)
        
        doc.close()
        return True
        
    except ImportError:
        return False
    except Exception as e:
        print(f"pymupdf 读取失败: {e}", file=sys.stderr)
        return False


def read_pdf_pypdf2(pdf_path: str, start_page: Optional[int] = None, end_page: Optional[int] = None) -> bool:
    """
    使用 PyPDF2 读取 PDF
    
    Args:
        pdf_path: PDF 文件路径
        start_page: 起始页码（从1开始，包含）
        end_page: 结束页码（从1开始，包含）
        
    Returns:
        成功返回 True，失败返回 False
    """
    try:
        import PyPDF2
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            
            print(f"PDF总页数: {total_pages}\n")
            print("=" * 80)
            
            # 确定要读取的页面范围
            if start_page is None:
                start_page = 1
            if end_page is None:
                end_page = total_pages
            
            # 验证页面范围
            start_page = max(1, min(start_page, total_pages))
            end_page = max(start_page, min(end_page, total_pages))
            
            # 读取指定页面
            for i in range(start_page - 1, end_page):
                page_num = i + 1
                print(f"\n第{page_num}页内容：\n")
                text = pdf_reader.pages[i].extract_text()
                print(text)
                print("\n" + "=" * 80)
            
            return True
            
    except ImportError:
        return False
    except Exception as e:
        print(f"PyPDF2 读取失败: {e}", file=sys.stderr)
        return False


def read_pdf_pdfplumber(pdf_path: str, start_page: Optional[int] = None, end_page: Optional[int] = None) -> bool:
    """
    使用 pdfplumber 读取 PDF
    
    Args:
        pdf_path: PDF 文件路径
        start_page: 起始页码（从1开始，包含）
        end_page: 结束页码（从1开始，包含）
        
    Returns:
        成功返回 True，失败返回 False
    """
    try:
        import pdfplumber
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            print(f"PDF总页数: {total_pages}\n")
            print("=" * 80)
            
            # 确定要读取的页面范围
            if start_page is None:
                start_page = 1
            if end_page is None:
                end_page = total_pages
            
            # 验证页面范围
            start_page = max(1, min(start_page, total_pages))
            end_page = max(start_page, min(end_page, total_pages))
            
            # 读取指定页面
            for i in range(start_page - 1, end_page):
                page_num = i + 1
                print(f"\n第{page_num}页内容：\n")
                text = pdf.pages[i].extract_text()
                print(text)
                print("\n" + "=" * 80)
            
            return True
            
    except ImportError:
        return False
    except Exception as e:
        print(f"pdfplumber 读取失败: {e}", file=sys.stderr)
        return False


def read_pdf(pdf_path: str, start_page: Optional[int] = None, end_page: Optional[int] = None) -> bool:
    """
    读取 PDF 文件内容
    优先级：pymupdf > pdfplumber > PyPDF2
    
    Args:
        pdf_path: PDF 文件路径
        start_page: 起始页码（从1开始，包含）
        end_page: 结束页码（从1开始，包含）
        
    Returns:
        成功返回 True，失败返回 False
    """
    # 检查文件是否存在
    if not os.path.exists(pdf_path):
        print(f"错误：文件不存在: {pdf_path}", file=sys.stderr)
        return False
    
    if not pdf_path.lower().endswith('.pdf'):
        print(f"警告：文件扩展名不是 .pdf: {pdf_path}", file=sys.stderr)
    
    # 优先使用 pymupdf（对繁体字和复杂字体支持最好）
    if read_pdf_pymupdf(pdf_path, start_page, end_page):
        return True
    
    # 如果 pymupdf 失败，尝试使用 pdfplumber
    print("\n尝试使用 pdfplumber...", file=sys.stderr)
    if read_pdf_pdfplumber(pdf_path, start_page, end_page):
        return True
    
    # 如果 pdfplumber 失败，尝试使用 PyPDF2
    print("\n尝试使用 PyPDF2...", file=sys.stderr)
    if read_pdf_pypdf2(pdf_path, start_page, end_page):
        return True
    
    # 所有方法都失败
    print("错误：无法读取 PDF 文件。请确保已安装以下库之一：", file=sys.stderr)
    print("安装方法：", file=sys.stderr)
    print("  pip install pymupdf（推荐，对繁体字支持好）", file=sys.stderr)
    print("  pip install pdfplumber", file=sys.stderr)
    print("  pip install PyPDF2", file=sys.stderr)
    return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='PDF 阅读器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  # 读取整个 PDF
  python3 pdf_reader.py /path/to/file.pdf
  
  # 读取指定页面
  python3 pdf_reader.py /path/to/file.pdf --start-page 1 --end-page 5
  
  # 只读取第3页
  python3 pdf_reader.py /path/to/file.pdf --page 3
        '''
    )
    
    parser.add_argument('pdf_path', type=str, help='PDF 文件路径')
    parser.add_argument('--start-page', type=int, default=None, help='起始页码（从1开始，包含）')
    parser.add_argument('--end-page', type=int, default=None, help='结束页码（从1开始，包含）')
    parser.add_argument('--page', type=int, default=None, help='只读取指定页面（从1开始）')
    
    args = parser.parse_args()
    
    # 如果指定了 --page，则只读取该页
    start_page = args.page if args.page is not None else args.start_page
    end_page = args.page if args.page is not None else args.end_page
    
    print(f"正在读取 PDF: {args.pdf_path}")
    if start_page is not None or end_page is not None:
        if start_page == end_page:
            print(f"读取页面: {start_page}")
        else:
            print(f"读取页面范围: {start_page or '开始'} - {end_page or '结束'}")
    print("-" * 80)
    
    success = read_pdf(args.pdf_path, start_page, end_page)
    
    if not success:
        sys.exit(1)


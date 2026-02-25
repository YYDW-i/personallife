# news/utils.py
import re
from django.utils.html import strip_tags

def clean_news_summary(raw_text: str) -> str:
    """去除 HTML 标签、特殊标记，并压缩空白"""
    if not raw_text:
        return ''
    # 1. 去除标准 HTML 标签
    text = strip_tags(raw_text)
    # 2. 去除类似 |--begin:htmlVideoCode--...--| 的特殊标记（可根据需要调整正则）
    text = re.sub(r'\|--.*?--\|', '', text, flags=re.DOTALL)
    # 3. 将连续的空白（换行、空格、制表符）压缩为单个空格
    text = re.sub(r'\s+', ' ', text)
    # 4. 去除首尾空格
    return text.strip()
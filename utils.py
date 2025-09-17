"""
通用工具函数模块
"""
from typing import Any


def safe_format(template: str, **kwargs: Any) -> str:
    """
    使用 .format_map() 安全地格式化字符串。
    模板中不存在的键将被忽略，而不是引发 KeyError。
    
    Args:
        template: 格式化模板字符串
        **kwargs: 格式化参数
        
    Returns:
        格式化后的字符串
    """
    class SafeDict(dict):
        def __missing__(self, key):
            return f'{{{key}}}'
    return template.format_map(SafeDict(kwargs))
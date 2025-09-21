"""
通用工具函数模块
"""
from typing import Any
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent


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

def check_platform(event: AstrMessageEvent) -> bool:
    """
    检查平台是否为AiocqhttpAdapter
    
    Args:
        event: 消息事件
        
    Returns:
        如果是AiocqhttpAdapter平台返回True，否则返回False
    """
    platform_name = event.get_platform_name()
    if platform_name != "aiocqhttp":
        logger.debug(f"[Authenticator] 跳过非aiocqhttp平台事件: {platform_name}")
        return False
    return True
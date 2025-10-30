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
    try:
        # 检查 event 是否有 get_platform_name 方法
        if not hasattr(event, 'get_platform_name'):
            logger.warning(f"[Authenticator] 事件对象缺少 get_platform_name 方法: {type(event)}")
            return False
            
        platform_name = event.get_platform_name()
        if platform_name != "aiocqhttp":
            logger.debug(f"[Authenticator] 跳过非aiocqhttp平台事件: {platform_name}")
            return False
        return True
    except AttributeError as e:
        logger.error(f"[Authenticator] 检查平台时发生 AttributeError: {e}")
        return False
    except Exception as e:
        logger.error(f"[Authenticator] 检查平台时发生未知错误: {e}")
        return False
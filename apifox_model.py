"""
Apifox API 模型定义模块
"""
from typing import Optional


class ApifoxModel:
    """Apifox API 请求模型"""
    
    def __init__(self, approve: bool, flag: str, reason: Optional[str] = None) -> None:
        """
        初始化Apifox模型
        
        Args:
            approve: 是否同意请求
            flag: 请求标识
            reason: 拒绝理由（可选）
        """
        self.approve = approve
        self.flag = flag
        self.reason = reason
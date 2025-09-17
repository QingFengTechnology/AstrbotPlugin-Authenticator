"""
加群审核模块 (AppReview)
处理群聊加群请求的自动审核功能
"""
import asyncio
from typing import Dict, Any, Optional

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from .apifox_model import ApifoxModel


class AppReview:
    """加群审核处理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化加群审核模块
        
        Args:
            config: 插件配置
        """
        self._load_config(config)
    
    def _load_config(self, config: Dict[str, Any]):
        """加载加群审核相关配置"""
        # 从配置结构中获取配置（直接获取，没有items层）
        automatic_review = config["AutomaticReview"]
        
        # 获取关键词配置
        keywords_config = automatic_review["AutomaticReview_KeywordsConfig"]
        self.accept_keywords = keywords_config["KeywordsConfig_AcceptKeywords"]
        self.reject_keywords = keywords_config["KeywordsConfig_RejectKeywords"]
        self.reject_reason = keywords_config["KeywordsConfig_RejectReason"]
        
        # 获取自动审核配置
        auto_review_config = automatic_review["AutomaticReview_AutoReviewConfig"]
        auto_review_enable = auto_review_config["AutoReviewConfig_Enable"]
        self.auto_accept = auto_review_enable == "True"
        self.auto_reject = auto_review_enable == "False"
        
        # 获取其他配置
        self.delay_seconds = automatic_review["AutomaticReview_DelaySeconds"]
        self.whitelist_groups = config["WhitelistGroups"]
    
    async def approve_request(self, event: AstrMessageEvent, flag: str, 
                             approve: bool = True, reason: str = "") -> bool:
        """
        同意或拒绝加群请求
        
        Args:
            event: 消息事件
            flag: 请求标识
            approve: 是否同意请求
            reason: 拒绝理由
            
        Returns:
            操作是否成功
        """
        try:
            # 检查是否为aiocqhttp平台
            if event.get_platform_name() == "aiocqhttp":
                # 使用NapCat API格式
                from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                assert isinstance(event, AiocqhttpMessageEvent)
                client = event.bot
                
                # 创建ApifoxModel实例
                api_model = ApifoxModel(
                    approve=approve,
                    flag=flag,
                    reason=reason
                )
                
                # 调用NapCat API
                payloads = {
                    "flag": api_model.flag,
                    "sub_type": "add",
                    "approve": api_model.approve,
                    "reason": api_model.reason if api_model.reason else ""
                }
                
                await client.call_action('set_group_add_request', **payloads)
                return True
            # 兼容其他平台的处理方式
            elif event.bot and hasattr(event.bot, "call_action"):
                await event.bot.call_action(
                    "set_group_add_request",
                    flag=flag,
                    sub_type="add",
                    approve=approve,
                    reason=reason
                )
                return True
            return False
        except Exception as e:
            logger.error(f"[Authenticator] 处理群聊申请失败: {e}")
            return False
    
    async def process_group_join_request(self, event: AstrMessageEvent, 
                                        request_data: Dict[str, Any]) -> None:
        """
        处理加群请求
        
        Args:
            event: 消息事件
            request_data: 请求数据
        """
        flag = request_data.get("flag", "")
        user_id = request_data.get("user_id", "")
        comment = request_data.get("comment", "")
        group_id = request_data.get("group_id", "")
        
        # 检查白名单，如果配置了白名单且当前群不在白名单中，则跳过处理
        if self.whitelist_groups and str(group_id) not in self.whitelist_groups:
            logger.debug(f"[Authenticator] 群 {group_id} 不在白名单内，跳过加群请求处理。")
            return
        
        logger.info(f"[Authenticator] 收到加群请求: 用户ID={user_id}, 群ID={group_id}, 验证信息={comment}。")
        
        # 获取延迟时间
        delay_seconds = self.delay_seconds
        
        # 自动处理逻辑
        if self.auto_accept:
            if delay_seconds > 0:
                logger.info(f"[Authenticator] 将在 {delay_seconds} 秒后同意用户 {user_id} 加入群 {group_id} 的请求。")
                await asyncio.sleep(delay_seconds)
            await self.approve_request(event, flag, True)
            logger.info(f"[Authenticator] 已同意用户 {user_id} 加入群 {group_id} 的请求。")
            return
        
        if self.auto_reject:
            if delay_seconds > 0:
                logger.info(f"[Authenticator] 将在 {delay_seconds} 秒后拒绝用户 {user_id} 加入群 {group_id} 的请求。")
                await asyncio.sleep(delay_seconds)
            await self.approve_request(event, flag, False, self.reject_reason)
            logger.info(f"[Authenticator] 已拒绝用户 {user_id} 加入群 {group_id} 的请求。")
            return
        
        # 根据关键词处理，优先检查拒绝关键词
        for keyword in self.reject_keywords:
            if keyword.lower() in comment.lower():
                if delay_seconds > 0:
                    logger.info(f"[Authenticator] 将在 {delay_seconds} 秒后根据关键词 '{keyword}' 拒绝用户 {user_id} 加入群 {group_id} 的请求。")
                    await asyncio.sleep(delay_seconds)
                await self.approve_request(event, flag, False, self.reject_reason)
                logger.info(f"[Authenticator] 已根据关键词 '{keyword}' 拒绝用户 {user_id} 加入群 {group_id} 的请求。")
                return
        
        # 再检查是否包含接受关键词
        for keyword in self.accept_keywords:
            if keyword.lower() in comment.lower():
                if delay_seconds > 0:
                    logger.info(f"[Authenticator] 将在 {delay_seconds} 秒后根据关键词 '{keyword}' 同意用户 {user_id} 加入群 {group_id} 的请求。")
                    await asyncio.sleep(delay_seconds)
                await self.approve_request(event, flag, True)
                logger.info(f"[Authenticator] 已根据关键词 '{keyword}' 同意用户 {user_id} 加入群 {group_id} 的请求。")
                return
        
        # 如果没有匹配到关键词，不做任何处理，等待手动审核
        logger.info(f"[Authenticator] 用户 {user_id} 加入群 {group_id} 的请求未匹配到任意关键词，等待手动审核。")
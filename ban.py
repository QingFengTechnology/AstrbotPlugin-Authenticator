"""
黑名单管理模块 (BanManager)
处理黑名单用户的相关功能
"""
import asyncio
import time
from typing import Dict, Any, Set, List, Optional

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter


class BanManager:
    """黑名单管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化黑名单管理模块
        
        Args:
            config: 插件配置
        """
        self.config = config
        self.banned_users: Set[str] = set()  # 黑名单用户ID集合
        self._load_config()
        
    def _load_config(self):
        """加载黑名单相关配置"""
        # 从配置结构中获取配置（直接获取，没有items层）
        ban_config = self.config["Ban"]
        
        # 获取基础配置
        self.enabled = ban_config["Ban_Enable"]
        
        # 获取黑名单功能设置
        ban_config_settings = ban_config["BanConfig"]
        
        # 忽略用户消息配置
        self.ignore_user_messages = ban_config_settings["BanConfig_IgnoreUser"]
        
        # 拒绝加群配置
        reject_config = ban_config_settings["BanConfig_RejectInvitationConfig"]
        self.reject_invitation_enabled = reject_config["RejectInvitationConfig_Enable"]
        self.reject_reason = reject_config["RejectInvitationConfig_Reason"]
        
        # 自动踢出配置（已弃用，但保留配置加载以避免错误）
        # auto_kick_config = ban_config_settings["BanConfig_AutoKickConfig"]
        # self.auto_kick_unit = auto_kick_config["AutoKickConfig_Unit"]
        # self.auto_kick_time = auto_kick_config["AutoKickConfig_Time"]
        
        # 白名单群组
        self.whitelist_groups = self.config["WhitelistGroups"]
        
        # 加载初始黑名单列表
        initial_ban_list = ban_config_settings.get("BanConfig_List", [])
        if initial_ban_list:
            for user_id in initial_ban_list:
                user_id_str = str(user_id).strip()
                if user_id_str:
                    self.banned_users.add(user_id_str)
            logger.info(f"[Authenticator] 从配置加载了 {len(initial_ban_list)} 个初始黑名单用户")
        
        logger.debug(f"[Authenticator] 黑名单配置加载完成: 启用={self.enabled}, 忽略消息={self.ignore_user_messages}, "
                    f"拒绝加群={self.reject_invitation_enabled}, "
                    f"初始黑名单用户数={len(initial_ban_list)}")
    
    def is_enabled(self) -> bool:
        """检查黑名单功能是否启用"""
        return self.enabled
    
    def add_to_ban_list(self, user_id: str) -> bool:
        """
        添加用户到黑名单
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否成功添加
        """
        if user_id not in self.banned_users:
            self.banned_users.add(user_id)
            logger.info(f"[Authenticator] 用户 {user_id} 已添加到黑名单")
            return True
        return False
    
    def remove_from_ban_list(self, user_id: str) -> bool:
        """
        从黑名单中移除用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否成功移除
        """
        if user_id in self.banned_users:
            self.banned_users.remove(user_id)
            logger.info(f"[Authenticator] 用户 {user_id} 已从黑名单移除")
            return True
        return False
    
    def is_banned(self, user_id: str) -> bool:
        """
        检查用户是否在黑名单中
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否在黑名单中
        """
        return user_id in self.banned_users
    
    async def should_ignore_user_message(self, event: AstrMessageEvent) -> bool:
        """
        检查是否应该忽略用户消息
        
        Args:
            event: 消息事件
            
        Returns:
            是否忽略该消息
        """
        if not self.enabled or not self.ignore_user_messages:
            return False
            
        user_id = str(event.get_sender_id())
        if self.is_banned(user_id):
            logger.info(f"[Authenticator] 忽略黑名单用户 {user_id} 的消息")
            return True
            
        return False
    
    async def process_group_join_request(self, event: AstrMessageEvent, 
                                       request_data: Dict[str, Any]) -> bool:
        """
        处理加群请求 - 检查是否在黑名单中
        
        Args:
            event: 消息事件
            request_data: 请求数据
            
        Returns:
            是否处理了该请求（如果在黑名单中并已拒绝返回True）
        """
        if not self.enabled or not self.reject_invitation_enabled:
            return False
            
        user_id = str(request_data.get("user_id", ""))
        group_id = str(request_data.get("group_id", ""))
        flag = request_data.get("flag", "")
        
        # 检查白名单，如果配置了白名单且当前群不在白名单中，则跳过处理
        if self.whitelist_groups and group_id not in self.whitelist_groups:
            logger.debug(f"[Authenticator] 群 {group_id} 不在白名单内，跳过黑名单检查。")
            return False
        
        if self.is_banned(user_id):
            logger.info(f"[Authenticator] 拒绝黑名单用户 {user_id} 加入群 {group_id} 的请求")
            
            # 调用拒绝加群请求的方法
            success = await self._reject_group_join_request(event, flag, self.reject_reason)
            if success:
                logger.info(f"[Authenticator] 已成功拒绝黑名单用户 {user_id} 的加群请求")
            else:
                logger.error(f"[Authenticator] 拒绝黑名单用户 {user_id} 的加群请求失败")
                
            return True
            
        return False
    
    async def _reject_group_join_request(self, event: AstrMessageEvent, 
                                        flag: str, reason: str) -> bool:
        """
        拒绝加群请求
        
        Args:
            event: 消息事件
            flag: 请求标识
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
                
                # 调用NapCat API
                payloads = {
                    "flag": flag,
                    "sub_type": "add",
                    "approve": False,
                    "reason": reason if reason else ""
                }
                
                await client.call_action('set_group_add_request', **payloads)
                return True
            # 兼容其他平台的处理方式
            elif event.bot and hasattr(event.bot, "call_action"):
                await event.bot.call_action(
                    "set_group_add_request",
                    flag=flag,
                    sub_type="add",
                    approve=False,
                    reason=reason
                )
                return True
            return False
        except Exception as e:
            logger.error(f"[Authenticator] 拒绝群聊申请失败: {e}")
            return False
    

    
    def stop_auto_kick_task(self):
        """停止自动踢出任务（空实现，保持接口兼容性）"""
        pass
    
    def cleanup(self):
        """清理资源"""
        self.stop_auto_kick_task()
        self.banned_users.clear()
        logger.debug("[Authenticator] 黑名单资源已清理")


# 消息过滤器 - 用于忽略黑名单用户的消息
@filter.event_message_type(filter.EventMessageType.ALL)
async def ignore_banned_users(self, event: AstrMessageEvent):
    """
    忽略黑名单用户的消息
    
    这个过滤器应该在其他过滤器之前执行，以确保黑名单用户的消息不会被处理
    """
    if await self.ban_manager.should_ignore_user_message(event):
        # 返回空结果，表示忽略此消息
        return []
    return None
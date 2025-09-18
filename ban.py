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
        self.auto_kick_task: Optional[asyncio.Task] = None
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
        
        # 自动踢出配置
        auto_kick_config = ban_config_settings["BanConfig_AutoKickConfig"]
        self.auto_kick_unit = auto_kick_config["AutoKickConfig_Unit"]
        self.auto_kick_time = auto_kick_config["AutoKickConfig_Time"]
        
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
                    f"拒绝加群={self.reject_invitation_enabled}, 自动踢出间隔={self.auto_kick_time}{self.auto_kick_unit}, "
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
    
    def start_auto_kick_task(self, context):
        """
        启动自动踢出任务
        
        Args:
            context: AstrBot上下文对象
        """
        logger.debug(f"[Authenticator] 开始初始化自动踢出任务，功能启用状态: {self.enabled}, 踢出时间: {self.auto_kick_time}")
        
        if not self.enabled or self.auto_kick_time <= 0:
            logger.debug("[Authenticator] 自动踢出功能未启用或间隔时间为0，不启动自动踢出任务")
            return
            
        # 计算间隔时间（秒）
        interval_seconds = self._get_interval_seconds()
        
        logger.debug(f"[Authenticator] 计算得到的检查间隔秒数: {interval_seconds}")
        
        if interval_seconds <= 0:
            logger.debug("[Authenticator] 自动踢出间隔时间为0，不启动自动踢出任务")
            return
            
        logger.info(f"[Authenticator] 启动自动踢出任务，检查间隔: {interval_seconds}秒")
        
        # 创建异步任务
        self.auto_kick_task = asyncio.create_task(
            self._auto_kick_loop(context, interval_seconds)
        )
        logger.debug("[Authenticator] 自动踢出任务已创建")
    
    def _get_interval_seconds(self) -> int:
        """
        根据配置的单位和时间计算间隔秒数
        
        Returns:
            间隔秒数
        """
        unit_multipliers = {
            "Second": 1,
            "Minute": 60,
            "Hour": 3600,
            "Day": 86400
        }
        
        multiplier = unit_multipliers.get(self.auto_kick_unit, 3600)  # 默认使用小时
        logger.debug(f"[Authenticator] 自动踢出时间单位: {self.auto_kick_unit}, 时间: {self.auto_kick_time}, 倍数: {multiplier}")
        result = self.auto_kick_time * multiplier
        logger.debug(f"[Authenticator] 计算得到的间隔秒数: {result}")
        return result
    
    async def _auto_kick_loop(self, context, interval_seconds: int):
        """
        自动踢出循环任务
        
        Args:
            context: AstrBot上下文对象
            interval_seconds: 检查间隔秒数
        """
        try:
            logger.debug("[Authenticator] 自动踢出循环任务已启动")
            while True:
                logger.debug(f"[Authenticator] 等待 {interval_seconds} 秒后开始下一次检查")
                await asyncio.sleep(interval_seconds)
                logger.debug("[Authenticator] 自动踢出检查周期开始")
                
                if not self.enabled:
                    logger.debug("[Authenticator] 黑名单功能已禁用，跳过本次检查")
                    continue
                    
                if not self.banned_users:
                    logger.debug("[Authenticator] 黑名单用户列表为空，跳过本次检查")
                    continue
                    
                logger.info(f"[Authenticator] 开始自动踢出检查，当前黑名单用户数: {len(self.banned_users)}")
                
                # 获取所有平台实例
                logger.debug("[Authenticator] 开始获取平台实例列表")
                platforms = context.platform_manager.get_insts()
                logger.debug(f"[Authenticator] 获取到 {len(platforms)} 个平台实例")
                
                for i, platform in enumerate(platforms):
                    logger.debug(f"[Authenticator] 开始检查第 {i+1}/{len(platforms)} 个平台: {type(platform).__name__}")
                    await self._check_and_kick_banned_users(platform)
                    logger.debug(f"[Authenticator] 第 {i+1}/{len(platforms)} 个平台检查完成")
                    
        except asyncio.CancelledError:
            logger.info("[Authenticator] 自动踢出任务已被取消")
        except Exception as e:
            logger.error(f"[Authenticator] 自动踢出任务发生错误: {e}")
            import traceback
            logger.error(f"[Authenticator] 错误详情: {traceback.format_exc()}")
    
    async def _check_and_kick_banned_users(self, platform):
        """
        检查并踢出黑名单用户
        
        Args:
            platform: 平台适配器实例
        """
        try:
            logger.debug(f"[Authenticator] 开始检查平台 {type(platform).__name__} 上的黑名单用户")
            
            # 如果有白名单配置，直接使用白名单群组，避免获取所有群组
            if self.whitelist_groups:
                logger.debug(f"[Authenticator] 使用白名单群组列表: {self.whitelist_groups}")
                groups_to_check = self.whitelist_groups
            else:
                # 没有白名单配置时，获取平台上的所有群组
                logger.debug("[Authenticator] 开始获取平台群组列表")
                groups_to_check = await self._get_platform_groups(platform)
                logger.debug(f"[Authenticator] 获取到 {len(groups_to_check)} 个群组: {groups_to_check}")
            
            for group_id in groups_to_check:
                logger.debug(f"[Authenticator] 开始检查群组 {group_id}")
                
                # 获取群成员列表
                logger.debug(f"[Authenticator] 开始获取群组 {group_id} 的成员列表")
                members = await self._get_group_members(platform, group_id)
                logger.debug(f"[Authenticator] 群组 {group_id} 有 {len(members)} 个成员")
                
                # 检查每个成员是否在黑名单中
                logger.debug(f"[Authenticator] 开始检查群组 {group_id} 中的黑名单用户")
                for user_id in members:
                    logger.debug(f"[Authenticator] 检查用户 {user_id} 是否在黑名单中")
                    if self.is_banned(str(user_id)):
                        logger.info(f"[Authenticator] 发现黑名单用户 {user_id} 在群 {group_id} 中，执行踢出操作")
                        await self._kick_member(platform, group_id, user_id, "黑名单成员自动踢出")
                    else:
                        logger.debug(f"[Authenticator] 用户 {user_id} 不在黑名单中")
                logger.debug(f"[Authenticator] 群组 {group_id} 的黑名单用户检查完成")
            logger.debug(f"[Authenticator] 平台 {type(platform).__name__} 上的黑名单用户检查完成")
                        
        except Exception as e:
            logger.error(f"[Authenticator] 检查并踢出黑名单用户时发生错误: {e}")
            import traceback
            logger.error(f"[Authenticator] 错误详情: {traceback.format_exc()}")
    
    async def _get_platform_groups(self, platform) -> List[str]:
        """
        获取平台上的所有群组ID
        
        Args:
            platform: 平台适配器实例
            
        Returns:
            群组ID列表
        """
        try:
            logger.debug(f"[Authenticator] 尝试获取平台 {type(platform).__name__} 的群组列表")
            
            # 首先尝试使用NapCat API格式调用协议端API
            if hasattr(platform, 'get_client') and hasattr(platform.get_client(), 'api'):
                logger.debug("[Authenticator] 平台支持 NapCat API 格式，使用协议端API调用")
                payloads = {}
                logger.debug("[Authenticator] 准备调用 /get_group_list API")
                
                # 调用协议端API
                result = await platform.get_client().api.call_action('get_group_list', **payloads)
                logger.debug(f"[Authenticator] /get_group_list API返回: {result}")
                
                # 解析返回结果 - NapCat API直接返回数据数组，没有'data'字段
                if result and isinstance(result, list):
                    groups = result
                    group_ids = [str(group.get('group_id')) for group in groups if group.get('group_id')]
                    logger.debug(f"[Authenticator] 从API返回中解析出 {len(group_ids)} 个群组ID: {group_ids[:10]}{'...' if len(group_ids) > 10 else ''}")
                    return group_ids
                else:
                    logger.warning(f"[Authenticator] /get_group_list API返回空数据或格式错误: {result}")
                    return []
            
            # 兼容旧版本方式
            if hasattr(platform, 'get_group_list'):
                logger.debug("[Authenticator] 平台支持旧版 get_group_list 方法")
                groups = await platform.get_group_list()
                logger.debug(f"[Authenticator] get_group_list 返回结果: {groups}")
                result = [str(group['group_id']) for group in groups] if groups else []
                logger.debug(f"[Authenticator] 转换后的群组ID列表: {result}")
                return result
            
            logger.debug("[Authenticator] 平台不支持 get_group_list 方法")
            return []
        except Exception as e:
            logger.error(f"[Authenticator] 获取群组列表失败: {e}")
            import traceback
            logger.error(f"[Authenticator] 错误详情: {traceback.format_exc()}")
            return []
    
    async def _get_group_members(self, platform, group_id: str) -> List[str]:
        """
        获取群成员列表
        
        Args:
            platform: 平台适配器实例
            group_id: 群组ID
            
        Returns:
            成员ID列表
        """
        try:
            logger.debug(f"[Authenticator] 尝试获取群组 {group_id} 的成员列表")
            
            # 首先尝试使用NapCat API格式调用协议端API
            if hasattr(platform, 'get_client') and hasattr(platform.get_client(), 'api'):
                logger.debug("[Authenticator] 平台支持 NapCat API 格式，使用协议端API调用")
                payloads = {
                    "group_id": int(group_id),
                    "no_cache": False
                }
                logger.debug(f"[Authenticator] 准备调用 /get_group_member_list API，参数: {payloads}")
                
                # 调用协议端API
                result = await platform.get_client().api.call_action('get_group_member_list', **payloads)
                logger.debug(f"[Authenticator] /get_group_member_list API返回: {result}")
                
                # 解析返回结果 - NapCat API直接返回数据数组，没有'data'字段
                if result and isinstance(result, list):
                    members = result
                    user_ids = [str(member.get('user_id')) for member in members if member.get('user_id')]
                    logger.debug(f"[Authenticator] 从API返回中解析出 {len(user_ids)} 个成员ID: {user_ids[:10]}{'...' if len(user_ids) > 10 else ''}")
                    return user_ids
                else:
                    logger.warning(f"[Authenticator] /get_group_member_list API返回空数据或格式错误: {result}")
                    return []
            
            # 兼容旧版本方式
            if hasattr(platform, 'get_group_member_list'):
                logger.debug("[Authenticator] 平台支持旧版 get_group_member_list 方法")
                members = await platform.get_group_member_list(group_id=int(group_id))
                logger.debug(f"[Authenticator] get_group_member_list 返回结果: {members}")
                result = [str(member['user_id']) for member in members] if members else []
                logger.debug(f"[Authenticator] 转换后的成员ID列表: {result}")
                return result
            
            logger.warning("[Authenticator] 平台不支持获取群成员列表的方法")
            return []
        except Exception as e:
            logger.error(f"[Authenticator] 获取群 {group_id} 成员列表失败: {e}")
            import traceback
            logger.error(f"[Authenticator] 错误详情: {traceback.format_exc()}")
            return []
    
    async def _kick_member(self, platform, group_id: str, user_id: str, reason: str = ""):
        """
        踢出群成员
        
        Args:
            platform: 平台适配器实例
            group_id: 群组ID
            user_id: 用户ID
            reason: 踢出理由
            
        Returns:
            操作是否成功
        """
        try:
            logger.debug(f"[Authenticator] 尝试踢出用户 {user_id} 从群组 {group_id}")
            
            # 使用NapCat API格式调用set_group_kick
            if hasattr(platform, 'get_client') and hasattr(platform.get_client(), 'api'):
                logger.debug("[Authenticator] 平台支持 NapCat API 格式")
                payloads = {
                    "group_id": int(group_id),
                    "user_id": int(user_id),
                    "reject_add_request": False  # 是否同时拒绝加群请求
                }
                logger.debug(f"[Authenticator] 准备调用 API，参数: {payloads}")
                
                # 调用协议端API
                result = await platform.get_client().api.call_action('set_group_kick', **payloads)
                logger.info(f"[Authenticator] 已踢出用户 {user_id} 从群 {group_id}，理由: {reason}, API返回: {result}")
                return True
            
            # 兼容旧版本方式
            if hasattr(platform, 'set_group_kick'):
                logger.debug("[Authenticator] 平台支持旧版 set_group_kick 方法")
                await platform.set_group_kick(
                    group_id=int(group_id),
                    user_id=int(user_id),
                    reject_add_request=False
                )
                logger.info(f"[Authenticator] 已踢出用户 {user_id} 从群 {group_id}，理由: {reason}")
                return True
            
            logger.warning(f"[Authenticator] 平台 {type(platform).__name__} 不支持踢出操作")
            return False
        except Exception as e:
            logger.error(f"[Authenticator] 踢出用户 {user_id} 从群 {group_id} 失败: {e}")
            import traceback
            logger.error(f"[Authenticator] 错误详情: {traceback.format_exc()}")
            return False
    
    def stop_auto_kick_task(self):
        """停止自动踢出任务"""
        if self.auto_kick_task and not self.auto_kick_task.done():
            self.auto_kick_task.cancel()
            logger.info("[Authenticator] 自动踢出任务已停止")
    
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
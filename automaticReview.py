"""
加群审核模块 (AppReview)
处理群聊加群请求的自动审核功能
"""
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from .function.apifox_model import ApifoxModel
from .function.utils import check_platform


class AppReview:
    """加群审核处理器"""
    
    def __init__(self, config: Dict[str, Any], ban_manager: Optional[Any] = None):
        """
        初始化加群审核模块
        
        Args:
            config: 插件配置
            ban_manager: 黑名单管理器实例（可选）
        """
        self.ban_manager = ban_manager
        self._load_config(config)
    
    def _load_config(self, config: Dict[str, Any]):
        """加载加群审核相关配置"""
        # 从配置结构中获取配置（直接获取，没有items层）
        automatic_review = config["AutomaticReview"]
        
        # 获取关键词配置
        keywords_config = automatic_review["AutomaticReview_KeywordsConfig"]
        self.accept_keywords = keywords_config["KeywordsConfig_AcceptKeywords"]
        
        # 获取拒绝配置（新的配置结构）
        reject_config = keywords_config["KeywordsConfig_RejectConfig"]
        self.reject_keywords = reject_config["RejectConfig_RejectKeywords"]
        self.auto_reject = reject_config["RejectConfig_AutoReject"]
        self.reject_reason = reject_config["RejectConfig_RejectReason"]
        
        # 获取等级限制配置
        level_config = automatic_review["AutomaticReview_LevelRestrictionsConfig"]
        self.level_restriction = level_config["LevelRestrictionsConfig_Number"]
        self.reject_invalid_level = level_config["LevelRestrictionsConfig_RejectInvaildLevel"]
        self.level_reject_reason = level_config["LevelRestrictionsConfig_RejectReason"]
        
        # 获取速率限制配置
        rate_limit_config = automatic_review["AutomaticReview_RateLimitConfig"]
        threshold_config = rate_limit_config["RateLimitConfig_ThresholdConfig"]
        limit_config = rate_limit_config["RateLimitConfig_LimitConfig"]
        
        # 阈值配置
        self.rate_limit_frequency = threshold_config["ThresholdConfig_Frequency"]
        self.rate_limit_time = threshold_config["ThresholdConfig_Time"]
        self.rate_limit_unit = threshold_config["RateLimitConfig_Unit"]  # 统计时间单位
        
        # 限制配置
        self.rate_limit_duration = limit_config["RateLimitConfig_Time"]
        self.rate_limit_duration_unit = limit_config["RateLimitConfig_Unit"]  # 限制时长单位
        self.rate_limit_auto_ban = limit_config["RateLimitConfig_AutoBan"]
        
        # 拒绝理由配置
        self.rate_limit_reject_reason = rate_limit_config["RateLimitConfig_RejectReason"]
        
        # 获取其他配置
        self.delay_seconds = automatic_review["AutomaticReview_DelaySeconds"]
        self.whitelist_groups = config["WhitelistGroups"]
        
        # 获取通报配置
        notification_config = automatic_review.get("AutomaticReview_NotificationConfig", {})
        target_config = notification_config.get("NotificationConfig_TargetConfig", {})
        
        # 通报目标配置
        self.notification_targets = target_config.get("TargetConfig_NotificationTarget", [])
        self.notification_target_type = target_config.get("TargetConfig_NotificationTargetType", "Group")
        self.notification_message_template = notification_config.get("NotificationConfig_MessageTemplate", 
                                                                   "已拒绝 {user}({user_id}) 的加群请求，理由: {reason}。")
        
        # 速率限制数据结构
        self.user_request_history: Dict[str, List[float]] = {}  # 用户ID -> 请求时间戳列表
        self.rate_limited_users: Dict[str, float] = {}  # 用户ID -> 限制结束时间戳
    
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
            if not check_platform(event):
                # 兼容其他平台的处理方式
                if event.bot and hasattr(event.bot, "call_action"):
                    await event.bot.call_action(
                        "set_group_add_request",
                        flag=flag,
                        sub_type="add",
                        approve=approve,
                        reason=reason
                    )
                    return True
                return False
            
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
        except Exception as e:
            logger.error(f"[Authenticator] 处理群聊申请失败: {e}")
            return False
    
    async def get_user_level(self, event: AstrMessageEvent, user_id: str) -> int:
        """
        获取用户的QQ等级
        
        Args:
            event: 消息事件
            user_id: 用户ID
            
        Returns:
            用户的QQ等级，如果获取失败返回0
        """
        # 检查是否为aiocqhttp平台
        if not check_platform(event):
            return 0
            
        try:
            # 使用NapCat API格式
            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
            assert isinstance(event, AiocqhttpMessageEvent)
            client = event.bot
            
            logger.debug(f"[Authenticator] 开始获取用户 {user_id} 的QQ等级信息")
            
            # 调用NapCat API获取用户信息 - 使用正确的API调用方式
            payloads = {
                "user_id": int(user_id),
                "no_cache": True
            }
            logger.debug(f"[Authenticator] 调用get_stranger_info API，参数: {payloads}")
            
            user_info = await client.api.call_action('get_stranger_info', **payloads)
            logger.debug(f"[Authenticator] API返回结果: {user_info}")
            
            if user_info:
                # 根据实际API返回结构检查qqLevel字段
                if "qqLevel" in user_info:
                    qq_level = int(user_info["qqLevel"])
                    logger.debug(f"[Authenticator] 成功获取用户 {user_id} 的QQ等级: {qq_level}")
                    return qq_level
                else:
                    logger.debug(f"[Authenticator] 返回数据中缺少qqLevel字段，完整响应: {user_info}")
            else:
                logger.debug(f"[Authenticator] API调用返回None或空结果")
                
        except Exception as e:
            logger.error(f"[Authenticator] 获取用户 {user_id} 的QQ等级失败: {e}")
            logger.debug(f"[Authenticator] 异常详细信息:", exc_info=True)
        
        logger.debug(f"[Authenticator] 最终返回默认等级: 0")
        return 0

    async def send_notification(self, event: AstrMessageEvent, user_id: str, 
                               group_id: str, reason: str) -> None:
        """
        发送拒绝加群通报
        
        Args:
            event: 消息事件
            user_id: 被拒绝的用户ID
            group_id: 群ID
            reason: 拒绝理由
        """
        # 如果没有配置通报目标，直接返回
        if not self.notification_targets:
            return
            
        try:
            # 获取用户昵称
            user_name = await self._get_user_name(event, user_id)
            
            # 格式化当前时间
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 格式化通报消息
            message = self.notification_message_template
            message = message.replace("{group_id}", str(group_id))
            message = message.replace("{user_name}", user_name)
            message = message.replace("{user_id}", str(user_id))
            message = message.replace("{reason}", reason)
            message = message.replace("{time}", current_time)
            
            # 发送通报到所有配置的目标
            for target in self.notification_targets:
                await self._send_to_target(event, target, message)
                
            logger.info(f"[Authenticator] 已向 {len(self.notification_targets)} 个目标发送拒绝加群通报")
            
        except Exception as e:
            logger.error(f"[Authenticator] 发送拒绝加群通报失败: {e}")
    
    async def _get_user_name(self, event: AstrMessageEvent, user_id: str) -> str:
        """
        获取用户昵称
        
        Args:
            event: 消息事件
            user_id: 用户ID
            
        Returns:
            用户昵称，如果获取失败返回用户ID
        """
        # 检查是否为aiocqhttp平台
        if not check_platform(event):
            return str(user_id)
            
        try:
            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
            assert isinstance(event, AiocqhttpMessageEvent)
            client = event.bot
            
            # 调用NapCat API获取用户信息
            payloads = {
                "user_id": int(user_id),
                "no_cache": True
            }
            
            user_info = await client.api.call_action('get_stranger_info', **payloads)
            
            if user_info and "nickname" in user_info:
                return user_info["nickname"]
            else:
                return str(user_id)
                
        except Exception as e:
            logger.warning(f"[Authenticator] 获取用户 {user_id} 昵称失败: {e}")
            return str(user_id)
    
    async def _send_to_target(self, event: AstrMessageEvent, target: str, message: str) -> None:
        """
        向指定目标发送消息
        
        Args:
            event: 消息事件
            target: 目标ID
            message: 消息内容
        """
        try:
            # 检查是否为aiocqhttp平台
            if not check_platform(event):
                logger.warning(f"[Authenticator] 非aiocqhttp平台暂不支持通报功能")
                return
                
            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
            assert isinstance(event, AiocqhttpMessageEvent)
            client = event.bot
            
            if self.notification_target_type == "Group":
                # 发送到群聊
                await client.call_action('send_group_msg', group_id=int(target), message=message)
                logger.debug(f"[Authenticator] 已向群 {target} 发送通报消息")
            else:
                # 发送到私聊
                await client.call_action('send_private_msg', user_id=int(target), message=message)
                logger.debug(f"[Authenticator] 已向用户 {target} 发送通报消息")
                
        except Exception as e:
            logger.error(f"[Authenticator] 向目标 {target} 发送通报消息失败: {e}")

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
        
        # 检查速率限制（如果启用了速率限制）
        is_rate_limited, rate_limit_reason = self._is_user_rate_limited(user_id)
        if is_rate_limited:
            # 记录当前请求（即使被限制也要记录）
            self._record_user_request(user_id)
            
            if delay_seconds > 0:
                logger.info(f"[Authenticator] 将在 {delay_seconds} 秒后根据速率限制拒绝用户 {user_id} 加入群 {group_id} 的请求。")
                await asyncio.sleep(delay_seconds)
            
            # 使用速率限制特定的拒绝理由
            reject_reason = rate_limit_reason if rate_limit_reason else "加群请求过于频繁，请稍后再试"
            await self.approve_request(event, flag, False, reject_reason)
            logger.info(f"[Authenticator] 已根据速率限制拒绝用户 {user_id} 加入群 {group_id} 的请求。")
            
            # 发送通报，使用通用描述性理由
            await self.send_notification(event, user_id, group_id, "达到加群频率限制")
            
            # 如果启用了自动拉黑，将用户添加到黑名单
            if self.rate_limit_auto_ban and self.ban_manager:
                try:
                    # 调用黑名单管理器的添加方法
                    success = self.ban_manager.add_to_ban_list(user_id)
                    if success:
                        logger.info(f"[Authenticator] 用户 {user_id} 触发速率限制，已自动添加到黑名单")
                    else:
                        logger.warning(f"[Authenticator] 用户 {user_id} 触发速率限制，但添加到黑名单失败（可能已在黑名单中）")
                except Exception as e:
                    logger.error(f"[Authenticator] 自动拉黑用户 {user_id} 时发生错误: {e}")
            elif self.rate_limit_auto_ban and not self.ban_manager:
                logger.warning(f"[Authenticator] 用户 {user_id} 触发速率限制，但黑名单管理器不可用，无法自动拉黑")
            
            return
        
        # 记录用户的加群请求
        self._record_user_request(user_id)
        
        # 检查等级限制（如果启用了等级限制）
        if self.level_restriction > 0:
            user_level = await self.get_user_level(event, user_id)
            logger.info(f"[Authenticator] 用户 {user_id} 的QQ等级为: {user_level}, 限制等级为: {self.level_restriction}")
            
            # 如果获取等级失败（返回0）且启用了拒绝无效等级用户
            if user_level == 0 and self.reject_invalid_level:
                if delay_seconds > 0:
                    logger.info(f"[Authenticator] 将在 {delay_seconds} 秒后根据等级限制（获取等级失败）拒绝用户 {user_id} 加入群 {group_id} 的请求。")
                    await asyncio.sleep(delay_seconds)
                await self.approve_request(event, flag, False, self.level_reject_reason)
                logger.info(f"[Authenticator] 已根据等级限制（获取等级失败）拒绝用户 {user_id} 加入群 {group_id} 的请求。")
                # 发送通报，使用通用描述性理由
                await self.send_notification(event, user_id, group_id, "QQ等级获取失败")
                return
            
            # 如果获取等级失败（返回0）且未启用拒绝无效等级用户，则忽略不做处理
            if user_level == 0 and not self.reject_invalid_level:
                logger.info(f"[Authenticator] 用户 {user_id} 的QQ等级获取失败，且未启用拒绝无效等级用户，忽略不做处理。")
                return
            
            # 如果成功获取到等级且等级低于限制
            if user_level > 0 and user_level < self.level_restriction:
                if delay_seconds > 0:
                    logger.info(f"[Authenticator] 将在 {delay_seconds} 秒后根据等级限制拒绝用户 {user_id} 加入群 {group_id} 的请求。")
                    await asyncio.sleep(delay_seconds)
                await self.approve_request(event, flag, False, self.level_reject_reason)
                logger.info(f"[Authenticator] 已根据等级限制拒绝用户 {user_id} 加入群 {group_id} 的请求。")
                # 发送通报，使用通用描述性理由
                await self.send_notification(event, user_id, group_id, "QQ等级不足")
                return
        
        # 根据关键词处理，优先检查拒绝关键词
        for keyword in self.reject_keywords:
            if self._is_valid_keyword_match(comment, keyword):
                if delay_seconds > 0:
                    logger.info(f"[Authenticator] 将在 {delay_seconds} 秒后根据关键词 '{keyword}' 拒绝用户 {user_id} 加入群 {group_id} 的请求。")
                    await asyncio.sleep(delay_seconds)
                await self.approve_request(event, flag, False, self.reject_reason)
                logger.info(f"[Authenticator] 已根据关键词 '{keyword}' 拒绝用户 {user_id} 加入群 {group_id} 的请求。")
                # 发送通报，使用通用描述性理由
                await self.send_notification(event, user_id, group_id, "命中拒绝请求关键词")
                return
        
        # 再检查是否包含接受关键词
        for keyword in self.accept_keywords:
            if self._is_valid_keyword_match(comment, keyword):
                if delay_seconds > 0:
                    logger.info(f"[Authenticator] 将在 {delay_seconds} 秒后根据关键词 '{keyword}' 同意用户 {user_id} 加入群 {group_id} 的请求。")
                    await asyncio.sleep(delay_seconds)
                await self.approve_request(event, flag, True)
                logger.info(f"[Authenticator] 已根据关键词 '{keyword}' 同意用户 {user_id} 加入群 {group_id} 的请求。")
                return
        
        # 如果没有匹配到关键词，根据AutoReject配置决定是否自动拒绝
        if self.auto_reject:
            if delay_seconds > 0:
                logger.info(f"[Authenticator] 将在 {delay_seconds} 秒后根据AutoReject配置拒绝用户 {user_id} 加入群 {group_id} 的请求。")
                await asyncio.sleep(delay_seconds)
            await self.approve_request(event, flag, False, self.reject_reason)
            logger.info(f"[Authenticator] 已根据AutoReject配置拒绝用户 {user_id} 加入群 {group_id} 的请求。")
            # 发送通报，使用通用描述性理由
            await self.send_notification(event, user_id, group_id, "加群答案错误")
        else:
            # 不做任何处理，等待手动审核
            logger.info(f"[Authenticator] 用户 {user_id} 加入群 {group_id} 的请求未匹配到任意关键词，等待手动审核。")
    
    def _convert_time_to_seconds(self, time_value: int, unit: str) -> int:
        """
        将时间值转换为秒数
        
        Args:
            time_value: 时间数值
            unit: 时间单位（Minute/Hour/Day）
            
        Returns:
            对应的秒数
        """
        if unit == "Minute":
            return time_value * 60
        elif unit == "Hour":
            return time_value * 3600
        elif unit == "Day":
            return time_value * 86400
        else:
            return time_value  # 默认按秒处理
    
    def _cleanup_old_requests(self, user_id: str) -> None:
        """
        清理用户的旧请求记录
        
        Args:
            user_id: 用户ID
        """
        if user_id not in self.user_request_history:
            return
            
        current_time = time.time()
        time_window = self._convert_time_to_seconds(self.rate_limit_time, self.rate_limit_unit)
        
        # 只保留在时间窗口内的请求记录
        self.user_request_history[user_id] = [
            timestamp for timestamp in self.user_request_history[user_id]
            if current_time - timestamp <= time_window
        ]
        
        # 如果清理后没有记录，删除用户条目
        if not self.user_request_history[user_id]:
            del self.user_request_history[user_id]
    
    def _is_user_rate_limited(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        检查用户是否被速率限制
        
        Args:
            user_id: 用户ID
            
        Returns:
            (是否被限制, 限制原因)
        """
        # 如果速率限制功能被禁用，直接返回
        if self.rate_limit_frequency <= 0:
            return False, None
        
        current_time = time.time()
        
        # 检查是否在限制期内
        if user_id in self.rate_limited_users:
            if current_time < self.rate_limited_users[user_id]:
                remaining_time = int(self.rate_limited_users[user_id] - current_time)
                # 使用配置的拒绝理由，并替换时间占位符
                reason = self._format_reject_reason(remaining_time, self.rate_limit_duration_unit)
                return True, reason
            else:
                # 限制期已过，清除限制记录
                del self.rate_limited_users[user_id]
        
        # 清理旧请求记录
        self._cleanup_old_requests(user_id)
        
        # 检查当前请求频率
        if user_id in self.user_request_history:
            request_count = len(self.user_request_history[user_id])
            if request_count >= self.rate_limit_frequency:
                # 触发速率限制
                limit_duration = self._convert_time_to_seconds(
                    self.rate_limit_duration, self.rate_limit_duration_unit
                )
                limit_end_time = current_time + limit_duration
                self.rate_limited_users[user_id] = limit_end_time
                
                logger.info(f"[Authenticator] 用户 {user_id} 触发速率限制，限制时长: {limit_duration} 秒")
                # 使用配置的拒绝理由，并替换时间占位符
                reason = self._format_reject_reason(limit_duration, self.rate_limit_duration_unit)
                return True, reason
        
        return False, None
    
    def _format_reject_reason(self, time_in_seconds: int, time_unit: str) -> str:
        """
        格式化拒绝理由，根据配置的时间单位自动转换时间，并替换占位符
        
        Args:
            time_in_seconds: 时间（秒）
            time_unit: 时间单位（Minute/Hour/Day）
            
        Returns:
            格式化后的拒绝理由
        """
        # 根据时间单位转换时间值
        if time_unit == "Minute":
            time_value = max(1, time_in_seconds // 60)  # 转换为分钟，至少1分钟
            unit_display = "分钟"
        elif time_unit == "Hour":
            time_value = max(1, time_in_seconds // 3600)  # 转换为小时，至少1小时
            unit_display = "小时"
        elif time_unit == "Day":
            time_value = max(1, time_in_seconds // 86400)  # 转换为天，至少1天
            unit_display = "天"
        else:
            time_value = time_in_seconds  # 默认按秒处理
            unit_display = "秒"
        
        # 替换占位符
        reason = self.rate_limit_reject_reason
        reason = reason.replace("{time}", str(time_value))
        reason = reason.replace("{unit}", unit_display)
        
        return reason
    
    def _record_user_request(self, user_id: str) -> None:
        """
        记录用户的加群请求
        
        Args:
            user_id: 用户ID
        """
        if self.rate_limit_frequency <= 0:
            return
            
        current_time = time.time()
        
        if user_id not in self.user_request_history:
            self.user_request_history[user_id] = []
        
        self.user_request_history[user_id].append(current_time)
    
    def _is_valid_keyword_match(self, comment: str, keyword: str) -> bool:
        """
        判断关键词是否匹配
        
        Args:
            comment: 用户输入的验证信息
            keyword: 要匹配的关键词
            
        Returns:
            是否匹配
        """
        return keyword.lower() in comment.lower()
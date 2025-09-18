from typing import Dict, Any

from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star

from .automaticReview import AppReview
from .simpleReCAPTCHA import ReCAPTCHA
from .ban import BanManager

def require_aiocqhttp_platform(func):
    """检查平台是否为 aiocqhttp"""
    async def wrapper(self, event: AstrMessageEvent, *args, **kwargs):
        # 检查平台是否为 aiocqhttp
        if event.get_platform_name() != "aiocqhttp":
            logger.debug(f"[Authenticator] 检测到非 aiocqhttp 平台({event.get_platform_name()})，跳过执行。")
            return
        # 如果是 aiocqhttp 平台，则执行原函数
        return await func(self, event, *args, **kwargs)
    return wrapper

# 主类定义
class AuthenticatorPlugin(Star):
    def __init__(self, context: Context, config: Dict[str, Any]):
        super().__init__(context)
        self.context = context
        
        # 初始化模块 - 传递完整的配置对象
        self.recaptcha = ReCAPTCHA(config)
        self.appreview = AppReview(config)
        self.ban_manager = BanManager(config)
        
        self._apply_monkey_patch()
        
        # 启动黑名单自动踢出任务（已弃用）
        # self.ban_manager.start_auto_kick_task(context)
        
        logger.debug("[Authenticator] 插件初始化完成。")
    
    def _apply_monkey_patch(self):
        """应用monkey patch确保session_id属性存在"""
        try:
            from astrbot.core.platform.astrbot_message import AstrBotMessage
            original_init = AstrBotMessage.__init__
            
            def patched_init(self, *args, **kwargs):
                original_init(self, *args, **kwargs)
                if not hasattr(self, "session_id") or not self.session_id:
                    self.session_id = "unknown_session"
            AstrBotMessage.__init__ = patched_init
            logger.debug("已应用AstrBotMessage的monkey patch。")
        except Exception as e:
            logger.warning(f"应用monkey patch失败: {e}")

    @require_aiocqhttp_platform
    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handle_event(self, event: AstrMessageEvent):
        """处理所有事件"""
        raw = event.message_obj.raw_message
        post_type = raw.get("post_type")

        # 处理群聊申请事件（加群请求需要特殊处理，不能忽略）
        if post_type == "request" and raw.get("request_type") == "group" and raw.get("sub_type") == "add":
            # 先检查黑名单
            if await self.ban_manager.process_group_join_request(event, raw):
                return  # 如果在黑名单中并已处理，直接返回
            
            await self.appreview.process_group_join_request(event, raw)
            return

        # 对于其他类型的事件，检查是否应该忽略黑名单用户的消息
        if await self.ban_manager.should_ignore_user_message(event):
            return
        
        # 处理群消息和通知事件
        if post_type == "notice":
            if raw.get("notice_type") == "group_increase":
                await self.recaptcha.process_new_member(event)
            elif raw.get("notice_type") == "group_decrease":
                await self.recaptcha.process_member_decrease(event)
        
        elif post_type == "message" and raw.get("message_type") == "group":
            await self.recaptcha.process_verification_message(event)

    async def terminate(self):
        """插件被卸载/停用时调用"""
        # 清理所有待处理的验证任务
        self.recaptcha.cleanup()
        
        # 停止黑名单自动踢出任务
        self.ban_manager.cleanup()
        
        logger.debug("[Authenticator] 插件已停止。")
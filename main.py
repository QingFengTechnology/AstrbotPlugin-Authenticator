from typing import Dict, Any

from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star

from .appreview import AppReview
from .recaptcha import ReCAPTCHA

# 主类定义
class AuthenticatorPlugin(Star):
    def __init__(self, context: Context, config: Dict[str, Any]):
        super().__init__(context)
        self.context = context
        
        # 初始化模块 - 传递完整的配置对象
        self.recaptcha = ReCAPTCHA(config)
        self.appreview = AppReview(config)
        
        self._apply_monkey_patch()
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

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handle_event(self, event: AstrMessageEvent):
        """处理所有事件"""
        raw = event.message_obj.raw_message
        post_type = raw.get("post_type")

        # 处理群聊申请事件
        if post_type == "request" and raw.get("request_type") == "group" and raw.get("sub_type") == "add":
            await self.appreview.process_group_join_request(event, raw)
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
        logger.debug("[Authenticator] 插件已停止。")
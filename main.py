import asyncio
import random
import re
from typing import Dict, Any, Tuple, Optional

from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star

def _safe_format(template: str, **kwargs: Any) -> str:
    """
    使用 .format_map() 安全地格式化字符串。
    模板中不存在的键将被忽略，而不是引发 KeyError。
    """
    class SafeDict(dict):
        def __missing__(self, key):
            return f'{{{key}}}'
    return template.format_map(SafeDict(kwargs))

class ApifoxModel:
    def __init__(self, approve: bool, flag: str, reason: Optional[str] = None) -> None:
        self.approve = approve
        self.flag = flag
        self.reason = reason

class AuthenticatorPlugin(Star):
    def __init__(self, context: Context, config: Dict[str, Any]):
        super().__init__(context)
        self.context = context
        
        self._load_recaptcha_config(config)
        self._load_appreview_config(config)

        self.pending: Dict[str, Dict[str, Any]] = {}
        
        self._apply_monkey_patch()
    
    def _load_recaptcha_config(self, config: Dict[str, Any]):
        """加载ReCAPTCHA相关配置"""

        self.verification_timeout = config.get("verification_timeout")
        self.kick_countdown_warning_time = config.get("kick_countdown_warning_time")
        self.kick_delay = config.get("kick_delay")
        self.new_member_prompt = config.get("new_member_prompt")
        self.welcome_message = config.get("welcome_message")
        self.wrong_answer_prompt = config.get("wrong_answer_prompt")
        self.countdown_warning_prompt = config.get("countdown_warning_prompt")
        self.failure_message = config.get("failure_message")
        self.kick_message = config.get("kick_message")
        self.disable_failure_message = config.get("disable_failure_message")
        self.disable_kick_message = config.get("disable_kick_message")
        self.whitelist_groups = config.get("whitelist_groups")
    
    def _load_appreview_config(self, config: Dict[str, Any]):
        """加载AppReview相关配置"""
        self.accept_keywords = config.get("accept_keywords")
        self.reject_keywords = config.get("reject_keywords")
        self.auto_accept = config.get("auto_accept")
        self.auto_reject = config.get("auto_reject")
        self.reject_reason = config.get("reject_reason")
        self.delay_seconds = config.get("delay_seconds")
    
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

    def _generate_math_problem(self) -> Tuple[str, int]:
        """生成一个100以内的加减法问题"""
        op_type = random.choice(['add', 'sub'])
        if op_type == 'add':
            num1 = random.randint(0, 100)
            num2 = random.randint(0, 100 - num1)
            answer = num1 + num2
            question = f"{num1} + {num2} = ?"
            return question, answer
        else:
            num1 = random.randint(1, 100)
            num2 = random.randint(0, num1)
            answer = num1 - num2
            question = f"{num1} - {num2} = ?"
            return question, answer

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handle_event(self, event: AstrMessageEvent):
        """处理所有事件"""
        raw = event.message_obj.raw_message
        post_type = raw.get("post_type")

        # 处理群聊申请事件
        if post_type == "request" and raw.get("request_type") == "group" and raw.get("sub_type") == "add":
            await self._process_group_join_request(event, raw)
            return
        
        # 处理群消息和通知事件
        if post_type == "notice":
            if raw.get("notice_type") == "group_increase":
                await self._process_new_member(event)
            elif raw.get("notice_type") == "group_decrease":
                await self._process_member_decrease(event)
        
        elif post_type == "message" and raw.get("message_type") == "group":
            await self._process_verification_message(event)

    async def _process_new_member(self, event: AstrMessageEvent):
        """处理新成员入群"""
        raw = event.message_obj.raw_message
        uid = str(raw.get("user_id"))
        gid = raw.get("group_id")
        if self.whitelist_groups and str(gid) not in self.whitelist_groups:
            logger.debug(f"[Authenticator] 群 {gid} 不在白名单内，跳过验证。")
            return
        
        await self._start_verification_process(event, uid, gid, is_new_member=True)

    async def _start_verification_process(self, event: AstrMessageEvent, uid: str, gid: int, is_new_member: bool):
        """启动或重启验证流程"""
        if uid in self.pending:
            old_task = self.pending[uid].get("task")
            if old_task and not old_task.done():
                old_task.cancel()

        question, answer = self._generate_math_problem()
        logger.info(f"[Authenticator] 为用户 {uid} 在群 {gid} 生成验证问题: {question} (答案: {answer})")

        nickname = uid
        try:
            user_info = await event.bot.api.call_action("get_group_member_info", group_id=gid, user_id=int(uid))
            nickname = user_info.get("card", "") or user_info.get("nickname", uid)
        except Exception as e:
            logger.warning(f"[Authenticator] 获取用户 {uid} 昵称失败: {e}")

        task = asyncio.create_task(self._timeout_kick(event.bot, uid, gid, nickname))
        self.pending[uid] = {"gid": gid, "answer": answer, "task": task}

        at_user = f"[CQ:at,qq={uid}]"
        
        format_args = {
            "at_user": at_user,
            "member_name": nickname,
            "question": question,
            "timeout": self.verification_timeout // 60,
            "countdown": self.kick_delay
        }
        
        if is_new_member:
            prompt_message = _safe_format(self.new_member_prompt, **format_args)
        else:
            prompt_message = _safe_format(self.wrong_answer_prompt, **format_args)

        await event.bot.api.call_action("send_group_msg", group_id=gid, message=prompt_message)

    async def _process_verification_message(self, event: AstrMessageEvent):
        """处理群消息以进行验证"""
        uid = str(event.get_sender_id())
        if uid not in self.pending:
            return
        
        raw = event.message_obj.raw_message
        gid = self.pending[uid]["gid"]

        bot_id = str(event.get_self_id())
        message_segs = raw.get("message", [])
        if not isinstance(message_segs, list):
            return

        at_me = any(seg.get("type") == "at" and str(seg.get("data", {}).get("qq")) == bot_id for seg in message_segs)

        if not at_me:
            return
        
        text_without_at = re.sub(r'\[CQ:at,qq=\d+\]', '', event.message_str).strip()
        numbers_found = re.findall(r'\d+', text_without_at)
        
        if not numbers_found:
            return

        try:
            user_answer = int(numbers_found[-1])
        except (ValueError, TypeError):
            return

        correct_answer = self.pending[uid].get("answer")

        if user_answer == correct_answer:
            logger.info(f"[Authenticator] 用户 {uid} 在群 {gid} 验证成功。")
            self.pending[uid]["task"].cancel()
            self.pending.pop(uid, None)

            nickname = raw.get("sender", {}).get("card", "") or raw.get("sender", {}).get("nickname", uid)
            
            welcome_msg = _safe_format(
                self.welcome_message, 
                at_user=f"[CQ:at,qq={uid}]", 
                member_name=nickname
            )
            await event.bot.api.call_action("send_group_msg", group_id=gid, message=welcome_msg)
            event.stop_event()
        else:
            logger.info(f"[Authenticator] 用户 {uid} 在群 {gid} 回答错误。重新生成问题。")
            await self._start_verification_process(event, uid, gid, is_new_member=False)
            event.stop_event()

    async def _process_member_decrease(self, event: AstrMessageEvent):
        """处理成员离开"""
        uid = str(event.message_obj.raw_message.get("user_id"))
        if uid in self.pending:
            self.pending[uid]["task"].cancel()
            self.pending.pop(uid, None)
            logger.debug(f"[Authenticator] 待验证用户 {uid} 已离开，清理其验证状态。")

    async def _timeout_kick(self, bot, uid: str, gid: int, nickname: str):
        """处理超时、警告和踢出的协程"""
        try:
            wait_time = self.verification_timeout - self.kick_countdown_warning_time
            if self.kick_countdown_warning_time > 0 and wait_time > 0:
                await asyncio.sleep(wait_time)
                if uid not in self.pending: return
                
                at_user = f"[CQ:at,qq={uid}]"
                warning_msg = _safe_format(
                    self.countdown_warning_prompt, 
                    at_user=at_user, 
                    member_name=nickname
                )
                try:
                    await bot.api.call_action("send_group_msg", group_id=gid, message=warning_msg)
                except Exception as e:
                    logger.warning(f"[Authenticator] 发送超时警告失败: {e}")
                
                await asyncio.sleep(self.kick_countdown_warning_time)
            else:
                await asyncio.sleep(self.verification_timeout)

            if uid not in self.pending: return

            # 发送验证超时提示语（如果未禁用）
            if not self.disable_failure_message:
                at_user = f"[CQ:at,qq={uid}]"
                failure_msg = _safe_format(
                    self.failure_message, 
                    at_user=at_user, 
                    member_name=nickname, 
                    countdown=self.kick_delay
                )
                await bot.api.call_action("send_group_msg", group_id=gid, message=failure_msg)
            
            await asyncio.sleep(self.kick_delay)

            if uid not in self.pending: return
            
            await bot.api.call_action("set_group_kick", group_id=gid, user_id=int(uid), reject_add_request=False)
            logger.info(f"[Authenticator] 用户 {uid} ({nickname}) 验证超时，已从群 {gid} 踢出。")
            
            # 发送最终踢出提示语（如果未禁用）
            if not self.disable_kick_message:
                at_user = f"[CQ:at,qq={uid}]"
                kick_msg = _safe_format(
                    self.kick_message, 
                    at_user=at_user, 
                    member_name=nickname
                )
                await bot.api.call_action("send_group_msg", group_id=gid, message=kick_msg)

        except asyncio.CancelledError:
            logger.info(f"[Authenticator] 踢出任务已取消 (用户 {uid})。")
        except Exception as e:
            logger.error(f"[Authenticator] 踢出流程发生错误 (用户 {uid}): {e}")
        finally:
            self.pending.pop(uid, None)

    async def _process_group_join_request(self, event: AstrMessageEvent, request_data):
        """处理加群请求"""
        flag = request_data.get("flag", "")
        user_id = request_data.get("user_id", "")
        comment = request_data.get("comment", "")
        group_id = request_data.get("group_id", "")
        
        logger.info(f"[Authenticator] 收到加群请求: 用户ID={user_id}, 群ID={group_id}, 验证信息={comment}")
        
        # 获取延迟时间
        delay_seconds = self.delay_seconds
        
        # 自动处理逻辑
        if self.auto_accept:
            if delay_seconds > 0:
                logger.info(f"[Authenticator] 将在 {delay_seconds} 秒后自动同意用户 {user_id} 加入群 {group_id} 的请求")
                await asyncio.sleep(delay_seconds)
            await self._approve_request(event, flag, True)
            logger.info(f"[Authenticator] 自动同意用户 {user_id} 加入群 {group_id} 的请求")
            return
        
        if self.auto_reject:
            if delay_seconds > 0:
                logger.info(f"[Authenticator] 将在 {delay_seconds} 秒后自动拒绝用户 {user_id} 加入群 {group_id} 的请求")
                await asyncio.sleep(delay_seconds)
            await self._approve_request(event, flag, False, self.reject_reason)
            logger.info(f"[Authenticator] 自动拒绝用户 {user_id} 加入群 {group_id} 的请求")
            return
        
        # 根据关键词处理，优先检查拒绝关键词
        for keyword in self.reject_keywords:
            if keyword.lower() in comment.lower():
                if delay_seconds > 0:
                    logger.info(f"[Authenticator] 将在 {delay_seconds} 秒后根据关键词 '{keyword}' 拒绝用户 {user_id} 加入群 {group_id} 的请求")
                    await asyncio.sleep(delay_seconds)
                await self._approve_request(event, flag, False, self.reject_reason)
                logger.info(f"[Authenticator] 根据关键词 '{keyword}' 拒绝用户 {user_id} 加入群 {group_id} 的请求")
                return
        
        # 再检查是否包含接受关键词
        for keyword in self.accept_keywords:
            if keyword.lower() in comment.lower():
                if delay_seconds > 0:
                    logger.info(f"[Authenticator] 将在 {delay_seconds} 秒后根据关键词 '{keyword}' 同意用户 {user_id} 加入群 {group_id} 的请求")
                    await asyncio.sleep(delay_seconds)
                await self._approve_request(event, flag, True)
                logger.info(f"[Authenticator] 根据关键词 '{keyword}' 同意用户 {user_id} 加入群 {group_id} 的请求")
                return
        
        # 如果没有匹配到关键词，不做任何处理，等待手动审核
        logger.info(f"[Authenticator] 用户 {user_id} 加入群 {group_id} 的请求未匹配到关键词，等待手动审核")
        return

    async def _approve_request(self, event: AstrMessageEvent, flag, approve=True, reason=""):
        """同意或拒绝请求"""
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

    async def terminate(self):
        """插件被卸载/停用时调用"""
        logger.info("Authenticator插件已停用")
        # 取消所有待处理的验证任务
        for uid, data in self.pending.items():
            task = data.get("task")
            if task and not task.done():
                task.cancel()
        self.pending.clear()
"""
验证码验证模块 (ReCAPTCHA)
处理新成员入群验证功能
"""
import asyncio
import random
import re
from typing import Dict, Any, Tuple, Optional

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from .function.utils import safe_format, check_platform


class ReCAPTCHA:
    """验证码验证处理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化验证码验证模块
        
        Args:
            config: 插件配置
        """
        self._load_config(config)
        self.pending: Dict[str, Dict[str, Any]] = {}
    
    def _load_config(self, config: Dict[str, Any]):
        """加载验证码验证相关配置"""
        # 从配置结构中获取配置（直接获取，没有items层）
        recaptcha_config = config["SimpleReCAPTCHA"]
        
        # 获取基础配置
        time_config = recaptcha_config["SimpleReCAPTCHA_TimeConfig"]
        self.verification_timeout = time_config["TimeConfig_VerificationTimeout"]
        self.kick_delay = time_config["TimeConfig_KickDelay"]
        
        # 获取难度配置
        difficulty_config = recaptcha_config["SimpleReCAPTCHA_DifficultyConfig"]
        self.min_number = difficulty_config["DifficultyConfig_MinNumber"]
        self.max_number = difficulty_config["DifficultyConfig_MaxNumber"]
        self.min_difference = difficulty_config["DifficultyConfig_MinimumDifference"]
        self.disable_integer = difficulty_config["DifficultyConfig_DisableInteger"]
        
        # 获取消息配置
        message_config = recaptcha_config["SimpleReCAPTCHA_MessageConfig"]
        self.new_member_prompt = message_config["MessageConfig_Join"]
        self.welcome_message = message_config["MessageConfig_Success"]
        self.wrong_answer_prompt = message_config["MessageConfig_Wrong"]
        
        # 获取倒计时警告配置
        countdown_config = message_config["MessageConfig_CountdownWarningConfig"]
        self.kick_countdown_warning_time = countdown_config["CountdownWarningConfig_Time"]
        self.countdown_warning_prompt = countdown_config["CountdownWarningConfig_Message"]
        
        # 获取失败配置
        failure_config = message_config["MessageConfig_FailureConfig"]
        self.disable_failure_message = not failure_config["FailureConfig_Enable"]
        self.failure_message = failure_config["FailureConfig_Message"]
        
        # 获取踢出配置
        kick_config = message_config["MessageConfig_KickConfig"]
        self.disable_kick_message = not kick_config["KickConfig_Enable"]
        self.kick_message = kick_config["KickConfig_Message"]
        
        self.whitelist_groups = config["WhitelistGroups"]

    def generate_math_problem(self) -> Tuple[str, int]:
        """
        生成一个基于配置的加减法问题
        
        Returns:
            Tuple[问题描述, 正确答案]
        """
        op_type = random.choice(['add', 'sub'])
        
        if op_type == 'add':
            # 生成加法题目
            num1 = self._generate_valid_number()
            max_num2 = min(self.max_number - num1, self.max_number)
            
            # 确保num2满足最小差值要求
            min_num2 = max(self.min_number, self.min_difference - num1) if self.min_difference > 0 else self.min_number
            
            if min_num2 > max_num2:
                # 如果无法满足最小差值要求，重新生成num1
                return self.generate_math_problem()
                
            num2 = random.randint(min_num2, max_num2)
            answer = num1 + num2
            question = f"{num1} + {num2} = ?"
            return question, answer
        else:
            # 生成减法题目
            # 确保num1大于等于num2，且差值满足最小差值要求
            min_num1 = max(self.min_number + 1, self.min_difference) if self.min_difference > 0 else self.min_number + 1
            
            if min_num1 > self.max_number:
                # 如果无法满足最小差值要求，重新生成
                return self.generate_math_problem()
                
            num1 = random.randint(min_num1, self.max_number)
            
            # num2的范围：从min_number到num1-1，但要确保差值满足最小差值要求
            max_num2 = num1 - 1
            min_num2 = max(self.min_number, num1 - self.max_number)
            
            # 如果设置了最小差值，确保num1 - num2 >= min_difference
            if self.min_difference > 0:
                min_num2 = max(min_num2, num1 - self.max_number, num1 - self.min_difference)
                
            if min_num2 > max_num2:
                # 如果无法满足要求，重新生成
                return self.generate_math_problem()
                
            num2 = random.randint(min_num2, max_num2)
            answer = num1 - num2
            question = f"{num1} - {num2} = ?"
            return question, answer
    
    async def timeout_kick(self, bot, uid: str, gid: int, nickname: str):
        """
        处理超时、警告和踢出的协程
        
        Args:
            bot: 机器人实例
            uid: 用户ID
            gid: 群ID
            nickname: 用户昵称
        """
        try:
            wait_time = self.verification_timeout - self.kick_countdown_warning_time
            if self.kick_countdown_warning_time > 0 and wait_time > 0:
                await asyncio.sleep(wait_time)
                if uid not in self.pending: return
                
                at_user = f"[CQ:at,qq={uid}]"
                warning_msg = safe_format(
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
                failure_msg = safe_format(
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
                kick_msg = safe_format(
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
    
    async def process_new_member(self, event: AstrMessageEvent):
        """
        处理新成员入群
        
        Args:
            event: 消息事件
        """
        # 平台检查：如果不是aiocqhttp平台，直接返回
        if not check_platform(event):
            return
            
        raw = event.message_obj.raw_message
        uid = str(raw.get("user_id"))
        gid = raw.get("group_id")
        if self.whitelist_groups and str(gid) not in self.whitelist_groups:
            logger.debug(f"[Authenticator] 群 {gid} 不在白名单内，跳过验证。")
            return
        
        await self.start_verification_process(event, uid, gid, is_new_member=True)
    
    async def start_verification_process(self, event: AstrMessageEvent, uid: str, 
                                       gid: int, is_new_member: bool):
        """
        启动或重启验证流程
        
        Args:
            event: 消息事件
            uid: 用户ID
            gid: 群ID
            is_new_member: 是否是新成员
        """
        # 平台检查：如果不是aiocqhttp平台，直接返回
        if not check_platform(event):
            return
            
        if uid in self.pending:
            old_task = self.pending[uid].get("task")
            if old_task and not old_task.done():
                old_task.cancel()

        question, answer = self.generate_math_problem()
        logger.info(f"[Authenticator] 为用户 {uid} 在群 {gid} 生成验证问题: {question} (答案: {answer})。")

        nickname = uid
        try:
            user_info = await event.bot.api.call_action("get_group_member_info", group_id=gid, user_id=int(uid))
            nickname = user_info.get("card", "") or user_info.get("nickname", uid)
        except Exception as e:
            logger.warning(f"[Authenticator] 获取用户 {uid} 昵称失败: {e}")

        task = asyncio.create_task(self.timeout_kick(event.bot, uid, gid, nickname))
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
            prompt_message = safe_format(self.new_member_prompt, **format_args)
        else:
            prompt_message = safe_format(self.wrong_answer_prompt, **format_args)

        await event.bot.api.call_action("send_group_msg", group_id=gid, message=prompt_message)
    
    async def process_verification_message(self, event: AstrMessageEvent):
        """
        处理群消息以进行验证
        
        Args:
            event: 消息事件
        """
        # 平台检查：如果不是aiocqhttp平台，直接返回
        if not check_platform(event):
            return
            
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
            
            welcome_msg = safe_format(
                self.welcome_message, 
                at_user=f"[CQ:at,qq={uid}]", 
                member_name=nickname
            )
            await event.bot.api.call_action("send_group_msg", group_id=gid, message=welcome_msg)
            event.stop_event()
        else:
            logger.info(f"[Authenticator] 用户 {uid} 在群 {gid} 回答错误。重新生成问题。")
            await self.start_verification_process(event, uid, gid, is_new_member=False)
            event.stop_event()
    
    async def process_member_decrease(self, event: AstrMessageEvent):
        """
        处理成员离开
        
        Args:
            event: 消息事件
        """
        # 平台检查：如果不是aiocqhttp平台，直接返回
        if not check_platform(event):
            return
            
        uid = str(event.message_obj.raw_message.get("user_id"))
        if uid in self.pending:
            self.pending[uid]["task"].cancel()
            self.pending.pop(uid, None)
            logger.info(f"[Authenticator] 待验证用户 {uid} 已离开，清理其验证状态。")
    
    def cleanup(self):
        """清理所有待处理的验证任务"""
        for uid, data in self.pending.items():
            task = data.get("task")
            if task and not task.done():
                task.cancel()
        self.pending.clear()

    def _generate_valid_number(self) -> int:
        """
        生成一个有效的数字，根据DisableInteger配置决定是否排除整十整百的数字
        
        Returns:
            生成的数字
        """
        while True:
            num = random.randint(self.min_number, self.max_number)
            
            # 如果不需要禁用整数，直接返回
            if not self.disable_integer:
                return num
            
            # 检查是否为整十整百的数字（末尾为0）
            if num % 10 != 0:
                return num
            
            # 如果是整十整百的数字，继续循环生成新的数字
"""
加群审核模块 (AppReview)
处理群聊加群请求的自动审核功能
"""
import asyncio
from typing import Dict, Any, Optional

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from .function.apifox_model import ApifoxModel


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
        
        # 获取拒绝配置（新的配置结构）
        reject_config = keywords_config["KeywordsConfig_RejectConfig"]
        self.reject_keywords = reject_config["RejectConfig_RejectKeywords"]
        self.auto_reject = reject_config["RejectConfig_AutoReject"]
        self.reject_reason = reject_config["RejectConfig_RejectReason"]
        
        # 获取等级限制配置
        level_config = automatic_review["AutomaticReview_LevelRestrictionsConfig"]
        self.level_restriction = level_config["LevelRestrictionsConfig_Number"]
        self.level_reject_reason = level_config["LevelRestrictionsConfig_RejectReason"]
        
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
        if event.get_platform_name() != "aiocqhttp":
            logger.debug(f"[Authenticator] 插件仅支持 aiocqhttp 平台获取用户等级，当前平台: {event.get_platform_name()}，返回默认等级。")
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
        
        # 检查等级限制（如果启用了等级限制）
        if self.level_restriction > 0:
            user_level = await self.get_user_level(event, user_id)
            logger.info(f"[Authenticator] 用户 {user_id} 的QQ等级为: {user_level}, 限制等级为: {self.level_restriction}")
            
            if user_level < self.level_restriction:
                if delay_seconds > 0:
                    logger.info(f"[Authenticator] 将在 {delay_seconds} 秒后根据等级限制拒绝用户 {user_id} 加入群 {group_id} 的请求。")
                    await asyncio.sleep(delay_seconds)
                await self.approve_request(event, flag, False, self.level_reject_reason)
                logger.info(f"[Authenticator] 已根据等级限制拒绝用户 {user_id} 加入群 {group_id} 的请求。")
                return
        
        # 根据关键词处理，优先检查拒绝关键词
        for keyword in self.reject_keywords:
            if self._is_valid_keyword_match(comment, keyword):
                if delay_seconds > 0:
                    logger.info(f"[Authenticator] 将在 {delay_seconds} 秒后根据关键词 '{keyword}' 拒绝用户 {user_id} 加入群 {group_id} 的请求。")
                    await asyncio.sleep(delay_seconds)
                await self.approve_request(event, flag, False, self.reject_reason)
                logger.info(f"[Authenticator] 已根据关键词 '{keyword}' 拒绝用户 {user_id} 加入群 {group_id} 的请求。")
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
        else:
            # 不做任何处理，等待手动审核
            logger.info(f"[Authenticator] 用户 {user_id} 加入群 {group_id} 的请求未匹配到任意关键词，等待手动审核。")
    
    def _is_valid_keyword_match(self, comment: str, keyword: str) -> bool:
        """
        智能判断关键词是否有效匹配
        
        避免数学方程中的数字被误判为答案
        
        Args:
            comment: 用户输入的验证信息
            keyword: 要匹配的关键词
            
        Returns:
            是否有效匹配
        """
        comment_lower = comment.lower()
        keyword_lower = keyword.lower()
        
        # 如果关键词是数字，需要更严格的匹配
        if keyword_lower.isdigit() or (keyword_lower.startswith('-') and keyword_lower[1:].isdigit()):
            # 检查是否是数学方程中的数字（在方程中出现）
            if self._is_number_in_equation(comment_lower, keyword_lower):
                return False
            
            # 检查是否是答案格式（如"x=2", "答案：2", "答案是2"等）
            if self._is_answer_format(comment_lower, keyword_lower):
                return True
                
            # 对于数字关键词，如果不是在答案格式中，不匹配
            return False
        
        # 对于非数字关键词，使用简单的包含匹配
        return keyword_lower in comment_lower
    
    def _is_number_in_equation(self, comment: str, number: str) -> bool:
        """检查数字是否出现在数学方程中"""
        # 检查评论是否包含方程关键词
        equation_keywords = ['方程', '解', '=', '+', '-', '*', '/', '^', 'x', 'y', 'z']
        
        has_equation_keyword = any(keyword in comment for keyword in equation_keywords)
        if not has_equation_keyword:
            return False
            
        # 找到数字的位置
        number_pos = comment.find(number)
        if number_pos == -1:
            return False
            
        # 如果数字作为答案出现，就不认为是方程中的数字
        # 先检查是否是答案格式
        if self._is_answer_format(comment, number):
            return False
            
        # 简单方法：如果评论包含明确的答案部分，且数字在答案部分，就不认为是方程中的数字
        answer_keywords = ['答案', '答', '结果为', '结果是', 'x=', 'y=', 'z=']
        
        for keyword in answer_keywords:
            keyword_pos = comment.find(keyword)
            if keyword_pos != -1 and number_pos > keyword_pos:
                # 数字在答案关键词之后，不认为是方程中的数字
                return False
        
        # 如果包含方程关键词且数字不在明确的答案部分，则认为数字在方程中
        return True
    
    def _is_answer_format(self, comment: str, number: str) -> bool:
        """
        判断数字是否以答案格式出现
        """
        # 答案格式模式（更宽松的匹配）
        answer_patterns = [
            f'答案{number}',
            f'答案是{number}',
            f'答案为{number}',
            f'x={number}',
            f'y={number}', 
            f'z={number}',
            f'={number}',
            f'答：{number}',
            f'答 {number}',
            f'结果{number}',
            f'结果是{number}',
            f'答案：{number}',
            f'答案 {number}',
            f'结果为{number}',
            f'结果：{number}'
        ]
        
        # 检查是否匹配任何答案格式
        for pattern in answer_patterns:
            if pattern in comment:
                return True
        
        # 特殊处理：如果评论以数字结尾，且前面有答案关键词
        answer_keywords = ['答案', '答', '结果', 'x', 'y', 'z']
        for keyword in answer_keywords:
            # 检查格式如："答案：2"、"答 2"、"x=2"等
            if f'{keyword}{number}' in comment or \
               f'{keyword}：{number}' in comment or \
               f'{keyword} {number}' in comment or \
               f'{keyword}={number}' in comment:
                return True
        
        # 检查数字是否出现在答案部分
        answer_keyword_positions = []
        answer_keywords_full = ['答案', '答', '结果', '答案是', '结果为']
        
        for keyword in answer_keywords_full:
            pos = comment.find(keyword)
            if pos != -1:
                answer_keyword_positions.append(pos)
        
        if answer_keyword_positions:
            # 找到数字的位置
            number_pos = comment.find(number)
            if number_pos != -1:
                # 如果数字出现在某个答案关键词之后，认为是答案
                for keyword_pos in answer_keyword_positions:
                    if number_pos > keyword_pos:
                        return True
        
        return False
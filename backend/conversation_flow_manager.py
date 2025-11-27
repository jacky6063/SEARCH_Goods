"""
對話驅動流程管理器 - 生日聚會專用
提供多輪對話的狀態管理和智能引導
"""
from __future__ import annotations
import json
import re
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

class ConversationStage(Enum):
    """對話階段定義"""
    INITIAL_EXPLORATION = "initial_exploration"        # 初始需求探索
    PARTY_DETAILS = "party_details"                   # 聚會詳細資訊
    FOOD_PREFERENCES = "food_preferences"             # 餐飲偏好
    BUDGET_DISCUSSION = "budget_discussion"           # 預算討論
    PERSONALIZED_SUGGESTIONS = "personalized_suggestions"  # 個人化建議
    FINAL_RECOMMENDATIONS = "final_recommendations"   # 最終商品推薦
    COMPLETED = "completed"                          # 對話完成

@dataclass
class PartyRequirements:
    """聚會需求資料結構"""
    # 基本資訊
    birthday_age: Optional[str] = None              # 生日年齡
    participant_count: Optional[str] = None         # 參與人數
    party_type: Optional[str] = None               # 聚會類型（正式/輕鬆）
    venue: Optional[str] = None                    # 場地（室內/戶外）
    timing: Optional[str] = None                   # 時間安排
    
    # 餐飲偏好
    food_style: List[str] = None                   # 餐點風格偏好
    drink_preferences: List[str] = None            # 飲料偏好
    dietary_restrictions: List[str] = None         # 飲食限制
    age_groups: List[str] = None                   # 參與者年齡層
    
    # 預算相關
    budget_range: Optional[str] = None             # 預算範圍
    budget_priority: Optional[str] = None          # 預算優先級
    flexibility: Optional[str] = None              # 預算彈性
    
    # 特殊需求
    theme: Optional[str] = None                    # 主題風格
    special_requests: List[str] = None             # 特殊需求
    allergies: List[str] = None                    # 過敏資訊

    def __post_init__(self):
        # 確保 List 類型欄位不是 None
        if self.food_style is None:
            self.food_style = []
        if self.drink_preferences is None:
            self.drink_preferences = []
        if self.dietary_restrictions is None:
            self.dietary_restrictions = []
        if self.age_groups is None:
            self.age_groups = []
        if self.special_requests is None:
            self.special_requests = []
        if self.allergies is None:
            self.allergies = []

@dataclass
class ConversationState:
    """對話狀態管理"""
    session_id: str
    stage: ConversationStage
    requirements: PartyRequirements
    collected_info: Dict[str, Any]
    conversation_history: List[Dict[str, str]]
    created_at: float
    last_updated: float
    completion_percentage: float = 0.0
    
    def update_stage(self, new_stage: ConversationStage):
        """更新對話階段"""
        self.stage = new_stage
        self.last_updated = time.time()
        self._calculate_completion()
    
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """添加對話記錄"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "metadata": metadata or {}
        })
        self.last_updated = time.time()
    
    def update_requirements(self, **kwargs):
        """更新需求資訊"""
        for key, value in kwargs.items():
            if hasattr(self.requirements, key):
                setattr(self.requirements, key, value)
                self.collected_info[key] = value
        self.last_updated = time.time()
        self._calculate_completion()
    
    def _calculate_completion(self):
        """計算完成百分比"""
        total_fields = 15  # PartyRequirements 的主要欄位數量
        filled_fields = sum(1 for key, value in asdict(self.requirements).items() 
                          if value and (not isinstance(value, list) or len(value) > 0))
        self.completion_percentage = min(100.0, (filled_fields / total_fields) * 100)

class ConversationFlowManager:
    """對話流程管理器"""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationState] = {}
        self.session_ttl = 1800  # 30分鐘過期時間
    
    def start_conversation(self, initial_message: str) -> ConversationState:
        """開始新的對話"""
        session_id = str(uuid.uuid4())[:12]
        
        state = ConversationState(
            session_id=session_id,
            stage=ConversationStage.INITIAL_EXPLORATION,
            requirements=PartyRequirements(),
            collected_info={},
            conversation_history=[],
            created_at=time.time(),
            last_updated=time.time()
        )
        
        state.add_message("user", initial_message)
        self.sessions[session_id] = state
        return state
    
    def get_session(self, session_id: str) -> Optional[ConversationState]:
        """獲取對話狀態"""
        self._cleanup_expired_sessions()
        return self.sessions.get(session_id)
    
    def continue_conversation(self, session_id: str, user_message: str) -> Optional[ConversationState]:
        """繼續對話"""
        state = self.get_session(session_id)
        if state:
            state.add_message("user", user_message)
        return state
    
    def _cleanup_expired_sessions(self):
        """清理過期對話"""
        current_time = time.time()
        expired_sessions = [
            sid for sid, state in self.sessions.items()
            if current_time - state.last_updated > self.session_ttl
        ]
        for sid in expired_sessions:
            del self.sessions[sid]

class StageHandler(ABC):
    """對話階段處理器基礎類"""
    
    @abstractmethod
    def should_handle(self, state: ConversationState, user_message: str) -> bool:
        """判斷是否應該處理當前階段"""
        pass
    
    @abstractmethod
    def process_message(self, state: ConversationState, user_message: str) -> Tuple[str, Dict[str, Any]]:
        """處理用戶訊息並回傳回應和後設資料"""
        pass
    
    @abstractmethod
    def get_next_stage(self, state: ConversationState) -> Optional[ConversationStage]:
        """獲取下一個對話階段"""
        pass

class InitialExplorationHandler(StageHandler):
    """初始需求探索處理器"""
    
    def should_handle(self, state: ConversationState, user_message: str) -> bool:
        return state.stage == ConversationStage.INITIAL_EXPLORATION
    
    def process_message(self, state: ConversationState, user_message: str) -> Tuple[str, Dict[str, Any]]:
        # 解析初始訊息中的基本資訊
        message_lower = user_message.lower()
        
        # 提取年齡資訊
        age_matches = re.findall(r'(\d+)\s*歲?', user_message)
        if age_matches:
            state.update_requirements(birthday_age=age_matches[0])
        
        # 提取預算資訊
        budget_matches = re.findall(r'(\d+)\s*元', user_message)
        if budget_matches:
            state.update_requirements(budget_range=budget_matches[0])
        
        # 生成個人化回應
        reply_parts = [
            "真棒！幫您準備生日聚會一定很有趣！🎉",
            "",
            "為了給您最棒的建議，我需要了解一些細節："
        ]
        
        questions = []
        
        if not state.requirements.birthday_age:
            questions.append("• 這次是幾歲的生日慶祝呢？")
        
        if not state.requirements.participant_count:
            questions.append("• 大概會有多少人參加聚會？")
        
        if not state.requirements.venue:
            questions.append("• 是在家裡還是其他地方舉辦？")
        
        reply_parts.extend(questions)
        
        if state.requirements.budget_range:
            reply_parts.append(f"\n我看到您提到了 {state.requirements.budget_range} 元的預算，這個範圍我們可以安排很棒的組合！")
        
        reply = "\n".join(reply_parts)
        
        return reply, {
            "needs_more_info": len(questions) > 0,
            "extracted_info": {
                "age": state.requirements.birthday_age,
                "budget": state.requirements.budget_range
            }
        }
    
    def get_next_stage(self, state: ConversationState) -> Optional[ConversationStage]:
        # 當基本資訊收集足夠時，進入聚會詳細資訊階段
        if (state.requirements.birthday_age and 
            state.requirements.participant_count):
            return ConversationStage.PARTY_DETAILS
        return None

class PartyDetailsHandler(StageHandler):
    """聚會詳細資訊處理器"""
    
    def should_handle(self, state: ConversationState, user_message: str) -> bool:
        return state.stage == ConversationStage.PARTY_DETAILS
    
    def process_message(self, state: ConversationState, user_message: str) -> Tuple[str, Dict[str, Any]]:
        message_lower = user_message.lower()
        
        # 解析聚會類型
        if any(kw in message_lower for kw in ['正式', '莊重', '優雅']):
            state.update_requirements(party_type="正式")
        elif any(kw in message_lower for kw in ['輕鬆', '隨意', '休閒', '開心']):
            state.update_requirements(party_type="輕鬆")
        
        # 解析場地資訊
        if any(kw in message_lower for kw in ['家裡', '家中', '室內']):
            state.update_requirements(venue="室內")
        elif any(kw in message_lower for kw in ['戶外', '公園', '花園']):
            state.update_requirements(venue="戶外")
        
        # 解析參與人數
        people_matches = re.findall(r'(\d+)\s*人', user_message)
        if people_matches:
            state.update_requirements(participant_count=people_matches[0])
        
        reply_parts = [
            "很好！我越來越了解您的需求了 😊",
            ""
        ]
        
        questions = []
        
        if not state.requirements.party_type:
            questions.append("• 希望是比較正式的慶祝，還是輕鬆隨意的聚會？")
        
        if not state.requirements.timing:
            questions.append("• 大概什麼時候舉辦？（幫助我推薦合適的點心類型）")
        
        if questions:
            reply_parts.extend(questions)
        else:
            reply_parts.append("接下來我們來聊聊餐點偏好吧！")
        
        return "\n".join(reply_parts), {"stage_ready": len(questions) == 0}
    
    def get_next_stage(self, state: ConversationState) -> Optional[ConversationStage]:
        if (state.requirements.party_type and 
            state.requirements.venue):
            return ConversationStage.FOOD_PREFERENCES
        return None

# 全域對話流程管理器實例
conversation_manager = ConversationFlowManager()

def get_conversation_manager() -> ConversationFlowManager:
    """獲取對話流程管理器實例"""
    return conversation_manager
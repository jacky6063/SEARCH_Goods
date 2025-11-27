"""
階段性 LLM 提示詞模板系統
為不同對話階段提供專門的提示詞，讓 LLM 能夠更自然地引導對話
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from enum import Enum
from conversation_flow_manager import ConversationStage, ConversationState

class PromptTemplate:
    """提示詞模板類"""
    
    def __init__(self, system_prompt: str, user_template: str, guidelines: List[str] = None):
        self.system_prompt = system_prompt
        self.user_template = user_template
        self.guidelines = guidelines or []
    
    def format_prompt(self, **kwargs) -> Dict[str, str]:
        """格式化提示詞"""
        formatted_user = self.user_template.format(**kwargs)
        guidelines_text = "\n".join([f"- {g}" for g in self.guidelines])
        
        full_system = f"{self.system_prompt}\n\n對話指引：\n{guidelines_text}" if guidelines_text else self.system_prompt
        
        return {
            "system": full_system,
            "user": formatted_user
        }

class BirthdayPartyPrompts:
    """生日聚會對話提示詞集合"""
    
    @staticmethod
    def get_stage_prompt(stage: ConversationStage, state: ConversationState, user_message: str) -> Dict[str, str]:
        """根據對話階段獲取相應的提示詞"""
        
        if stage == ConversationStage.INITIAL_EXPLORATION:
            return BirthdayPartyPrompts._get_initial_exploration_prompt(state, user_message)
        elif stage == ConversationStage.PARTY_DETAILS:
            return BirthdayPartyPrompts._get_party_details_prompt(state, user_message)
        elif stage == ConversationStage.FOOD_PREFERENCES:
            return BirthdayPartyPrompts._get_food_preferences_prompt(state, user_message)
        elif stage == ConversationStage.BUDGET_DISCUSSION:
            return BirthdayPartyPrompts._get_budget_discussion_prompt(state, user_message)
        elif stage == ConversationStage.PERSONALIZED_SUGGESTIONS:
            return BirthdayPartyPrompts._get_personalized_suggestions_prompt(state, user_message)
        else:
            return BirthdayPartyPrompts._get_default_prompt(state, user_message)
    
    @staticmethod
    def _get_initial_exploration_prompt(state: ConversationState, user_message: str) -> Dict[str, str]:
        """初始需求探索階段提示詞"""
        
        template = PromptTemplate(
            system_prompt="""你是一位專業又親切的聚會策劃顧問，專門幫助客戶準備完美的生日聚會。
你的任務是透過自然對話了解客戶需求，並在適當時機推薦商品。

當前階段：初始需求探索
目標：了解聚會的基本資訊（年齡、人數、場合等）

請用溫暖、專業又不失親切的語調與客戶對話。""",
            
            user_template="""客戶說：「{user_message}」

已收集的資訊：
- 生日年齡：{birthday_age}
- 參與人數：{participant_count}
- 聚會場地：{venue}
- 預算範圍：{budget_range}

請根據客戶的訊息，自然地：
1. 表達對幫忙準備聚會的熱忱
2. 針對缺少的重要資訊提出 1-2 個關鍵問題
3. 如果客戶提到預算，給予正面回應
4. 保持對話的溫度，讓客戶感到被重視

回應請控制在 3-4 行，不要太冗長。""",
            
            guidelines=[
                "一次只問 1-2 個問題，避免訊息過多",
                "先了解年齡和人數這兩個關鍵資訊",
                "用自然的對話方式，不要像表單填寫",
                "適時給予鼓勵和正面回饋",
                "如果資訊充足，暗示下一步會討論聚會風格"
            ]
        )
        
        return template.format_prompt(
            user_message=user_message,
            birthday_age=state.requirements.birthday_age or "尚未提及",
            participant_count=state.requirements.participant_count or "尚未提及",
            venue=state.requirements.venue or "尚未提及",
            budget_range=state.requirements.budget_range or "尚未提及"
        )
    
    @staticmethod
    def _get_party_details_prompt(state: ConversationState, user_message: str) -> Dict[str, str]:
        """聚會詳細資訊階段提示詞"""
        
        template = PromptTemplate(
            system_prompt="""你是一位專業的聚會策劃顧問，現在要了解聚會的風格和氛圍。
你已經知道基本資訊，現在要深入了解客戶想要的聚會氛圍。

當前階段：聚會詳細資訊收集
目標：了解聚會風格、時間安排、場地細節

請展現你的專業性，同時保持親切和同理心。""",
            
            user_template="""客戶說：「{user_message}」

已確認的基本資訊：
- 生日年齡：{birthday_age}
- 參與人數：{participant_count}
- 預算範圍：{budget_range}

正在收集的風格資訊：
- 聚會類型：{party_type}
- 舉辦場地：{venue}
- 時間安排：{timing}

請根據客戶回應：
1. 針對他們提到的資訊表達理解和認同
2. 根據年齡和人數給出一些風格建議
3. 詢問 1-2 個關於聚會氛圍或時間的問題
4. 適時提及這些資訊將如何影響餐點選擇

保持專業但溫暖的語調。""",
            
            guidelines=[
                "根據生日年齡調整建議風格（兒童/成人/長者）",
                "考慮人數規模給出實用建議",
                "了解室內外場地差異對餐點的影響",
                "準備進入餐飲偏好討論階段"
            ]
        )
        
        return template.format_prompt(
            user_message=user_message,
            birthday_age=state.requirements.birthday_age or "未知",
            participant_count=state.requirements.participant_count or "未知",
            budget_range=state.requirements.budget_range or "未提及",
            party_type=state.requirements.party_type or "尚未確認",
            venue=state.requirements.venue or "尚未確認",
            timing=state.requirements.timing or "尚未確認"
        )
    
    @staticmethod
    def _get_food_preferences_prompt(state: ConversationState, user_message: str) -> Dict[str, str]:
        """餐飲偏好階段提示詞"""
        
        template = PromptTemplate(
            system_prompt="""你是餐飲搭配專家，專門為聚會推薦完美的餐點組合。
現在要了解客戶和賓客的口味偏好，以及任何飲食限制。

當前階段：餐飲偏好收集
目標：了解食物口味、飲料偏好、過敏資訊等

用你的專業知識給出實用建議，同時收集必要資訊。""",
            
            user_template="""客戶說：「{user_message}」

聚會基本資訊：
- {birthday_age} 歲生日，{participant_count} 人參與
- {party_type} 風格，{venue} 舉辦
- 預算：{budget_range}

餐飲偏好收集進度：
- 食物風格偏好：{food_style}
- 飲料偏好：{drink_preferences}
- 飲食限制：{dietary_restrictions}
- 參與者年齡層：{age_groups}

請根據聚會資訊和客戶回應：
1. 基於年齡和聚會風格給出專業餐點建議
2. 詢問重要的偏好或限制（如甜鹹、冷熱飲等）
3. 考慮季節和場地對餐點選擇的影響
4. 準備引導到預算分配討論

展現餐飲搭配的專業性。""",
            
            guidelines=[
                "根據年齡層推薦合適的餐點類型",
                "考慮聚會時間對餐點的影響（正餐時間 vs 點心時間）",
                "主動詢問過敏資訊，確保安全",
                "平衡甜鹹搭配，照顾不同口味",
                "為預算討論做鋪墊"
            ]
        )
        
        return template.format_prompt(
            user_message=user_message,
            birthday_age=state.requirements.birthday_age or "未知",
            participant_count=state.requirements.participant_count or "未知",
            party_type=state.requirements.party_type or "一般",
            venue=state.requirements.venue or "未知",
            budget_range=state.requirements.budget_range or "彈性",
            food_style=", ".join(state.requirements.food_style) if state.requirements.food_style else "尚未確認",
            drink_preferences=", ".join(state.requirements.drink_preferences) if state.requirements.drink_preferences else "尚未確認",
            dietary_restrictions=", ".join(state.requirements.dietary_restrictions) if state.requirements.dietary_restrictions else "無特殊限制",
            age_groups=", ".join(state.requirements.age_groups) if state.requirements.age_groups else "尚未確認"
        )
    
    @staticmethod
    def _get_budget_discussion_prompt(state: ConversationState, user_message: str) -> Dict[str, str]:
        """預算討論階段提示詞"""
        
        template = PromptTemplate(
            system_prompt="""你是預算規劃專家，擅長在有限預算內創造最大價值。
現在要與客戶討論預算分配，確保每一元都花在刀口上。

當前階段：預算討論與分配
目標：確認預算範圍，討論餐飲分配優先級

用專業但貼心的方式討論金錢話題，讓客戶感到安心。""",
            
            user_template="""客戶說：「{user_message}」

聚會完整資訊：
- {birthday_age} 歲生日聚會，{participant_count} 人參與
- {party_type} 風格，{venue} 舉辦
- 餐飲偏好：{food_preferences_summary}
- 目前預算：{budget_range}

預算討論重點：
- 預算彈性：{flexibility}
- 優先級：{budget_priority}

請根據收集的所有資訊：
1. 若客戶剛提到預算，給予合理的分配建議
2. 基於人數和偏好，說明如何最有效運用預算
3. 詢問客戶對餐點 vs 飲料的預算分配偏好
4. 提供不同價位層級的選擇參考
5. 準備進入個人化建議階段

展現預算規劃的專業度和貼心度。""",
            
            guidelines=[
                "以人均成本概念幫助客戶理解預算",
                "提供彈性預算選項（基本/標準/豪華）",
                "說明餐點和飲料的合理分配比例",
                "強調質量比數量更重要",
                "為具體商品推薦做準備"
            ]
        )
        
        # 組合餐飲偏好摘要
        food_prefs = []
        if state.requirements.food_style:
            food_prefs.extend(state.requirements.food_style)
        if state.requirements.drink_preferences:
            food_prefs.extend(state.requirements.drink_preferences)
        food_preferences_summary = ", ".join(food_prefs) if food_prefs else "一般口味"
        
        return template.format_prompt(
            user_message=user_message,
            birthday_age=state.requirements.birthday_age or "未知",
            participant_count=state.requirements.participant_count or "未知",
            party_type=state.requirements.party_type or "一般",
            venue=state.requirements.venue or "未知",
            food_preferences_summary=food_preferences_summary,
            budget_range=state.requirements.budget_range or "待討論",
            flexibility=state.requirements.flexibility or "待確認",
            budget_priority=state.requirements.budget_priority or "均衡分配"
        )
    
    @staticmethod
    def _get_personalized_suggestions_prompt(state: ConversationState, user_message: str) -> Dict[str, str]:
        """個人化建議階段提示詞"""
        
        template = PromptTemplate(
            system_prompt="""你是聚會策劃的總顧問，現在要整合所有收集的資訊，
提供個人化的聚會餐點建議方案。

當前階段：個人化建議與確認
目標：基於完整需求提供客製化方案，準備商品推薦

展現你整合資訊和創造完美聚會的能力。""",
            
            user_template="""客戶說：「{user_message}」

完整聚會需求檔案：
【基本資訊】
- 生日：{birthday_age} 歲，參與：{participant_count} 人
- 風格：{party_type}，場地：{venue}
- 預算：{budget_range}，分配偏好：{budget_priority}

【餐飲需求】
- 食物偏好：{food_preferences}
- 飲料偏好：{drink_preferences}
- 特殊考量：{special_considerations}

請根據完整資訊：
1. 整合所有需求，提出 2-3 個具體的餐飲組合方案
2. 說明每個方案的特色和適合原因
3. 給出粗略的預算分配建議
4. 詢問客戶偏好哪個方向
5. 準備進入具體商品推薦階段

這是展現專業整合能力的關鍵時刻。""",
            
            guidelines=[
                "整合所有收集的資訊提供完整方案",
                "提供多個選項讓客戶選擇",
                "說明推薦理由，展現專業性",
                "確認最終需求後準備商品推薦",
                "保持期待感，讓客戶對最終結果充滿信心"
            ]
        )
        
        # 整理特殊考量
        special_considerations = []
        if state.requirements.dietary_restrictions:
            special_considerations.extend(state.requirements.dietary_restrictions)
        if state.requirements.allergies:
            special_considerations.extend(state.requirements.allergies)
        special_considerations_text = ", ".join(special_considerations) if special_considerations else "無特殊限制"
        
        return template.format_prompt(
            user_message=user_message,
            birthday_age=state.requirements.birthday_age or "未知",
            participant_count=state.requirements.participant_count or "未知",
            party_type=state.requirements.party_type or "一般",
            venue=state.requirements.venue or "未知",
            budget_range=state.requirements.budget_range or "彈性",
            budget_priority=state.requirements.budget_priority or "均衡分配",
            food_preferences=", ".join(state.requirements.food_style) if state.requirements.food_style else "一般口味",
            drink_preferences=", ".join(state.requirements.drink_preferences) if state.requirements.drink_preferences else "一般飲品",
            special_considerations=special_considerations_text
        )
    
    @staticmethod
    def _get_default_prompt(state: ConversationState, user_message: str) -> Dict[str, str]:
        """預設提示詞（用於未定義的階段）"""
        
        template = PromptTemplate(
            system_prompt="""你是專業的聚會策劃顧問，正在與客戶討論生日聚會準備事宜。
請根據當前對話脈絡，自然地回應客戶並推進對話。

保持專業、親切和有用的態度。""",
            
            user_template="""客戶說：「{user_message}」

當前對話階段：{stage}
對話完成度：{completion_percentage}%

已收集的資訊：
{collected_info_summary}

請自然地回應客戶，並適當推進對話向商品推薦發展。""",
            
            guidelines=[
                "根據對話脈絡給出合適回應",
                "適時推進對話進度",
                "保持專業和親切的語調"
            ]
        )
        
        # 整理已收集資訊摘要
        info_parts = []
        if state.requirements.birthday_age:
            info_parts.append(f"年齡：{state.requirements.birthday_age}")
        if state.requirements.participant_count:
            info_parts.append(f"人數：{state.requirements.participant_count}")
        if state.requirements.budget_range:
            info_parts.append(f"預算：{state.requirements.budget_range}")
        
        collected_info_summary = "、".join(info_parts) if info_parts else "基本資訊收集中"
        
        return template.format_prompt(
            user_message=user_message,
            stage=state.stage.value,
            completion_percentage=int(state.completion_percentage),
            collected_info_summary=collected_info_summary
        )

class ContextualPromptGenerator:
    """情境化提示詞產生器"""
    
    @staticmethod
    def should_transition_to_recommendations(state: ConversationState) -> bool:
        """判斷是否應該轉入商品推薦階段"""
        completion_threshold = 70  # 完成度達到 70% 就可以開始推薦
        
        has_basic_info = (
            state.requirements.birthday_age and 
            state.requirements.participant_count and
            state.requirements.budget_range
        )
        
        return (
            state.completion_percentage >= completion_threshold or
            has_basic_info or
            state.stage == ConversationStage.PERSONALIZED_SUGGESTIONS
        )
    
    @staticmethod
    def get_product_recommendation_prompt(state: ConversationState, product_catalog: List[Dict]) -> Dict[str, str]:
        """產生商品推薦階段的提示詞"""
        
        # 整理完整需求摘要
        requirements_summary = ContextualPromptGenerator._build_requirements_summary(state)
        
        # 選擇相關商品（這裡簡化為傳入所有商品，實際可以預篩選）
        relevant_products = product_catalog[:20]  # 限制數量避免 token 過多
        
        product_list = []
        for i, product in enumerate(relevant_products, 1):
            product_info = f"{i}. 商品：{product.get('Name', 'N/A')} | 價格：{product.get('Price', 'N/A')} | ID：{product.get('GoodIden', 'N/A')}"
            product_list.append(product_info)
        
        products_text = "\n".join(product_list)
        
        template = PromptTemplate(
            system_prompt="""你是專業的商品推薦顧問，現在要根據客戶的生日聚會需求，
從商品清單中選擇最合適的餐點和飲料組合。

任務：
1. 根據需求摘要選擇 8-12 個最合適的商品
2. 確保餐點和飲料的平衡搭配
3. 控制在預算範圍內
4. 考慮參與人數和年齡層

回應格式要求：
- 提供溫暖的開場
- 說明推薦理由
- 列出建議商品（使用商品ID）
- 給出預算分析
- 詢問客戶意見

請選擇商品 ID 列表格式：[ID1, ID2, ID3, ...]""",
            
            user_template="""客戶需求摘要：
{requirements_summary}

可選商品清單：
{products_list}

請根據需求選擇最合適的商品組合，並提供專業建議。
記住要考慮：
- 預算控制在 {budget_range} 內
- 適合 {participant_count} 人的份量
- {birthday_age} 歲的年齡層偏好
- 餐點和飲料的均衡搭配

請提供完整的推薦說明和商品 ID 清單。""",
            
            guidelines=[
                "優先選擇 CP 值高的商品",
                "確保甜鹹搭配和口感層次",
                "考慮保存和攜帶便利性",
                "留意年齡層的喜好差異",
                "提供清楚的預算分析"
            ]
        )
        
        return template.format_prompt(
            requirements_summary=requirements_summary,
            products_list=products_text,
            budget_range=state.requirements.budget_range or "1000元",
            participant_count=state.requirements.participant_count or "未知",
            birthday_age=state.requirements.birthday_age or "未知"
        )
    
    @staticmethod
    def _build_requirements_summary(state: ConversationState) -> str:
        """建構需求摘要"""
        summary_parts = []
        
        # 基本資訊
        if state.requirements.birthday_age:
            summary_parts.append(f"🎂 {state.requirements.birthday_age} 歲生日聚會")
        
        if state.requirements.participant_count:
            summary_parts.append(f"👥 {state.requirements.participant_count} 人參與")
        
        if state.requirements.party_type:
            summary_parts.append(f"🎭 {state.requirements.party_type} 風格")
        
        if state.requirements.venue:
            summary_parts.append(f"📍 {state.requirements.venue} 舉辦")
        
        # 預算資訊
        if state.requirements.budget_range:
            summary_parts.append(f"💰 預算 {state.requirements.budget_range} 元")
        
        # 餐飲偏好
        if state.requirements.food_style:
            summary_parts.append(f"🍪 食物偏好：{', '.join(state.requirements.food_style)}")
        
        if state.requirements.drink_preferences:
            summary_parts.append(f"🥤 飲料偏好：{', '.join(state.requirements.drink_preferences)}")
        
        # 特殊需求
        if state.requirements.dietary_restrictions:
            summary_parts.append(f"⚠️ 飲食限制：{', '.join(state.requirements.dietary_restrictions)}")
        
        return "\n".join(summary_parts) if summary_parts else "基本生日聚會需求"
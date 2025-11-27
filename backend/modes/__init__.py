# -*- coding: utf-8 -*-
"""
聊天模式模組匯入點：
- marketing_consultant：活動建議／資訊導購
- shopping_recommender：商品推薦／價格導購
"""

from .marketing_consultant import prepare_information_response
from .shopping_recommender import prepare_shopping_response

__all__ = [
    "prepare_information_response",
    "prepare_shopping_response",
]

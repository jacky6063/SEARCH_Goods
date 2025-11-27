"""
統一欄位處理工具模組
確保整個系統使用一致的欄位名稱和存取方式
"""
from typing import Dict, Any, Optional, List, Union


class FieldAccessor:
    """統一的欄位存取器，支援多種欄位名稱並提供容錯機制"""
    
    # 標準欄位對照表
    FIELD_MAPPINGS = {
        "product_id": ["GoodIden", "商品編號", "id", "goodiden", "barcode", "條碼", "sku"],
        "name": ["Name", "商品名稱", "name", "title", "商品名"],
        "category": [
            "CateName",
            "CateName_L3",
            "CateName_L2",
            "CateName_L1",
            "分類名稱",
            "小分類名稱",
            "中分類名稱",
            "大分類名稱",
            "category",
            "catename",
        ],
        "brand": ["BRAND_Name", "品牌", "brand", "Brand"],
        "description": ["DESCRIPTION", "描述", "description", "Description", "desc"],
        "price": ["Price", "售價", "price", "價格"],
        "special_price": ["SpecialOffer", "特價", "specialoffer", "special_price"],
        "size": ["Size", "規格", "size", "specification"],
        "stock": ["庫存量", "stock", "inventory"],
        "image_url": ["Goodspic_Link1", "商品圖片網址1", "image_url", "pic_url"],
        "shop_url": ["Goods_Link1", "購物網址", "shop_url", "link"],
        "video_url": ["Youtube 影片介紹", "video_url", "youtube"],
        "remark": ["REMARK", "備註", "remark", "note"]
    }
    
    @classmethod
    def get_field(cls, item: Dict[str, Any], field_type: str, default: Any = None) -> Any:
        """
        安全地取得指定類型的欄位值
        
        Args:
            item: 商品資料字典
            field_type: 欄位類型 (如 'name', 'price', 'category' 等)
            default: 預設值
            
        Returns:
            欄位值或預設值
        """
        if field_type not in cls.FIELD_MAPPINGS:
            return default
            
        field_names = cls.FIELD_MAPPINGS[field_type]
        
        for field_name in field_names:
            value = item.get(field_name)
            if value is not None and str(value).strip():
                return value
        
        return default
    
    @classmethod
    def get_product_id(cls, item: Dict[str, Any]) -> str:
        """取得商品編號"""
        return str(cls.get_field(item, "product_id", ""))
    
    @classmethod
    def get_name(cls, item: Dict[str, Any]) -> str:
        """取得商品名稱"""
        return str(cls.get_field(item, "name", "未知商品"))
    
    @classmethod
    def get_category(cls, item: Dict[str, Any]) -> str:
        """取得分類名稱 (優先順序: L3 > L2 > L1)"""
        return str(cls.get_field(item, "category", "未分類"))
    
    @classmethod
    def get_category_l1(cls, item: Dict[str, Any]) -> str:
        """取得大分類名稱 (Level 1)"""
        l1 = item.get("CateName_L1") or item.get("大分類名稱")
        return str(l1) if l1 else ""
    
    @classmethod
    def get_category_l2(cls, item: Dict[str, Any]) -> str:
        """取得中分類名稱 (Level 2)"""
        l2 = item.get("CateName_L2") or item.get("中分類名稱")
        return str(l2) if l2 else ""
    
    @classmethod
    def get_category_l3(cls, item: Dict[str, Any]) -> str:
        """取得小分類名稱 (Level 3)"""
        l3 = item.get("CateName_L3") or item.get("小分類名稱")
        return str(l3) if l3 else ""
    
    @classmethod
    def get_brand(cls, item: Dict[str, Any]) -> str:
        """取得品牌"""
        return str(cls.get_field(item, "brand", ""))
    
    @classmethod
    def get_description(cls, item: Dict[str, Any]) -> str:
        """取得商品描述"""
        return str(cls.get_field(item, "description", ""))
    
    @classmethod
    def get_price(cls, item: Dict[str, Any]) -> Optional[int]:
        """取得售價 (轉換為整數)"""
        price_str = cls.get_field(item, "price", "0")
        try:
            # 提取數字部分
            import re
            numbers = re.findall(r'\d+', str(price_str))
            return int(numbers[0]) if numbers else None
        except (ValueError, IndexError):
            return None
    
    @classmethod
    def get_special_price(cls, item: Dict[str, Any]) -> Optional[int]:
        """取得特價 (轉換為整數)"""
        price_str = cls.get_field(item, "special_price", "0")
        try:
            import re
            numbers = re.findall(r'\d+', str(price_str))
            return int(numbers[0]) if numbers else None
        except (ValueError, IndexError):
            return None
    
    @classmethod
    def get_size(cls, item: Dict[str, Any]) -> str:
        """取得規格"""
        return str(cls.get_field(item, "size", ""))
    
    @classmethod
    def get_stock(cls, item: Dict[str, Any]) -> Optional[int]:
        """取得庫存量"""
        stock_str = cls.get_field(item, "stock")
        try:
            return int(stock_str) if stock_str else None
        except (ValueError, TypeError):
            return None
    
    @classmethod
    def get_image_url(cls, item: Dict[str, Any]) -> str:
        """取得商品圖片網址"""
        return str(cls.get_field(item, "image_url", ""))
    
    @classmethod
    def get_shop_url(cls, item: Dict[str, Any]) -> str:
        """取得購物網址"""
        return str(cls.get_field(item, "shop_url", ""))
    
    @classmethod
    def standardize_product(cls, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        將商品資料標準化為統一格式
        
        Args:
            item: 原始商品資料
            
        Returns:
            標準化後的商品資料
        """
        return {
            "id": cls.get_product_id(item),
            "name": cls.get_name(item),
            "category": cls.get_category(item),
            "brand": cls.get_brand(item),
            "description": cls.get_description(item),
            "price": cls.get_price(item),
            "special_price": cls.get_special_price(item),
            "size": cls.get_size(item),
            "stock": cls.get_stock(item),
            "image_url": cls.get_image_url(item),
            "shop_url": cls.get_shop_url(item),
            # 保留原始資料以供備用
            "_raw": item
        }
    
    @classmethod
    def format_product_display(cls, item: Dict[str, Any]) -> str:
        """
        格式化商品顯示文字
        
        Args:
            item: 商品資料
            
        Returns:
            格式化的顯示文字
        """
        name = cls.get_name(item)
        price = cls.get_price(item)
        special_price = cls.get_special_price(item)
        
        if special_price and special_price < price:
            return f"{name} - 特價{special_price}元 (原價{price}元)"
        elif price:
            return f"{name} - {price}元"
        else:
            return name


def safe_get_fields(items: List[Dict[str, Any]], field_type: str) -> List[str]:
    """
    安全地從商品列表中提取特定欄位的所有值
    
    Args:
        items: 商品列表
        field_type: 欄位類型
        
    Returns:
        欄位值列表 (去除空值)
    """
    values = []
    for item in items:
        value = FieldAccessor.get_field(item, field_type)
        if value and str(value).strip():
            values.append(str(value))
    return values


def create_product_summary(items: List[Dict[str, Any]], max_items: int = 3) -> str:
    """
    建立商品摘要文字
    
    Args:
        items: 商品列表
        max_items: 最多顯示商品數量
        
    Returns:
        商品摘要文字
    """
    if not items:
        return "沒有找到商品"
    
    samples = []
    for item in items[:max_items]:
        name = FieldAccessor.get_name(item)
        if name and name != "未知商品":
            samples.append(name)
    
    if samples:
        return "、".join(samples)
    else:
        return f"{len(items)} 項商品"

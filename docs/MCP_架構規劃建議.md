# SEARCH_Goods MCP 架構規劃建議

> **文件版本**: v1.0  
> **撰寫日期**: 2025年11月14日  
> **評估對象**: SEARCH_Goods 商品查詢系統

---

## 📋 目錄

1. [系統現況分析](#系統現況分析)
2. [MCP 適用性評估](#mcp-適用性評估)
3. [MCP 架構設計方案](#mcp-架構設計方案)
4. [實施建議與優先順序](#實施建議與優先順序)
5. [技術實作細節](#技術實作細節)
6. [風險與挑戰](#風險與挑戰)

---

## 🔍 系統現況分析

### 當前架構

```
┌─────────────────────────────────────────────────┐
│              Frontend (SPA)                     │
│  - index.html (3684 lines)                      │
│  - Vanilla JavaScript                           │
│  - 三意圖路由 (商品/維修/公司)                    │
└─────────────────┬───────────────────────────────┘
                  │ HTTP REST API
┌─────────────────▼───────────────────────────────┐
│           Backend (FastAPI)                     │
│  ┌─────────────────────────────────────────┐   │
│  │ Core Services                           │   │
│  │ - goods_search_service.py               │   │
│  │ - llm_service.py (OpenAI)               │   │
│  │ - repair_llm_service.py                 │   │
│  │ - company_profile_service.py            │   │
│  └─────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────┐   │
│  │ Data Layer                              │   │
│  │ - CSV (VIEW_GOODS_enhanced.csv)         │   │
│  │ - In-memory cache                       │   │
│  │ - Pandas DataFrame                      │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### 系統特點

✅ **優點**:
- 單體架構，部署簡單
- FastAPI 高性能
- LLM 整合完善（OpenAI GPT-4o-mini）
- 三意圖智慧路由（商品/維修/公司）
- CSV 數據源靈活

⚠️ **限制**:
- 緊耦合的服務層
- 直接 API 調用，無統一協議
- 擴展性受限
- 多模型管理困難

---

## 🎯 MCP 適用性評估

### 什麼是 MCP？

**Model Context Protocol (MCP)** 是一個開放協議，用於標準化 AI 應用與外部數據源/工具的集成方式。

### 對 SEARCH_Goods 的價值分析

| 評估項目 | 適用性 | 說明 |
|---------|-------|------|
| **多模型管理** | ⭐⭐⭐⭐⭐ | 當前已整合 OpenAI，未來可能需要 Claude、Gemini |
| **工具擴展** | ⭐⭐⭐⭐⭐ | 需要更多外部工具（庫存查詢、訂單系統、CRM） |
| **上下文管理** | ⭐⭐⭐⭐ | 聊天歷史、會話狀態已有基礎實作 |
| **標準化接口** | ⭐⭐⭐⭐⭐ | 三意圖路由可抽象為 MCP Resources |
| **開發效率** | ⭐⭐⭐⭐ | 減少重複代碼，提升維護性 |

**結論**: ✅ **高度適合導入 MCP 架構**

---

## 🏗️ MCP 架構設計方案

### 方案 A：漸進式 MCP 導入（推薦）

保留現有架構，逐步將核心功能包裝為 MCP Server。

```
┌───────────────────────────────────────────────────────────┐
│                    Frontend (不變)                         │
└──────────────────────┬────────────────────────────────────┘
                       │
┌──────────────────────▼────────────────────────────────────┐
│              FastAPI Gateway (既有)                        │
│  ┌───────────────────────────────────────────────────┐   │
│  │ MCP Client Layer (新增)                           │   │
│  │  - 統一的 MCP 客戶端                               │   │
│  │  - 路由到不同 MCP Server                          │   │
│  └──────────┬────────────────────────┬─────────────────┘  │
└─────────────┼────────────────────────┼────────────────────┘
              │                        │
    ┌─────────▼──────┐      ┌─────────▼──────┐
    │ MCP Server 1   │      │ MCP Server 2   │
    │ (商品搜尋)      │      │ (維修服務)      │
    │                │      │                │
    │ Resources:     │      │ Resources:     │
    │ - products/    │      │ - repairs/     │
    │ - categories/  │      │ - diagnostics/ │
    │                │      │                │
    │ Tools:         │      │ Tools:         │
    │ - search       │      │ - analyze      │
    │ - filter       │      │ - quote        │
    │ - recommend    │      │ - schedule     │
    └────────────────┘      └────────────────┘
              │                        │
              ▼                        ▼
        ┌──────────┐            ┌──────────┐
        │ CSV Data │            │ Repair   │
        │          │            │ Database │
        └──────────┘            └──────────┘
```

### 方案 B：完全 MCP 重構

完全基於 MCP 協議重建系統（長期規劃）。

---

## 📝 實施建議與優先順序

### Phase 1: 基礎設施（2-3 週）

**優先級：P0（必要）**

1. **安裝 MCP SDK**
   ```bash
   pip install mcp  # Python MCP SDK
   ```

2. **建立 MCP Server 框架**
   ```
   backend/
   ├── mcp_servers/
   │   ├── __init__.py
   │   ├── products_server.py      # 商品搜尋 MCP Server
   │   ├── repair_server.py        # 維修服務 MCP Server
   │   └── company_server.py       # 公司資訊 MCP Server
   └── mcp_client/
       ├── __init__.py
       └── gateway.py              # MCP 客戶端統一入口
   ```

3. **定義 MCP Resources**
   - `products://search` - 商品搜尋
   - `products://categories` - 分類查詢
   - `repairs://items` - 維修項目
   - `company://profile` - 公司資訊

### Phase 2: 核心服務遷移（3-4 週）

**優先級：P1（重要）**

#### 2.1 商品搜尋 MCP Server

```python
# backend/mcp_servers/products_server.py
from mcp.server import Server
from mcp.types import Resource, Tool

class ProductsMCPServer(Server):
    """商品搜尋 MCP Server"""
    
    def __init__(self):
        super().__init__("products-server")
        
    async def list_resources(self):
        """定義可用資源"""
        return [
            Resource(
                uri="products://search",
                name="商品搜尋",
                description="搜尋商品資料庫",
                mimeType="application/json"
            ),
            Resource(
                uri="products://categories",
                name="商品分類",
                description="查詢商品分類層級",
                mimeType="application/json"
            )
        ]
    
    async def list_tools(self):
        """定義可用工具"""
        return [
            Tool(
                name="search_products",
                description="搜尋符合條件的商品",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "price_min": {"type": "number"},
                        "price_max": {"type": "number"},
                        "category": {"type": "string"}
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="filter_by_price",
                description="依價格範圍篩選商品",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "min": {"type": "number"},
                        "max": {"type": "number"}
                    }
                }
            )
        ]
    
    async def call_tool(self, name: str, arguments: dict):
        """執行工具"""
        if name == "search_products":
            return await self._search_products(arguments)
        elif name == "filter_by_price":
            return await self._filter_by_price(arguments)
    
    async def _search_products(self, args):
        """實際執行商品搜尋"""
        from goods_search_service import search_products
        results = search_products(
            query=args["query"],
            topn=args.get("topn", 20)
        )
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(results, ensure_ascii=False)
                }
            ]
        }
```

#### 2.2 MCP Gateway 實作

```python
# backend/mcp_client/gateway.py
from mcp.client import Client
from typing import Dict, Any

class MCPGateway:
    """MCP 客戶端統一入口"""
    
    def __init__(self):
        self.clients: Dict[str, Client] = {}
        self._init_clients()
    
    def _init_clients(self):
        """初始化所有 MCP 客戶端"""
        self.clients["products"] = Client("products-server")
        self.clients["repair"] = Client("repair-server")
        self.clients["company"] = Client("company-server")
    
    async def route_intent(self, intent: str, message: str, **kwargs) -> Any:
        """根據意圖路由到對應的 MCP Server"""
        if intent == "shopping":
            return await self._call_products(message, **kwargs)
        elif intent == "repair":
            return await self._call_repair(message, **kwargs)
        elif intent == "company":
            return await self._call_company(message, **kwargs)
    
    async def _call_products(self, message: str, **kwargs):
        """調用商品搜尋 MCP Server"""
        client = self.clients["products"]
        result = await client.call_tool(
            "search_products",
            {"query": message, **kwargs}
        )
        return result
```

#### 2.3 FastAPI 整合

```python
# backend/app.py 修改
from mcp_client.gateway import MCPGateway

# 初始化 MCP Gateway
mcp_gateway = MCPGateway()

@app.post("/api/chat")
async def chat_endpoint(req: ChatReq):
    """聊天端點（使用 MCP）"""
    # 意圖識別（保持不變）
    intent = detect_intent(req.message)
    
    # 透過 MCP Gateway 路由
    result = await mcp_gateway.route_intent(
        intent=intent,
        message=req.message,
        history=req.history,
        session_id=req.session_id
    )
    
    return result
```

### Phase 3: 高級功能（4-6 週）

**優先級：P2（增強）**

1. **多模型支援**
   - Claude MCP Server
   - Gemini MCP Server
   - 本地 Llama MCP Server

2. **外部工具集成**
   - 庫存管理 MCP Server
   - 訂單系統 MCP Server
   - CRM MCP Server

3. **智能路由優化**
   - 基於成本的模型選擇
   - 基於效能的負載均衡

---

## 🛠️ 技術實作細節

### MCP Server 生命週期

```python
# backend/mcp_servers/base_server.py
from abc import ABC, abstractmethod
import asyncio

class BaseMCPServer(ABC):
    """MCP Server 基類"""
    
    def __init__(self, name: str):
        self.name = name
        self.running = False
    
    async def start(self):
        """啟動 Server"""
        self.running = True
        print(f"✅ {self.name} MCP Server started")
    
    async def stop(self):
        """停止 Server"""
        self.running = False
        print(f"🛑 {self.name} MCP Server stopped")
    
    @abstractmethod
    async def list_resources(self):
        """列出可用資源"""
        pass
    
    @abstractmethod
    async def list_tools(self):
        """列出可用工具"""
        pass
    
    @abstractmethod
    async def call_tool(self, name: str, arguments: dict):
        """執行工具"""
        pass
```

### 配置管理

```yaml
# backend/mcp_config.yaml
servers:
  products:
    enabled: true
    port: 8001
    resources:
      - products://search
      - products://categories
    tools:
      - search_products
      - filter_by_price
      - recommend_items
    
  repair:
    enabled: true
    port: 8002
    resources:
      - repairs://items
      - repairs://diagnostics
    tools:
      - analyze_issue
      - generate_quote
      - schedule_service
    
  company:
    enabled: true
    port: 8003
    resources:
      - company://profile
      - company://faq
    tools:
      - get_info
      - search_faq

routing:
  default_intent: shopping
  intent_mapping:
    shopping: products
    repair: repair
    company: company
```

### 監控與日誌

```python
# backend/mcp_client/monitoring.py
import logging
from datetime import datetime

class MCPMonitor:
    """MCP 調用監控"""
    
    def __init__(self):
        self.logger = logging.getLogger("mcp")
        self.metrics = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "avg_latency": 0
        }
    
    async def log_call(self, server: str, tool: str, duration: float, success: bool):
        """記錄 MCP 調用"""
        self.metrics["total_calls"] += 1
        if success:
            self.metrics["successful_calls"] += 1
        else:
            self.metrics["failed_calls"] += 1
        
        self.logger.info(f"[{datetime.now()}] {server}.{tool} - {duration:.2f}ms - {'✅' if success else '❌'}")
```

---

## ⚠️ 風險與挑戰

### 技術風險

| 風險 | 影響 | 機率 | 緩解措施 |
|-----|------|------|---------|
| MCP SDK 穩定性 | 高 | 中 | 使用成熟版本，預留回退機制 |
| 性能開銷 | 中 | 高 | 增加緩存層，優化調用路徑 |
| 複雜度增加 | 中 | 高 | 完善文檔，漸進式遷移 |
| 現有功能破壞 | 高 | 低 | 完整測試，保留舊接口 |

### 組織風險

- **學習曲線**: 團隊需要學習 MCP 協議
- **開發時間**: 短期內會增加開發工作量
- **維護成本**: 需要維護多個 MCP Server

---

## 📊 成本效益分析

### 初期投入（Phase 1-2）

- **開發時間**: 5-7 週
- **人力**: 1-2 名全職開發
- **風險**: 中等

### 長期收益

✅ **技術收益**:
- 架構清晰，易於擴展
- 多模型切換成本低
- 標準化接口，降低維護成本

✅ **業務收益**:
- 快速集成新功能
- 支援更多使用場景
- 提升系統穩定性

---

## 🎯 最終建議

### 適合導入 MCP 的場景

✅ **強烈推薦**:
1. 計劃支援多個 LLM 模型（Claude、Gemini、本地模型）
2. 需要集成更多外部系統（ERP、CRM、庫存）
3. 系統將持續擴展（新功能、新服務）
4. 團隊有足夠技術能力和時間

⚠️ **謹慎評估**:
1. 只使用單一 LLM 且功能穩定
2. 短期內無擴展計劃
3. 團隊資源有限
4. 追求極致性能（MCP 有額外開銷）

### 實施路線圖

```
[月份 1-2] Phase 1: 基礎設施
  - MCP SDK 導入
  - Server 框架建立
  - 基本路由實作

[月份 3-4] Phase 2: 核心遷移
  - 商品搜尋 MCP Server
  - 維修服務 MCP Server
  - 公司資訊 MCP Server

[月份 5-6] Phase 3: 高級功能
  - 多模型支援
  - 外部工具集成
  - 性能優化

[月份 7+] Phase 4: 持續優化
  - 監控完善
  - 擴展新功能
  - 最佳實踐積累
```

---

## 📚 參考資源

- [Model Context Protocol 官方文檔](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Server Examples](https://github.com/modelcontextprotocol/servers)
- [FastAPI + MCP 整合範例](https://github.com/modelcontextprotocol/examples)

---

## 📧 聯絡與反饋

如有任何問題或建議，請聯繫技術團隊。

**最後更新**: 2025年11月14日  
**版本**: v1.0  
**作者**: GitHub Copilot (Claude 3.5 Sonnet)

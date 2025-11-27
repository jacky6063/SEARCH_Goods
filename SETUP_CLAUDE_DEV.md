# SEARCH_Goods 開發環境設定指南 - Claude 4 Sonnet

## ✅ Continue IDE 已配置完成

您的 Continue IDE 現在已設定使用 Claude-4-Sonnet 作為主要開發助手！

## 🔑 API Key 設定步驟

### 1. 取得 Anthropic API Key
1. 前往 [Anthropic Console](https://console.anthropic.com/)
2. 註冊/登入帳戶
3. 建立新的 API Key
4. 複製您的 API Key

### 2. 設定環境變數 (macOS/bash)
```bash
# 編輯您的 bash 配置檔案
nano ~/.bash_profile

# 或者如果您使用 .bashrc
nano ~/.bashrc

# 新增以下行 (替換 your-api-key-here)
export ANTHROPIC_API_KEY="your-api-key-here"

# 儲存檔案後重新載入
source ~/.bash_profile
# 或
source ~/.bashrc
```

### 3. 快速設定指令
```bash
# 一次性設定 (此次 session 有效)
export ANTHROPIC_API_KEY="your-api-key-here"

# 永久設定 (推薦)
echo 'export ANTHROPIC_API_KEY="your-api-key-here"' >> ~/.bash_profile
source ~/.bash_profile
```

## 🚀 Continue IDE 功能

配置完成後，您可以在 VS Code 中使用：

- **Ctrl+I** (或 Cmd+I): 開啟 Continue 聊天
- **Tab**: 智能程式碼補全
- **Ctrl+Shift+I**: 快速編輯建議
- 選取程式碼後按 **Ctrl+I**: 對選取的程式碼提問

## 📋 已設定的模型

1. **Claude 3 Haiku** (主要) - 快速且高效的程式設計助手 ✅ 已驗證
2. **GPT-4o** (備用) - 如果需要 OpenAI 模型
3. **Qwen2.5 Coder** (本地) - 離線程式碼補全

## ✅ 配置驗證成功

**API 測試結果**: Claude 3 Haiku 已成功連接並可正常使用！

**測試回應示例**:
```
作為一個人工智能助理,我可以為程式開發提供以下協助:
1. 提供程式設計和開發的建議和意見
2. 協助進行問題排查和除錯
3. 提供程式語言的語法和用法參考
4. 協助進行數據分析和可視化
5. 提供軟體測試和安全性評估
```

## 🔧 使用方式

重新啟動 VS Code 後：
1. **Cmd+I**: 開啟 Continue 聊天面板
2. **Tab**: 智能程式碼補全
3. 選取程式碼 + **Cmd+I**: 分析程式碼
4. 應該會看到 "Claude 3 Haiku (開發環境)" 的回應

## 💡 使用建議

- Claude 4 Sonnet 特別適合：
  - 複雜的程式邏輯分析
  - 程式碼重構建議  
  - API 文件撰寫
  - 錯誤除錯協助
  - 程式架構設計

---
配置完成！您現在可以享受 Claude 4 Sonnet 的強大程式設計協助了！ 🎉
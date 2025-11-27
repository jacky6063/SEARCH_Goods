export function modifyConfig(config: any): any {
  // 設定 Claude-3-Haiku 作為主要開發模型（已驗證可用）
  config.models = [
    {
      title: "Claude 3 Haiku (開發環境)",
      provider: "anthropic",
      model: "claude-3-haiku-20240307",
      apiKey: "$ANTHROPIC_API_KEY",
    },
    // 保留 OpenAI 作為備用選項
    {
      title: "GPT-4o (備用)",
      provider: "openai", 
      model: "gpt-4o",
      apiKey: "$OPENAI_API_KEY",
    },
    // 本地模型選項
    {
      title: "Qwen2.5 Coder (本地)",
      provider: "ollama",
      model: "qwen2.5-coder:7b",
    }
  ];

  // 設定 Claude 作為預設的聊天模型
  config.defaultModel = {
    title: "Claude 3 Haiku (開發環境)",
    provider: "anthropic", 
    model: "claude-3-haiku-20240307",
    apiKey: "$ANTHROPIC_API_KEY",
  };

  // 優化程式碼補全設定
  config.tabAutocompleteModel = {
    title: "Claude 3 Haiku (補全)",
    provider: "anthropic",
    model: "claude-3-haiku-20240307", 
    apiKey: "$ANTHROPIC_API_KEY",
  };

  return config;
}
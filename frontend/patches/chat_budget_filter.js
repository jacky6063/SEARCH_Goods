export function hasBudgetIntent(text = "") {
  const t = (text || "").toString().trim();
  if (!t) return false;
  const kw = /(預算|多少錢|多少元|幫我抓|抓一下|價位|上限|大約|大概|便宜|貴不貴|價格)/i;
  const money = /(\d[\d,\.]*)(\s*)(元|塊|\$)/i;
  return kw.test(t) || money.test(t);
}
export function filterBudgetBlock(lastUserText, rootSelector = ".chat-area") {
  const root = document.querySelector(rootSelector) || document;
  if (hasBudgetIntent(lastUserText)) return;
  const msgs = root.querySelectorAll(".assistant-message, .msg-assistant, .chat-ai, .bot");
  const last = msgs[msgs.length - 1];
  if (!last) return;
  const patterns = [
    /如果您有特定的需求或預算/,
    /預估金額約/i,
    /預算\s*\d+/,
    /剩餘\s*[-]?\d+\s*元/,
  ];
  last.querySelectorAll("p, div, li").forEach(el => {
    const txt = (el.textContent || "").trim();
    if (!txt) return;
    if (patterns.some(re => re.test(txt))) {
      const prev = el.previousElementSibling;
      if (prev && /預算|估算|總價/i.test(prev.textContent || "")) prev.remove();
      el.remove();
    }
  });
  last.querySelectorAll("p:empty, div:empty, li:empty").forEach(n => n.remove());
}
export function installBudgetFilter(getLastUserText, getChatRootSelector = ".chat-area") {
  return () => {
    const text = (typeof getLastUserText === "function") ? getLastUserText() : "";
    filterBudgetBlock(text, getChatRootSelector);
  };
}

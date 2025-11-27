// 測試連續維修查詢的意圖檢測
const REPAIR_KEYWORDS = ['維修', '修理', '故障', '壞了', '不能用', '漏水', '漏電', '跳電', '瓦斯洩漏', '插座發熱', '燈不亮', '管線破裂'];
const SHOPPING_KEYWORDS = ['購買', '訂購', '價格', '多少錢', '買', '價錢', '報價', '費用', '成本', '選購', '推薦', '哪裡買', '有賣'];
const COMPANY_KEYWORDS = ['公司', '地址', '電話', '聯絡', '聯繫', '營業時間', '服務時間', '辦公時間', '傳真', 'email', '郵件', '位置', '怎麼去', '在哪裡', '找你們'];

// 模擬狀態
let currentIntentMode = null;
let intentModeLock = 'auto'; // 'auto', 'system', 'manual'

function detectIntentPure(text) {
    let repairScore = 0;
    let shoppingScore = 0;
    let companyScore = 0;
    
    const lowerText = text.toLowerCase();
    
    REPAIR_KEYWORDS.forEach(kw => {
        if (lowerText.includes(kw.toLowerCase())) repairScore++;
    });
    
    SHOPPING_KEYWORDS.forEach(kw => {
        if (lowerText.includes(kw.toLowerCase())) shoppingScore++;
    });
    
    COMPANY_KEYWORDS.forEach(kw => {
        if (lowerText.includes(kw.toLowerCase())) companyScore++;
    });
    
    if (companyScore > 0 && companyScore >= repairScore && companyScore >= shoppingScore) {
        return { intent: 'company', scores: { repair: repairScore, shopping: shoppingScore, company: companyScore } };
    }
    if (repairScore > shoppingScore) {
        return { intent: 'repair', scores: { repair: repairScore, shopping: shoppingScore, company: companyScore } };
    }
    if (shoppingScore > 0) {
        return { intent: 'shopping', scores: { repair: repairScore, shopping: shoppingScore, company: companyScore } };
    }
    return { intent: 'shopping', scores: { repair: repairScore, shopping: shoppingScore, company: companyScore } };
}

function detectIntent(text) {
    const result = detectIntentPure(text);
    const { intent: detectedIntent, scores } = result;
    const { repair: repairScore, shopping: shoppingScore, company: companyScore } = scores;
    
    // 檢查是否有明確意圖
    const hasExplicitIntent = 
        (detectedIntent === 'repair' && repairScore >= 1) ||
        (detectedIntent === 'shopping' && shoppingScore >= 1) ||
        (detectedIntent === 'company' && companyScore >= 1);
    
    console.log(`  [detectIntent] 純檢測: ${detectedIntent}, 分數: R=${repairScore}/S=${shoppingScore}/C=${companyScore}, 明確意圖: ${hasExplicitIntent}`);
    
    // 首次檢測：設定鎖定
    if (intentModeLock === 'auto' && (repairScore > 0 || shoppingScore > 0 || companyScore > 0)) {
        currentIntentMode = detectedIntent;
        intentModeLock = 'system';
        console.log(`  [detectIntent] 首次檢測，鎖定為: ${currentIntentMode}`);
        return detectedIntent;
    }
    
    // 系統鎖定狀態
    if (intentModeLock === 'system') {
        if (hasExplicitIntent) {
            // 有明確意圖，切換並保持鎖定
            if (detectedIntent !== currentIntentMode) {
                console.log(`  [detectIntent] 切換意圖: ${currentIntentMode} → ${detectedIntent}`);
                currentIntentMode = detectedIntent;
            } else {
                console.log(`  [detectIntent] 保持鎖定在: ${currentIntentMode}`);
            }
            return detectedIntent;
        } else {
            // 無明確意圖，繼續使用當前模式
            console.log(`  [detectIntent] 無明確意圖，保持: ${currentIntentMode}`);
            return currentIntentMode;
        }
    }
    
    return detectedIntent;
}

// 測試場景：連續維修查詢
console.log('🧪 測試場景：連續維修查詢\n');
console.log('='.repeat(70));

const testQueries = [
    { query: '瓦斯洩漏', expected: 'repair' },
    { query: '插座發熱', expected: 'repair' },
    { query: '搜尋商品', expected: 'shopping' }
];

testQueries.forEach((test, index) => {
    console.log(`\n步驟 ${index + 1}: "${test.query}"`);
    console.log(`  當前狀態: intentModeLock=${intentModeLock}, currentIntentMode=${currentIntentMode}`);
    
    const result = detectIntent(test.query);
    const status = result === test.expected ? '✅' : '❌';
    
    console.log(`  最終結果: ${result} ${status} (預期: ${test.expected})`);
    
    if (result !== test.expected) {
        console.log(`  ⚠️  錯誤！預期 ${test.expected} 但得到 ${result}`);
    }
});

console.log('\n' + '='.repeat(70));
console.log('\n�� 問題診斷：');
console.log('如果步驟2失敗，表示「插座發熱」被誤判為非維修意圖');
console.log('可能原因：');
console.log('1. hasExplicitIntent 判斷邏輯有誤');
console.log('2. 系統鎖定狀態下的繼續邏輯有問題');
console.log('3. 關鍵字匹配失敗');

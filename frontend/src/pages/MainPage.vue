<script setup lang="ts">
import { ref, reactive, computed } from 'vue';
import UploadScanPanel from '../components/UploadScanPanel.vue';
import type { UserProfile, ScanResult } from '../types';
import { scan } from '../api/medlens';

const userProfile = reactive<UserProfile>({
  age: 0,
  gender: 'male',
  pregnancy_status: 'none',
  chronic_diseases: [],
  allergies: [],
  drinking_habit: false,
  coffee_habit: false,
  grapefruit_habit: false
});

const loadingScan = ref(false);
const scanResult = ref<ScanResult | null>(null);
const errorMessage = ref('');

const loadingMessages = [
  '正在识别图片文字...',
  '正在理解药品信息...',
  '正在核查潜在风险...',
  '正在生成安全提醒...'
];

const currentLoadingMessage = ref(0);

const handleScan = async (file: File) => {
  if (!file) {
    errorMessage.value = '请选择图片文件';
    return;
  }

  scanResult.value = null;
  errorMessage.value = '';
  loadingScan.value = true;
  currentLoadingMessage.value = 0;

  const messageInterval = setInterval(() => {
    currentLoadingMessage.value = (currentLoadingMessage.value + 1) % loadingMessages.length;
  }, 2000);

  try {
    const result = await scan(file, userProfile);
    scanResult.value = result;
  } catch (error: any) {
    errorMessage.value = error.message || '分析失败';
  } finally {
    clearInterval(messageInterval);
    loadingScan.value = false;
  }
};

const handleFileSelect = () => {
  scanResult.value = null;
  errorMessage.value = '';
};

const handleReset = () => {
  scanResult.value = null;
  errorMessage.value = '';
};

function sanitizeSummary(text: string): string {
  const dangerousPatterns = [
    /你应该停药/g,
    /可以停药/g,
    /自行换药/g,
    /自行调整剂量/g,
    /无需咨询医生/g,
    /一定安全/g,
    /推荐你服用某药/g
  ];
  let result = text;
  for (const pattern of dangerousPatterns) {
    result = result.replace(pattern, '请咨询医生或药师确认，请勿自行停药、换药或调整剂量。');
  }
  return result;
}

function getFinalSummary(scanResult: ScanResult | null): string {
  if (!scanResult) return '';

  const overall = scanResult?.graphrag?.overall_summary;
  if (overall && overall.trim()) return sanitizeSummary(overall);

  const riskCards = scanResult?.graphrag?.risk_cards || [];
  const extractionItems = scanResult?.extraction?.items || [];

  if (!extractionItems.length && !riskCards.length) {
    return '未能稳定识别图片中的药品信息，请重新上传更清晰的药盒、说明书或医嘱图片，或咨询医生/药师确认。';
  }

  if (riskCards.length > 0) {
    const high = riskCards.find(c => c.severity === 'high');
    const medium = riskCards.find(c => c.severity === 'medium');
    const first = high || medium || riskCards[0];
    const reason = first.reason || first.title || first.suggestion || '系统发现潜在用药风险';
    return sanitizeSummary(`系统发现潜在用药风险：${reason} 请咨询医生或药师确认，请勿自行停药、换药或调整剂量。`);
  }

  return '基于当前图片和知识库，暂未发现明确用药风险；但这不代表一定安全，请以正式说明书和医生/药师建议为准。';
}

const finalSummary = computed(() => getFinalSummary(scanResult.value));
</script>

<template>
  <div class="page">
    <div class="container">
      <header class="header">
        <h1>MedLens</h1>
        <p class="subtitle">上传药品说明书、药盒或医嘱图片，获取用药安全提醒</p>
      </header>

      <main class="main-content">
        <div v-if="errorMessage" class="error-card">
          <div class="error-content">
            <span class="error-icon">!</span>
            <span class="error-text">分析失败：{{ errorMessage }}</span>
          </div>
          <button class="retry-btn" @click="handleReset">重新上传</button>
        </div>

        <div v-else-if="loadingScan" class="loading-card">
          <div class="loading-spinner"></div>
          <h3>正在分析，请稍候...</h3>
          <p class="loading-message">{{ loadingMessages[currentLoadingMessage] }}</p>
        </div>

        <div v-else-if="scanResult" class="result-card">
          <div class="result-header">
            <h3>用药安全提醒</h3>
          </div>
          <div class="result-content">
            <p>{{ finalSummary }}</p>
          </div>
          <button class="retry-btn" @click="handleReset">重新分析</button>
        </div>

        <div v-else class="upload-card">
          <UploadScanPanel
            @scan="handleScan"
            @file-select="handleFileSelect"
            :loading="loadingScan"
          />
        </div>
      </main>

      <footer class="disclaimer">
        <p>本系统仅用于家庭用药信息解释和风险提示，不能替代医生、药师或医疗机构建议。请勿根据本系统结果自行停药、换药或调整剂量。</p>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: #f7f9fb;
  padding: 48px 24px;
}

.container {
  max-width: 960px;
  margin: 0 auto;
}

.header {
  text-align: center;
  margin-bottom: 40px;
}

.header h1 {
  font-size: 32px;
  font-weight: 700;
  color: #2c3e50;
  margin: 0 0 12px 0;
}

.subtitle {
  font-size: 16px;
  color: #7f8c8d;
  margin: 0;
}

.main-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}

.upload-card {
  width: 100%;
  max-width: 720px;
}

.loading-card {
  width: 100%;
  max-width: 720px;
  background: white;
  border-radius: 12px;
  padding: 48px;
  text-align: center;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #e0e0e0;
  border-top-color: #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 24px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-card h3 {
  font-size: 20px;
  color: #2c3e50;
  margin: 0 0 12px 0;
}

.loading-message {
  font-size: 14px;
  color: #7f8c8d;
  margin: 0;
}

.result-card {
  width: 100%;
  max-width: 720px;
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.result-header {
  margin-bottom: 20px;
}

.result-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
  padding-bottom: 12px;
  border-bottom: 1px solid #ecf0f1;
}

.result-content p {
  font-size: 16px;
  line-height: 1.8;
  color: #34495e;
  margin: 0 0 20px 0;
}

.error-card {
  width: 100%;
  max-width: 720px;
  background: #fff5f5;
  border: 1px solid #ffe5e5;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
}

.error-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 16px;
}

.error-icon {
  width: 24px;
  height: 24px;
  background: #e74c3c;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 14px;
}

.error-text {
  font-size: 14px;
  color: #c0392b;
}

.retry-btn {
  background: #3498db;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 10px 24px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.retry-btn:hover {
  background: #2980b9;
}

.disclaimer {
  margin-top: 48px;
  padding-top: 24px;
  border-top: 1px solid #e0e0e0;
  text-align: center;
}

.disclaimer p {
  font-size: 13px;
  color: #95a5a6;
  line-height: 1.6;
  margin: 0;
}
</style>

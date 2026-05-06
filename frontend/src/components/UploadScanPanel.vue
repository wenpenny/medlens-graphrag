<script setup lang="ts">
import { ref } from 'vue';

defineProps<{
  loading: boolean;
}>();

const emit = defineEmits<{
  (e: 'scan', file: File): void;
  (e: 'file-select', file: File): void;
}>();

const file = ref<File | null>(null);
const localLoading = ref(false);
const error = ref('');
const fileInputRef = ref<HTMLInputElement | null>(null);

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const selectedFile = target.files?.[0];
  
  if (selectedFile) {
    const validTypes = ['image/jpeg', 'image/png', 'image/jpg'];
    if (!validTypes.includes(selectedFile.type)) {
      error.value = '请上传有效的图片文件 (JPG/PNG)';
      file.value = null;
      return;
    }
    
    file.value = selectedFile;
    error.value = '';
    emit('file-select', selectedFile);
  }
};

const handleDrop = (event: DragEvent) => {
  event.preventDefault();
  const selectedFile = event.dataTransfer?.files?.[0];
  
  if (selectedFile) {
    const validTypes = ['image/jpeg', 'image/png', 'image/jpg'];
    if (!validTypes.includes(selectedFile.type)) {
      error.value = '请上传有效的图片文件 (JPG/PNG)';
      file.value = null;
      return;
    }
    
    file.value = selectedFile;
    error.value = '';
    emit('file-select', selectedFile);
  }
};

const handleDragOver = (event: DragEvent) => {
  event.preventDefault();
};

const handleDropZoneClick = () => {
  if (!file.value && fileInputRef.value) {
    fileInputRef.value.click();
  }
};

const handleScan = async () => {
  if (!file.value) {
    error.value = '请先选择图片文件';
    return;
  }
  
  localLoading.value = true;
  error.value = '';
  
  try {
    emit('scan', file.value);
  } catch (err) {
    error.value = '处理文件时出错';
  } finally {
    localLoading.value = false;
  }
};

const handleClear = () => {
  file.value = null;
  error.value = '';
};

const getObjectUrl = (f: File) => {
  return window.URL.createObjectURL(f);
};
</script>

<template>
  <div class="upload-panel">
    <div class="drop-zone"
      :class="{ 'has-file': file }"
      @drop="handleDrop"
      @dragover="handleDragOver"
      @click="handleDropZoneClick"
    >
      <input
        ref="fileInputRef"
        type="file"
        accept="image/jpeg,image/png,image/jpg"
        @change="handleFileChange"
        class="file-input"
      />
      
      <div v-if="!file" class="drop-zone-content">
        <p>点击上传药品说明书、药盒或医嘱图片</p>
        <p class="upload-hint">支持 JPG、PNG 等图片格式</p>
      </div>
      
      <div v-else class="file-preview">
        <img :src="getObjectUrl(file)" alt="Preview" class="preview-img" />
        <div class="file-info">
          <span class="file-name">{{ file.name }}</span>
          <span class="file-size">{{ (file.size / 1024).toFixed(1) }} KB</span>
        </div>
        <button class="clear-btn" @click.stop="handleClear">
          <span>×</span>
        </button>
      </div>
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <button
      class="scan-btn"
      :disabled="!file || loading || localLoading"
      @click="handleScan"
    >
      <span v-if="loading || localLoading" class="loading-spinner"></span>
      {{ loading || localLoading ? '分析中...' : '开始分析' }}
    </button>

    <button v-if="file" class="reselect-btn" @click="handleClear">
      重新选择
    </button>
  </div>
</template>

<style scoped>
.upload-panel {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.drop-zone {
  border: 2px dashed #ddd;
  border-radius: 10px;
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #fafafa;
}

.drop-zone:hover {
  border-color: #3498db;
  background: #f5f9fc;
}

.drop-zone.has-file {
  border-style: solid;
  border-color: #3498db;
}

.file-input {
  display: none;
}

.drop-zone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.drop-zone-content p {
  margin: 0;
  font-size: 16px;
  color: #34495e;
}

.upload-hint {
  font-size: 13px !important;
  color: #95a5a6 !important;
}

.file-preview {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.preview-img {
  max-width: 100%;
  max-height: 200px;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.file-info {
  display: flex;
  gap: 12px;
  font-size: 13px;
  color: #7f8c8d;
}

.file-name {
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.clear-btn {
  position: absolute;
  top: -10px;
  right: -10px;
  width: 28px;
  height: 28px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 50%;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.error-message {
  margin-top: 16px;
  padding: 12px 14px;
  background: #fff5f5;
  border: 1px solid #ffe5e5;
  border-radius: 8px;
  font-size: 13px;
  color: #c0392b;
  text-align: center;
}

.scan-btn {
  width: 100%;
  margin-top: 16px;
  padding: 14px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  transition: background 0.2s;
}

.scan-btn:hover:not(:disabled) {
  background: #2980b9;
}

.scan-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.reselect-btn {
  width: 100%;
  margin-top: 10px;
  padding: 10px;
  background: transparent;
  color: #7f8c8d;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.reselect-btn:hover {
  border-color: #3498db;
  color: #3498db;
}

.loading-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>

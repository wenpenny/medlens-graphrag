import axios, { AxiosError } from 'axios';
import type { 
  HealthResponse, 
  IndexStatus, 
  UserProfile, 
  ExtractedItem, 
  GraphRAGResult, 
  ScanResult,
  APIError,
  OCRResult,
  ExtractionResult
} from '../types';

const api = axios.create({
  baseURL: '/api',
  timeout: 60000
});

api.interceptors.request.use(
  (config) => {
    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);
    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => {
    console.log(`[API Response] ${response.status} ${response.config.baseURL}${response.config.url}`);
    return response.data;
  },
  (error: AxiosError) => {
    console.error(`[API Error] ${error.message}`);
    if (error.response) {
      console.error(`[API Error Response] Status: ${error.response.status}, Data:`, error.response.data);
    }
    if (error.response?.data) {
      throw error.response.data as APIError;
    }
    throw { 
      code: 'NETWORK_ERROR', 
      message: error.message || '网络请求失败' 
    } as APIError;
  }
);

export async function health(): Promise<HealthResponse> {
  return api.get('/health');
}

export async function getIndexStatus(): Promise<IndexStatus> {
  return api.get('/index/status');
}

export async function buildIndex(force: boolean = true): Promise<Record<string, number | string>> {
  return api.post(`/index/build?force=${force}`);
}

export async function scan(file: File, userProfile: UserProfile): Promise<ScanResult> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('user_profile', JSON.stringify(userProfile));
  return api.post('/scan', formData);
}

export async function graphragQuery(userProfile: UserProfile, extractedItems: ExtractedItem[]): Promise<GraphRAGResult> {
  return api.post('/graphrag/query', {
    user_profile: userProfile,
    extracted_items: extractedItems
  });
}

export async function extractQueryEntities(ocrText: string): Promise<ExtractionResult> {
  return api.post('/extract-query-entities', {
    ocr_text: ocrText
  });
}

export async function ocr(file: File): Promise<OCRResult> {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/ocr', formData);
}
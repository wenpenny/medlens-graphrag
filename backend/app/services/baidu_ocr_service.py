import os
import base64
import requests
from datetime import datetime, timedelta
from app.config import settings
from app.logger import get_logger
from app.exceptions import AppError

logger = get_logger(__name__)

class BaiduOCRService:
    _instance = None
    _access_token = None
    _token_expire_time = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BaiduOCRService, cls).__new__(cls)
        return cls._instance
    
    def _check_config(self):
        if not settings.BAIDU_OCR_API_KEY or not settings.BAIDU_OCR_SECRET_KEY:
            raise AppError(
                status_code=400,
                code="BAIDU_OCR_CONFIG_MISSING",
                message="BAIDU_OCR_API_KEY 或 BAIDU_OCR_SECRET_KEY 未配置"
            )
    
    def get_access_token(self) -> str:
        logger.info("[OCR] requesting access token")
        
        self._check_config()
        
        if self._access_token and self._token_expire_time and datetime.now() < self._token_expire_time:
            logger.info("[OCR] access token loaded from cache")
            return self._access_token
        
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": settings.BAIDU_OCR_API_KEY,
            "client_secret": settings.BAIDU_OCR_SECRET_KEY
        }
        
        try:
            response = requests.post(url, data=params)
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                raise AppError(
                    status_code=400,
                    code="BAIDU_OCR_TOKEN_ERROR",
                    message=f"获取访问令牌失败: {result.get('error_description', '未知错误')}"
                )
            
            self._access_token = result["access_token"]
            expires_in = result.get("expires_in", 30 * 24 * 3600)
            self._token_expire_time = datetime.now() + timedelta(seconds=expires_in)
            
            logger.info("[OCR] access token fetched")
            return self._access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[OCR][ERROR] 请求访问令牌失败: {str(e)}")
            raise AppError(
                status_code=500,
                code="BAIDU_OCR_TOKEN_ERROR",
                message=f"请求访问令牌失败: {str(e)}"
            )
    
    def recognize(self, image_path: str) -> dict:
        logger.info(f"[OCR] start recognize image: {image_path}")
        
        if not os.path.exists(image_path):
            raise AppError(
                status_code=400,
                code="OCR_IMAGE_NOT_FOUND",
                message=f"图片文件不存在: {image_path}"
            )
        
        access_token = self.get_access_token()
        
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")
        
        ocr_mode = settings.BAIDU_OCR_MODE or "accurate_basic"
        if ocr_mode == "accurate_basic":
            endpoint = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"
        else:
            endpoint = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"
        
        url = f"{endpoint}?access_token={access_token}"
        logger.info(f"[OCR] calling baidu endpoint: {endpoint}")
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "image": image_base64,
            "language_type": "CHN_ENG",
            "detect_direction": "true",
            "paragraph": "true"
        }
        
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            result = response.json()
            
            if "error_code" in result:
                error_msg = result.get("error_msg", "未知错误")
                logger.error(f"[OCR][ERROR] {result['error_code']} {error_msg}")
                raise AppError(
                    status_code=400,
                    code="BAIDU_OCR_REQUEST_FAILED",
                    message=f"OCR识别失败: {error_msg}"
                )
            
            words_result = result.get("words_result", [])
            ocr_text = "\n".join(item["words"] for item in words_result)
            words_count = len(words_result)
            text_length = len(ocr_text)
            
            logger.info(f"[OCR] success, words count: {words_count}, text length: {text_length}")
            
            words = [{"text": item["words"], "confidence": 1.0} for item in words_result]
            
            return {
                "source": "baidu_ocr",
                "text": ocr_text,
                "ocr_text": ocr_text,
                "words": words,
                "words_result": words_result,
                "need_manual_input": text_length == 0,
                "confidence": 1.0,
                "raw": result
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[OCR][ERROR] 请求失败: {str(e)}")
            raise AppError(
                status_code=500,
                code="BAIDU_OCR_REQUEST_FAILED",
                message=f"OCR请求失败: {str(e)}"
            )
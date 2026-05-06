import json
import re
import requests
from app.config import settings
from app.logger import get_logger
from app.exceptions import AppError

logger = get_logger(__name__)

class DeepSeekService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DeepSeekService, cls).__new__(cls)
        return cls._instance
    
    def _check_config(self):
        if not settings.DEEPSEEK_API_KEY:
            raise AppError(
                status_code=400,
                code="DEEPSEEK_CONFIG_MISSING",
                message="DEEPSEEK_API_KEY 未配置"
            )
    
    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        logger.info(f"[DeepSeek] request start, model={settings.DEEPSEEK_MODEL}")
        logger.info(f"[DeepSeek] system prompt length: {len(system_prompt)}")
        logger.info(f"[DeepSeek] user prompt length: {len(user_prompt)}")
        
        self._check_config()
        
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        body = {
            "model": settings.DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }
        
        try:
            response = requests.post(url, headers=headers, json=body)
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                error_msg = result.get("error", {}).get("message", "未知错误")
                logger.error(f"[DeepSeek][ERROR] API error: {error_msg}")
                raise AppError(
                    status_code=400,
                    code="DEEPSEEK_REQUEST_FAILED",
                    message=f"DeepSeek API 错误: {error_msg}"
                )
            
            content = result["choices"][0]["message"]["content"]
            logger.info(f"[DeepSeek] response received, content length: {len(content)}")
            
            return content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[DeepSeek][ERROR] 请求失败: {str(e)}")
            raise AppError(
                status_code=500,
                code="DEEPSEEK_REQUEST_FAILED",
                message=f"DeepSeek 请求失败: {str(e)}"
            )
        except KeyError as e:
            logger.error(f"[DeepSeek][ERROR] 响应格式错误: {str(e)}")
            raise AppError(
                status_code=500,
                code="DEEPSEEK_REQUEST_FAILED",
                message=f"DeepSeek 响应格式错误: {str(e)}"
            )
    
    def chat_json(self, system_prompt: str, user_prompt: str) -> dict:
        logger.info(f"[DeepSeek] request start (JSON mode), model={settings.DEEPSEEK_MODEL}")
        logger.info(f"[DeepSeek] system prompt length: {len(system_prompt)}")
        logger.info(f"[DeepSeek] user prompt length: {len(user_prompt)}")
        
        self._check_config()
        
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        body = {
            "model": settings.DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        try:
            response = requests.post(url, headers=headers, json=body)
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                error_msg = result.get("error", {}).get("message", "未知错误")
                logger.error(f"[DeepSeek][ERROR] API error: {error_msg}")
                raise AppError(
                    status_code=400,
                    code="DEEPSEEK_REQUEST_FAILED",
                    message=f"DeepSeek API 错误: {error_msg}"
                )
            
            content = result["choices"][0]["message"]["content"]
            logger.info(f"[DeepSeek] response received, content length: {len(content)}")
            
            cleaned_content = re.sub(r'^```json\s*', '', content)
            cleaned_content = re.sub(r'\s*```$', '', cleaned_content)
            
            try:
                json_result = json.loads(cleaned_content)
                logger.info("[DeepSeek] JSON parsed successfully")
                return json_result
            except json.JSONDecodeError as e:
                logger.error(f"[DeepSeek][ERROR] JSON parse failed: {str(e)}")
                raw_preview = cleaned_content[:1000]
                raise AppError(
                    status_code=500,
                    code="DEEPSEEK_JSON_PARSE_FAILED",
                    message=f"JSON 解析失败: {str(e)}\n原始内容预览: {raw_preview}"
                )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[DeepSeek][ERROR] 请求失败: {str(e)}")
            raise AppError(
                status_code=500,
                code="DEEPSEEK_REQUEST_FAILED",
                message=f"DeepSeek 请求失败: {str(e)}"
            )
        except KeyError as e:
            logger.error(f"[DeepSeek][ERROR] 响应格式错误: {str(e)}")
            raise AppError(
                status_code=500,
                code="DEEPSEEK_REQUEST_FAILED",
                message=f"DeepSeek 响应格式错误: {str(e)}"
            )
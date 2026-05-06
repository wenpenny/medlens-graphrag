import re

DISCLAIMER = "本系统仅用于家庭用药信息解释和风险提示，不能替代医生、药师或医疗机构建议。请勿根据本系统结果自行停药、换药或调整剂量。"

DANGEROUS_PHRASES = [
    "你应该停药",
    "可以停药",
    "自行换药",
    "自行调整剂量",
    "无需咨询医生",
    "一定安全",
    "推荐你服用某药",
]

REPLACEMENT_TEXT = "请咨询医生或药师确认，请勿自行停药、换药或调整剂量。"

def sanitize_medical_output(text: str) -> str:
    for phrase in DANGEROUS_PHRASES:
        text = re.sub(re.escape(phrase), REPLACEMENT_TEXT, text)
    return text
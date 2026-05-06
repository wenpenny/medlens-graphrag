from app.logger import get_logger
from app.exceptions import AppError
from app.services.deepseek_service import DeepSeekService
from app.safety import sanitize_medical_output, DISCLAIMER

logger = get_logger(__name__)

SYSTEM_PROMPT = """你是一位专业的临床药师，但你说话的风格要像家人提醒一样亲切、简单易懂。

你的任务是：基于提供的药品信息和知识库检索结果，为患者生成一段简单、亲切的用药提醒。

重要要求：
1. 只输出一段自然语言，不要分点、列表或表格。
2. 不要提到任何技术术语（如检索、知识库、系统、分析等）。
3. 语言要简单，老人、儿童家长和普通成年人都能看懂。
4. 句子不要太长，控制在80-180个中文字符。
5. 语气要亲切，像家人提醒一样。

必须包含的内容：
- 这是什么药（药品名称）
- 主要用途
- 用法用量（如果有）
- 最重要的风险
- 哪些人用前要先问医生或药师
- 饮食提醒（如果有）
- 最后必须提醒：请按说明书或医嘱使用，不要自己加量、减量、换药或停药

输出格式：
直接输出一段自然语言即可，不要有任何格式标记。

注意事项：
- 如果没有检索到明确的用法用量，输出："系统没有检索到稳定的用法用量，请先看清说明书或问医生/药师。"
- 如果没有明确的联用风险，不要硬编具体药名。
- 如果没有明确的饮食风险，不要硬编"不要喝酒"。
- 如果没有明确的慢病或特殊人群风险，可以使用通用提醒："老人、儿童、孕妇、哺乳期人群，或有慢病、正在吃其他药的人，用前请先问医生或药师。"

禁止出现的表达：
- 你应该停药
- 可以停药
- 自行换药
- 自行调整剂量
- 无需咨询医生
- 一定安全
- 绝对不能吃
- 推荐你服用某药

如果出现这些词，请改成：
- 用前请先问医生或药师
- 请按说明书或医嘱使用
- 不要自己加量、减量、换药或停药
"""

class ReportGenerateService:
    def __init__(self):
        self.deepseek = DeepSeekService()

    def generate(self, user_profile: dict, extracted_items: list, local_context: dict) -> dict:
        logger.info("[Report] start grounded generation")

        risk_paths = local_context.get("graph_context", {}).get("risk_paths", [])
        text_units = local_context.get("text_context", {}).get("vector_text_units", [])
        community_reports = local_context.get("community_context", {}).get("community_reports", [])

        logger.info(f"[Report] risk_paths={len(risk_paths)} text_units={len(text_units)} community_reports={len(community_reports)}")

        drug_name = ""
        generic_name = ""
        indications = []
        dosage = ""

        for item in extracted_items:
            if item.get("drug_name"):
                drug_name = item.get("drug_name")
                generic_name = item.get("generic_name", "")
                indications = item.get("indications", [])
                dosage = item.get("dosage", "")
                break

        if not drug_name:
            logger.error("[Report][ERROR] no drug name identified")
            raise AppError(
                status_code=400,
                code="DRUG_NOT_IDENTIFIED",
                message="未能识别到药品信息"
            )

        risk_info = ""
        risk_drugs = []
        risk_groups = []
        food_reminder = ""

        for path in risk_paths:
            if path.get("relation_type") == "药物相互作用":
                risk_drugs.append(path.get("target", ""))
            elif path.get("relation_type") == "禁忌症":
                risk_groups.append(path.get("target", ""))
            elif path.get("relation_type") == "慎用人群":
                risk_groups.append(path.get("target", ""))
            elif path.get("relation_type") == "饮食禁忌":
                food_reminder = path.get("target", "")

        all_texts = []
        for tu in text_units[:5]:
            all_texts.append(tu.get("text", ""))
        for cr in community_reports[:3]:
            all_texts.append(cr.get("text", ""))

        texts_str = "\n".join(all_texts)

        user_prompt = f"""请帮我生成一段简单的用药提醒，就像家人说话一样亲切。

药品信息：
- 药品名称：{drug_name}（{generic_name}）
- 主要用途：{', '.join(indications)}
- 用法用量：{dosage or '未明确'}

风险信息：
- 药物相互作用：{', '.join(risk_drugs) or '未明确'}
- 慎用人群：{', '.join(risk_groups) or '未明确'}
- 饮食禁忌：{food_reminder or '未明确'}

其他相关信息：
{texts_str}

请按照以下结构生成：
这是【药品名】，主要用于【用途】；用法用量为：【用法用量】。这个药可能【核心风险】，老人、儿童、孕妇、【相关人群】的人，以及正在吃【相关药物】的人，用前请先问医生或药师；【饮食提醒】。请按说明书或医嘱使用，不要自己加量、减量、换药或停药。

注意：
- 如果没有明确的用法用量，直接说"系统没有检索到稳定的用法用量，请先看清说明书或问医生/药师。"
- 如果没有明确的联用风险，不要硬编具体药名
- 如果没有明确的饮食风险，不要硬编"不要喝酒"
- 如果没有明确的人群风险，使用通用提醒
- 不要提到任何技术术语
- 语言要简单、亲切，像家人提醒一样
"""

        logger.info("[Report] calling DeepSeek for report generation...")
        overall_summary = self.deepseek.chat(SYSTEM_PROMPT, user_prompt)
        logger.info("[Report] DeepSeek response received")

        if not overall_summary or not overall_summary.strip():
            logger.error("[Report][ERROR] DeepSeek returned empty response")
            raise AppError(
                status_code=500,
                code="EMPTY_RESPONSE",
                message="生成用药提醒失败：服务未返回有效内容"
            )

        overall_summary = sanitize_medical_output(overall_summary)

        logger.info(f"[Report] DeepSeek report generated")
        logger.info(f"[Report] overall_summary: {overall_summary}")

        return {
            "overall_summary": overall_summary,
            "disclaimer": DISCLAIMER
        }

# yourapp/services/zhipu_client.py
from openai import OpenAI
from django.conf import settings

def get_health_analysis(prompt: str) -> str:
    """调用智谱大模型返回健康分析"""
    if not settings.OPENAI_API_KEY:
        raise ValueError("请先在 .env 中配置 OPENAI_API_KEY。")
    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.ZAI_BASE_URL,
                    timeout=30, max_retries=0)
    resp = client.chat.completions.create(
        model=settings.ZAI_MODEL,
        messages=[
            {"role": "system", "content": "请根据用户提供的身体数据给出专业的健康分析报告。（中文输出）"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    result = resp.choices[0].message.content
    if not result or not result.strip():
        raise ValueError("AI 返回内容为空，请稍后重试。")
    return result.strip()

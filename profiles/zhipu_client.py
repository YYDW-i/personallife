# yourapp/services/zhipu_client.py
from openai import OpenAI
from config import settings

_client = OpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.ZAI_BASE_URL,
)

def get_health_analysis(prompt: str) -> str:
    """调用智谱大模型返回健康分析"""
    resp = _client.chat.completions.create(
        model=settings.ZAI_MODEL,
        messages=[
            {"role": "system", "content": "请根据用户提供的身体数据给出专业的健康分析报告。（中文输出）"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    return resp.choices[0].message.content

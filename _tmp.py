from pathlib import Path

import openai
from dotenv import dotenv_values

config = dotenv_values(Path(__file__).with_name(".env"))
key = config.get("OPENAI_API_KEY")
model = config.get("OPENAI_MODEL")

if not key or not model:
    raise SystemExit(".env 缺少 OPENAI_API_KEY 或 OPENAI_MODEL")

try:
    with openai.OpenAI(
        api_key=key,
        base_url="https://api.openai.com/v1",
        max_retries=0,  # 不自动重试，只调用一次
        timeout=30,
    ) as client:
        response = client.responses.create(
            model=model,
            input="Reply with OK only.",
            max_output_tokens=64,
        )
    print("调用成功：当前 key 可以访问该模型。")
    print("模型：", model)
    print("回复：", response.output_text or "无文本输出，可能达到输出上限")

except openai.AuthenticationError:
    print("认证失败：key 无效、已撤销或填写错误，不能仅判断为过期。")
except openai.RateLimitError:
    print("请求受限：检查账户额度、余额或请求频率。")
except openai.APIConnectionError:
    print("连接失败或超时：检查网络、代理。")
except openai.APIStatusError as e:
    print(f"调用失败：HTTP {e.status_code}，错误代码：{e.code}")
    print("请检查模型名称、访问权限及请求参数。")
import os
from dataclasses import dataclass

import httpx
from fastapi import HTTPException


@dataclass
class Completion:
    content: str
    input_tokens: int
    output_tokens: int


class PlatformModel:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def complete(self, purpose: str, prompt: str) -> Completion:
        instruction = (
            "只返回一条 DuckDB SELECT。"
            if purpose == "sql"
            else "用三句中文回答：结论、数据支撑、建议。数字必须来自给出的结果。"
        )
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        usage = body.get("usage") or {}
        return Completion(
            content=body["choices"][0]["message"]["content"].strip(),
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
        )


def model_for_user(cipher: str, fallback: PlatformModel) -> PlatformModel:
    from app.secrets import decrypt_secret

    return PlatformModel(
        decrypt_secret(cipher),
        fallback.base_url,
        fallback.model,
    )


def current_prices() -> tuple[float, float]:
    return (
        float(os.environ.get("MODEL_INPUT_PRICE", "0")),
        float(os.environ.get("MODEL_OUTPUT_PRICE", "0")),
    )


def get_model() -> PlatformModel:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=503, detail="未配置平台密钥")
    return PlatformModel(
        api_key,
        os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
    )

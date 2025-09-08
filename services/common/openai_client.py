import os, json, re
from typing import Any, Dict, List
from openai import OpenAI

def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    return OpenAI(api_key=api_key)

def get_model(default="gpt-4o-mini"):
    return os.getenv("OPENAI_MODEL", default)

def extract_json(text: str) -> Dict[str, Any]:
    """
    Attempts to extract the first JSON object from a response.
    Works if the model wraps JSON in ```json ... ``` or plain.
    """
    # fenced
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S)
    if m:
        return json.loads(m.group(1))
    # first object
    m = re.search(r"(\{.*\})", text, re.S)
    if m:
        return json.loads(m.group(1))
    # otherwise try direct parse
    return json.loads(text)

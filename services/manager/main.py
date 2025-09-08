import os
from fastapi import FastAPI, Body
from openai import OpenAI

app = FastAPI(title="Manager Agent")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model  = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

@app.post("/decide")
def decide(body: dict = Body(...)):
    symbol   = body.get("symbol", "AAPL")
    ideas    = body.get("ideas", [])
    insights = body.get("insights", "")
    prompt = f"""Given the ideas {ideas} and insights {insights},
decide whether to BUY, SELL, or HOLD {symbol}.
Return JSON with fields: side, qty (1-10), confidence (0-1)."""
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    return {"symbol": symbol, "decision": resp.choices[0].message.content}

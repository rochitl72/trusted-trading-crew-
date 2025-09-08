import os
from fastapi import FastAPI, Body
from openai import OpenAI

app = FastAPI(title="Researcher Agent")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model  = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

@app.post("/insights")
def insights(body: dict = Body(...)):
    symbol = body.get("symbol", "AAPL")
    prompt = f"Provide recent market research insights for {symbol} in 3 bullet points."
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    return {"symbol": symbol, "insights": resp.choices[0].message.content}

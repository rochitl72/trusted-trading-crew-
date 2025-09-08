import os
from fastapi import FastAPI, Body
from openai import OpenAI

app = FastAPI(title="Analyst Agent")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model  = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

@app.post("/ideas")
def ideas(body: dict = Body(None)):
    symbols = body.get("symbols", ["AAPL", "MSFT", "TSLA"])
    prompt = f"Rate these stocks from -1 (strong sell) to +1 (strong buy) with a short rationale: {symbols}"
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    text = resp.choices[0].message.content
    ideas = [{"symbol": s, "score": 0.0, "rationale": text} for s in symbols]
    return {"ideas": ideas}

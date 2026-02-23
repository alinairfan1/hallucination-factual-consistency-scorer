from fastapi import FastAPI

app = FastAPI(title="Hallucination / Factual-Consistency Scorer")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

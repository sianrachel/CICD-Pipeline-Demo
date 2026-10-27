from fastapi import FastAPI

app = FastAPI()


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/scenarios")
def scenarios():
    return ["roundabout-merge", "unprotected-right-turn"]

from fastapi import FastAPI
import torch, random

app = FastAPI()

@app.post("/predict")
async def predict():
    # predicción dummy: media de tensor + número aleatorio
    val = torch.randn(1).mean().item() + random.random()
    return {"prediction": round(val, 4)}

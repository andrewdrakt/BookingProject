from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI()

class ServoCommand(BaseModel):
    status: int
    ip: str

@app.post("/servo")
async def control_servo(command: ServoCommand):
    if command.status not in [0, 1, 2]:
        raise HTTPException(status_code=400, detail="Неверная команда")
    target_url = f"http://{command.ip}/servo"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(target_url, json={"status": command.status})
            response.raise_for_status()
            text = response.text
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Ошибка подключения к ESP: {e}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=500, detail=f"ESP вернул ошибку: {e.response.status_code}")

    return {"message": "Команда отправлена успешно", "esp_response": text}

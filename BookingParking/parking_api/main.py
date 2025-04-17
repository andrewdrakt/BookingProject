from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI()
ESP32_URL = "http://192.168.1.8/control"

class ServoCommand(BaseModel):
    status: int

@app.post("/servo")
async def control_servo(command: ServoCommand):
    if command.status not in [0, 1]:
        raise HTTPException(status_code=400, detail="Неверная команда")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(ESP32_URL, json={"status": command.status})
            response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка отправки команды на устройство: {e}")
    return {"message": "Команда отправлена успешно"}

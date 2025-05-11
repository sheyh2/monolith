from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from datetime import datetime
import os
from db_manager import DatabaseManager

app = FastAPI()

# Настройка БД (замени на свои значения)
# Initialize database connection
db_manager = DatabaseManager(
    dbname="mvp_db",
    user="mvp",
    password="123",
    host="localhost",
    port=5432
)

# Папка для сохранения кадров
UPLOAD_FOLDER = "loaded_frames"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.post("/upload-frame/")
async def upload_frame(file: UploadFile = File(...)):
    try:
        # Сохраняем файл
        timestamp = datetime.utcnow()
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S_%f')}_{file.filename}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Сохраняем в БД
        frame_id = db_manager.insert_frame(file_path, timestamp)
        if frame_id is None:
            return JSONResponse(status_code=500, content={"error": "Failed to save frame in database"})

        return {"id": frame_id, "filename": filename, "timestamp": timestamp.isoformat()}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

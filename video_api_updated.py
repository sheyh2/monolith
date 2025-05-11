import tempfile
import os
import cv2
import base64
import numpy as np
from io import BytesIO
from PIL import Image
from fastapi import APIRouter, UploadFile, File, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException, Query, \
    Depends
from typing import List, Dict, Any, Optional
import asyncio
import json
from pydantic import BaseModel
import logging
from datetime import datetime, date

# Импортируем классы из main.py
from main import FaceProcessor, DatabaseManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Создаем один экземпляр DatabaseManager и FaceProcessor для повторного использования
db_manager = DatabaseManager(
        dbname="mvp_db",
        user="mvp",
        password="123",
        host="localhost",
        port=5432
    )
data_path = os.getenv("FACE_DATA_PATH", "face/model/face_id/data_face/")
face_processor = FaceProcessor(db_manager, recognition_attempts=3, data_path=data_path)

# Создаем маршрутизатор для видео-API
video_router = APIRouter(prefix="/api/video", tags=["video"])

# Временное хранилище для информации о задачах обработки видео
video_tasks = {}


class VideoProcessingStatus(BaseModel):
    task_id: str
    status: str
    progress: float = 0
    processed_frames: int = 0
    total_frames: int = 0
    faces_detected: int = 0


class InitTaskRequest(BaseModel):
    total_frames: int


class FrameData(BaseModel):
    frame_number: int
    frame_data: str  # Base64 encoded image


@video_router.post("/init-task", response_model=Dict[str, Any])
async def init_task(request: InitTaskRequest):
    """
    Инициализация задачи обработки видео
    """
    try:
        # Генерируем ID задачи
        task_id = f"task_{len(video_tasks) + 1}"

        # Инициализируем статус задачи
        video_tasks[task_id] = {
            "status": "initialized",
            "progress": 0,
            "processed_frames": 0,
            "total_frames": request.total_frames,
            "faces_detected": 0,
            "frames": {}
        }

        return {
            "task_id": task_id,
            "message": "Задача инициализирована",
            "status": "initialized"
        }

    except Exception as e:
        logger.error(f"Ошибка при инициализации задачи: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при инициализации задачи: {str(e)}")


@video_router.post("/frame/{task_id}", response_model=Dict[str, Any])
async def process_frame(task_id: str, frame_data: FrameData, background_tasks: BackgroundTasks):
    """
    Обработка одного кадра видео
    """
    if task_id not in video_tasks:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    try:
        # Обновляем статус
        video_tasks[task_id]["status"] = "processing"

        # Декодируем данные кадра из base64
        image_data = frame_data.frame_data.split(',')[1] if ',' in frame_data.frame_data else frame_data.frame_data
        image_bytes = base64.b64decode(image_data)

        # Сохраняем кадр во временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(image_bytes)
            frame_path = temp_file.name

        # Добавляем задачу обработки кадра в фоновые задачи
        background_tasks.add_task(process_frame_task, task_id, frame_data.frame_number, frame_path)

        # Обновляем счетчик обработанных кадров
        video_tasks[task_id]["processed_frames"] += 1

        # Вычисляем прогресс
        total_frames = video_tasks[task_id]["total_frames"]
        progress = (video_tasks[task_id]["processed_frames"] / total_frames) * 100
        video_tasks[task_id]["progress"] = progress

        return {
            "task_id": task_id,
            "frame_number": frame_data.frame_number,
            "status": "processing",
            "progress": progress
        }

    except Exception as e:
        logger.error(f"Ошибка при обработке кадра: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке кадра: {str(e)}")


async def process_frame_task(task_id: str, frame_number: int, frame_path: str):
    """
    Фоновая задача для обработки кадра
    """
    try:
        # Загружаем кадр
        frame = cv2.imread(frame_path)

        # Обрабатываем кадр
        processed_frame = face_processor.process_frame(frame, output=False)

        # Обновляем статистику
        faces_in_frame = len([id for id in face_processor.track_metadata])
        video_tasks[task_id]["faces_detected"] += faces_in_frame

        # Сохраняем результаты обработки кадра
        video_tasks[task_id]["frames"][frame_number] = {
            "processed": True,
            "faces_detected": faces_in_frame
        }

        # Удаляем временный файл
        try:
            os.unlink(frame_path)
        except Exception as e:
            logger.warning(f"Не удалось удалить временный файл {frame_path}: {str(e)}")

    except Exception as e:
        logger.error(f"Ошибка при обработке кадра {frame_number}: {str(e)}", exc_info=True)
        video_tasks[task_id]["frames"][frame_number] = {
            "processed": False,
            "error": str(e)
        }


@video_router.post("/complete-task/{task_id}", response_model=Dict[str, Any])
async def complete_task(task_id: str):
    """
    Завершение задачи обработки видео
    """
    if task_id not in video_tasks:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    try:
        # Обновляем статус задачи
        video_tasks[task_id]["status"] = "completed"
        video_tasks[task_id]["progress"] = 100

        return {
            "task_id": task_id,
            "status": "completed",
            "message": "Обработка видео завершена",
            "processed_frames": video_tasks[task_id]["processed_frames"],
            "total_frames": video_tasks[task_id]["total_frames"],
            "faces_detected": video_tasks[task_id]["faces_detected"]
        }

    except Exception as e:
        logger.error(f"Ошибка при завершении задачи: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при завершении задачи: {str(e)}")


@video_router.post("/upload", response_model=Dict[str, Any])
async def upload_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Загрузка видео для обработки
    """
    try:
        # Создаем временный файл для сохранения видео
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            temp_file.write(await file.read())
            temp_path = temp_file.name

        # Генерируем ID задачи
        task_id = f"task_{len(video_tasks) + 1}"

        # Инициализируем статус задачи
        video_tasks[task_id] = {
            "status": "queued",
            "progress": 0,
            "file_path": temp_path,
            "processed_frames": 0,
            "total_frames": 0,
            "faces_detected": 0
        }

        # Добавляем задачу в фоновые задачи
        background_tasks.add_task(process_video, task_id, temp_path)

        return {
            "task_id": task_id,
            "message": "Видео успешно загружено и поставлено в очередь на обработку",
            "status": "queued"
        }

    except Exception as e:
        logger.error(f"Ошибка при загрузке видео: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке видео: {str(e)}")


@video_router.get("/status/{task_id}", response_model=VideoProcessingStatus)
async def get_processing_status(task_id: str):
    """
    Получить статус обработки видео
    """
    if task_id not in video_tasks:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    task_info = video_tasks[task_id]

    return VideoProcessingStatus(
        task_id=task_id,
        status=task_info["status"],
        progress=task_info["progress"],
        processed_frames=task_info["processed_frames"],
        total_frames=task_info["total_frames"],
        faces_detected=task_info["faces_detected"]
    )


async def process_video(task_id: str, video_path: str):
    """
    Функция для обработки видео в фоновом режиме
    """
    try:
        # Обновляем статус
        video_tasks[task_id]["status"] = "processing"

        # Открываем видео файл
        cap = cv2.VideoCapture(video_path)

        # Получаем общее количество кадров
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_tasks[task_id]["total_frames"] = total_frames

        # Для каждого кадра
        frame_count = 0
        faces_detected = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Обрабатываем кадр без вывода (output=False)
            processed_frame = face_processor.process_frame(frame, output=False)

            # Обновляем статистику
            frame_count += 1
            faces_in_frame = len([id for id in face_processor.track_metadata])
            faces_detected += faces_in_frame

            # Обновляем информацию о прогрессе
            video_tasks[task_id]["processed_frames"] = frame_count
            video_tasks[task_id]["faces_detected"] = faces_detected
            video_tasks[task_id]["progress"] = (frame_count / total_frames) * 100

            # Не обрабатываем все кадры для оптимизации
            if frame_count % 5 != 0:  # Обрабатываем каждый 5-й кадр
                continue

        # Освобождаем ресурсы
        cap.release()

        # Удаляем временный файл
        try:
            os.unlink(video_path)
        except Exception as e:
            logger.warning(f"Не удалось удалить временный файл {video_path}: {str(e)}")

        # Обновляем статус задачи
        video_tasks[task_id]["status"] = "completed"
        video_tasks[task_id]["progress"] = 100

    except Exception as e:
        logger.error(f"Ошибка при обработке видео: {str(e)}", exc_info=True)
        video_tasks[task_id]["status"] = "error"
        video_tasks[task_id]["error_message"] = str(e)


@video_router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint для получения обновлений статуса обработки видео в реальном времени
    """
    await websocket.accept()

    if task_id not in video_tasks:
        await websocket.send_json({"error": "Задача не найдена"})
        await websocket.close()
        return

    try:
        # Отправляем обновления статуса каждую секунду
        while True:
            if task_id not in video_tasks:
                await websocket.close()
                break

            task_info = video_tasks[task_id]

            # Формируем данные для отправки
            data = {
                "task_id": task_id,
                "status": task_info["status"],
                "progress": task_info["progress"],
                "processed_frames": task_info["processed_frames"],
                "total_frames": task_info["total_frames"],
                "faces_detected": task_info["faces_detected"]
            }

            # Отправляем данные
            await websocket.send_json(data)

            # Если задача завершена или произошла ошибка, закрываем соединение
            if task_info["status"] in ["completed", "error"]:
                await asyncio.sleep(5)  # Ждем 5 секунд, чтобы клиент успел получить финальный статус
                await websocket.close()
                break

            await asyncio.sleep(1)  # Обновление каждую секунду

    except WebSocketDisconnect:
        # Клиент отключился
        pass
    except Exception as e:
        logger.error(f"Ошибка WebSocket: {str(e)}", exc_info=True)
        if websocket.client_state == WebSocket.CLIENT_STATE_CONNECTED:
            await websocket.send_json({"error": str(e)})
            await websocket.close()


# --- НОВЫЕ ЭНДПОИНТЫ ДЛЯ ДАШБОРДА ---

class FrameDataResponse(BaseModel):
    faces: List[Dict[str, Any]]


@video_router.get("/frame-data", response_model=FrameDataResponse)
async def get_frame_data(frame_id: int):
    """
    Получить данные для указанного кадра
    """
    try:
        # Получаем данные о лицах из базы данных для указанного кадра
        faces_data = db_manager.get_faces_by_frame_id(frame_id)

        return {"faces": faces_data}

    except Exception as e:
        logger.error(f"Ошибка при получении данных кадра: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении данных кадра: {str(e)}")


# Создаем маршрутизатор для статистики
stats_router = APIRouter(prefix="/api/stats", tags=["statistics"])


class DateRangeParams:
    def __init__(
            self,
            start_date: Optional[date] = Query(None),
            end_date: Optional[date] = Query(None),
            person_type: Optional[str] = Query(None),
            max_frame_id: Optional[int] = Query(None),
            task_id: Optional[str] = Query(None)
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.person_type = person_type
        self.max_frame_id = max_frame_id
        self.task_id = task_id


@stats_router.get("/overall")
async def get_overall_stats(params: DateRangeParams = Depends()):
    """
    Получить общую статистику
    """
    try:
        # Получаем данные из базы с учетом фильтров
        stats = db_manager.get_overall_stats(
            start_date=params.start_date,
            end_date=params.end_date,
            person_type=params.person_type,
            max_frame_id=params.max_frame_id,
            task_id=params.task_id
        )

        return stats

    except Exception as e:
        logger.error(f"Ошибка при получении общей статистики: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении общей статистики: {str(e)}")


@stats_router.get("/timeseries")
async def get_timeseries_stats(params: DateRangeParams = Depends()):
    """
    Получить статистику временного ряда
    """
    try:
        # Получаем данные из базы с учетом фильтров
        stats = db_manager.get_timeseries_stats(
            start_date=params.start_date,
            end_date=params.end_date,
            person_type=params.person_type,
            max_frame_id=params.max_frame_id
        )

        return {"data": stats}

    except Exception as e:
        logger.error(f"Ошибка при получении статистики временного ряда: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении статистики временного ряда: {str(e)}")


@stats_router.get("/emotions")
async def get_emotions_stats(params: DateRangeParams = Depends()):
    """
    Получить статистику эмоций
    """
    try:
        # Получаем данные из базы с учетом фильтров
        stats = db_manager.get_emotions_stats(
            start_date=params.start_date,
            end_date=params.end_date,
            person_type=params.person_type,
            max_frame_id=params.max_frame_id
        )

        return {"emotions": stats}

    except Exception as e:
        logger.error(f"Ошибка при получении статистики эмоций: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении статистики эмоций: {str(e)}")


@stats_router.get("/peak-hours")
async def get_peak_hours_stats(params: DateRangeParams = Depends()):
    """
    Получить статистику пиковых часов
    """
    try:
        # Получаем данные из базы с учетом фильтров
        stats = db_manager.get_peak_hours_stats(
            start_date=params.start_date,
            end_date=params.end_date,
            person_type=params.person_type,
            max_frame_id=params.max_frame_id
        )

        return {"hours": stats}

    except Exception as e:
        logger.error(f"Ошибка при получении статистики пиковых часов: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении статистики пиковых часов: {str(e)}")


@stats_router.get("/demographics")
async def get_demographics_stats(params: DateRangeParams = Depends()):
    """
    Получить демографическую статистику
    """
    try:
        # Получаем данные из базы с учетом фильтров
        gender_stats = db_manager.get_gender_stats(
            start_date=params.start_date,
            end_date=params.end_date,
            person_type=params.person_type,
            max_frame_id=params.max_frame_id
        )

        age_stats = db_manager.get_age_stats(
            start_date=params.start_date,
            end_date=params.end_date,
            person_type=params.person_type,
            max_frame_id=params.max_frame_id
        )

        return {
            "gender": gender_stats,
            "age_groups": age_stats
        }

    except Exception as e:
        logger.error(f"Ошибка при получении демографической статистики: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении демографической статистики: {str(e)}")


@stats_router.get("/frame")
async def get_frame_stats(params: DateRangeParams = Depends()):
    """
    Получить статистику до указанного кадра
    """
    try:
        # Проверяем, что указан max_frame_id
        if not params.max_frame_id:
            raise HTTPException(status_code=400, detail="Необходимо указать max_frame_id")

        # Получаем данные из базы с учетом фильтров
        stats = db_manager.get_frame_stats(
            max_frame_id=params.max_frame_id,
            task_id=params.task_id,
            person_type=params.person_type
        )

        return stats

    except Exception as e:
        logger.error(f"Ошибка при получении статистики по кадру: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении статистики по кадру: {str(e)}")


@stats_router.get("/age-distribution")
async def get_age_distribution(params: DateRangeParams = Depends()):
    """
    Получить распределение по возрасту
    """
    try:
        # Получаем данные из базы с учетом фильтров
        stats = db_manager.get_age_stats(
            start_date=params.start_date,
            end_date=params.end_date,
            person_type=params.person_type,
            max_frame_id=params.max_frame_id
        )

        return {"age_groups": stats}

    except Exception as e:
        logger.error(f"Ошибка при получении распределения по возрасту: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении распределения по возрасту: {str(e)}")


@stats_router.get("/gender-distribution")
async def get_gender_distribution(params: DateRangeParams = Depends()):
    """
    Получить распределение по полу
    """
    try:
        # Получаем данные из базы с учетом фильтров
        stats = db_manager.get_gender_stats(
            start_date=params.start_date,
            end_date=params.end_date,
            person_type=params.person_type,
            max_frame_id=params.max_frame_id
        )

        return {"gender": stats}

    except Exception as e:
        logger.error(f"Ошибка при получении распределения по полу: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении распределения по полу: {str(e)}")


@stats_router.get("/visitor-trends")
async def get_visitor_trends(params: DateRangeParams = Depends()):
    """
    Получить тренды посещений
    """
    try:
        # Получаем данные из базы с учетом фильтров
        stats = db_manager.get_visitor_trends(
            start_date=params.start_date,
            end_date=params.end_date,
            person_type=params.person_type,
            max_frame_id=params.max_frame_id
        )

        return {"trends": stats}

    except Exception as e:
        logger.error(f"Ошибка при получении трендов посещений: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении трендов посещений: {str(e)}")


@stats_router.get("/top-visitors")
async def get_top_visitors(params: DateRangeParams = Depends()):
    """
    Получить топ посетителей
    """
    try:
        # Получаем данные из базы с учетом фильтров
        stats = db_manager.get_top_visitors(
            start_date=params.start_date,
            end_date=params.end_date,
            person_type=params.person_type,
            max_frame_id=params.max_frame_id
        )

        return {"visitors": stats}

    except Exception as e:
        logger.error(f"Ошибка при получении топ посетителей: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении топ посетителей: {str(e)}")


@stats_router.get("/visit-duration")
async def get_visit_duration(params: DateRangeParams = Depends()):
    """
    Получить продолжительность визитов
    """
    try:
        # Получаем данные из базы с учетом фильтров
        stats = db_manager.get_visit_duration(
            start_date=params.start_date,
            end_date=params.end_date,
            person_type=params.person_type,
            max_frame_id=params.max_frame_id
        )

        return {"duration_groups": stats}

    except Exception as e:
        logger.error(f"Ошибка при получении продолжительности визитов: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении продолжительности визитов: {str(e)}")


@stats_router.get("/peak-hours-detailed")
async def get_peak_hours_detailed(params: DateRangeParams = Depends()):
    """
    Получить детальные данные о пиковых часах
    """
    try:
        # Получаем данные из базы с учетом фильтров
        stats = db_manager.get_peak_hours_detailed(
            start_date=params.start_date,
            end_date=params.end_date,
            person_type=params.person_type,
            max_frame_id=params.max_frame_id
        )

        return {"hourly_data": stats}

    except Exception as e:
        logger.error(f"Ошибка при получении детальных данных о пиковых часах: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении детальных данных о пиковых часах: {str(e)}")


@stats_router.get("/waiters")
async def get_waiters_stats(params: DateRangeParams = Depends()):
    """
    Получить статистику официантов
    """
    try:
        # Получаем данные из базы с учетом фильтров
        stats = db_manager.get_waiters_stats(
            start_date=params.start_date,
            end_date=params.end_date,
            max_frame_id=params.max_frame_id
        )

        return {"waiters": stats}

    except Exception as e:
        logger.error(f"Ошибка при получении статистики официантов: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении статистики официантов: {str(e)}")


@stats_router.get("/waiter-load")
async def get_waiter_load(params: DateRangeParams = Depends()):
    """
    Получить данные о нагрузке официантов
    """
    try:
        # Получаем данные из базы с учетом фильтров
        stats = db_manager.get_waiter_load(
            start_date=params.start_date,
            end_date=params.end_date,
            max_frame_id=params.max_frame_id
        )

        return {"waiters": stats}

    except Exception as e:
        logger.error(f"Ошибка при получении данных о нагрузке официантов: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении данных о нагрузке официантов: {str(e)}")


@stats_router.get("/waiter-efficiency")
async def get_waiter_efficiency(params: DateRangeParams = Depends()):
    """
    Получить данные об эффективности официантов
    """
    try:
        # Получаем данные из базы с учетом фильтров
        stats = db_manager.get_waiter_efficiency(
            start_date=params.start_date,
            end_date=params.end_date,
            max_frame_id=params.max_frame_id
        )

        return {"waiters": stats}

    except Exception as e:
        logger.error(f"Ошибка при получении данных об эффективности официантов: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500,
                            detail=f"Ошибка при получении данных об эффективности официантов: {str(e)}")


@stats_router.get("/celebrity-impact")
async def get_celebrity_impact(params: DateRangeParams = Depends()):
    """
    Получить данные о влиянии знаменитостей
    """
    try:
        # Получаем данные из базы с учетом фильтров
        stats = db_manager.get_celebrity_impact(
            start_date=params.start_date,
            end_date=params.end_date,
            max_frame_id=params.max_frame_id
        )

        return {"timeline": stats}

    except Exception as e:
        logger.error(f"Ошибка при получении данных о влиянии знаменитостей: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении данных о влиянии знаменитостей: {str(e)}")


@stats_router.get("/celebrity-visits")
async def get_celebrity_visits(params: DateRangeParams = Depends()):
    """
    Получить данные о визитах знаменитостей
    """
    try:
        # Получаем данные из базы с учетом фильтров
        stats = db_manager.get_celebrity_visits(
            start_date=params.start_date,
            end_date=params.end_date,
            max_frame_id=params.max_frame_id
        )

        return {"visits": stats}

    except Exception as e:
        logger.error(f"Ошибка при получении данных о визитах знаменитостей: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении данных о визитах знаменитостей: {str(e)}")


@stats_router.get("/satisfaction-correlation")
async def get_satisfaction_correlation(params: DateRangeParams = Depends()):
    """
    Получить данные о корреляции эмоций с удовлетворенностью
    """
    try:
        # Получаем данные из базы с учетом фильтров
        stats, correlation_coefficient = db_manager.get_satisfaction_correlation(
            start_date=params.start_date,
            end_date=params.end_date,
            person_type=params.person_type,
            max_frame_id=params.max_frame_id
        )

        return {
            "correlation": stats,
            "correlation_coefficient": correlation_coefficient
        }

    except Exception as e:
        logger.error(f"Ошибка при получении данных о корреляции: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении данных о корреляции: {str(e)}")


@stats_router.get("/period-comparison")
async def get_period_comparison(
        period1_start: date,
        period1_end: date,
        period2_start: date,
        period2_end: date,
        person_type: Optional[str] = Query(None)
):
    """
    Получить данные для сравнения двух периодов
    """
    try:
        # Получаем данные для первого периода
        period1_stats = db_manager.get_period_stats(
            start_date=period1_start,
            end_date=period1_end,
            person_type=person_type
        )

        # Получаем данные для второго периода
        period2_stats = db_manager.get_period_stats(
            start_date=period2_start,
            end_date=period2_end,
            person_type=person_type
        )

        return {
            "period1": period1_stats,
            "period2": period2_stats
        }

    except Exception as e:
        logger.error(f"Ошибка при получении данных для сравнения периодов: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении данных для сравнения периодов: {str(e)}")


# Функция для интеграции с основным приложением FastAPI
def register_api_routers(app):
    """
    Регистрирует маршрутизаторы API в основном приложении FastAPI.
    Вызовите эту функцию в файле main.py при создании приложения FastAPI.

    Пример использования:
    ```python
    from fastapi import FastAPI
    from video_api import register_api_routers

    app = FastAPI()
    register_api_routers(app)
    ```
    """
    app.include_router(video_router)
    app.include_router(stats_router)


# Если файл запущен напрямую, создаем тестовое приложение
if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI

    app = FastAPI(title="Restaurant Analytics API")
    register_api_routers(app)

    print("Запуск тестового сервера API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
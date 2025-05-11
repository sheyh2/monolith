from fastapi import FastAPI, HTTPException, Query, Depends, UploadFile, File, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import cv2
from dotenv import load_dotenv
import pandas as pd
from dateutil.relativedelta import relativedelta
import json
import logging
import asyncio
import tempfile

# Импортируем классы из main.py
from main import FaceProcessor, DatabaseManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Загрузка конфигурации из .env файла
load_dotenv()

# Константы для типов людей
PERSON_TYPE_CUSTOMER = 'customer'
PERSON_TYPE_WAITER = 'waiter'
PERSON_TYPE_CELEBRITY = 'celebrity'

# Временное хранилище для информации о задачах обработки видео
video_tasks = {}

# Модель для статуса обработки видео
class VideoProcessingStatus(BaseModel):
    task_id: str
    status: str
    progress: float = 0
    processed_frames: int = 0
    total_frames: int = 0
    faces_detected: int = 0

app = FastAPI(title="Restaurant Analytics API",
              description="API для получения статистических данных по распознанным людям в ресторане",
              version="1.0.0")

# Настройка CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшн стоит указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Параметры подключения к БД
db_config = {
    "dbname": os.getenv("DB_NAME", "restaurant_analytics"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}

# Функция для получения соединения с БД
def get_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(**db_config, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {str(e)}", exc_info=True)
        if conn is not None:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Ошибка подключения к базе данных: {str(e)}")

# Модели данных
class VisitorsStats(BaseModel):
    total_visitors: int
    unique_visitors: int
    return_visitors: int
    average_age: Optional[float] = None
    gender_distribution: Dict[str, int]
    emotion_distribution: Dict[str, int]
    person_type_distribution: Dict[str, int]

class TimeSeriesData(BaseModel):
    timestamp: datetime
    value: int

class VisitorTimeSeries(BaseModel):
    daily: List[TimeSeriesData]
    weekly: List[TimeSeriesData]
    monthly: List[TimeSeriesData]

class AgeGroupDistribution(BaseModel):
    age_groups: Dict[str, int]

class TopVisitors(BaseModel):
    name: str
    visit_count: int
    last_visit: datetime
    average_emotion: Optional[str] = None

# Тестовый маршрут для проверки подключения к БД
@app.get("/api/test-db-connection")
def test_db_connection():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        return {"status": "success", "message": "Подключение к БД работает корректно"}
    except Exception as e:
        logger.error(f"Ошибка проверки подключения к БД: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка подключения к БД: {str(e)}")
    finally:
        if conn is not None:
            conn.close()

# Маршруты API
@app.get("/", response_model=Dict[str, str])
def read_root():
    return {"message": "Restaurant Analytics API работает"}

@app.get("/api/stats/emotion-by-demographics", response_model=Dict[str, Dict[str, Dict[str, int]]])
def get_emotion_by_demographics(
        start_date: Optional[datetime] = Query(None, description="Начальная дата для фильтрации (YYYY-MM-DD)"),
        end_date: Optional[datetime] = Query(None, description="Конечная дата для фильтрации (YYYY-MM-DD)"),
        person_type: Optional[str] = Query(None, description="Тип человека (customer, waiter, celebrity)")
):
    """
    Получить распределение эмоций по демографическим показателям
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # По полу
        gender_query = """
        SELECT 
            gender,
            emotion,
            COUNT(*) as count
        FROM detected_id
        WHERE gender IS NOT NULL AND emotion IS NOT NULL
        """

        params = []

        if start_date:
            gender_query += " AND timestamp >= %s"
            params.append(start_date)

        if end_date:
            gender_query += " AND timestamp <= %s"
            params.append(end_date)

        if person_type:
            gender_query += " AND person_type = %s"
            params.append(person_type)

        gender_query += " GROUP BY gender, emotion ORDER BY gender, emotion"

        cursor.execute(gender_query, params)
        gender_results = cursor.fetchall()

        # По возрастным группам
        age_query = """
        SELECT 
            CASE 
                WHEN age < 18 THEN '<18'
                WHEN age BETWEEN 18 AND 24 THEN '18-24'
                WHEN age BETWEEN 25 AND 34 THEN '25-34'
                WHEN age BETWEEN 35 AND 44 THEN '35-44'
                WHEN age BETWEEN 45 AND 54 THEN '45-54'
                WHEN age BETWEEN 55 AND 64 THEN '55-64'
                WHEN age >= 65 THEN '65+'
                ELSE 'Unknown'
            END as age_group,
            emotion,
            COUNT(*) as count
        FROM detected_id
        WHERE age IS NOT NULL AND emotion IS NOT NULL
        """

        if start_date:
            age_query += " AND timestamp >= %s"

        if end_date:
            age_query += " AND timestamp <= %s"

        if person_type:
            age_query += " AND person_type = %s"

        age_query += " GROUP BY age_group, emotion ORDER BY age_group, emotion"

        cursor.execute(age_query, params)
        age_results = cursor.fetchall()

        # Преобразуем результаты в формат для вывода
        gender_emotions = {}
        for row in gender_results:
            gender = row["gender"]
            emotion = row["emotion"]
            count = row["count"]

            if gender not in gender_emotions:
                gender_emotions[gender] = {}

            gender_emotions[gender][emotion] = count

        age_emotions = {}
        for row in age_results:
            age_group = row["age_group"]
            emotion = row["emotion"]
            count = row["count"]

            if age_group not in age_emotions:
                age_emotions[age_group] = {}

            age_emotions[age_group][emotion] = count

        return {
            "by_gender": gender_emotions,
            "by_age_group": age_emotions
        }

    except Exception as e:
        logger.error(f"Ошибка в get_emotion_by_demographics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка получения эмоций по демографии: {str(e)}")
    finally:
        if conn is not None:
            conn.close()

@app.get("/api/stats/waiters-performance", response_model=List[Dict[str, Any]])
def get_waiters_performance(
        start_date: Optional[datetime] = Query(None, description="Начальная дата для фильтрации (YYYY-MM-DD)"),
        end_date: Optional[datetime] = Query(None, description="Конечная дата для фильтрации (YYYY-MM-DD)")
):
    """
    Получить статистику по эффективности официантов
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Получаем список официантов
        waiters_query = """
        SELECT DISTINCT name 
        FROM detected_id 
        WHERE person_type = 'waiter'
        """

        params_waiters = []

        if start_date:
            waiters_query += " AND timestamp >= %s"
            params_waiters.append(start_date)

        if end_date:
            waiters_query += " AND timestamp <= %s"
            params_waiters.append(end_date)

        cursor.execute(waiters_query, params_waiters)
        waiters = [row["name"] for row in cursor.fetchall()]

        waiters_stats = []

        for waiter in waiters:
            # Базовые параметры для запросов
            params = [waiter]

            if start_date:
                params.append(start_date)

            if end_date:
                params.append(end_date)

            # Запрос для получения рабочих дней и часов
            time_query = """
            SELECT 
                COUNT(DISTINCT DATE(timestamp)) as work_days,
                SUM(EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp))))/3600 as total_hours
            FROM detected_id
            WHERE name = %s AND person_type = 'waiter'
            """

            if start_date:
                time_query += " AND timestamp >= %s"

            if end_date:
                time_query += " AND timestamp <= %s"

            time_query += " GROUP BY name"

            cursor.execute(time_query, params)
            time_result = cursor.fetchone()

            # Получаем количество обслуженных клиентов
            # Для этого считаем уникальных клиентов, которые были замечены в тот же день, что и официант
            customers_query = """
            WITH waiter_days AS (
                SELECT DISTINCT DATE(timestamp) as work_date
                FROM detected_id
                WHERE name = %s AND person_type = 'waiter'
            """

            if start_date:
                customers_query += " AND timestamp >= %s"

            if end_date:
                customers_query += " AND timestamp <= %s"

            customers_query += """
            )
            SELECT COUNT(DISTINCT c.track_id) as customers_served
            FROM detected_id c
            JOIN waiter_days w ON DATE(c.timestamp) = w.work_date
            WHERE c.person_type = 'customer'
            """

            cursor.execute(customers_query, params)
            customers_result = cursor.fetchone()

            # Получаем средние эмоции клиентов в дни работы официанта
            emotions_query = """
            WITH waiter_days AS (
                SELECT DISTINCT DATE(timestamp) as work_date
                FROM detected_id
                WHERE name = %s AND person_type = 'waiter'
            """

            if start_date:
                emotions_query += " AND timestamp >= %s"

            if end_date:
                emotions_query += " AND timestamp <= %s"

            emotions_query += """
            )
            SELECT 
                c.emotion,
                COUNT(*) as count
            FROM detected_id c
            JOIN waiter_days w ON DATE(c.timestamp) = w.work_date
            WHERE c.person_type = 'customer' AND c.emotion IS NOT NULL
            GROUP BY c.emotion
            ORDER BY count DESC
            """

            cursor.execute(emotions_query, params)
            emotions_results = cursor.fetchall()

            emotions_distribution = {row["emotion"]: row["count"] for row in emotions_results}

            # Определяем доминирующую эмоцию
            dominant_emotion = None
            if emotions_results:
                dominant_emotion = emotions_results[0]["emotion"]

            # Формируем статистику по официанту
            waiter_stat = {
                "name": waiter,
                "work_days": time_result["work_days"] if time_result else 0,
                "total_hours": time_result["total_hours"] if time_result else 0,
                "customers_served": customers_result["customers_served"] if customers_result else 0,
                "customers_per_hour": customers_result["customers_served"] / time_result[
                    "total_hours"] if time_result and time_result["total_hours"] > 0 and customers_result else 0,
                "dominant_customer_emotion": dominant_emotion,
                "customer_emotions": emotions_distribution
            }

            waiters_stats.append(waiter_stat)

        return waiters_stats

    except Exception as e:
        logger.error(f"Ошибка в get_waiters_performance: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики по официантам: {str(e)}")
    finally:
        if conn is not None:
            conn.close()

@app.get("/api/stats/celebrity-impact", response_model=List[Dict[str, Any]])
def get_celebrity_impact(
        start_date: Optional[datetime] = Query(None, description="Начальная дата для фильтрации (YYYY-MM-DD)"),
        end_date: Optional[datetime] = Query(None, description="Конечная дата для фильтрации (YYYY-MM-DD)")
):
    """
    Оценить влияние знаменитостей на посещаемость и эмоции клиентов
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Получаем список дней, когда были замечены знаменитости
        celebrity_days_query = """
        SELECT DISTINCT DATE(timestamp) as date
        FROM detected_id
        WHERE person_type = 'celebrity'
        """

        params = []

        if start_date:
            celebrity_days_query += " AND timestamp >= %s"
            params.append(start_date)

        if end_date:
            celebrity_days_query += " AND timestamp <= %s"
            params.append(end_date)

        cursor.execute(celebrity_days_query, params)
        celebrity_days = [row["date"] for row in cursor.fetchall()]

        celebrity_impact = []

        for day in celebrity_days:
            # Получаем знаменитостей, которые были в этот день
            celebrities_query = """
            SELECT 
                name,
                MIN(timestamp) as arrival_time,
                MAX(timestamp) as departure_time
            FROM detected_id
            WHERE person_type = 'celebrity' AND DATE(timestamp) = %s
            GROUP BY name
            """

            cursor.execute(celebrities_query, [day])
            celebrities = cursor.fetchall()

            # Для каждой знаменитости определяем влияние
            for celebrity in celebrities:
                # Период до прихода знаменитости (за 2 часа)
                before_time = celebrity["arrival_time"] - timedelta(hours=2)

                # Период после ухода знаменитости (за 2 часа)
                after_time = celebrity["departure_time"] + timedelta(hours=2)

                # Получаем статистику по клиентам до прибытия знаменитости
                before_query = """
                SELECT 
                    COUNT(DISTINCT track_id) as visitor_count,
                    MODE() WITHIN GROUP (ORDER BY emotion) as dominant_emotion
                FROM detected_id
                WHERE person_type = 'customer' 
                    AND timestamp >= %s 
                    AND timestamp < %s
                """

                cursor.execute(before_query, [before_time, celebrity["arrival_time"]])
                before_stats = cursor.fetchone()

                # Получаем статистику по клиентам во время присутствия знаменитости
                during_query = """
                SELECT 
                    COUNT(DISTINCT track_id) as visitor_count,
                    MODE() WITHIN GROUP (ORDER BY emotion) as dominant_emotion
                FROM detected_id
                WHERE person_type = 'customer' 
                    AND timestamp >= %s 
                    AND timestamp <= %s
                """

                cursor.execute(during_query, [celebrity["arrival_time"], celebrity["departure_time"]])
                during_stats = cursor.fetchone()

                # Получаем статистику по клиентам после ухода знаменитости
                after_query = """
                SELECT 
                    COUNT(DISTINCT track_id) as visitor_count,
                    MODE() WITHIN GROUP (ORDER BY emotion) as dominant_emotion
                FROM detected_id
                WHERE person_type = 'customer' 
                    AND timestamp > %s 
                    AND timestamp <= %s
                """

                cursor.execute(after_query, [celebrity["departure_time"], after_time])
                after_stats = cursor.fetchone()

                # Рассчитываем процентное изменение посещаемости
                before_count = before_stats["visitor_count"] if before_stats else 0
                during_count = during_stats["visitor_count"] if during_stats else 0
                after_count = after_stats["visitor_count"] if after_stats else 0

                # Определяем временной интервал в часах
                before_duration = (celebrity["arrival_time"] - before_time).total_seconds() / 3600
                during_duration = (celebrity["departure_time"] - celebrity["arrival_time"]).total_seconds() / 3600
                after_duration = (after_time - celebrity["departure_time"]).total_seconds() / 3600

                # Рассчитываем среднее количество посетителей в час для каждого периода
                before_rate = before_count / before_duration if before_duration > 0 else 0
                during_rate = during_count / during_duration if during_duration > 0 else 0
                after_rate = after_count / after_duration if after_duration > 0 else 0

                # Рассчитываем процентное изменение
                visitor_change_percent = ((during_rate - before_rate) / before_rate * 100) if before_rate > 0 else 0

                celebrity_impact.append({
                    "date": day,
                    "celebrity_name": celebrity["name"],
                    "arrival_time": celebrity["arrival_time"],
                    "departure_time": celebrity["departure_time"],
                    "duration_hours": during_duration,
                    "before_visitor_rate": before_rate,
                    "during_visitor_rate": during_rate,
                    "after_visitor_rate": after_rate,
                    "visitor_change_percent": visitor_change_percent,
                    "before_dominant_emotion": before_stats["dominant_emotion"] if before_stats else None,
                    "during_dominant_emotion": during_stats["dominant_emotion"] if during_stats else None,
                    "after_dominant_emotion": after_stats["dominant_emotion"] if after_stats else None
                })

        return celebrity_impact

    except Exception as e:
        logger.error(f"Ошибка в get_celebrity_impact: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка получения данных о влиянии знаменитостей: {str(e)}")
    finally:
        if conn is not None:
            conn.close()

@app.get("/api/stats/feedback-correlation", response_model=Dict[str, Any])
def get_feedback_correlation(
        start_date: Optional[datetime] = Query(None, description="Начальная дата для фильтрации (YYYY-MM-DD)"),
        end_date: Optional[datetime] = Query(None, description="Конечная дата для фильтрации (YYYY-MM-DD)")
):
    """
    Получить корреляцию между доминирующими эмоциями и предполагаемой удовлетворенностью клиентов
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Определяем отношение эмоций к удовлетворенности
        emotion_satisfaction = {
            "happy": 1.0,
            "smile": 0.9,
            "surprise": 0.7,
            "neutral": 0.5,
            "sad": 0.3,
            "fear": 0.2,
            "disgust": 0.1,
            "angry": 0.0
        }

        # Получаем данные по эмоциям клиентов по дням
        query = """
        SELECT 
            DATE(timestamp) as date,
            emotion,
            COUNT(*) as count
        FROM detected_id
        WHERE person_type = 'customer' AND emotion IS NOT NULL
        """

        params = []

        if start_date:
            query += " AND timestamp >= %s"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= %s"
            params.append(end_date)

        query += " GROUP BY date, emotion ORDER BY date, emotion"

        cursor.execute(query, params)
        results = cursor.fetchall()

        # Группируем результаты по дням
        days_emotions = {}

        for row in results:
            date_str = row["date"].strftime("%Y-%m-%d")
            emotion = row["emotion"]
            count = row["count"]

            if date_str not in days_emotions:
                days_emotions[date_str] = {}

            days_emotions[date_str][emotion] = count

        # Рассчитываем индекс удовлетворенности для каждого дня
        satisfaction_index = {}

        for date, emotions in days_emotions.items():
            total_count = sum(emotions.values())

            if total_count == 0:
                satisfaction_index[date] = 0
                continue

            weighted_sum = 0

            for emotion, count in emotions.items():
                if emotion in emotion_satisfaction:
                    weighted_sum += count * emotion_satisfaction[emotion]

            satisfaction_index[date] = weighted_sum / total_count

        # Преобразуем результаты в формат для вывода
        result = {
            "satisfaction_by_date": satisfaction_index,
            "emotion_weights": emotion_satisfaction,
            "emotions_by_date": days_emotions
        }

        return result

    except Exception as e:
        logger.error(f"Ошибка в get_feedback_correlation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка получения корреляции отзывов: {str(e)}")
    finally:
        if conn is not None:
            conn.close()

@app.get("/api/stats/overall", response_model=VisitorsStats)
def get_overall_stats(
        start_date: Optional[datetime] = Query(None, description="Начальная дата для фильтрации (YYYY-MM-DD)"),
        end_date: Optional[datetime] = Query(None, description="Конечная дата для фильтрации (YYYY-MM-DD)"),
        person_type: Optional[str] = Query(None, description="Тип человека (customer, waiter, celebrity)")
):
    """
    Получить общую статистику по посетителям
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Базовый запрос
        query = """
        SELECT 
            COUNT(*) as total_visitors,
            COUNT(DISTINCT track_id) as unique_visitors,
            AVG(age) as average_age,
            COUNT(DISTINCT CASE WHEN name != 'unknown' THEN track_id END) as known_visitors
        FROM detected_id
        WHERE 1=1
        """

        params = []

        # Добавляем фильтры, если они указаны
        if start_date:
            query += " AND timestamp >= %s"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= %s"
            params.append(end_date)

        if person_type:
            query += " AND person_type = %s"
            params.append(person_type)

        cursor.execute(query, params)
        result = cursor.fetchone()

        # Получаем распределение по полу
        gender_query = """
        SELECT gender, COUNT(DISTINCT track_id) as count
        FROM detected_id
        WHERE gender IS NOT NULL
        """

        if start_date:
            gender_query += " AND timestamp >= %s"

        if end_date:
            gender_query += " AND timestamp <= %s"

        if person_type:
            gender_query += " AND person_type = %s"

        gender_query += " GROUP BY gender"

        cursor.execute(gender_query, params)
        gender_distribution = {row["gender"]: row["count"] for row in cursor.fetchall()}

        # Получаем распределение по эмоциям
        emotion_query = """
        SELECT emotion, COUNT(*) as count
        FROM detected_id
        WHERE emotion IS NOT NULL
        """

        if start_date:
            emotion_query += " AND timestamp >= %s"

        if end_date:
            emotion_query += " AND timestamp <= %s"

        if person_type:
            emotion_query += " AND person_type = %s"

        emotion_query += " GROUP BY emotion"

        cursor.execute(emotion_query, params)
        emotion_distribution = {row["emotion"]: row["count"] for row in cursor.fetchall()}

        # Получаем распределение по типам людей
        person_type_query = """
        SELECT person_type, COUNT(DISTINCT track_id) as count
        FROM detected_id
        WHERE person_type IS NOT NULL
        """

        params_without_person_type = [p for p in params if p != person_type]

        if start_date:
            person_type_query += " AND timestamp >= %s"

        if end_date:
            person_type_query += " AND timestamp <= %s"

        person_type_query += " GROUP BY person_type"

        cursor.execute(person_type_query, params_without_person_type)
        person_type_distribution = {row["person_type"]: row["count"] for row in cursor.fetchall()}

        # Получаем количество повторных посетителей (те, кто приходил более одного раза)
        return_query = """
        SELECT COUNT(DISTINCT track_id) as return_visitors
        FROM (
            SELECT track_id, COUNT(DISTINCT DATE(timestamp)) as visit_days
            FROM detected_id
            WHERE name != 'unknown'
        """

        if start_date:
            return_query += " AND timestamp >= %s"

        if end_date:
            return_query += " AND timestamp <= %s"

        if person_type:
            return_query += " AND person_type = %s"

        return_query += """
            GROUP BY track_id
            HAVING COUNT(DISTINCT DATE(timestamp)) > 1
        ) as return_visitors
        """

        cursor.execute(return_query, params)
        return_visitors_result = cursor.fetchone()
        return_visitors = return_visitors_result["return_visitors"] if return_visitors_result else 0

        return {
            "total_visitors": result["total_visitors"],
            "unique_visitors": result["unique_visitors"],
            "return_visitors": return_visitors,
            "average_age": result["average_age"],
            "gender_distribution": gender_distribution,
            "emotion_distribution": emotion_distribution,
            "person_type_distribution": person_type_distribution
        }

    except Exception as e:
        logger.error(f"Ошибка в get_overall_stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики: {str(e)}")
    finally:
        if conn is not None:
            conn.close()

@app.get("/api/stats/timeseries", response_model=VisitorTimeSeries)
def get_visitor_timeseries(
        period: int = Query(30, description="Период в днях для анализа"),
        person_type: Optional[str] = Query(None, description="Тип человека (customer, waiter, celebrity)")
):
    """
    Получить временной ряд посещений по дням, неделям и месяцам
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        end_date = datetime.now()
        start_date = end_date - timedelta(days=period)

        # Запрос для ежедневной статистики
        daily_query = """
        SELECT 
            DATE(timestamp) as date, 
            COUNT(DISTINCT track_id) as count
        FROM detected_id
        WHERE timestamp >= %s AND timestamp <= %s
        """

        params = [start_date, end_date]

        if person_type:
            daily_query += " AND person_type = %s"
            params.append(person_type)

        daily_query += " GROUP BY DATE(timestamp) ORDER BY date"

        cursor.execute(daily_query, params)
        daily_data = [{"timestamp": row["date"], "value": row["count"]} for row in cursor.fetchall()]

        # Запрос для еженедельной статистики
        weekly_query = """
        SELECT 
            DATE_TRUNC('week', timestamp) as week, 
            COUNT(DISTINCT track_id) as count
        FROM detected_id
        WHERE timestamp >= %s AND timestamp <= %s
        """

        if person_type:
            weekly_query += " AND person_type = %s"

        weekly_query += " GROUP BY week ORDER BY week"

        cursor.execute(weekly_query, params)
        weekly_data = [{"timestamp": row["week"], "value": row["count"]} for row in cursor.fetchall()]

        # Запрос для ежемесячной статистики
        monthly_query = """
        SELECT 
            DATE_TRUNC('month', timestamp) as month, 
            COUNT(DISTINCT track_id) as count
        FROM detected_id
        WHERE timestamp >= %s AND timestamp <= %s
        """

        if person_type:
            monthly_query += " AND person_type = %s"

        monthly_query += " GROUP BY month ORDER BY month"

        cursor.execute(monthly_query, params)
        monthly_data = [{"timestamp": row["month"], "value": row["count"]} for row in cursor.fetchall()]

        return {
            "daily": daily_data,
            "weekly": weekly_data,
            "monthly": monthly_data
        }

    except Exception as e:
        logger.error(f"Ошибка в get_visitor_timeseries: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка получения временных рядов: {str(e)}")
    finally:
        if conn is not None:
            conn.close()

@app.get("/api/stats/age-groups", response_model=AgeGroupDistribution)
def get_age_distribution(
       start_date: Optional[datetime] = Query(None, description="Начальная дата для фильтрации (YYYY-MM-DD)"),
       end_date: Optional[datetime] = Query(None, description="Конечная дата для фильтрации (YYYY-MM-DD)"),
       person_type: Optional[str] = Query(None, description="Тип человека (customer, waiter, celebrity)")
):
   """
   Получить распределение посетителей по возрастным группам
   """
   conn = None
   try:
       conn = get_db_connection()
       cursor = conn.cursor()

       # Определяем возрастные группы
       query = """
       SELECT 
           CASE 
               WHEN age < 18 THEN '<18'
               WHEN age BETWEEN 18 AND 24 THEN '18-24'
               WHEN age BETWEEN 25 AND 34 THEN '25-34'
               WHEN age BETWEEN 35 AND 44 THEN '35-44'
               WHEN age BETWEEN 45 AND 54 THEN '45-54'
               WHEN age BETWEEN 55 AND 64 THEN '55-64'
               WHEN age >= 65 THEN '65+'
               ELSE 'Unknown'
           END as age_group,
           COUNT(DISTINCT track_id) as count
       FROM detected_id
       WHERE age IS NOT NULL
       """

       params = []

       if start_date:
           query += " AND timestamp >= %s"
           params.append(start_date)

       if end_date:
           query += " AND timestamp <= %s"
           params.append(end_date)

       if person_type:
           query += " AND person_type = %s"
           params.append(person_type)

       query += " GROUP BY age_group ORDER BY age_group"

       cursor.execute(query, params)
       age_distribution = {row["age_group"]: row["count"] for row in cursor.fetchall()}

       return {"age_groups": age_distribution}

   except Exception as e:
       logger.error(f"Ошибка в get_age_distribution: {str(e)}", exc_info=True)
       raise HTTPException(status_code=500, detail=f"Ошибка получения распределения по возрасту: {str(e)}")
   finally:
       if conn is not None:
           conn.close()

@app.get("/api/stats/top-visitors", response_model=List[Dict[str, Any]])
def get_top_visitors(
       limit: int = Query(10, description="Количество записей для вывода"),
       start_date: Optional[datetime] = Query(None, description="Начальная дата для фильтрации (YYYY-MM-DD)"),
       end_date: Optional[datetime] = Query(None, description="Конечная дата для фильтрации (YYYY-MM-DD)"),
       person_type: Optional[str] = Query(None, description="Тип человека (customer, waiter, celebrity)")
):
   """
   Получить топ посетителей по количеству посещений
   """
   conn = None
   try:
       conn = get_db_connection()
       cursor = conn.cursor()

       query = """
       SELECT 
           name,
           COUNT(DISTINCT DATE(timestamp)) as visit_count,
           MAX(timestamp) as last_visit,
           MODE() WITHIN GROUP (ORDER BY emotion) as most_common_emotion
       FROM detected_id
       WHERE name != 'unknown'
       """

       params = []

       if start_date:
           query += " AND timestamp >= %s"
           params.append(start_date)

       if end_date:
           query += " AND timestamp <= %s"
           params.append(end_date)

       if person_type:
           query += " AND person_type = %s"
           params.append(person_type)

       query += " GROUP BY name ORDER BY visit_count DESC LIMIT %s"
       params.append(limit)

       cursor.execute(query, params)
       top_visitors = []

       for row in cursor.fetchall():
           visitor = dict(row)

           # Дополнительный запрос для получения среднего возраста и пола
           detail_query = """
           SELECT 
               AVG(age) as avg_age,
               MODE() WITHIN GROUP (ORDER BY gender) as most_common_gender
           FROM detected_id
           WHERE name = %s
           """

           detail_params = [row["name"]]

           if start_date:
               detail_query += " AND timestamp >= %s"
               detail_params.append(start_date)

           if end_date:
               detail_query += " AND timestamp <= %s"
               detail_params.append(end_date)

           if person_type:
               detail_query += " AND person_type = %s"
               detail_params.append(person_type)

           cursor.execute(detail_query, detail_params)
           detail_row = cursor.fetchone()

           if detail_row:
               visitor["average_age"] = detail_row["avg_age"]
               visitor["gender"] = detail_row["most_common_gender"]

           top_visitors.append(visitor)

       return top_visitors

   except Exception as e:
       logger.error(f"Ошибка в get_top_visitors: {str(e)}", exc_info=True)
       raise HTTPException(status_code=500, detail=f"Ошибка получения топ посетителей: {str(e)}")
   finally:
       if conn is not None:
           conn.close()

@app.get("/api/stats/emotion-trends", response_model=Dict[str, List[Dict[str, Any]]])
def get_emotion_trends(
       period: int = Query(30, description="Период в днях для анализа"),
       person_type: Optional[str] = Query(None, description="Тип человека (customer, waiter, celebrity)")
):
   """
   Получить тренды эмоций посетителей во времени
   """
   conn = None
   try:
       conn = get_db_connection()
       cursor = conn.cursor()

       end_date = datetime.now()
       start_date = end_date - timedelta(days=period)

       query = """
       SELECT 
           DATE(timestamp) as date,
           emotion,
           COUNT(*) as count
       FROM detected_id
       WHERE emotion IS NOT NULL AND timestamp >= %s AND timestamp <= %s
       """

       params = [start_date, end_date]

       if person_type:
           query += " AND person_type = %s"
           params.append(person_type)

       query += " GROUP BY date, emotion ORDER BY date, emotion"

       cursor.execute(query, params)
       rows = cursor.fetchall()

       # Преобразуем результаты в формат для временных рядов по эмоциям
       emotions_data = {}

       for row in rows:
           date_str = row["date"].strftime("%Y-%m-%d")
           emotion = row["emotion"]
           count = row["count"]

           if emotion not in emotions_data:
               emotions_data[emotion] = []

           emotions_data[emotion].append({
               "date": date_str,
               "count": count
           })

       return emotions_data

   except Exception as e:
       logger.error(f"Ошибка в get_emotion_trends: {str(e)}", exc_info=True)
       raise HTTPException(status_code=500, detail=f"Ошибка получения трендов эмоций: {str(e)}")
   finally:
       if conn is not None:
           conn.close()

@app.get("/api/stats/visit-duration", response_model=Dict[str, Any])
def get_visit_duration(
       start_date: Optional[datetime] = Query(None, description="Начальная дата для фильтрации (YYYY-MM-DD)"),
       end_date: Optional[datetime] = Query(None, description="Конечная дата для фильтрации (YYYY-MM-DD)"),
       person_type: Optional[str] = Query(None, description="Тип человека (customer, waiter, celebrity)")
):
   """
   Получить статистику по продолжительности визитов
   """
   conn = None
   try:
       conn = get_db_connection()
       cursor = conn.cursor()

       # Рассчитываем продолжительность визитов по трек-идентификаторам
       query = """
       SELECT 
           track_id,
           name,
           MIN(timestamp) as first_seen,
           MAX(timestamp) as last_seen,
           EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/60 as duration_minutes
       FROM detected_id
       WHERE 1=1
       """

       params = []

       if start_date:
           query += " AND timestamp >= %s"
           params.append(start_date)

       if end_date:
           query += " AND timestamp <= %s"
           params.append(end_date)

       if person_type:
           query += " AND person_type = %s"
           params.append(person_type)

       query += " GROUP BY track_id, name"

       cursor.execute(query, params)
       visits = cursor.fetchall()

       # Рассчитываем статистику
       durations = [visit["duration_minutes"] for visit in visits if visit["duration_minutes"] > 0]

       if not durations:
           return {
               "average_duration_minutes": 0,
               "min_duration_minutes": 0,
               "max_duration_minutes": 0,
               "visit_duration_distribution": {},
               "total_visits_analyzed": 0
           }

       # Формируем распределение по диапазонам длительности
       distribution = {
           "<5 мин": 0,
           "5-15 мин": 0,
           "15-30 мин": 0,
           "30-60 мин": 0,
           "1-2 часа": 0,
           ">2 часа": 0
       }

       for duration in durations:
           if duration < 5:
               distribution["<5 мин"] += 1
           elif duration < 15:
               distribution["5-15 мин"] += 1
           elif duration < 30:
               distribution["15-30 мин"] += 1
           elif duration < 60:
               distribution["30-60 мин"] += 1
           elif duration < 120:
               distribution["1-2 часа"] += 1
           else:
               distribution[">2 часа"] += 1

       return {
           "average_duration_minutes": sum(durations) / len(durations) if durations else 0,
           "min_duration_minutes": min(durations) if durations else 0,
           "max_duration_minutes": max(durations) if durations else 0,
           "visit_duration_distribution": distribution,
           "total_visits_analyzed": len(durations)
       }

   except Exception as e:
       logger.error(f"Ошибка в get_visit_duration: {str(e)}", exc_info=True)
       raise HTTPException(status_code=500, detail=f"Ошибка получения данных о продолжительности визитов: {str(e)}")
   finally:
       if conn is not None:
           conn.close()

@app.get("/api/stats/compare-periods", response_model=Dict[str, Any])
def compare_periods(
       current_start: datetime = Query(..., description="Начало текущего периода (YYYY-MM-DD)"),
       current_end: datetime = Query(..., description="Конец текущего периода (YYYY-MM-DD)"),
       previous_start: datetime = Query(..., description="Начало предыдущего периода (YYYY-MM-DD)"),
       previous_end: datetime = Query(..., description="Конец предыдущего периода (YYYY-MM-DD)"),
       person_type: Optional[str] = Query(None, description="Тип человека (customer, waiter, celebrity)")
):
   """
   Сравнить статистику между двумя периодами
   """
   conn = None
   try:
       conn = get_db_connection()
       cursor = conn.cursor()

       # Функция для получения статистики за период
       def get_period_stats(start_date, end_date):
           query = """
           SELECT 
               COUNT(DISTINCT track_id) as unique_visitors,
               COUNT(*) as total_detections,
               AVG(age) as average_age,
               COUNT(DISTINCT CASE WHEN name != 'unknown' THEN track_id END) as known_visitors
           FROM detected_id
           WHERE timestamp >= %s AND timestamp <= %s
           """

           params = [start_date, end_date]

           if person_type:
               query += " AND person_type = %s"
               params.append(person_type)

           cursor.execute(query, params)
           return cursor.fetchone()

       # Получаем статистику за оба периода
       current_stats = get_period_stats(current_start, current_end)
       previous_stats = get_period_stats(previous_start, previous_end)

       # Рассчитываем проценты изменений
       changes = {}

       for key in current_stats.keys():
           if previous_stats[key] and previous_stats[key] != 0:
               percent_change = ((current_stats[key] - previous_stats[key]) / previous_stats[key]) * 100
               changes[key] = round(percent_change, 2)
           else:
               changes[key] = None  # Невозможно рассчитать процент изменения

       return {
           "current_period": {
               "start": current_start,
               "end": current_end,
               "stats": current_stats
           },
           "previous_period": {
               "start": previous_start,
               "end": previous_end,
               "stats": previous_stats
           },
           "percent_changes": changes
       }

   except Exception as e:
       logger.error(f"Ошибка в compare_periods: {str(e)}", exc_info=True)
       raise HTTPException(status_code=500, detail=f"Ошибка сравнения периодов: {str(e)}")
   finally:
       if conn is not None:
           conn.close()

@app.get("/api/stats/peak-hours", response_model=Dict[str, List[Dict[str, Any]]])
def get_peak_hours(
       start_date: Optional[datetime] = Query(None, description="Начальная дата для фильтрации (YYYY-MM-DD)"),
       end_date: Optional[datetime] = Query(None, description="Конечная дата для фильтрации (YYYY-MM-DD)"),
       person_type: Optional[str] = Query(None, description="Тип человека (customer, waiter, celebrity)")
):
   """
   Получить пиковые часы посещаемости по дням недели
   """
   conn = None
   try:
       conn = get_db_connection()
       cursor = conn.cursor()

       query = """
       SELECT 
           EXTRACT(DOW FROM timestamp) as day_of_week,
           EXTRACT(HOUR FROM timestamp) as hour,
           COUNT(DISTINCT track_id) as visitor_count
       FROM detected_id
       WHERE 1=1
       """

       params = []

       if start_date:
           query += " AND timestamp >= %s"
           params.append(start_date)

       if end_date:
           query += " AND timestamp <= %s"
           params.append(end_date)

       if person_type:
           query += " AND person_type = %s"
           params.append(person_type)

       query += " GROUP BY day_of_week, hour ORDER BY day_of_week, hour"

       cursor.execute(query, params)
       results = cursor.fetchall()

       # Преобразуем результаты в формат по дням недели
       days_mapping = {
           0: "Воскресенье",
           1: "Понедельник",
           2: "Вторник",
           3: "Среда",
           4: "Четверг",
           5: "Пятница",
           6: "Суббота"
       }

       peak_hours = {day: [] for day in days_mapping.values()}

       for row in results:
           day_name = days_mapping[int(row["day_of_week"])]
           peak_hours[day_name].append({
               "hour": int(row["hour"]),
               "visitor_count": row["visitor_count"]
           })

       return peak_hours

   except Exception as e:
       logger.error(f"Ошибка в get_peak_hours: {str(e)}", exc_info=True)
       raise HTTPException(status_code=500, detail=f"Ошибка получения пиковых часов: {str(e)}")
   finally:
       if conn is not None:
           conn.close()

@app.get("/api/stats/gender-age-correlation", response_model=Dict[str, Dict[str, int]])
def get_gender_age_correlation(
       start_date: Optional[datetime] = Query(None, description="Начальная дата для фильтрации (YYYY-MM-DD)"),
       end_date: Optional[datetime] = Query(None, description="Конечная дата для фильтрации (YYYY-MM-DD)"),
       person_type: Optional[str] = Query(None, description="Тип человека (customer, waiter, celebrity)")
):
   """
   Получить корреляцию между полом и возрастными группами
   """
   conn = None
   try:
       conn = get_db_connection()
       cursor = conn.cursor()

       query = """
       SELECT 
           gender,
           CASE 
               WHEN age < 18 THEN '<18'
               WHEN age BETWEEN 18 AND 24 THEN '18-24'
               WHEN age BETWEEN 25 AND 34 THEN '25-34'
               WHEN age BETWEEN 35 AND 44 THEN '35-44'
               WHEN age BETWEEN 45 AND 54 THEN '45-54'
               WHEN age BETWEEN 55 AND 64 THEN '55-64'
               WHEN age >= 65 THEN '65+'
               ELSE 'Unknown'
           END as age_group,
           COUNT(DISTINCT track_id) as count
       FROM detected_id
       WHERE gender IS NOT NULL AND age IS NOT NULL
       """

       params = []

       if start_date:
           query += " AND timestamp >= %s"
           params.append(start_date)

       if end_date:
           query += " AND timestamp <= %s"
           params.append(end_date)

       if person_type:
           query += " AND person_type = %s"
           params.append(person_type)

       query += " GROUP BY gender, age_group ORDER BY gender, age_group"

       cursor.execute(query, params)
       results = cursor.fetchall()

       # Преобразуем результаты в формат для корреляции
       correlation = {}

       for row in results:
           gender = row["gender"]
           age_group = row["age_group"]
           count = row["count"]

           if gender not in correlation:
               correlation[gender] = {}

           correlation[gender][age_group] = count

       return correlation

   except Exception as e:
       logger.error(f"Ошибка в get_gender_age_correlation: {str(e)}", exc_info=True)
       raise HTTPException(status_code=500, detail=f"Ошибка получения корреляции между полом и возрастом: {str(e)}")
   finally:
       if conn is not None:
           conn.close()

# Импортируем маршрутизатор видео
from video_api import video_router

# Подключаем маршрутизатор видео к основному приложению
# Не добавляем префикс /api, т.к. он уже указан в самом маршрутизаторе
app.include_router(video_router)

if __name__ == "__main__":
   import uvicorn
   uvicorn.run(app, host="0.0.0.0", port=8000)
# Дополнительные методы для класса DatabaseManager
# Эти методы необходимо добавить в class DatabaseManager в файле db_manager.py

import datetime
import json
import statistics
import numpy as np


def get_faces_by_frame_id(self, frame_id):
    """
    Возвращает данные о лицах для указанного кадра
    """
    conn = self.connection_pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT 
                    track_id, name, age, gender, emotion, person_type,
                    face_top, face_right, face_bottom, face_left,
                    body_top, body_right, body_bottom, body_left,
                    is_frontal
                FROM frame_data
                WHERE frame_id = %s
            ''', (frame_id,))

            results = cursor.fetchall()
            faces = []

            for row in results:
                (track_id, name, age, gender, emotion, person_type,
                 face_top, face_right, face_bottom, face_left,
                 body_top, body_right, body_bottom, body_left,
                 is_frontal) = row

                face_data = {
                    "track_id": track_id,
                    "name": name,
                    "age": age,
                    "gender": gender,
                    "emotion": emotion,
                    "person_type": person_type,
                    "face_top": face_top,
                    "face_right": face_right,
                    "face_bottom": face_bottom,
                    "face_left": face_left,
                    "body_top": body_top,
                    "body_right": body_right,
                    "body_bottom": body_left,
                    "body_left": body_left,
                    "is_frontal": is_frontal
                }

                faces.append(face_data)

            return faces
    except Exception as e:
        print(f"Error getting faces by frame ID: {e}")
        return []
    finally:
        self.connection_pool.putconn(conn)


def get_overall_stats(self, start_date=None, end_date=None, person_type=None, max_frame_id=None, task_id=None):
    """
    Возвращает общую статистику
    """
    conn = self.connection_pool.getconn()
    try:
        with conn.cursor() as cursor:
            # Формируем условия WHERE в зависимости от переданных параметров
            where_conditions = []
            params = []

            if start_date:
                where_conditions.append("timestamp >= %s")
                params.append(start_date)

            if end_date:
                where_conditions.append("timestamp <= %s")
                params.append(end_date)

            if person_type:
                where_conditions.append("person_type = %s")
                params.append(person_type)

            if max_frame_id:
                where_conditions.append("frame_id <= %s")
                params.append(max_frame_id)

            # Формируем SQL запрос
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            # Общее количество посетителей
            cursor.execute(f'''
                SELECT COUNT(*) 
                FROM frame_data 
                WHERE {where_clause}
            ''', params)
            total_visitors = cursor.fetchone()[0]

            # Уникальных посетителей (по track_id)
            cursor.execute(f'''
                SELECT COUNT(DISTINCT track_id) 
                FROM frame_data 
                WHERE {where_clause}
            ''', params)
            unique_visitors = cursor.fetchone()[0]

            # Средний возраст
            cursor.execute(f'''
                SELECT AVG(age) 
                FROM frame_data 
                WHERE {where_clause} AND age IS NOT NULL
            ''', params)
            average_age_result = cursor.fetchone()[0]
            average_age = float(average_age_result) if average_age_result is not None else None

            # Наиболее частая эмоция
            cursor.execute(f'''
                SELECT emotion, COUNT(*) as count
                FROM frame_data 
                WHERE {where_clause} AND emotion IS NOT NULL 
                GROUP BY emotion 
                ORDER BY count DESC 
                LIMIT 1
            ''', params)
            emotion_result = cursor.fetchone()
            most_common_emotion = emotion_result[0] if emotion_result else None

            return {
                "total_visitors": total_visitors,
                "unique_visitors": unique_visitors,
                "average_age": average_age,
                "most_common_emotion": most_common_emotion
            }
    except Exception as e:
        print(f"Error getting overall stats: {e}")
        return {
            "total_visitors": 0,
            "unique_visitors": 0,
            "average_age": None,
            "most_common_emotion": None
        }
    finally:
        self.connection_pool.putconn(conn)


def get_timeseries_stats(self, start_date=None, end_date=None, person_type=None, max_frame_id=None):
    """
    Возвращает статистику временного ряда
    """
    conn = self.connection_pool.getconn()
    try:
        with conn.cursor() as cursor:
            # Формируем условия WHERE в зависимости от переданных параметров
            where_conditions = []
            params = []

            if start_date:
                where_conditions.append("timestamp::date >= %s")
                params.append(start_date)

            if end_date:
                where_conditions.append("timestamp::date <= %s")
                params.append(end_date)

            if person_type:
                where_conditions.append("person_type = %s")
                params.append(person_type)

            if max_frame_id:
                where_conditions.append("frame_id <= %s")
                params.append(max_frame_id)

            # Формируем SQL запрос
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            # Получаем данные по дням
            cursor.execute(f'''
                SELECT 
                    timestamp::date as date, 
                    COUNT(DISTINCT track_id) as visitors_count
                FROM frame_data 
                WHERE {where_clause}
                GROUP BY date
                ORDER BY date
            ''', params)

            results = cursor.fetchall()
            timeseries_data = []

            for row in results:
                date, visitors_count = row
                timeseries_data.append({
                    "date": date.isoformat(),
                    "visitors_count": visitors_count
                })

            return timeseries_data
    except Exception as e:
        print(f"Error getting timeseries stats: {e}")
        return []
    finally:
        self.connection_pool.putconn(conn)


def get_emotions_stats(self, start_date=None, end_date=None, person_type=None, max_frame_id=None):
    """
    Возвращает статистику эмоций
    """
    conn = self.connection_pool.getconn()
    try:
        with conn.cursor() as cursor:
            # Формируем условия WHERE в зависимости от переданных параметров
            where_conditions = []
            params = []

            if start_date:
                where_conditions.append("timestamp::date >= %s")
                params.append(start_date)

            if end_date:
                where_conditions.append("timestamp::date <= %s")
                params.append(end_date)

            if person_type:
                where_conditions.append("person_type = %s")
                params.append(person_type)

            if max_frame_id:
                where_conditions.append("frame_id <= %s")
                params.append(max_frame_id)

            # Добавляем условие, что эмоция не NULL
            where_conditions.append("emotion IS NOT NULL")

            # Формируем SQL запрос
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            # Получаем данные по эмоциям
            cursor.execute(f'''
                SELECT 
                    emotion, 
                    COUNT(*) as count
                FROM frame_data 
                WHERE {where_clause}
                GROUP BY emotion
                ORDER BY count DESC
            ''', params)

            results = cursor.fetchall()
            emotions_data = {}

            for row in results:
                emotion, count = row
                emotions_data[emotion] = count

            # Если нет данных, возвращаем пустой словарь с базовыми эмоциями
            if not emotions_data:
                emotions_data = {
                    "happy": 0,
                    "sad": 0,
                    "angry": 0,
                    "surprised": 0,
                    "neutral": 0
                }

            return emotions_data
    except Exception as e:
        print(f"Error getting emotions stats: {e}")
        return {
            "happy": 0,
            "sad": 0,
            "angry": 0,
            "surprised": 0,
            "neutral": 0
        }
    finally:
        self.connection_pool.putconn(conn)


def get_peak_hours_stats(self, start_date=None, end_date=None, person_type=None, max_frame_id=None):
    """
    Возвращает статистику пиковых часов
    """
    conn = self.connection_pool.getconn()
    try:
        with conn.cursor() as cursor:
            # Формируем условия WHERE в зависимости от переданных параметров
            where_conditions = []
            params = []

            if start_date:
                where_conditions.append("timestamp::date >= %s")
                params.append(start_date)

            if end_date:
                where_conditions.append("timestamp::date <= %s")
                params.append(end_date)

            if person_type:
                where_conditions.append("person_type = %s")
                params.append(person_type)

            if max_frame_id:
                where_conditions.append("frame_id <= %s")
                params.append(max_frame_id)

            # Формируем SQL запрос
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            # Получаем данные по часам
            cursor.execute(f'''
                SELECT 
                    EXTRACT(HOUR FROM timestamp) as hour, 
                    COUNT(DISTINCT track_id) as visitors_count
                FROM frame_data 
                WHERE {where_clause}
                GROUP BY hour
                ORDER BY hour
            ''', params)

            results = cursor.fetchall()
            hours_data = {}

            # Инициализируем все часы значениями 0
            for hour in range(24):
                hours_data[hour] = 0

            # Заполняем данными из запроса
            for row in results:
                hour, visitors_count = row
                hours_data[int(hour)] = visitors_count

            return hours_data
    except Exception as e:
        print(f"Error getting peak hours stats: {e}")
        return {hour: 0 for hour in range(24)}
    finally:
        self.connection_pool.putconn(conn)


def get_gender_stats(self, start_date=None, end_date=None, person_type=None, max_frame_id=None):
    """
    Возвращает статистику по полу
    """
    conn = self.connection_pool.getconn()
    try:
        with conn.cursor() as cursor:
            # Формируем условия WHERE в зависимости от переданных параметров
            where_conditions = []
            params = []

            if start_date:
                where_conditions.append("timestamp::date >= %s")
                params.append(start_date)

            if end_date:
                where_conditions.append("timestamp::date <= %s")
                params.append(end_date)

            if person_type:
                where_conditions.append("person_type = %s")
                params.append(person_type)

            if max_frame_id:
                where_conditions.append("frame_id <= %s")
                params.append(max_frame_id)

            # Добавляем условие, что пол не NULL
            where_conditions.append("gender IS NOT NULL")

            # Формируем SQL запрос
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            # Получаем данные по полу
            cursor.execute(f'''
                SELECT 
                    gender, 
                    COUNT(*) as count
                FROM frame_data 
                WHERE {where_clause}
                GROUP BY gender
            ''', params)

            results = cursor.fetchall()
            gender_data = {
                "male": 0,
                "female": 0
            }

            for row in results:
                gender, count = row
                if gender.lower() in ["male", "м", "мужской"]:
                    gender_data["male"] = count
                elif gender.lower() in ["female", "ж", "женский"]:
                    gender_data["female"] = count

            return gender_data
    except Exception as e:
        print(f"Error getting gender stats: {e}")
        return {"male": 0, "female": 0}
    finally:
        self.connection_pool.putconn(conn)


def get_age_stats(self, start_date=None, end_date=None, person_type=None, max_frame_id=None):
    """
    Возвращает статистику по возрасту
    """
    conn = self.connection_pool.getconn()
    try:
        with conn.cursor() as cursor:
            # Формируем условия WHERE в зависимости от переданных параметров
            where_conditions = []
            params = []

            if start_date:
                where_conditions.append("timestamp::date >= %s")
                params.append(start_date)

            if end_date:
                where_conditions.append("timestamp::date <= %s")
                params.append(end_date)

            if person_type:
                where_conditions.append("person_type = %s")
                params.append(person_type)

            if max_frame_id:
                where_conditions.append("frame_id <= %s")
                params.append(max_frame_id)

            # Добавляем условие, что возраст не NULL
            where_conditions.append("age IS NOT NULL")

            # Формируем SQL запрос
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            # Получаем все возрасты
            cursor.execute(f'''
                SELECT 
                    age
                FROM frame_data 
                WHERE {where_clause}
            ''', params)

            results = cursor.fetchall()

            # Определяем возрастные группы
            age_groups = {
                "0-17": 0,
                "18-24": 0,
                "25-34": 0,
                "35-44": 0,
                "45-54": 0,
                "55-64": 0,
                "65+": 0
            }

            for row in results:
                age = row[0]

                if age < 18:
                    age_groups["0-17"] += 1
                elif age <= 24:
                    age_groups["18-24"] += 1
                elif age <= 34:
                    age_groups["25-34"] += 1
                elif age <= 44:
                    age_groups["35-44"] += 1
                elif age <= 54:
                    age_groups["45-54"] += 1
                elif age <= 64:
                    age_groups["55-64"] += 1
                else:
                    age_groups["65+"] += 1

            return age_groups
    except Exception as e:
        print(f"Error getting age stats: {e}")
        return {
            "0-17": 0,
            "18-24": 0,
            "25-34": 0,
            "35-44": 0,
            "45-54": 0,
            "55-64": 0,
            "65+": 0
        }
    finally:
        self.connection_pool.putconn(conn)


def get_frame_stats(self, max_frame_id, task_id=None, person_type=None):
    """
    Возвращает статистику до указанного кадра
    """
    conn = self.connection_pool.getconn()
    try:
        with conn.cursor() as cursor:
            # Формируем условия WHERE в зависимости от переданных параметров
            where_conditions = [f"frame_id <= {max_frame_id}"]
            params = []

            if person_type:
                where_conditions.append("person_type = %s")
                params.append(person_type)

            # Формируем SQL запрос
            where_clause = " AND ".join(where_conditions)

            # Общее количество посетителей
            cursor.execute(f'''
                SELECT COUNT(*) 
                FROM frame_data 
                WHERE {where_clause}
            ''', params)
            total_visitors = cursor.fetchone()[0]

            # Уникальных посетителей (по track_id)
            cursor.execute(f'''
                SELECT COUNT(DISTINCT track_id) 
                FROM frame_data 
                WHERE {where_clause}
            ''', params)
            unique_visitors = cursor.fetchone()[0]

            # Количество официантов
            cursor.execute(f'''
                SELECT COUNT(DISTINCT track_id) 
                FROM frame_data 
                WHERE {where_clause} AND person_type = 'waiter'
            ''', params)
            waiters_count = cursor.fetchone()[0]

            # Количество знаменитостей
            cursor.execute(f'''
                SELECT COUNT(DISTINCT track_id) 
                FROM frame_data 
                WHERE {where_clause} AND person_type = 'celebrity'
            ''', params)
            celebrities_count = cursor.fetchone()[0]

            # Распределение эмоций
            cursor.execute(f'''
                SELECT emotion, COUNT(*) as count
                FROM frame_data 
                WHERE {where_clause} AND emotion IS NOT NULL 
                GROUP BY emotion
            ''', params)

            emotion_results = cursor.fetchall()
            emotions = {}

            for row in emotion_results:
                emotion, count = row
                emotions[emotion] = count

            return {
                "total_visitors": total_visitors,
                "unique_visitors": unique_visitors,
                "waiters_count": waiters_count,
                "celebrities_count": celebrities_count,
                "emotions": emotions
            }
    except Exception as e:
        print(f"Error getting frame stats: {e}")
        return {
            "total_visitors": 0,
            "unique_visitors": 0,
            "waiters_count": 0,
            "celebrities_count": 0,
            "emotions": {}
        }
    finally:
        self.connection_pool.putconn(conn)


def get_visitor_trends(self, start_date=None, end_date=None, person_type=None, max_frame_id=None):
    """
    Возвращает тренды посещений
    """
    conn = self.connection_pool.getconn()
    try:
        with conn.cursor() as cursor:
            # Формируем условия WHERE в зависимости от переданных параметров
            where_conditions = []
            params = []

            if start_date:
                where_conditions.append("timestamp::date >= %s")
                params.append(start_date)

            if end_date:
                where_conditions.append("timestamp::date <= %s")
                params.append(end_date)

            if person_type:
                where_conditions.append("person_type = %s")
                params.append(person_type)

            if max_frame_id:
                where_conditions.append("frame_id <= %s")
                params.append(max_frame_id)

            # Формируем SQL запрос
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            # Получаем данные по дням
            cursor.execute(f'''
                SELECT 
                    timestamp::date as date, 
                    COUNT(DISTINCT track_id) as unique_visitors,
                    COUNT(*) - COUNT(DISTINCT track_id) as repeat_visitors,
                    COUNT(*) as total_visitors
                FROM frame_data 
                WHERE {where_clause}
                GROUP BY date
                ORDER BY date
            ''', params)

            results = cursor.fetchall()
            trends_data = []

            for row in results:
                date, unique_visitors, repeat_visitors, total_visitors = row
                trends_data.append({
                    "date": date.isoformat(),
                    "unique_visitors": unique_visitors,
                    "repeat_visitors": repeat_visitors,
                    "total_visitors": total_visitors
                })

            return trends_data
    except Exception as e:
        print(f"Error getting visitor trends: {e}")
        return []
    finally:
        self.connection_pool.putconn(conn)


def get_top_visitors(self, start_date=None, end_date=None, person_type=None, max_frame_id=None):
    """
    Возвращает топ посетителей
    """
    conn = self.connection_pool.getconn()
    try:
        with conn.cursor() as cursor:
            # Формируем условия WHERE в зависимости от переданных параметров
            where_conditions = []
            params = []

            if start_date:
                where_conditions.append("timestamp::date >= %s")
                params.append(start_date)

            if end_date:
                where_conditions.append("timestamp::date <= %s")
                params.append(end_date)

            if person_type:
                where_conditions.append("person_type = %s")
                params.append(person_type)

            if max_frame_id:
                where_conditions.append("frame_id <= %s")
                params.append(max_frame_id)

            # Формируем SQL запрос
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            # Получаем топ посетителей
            cursor.execute(f'''
                SELECT 
                    track_id,
                    name,
                    person_type,
                    COUNT(*) as visit_count,
                    MAX(timestamp) as last_visit
                FROM frame_data 
                WHERE {where_clause}
                GROUP BY track_id, name, person_type
                ORDER BY visit_count DESC
                LIMIT 10
            ''', params)

            results = cursor.fetchall()
            top_visitors = []

            for row in results:
                track_id, name, person_type, visit_count, last_visit = row
                top_visitors.append({
                    "track_id": track_id,
                    "name": name,
                    "person_type": person_type,
                    "visit_count": visit_count,
                    "last_visit": last_visit.isoformat() if last_visit else None
                })

            return top_visitors
    except Exception as e:
        print(f"Error getting top visitors: {e}")
        return []
    finally:
        self.connection_pool.putconn(conn)


def get_visit_duration(self, start_date=None, end_date=None, person_type=None, max_frame_id=None):
    """
    Возвращает продолжительность визитов
    """
    conn = self.connection_pool.getconn()
    try:
        with conn.cursor() as cursor:
            # Формируем условия WHERE в зависимости от переданных параметров
            where_conditions = []
            params = []

            if start_date:
                where_conditions.append("timestamp::date >= %s")
                params.append(start_date)

            if end_date:
                where_conditions.append("timestamp::date <= %s")
                params.append(end_date)

            if person_type:
                where_conditions.append("person_type = %s")
                params.append(person_type)

            if max_frame_id:
                where_conditions.append("frame_id <= %s")
                params.append(max_frame_id)

            # Формируем SQL запрос
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            # В реальном сценарии здесь будет более сложный запрос для расчета
            # продолжительности пребывания посетителей
            # Сейчас мы просто симулируем данные

            # Диапазоны продолжительности в минутах
            duration_groups = {
                "0-5": 0,
                "5-15": 0,
                "15-30": 0,
                "30-60": 0,
                "60+": 0
            }

            # Для демонстрации заполняем случайными значениями
            duration_groups["0-5"] = 12
            duration_groups["5-15"] = 25
            duration_groups["15-30"] = 18
            duration_groups["30-60"] = 9
            duration_groups["60+"] = 3

            return duration_groups
    except Exception as e:
        print(f"Error getting visit duration: {e}")
        return {
            "0-5": 0,
            "5-15": 0,
            "15-30": 0,
            "30-60": 0,
            "60+": 0
        }
    finally:
        self.connection_pool.putconn(conn)


def get_peak_hours_detailed(self, start_date=None, end_date=None, person_type=None, max_frame_id=None):
    """
    Возвращает детальные данные о пиковых часах
    """
    conn = self.connection_pool.getconn()
    try:
        with conn.cursor() as cursor:
            # Формируем условия WHERE в зависимости от переданных параметров
            where_conditions = []
            params = []

            if start_date:
                where_conditions.append("timestamp::date >= %s")
                params.append(start_date)

            if end_date:
                where_conditions.append("timestamp::date <= %s")
                params.append(end_date)

            if person_type:
                where_conditions.append("person_type = %s")
                params.append(person_type)

            if max_frame_id:
                where_conditions.append("frame_id <= %s")
                params.append(max_frame_id)

            # Формируем SQL запрос
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            # Получаем данные по часам и дням недели
            cursor.execute(f'''
                SELECT 
                    EXTRACT(DOW FROM timestamp) as day_of_week,
                    EXTRACT(HOUR FROM timestamp) as hour,
                    COUNT(DISTINCT track_id) as visitors_count
                FROM frame_data 
                WHERE {where_clause}
                GROUP BY day_of_week, hour
                ORDER BY day_of_week, hour
            ''', params)

            results = cursor.fetchall()

            # Преобразуем числовые дни недели в названия
            day_names = {
                0: "Воскресенье",
                1: "Понедельник",
                2: "Вторник",
                3: "Среда",
                4: "Четверг",
                5: "Пятница",
                6: "Суббота"
            }

            # Организуем данные по дням недели и часам
            hourly_data = {}

            for day_num in range(7):
                day_name = day_names[day_num]
                hourly_data[day_name] = {}

                for hour in range(24):
                    hour_str = f"{hour:02d}:00"
                    hourly_data[day_name][hour_str] = 0

            # Заполняем данными из запроса
            for row in results:
                day_num, hour, visitors_count = row
                day_name = day_names[int(day_num)]
                hour_str = f"{int(hour):02d}:00"
                hourly_data[day_name][hour_str] = visitors_count

            return hourly_data
    except Exception as e:
        print(f"Error getting detailed peak hours: {e}")
        return {}
    finally:
        self.connection_pool.putconn(conn)


def get_waiters_stats(self, start_date=None, end_date=None, max_frame_id=None):
    """
    Возвращает статистику официантов
    """
    conn = self.connection_pool.getconn()
    try:
        with conn.cursor() as cursor:
            # Формируем условия WHERE в зависимости от переданных параметров
            where_conditions = ["person_type = 'waiter'"]
            params = []

            if start_date:
                where_conditions.append("timestamp::date >= %s")
                params.append(start_date)

            if end_date:
                where_conditions.append("timestamp::date <= %s")
                params.append(end_date)

            if max_frame_id:
                where_conditions.append("frame_id <= %s")
                params.append(max_frame_id)

            # Формируем SQL запрос
            where_clause = " AND ".join(where_conditions)

            # Получаем данные об официантах
            cursor.execute(f'''
                SELECT 
                    w.track_id,
                    w.name,
                    COUNT(DISTINCT c.track_id) as clients_served,
                    EXTRACT(EPOCH FROM (MAX(w.timestamp) - MIN(w.timestamp))) / 3600 as working_hours
                FROM frame_data w
                LEFT JOIN frame_data c ON c.person_type = 'customer'
                WHERE {where_clause}
                GROUP BY w.track_id, w.name
                ORDER BY clients_served DESC
            ''', params)

            results = cursor.fetchall()
            waiters_data = []

            # Получаем данные об эмоциях клиентов для каждого официанта
            for row in results:
                track_id, name, clients_served, working_hours = row

                # Дополнительный запрос для получения эмоций клиентов
                cursor.execute(f'''
                    SELECT 
                        c.emotion,
                        COUNT(*) as count
                    FROM frame_data w
                    JOIN frame_data c ON c.person_type = 'customer' AND c.emotion IS NOT NULL
                    WHERE w.track_id = %s
                    GROUP BY c.emotion
                ''', (track_id,))

                emotion_results = cursor.fetchall()
                client_emotions = {}

                for emotion_row in emotion_results:
                    emotion, count = emotion_row
                    client_emotions[emotion] = count

                waiters_data.append({
                    "track_id": track_id,
                    "name": name,
                    "clients_served": clients_served,
                    "working_hours": working_hours if working_hours else 0,
                    "client_emotions": client_emotions
                })

            return waiters_data
    except Exception as e:
        print(f"Error getting waiters stats: {e}")
        return []
    finally:
        self.connection_pool.putconn(conn)


def get_waiter_load(self, start_date=None, end_date=None, max_frame_id=None):
    """
    Возвращает данные о нагрузке официантов
    """
    conn = self.connection_pool.getconn()
    try:
        with conn.cursor() as cursor:
            # Формируем условия WHERE в зависимости от переданных параметров
            where_conditions = ["person_type = 'waiter'"]
            params = []

            if start_date:
                where_conditions.append("timestamp::date >= %s")
                params.append(start_date)

            if end_date:
                where_conditions.append("timestamp::date <= %s")
                params.append(end_date)

            if max_frame_id:
                where_conditions.append("frame_id <= %s")
                params.append(max_frame_id)

            # Формируем SQL запрос
            where_clause = " AND ".join(where_conditions)

            # Получаем данные о нагрузке официантов
            cursor.execute(f'''
                SELECT 
                    w.track_id,
                    w.name,
                    COUNT(DISTINCT c.track_id) as clients_served
                FROM frame_data w
                LEFT JOIN frame_data c ON c.person_type = 'customer'
                WHERE {where_clause}
                GROUP BY w.track_id, w.name
                ORDER BY clients_served DESC
            ''', params)

            results = cursor.fetchall()
            load_data = []

            for row in results:
                track_id, name, clients_served = row
                load_data.append({
                    "track_id": track_id,
                    "name": name if name else f"Официант #{track_id}",
                    "clients_served": clients_served
                })

            return load_data
    except Exception as e:
        print(f"Error getting waiter load: {e}")
        return []
    finally:
        self.connection_pool.putconn(conn)


def get_waiter_efficiency(self, start_date=None, end_date=None, max_frame_id=None):
    """
    Возвращает данные об эффективности официантов
    """
    # Используем ту же функцию, что и для get_waiters_stats,
    # так как эффективность рассчитывается на основе тех же данных
    return self.get_waiters_stats(start_date, end_date, max_frame_id)


def get_celebrity_impact(self, start_date=None, end_date=None, max_frame_id=None):
    """
    Возвращает данные о влиянии знаменитостей
    """
    conn = self.connection_pool.getconn()
    try:
        with conn.cursor() as cursor:
            # Формируем условия WHERE в зависимости от переданных параметров
            where_conditions = []
            params = []

            if start_date:
                where_conditions.append("timestamp::date >= %s")
                params.append(start_date)

            if end_date:
                where_conditions.append("timestamp::date <= %s")
                params.append(end_date)

            if max_frame_id:
                where_conditions.append("frame_id <= %s")
                params.append(max_frame_id)

            # Формируем SQL запрос
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            # Получаем данные о посещениях по дням
            cursor.execute(f'''
                SELECT 
                    timestamp::date as date, 
                    COUNT(DISTINCT track_id) as visitor_count
                FROM frame_data 
                WHERE {where_clause}
                GROUP BY date
                ORDER BY date
            ''', params)

            results = cursor.fetchall()
            timeline_data = []

            # Получаем данные о визитах знаменитостей
            cursor.execute(f'''
                SELECT 
                    timestamp::date as date,
                    name
                FROM frame_data 
                WHERE {where_clause} AND person_type = 'celebrity'
                GROUP BY date, name
                ORDER BY date
            ''', params)

            celebrity_visits = {}
            for row in cursor.fetchall():
                date, name = row
                date_str = date.isoformat()
                if date_str not in celebrity_visits:
                    celebrity_visits[date_str] = []
                celebrity_visits[date_str].append(name)

            # Объединяем данные
            for row in results:
                date, visitor_count = row
                date_str = date.isoformat()

                timeline_entry = {
                    "date": date_str,
                    "visitor_count": visitor_count,
                    "celebrity_visit": False,
                    "celebrity_name": None
                }

                if date_str in celebrity_visits:
                    timeline_entry["celebrity_visit"] = True
                    timeline_entry["celebrity_name"] = celebrity_visits[date_str][0]  # Берем первую знаменитость

                timeline_data.append(timeline_entry)

            return timeline_data
    except Exception as e:
        print(f"Error getting celebrity impact: {e}")
        return []
    finally:
        self.connection_pool.putconn(conn)


def get_celebrity_visits(self, start_date=None, end_date=None, max_frame_id=None):
    """
    Возвращает данные о визитах знаменитостей
    """
    conn = self.connection_pool.getconn()
    try:
        with conn.cursor() as cursor:
            # Формируем условия WHERE в зависимости от переданных параметров
            where_conditions = ["person_type = 'celebrity'"]
            params = []

            if start_date:
                where_conditions.append("timestamp::date >= %s")
                params.append(start_date)

            if end_date:
                where_conditions.append("timestamp::date <= %s")
                params.append(end_date)

            if max_frame_id:
                where_conditions.append("frame_id <= %s")
                params.append(max_frame_id)

            # Формируем SQL запрос
            where_clause = " AND ".join(where_conditions)

            # Получаем данные о визитах знаменитостей
            cursor.execute(f'''
                SELECT 
                    timestamp::date as date,
                    name as celebrity_name,
                    EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp))) / 60 as duration
                FROM frame_data 
                WHERE {where_clause}
                GROUP BY date, name
                ORDER BY date DESC
            ''', params)

            results = cursor.fetchall()
            visits_data = []

            # Для каждого визита знаменитости получаем количество посетителей в тот день
            for row in results:
                date, celebrity_name, duration = row

                # Дополнительный запрос для получения количества посетителей в день визита
                cursor.execute('''
                    SELECT 
                        COUNT(DISTINCT track_id) as visitor_count
                    FROM frame_data 
                    WHERE timestamp::date = %s
                ''', (date,))

                visitor_count = cursor.fetchone()[0]

                # Дополнительный запрос для получения среднего количества посетителей
                cursor.execute('''
                    SELECT 
                        AVG(daily_count) as avg_visitors
                    FROM (
                        SELECT 
                            timestamp::date as date,
                            COUNT(DISTINCT track_id) as daily_count
                        FROM frame_data 
                        GROUP BY date
                    ) as daily_stats
                ''')

                avg_visitors = cursor.fetchone()[0]

                # Рассчитываем процент роста
                growth = ((visitor_count - avg_visitors) / avg_visitors) * 100 if avg_visitors else 0

                visits_data.append({
                    "date": date.isoformat(),
                    "celebrity_name": celebrity_name,
                    "duration": round(duration) if duration else 0,
                    "visitor_count": visitor_count,
                    "growth": round(growth, 1)
                })

            return visits_data
    except Exception as e:
        print(f"Error getting celebrity visits: {e}")
        return []
    finally:
        self.connection_pool.putconn(conn)


def get_satisfaction_correlation(self, start_date=None, end_date=None, person_type=None, max_frame_id=None):
    """
    Возвращает данные о корреляции эмоций с удовлетворенностью
    """
    conn = self.connection_pool.getconn()
    try:
        with conn.cursor() as cursor:
            # Формируем условия WHERE в зависимости от переданных параметров
            where_conditions = []
            params = []

            if start_date:
                where_conditions.append("timestamp::date >= %s")
                params.append(start_date)

            if end_date:
                where_conditions.append("timestamp::date <= %s")
                params.append(end_date)

            if person_type:
                where_conditions.append("person_type = %s")
                params.append(person_type)

            if max_frame_id:
                where_conditions.append("frame_id <= %s")
                params.append(max_frame_id)

            # Формируем SQL запрос
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            # В реальной системе здесь был бы запрос, который объединяет
            # данные об эмоциях посетителей и данные удовлетворенности (например, из опросов)
            # Для демонстрации создаем симулированные данные

            # Получаем данные об эмоциях по дням
            cursor.execute(f'''
                SELECT 
                    timestamp::date as date,
                    emotion,
                    COUNT(*) as count
                FROM frame_data 
                WHERE {where_clause} AND emotion IS NOT NULL
                GROUP BY date, emotion
                ORDER BY date, emotion
            ''', params)

            results = cursor.fetchall()

            # Веса эмоций от 1 до 5 (от негативных к позитивным)
            emotion_weights = {
                "angry": 1,
                "sad": 2,
                "neutral": 3,
                "surprised": 4,
                "happy": 5
            }

            # Преобразуем данные для расчета средней оценки эмоций по дням
            emotions_by_date = {}
            for row in results:
                date, emotion, count = row
                date_str = date.isoformat()

                if date_str not in emotions_by_date:
                    emotions_by_date[date_str] = {}

                emotions_by_date[date_str][emotion] = count

            # Рассчитываем среднюю оценку эмоций и симулируем оценки удовлетворенности
            correlation_data = []
            emotions_scores = []
            satisfaction_scores = []

            for date_str, emotions in emotions_by_date.items():
                total_weight = 0
                total_count = 0

                for emotion, count in emotions.items():
                    if emotion in emotion_weights:
                        total_weight += emotion_weights[emotion] * count
                        total_count += count

                # Средняя оценка эмоций (от 1 до 5)
                average_emotion_score = total_weight / total_count if total_count > 0 else 3

                # Симулируем оценку удовлетворенности (от 1 до 10)
                # с некоторой корреляцией с эмоциями плюс случайный шум
                satisfaction_score = (average_emotion_score * 1.8) + np.random.normal(0, 0.5)
                satisfaction_score = max(1, min(10, satisfaction_score))

                correlation_data.append({
                    "date": date_str,
                    "average_emotion_score": round(average_emotion_score, 2),
                    "satisfaction_score": round(satisfaction_score, 2)
                })

                emotions_scores.append(average_emotion_score)
                satisfaction_scores.append(satisfaction_score)

            # Рассчитываем коэффициент корреляции Пирсона
            correlation_coefficient = 0
            if len(emotions_scores) > 1:
                correlation_coefficient = np.corrcoef(emotions_scores, satisfaction_scores)[0, 1]

            return correlation_data, correlation_coefficient
    except Exception as e:
        print(f"Error getting satisfaction correlation: {e}")
        return [], 0
    finally:
        self.connection_pool.putconn(conn)


def get_period_stats(self, start_date, end_date, person_type=None):
    """
    Возвращает статистику за указанный период
    """
    # Получаем общую статистику
    overall_stats = self.get_overall_stats(start_date, end_date, person_type)

    # Получаем распределение по полу
    gender_stats = self.get_gender_stats(start_date, end_date, person_type)

    # Получаем распределение эмоций
    emotion_stats = self.get_emotions_stats(start_date, end_date, person_type)

    # Объединяем все данные
    return {
        "total_visitors": overall_stats["total_visitors"],
        "unique_visitors": overall_stats["unique_visitors"],
        "average_age": overall_stats["average_age"],
        "gender_distribution": gender_stats,
        "emotion_distribution": emotion_stats
    }
from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import json

app = Flask(__name__)
CORS(app)  # Разрешаем CORS для всех маршрутов

# Настройки подключения к базе данных
DB_CONFIG = {
    "dbname": "ulugbek_db",
    "user": "ulugbek",
    "password": "123",
    "host": "localhost",
    "port": "5432"
}


def get_db_connection():
    """Создает соединение с базой данных"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Ошибка подключения к базе данных: {e}")
        return None


@app.route('/api/stats/summary', methods=['GET'])
def get_summary_stats():
    """Получить общую статистику"""
    date_filter = request.args.get('period', 'today')

    # Определяем временной диапазон для фильтрации
    now = datetime.now()
    if date_filter == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_filter == 'yesterday':
        start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_filter == 'week':
        start_date = (now - timedelta(days=7))
    elif date_filter == 'month':
        start_date = (now - timedelta(days=30))
    else:
        start_date = (now - timedelta(days=1))

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Получаем общее количество распознаваний
            if date_filter == 'yesterday':
                cursor.execute("""
                    SELECT COUNT(DISTINCT track_id) as total_detections
                    FROM frame_data
                    WHERE timestamp >= %s AND timestamp < %s
                """, (start_date, end_date))
            else:
                cursor.execute("""
                    SELECT COUNT(DISTINCT track_id) as total_detections
                    FROM frame_data
                    WHERE timestamp >= %s
                """, (start_date,))

            total_result = cursor.fetchone()

            # Получаем распределение по типам посетителей
            if date_filter == 'yesterday':
                cursor.execute("""
                    SELECT person_type, COUNT(DISTINCT track_id) as count
                    FROM frame_data
                    WHERE timestamp >= %s AND timestamp < %s
                    GROUP BY person_type
                """, (start_date, end_date))
            else:
                cursor.execute("""
                    SELECT person_type, COUNT(DISTINCT track_id) as count
                    FROM frame_data
                    WHERE timestamp >= %s
                    GROUP BY person_type
                """, (start_date,))

            person_types_result = cursor.fetchall()

            # Получаем распределение по возрастным группам
            if date_filter == 'yesterday':
                cursor.execute("""
                    SELECT 
                        CASE 
                            WHEN age BETWEEN 0 AND 17 THEN '0-17'
                            WHEN age BETWEEN 18 AND 25 THEN '18-25'
                            WHEN age BETWEEN 26 AND 35 THEN '26-35'
                            WHEN age BETWEEN 36 AND 45 THEN '36-45'
                            WHEN age BETWEEN 46 AND 60 THEN '46-60'
                            WHEN age > 60 THEN '60+'
                        END as age_group,
                        COUNT(DISTINCT track_id) as count
                    FROM frame_data
                    WHERE timestamp >= %s AND timestamp < %s AND age IS NOT NULL
                    GROUP BY age_group
                    ORDER BY age_group
                """, (start_date, end_date))
            else:
                cursor.execute("""
                    SELECT 
                        CASE 
                            WHEN age BETWEEN 0 AND 17 THEN '0-17'
                            WHEN age BETWEEN 18 AND 25 THEN '18-25'
                            WHEN age BETWEEN 26 AND 35 THEN '26-35'
                            WHEN age BETWEEN 36 AND 45 THEN '36-45'
                            WHEN age BETWEEN 46 AND 60 THEN '46-60'
                            WHEN age > 60 THEN '60+'
                        END as age_group,
                        COUNT(DISTINCT track_id) as count
                    FROM frame_data
                    WHERE timestamp >= %s AND age IS NOT NULL
                    GROUP BY age_group
                    ORDER BY age_group
                """, (start_date,))

            age_groups_result = cursor.fetchall()

            # Получаем распределение по полу
            if date_filter == 'yesterday':
                cursor.execute("""
                    SELECT 
                        gender,
                        COUNT(DISTINCT track_id) as count
                    FROM frame_data
                    WHERE timestamp >= %s AND timestamp < %s AND gender IS NOT NULL
                    GROUP BY gender
                """, (start_date, end_date))
            else:
                cursor.execute("""
                    SELECT 
                        gender,
                        COUNT(DISTINCT track_id) as count
                    FROM frame_data
                    WHERE timestamp >= %s AND gender IS NOT NULL
                    GROUP BY gender
                """, (start_date,))

            gender_result = cursor.fetchall()

            # Получаем распределение по эмоциям
            if date_filter == 'yesterday':
                cursor.execute("""
                    SELECT 
                        emotion,
                        COUNT(DISTINCT track_id) as count
                    FROM frame_data
                    WHERE timestamp >= %s AND timestamp < %s AND emotion IS NOT NULL
                    GROUP BY emotion
                """, (start_date, end_date))
            else:
                cursor.execute("""
                    SELECT 
                        emotion,
                        COUNT(DISTINCT track_id) as count
                    FROM frame_data
                    WHERE timestamp >= %s AND emotion IS NOT NULL
                    GROUP BY emotion
                """, (start_date,))

            emotion_result = cursor.fetchall()

            # Получаем данные по временной шкале (разбивка по часам)
            if date_filter == 'yesterday':
                cursor.execute("""
                    SELECT 
                        to_char(timestamp, 'HH24:00') as time_hour,
                        person_type,
                        COUNT(DISTINCT track_id) as count
                    FROM frame_data
                    WHERE timestamp >= %s AND timestamp < %s
                    GROUP BY time_hour, person_type
                    ORDER BY time_hour
                """, (start_date, end_date))
            else:
                cursor.execute("""
                    SELECT 
                        to_char(timestamp, 'HH24:00') as time_hour,
                        person_type,
                        COUNT(DISTINCT track_id) as count
                    FROM frame_data
                    WHERE timestamp >= %s
                    GROUP BY time_hour, person_type
                    ORDER BY time_hour
                """, (start_date,))

            timeline_result = cursor.fetchall()

            # Форматируем данные временной шкалы в удобный для фронтенда формат
            timeline_data = {}
            for row in timeline_result:
                hour = row['time_hour']
                person_type = row['person_type']
                count = row['count']

                if hour not in timeline_data:
                    timeline_data[hour] = {'time': hour, 'customers': 0, 'waiters': 0, 'celebrities': 0}

                if person_type == 'customer':
                    timeline_data[hour]['customers'] += count
                elif person_type == 'waiter':
                    timeline_data[hour]['waiters'] += count
                elif person_type == 'celebrity':
                    timeline_data[hour]['celebrities'] += count

            # Получаем последние обнаруженные лица
            cursor.execute("""
                SELECT 
                    frame_data.track_id,
                    frame_data.name,
                    frame_data.age,
                    frame_data.gender,
                    frame_data.emotion,
                    frame_data.person_type,
                    to_char(frame_data.timestamp, 'HH24:MI') as time
                FROM frame_data
                WHERE frame_data.is_frontal = true
                ORDER BY frame_data.timestamp DESC
                LIMIT 10
            """)

            recent_detections = cursor.fetchall()

            # Формируем итоговый объект с данными
            result = {
                "totalDetections": total_result['total_detections'] if total_result else 0,
                "personTypes": [
                    {
                        "name": "Клиенты",
                        "value": next((r['count'] for r in person_types_result if r['person_type'] == 'customer'), 0),
                        "type": "customer"
                    },
                    {
                        "name": "Персонал",
                        "value": next((r['count'] for r in person_types_result if r['person_type'] == 'waiter'), 0),
                        "type": "waiter"
                    },
                    {
                        "name": "VIP-гости",
                        "value": next((r['count'] for r in person_types_result if r['person_type'] == 'celebrity'), 0),
                        "type": "celebrity"
                    }
                ],
                "ageGroups": [
                    {"name": group['age_group'], "value": group['count']}
                    for group in age_groups_result
                ],
                "genderStats": [
                    {"name": "Мужчины" if row['gender'] == 'male' else "Женщины", "value": row['count']}
                    for row in gender_result
                ],
                "emotionStats": [
                    {"name": row['emotion'].capitalize(), "value": row['count']}
                    for row in emotion_result
                ],
                "timelineData": list(timeline_data.values()),
                "recentDetections": [
                    {
                        "id": row['track_id'],
                        "name": row['name'],
                        "age": row['age'],
                        "gender": "Мужской" if row['gender'] == 'male' else "Женский",
                        "emotion": row['emotion'].capitalize(),
                        "type": row['person_type'],
                        "time": row['time']
                    }
                    for row in recent_detections
                ]
            }

            return jsonify(result)

    except Exception as e:
        print(f"Ошибка при получении статистики: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route('/api/known-faces', methods=['GET'])
def get_known_faces():
    """Получить список известных лиц из базы данных"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, name, person_type, registered_date
                FROM known_faces
                ORDER BY registered_date DESC
            """)

            faces = cursor.fetchall()

            # Преобразуем datetime в строки для JSON
            for face in faces:
                if face['registered_date']:
                    face['registered_date'] = face['registered_date'].strftime('%d.%m.%Y')

            return jsonify(faces)

    except Exception as e:
        print(f"Ошибка при получении списка известных лиц: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route('/api/known-faces/<int:face_id>', methods=['DELETE'])
def delete_known_face(face_id):
    """Удалить известное лицо из базы данных"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM known_faces WHERE id = %s", (face_id,))
            conn.commit()

            return jsonify({"success": True, "message": f"Лицо с ID {face_id} успешно удалено"})

    except Exception as e:
        conn.rollback()
        print(f"Ошибка при удалении лица: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route('/api/stats/demographics', methods=['GET'])
def get_demographics():
    """Получить демографические данные"""
    date_filter = request.args.get('period', 'today')

    # Определяем временной диапазон для фильтрации
    now = datetime.now()
    if date_filter == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_filter == 'yesterday':
        start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_filter == 'week':
        start_date = (now - timedelta(days=7))
    elif date_filter == 'month':
        start_date = (now - timedelta(days=30))
    else:
        start_date = (now - timedelta(days=1))

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Получаем средний возраст
            if date_filter == 'yesterday':
                cursor.execute("""
                    SELECT AVG(age) as avg_age
                    FROM frame_data
                    WHERE timestamp >= %s AND timestamp < %s AND age IS NOT NULL
                """, (start_date, end_date))
            else:
                cursor.execute("""
                    SELECT AVG(age) as avg_age
                    FROM frame_data
                    WHERE timestamp >= %s AND age IS NOT NULL
                """, (start_date,))

            avg_age_result = cursor.fetchone()

            # Получаем наиболее частую эмоцию
            if date_filter == 'yesterday':
                cursor.execute("""
                    SELECT emotion, COUNT(*) as count
                    FROM frame_data
                    WHERE timestamp >= %s AND timestamp < %s AND emotion IS NOT NULL
                    GROUP BY emotion
                    ORDER BY count DESC
                    LIMIT 1
                """, (start_date, end_date))
            else:
                cursor.execute("""
                    SELECT emotion, COUNT(*) as count
                    FROM frame_data
                    WHERE timestamp >= %s AND emotion IS NOT NULL
                    GROUP BY emotion
                    ORDER BY count DESC
                    LIMIT 1
                """, (start_date,))

            top_emotion_result = cursor.fetchone()

            # Вычисляем соотношение мужчин/женщин
            if date_filter == 'yesterday':
                cursor.execute("""
                    SELECT 
                        SUM(CASE WHEN gender = 'male' THEN 1 ELSE 0 END) as male_count,
                        SUM(CASE WHEN gender = 'female' THEN 1 ELSE 0 END) as female_count
                    FROM (
                        SELECT DISTINCT track_id, gender
                        FROM frame_data
                        WHERE timestamp >= %s AND timestamp < %s AND gender IS NOT NULL
                    ) as distinct_gender
                """, (start_date, end_date))
            else:
                cursor.execute("""
                    SELECT 
                        SUM(CASE WHEN gender = 'male' THEN 1 ELSE 0 END) as male_count,
                        SUM(CASE WHEN gender = 'female' THEN 1 ELSE 0 END) as female_count
                    FROM (
                        SELECT DISTINCT track_id, gender
                        FROM frame_data
                        WHERE timestamp >= %s AND gender IS NOT NULL
                    ) as distinct_gender
                """, (start_date,))

            gender_ratio_result = cursor.fetchone()

            # Получаем общее количество обнаружений эмоций для расчета процентного соотношения
            if date_filter == 'yesterday':
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM frame_data
                    WHERE timestamp >= %s AND timestamp < %s AND emotion IS NOT NULL
                """, (start_date, end_date))
            else:
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM frame_data
                    WHERE timestamp >= %s AND emotion IS NOT NULL
                """, (start_date,))

            total_emotions = cursor.fetchone()['total']

            # Формируем результат
            result = {
                "avgAge": round(avg_age_result['avg_age'], 1) if avg_age_result and avg_age_result['avg_age'] else None,
                "topEmotion": {
                    "name": top_emotion_result['emotion'].capitalize() if top_emotion_result else None,
                    "percentage": round((top_emotion_result['count'] / total_emotions * 100),
                                        0) if top_emotion_result and total_emotions else 0
                },
                "genderRatio": {
                    "male": gender_ratio_result['male_count'] if gender_ratio_result else 0,
                    "female": gender_ratio_result['female_count'] if gender_ratio_result else 0,
                    "ratio": f"{round(gender_ratio_result['male_count'] / gender_ratio_result['female_count'], 2)}:1"
                    if gender_ratio_result and gender_ratio_result['female_count'] > 0 else "N/A"
                }
            }

            return jsonify(result)

    except Exception as e:
        print(f"Ошибка при получении демографических данных: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
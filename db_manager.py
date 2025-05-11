import numpy as np

np.float = float
from PIL import Image
from datetime import datetime
import psycopg2
from psycopg2 import pool
import numpy as np


# Константы для типов людей
PERSON_TYPE_CUSTOMER = 'customer'
PERSON_TYPE_WAITER = 'waiter'
PERSON_TYPE_CELEBRITY = 'celebrity'

class DatabaseManager:
    """
    Manages database connections and operations using connection pooling
    """

    def __init__(self, dbname, user, password, host="localhost", port="5432", min_conn=1, max_conn=10):
        self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
            min_conn,
            max_conn,
            user=user,
            password=password,
            host=host,
            port=port,
            database=dbname
        )
        self.init_db()

    def init_db(self):
        """Initialize database tables if they don't exist and add any missing columns"""
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Create customers table if it doesn't exist
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS detected_id (
                        id SERIAL PRIMARY KEY,
                        track_id INTEGER NOT NULL,
                        frame_id INTEGER NOT NULL,
                        name TEXT,
                        age INTEGER,
                        gender TEXT,
                        emotion TEXT,
                        face_top INTEGER,
                        face_right INTEGER,
                        face_bottom INTEGER,
                        face_left INTEGER,
                        body_top INTEGER,
                        body_right INTEGER,
                        body_bottom INTEGER,
                        body_left INTEGER,
                        person_type TEXT DEFAULT 'customer',
                        timestamp TIMESTAMP
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS detected_things (
                        id SERIAL PRIMARY KEY,
                        frame_id INTEGER NOT NULL,
                        class text NOT NULL,
                        class_id INTEGER NOT NULL,
                        x1 INTEGER,
                        y1 INTEGER,
                        x2 INTEGER,
                        y2 INTEGER,
                        conf FLOAT,
                        timestamp TIMESTAMP
                                    )
                                ''')

                # Create known_faces table for storing registered faces if it doesn't exist
                # Добавление поля person_type для указания типа человека (customer, waiter, celebrity)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS known_faces (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        face_encoding BYTEA NOT NULL,
                        person_type TEXT DEFAULT 'customer',
                        registered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS frame_data (
                        id SERIAL PRIMARY KEY,
                        frame_id INTEGER NOT NULL,
                        track_id INTEGER NOT NULL,
                        name TEXT,
                        age INTEGER,
                        gender TEXT,
                        emotion TEXT,
                        face_top INTEGER,
                        face_right INTEGER,
                        face_bottom INTEGER,
                        face_left INTEGER,
                        body_top INTEGER,
                        body_right INTEGER,
                        body_bottom INTEGER,
                        body_left INTEGER,
                        is_frontal BOOLEAN,
                        person_type TEXT DEFAULT 'customer',
                        timestamp TIMESTAMP
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS frames (
                        id SERIAL PRIMARY KEY,
                        frame_path VARCHAR NOT NULL,
                        processed BOOLEAN NOT NULL,
                        timestamp TIMESTAMP
                    )
                ''')

                conn.commit()
        except Exception as e:
            print(f"Database initialization error: {e}")
            conn.rollback()
        finally:
            self.connection_pool.putconn(conn)

    def save_frame_data(self, frame_id, track_id, face_data, visible, person_type=PERSON_TYPE_CUSTOMER):
        """Save data for each frame to the frame_data table"""
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cursor:
                name = face_data.get("name", "unknown")

                # Преобразуем numpy.int64 в стандартный Python int
                age = int(face_data.get("age")) if face_data.get("age") is not None else None
                gender = face_data.get("gender")
                emotion = face_data.get("emotion")

                # Face location
                face_location = face_data.get("face_location", (None, None, None, None))
                if face_location and len(face_location) == 4:
                    # Преобразуем numpy.int64 в стандартный Python int
                    top = int(face_location[0]) if face_location[0] is not None else None
                    right = int(face_location[1]) if face_location[1] is not None else None
                    bottom = int(face_location[2]) if face_location[2] is not None else None
                    left = int(face_location[3]) if face_location[3] is not None else None
                else:
                    top, right, bottom, left = None, None, None, None

                # Body location - преобразуем numpy.int64 в стандартный Python int
                body_top = int(face_data.get("body_top")) if face_data.get("body_top") is not None else None
                body_right = int(face_data.get("body_right")) if face_data.get("body_right") is not None else None
                body_bottom = int(face_data.get("body_bottom")) if face_data.get("body_bottom") is not None else None
                body_left = int(face_data.get("body_left")) if face_data.get("body_left") is not None else None

                timestamp = datetime.now()

                # Преобразуем frame_id и track_id в стандартный Python int
                if frame_id is not None:
                    frame_id = int(frame_id)
                if track_id is not None:
                    track_id = int(track_id)

                try:
                    cursor.execute('''
                        INSERT INTO frame_data 
                        (frame_id, track_id, name, age, gender, emotion, 
                         face_top, face_right, face_bottom, face_left, 
                         body_top, body_right, body_bottom, body_left,
                         is_frontal, person_type, timestamp)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (frame_id, track_id, name, age, gender, emotion,
                          top, right, bottom, left,
                          body_top, body_right, body_bottom, body_left,
                          visible, person_type, timestamp))



                    conn.commit()
                except Exception as e:
                    print(e)
        except Exception as e:
            print(f"Error saving frame data: {e}")
            conn.rollback()
        finally:
            self.connection_pool.putconn(conn)

    def write_detection_to_db(self, frame_id, class_name, class_id, x1, y1, x2, y2, confidence, timestamp=None):
        """Write information about detected objects to the database"""
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # print(frame_id, class_name, class_id, x1, y1, x2, y2, confidence)
                # Uncomment and use these conversions - they are needed!
                if frame_id is not None:
                    frame_id = int(frame_id)  # Convert numpy.int64 to Python int
                if class_id is not None:
                    class_id = int(class_id)  # Convert numpy.int64 to Python int
                if x1 is not None:
                    x1 = int(x1)
                if y1 is not None:
                    y1 = int(y1)
                if x2 is not None:
                    x2 = int(x2)
                if y2 is not None:
                    y2 = int(y2)
                if confidence is not None:
                    confidence = float(confidence)

                # Use current timestamp if none provided
                if timestamp is None:
                    timestamp = datetime.now()

                try:
                    cursor.execute('''
                        INSERT INTO detected_things 
                        (frame_id, class, class_id, x1, y1, x2, y2, conf, timestamp)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    ''', (frame_id, class_name, class_id, x1, y1, x2, y2, confidence, timestamp))
                    # print(frame_id, class_name, class_id, x1, y1, x2, y2, confidence, timestamp)

                    # inserted_id = cursor.fetchone()[0]
                    # print(inserted_id)
                    conn.commit()
                    # return inserted_id
                except Exception as e:
                    print(f"Error inserting detection: {e}")
                    conn.rollback()  # Add this to ensure rollback on error

        except Exception as e:
            print(f"Error writing detection to database: {e}")
            conn.rollback()
        finally:
            self.connection_pool.putconn(conn)

    def update_by_track_id(self, track_id, updates: dict):
        """Update any fields in 'detected_id' table for a given track_id"""
        if not updates:
            print("No updates provided.")
            return

        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Генерируем динамически SET-часть запроса
                set_clause = ', '.join([f"{key} = %s" for key in updates])
                values = list(updates.values())
                values.append(track_id)  # Добавляем track_id в конец

                query = f'''
                    UPDATE detected_id
                    SET {set_clause}
                    WHERE track_id = %s
                '''

                cursor.execute(query, values)
                conn.commit()
                print(f"Updated track_id {track_id} with fields: {list(updates.keys())}")
        except Exception as e:
            print(f"Error updating fields: {e}")
        finally:
            self.connection_pool.putconn(conn)

    def get_frame_data(self, track_id):
        """Get stored data for a specific frame and track_id"""
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT name, age, gender, emotion, person_type,
                           face_top, face_right, face_bottom, face_left,
                           body_top, body_right, body_bottom, body_left
                    FROM detected_id
                    WHERE track_id = %s
                ''', (track_id,))  # Notice the trailing comma here to make it a tuple

                result = cursor.fetchone()
                if result:
                    name, age, gender, emotion, person_type, \
                        face_top, face_right, face_bottom, face_left, \
                        body_top, body_right, body_bottom, body_left = result

                    return {
                        "name": name,
                        "age": age,
                        "gender": gender,
                        "emotion": emotion,
                        "person_type": person_type,
                        "face_location": (face_top, face_right, face_bottom, face_left),
                        "body_top": body_top,
                        "body_right": body_right,
                        "body_bottom": body_bottom,
                        "body_left": body_left
                    }
                return None
        except Exception as e:
            print(f"Error retrieving frame data: {e}")
            return None
        finally:
            self.connection_pool.putconn(conn)

    def get_unprocessed_frames(self):
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT id, frame_path, timestamp
                    FROM frames
                    WHERE processed = %s
                ''', (0,))

                result = cursor.fetchall()
                if result:
                    return [
                        {
                            "id": row[0],
                            "frame_path": row[1],
                            "timestamp": row[2],
                        }
                        for row in result
                    ]
                return []
        except Exception as e:
            print(f"Error retrieving frames: {e}")
            return []
        finally:
            self.connection_pool.putconn(conn)

    """Mark a frame as processed in the database"""

    def mark_frame_as_processed(self, frame_id):
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    UPDATE frames
                    SET processed = %s
                    WHERE id = %s
                ''', (1, frame_id))
                conn.commit()
        except Exception as e:
            print(f"Error updating frame status: {e}")
        finally:
            self.connection_pool.putconn(conn)

    """Insert a new frame record into the database"""
    def insert_frame(self, frame_path, timestamp, processed=0):
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO frames (frame_path, timestamp, processed)
                    VALUES (%s, %s, %s)
                    RETURNING id
                ''', (frame_path, timestamp, processed))
                frame_id = cursor.fetchone()[0]
                conn.commit()
                return frame_id
        except Exception as e:
            print(f"Error inserting frame: {e}")
            return None
        finally:
            self.connection_pool.putconn(conn)

    def save_face_data(self, frame_id, track_id, face_data):
        """Save data for each frame to the frame_data table"""
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cursor:
                name = face_data.get("name", "unknown")

                # Преобразуем numpy.int64 в стандартный Python int
                age = int(face_data.get("age")) if face_data.get("age") is not None else None
                gender = face_data.get("gender")
                emotion = face_data.get("emotion")
                person_type = face_data.get("person_type")
                # Face location
                face_location = face_data.get("face_location", (None, None, None, None))
                if face_location and len(face_location) == 4:
                    # Преобразуем numpy.int64 в стандартный Python int
                    top = int(face_location[0]) if face_location[0] is not None else None
                    right = int(face_location[1]) if face_location[1] is not None else None
                    bottom = int(face_location[2]) if face_location[2] is not None else None
                    left = int(face_location[3]) if face_location[3] is not None else None
                else:
                    top, right, bottom, left = None, None, None, None

                # Body location - преобразуем numpy.int64 в стандартный Python int
                body_top = int(face_data.get("body_top")) if face_data.get("body_top") is not None else None
                body_right = int(face_data.get("body_right")) if face_data.get("body_right") is not None else None
                body_bottom = int(face_data.get("body_bottom")) if face_data.get("body_bottom") is not None else None
                body_left = int(face_data.get("body_left")) if face_data.get("body_left") is not None else None


                # Преобразуем frame_id и track_id в стандартный Python int
                if frame_id is not None:
                    frame_id = int(frame_id)
                if track_id is not None:
                    track_id = int(track_id)
                timestamp = datetime.now()
                try:
                    cursor.execute('''
                        INSERT INTO detected_id 
                        (frame_id, track_id, name, age, gender, emotion, 
                         face_top, face_right, face_bottom, face_left, 
                         body_top, body_right, body_bottom, body_left,
                         person_type, timestamp)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (frame_id, track_id, name, age, gender, emotion,
                          top, right, bottom, left,
                          body_top, body_right, body_bottom, body_left,
                          person_type, timestamp))

                    conn.commit()
                except Exception as e:
                    print(e)
        except Exception as e:
            print(f"Error saving frame data: {e}")
            conn.rollback()
        finally:
            self.connection_pool.putconn(conn)

    def register_known_face(self, name, face_encoding, person_type=PERSON_TYPE_CUSTOMER):
        """Register a known face in the database"""
        conn = self.connection_pool.getconn()
        try:
            # Convert numpy array to binary for storage
            face_encoding_binary = face_encoding.tobytes()

            with conn.cursor() as cursor:
                # Проверяем, существует ли колонка person_type в known_faces
                cursor.execute('''
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='known_faces' AND column_name='person_type'
                ''')
                has_person_type = cursor.fetchone() is not None

                if has_person_type:
                    cursor.execute('''
                            INSERT INTO known_faces (name, face_encoding, person_type)
                            VALUES (%s, %s, %s)
                        ''', (name, face_encoding_binary, person_type))
                else:
                    # Если колонки person_type нет, пробуем с is_waiter
                    is_waiter = (person_type == PERSON_TYPE_WAITER)
                    cursor.execute('''
                            INSERT INTO known_faces (name, face_encoding, is_waiter)
                            VALUES (%s, %s, %s)
                        ''', (name, face_encoding_binary, is_waiter))
                conn.commit()
        except Exception as e:
            print(f"Error registering face: {e}")
            conn.rollback()
        finally:
            self.connection_pool.putconn(conn)

    def get_known_faces(self):
        """Retrieve all known faces from database"""
        conn = self.connection_pool.getconn()
        known_faces = {'encodings': [], 'names': [], 'person_type': []}

        try:
            with conn.cursor() as cursor:
                # Пробуем сначала с новой структурой
                try:
                    cursor.execute('SELECT name, face_encoding, person_type FROM known_faces')
                    for name, face_encoding_binary, person_type in cursor.fetchall():
                        # Convert binary back to numpy array
                        face_encoding = np.frombuffer(face_encoding_binary, dtype=np.float64)
                        known_faces['encodings'].append(face_encoding)
                        known_faces['names'].append(name)
                        known_faces['person_type'].append(person_type)
                except psycopg2.Error:
                    # Если не получилось, используем старую структуру
                    cursor.execute('SELECT name, face_encoding, is_waiter FROM known_faces')
                    for name, face_encoding_binary, is_waiter in cursor.fetchall():
                        # Convert binary back to numpy array
                        face_encoding = np.frombuffer(face_encoding_binary, dtype=np.float64)
                        known_faces['encodings'].append(face_encoding)
                        known_faces['names'].append(name)
                        known_faces['person_type'].append(PERSON_TYPE_WAITER if is_waiter else PERSON_TYPE_CUSTOMER)
        except Exception as e:
            print(f"Error retrieving known faces: {e}")
        finally:
            self.connection_pool.putconn(conn)

        return known_faces

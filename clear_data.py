
import psycopg2

class DatabaseManager:
    def __init__(self, dbname, user, password, host):
        self.connection = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host
        )
        self.connection.autocommit = True
        self.cursor = self.connection.cursor()

    def clear_all_tables(self):
        self.cursor.execute("""
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                    EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' RESTART IDENTITY CASCADE';
                END LOOP;
            END;
            $$;
        """)
        print("✅ Все таблицы очищены (данные удалены, автоинкременты сброшены).")

    def close(self):
        self.cursor.close()
        self.connection.close()


import psycopg2


def delete_all_tables_postgres():
    try:
        # Подключение к базе данных
        conn = psycopg2.connect(
            dbname="ulugbek_db",
            user="ulugbek",
            password="123",
            host="localhost"
        )
        cursor = conn.cursor()

        # Временно отключаем ограничения
        cursor.execute("SET CONSTRAINTS ALL DEFERRED;")

        # Получаем список всех таблиц
        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
        tables = cursor.fetchall()

        # Удаляем каждую таблицу
        for table in tables:
            table_name = table[0]
            print(f"Удаление таблицы: {table_name}")
            cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;")

        # Восстанавливаем ограничения
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE;")

        # Фиксируем изменения
        conn.commit()
        print("Все таблицы успешно удалены.")

    except Exception as e:
        print(f"Произошла ошибка при удалении таблиц: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# Вызов функции
# delete_all_tables_postgres()
db_manager = DatabaseManager(
    dbname="ulugbek_db",
    user="ulugbek",
    password="123",
    host="localhost"
)

db_manager.clear_all_tables()
db_manager.close()




# Использование

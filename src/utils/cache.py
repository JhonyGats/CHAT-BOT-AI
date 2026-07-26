import sqlite3
import json
from datetime import datetime
import threading

class ChatCache:
    """
    Класс для кэширования данных приложения в SQLite базе данных
    Обеспечивает потокобезопасное хранение
    """
    def __init__(self):
        self.db_name = 'chat_cache.db'
        self.local = threading.local()
        self.create_tables()

    def get_connection(self):
        """
        Возвращает соединение с БД для текущего потока
        Если соединение ещё не создано – создаёт новое
        """
        if not hasattr(self.local, 'connection'):
            self.local.connection = sqlite3.connect(self.db_name)
        return self.local.connection

    def create_tables(self):
        """
        Создаёт все необходимые таблицы, если они ещё не существуют
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT,
                user_message TEXT,
                ai_response TEXT,
                timestamp DATETIME,
                tokens_used INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                model TEXT,
                message_length INTEGER,
                response_time FLOAT,
                tokens_used INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def save_message(self, model, user_message, ai_response, tokens_used):
        """
        Сохраняет одно сообщение (пользователь + ответ AI) в историю
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO messages (model, user_message, ai_response, timestamp, tokens_used)
            VALUES (?, ?, ?, ?, ?)
        ''', (model, user_message, ai_response, datetime.now(), tokens_used))
        conn.commit()

    def get_chat_history(self, limit=50):
        """
        Возвращает последние `limit` сообщений из истории, отсортированных
        по времени убывания (сначала новые)n
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM messages
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()

    def save_analytics(self, timestamp, model, message_length, response_time, tokens_used):
        """
        Сохраняет данные аналитики для одного сообщения
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO analytics_messages
            (timestamp, model, message_length, response_time, tokens_used)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, model, message_length, response_time, tokens_used))
        conn.commit()

    def get_analytics_history(self):
        """
        Возвращает все записи аналитики, отсортированные по времени (от старых к новым)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, model, message_length, response_time, tokens_used
            FROM analytics_messages
            ORDER BY timestamp ASC
        ''')
        return cursor.fetchall()

    def __del__(self):
        """
        Деструктор: закрывает соединение с БД, если оно было открыто в текущем потоке.
        """
        if hasattr(self.local, 'connection'):
            self.local.connection.close()

    def clear_history(self):
        """
        Полностью очищает таблицу messages
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM messages')
        conn.commit()

    def get_formatted_history(self):
        """
        Возвращает всю историю сообщений в виде списка словарей
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, model, user_message, ai_response, timestamp, tokens_used
            FROM messages
            ORDER BY timestamp ASC
        ''')
        history = []
        for row in cursor.fetchall():
            history.append({
                "id": row[0],
                "model": row[1],
                "user_message": row[2],
                "ai_response": row[3],
                "timestamp": row[4],
                "tokens_used": row[5]
            })
        return history

    # Методы для хранения настроек
    def save_setting(self, key: str, value: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        conn.commit()

    def get_setting(self, key: str, default=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        return row[0] if row else default

    def delete_setting(self, key: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM settings WHERE key = ?', (key,))
        conn.commit()
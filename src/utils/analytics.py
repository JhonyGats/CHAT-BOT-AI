import time
from datetime import datetime

class Analytics:
    """
    Класс для сбора, хранения и анализа статистики использования чата
    Данные сохраняются в SQLite через объект cache и загружаются при инициализации
    """
    def __init__(self, cache):
        """
        Инициализация системы аналитики
        """
        self.cache = cache
        self.start_time = time.time()
        self.model_usage = {}
        self.session_data = []
        self._load_historical_data()

    def _load_historical_data(self):
        """
        Загрузка данных аналитики из базы данных при инициализации
        """
        history = self.cache.get_analytics_history()
        for record in history:
            
            # Распаковка записи: временная метка, модель, длина сообщения, время ответа, токены
            timestamp, model, message_length, response_time, tokens_used = record
            
            # Если модель встречается впервые - инициализируем счётчики
            if model not in self.model_usage:
                self.model_usage[model] = {'count': 0, 'tokens': 0}
            
            # Обновляем статистику по модели
            self.model_usage[model]['count'] += 1
            self.model_usage[model]['tokens'] += tokens_used
            
            # Добавляем детальную запись в сессионные данные
            self.session_data.append({
                'timestamp': datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f'),
                'model': model,
                'message_length': message_length,
                'response_time': response_time,
                'tokens_used': tokens_used
            })

    def track_message(self, model: str, message_length: int, response_time: float, tokens_used: int):
        """
        Регистрирует новое сообщение в системе аналитики.

        """
        timestamp = datetime.now()
        
        # Сохраняем запись в базу данных через cache
        self.cache.save_analytics(timestamp, model, message_length, response_time, tokens_used)
        
        # Обновляем статистику по модели
        if model not in self.model_usage:
            self.model_usage[model] = {'count': 0, 'tokens': 0}
        self.model_usage[model]['count'] += 1
        self.model_usage[model]['tokens'] += tokens_used
        self.session_data.append({
            'timestamp': timestamp,
            'model': model,
            'message_length': message_length,
            'response_time': response_time,
            'tokens_used': tokens_used
        })

    def get_statistics(self) -> dict:
        """
        Вычисляет агрегированную статистику по текущей сессии и всей истории.
        
        """
        total_time = time.time() - self.start_time
        total_tokens = sum(model['tokens'] for model in self.model_usage.values())
        total_messages = sum(model['count'] for model in self.model_usage.values())
        return {
            'total_messages': total_messages,
            'total_tokens': total_tokens,
            'session_duration': total_time,
            
            # Вычисляем сообщения в минуту (избегаем деления на 0)
            'messages_per_minute': (total_messages * 60) / total_time if total_time > 0 else 0,
            'tokens_per_message': total_tokens / total_messages if total_messages > 0 else 0,
            'model_usage': self.model_usage
        }

    def export_data(self) -> list:
        """
        Экспортирует все детальные записи текущей сессии
        """
        return self.session_data

    def clear_data(self):
        """
        Очищает всю накопленную аналитику в памяти (модельную статистику и детальные записи)
        Это НЕ удаляет данные из базы данных, только сбрасывает текущую сессию
        """
        self.model_usage.clear()
        self.session_data.clear()
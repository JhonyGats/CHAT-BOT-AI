import logging
import os
from datetime import datetime

class AppLogger:
    """
    Класс для настройки и использования системы логирования
    Логи записываются одновременно:
      - В файл (в папку logs/, имя файла содержит дату)
      - В консоль (терминал)
    """
    def __init__(self):
        
        # Папка для хранения логов (создаётся автоматически)
        self.logs_dir = "logs"
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
            
        # Имя файла лога
        current_date = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(self.logs_dir, f"chat_app_{current_date}.log")
        
        # Формат сообщений
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Обработчик для записи в файл
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        
        # Обработчик для вывода в консоль
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # Создаём логгер с именем 'ChatApp' и устанавливаем уровень DEBUG
        self.logger = logging.getLogger('ChatApp')
        self.logger.setLevel(logging.DEBUG)
        
        # Добавляем обработчики (логи будут дублироваться и в файл, и в консоль)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def info(self, message: str):
        """
        Логирование информационного сообщения (подтверждения, статусы).
        """
        self.logger.info(message)

    def error(self, message: str, exc_info=None):
        """
        Логирование ошибок
        """
        self.logger.error(message, exc_info=exc_info)

    def debug(self, message: str):
        """
        Логирование отладочной информации
        """
        self.logger.debug(message)

    def warning(self, message: str):
        """
        Логирование предупреждений
        """
        self.logger.warning(message)
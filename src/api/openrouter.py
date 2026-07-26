import requests
import os
from dotenv import load_dotenv
from utils.logger import AppLogger

# Загружаем переменные окружения
load_dotenv()

class OpenRouterClient:
    """
    Клиент для взаимодействия с OpenRouter API
    """
    def __init__(self, api_key: str):
        """
        Инициализация клиента
        """
        self.logger = AppLogger()
        if not api_key:
            raise ValueError("API key must be provided")
        self.api_key = api_key
        self.base_url = os.getenv("BASE_URL", "https://openrouter.ai/api/v1")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.logger.info("OpenRouterClient initialized")
        self.available_models = self.get_models()

    def get_models(self):
        """
        Получение списка доступных моделей от OpenRouter
        """
        self.logger.debug("Fetching available models")
        try:
            #  GET-запрос к эндпоинту /models
            response = requests.get(f"{self.base_url}/models", headers=self.headers)
            models_data = response.json()
            self.logger.info(f"Retrieved {len(models_data['data'])} models")
            return [
                {"id": model["id"], "name": model["name"]}
                for model in models_data["data"]
            ]
        except Exception as e:
            # Если запрос не удался, используем запасной список моделей
            default = [
                {"id": "deepseek-coder", "name": "DeepSeek"},
                {"id": "claude-3-sonnet", "name": "Claude 3.5 Sonnet"},
                {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"}
            ]
            self.logger.info(f"Using default models due to error: {e}")
            return default

    def send_message(self, message: str, model: str):
        """
        Отправка сообщения выбранной модели и получение ответа
        """
        self.logger.debug(f"Sending message to model: {model}")
        # Формируем данные для POST-запроса
        data = {
            "model": model,
            "messages": [{"role": "user", "content": message}]
        }
        try:
            # POST-запрос к эндпоинту /chat/completions
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            self.logger.info("Successfully received response")
            return response.json()
        except Exception as e:
            self.logger.error(f"API request failed: {e}", exc_info=True)
            return {"error": str(e)}

    def get_balance(self):
        """
        Получение текущего баланса аккаунта OpenRouter
        """
        try:
            # GET-запрос к эндпоинту /credits
            response = requests.get(f"{self.base_url}/credits", headers=self.headers)
            data = response.json()
            if data:
                data = data.get('data')
                return f"${(data.get('total_credits', 0) - data.get('total_usage', 0)):.2f}"
            return "Ошибка"
        except Exception as e:
            self.logger.error(f"Balance check failed: {e}", exc_info=True)
            return "Ошибка"
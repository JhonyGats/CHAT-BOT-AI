import flet as ft
from api.openrouter import OpenRouterClient
from ui.styles import AppStyles
from ui.components import MessageBubble, ModelSelector, LoginUI
from utils.cache import ChatCache
from utils.logger import AppLogger
from utils.analytics import Analytics
from utils.monitor import PerformanceMonitor
import asyncio
import time
import json
from datetime import datetime
import os
import random

# Основное приложение чата
class ChatApp:
    """
    Главный класс чата. Создаётся после успешной аутентификации
    Управляет интерфейсом, отправкой сообщений, историей, аналитикой
    """
    def __init__(self, api_key: str):
        self.api_client = OpenRouterClient(api_key=api_key)
        self.cache = ChatCache()
        self.logger = AppLogger()
        self.analytics = Analytics(self.cache)
        self.monitor = PerformanceMonitor()
        self.exports_dir = "exports"
        os.makedirs(self.exports_dir, exist_ok=True)

        self.balance_text = ft.Text("Баланс: Загрузка...", **AppStyles.BALANCE_TEXT)
        self.update_balance()

    def load_chat_history(self):
        """
        Загружает последние сообщения из базы данных и отображает их в интерфейсе
        Сообщения добавляются в обратном порядке, чтобы хронология была правильной
        """
        try:
            history = self.cache.get_chat_history()
            for msg in reversed(history):
                _, model, user_message, ai_response, timestamp, tokens = msg
                self.chat_history.controls.extend([
                    MessageBubble(message=user_message, is_user=True),
                    MessageBubble(message=ai_response, is_user=False)
                ])
        except Exception as e:
            self.logger.error(f"Ошибка загрузки истории чата: {e}")

    def update_balance(self):
        """
        Обновляет отображение баланса API
        """
        try:
            balance = self.api_client.get_balance()
            self.balance_text.value = f"Баланс: {balance}"
            self.balance_text.color = ft.Colors.GREEN_400
        except Exception as e:
            self.balance_text.value = "Баланс: н/д"
            self.balance_text.color = ft.Colors.RED_400
            self.logger.error(f"Ошибка обновления баланса: {e}")

    def main(self, page: ft.Page):
        """
        Основная функция построения интерфейса чата
        Вызывается после успешного ввода PIN или первого входа
        """
        for key, value in AppStyles.PAGE_SETTINGS.items():
            setattr(page, key, value)
        AppStyles.set_window_size(page)

        models = self.api_client.available_models
        self.model_dropdown = ModelSelector(models)
        
        self.message_input = ft.TextField(**AppStyles.MESSAGE_INPUT)
        self.chat_history = ft.ListView(**AppStyles.CHAT_HISTORY)
        self.load_chat_history()

        # Асинхронные обработчики событий
        async def send_message_click(e):
            if not self.message_input.value:
                return
            try:
                # Визуальный сигнал - синяя рамка у поля ввода
                self.message_input.border_color = ft.Colors.BLUE_400
                page.update()

                # Запоминаем время отправки и текст
                start_time = time.time()
                user_message = self.message_input.value
                self.message_input.value = ""
                page.update()

                # Показываем сообщение пользователя
                self.chat_history.controls.append(MessageBubble(message=user_message, is_user=True))
                
                # Индикатор загрузки
                loading = ft.ProgressRing()
                self.chat_history.controls.append(loading)
                page.update()

                # Асинхронный вызов API
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.api_client.send_message(
                        user_message,
                        self.model_dropdown.value
                    )
                )
                
                # Убираем индикатор загрузки
                self.chat_history.controls.remove(loading)

                if "error" in response:
                    response_text = f"Ошибка: {response['error']}"
                    tokens_used = 0
                    self.logger.error(f"Ошибка API: {response['error']}")
                else:
                    # Извлекаем текст ответа из JSON
                    response_text = response["choices"][0]["message"]["content"]
                    tokens_used = response.get("usage", {}).get("total_tokens", 0)

                # Сохраняем сообщение в базу
                self.cache.save_message(
                    model=self.model_dropdown.value,
                    user_message=user_message,
                    ai_response=response_text,
                    tokens_used=tokens_used
                )

                # Показываем ответ AI
                self.chat_history.controls.append(MessageBubble(message=response_text, is_user=False))

                # Собираем аналитику
                response_time = time.time() - start_time
                self.analytics.track_message(
                    model=self.model_dropdown.value,
                    message_length=len(user_message),
                    response_time=response_time,
                    tokens_used=tokens_used
                )

                # Логируем метрики производительности
                self.monitor.log_metrics(self.logger)
                page.update()

            except Exception as e:
                self.logger.error(f"Ошибка отправки сообщения: {e}")
                self.message_input.border_color = ft.Colors.RED_500
                
                # Всплывающее уведомление
                snack = ft.SnackBar(
                    content=ft.Text(str(e), color=ft.Colors.RED_500, weight=ft.FontWeight.BOLD),
                    bgcolor=ft.Colors.GREY_900,
                    duration=5000,
                )
                page.overlay.append(snack)
                snack.open = True
                page.update()

        async def show_analytics(e):
            """
            Показывает окно с аналитикой: общее количество сообщений, токенов,
            средние значения и статистику по моделям
            """
            stats = self.analytics.get_statistics()
            dialog = ft.AlertDialog(
                title=ft.Text("Аналитика"),
                content=ft.Column([
                    ft.Text(f"Всего сообщений: {stats['total_messages']}"),
                    ft.Text(f"Всего токенов: {stats['total_tokens']}"),
                    ft.Text(f"Среднее токенов/сообщение: {stats['tokens_per_message']:.2f}"),
                    ft.Text(f"Сообщений в минуту: {stats['messages_per_minute']:.2f}")
                ]),
                actions=[ft.TextButton("Закрыть", on_click=lambda e: close_dialog(dialog))],
            )
            page.overlay.append(dialog)
            dialog.open = True
            page.update()

        async def clear_history(e):
            """
            Очищает всю историю чата (из базы и из интерфейса)
            Также сбрасывает аналитику
            """
            try:
                self.cache.clear_history()
                self.analytics.clear_data()
                self.chat_history.controls.clear()
                page.update()
            except Exception as e:
                self.logger.error(f"Ошибка очистки истории: {e}")
                show_error_snack(page, f"Ошибка очистки истории: {str(e)}")

        async def confirm_clear_history(e):
            """
            Показывает диалог подтверждения перед очисткой истории.
            """
            def close_dlg(e):
                close_dialog(dialog)
            async def clear_confirmed(e):
                await clear_history(e)
                close_dialog(dialog)

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Подтверждение удаления"),
                content=ft.Text("Вы уверены? Это действие нельзя отменить!"),
                actions=[
                    ft.TextButton("Отмена", on_click=close_dlg),
                    ft.TextButton("Очистить", on_click=clear_confirmed),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.overlay.append(dialog)
            dialog.open = True
            page.update()

        async def save_dialog(e):
            """
            Сохраняет всю историю чата в JSON-файл в папке exports/
            Имя файла содержит дату и время.
            """
            try:
                history = self.cache.get_chat_history()
                dialog_data = []
                for msg in history:
                    dialog_data.append({
                        "timestamp": msg[4],
                        "model": msg[1],
                        "user_message": msg[2],
                        "ai_response": msg[3],
                        "tokens_used": msg[5]
                    })
                filename = f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                filepath = os.path.join(self.exports_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(dialog_data, f, ensure_ascii=False, indent=2, default=str)

                # Диалог об успешном сохранении с возможностью открыть папку
                dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Диалог сохранен"),
                    content=ft.Column([
                        ft.Text("Путь сохранения:"),
                        ft.Text(filepath, selectable=True, weight=ft.FontWeight.BOLD),
                    ]),
                    actions=[
                        ft.TextButton("OK", on_click=lambda e: close_dialog(dialog)),
                        ft.TextButton("Открыть папку", on_click=lambda e: os.startfile(self.exports_dir)),
                    ],
                )
                page.overlay.append(dialog)
                dialog.open = True
                page.update()
            except Exception as e:
                self.logger.error(f"Ошибка сохранения: {e}")
                show_error_snack(page, f"Ошибка сохранения: {str(e)}")

        # Вспомогательные функции
        def close_dialog(dialog):
            """Закрывает диалоговое окно и удаляет его из overlay."""
            dialog.open = False
            page.update()
            if dialog in page.overlay:
                page.overlay.remove(dialog)

        def show_error_snack(page, msg):
            """Показывает всплывающее сообщение об ошибке."""
            snack = ft.SnackBar(
                content=ft.Text(msg, color=ft.Colors.RED_500),
                bgcolor=ft.Colors.GREY_900,
                duration=5000,
            )
            page.overlay.append(snack)
            snack.open = True
            page.update()

        # Создание элементов интерфейса
        send_button = ft.ElevatedButton(on_click=send_message_click, **AppStyles.SEND_BUTTON)
        save_button = ft.ElevatedButton(on_click=save_dialog, **AppStyles.SAVE_BUTTON)
        clear_button = ft.ElevatedButton(on_click=confirm_clear_history, **AppStyles.CLEAR_BUTTON)
        analytics_button = ft.ElevatedButton(on_click=show_analytics, **AppStyles.ANALYTICS_BUTTON)

        control_buttons = ft.Row(
            controls=[save_button, analytics_button, clear_button],
            **AppStyles.CONTROL_BUTTONS_ROW
        )
        input_row = ft.Row(
            controls=[self.message_input, send_button],
            **AppStyles.INPUT_ROW
        )
        controls_column = ft.Column(
            controls=[input_row, control_buttons],
            **AppStyles.CONTROLS_COLUMN
        )
        balance_container = ft.Container(
            content=self.balance_text,
            **AppStyles.BALANCE_CONTAINER
        )
        model_selection = ft.Column(
            controls=[self.model_dropdown.search_field, self.model_dropdown, balance_container],
            **AppStyles.MODEL_SELECTION_COLUMN
        )
        self.main_column = ft.Column(
            controls=[model_selection, self.chat_history, controls_column],
            **AppStyles.MAIN_COLUMN
        )

        page.add(self.main_column)
        self.monitor.get_metrics()
        self.logger.info("Приложение запущено")

# Аутентификация
class LoginApp:
    """
    Класс для управления входом в приложение.
    При первом запуске запрашивает API-ключ, проверяет баланс,
    генерирует и показывает PIN, сохраняет ключ и PIN в БД.
    При последующих запусках запрашивает только PIN.
    """
    def __init__(self):
        self.cache = ChatCache()
        self.page = None

    def main(self, page: ft.Page):
        """
        Точка входа для окна аутентификации.
        Определяет, есть ли сохранённые ключ и PIN, и показывает
        соответствующий экран.
        """
        self.page = page
        page.title = "Вход в AI Chat"
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.bgcolor = ft.Colors.GREY_900
        page.theme_mode = ft.ThemeMode.DARK
        page.window.width = 500
        page.window.height = 400
        page.window.resizable = False

        # Проверяем, есть ли сохранённые настройки
        api_key = self.cache.get_setting("api_key")
        pin = self.cache.get_setting("pin")

        if api_key and pin:
            self.show_pin_screen()
        else:
            self.show_key_screen()

    def show_key_screen(self, error_text=""):
        """
        Отображает экран для ввода API-ключа OpenRouter
        """
        self.page.clean()
        self.page.add(LoginUI.build_key_screen(
            self.page,
            on_submit=self.submit_key,
            error_text=error_text
        ))
        self.page.update()

    def submit_key(self, key_value, error_label):
        """
        Обрабатывает введённый ключ: проверяет его через API,
        при успехе генерирует PIN и показывает его пользователю
        """
        key = key_value.strip()
        if not key:
            error_label.value = "Пожалуйста, введите ключ"
            self.page.update()
            return

        try:
            # Проверяем ключ
            client = OpenRouterClient(api_key=key)
            balance = client.get_balance()
            if balance == "Ошибка" or "Ошибка" in balance:
                error_label.value = "Неверный ключ или ошибка API"
                self.page.update()
                return

            # Генерируем PIN
            pin = str(random.randint(1000, 9999))
            self.cache.save_setting("api_key", key)
            self.cache.save_setting("pin", pin)

            # Показываем PIN пользователю
            def on_ok(e):
                self.page.dialog.open = False
                self.page.update()
                self.start_chat_app(key)

            dialog = ft.AlertDialog(
                title=ft.Text("Ваш PIN для входа"),
                content=ft.Text(
                    f"Запомните этот PIN: **{pin}**\n\n"
                    "При следующем запуске приложения введите его для входа.\n\n"
                    "Если забудете PIN, нажмите кнопку «Сбросить ключ» на экране входа.",
                    selectable=True
                ),
                actions=[ft.TextButton("OK, запомнил", on_click=on_ok)],
                actions_alignment=ft.MainAxisAlignment.END,
            )

            self.page.dialog = dialog
            dialog.open = True
            self.page.update()

        except Exception as ex:
            error_label.value = f"Ошибка: {str(ex)}"
            self.page.update()

    def show_pin_screen(self, error_text=""):
        """
        Отображает экран для ввода PIN-кода
        """
        self.page.clean()
        self.page.add(LoginUI.build_pin_screen(
            self.page,
            on_submit=self.submit_pin,
            on_reset=self.reset_key,
            error_text=error_text
        ))
        self.page.update()

    def submit_pin(self, pin_value, error_label):
        """
        Проверяет введённый PIN с сохранённым в БД
        Если совпадает - запускает основное приложение
        """
        entered = pin_value.strip()
        saved_pin = self.cache.get_setting("pin")
        if entered == saved_pin:
            api_key = self.cache.get_setting("api_key")
            self.start_chat_app(api_key)
        else:
            error_label.value = "Неверный PIN"
            self.page.update()

    def reset_key(self, e):
        """
        Сбрасывает сохранённые ключ и PIN, переключает на экран ввода ключа
        """
        self.cache.delete_setting("api_key")
        self.cache.delete_setting("pin")
        self.show_key_screen()

    def start_chat_app(self, api_key):
        """
        Запускает основное окно чата с переданным ключом.
        """
        self.page.clean()
        app = ChatApp(api_key)
        app.main(self.page)

# Точка входа
if __name__ == "__main__":
    login_app = LoginApp()
    ft.app(target=login_app.main)
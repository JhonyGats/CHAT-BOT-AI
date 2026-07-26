import flet as ft
from ui.styles import AppStyles

class MessageBubble(ft.Container):
    def __init__(self, message: str, is_user: bool):
        super().__init__()
        self.padding = 10
        self.border_radius = 10
        self.bgcolor = ft.Colors.BLUE_700 if is_user else ft.Colors.GREY_700
        self.alignment = ft.alignment.center_right if is_user else ft.alignment.center_left
        self.margin = ft.margin.only(
            left=50 if is_user else 0,
            right=0 if is_user else 50,
            top=5,
            bottom=5
        )
        self.content = ft.Column(
            controls=[
                ft.Text(
                    value=message,
                    color=ft.Colors.WHITE,
                    size=16,
                    selectable=True,
                    weight=ft.FontWeight.W_400
                )
            ],
            tight=True
        )

class ModelSelector(ft.Dropdown):
    def __init__(self, models: list):
        super().__init__()
        for key, value in AppStyles.MODEL_DROPDOWN.items():
            setattr(self, key, value)
        self.label = None
        self.hint_text = "Выбор модели"
        self.options = [
            ft.dropdown.Option(key=model['id'], text=model['name'])
            for model in models
        ]
        self.all_options = self.options.copy()
        self.value = models[0]['id'] if models else None
        self.search_field = ft.TextField(
            on_change=self.filter_options,
            hint_text="Поиск модели",
            **AppStyles.MODEL_SEARCH_FIELD
        )

    def filter_options(self, e):
        search_text = self.search_field.value.lower() if self.search_field.value else ""
        if not search_text:
            self.options = self.all_options
        else:
            self.options = [
                opt for opt in self.all_options
                if search_text in opt.text.lower() or search_text in opt.key.lower()
            ]
        e.page.update()

class LoginUI:
    @staticmethod
    def build_key_screen(page: ft.Page, on_submit, error_text=""):
        key_input = ft.TextField(
            label="API ключ OpenRouter",
            password=True,
            can_reveal_password=True,
            width=400,
            hint_text="Введите ваш ключ от OpenRouter"
        )
        error_label = ft.Text(error_text, color=ft.Colors.RED_400)
        submit_btn = ft.ElevatedButton(
            "Проверить и войти",
            on_click=lambda e: on_submit(key_input.value, error_label)
        )
        return ft.Column([
            ft.Text("Введите ключ API", size=20, weight=ft.FontWeight.BOLD),
            key_input,
            submit_btn,
            error_label
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    @staticmethod
    def build_pin_screen(page: ft.Page, on_submit, on_reset, error_text=""):
        pin_input = ft.TextField(
            label="Введите PIN",
            password=True,
            can_reveal_password=False,
            width=200,
            hint_text="4 цифры",
            max_length=4,
            input_filter=ft.InputFilter(allow=True, regex_string=r"^[0-9]*$")
        )
        error_label = ft.Text(error_text, color=ft.Colors.RED_400)
        submit_btn = ft.ElevatedButton(
            "Войти",
            on_click=lambda e: on_submit(pin_input.value, error_label)
        )
        reset_btn = ft.TextButton("Забыли PIN? Сбросить ключ", on_click=on_reset)
        return ft.Column([
            ft.Text("Введите PIN для доступа", size=20, weight=ft.FontWeight.BOLD),
            pin_input,
            submit_btn,
            reset_btn,
            error_label
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
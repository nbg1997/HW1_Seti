import customtkinter as ctk
import math


class SplashScreen(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        # Настройки окна: убираем стандартные рамки Windows и делаем его поверх всех окон
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.configure(fg_color="#1A1B26")

        # Размеры экрана загрузки
        width = 400
        height = 300

        # Центрируем окно загрузки ровно по центру экрана монитора
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w // 2) - (width // 2)
        y = (screen_h // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        # Холст для рисования логотипа
        self.canvas = ctk.CTkCanvas(self, width=width, height=height, bg="#1A1B26", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Рисуем текст
        self.canvas.create_text(200, 220, text="NEON AUDIO", fill="#7AA2F7", font=("Arial", 26, "bold"))
        self.canvas.create_text(200, 250, text="loading engine modules...", fill="#414868", font=("Arial", 12))

        # Цвета из нашей "неоновой" палитры
        colors = ["#F7768E", "#FF9E64", "#E0AF68", "#9ECE6A", "#7DCFFF", "#BB9AF7"]
        self.bars = []

        # Создаем полоски логотипа
        for i in range(6):
            bar = self.canvas.create_line(125 + i * 30, 140, 125 + i * 30, 140, fill=colors[i], width=8,
                                          capstyle="round")
            self.bars.append(bar)

        self.frame_count = 0
        self.anim_job = None

        # Запускаем анимацию
        self.animate()

        # Через 2.5 секунды закрываем загрузочный экран и открываем программу
        self.after(2500, self.finish)

    def animate(self):
        """Математически плавная анимация волн через синус"""
        self.frame_count += 0.15
        for i, bar in enumerate(self.bars):
            # Синус дает плавное расширение и сужение линий
            offset = math.sin(self.frame_count + i) * 40
            # Изменяем координаты полоски
            self.canvas.coords(bar, 125 + i * 30, 140 - abs(offset) - 5, 125 + i * 30, 140 + abs(offset) + 5)

        # Зацикливаем анимацию (30 мс = ~30 fps)
        self.anim_job = self.after(30, self.animate)

    def finish(self):
        """Завершение загрузки"""
        if self.anim_job:
            self.after_cancel(self.anim_job)  # Останавливаем анимацию
        self.destroy()  # Уничтожаем окно загрузки
        self.parent.deiconify()  # Показываем главное окно приложения
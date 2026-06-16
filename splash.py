import math
import customtkinter as ctk


class SplashScreen(ctk.CTkToplevel):
    """
    Класс экрана загрузки (Preety Screen).
    Создает всплывающее окно без рамок с анимированным логотипом,
    которое отображается перед запуском основного интерфейса приложения.
    """

    # ==========================================
    # БЛОК 1: ИНИЦИАЛИЗАЦИЯ И НАСТРОЙКА ОКНА
    # ==========================================
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        # Настройки окна: убираем системные рамки Windows и фиксируем поверх остальных окон
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.configure(fg_color="#1A1B26")

        # Размеры экрана загрузки
        width = 400
        height = 300

        # Вычисляем координаты для центрирования окна ровно по центру экрана монитора
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w // 2) - (width // 2)
        y = (screen_h // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        # ==========================================
        # БЛОК 2: ОТРИСОВКА ЭЛЕМЕНТОВ ЛОГОТИПА
        # ==========================================
        # Холст для рисования логотипа и текста
        self.canvas = ctk.CTkCanvas(self, width=width, height=height, bg="#1A1B26", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Рисуем текст (Название и статус загрузки)
        self.canvas.create_text(200, 220, text="NEON AUDIO", fill="#7AA2F7", font=("Arial", 26, "bold"))
        self.canvas.create_text(200, 250, text="loading engine modules...", fill="#414868", font=("Arial", 12))

        # Цвета из нашей фирменной "неоновой" палитры
        colors = ["#F7768E", "#FF9E64", "#E0AF68", "#9ECE6A", "#7DCFFF", "#BB9AF7"]
        self.bars = []

        # Создаем изначальные полоски логотипа (пока в виде точек/коротких линий)
        for i in range(6):
            bar = self.canvas.create_line(125 + i * 30, 140, 125 + i * 30, 140, fill=colors[i], width=8,
                                          capstyle="round")
            self.bars.append(bar)

        # ==========================================
        # БЛОК 3: ЗАПУСК АНИМАЦИИ И ТАЙМЕРА
        # ==========================================
        self.frame_count = 0
        self.anim_job = None

        # Запускаем цикл анимации
        self.animate()

        # Устанавливаем таймер: через 2.5 секунды закрыть сплэш-скрин и открыть программу
        self.after(2500, self.finish)

    # ==========================================
    # БЛОК 4: ЛОГИКА АНИМАЦИИ И ЗАВЕРШЕНИЯ
    # ==========================================
    def animate(self):
        """
        Математически плавная анимация волн.
        Использует функцию синуса для расчета высоты каждой отдельной полоски.
        """
        self.frame_count += 0.15
        for i, bar in enumerate(self.bars):
            # Синус дает плавное расширение и сужение линий (эффект пульсации)
            offset = math.sin(self.frame_count + i) * 40

            # Применяем новые координаты (раздвигаем линию от центра вверх и вниз)
            self.canvas.coords(bar, 125 + i * 30, 140 - abs(offset) - 5, 125 + i * 30, 140 + abs(offset) + 5)

        # Зацикливаем вызов анимации каждые 30 мс (~30 кадров в секунду)
        self.anim_job = self.after(30, self.animate)

    def finish(self):
        """
        Корректное завершение работы экрана загрузки.
        Останавливает анимацию, уничтожает временное окно и показывает основной интерфейс.
        """
        # Обязательно останавливаем запланированную анимацию, чтобы избежать ошибок и утечек памяти
        if self.anim_job:
            self.after_cancel(self.anim_job)

        self.destroy()  # Уничтожаем окно загрузки
        self.parent.deiconify()  # Показываем (разворачиваем) главное окно приложения
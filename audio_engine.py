import os
import numpy as np
import pygame
from pydub import AudioSegment


class AudioProcessor:
    """
    Движок для обработки и воспроизведения аудио.
    Использует pydub для загрузки/манипуляций (реверс, обрезка) и pygame для воспроизведения.
    """

    # ==========================================
    # БЛОК 1: ИНИЦИАЛИЗАЦИЯ И СОСТОЯНИЕ
    # ==========================================
    def __init__(self):
        # Основные аудио-данные
        self.audio = None  # Объект AudioSegment (текущий трек)
        self.temp_path = "temp_preview.wav"  # Временный файл для плеера pygame
        self.duration_ms = 0  # Длина трека в миллисекундах

        # Переменные воспроизведения
        self.start_time_offset = 0  # Смещение при перемотке (откуда начали играть)
        self.paused = False  # Флаг паузы

        # Настройки звука
        self.volume = 1.0  # Текущая громкость (от 0.0 до 1.0)
        self.is_muted = False  # Флаг беззвучного режима
        self.is_reversed = False  # Флаг состояния "задом наперёд"

        # Привязка бинарных файлов FFmpeg (необходимы для чтения mp3)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        AudioSegment.converter = os.path.join(current_dir, "ffmpeg.exe")
        AudioSegment.ffprobe = os.path.join(current_dir, "ffprobe.exe")

        # Инициализация микшера для воспроизведения
        pygame.mixer.init()
        pygame.mixer.music.set_volume(self.volume)

    # ==========================================
    # БЛОК 2: РАБОТА С ФАЙЛАМИ И ОБРАБОТКА
    # ==========================================
    def _release_file(self):
        """
        Внутренний метод. Принудительно заставляет pygame 'отпустить' временный файл.
        Необходимо для ОС Windows, чтобы избежать ошибки PermissionError (Errno 13)
        при попытке перезаписать файл во время реверса или загрузки нового трека.
        """
        pygame.mixer.music.stop()
        try:
            pygame.mixer.music.unload()
        except AttributeError:
            pass  # Если версия pygame не поддерживает unload, просто игнорируем

    def load_file(self, path):
        """Загружает аудиофайл (mp3/wav), сбрасывает настройки и создает временный WAV."""
        try:
            self._release_file()  # Снимаем блокировку со старого файла

            self.audio = AudioSegment.from_file(path)
            self.duration_ms = len(self.audio)
            self.is_reversed = False  # При загрузке нового трека сбрасываем флаг реверса

            # Экспортируем в WAV, так как pygame лучше всего работает с этим форматом
            self.audio.export(self.temp_path, format="wav")
            return True
        except Exception as e:
            print(f"Ошибка загрузки: {e}")
            return False

    def reverse_audio(self):
        """Разворачивает аудиодорожку задом наперёд с помощью pydub."""
        if self.audio:
            self._release_file()  # Снимаем блокировку ОС перед перезаписью

            self.audio = self.audio.reverse()
            self.is_reversed = not self.is_reversed  # Меняем статус реверса на противоположный

            self.audio.export(self.temp_path, format="wav")
            return True
        return False

    # ==========================================
    # БЛОК 3: УПРАВЛЕНИЕ ВОСПРОИЗВЕДЕНИЕМ (ПЛЕЕР)
    # ==========================================
    def play(self, start_ms=0):
        """Запускает воспроизведение трека с указанной миллисекунды."""
        if os.path.exists(self.temp_path):
            self.start_time_offset = start_ms
            pygame.mixer.music.load(self.temp_path)
            # Если включен Mute, передаем 0.0, иначе текущую громкость
            pygame.mixer.music.set_volume(0.0 if self.is_muted else self.volume)
            # В pygame start принимает секунды, поэтому делим на 1000
            pygame.mixer.music.play(start=start_ms / 1000.0)
            self.paused = False

    def pause(self):
        """Ставит трек на паузу."""
        pygame.mixer.music.pause()
        self.paused = True

    def unpause(self):
        """Снимает трек с паузы."""
        pygame.mixer.music.unpause()
        self.paused = False

    def stop(self):
        """Полностью останавливает воспроизведение и сбрасывает тайминг в ноль."""
        self._release_file()
        self.start_time_offset = 0
        self.paused = False

    # ==========================================
    # БЛОК 4: УПРАВЛЕНИЕ ГРОМКОСТЬЮ
    # ==========================================
    def set_volume(self, val):
        """Устанавливает новый уровень громкости (0.0 - 1.0)."""
        self.volume = val
        if not self.is_muted:
            pygame.mixer.music.set_volume(self.volume)

    def toggle_mute(self):
        """Включает/выключает беззвучный режим, возвращает новое состояние."""
        self.is_muted = not self.is_muted
        if self.is_muted:
            pygame.mixer.music.set_volume(0.0)
        else:
            pygame.mixer.music.set_volume(self.volume)
        return self.is_muted

    # ==========================================
    # БЛОК 5: АНАЛИЗ ДАННЫХ (ДЛЯ ИНТЕРФЕЙСА)
    # ==========================================
    def get_current_pos_ms(self):
        """Возвращает текущую позицию воспроизведения в миллисекундах."""
        if self.paused:
            # На паузе pygame get_pos() замирает, прибавляем это к нашему оффсету
            return self.start_time_offset + pygame.mixer.music.get_pos()
        if pygame.mixer.music.get_busy():
            pos = pygame.mixer.music.get_pos()
            return self.start_time_offset + pos if pos != -1 else self.start_time_offset
        return self.start_time_offset

    def get_fft_data(self, current_ms):
        """
        Выполняет Быстрое Преобразование Фурье (FFT) для отрисовки эквалайзера.
        Берет срез аудио (50 мс) и раскладывает его на 15 частотных полос.
        """
        if self.audio is None: return [0] * 15

        start = int(current_ms)
        chunk = self.audio[start: start + 50]  # Берем "кусочек" звука длиной 50мс
        if len(chunk) < 10: return [0] * 15

        # Получаем сырые данные амплитуды
        samples = np.array(chunk.get_array_of_samples())

        # Если трек стерео (2 канала), усредняем до моно (1 канал) для упрощения математики
        if chunk.channels == 2:
            samples = samples.reshape((-1, 2)).mean(axis=1)

        # Применяем Фурье (превращаем волну в частоты)
        fft_res = np.abs(np.fft.rfft(samples))[:500]

        # Разбиваем результат на 15 корзин (для 15 столбиков эквалайзера)
        bins = np.array_split(fft_res, 15)
        # Нормализуем данные, чтобы они помещались в масштаб интерфейса
        return [np.mean(b) / 500000 for b in bins]

    def get_waveform_data(self):
        """Возвращает данные массива для отрисовки статической звуковой волны."""
        if self.audio:
            samples = np.array(self.audio.get_array_of_samples())
            # Берем каждый 200-й сэмпл для оптимизации скорости отрисовки
            return samples[::200]
        return None
from pydub import AudioSegment
import os
import pygame
import numpy as np


class AudioProcessor:
    def __init__(self):
        self.audio = None
        self.temp_path = "temp_preview.wav"
        self.duration_ms = 0
        self.start_time_offset = 0
        self.paused = False

        self.volume = 1.0
        self.is_muted = False

        # Флаг для отслеживания состояния реверса
        self.is_reversed = False

        current_dir = os.path.dirname(os.path.abspath(__file__))
        AudioSegment.converter = os.path.join(current_dir, "ffmpeg.exe")
        AudioSegment.ffprobe = os.path.join(current_dir, "ffprobe.exe")

        pygame.mixer.init()
        pygame.mixer.music.set_volume(self.volume)

    def _release_file(self):
        """Принудительно заставляет pygame 'отпустить' файл в Windows"""
        pygame.mixer.music.stop()
        try:
            pygame.mixer.music.unload()
        except AttributeError:
            pass

    def load_file(self, path):
        try:
            self._release_file()
            self.audio = AudioSegment.from_file(path)
            self.duration_ms = len(self.audio)
            self.is_reversed = False  # Сбрасываем флаг при загрузке нового файла
            self.audio.export(self.temp_path, format="wav")
            return True
        except Exception as e:
            print(f"Ошибка загрузки: {e}")
            return False

    def reverse_audio(self):
        """Разворачивает аудио задом наперед и меняет статус"""
        if self.audio:
            self._release_file()
            self.audio = self.audio.reverse()
            self.is_reversed = not self.is_reversed  # Меняем статус на противоположный
            self.audio.export(self.temp_path, format="wav")
            return True
        return False

    def play(self, start_ms=0):
        if os.path.exists(self.temp_path):
            self.start_time_offset = start_ms
            pygame.mixer.music.load(self.temp_path)
            pygame.mixer.music.set_volume(0.0 if self.is_muted else self.volume)
            pygame.mixer.music.play(start=start_ms / 1000.0)
            self.paused = False

    def pause(self):
        pygame.mixer.music.pause()
        self.paused = True

    def unpause(self):
        pygame.mixer.music.unpause()
        self.paused = False

    def stop(self):
        self._release_file()
        self.start_time_offset = 0
        self.paused = False

    def set_volume(self, val):
        self.volume = val
        if not self.is_muted:
            pygame.mixer.music.set_volume(self.volume)

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            pygame.mixer.music.set_volume(0.0)
        else:
            pygame.mixer.music.set_volume(self.volume)
        return self.is_muted

    def get_current_pos_ms(self):
        if self.paused:
            return self.start_time_offset + pygame.mixer.music.get_pos()
        if pygame.mixer.music.get_busy():
            pos = pygame.mixer.music.get_pos()
            return self.start_time_offset + pos if pos != -1 else self.start_time_offset
        return self.start_time_offset

    def get_fft_data(self, current_ms):
        if self.audio is None: return [0] * 15
        start = int(current_ms)
        chunk = self.audio[start: start + 50]
        if len(chunk) < 10: return [0] * 15

        samples = np.array(chunk.get_array_of_samples())
        if chunk.channels == 2:
            samples = samples.reshape((-1, 2)).mean(axis=1)

        fft_res = np.abs(np.fft.rfft(samples))[:500]
        bins = np.array_split(fft_res, 15)
        return [np.mean(b) / 500000 for b in bins]

    def get_waveform_data(self):
        if self.audio:
            samples = np.array(self.audio.get_array_of_samples())
            return samples[::200]
        return None
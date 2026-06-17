import os
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from audio_engine import AudioProcessor


@pytest.fixture
def processor():
    """
    Фикстура pytest. Выполняется перед каждым тестом.
    Мокируем (отключаем) реальный pygame.mixer, чтобы тесты
    могли работать на серверах (CI/CD) без звуковых карт.
    """
    with patch('audio_engine.pygame.mixer'):
        yield AudioProcessor()


def test_initial_state(processor):
    """Проверка базового состояния при инициализации."""
    assert processor.volume == 1.0
    assert processor.is_muted is False
    assert processor.is_reversed is False
    assert processor.paused is False
    assert processor.duration_ms == 0


def test_set_volume(processor):
    """Проверка логики изменения громкости."""
    processor.set_volume(0.5)
    assert processor.volume == 0.5
    processor.set_volume(0.0)
    assert processor.volume == 0.0


def test_toggle_mute(processor):
    """Проверка включения и выключения беззвучного режима (Mute)."""
    assert processor.toggle_mute() is True
    assert processor.is_muted is True

    assert processor.toggle_mute() is False
    assert processor.is_muted is False


@patch('audio_engine.AudioSegment')
def test_load_file_success(mock_audio_segment, processor):
    """Проверка успешной загрузки файла с имитацией pydub.AudioSegment."""
    # Создаем фейковый аудио-объект длиной 5000 мс (5 сек)
    mock_audio = MagicMock()
    mock_audio.__len__.return_value = 5000
    mock_audio_segment.from_file.return_value = mock_audio

    result = processor.load_file("fake_audio.mp3")

    assert result is True
    assert processor.duration_ms == 5000
    assert processor.is_reversed is False
    # Проверяем, что файл был отправлен на экспорт во временный wav
    mock_audio.export.assert_called_with(processor.temp_path, format="wav")


@patch('audio_engine.AudioSegment')
def test_load_file_exception(mock_audio_segment, processor):
    """Проверка обработки ошибки при поврежденном файле."""
    # Заставляем загрузчик выбросить ошибку
    mock_audio_segment.from_file.side_effect = Exception("File corrupted")

    result = processor.load_file("bad_audio.mp3")
    assert result is False


@patch('audio_engine.AudioSegment')
def test_reverse_audio(mock_audio_segment, processor):
    """Проверка логики реверса звуковой дорожки."""
    mock_audio = MagicMock()
    mock_audio.reverse.return_value = mock_audio
    processor.audio = mock_audio
    processor.is_reversed = False

    result = processor.reverse_audio()

    assert result is True
    assert processor.is_reversed is True
    mock_audio.export.assert_called()


def test_reverse_audio_no_file(processor):
    """Проверка реверса, если файл не был загружен."""
    processor.audio = None
    result = processor.reverse_audio()
    assert result is False


def test_play_pause_stop_logic(processor):
    """Проверка переключения флагов при управлении плеером."""
    # Чтобы функция play прошла дальше, создаем пустой временный файл
    with open(processor.temp_path, "w") as f:
        f.write("dummy")

    processor.play(1000)
    assert processor.start_time_offset == 1000
    assert processor.paused is False

    processor.pause()
    assert processor.paused is True

    processor.unpause()
    assert processor.paused is False

    processor.stop()
    assert processor.start_time_offset == 0
    assert processor.paused is False

    # Убираем за собой временный файл
    os.remove(processor.temp_path)


def test_get_waveform_data(processor):
    """Проверка получения данных волны для отрисовки."""
    # Если трека нет, должен вернуть None
    assert processor.get_waveform_data() is None

    # Если трек есть, имитируем возврат массива сэмплов
    mock_audio = MagicMock()
    # Создаем фейковый массив из 1000 нулей
    mock_audio.get_array_of_samples.return_value = [0] * 1000
    processor.audio = mock_audio

    data = processor.get_waveform_data()
    assert data is not None
    # Так как в движке мы берем каждый 200-й сэмпл (samples[::200]), 1000 / 200 = 5 элементов
    assert len(data) == 5


def test_get_current_pos_ms(processor):
    """Проверка вычисления текущей позиции времени."""
    processor.start_time_offset = 1000

    with patch('audio_engine.pygame.mixer.music.get_pos', return_value=500):
        # 1. Проверка на паузе (смещение 1000 + позиция 500 = 1500)
        processor.paused = True
        assert processor.get_current_pos_ms() == 1500

        # 2. Проверка при воспроизведении
        processor.paused = False
        with patch('audio_engine.pygame.mixer.music.get_busy', return_value=True):
            assert processor.get_current_pos_ms() == 1500

def test_get_fft_data_empty(processor):
    """Проверка возврата нулей для FFT, если трек не загружен."""
    processor.audio = None
    fft_data = processor.get_fft_data(0)
    assert len(fft_data) == 15
    assert all(v == 0 for v in fft_data)
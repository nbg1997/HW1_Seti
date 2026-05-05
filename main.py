import sys
import os
import numpy as np
import pygame

# Фикс для Python 3.13
try:
    import audioop
except ImportError:
    import audioop_lts as audioop

    sys.modules["audioop"] = audioop

import customtkinter as ctk
from tkinter import filedialog
from audio_engine import AudioProcessor
from splash import SplashScreen

ctk.set_appearance_mode("dark")


class AudioEditorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.withdraw()

        self.title("Neon Audio Editor")
        self.geometry("1000x720")
        self.minsize(800, 600)
        self.configure(fg_color="#1A1B26")

        self.processor = AudioProcessor()
        self.cursor_line = None
        self.cursor_triangle = None
        self.wave_lines = []
        self.last_x_idx = 0

        self.current_filename = ""

        self.is_dragging = False
        self.was_playing = False
        self.drag_ms = 0
        self._resize_timer = None

        self.build_ui()
        self.splash = SplashScreen(self)

    def build_ui(self):
        self.nav_frame = ctk.CTkFrame(self, fg_color="#24283B", corner_radius=0, height=60)
        self.nav_frame.pack(side="top", fill="x")

        ctk.CTkButton(self.nav_frame, text="ОТКРЫТЬ ФАЙЛ", fg_color="#7AA2F7", font=("Arial", 12, "bold"),
                      command=self.load_audio).pack(side="left", padx=20, pady=10)

        self.lbl_status = ctk.CTkLabel(self.nav_frame, text="Файл не выбран", text_color="#414868", font=("Arial", 14))
        self.lbl_status.pack(side="left", padx=10)

        self.lbl_time = ctk.CTkLabel(self.nav_frame, text="00:00 / 00:00", text_color="#7DCFFF",
                                     font=("Arial", 16, "bold"))
        self.lbl_time.pack(side="right", padx=20)

        self.wave_canvas = ctk.CTkCanvas(self, bg="#1A1B26", highlightthickness=0)
        self.wave_canvas.pack(fill="both", expand=True, padx=20, pady=10)

        self.wave_canvas.bind("<Button-1>", self.on_seek_click)
        self.wave_canvas.bind("<B1-Motion>", self.on_seek_drag)
        self.wave_canvas.bind("<ButtonRelease-1>", self.on_seek_release)
        self.wave_canvas.bind("<Configure>", self.on_resize)

        self.bottom_panel = ctk.CTkFrame(self, fg_color="#24283B", height=180)
        self.bottom_panel.pack(side="bottom", fill="x", padx=20, pady=20)

        self.eq_frame = ctk.CTkFrame(self.bottom_panel, fg_color="#1A1B26", border_width=1, border_color="#414868",
                                     corner_radius=10)
        self.eq_frame.pack(side="left", padx=20, pady=15)

        top_eq_bar = ctk.CTkFrame(self.eq_frame, fg_color="transparent")
        top_eq_bar.pack(fill="x", padx=10, pady=(5, 0))
        ctk.CTkLabel(top_eq_bar, text="SPECTRUM EQ", font=("Arial", 10, "bold"), text_color="#7AA2F7").pack(side="left")
        ctk.CTkLabel(top_eq_bar, text="0 dB", font=("Arial", 10, "bold"), text_color="#F7768E").pack(side="right")

        self.viz_canvas = ctk.CTkCanvas(self.eq_frame, width=300, height=100, bg="#1A1B26", highlightthickness=0)
        self.viz_canvas.pack(padx=10, pady=2)

        for i in range(15):
            self.viz_canvas.create_rectangle(i * 20, 0, i * 20 + 15, 100, fill="#1F2335", outline="")
        self.bars = [self.viz_canvas.create_rectangle(i * 20, 100, i * 20 + 15, 100, fill="#9ECE6A", outline="") for i
                     in range(15)]

        bot_eq_bar = ctk.CTkFrame(self.eq_frame, fg_color="transparent", height=15)
        bot_eq_bar.pack(fill="x", padx=10, pady=(0, 5))
        ctk.CTkLabel(bot_eq_bar, text="-60 dB", font=("Arial", 10), text_color="#9ECE6A").pack(side="right")

        self.vol_container = ctk.CTkFrame(self.bottom_panel, fg_color="#24283B", width=60, height=140, corner_radius=12)
        self.vol_container.pack(side="right", padx=20, pady=10)
        self.vol_container.pack_propagate(False)

        self.btn_vol = ctk.CTkButton(self.vol_container, text="🔊", width=40, height=40,
                                     fg_color="transparent", hover_color="#3B4261",
                                     font=("Segoe UI Emoji", 24), command=self.toggle_mute)
        self.btn_vol.place(relx=0.5, rely=0.95, anchor="s")

        self.slider_vol = ctk.CTkSlider(self.vol_container, orientation="vertical", width=15, height=80,
                                        fg_color="#1A1B26", progress_color="#9ECE6A", button_color="#FF9E64",
                                        button_hover_color="#E0AF68", command=self.change_volume)
        self.slider_vol.set(1.0)

        self.hide_timer = None
        for widget in (self.vol_container, self.btn_vol, self.slider_vol):
            widget.bind("<Enter>", self.show_vol_slider)
            widget.bind("<Leave>", self.schedule_hide)

        self.btn_frame = ctk.CTkFrame(self.bottom_panel, fg_color="transparent")
        self.btn_frame.pack(expand=True)

        self.btn_reverse = ctk.CTkButton(self.btn_frame, text="⏪", width=60, height=60, corner_radius=30,
                                         font=("Arial", 22), fg_color="#BB9AF7", hover_color="#9d7cdb",
                                         command=self.apply_reverse)
        self.btn_reverse.pack(side="left", padx=15)

        self.btn_play = ctk.CTkButton(self.btn_frame, text="▶", width=60, height=60, corner_radius=30,
                                      font=("Arial", 22), fg_color="#7AA2F7", hover_color="#5a86eb",
                                      command=self.toggle_play)
        self.btn_play.pack(side="left", padx=15)

        self.btn_stop = ctk.CTkButton(self.btn_frame, text="■", width=60, height=60, corner_radius=30,
                                      font=("Arial", 22), fg_color="#F7768E", hover_color="#d65e75",
                                      command=self.stop_audio)
        self.btn_stop.pack(side="left", padx=15)

        self.update_loop()

    # --- УМНЫЙ РЕВЕРС С СОХРАНЕНИЕМ ПОЗИЦИИ ---
    def apply_reverse(self):
        if not self.processor.audio: return

        # 1. Запоминаем текущую позицию и играла ли музыка
        curr_ms = self.processor.get_current_pos_ms()
        was_playing = not self.processor.paused and pygame.mixer.music.get_busy()

        self.lbl_status.configure(text=f"Загружен: {self.current_filename} (Обработка...)", text_color="#FF9E64")
        self.update()

        self.processor.stop()
        self.btn_play.configure(text="▶")

        if self.processor.reverse_audio():
            if self.processor.is_reversed:
                self.btn_reverse.configure(text="⏩")
                self.lbl_status.configure(text=f"Загружен: {self.current_filename}  [РЕВЕРС]", text_color="#BB9AF7")
            else:
                self.btn_reverse.configure(text="⏪")
                self.lbl_status.configure(text=f"Загружен: {self.current_filename}", text_color="#7DCFFF")

            self.last_x_idx = 0
            self.draw_waveform()

            # 2. Высчитываем новую позицию (Длина минус текущее время)
            new_ms = self.processor.duration_ms - curr_ms
            new_ms = max(0, min(new_ms, self.processor.duration_ms))  # Защита от выхода за границы

            # 3. Визуально перекидываем ползунок на новое место
            w = self.wave_canvas.winfo_width()
            x = (new_ms / self.processor.duration_ms) * w
            self.update_drag_visuals(x)

            # 4. Если музыка играла — сразу запускаем задом наперед!
            if was_playing:
                self.processor.play(start_ms=self.drag_ms)
                self.btn_play.configure(text="⏸")
            else:
                self.processor.start_time_offset = self.drag_ms

    def on_resize(self, event):
        if not self.processor.audio: return
        if self._resize_timer:
            self.after_cancel(self._resize_timer)
        self._resize_timer = self.after(200, self.draw_waveform)

    def on_seek_click(self, event):
        if not self.processor.audio: return
        self.is_dragging = True
        self.was_playing = not self.processor.paused and pygame.mixer.music.get_busy()
        if self.was_playing:
            self.processor.pause()
        self.update_drag_visuals(event.x)

    def on_seek_drag(self, event):
        if not self.processor.audio or not self.is_dragging: return
        self.update_drag_visuals(event.x)

    def on_seek_release(self, event):
        if not self.processor.audio: return
        self.is_dragging = False
        if self.was_playing:
            self.processor.play(start_ms=self.drag_ms)
            self.btn_play.configure(text="⏸")
        else:
            self.processor.start_time_offset = self.drag_ms
            self.processor.play(start_ms=self.drag_ms)
            self.processor.pause()

    def update_drag_visuals(self, x):
        w = self.wave_canvas.winfo_width()
        x = max(0, min(x, w))
        self.drag_ms = (x / w) * self.processor.duration_ms

        self.wave_canvas.coords(self.cursor_line, x, 0, x, self.wave_canvas.winfo_height())
        self.wave_canvas.coords(self.cursor_triangle, x, 12, x - 7, 0, x + 7, 0)

        curr_idx = int(x)
        for i, line in enumerate(self.wave_lines):
            color = "#3B4261" if i < curr_idx else "#7DCFFF"
            self.wave_canvas.itemconfig(line, fill=color)
        self.last_x_idx = curr_idx

        total_sec, curr_sec = self.processor.duration_ms // 1000, self.drag_ms // 1000
        self.lbl_time.configure(
            text=f"{int(curr_sec // 60):02}:{int(curr_sec % 60):02} / {int(total_sec // 60):02}:{int(total_sec % 60):02}")

    def show_vol_slider(self, event=None):
        if self.hide_timer:
            self.after_cancel(self.hide_timer)
            self.hide_timer = None
        self.vol_container.configure(fg_color="#1F2335", border_width=1, border_color="#7AA2F7")
        self.slider_vol.place(relx=0.5, rely=0.45, anchor="center")

    def schedule_hide(self, event=None):
        self.hide_timer = self.after(300, self.hide_vol_slider)

    def hide_vol_slider(self):
        self.vol_container.configure(fg_color="#24283B", border_width=0)
        self.slider_vol.place_forget()

    def change_volume(self, val):
        self.processor.set_volume(val)
        if self.processor.is_muted and val > 0:
            self.processor.toggle_mute()
        self.update_vol_icon(val)

    def toggle_mute(self):
        is_muted = self.processor.toggle_mute()
        if is_muted:
            self.btn_vol.configure(text="🔇")
            self.slider_vol.set(0)
        else:
            self.update_vol_icon(self.processor.volume)
            self.slider_vol.set(self.processor.volume)

    def update_vol_icon(self, val):
        if val == 0:
            self.btn_vol.configure(text="🔇")
        elif val < 0.5:
            self.btn_vol.configure(text="🔉")
        else:
            self.btn_vol.configure(text="🔊")

    def toggle_play(self):
        if not self.processor.audio: return
        if self.processor.paused:
            self.processor.unpause()
            self.btn_play.configure(text="⏸")
        elif pygame.mixer.music.get_busy():
            self.processor.pause()
            self.btn_play.configure(text="▶")
        else:
            self.processor.play(self.processor.start_time_offset)
            self.btn_play.configure(text="⏸")

    def stop_audio(self):
        self.processor.stop()
        self.btn_play.configure(text="▶")
        self.last_x_idx = 0
        for line in self.wave_lines:
            self.wave_canvas.itemconfig(line, fill="#7DCFFF")
        if self.cursor_line:
            self.wave_canvas.coords(self.cursor_line, 0, 0, 0, self.wave_canvas.winfo_height())
            self.wave_canvas.coords(self.cursor_triangle, 0, 12, -7, 0, 7, 0)
            self.lbl_time.configure(
                text=f"00:00 / {int((self.processor.duration_ms // 1000) // 60):02}:{int((self.processor.duration_ms // 1000) % 60):02}")

    def draw_waveform(self):
        data = self.processor.get_waveform_data()
        if data is not None:
            self.wave_canvas.delete("all")
            self.wave_lines.clear()

            self.wave_canvas.update()
            w, h = self.wave_canvas.winfo_width(), self.wave_canvas.winfo_height()

            self.wave_canvas.create_line(0, h / 2, w, h / 2, fill="#414868")
            step = len(data) / w

            for x in range(int(w)):
                idx = int(x * step)
                if idx < len(data):
                    val = (data[idx] / 32768) * (h / 2) * 0.8
                    line = self.wave_canvas.create_line(x, h / 2 - val, x, h / 2 + val, fill="#7DCFFF")
                    self.wave_lines.append(line)

            self.cursor_line = self.wave_canvas.create_line(0, 0, 0, h, fill="#FF9E64", width=2)
            self.cursor_triangle = self.wave_canvas.create_polygon(0, 10, -6, 0, 6, 0, fill="#FF9E64")
            self.last_x_idx = 0

    def update_loop(self):
        curr_ms = self.processor.get_current_pos_ms()

        if self.processor.audio and self.cursor_line and not self.is_dragging:
            w = self.wave_canvas.winfo_width()
            x = (curr_ms / self.processor.duration_ms) * w

            self.wave_canvas.coords(self.cursor_line, x, 0, x, self.wave_canvas.winfo_height())
            self.wave_canvas.coords(self.cursor_triangle, x, 12, x - 7, 0, x + 7, 0)

            curr_idx = int(x)
            if curr_idx > self.last_x_idx and curr_idx < len(self.wave_lines):
                for i in range(self.last_x_idx, curr_idx):
                    self.wave_canvas.itemconfig(self.wave_lines[i], fill="#3B4261")
                self.last_x_idx = curr_idx
            elif curr_idx < self.last_x_idx:
                for i in range(curr_idx, len(self.wave_lines)):
                    self.wave_canvas.itemconfig(self.wave_lines[i], fill="#7DCFFF")
                for i in range(0, curr_idx):
                    self.wave_canvas.itemconfig(self.wave_lines[i], fill="#3B4261")
                self.last_x_idx = curr_idx

            total_sec, curr_sec = self.processor.duration_ms // 1000, curr_ms // 1000
            self.lbl_time.configure(
                text=f"{int(curr_sec // 60):02}:{int(curr_sec % 60):02} / {int(total_sec // 60):02}:{int(total_sec % 60):02}")

        fft_levels = self.processor.get_fft_data(curr_ms)
        for i, level in enumerate(fft_levels):
            height_val = min(level * 100, 90)
            new_y = 100 - height_val

            if height_val > 75:
                color = "#F7768E"
            elif height_val > 40:
                color = "#E0AF68"
            else:
                color = "#9ECE6A"

            self.viz_canvas.coords(self.bars[i], i * 20, new_y, i * 20 + 15, 100)
            self.viz_canvas.itemconfig(self.bars[i], fill=color)

        self.after(30, self.update_loop)

    def load_audio(self):
        path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav")])
        if path and self.processor.load_file(path):
            self.current_filename = os.path.basename(path)
            self.lbl_status.configure(text=f"Загружен: {self.current_filename}", text_color="#7DCFFF")
            self.btn_reverse.configure(text="⏪")
            self.last_x_idx = 0
            self.btn_play.configure(text="▶")
            self.after(200, self.draw_waveform)


if __name__ == "__main__":
    app = AudioEditorApp()
    app.mainloop()
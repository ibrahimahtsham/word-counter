import os
import json
import speech_recognition as sr
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import sys
import pyaudio
import numpy as np
import logging


# Set up logging
log_file = "word_counter.log"
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)

        def append():
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.insert(tk.END, msg + "\n")
            self.text_widget.config(state=tk.DISABLED)
            self.text_widget.yview(tk.END)

        self.text_widget.after(0, append)


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")


class WordCounter:
    def __init__(
        self,
        save_path,
        words_to_track,
        audio_source_var,
        volume_meter,
        transcript_text,
        words_listbox,
        device_map,
    ):
        self.save_path = save_path
        self.words_to_track = words_to_track
        self.counts = self.load_counts()
        self.recognizer = sr.Recognizer()
        self.running = True
        self.audio_source_var = audio_source_var
        self.volume_meter = volume_meter
        self.transcript_text = transcript_text
        self.words_listbox = words_listbox
        self.device_map = device_map
        self.update_listbox()

    def load_counts(self):
        if os.path.exists(self.save_path):
            with open(self.save_path, "r") as file:
                return json.load(file)
        return {word: 0 for word in self.words_to_track}

    def save_counts(self):
        with open(self.save_path, "w") as file:
            json.dump(self.counts, file)

    def update_listbox(self):
        self.words_listbox.delete(0, tk.END)
        for word, count in self.counts.items():
            self.words_listbox.insert(tk.END, f"{word}: {count}")

    def listen_and_count(self):
        logging.debug("Starting listen_and_count")
        while self.running:
            try:
                device_name = self.audio_source_var.get()
                device_index = self.device_map[device_name]
                logging.debug(f"Using device index: {device_index}")
                source = sr.Microphone(device_index=device_index)
                with source as audio_source:
                    self.recognizer.adjust_for_ambient_noise(audio_source)
                    logging.debug("Adjusted for ambient noise")
                    while self.running:
                        try:
                            audio = self.recognizer.listen(audio_source, timeout=5)
                            logging.debug("Audio captured")
                            text = self.recognizer.recognize_google(audio).lower()
                            logging.debug(f"Recognized text: {text}")
                            self.transcript_text.insert(tk.END, text + "\n")
                            self.transcript_text.see(tk.END)
                            for word in self.words_to_track:
                                if word in text:
                                    self.counts[word] += text.split().count(word)
                            self.save_counts()
                            self.update_listbox()
                        except sr.UnknownValueError:
                            logging.debug(
                                "UnknownValueError: Could not understand audio"
                            )
                            self.transcript_text.insert(
                                tk.END, "[Could not understand audio]\n"
                            )
                            self.transcript_text.see(tk.END)
                            continue
                        except sr.WaitTimeoutError:
                            logging.debug("WaitTimeoutError: Listening timed out")
                            break
                        except Exception as e:
                            logging.error(f"Error in listen_and_count: {e}")
                            break
            except Exception as e:
                logging.error(f"Error in listen_and_count: {e}")
                break

    def update_volume_meter(self):
        logging.debug("Starting update_volume_meter")
        p = pyaudio.PyAudio()
        device_name = self.audio_source_var.get()
        device_index = self.device_map[device_name]
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=44100,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=1024,
            )
        except Exception as e:
            logging.error(f"Error opening audio stream: {e}")
            return

        scaling_factor = (
            100  # Increase this factor to amplify the volume values appropriately
        )
        while self.running:
            try:
                data = np.frombuffer(stream.read(1024), dtype=np.int16)
                volume = np.linalg.norm(data) / 1024
                amplified_volume = volume * scaling_factor
                self.volume_meter["value"] = min(amplified_volume, 100)
                logging.debug(f"Volume: {amplified_volume}")
            except Exception as e:
                logging.error(f"Error in update_volume_meter: {e}")
                break  # Exit the loop if an error occurs

        # Ensure the stream is properly closed and PyAudio is terminated
        try:
            stream.stop_stream()
            stream.close()
            p.terminate()
        except Exception as e:
            logging.error(f"Error closing audio stream: {e}")


def create_icon(counter, root):
    def quit_program(icon, item):
        logging.debug("Quitting program")
        counter.running = False
        counter.save_counts()
        icon.stop()
        root.quit()

    def toggle_count(icon, item):
        if root.state() == "withdrawn":
            root.deiconify()
        else:
            root.withdraw()

    image = Image.new("RGB", (64, 64), (255, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.text((10, 25), "WC", fill="white")

    menu = Menu(MenuItem("Show/Hide", toggle_count), MenuItem("Quit", quit_program))
    return Icon("Word Counter", image, menu=menu)


def add_word():
    word = word_input.get().strip().lower()
    if word and word not in counter.words_to_track:
        counter.words_to_track.append(word)
        counter.counts[word] = 0
        counter.update_listbox()
        word_input.delete(0, tk.END)


def remove_word():
    selected_word = words_listbox.get(tk.ACTIVE).split(":")[0]
    if selected_word in counter.words_to_track:
        counter.words_to_track.remove(selected_word)
        del counter.counts[selected_word]
        counter.update_listbox()


def toggle_listening():
    if counter.running:
        counter.running = False
        pause_button.config(text="Resume Listening")
    else:
        counter.running = True
        threading.Thread(target=counter.listen_and_count).start()
        threading.Thread(target=counter.update_volume_meter).start()
        pause_button.config(text="Pause Listening")


def save_transcript():
    file_path = filedialog.asksaveasfilename(
        defaultextension=".txt", filetypes=[("Text Files", "*.txt")]
    )
    if file_path:
        with open(file_path, "w") as file:
            file.write(transcript_text.get("1.0", tk.END))


def show_logs():
    if log_window.state() == "withdrawn":
        log_window.deiconify()
    else:
        log_window.withdraw()


def get_audio_devices():
    p = pyaudio.PyAudio()
    devices = []
    device_map = {}
    seen_devices = set()
    default_device_index = p.get_default_input_device_info()["index"]
    default_device_name = None
    for i in range(p.get_device_count()):
        device_info = p.get_device_info_by_index(i)
        device_name = device_info["name"]
        if (
            device_info["maxInputChannels"] > 0
            and device_info["hostApi"] == 0  # Ensure the device is enabled and usable
            and device_name not in seen_devices
        ):
            if i == default_device_index:
                device_name += " (Default)"
                default_device_name = device_name
            devices.append(device_name)
            device_map[device_name] = i
            seen_devices.add(device_name)
    p.terminate()
    return devices, default_device_name, device_map


if __name__ == "__main__":
    exe_dir = os.path.dirname(sys.argv[0])
    save_file = os.path.join(exe_dir, "word_counter.json")
    words_to_track = ["example", "count", "sigma"]  # Default words to track

    # Create the tkinter window
    root = tk.Tk()
    root.title("Word Counter")
    root.geometry("1000x800")

    style = ttk.Style()
    style.theme_use("clam")

    # Top controls
    top_frame = ttk.Frame(root)
    top_frame.pack(side=tk.TOP, fill=tk.X, pady=10)

    volume_label = ttk.Label(top_frame, text="Volume:", font=("Helvetica", 12))
    volume_label.pack(side=tk.LEFT, padx=5)

    volume_meter = ttk.Progressbar(
        top_frame, orient="horizontal", length=200, mode="determinate"
    )
    volume_meter.pack(side=tk.LEFT, padx=10)

    audio_devices, default_device_name, device_map = get_audio_devices()
    audio_source_var = tk.StringVar(value=default_device_name)
    max_length = max(len(name) for name in audio_devices)
    audio_device_menu = ttk.Combobox(
        top_frame,
        textvariable=audio_source_var,
        values=audio_devices,
        width=max_length,
    )
    audio_device_menu.pack(side=tk.LEFT, padx=5)

    save_button = ttk.Button(top_frame, text="Save Transcript", command=save_transcript)
    save_button.pack(side=tk.LEFT, padx=5)

    pause_button = ttk.Button(
        top_frame, text="Pause Listening", command=toggle_listening
    )
    pause_button.pack(side=tk.LEFT, padx=5)

    log_button = ttk.Button(top_frame, text="Show Logs", command=show_logs)
    log_button.pack(side=tk.LEFT, padx=5)

    # Main content area
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Sidebar for words list
    sidebar_frame = ttk.Frame(main_frame)
    sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10)

    word_input = ttk.Entry(sidebar_frame, font=("Helvetica", 14))
    word_input.pack(side=tk.TOP, fill=tk.X, pady=5)

    add_button = ttk.Button(sidebar_frame, text="+", command=add_word)
    add_button.pack(side=tk.TOP, pady=5)

    remove_button = ttk.Button(sidebar_frame, text="-", command=remove_word)
    remove_button.pack(side=tk.TOP, pady=5)

    words_listbox = tk.Listbox(sidebar_frame, height=20)
    words_listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)

    # Transcript area
    transcript_frame = ttk.Frame(main_frame)
    transcript_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    transcript_text = tk.Text(transcript_frame, height=15, width=50, wrap="word")
    transcript_text.pack(fill=tk.BOTH, expand=True)

    counter = WordCounter(
        save_file,
        words_to_track,
        audio_source_var,
        volume_meter,
        transcript_text,
        words_listbox,
        device_map,
    )

    # Create the log window at the start
    log_window = tk.Toplevel(root)
    log_window.title("Logs")
    log_window.geometry("1000x800")
    log_window.withdraw()

    log_text = tk.Text(log_window, wrap="word")
    log_text.pack(fill=tk.BOTH, expand=True)

    text_handler = TextHandler(log_text)
    text_handler.setFormatter(formatter)
    logger.addHandler(text_handler)

    # Override the window close event for the log window
    def hide_log_window():
        log_window.withdraw()

    log_window.protocol("WM_DELETE_WINDOW", hide_log_window)

    # Override the window close event for the main window
    def on_closing():
        logging.debug("Main window closing")
        root.withdraw()
        log_window.withdraw()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Run in a separate thread
    listen_thread = threading.Thread(target=counter.listen_and_count)
    listen_thread.start()

    # Run the volume meter update in a separate thread
    volume_thread = threading.Thread(target=counter.update_volume_meter)
    volume_thread.start()

    # Create taskbar icon
    icon = create_icon(counter, root)
    icon_thread = threading.Thread(target=icon.run)
    icon_thread.start()

    # Start the tkinter main loop
    try:
        root.mainloop()
    except Exception as e:
        logging.error(f"Error in main loop: {e}")

    # Ensure all threads are properly stopped
    logging.debug("Stopping all threads")
    counter.running = False
    listen_thread.join()
    volume_thread.join()
    icon.stop()
    icon_thread.join()
    logging.debug("All threads stopped")

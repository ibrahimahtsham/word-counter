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


class WordCounter:
    def __init__(
        self,
        save_path,
        words_to_track,
        label,
        audio_source_var,
        indicator_label,
        transcript_text,
    ):
        self.save_path = save_path
        self.words_to_track = [
            word.strip().lower() for word in words_to_track.split(",")
        ]
        self.counts = self.load_counts()
        self.recognizer = sr.Recognizer()
        self.running = True
        self.label = label
        self.audio_source_var = audio_source_var
        self.indicator_label = indicator_label
        self.transcript_text = transcript_text
        self.update_label()

    def load_counts(self):
        if os.path.exists(self.save_path):
            with open(self.save_path, "r") as file:
                return json.load(file)
        return {word: 0 for word in self.words_to_track}

    def save_counts(self):
        with open(self.save_path, "w") as file:
            json.dump(self.counts, file)

    def update_label(self):
        counts_text = ", ".join(
            [f"{word}: {count}" for word, count in self.counts.items()]
        )
        self.label.config(text=f"Counts: {counts_text}")

    def listen_and_count(self):
        while self.running:
            try:
                source = (
                    sr.Microphone()
                    if self.audio_source_var.get() == "mic"
                    else sr.AudioFile("path_to_desktop_audio.wav")
                )
                with source as audio_source:
                    self.recognizer.adjust_for_ambient_noise(audio_source)
                    self.indicator_label.config(text="Listening...", foreground="green")
                    while self.running:
                        try:
                            audio = self.recognizer.listen(audio_source, timeout=5)
                            text = self.recognizer.recognize_google(audio).lower()
                            self.transcript_text.insert(tk.END, text + "\n")
                            self.transcript_text.see(tk.END)
                            for word in self.words_to_track:
                                if word in text:
                                    self.counts[word] += text.split().count(word)
                            self.save_counts()
                            self.update_label()
                        except sr.UnknownValueError:
                            continue
                        except sr.WaitTimeoutError:
                            break
            except Exception as e:
                self.indicator_label.config(text="Error occurred", foreground="red")
                print(f"Error: {e}")


def create_icon(counter, root):
    def quit_program(icon, item):
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


def update_words():
    counter.words_to_track = [
        word.strip().lower() for word in word_input.get().split(",")
    ]
    counter.counts = {word: 0 for word in counter.words_to_track}
    counter.update_label()


def toggle_listening():
    if counter.running:
        counter.running = False
        pause_button.config(text="Resume Listening")
    else:
        counter.running = True
        threading.Thread(target=counter.listen_and_count).start()
        pause_button.config(text="Pause Listening")


def save_transcript():
    file_path = filedialog.asksaveasfilename(
        defaultextension=".txt", filetypes=[("Text Files", "*.txt")]
    )
    if file_path:
        with open(file_path, "w") as file:
            file.write(transcript_text.get("1.0", tk.END))


if __name__ == "__main__":
    exe_dir = os.path.dirname(sys.argv[0])
    save_file = os.path.join(exe_dir, "word_counter.json")
    words_to_track = "example, count, sigma"  # Default words to track

    # Create the tkinter window
    root = tk.Tk()
    root.title("Word Counter")
    root.geometry("500x600")

    style = ttk.Style()
    style.theme_use("clam")

    label = ttk.Label(root, text="Counts: 0", font=("Helvetica", 16))
    label.pack(pady=10)

    word_input = ttk.Entry(root, font=("Helvetica", 14))
    word_input.insert(0, words_to_track)
    word_input.pack(pady=10)

    update_button = ttk.Button(root, text="Update Words", command=update_words)
    update_button.pack(pady=5)

    audio_source_var = tk.StringVar(value="mic")
    mic_radio = ttk.Radiobutton(
        root, text="Microphone", variable=audio_source_var, value="mic"
    )
    desktop_radio = ttk.Radiobutton(
        root, text="Desktop Audio", variable=audio_source_var, value="desktop"
    )
    mic_radio.pack()
    desktop_radio.pack()

    indicator_label = ttk.Label(
        root, text="Not Listening", font=("Helvetica", 12), foreground="red"
    )
    indicator_label.pack(pady=10)

    transcript_text = tk.Text(root, height=15, width=50, wrap="word")
    transcript_text.pack(pady=10)

    pause_button = ttk.Button(root, text="Pause Listening", command=toggle_listening)
    pause_button.pack(pady=5)

    save_button = ttk.Button(root, text="Save Transcript", command=save_transcript)
    save_button.pack(pady=5)

    counter = WordCounter(
        save_file,
        words_to_track,
        label,
        audio_source_var,
        indicator_label,
        transcript_text,
    )

    # Override the window close event
    def on_closing():
        root.withdraw()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Run in a separate thread
    listen_thread = threading.Thread(target=counter.listen_and_count)
    listen_thread.start()

    # Create taskbar icon
    icon = create_icon(counter, root)
    icon_thread = threading.Thread(target=icon.run)
    icon_thread.start()

    # Start the tkinter main loop
    root.mainloop()

    # Ensure all threads are properly stopped
    counter.running = False
    listen_thread.join()
    icon.stop()
    icon_thread.join()

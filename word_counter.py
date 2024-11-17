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
        audio_source_var,
        indicator_label,
        transcript_text,
        words_listbox,
    ):
        self.save_path = save_path
        self.words_to_track = words_to_track
        self.counts = self.load_counts()
        self.recognizer = sr.Recognizer()
        self.running = True
        self.audio_source_var = audio_source_var
        self.indicator_label = indicator_label
        self.transcript_text = transcript_text
        self.words_listbox = words_listbox
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
                            self.update_listbox()
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
    words_to_track = ["example", "count", "sigma"]  # Default words to track

    # Create the tkinter window
    root = tk.Tk()
    root.title("Word Counter")
    root.geometry("800x600")

    style = ttk.Style()
    style.theme_use("clam")

    # Top controls
    top_frame = ttk.Frame(root)
    top_frame.pack(side=tk.TOP, fill=tk.X, pady=10)

    indicator_label = ttk.Label(
        top_frame, text="Not Listening", font=("Helvetica", 12), foreground="red"
    )
    indicator_label.pack(side=tk.LEFT, padx=10)

    audio_source_var = tk.StringVar(value="mic")
    mic_radio = ttk.Radiobutton(
        top_frame, text="Microphone", variable=audio_source_var, value="mic"
    )
    desktop_radio = ttk.Radiobutton(
        top_frame, text="Desktop Audio", variable=audio_source_var, value="desktop"
    )
    mic_radio.pack(side=tk.LEFT, padx=5)
    desktop_radio.pack(side=tk.LEFT, padx=5)

    save_button = ttk.Button(top_frame, text="Save Transcript", command=save_transcript)
    save_button.pack(side=tk.LEFT, padx=5)

    pause_button = ttk.Button(
        top_frame, text="Pause Listening", command=toggle_listening
    )
    pause_button.pack(side=tk.LEFT, padx=5)

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
        indicator_label,
        transcript_text,
        words_listbox,
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

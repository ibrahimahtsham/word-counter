import os
import json
import speech_recognition as sr
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
import threading
import tkinter as tk
import sys


class WordCounter:
    def __init__(self, save_path, word_to_track, label, audio_source_var):
        self.save_path = save_path
        self.word_to_track = word_to_track.lower()
        self.count = self.load_count()
        self.recognizer = sr.Recognizer()
        self.running = True
        self.label = label
        self.audio_source_var = audio_source_var
        self.update_label()

    def load_count(self):
        if os.path.exists(self.save_path):
            with open(self.save_path, "r") as file:
                return json.load(file).get(self.word_to_track, 0)
        return 0

    def save_count(self):
        data = {self.word_to_track: self.count}
        with open(self.save_path, "w") as file:
            json.dump(data, file)

    def update_label(self):
        self.label.config(text=f"Count: {self.count}")

    def listen_and_count(self):
        while self.running:
            source = (
                sr.Microphone()
                if self.audio_source_var.get() == "mic"
                else sr.AudioFile("path_to_desktop_audio.wav")
            )
            with source as audio_source:
                self.recognizer.adjust_for_ambient_noise(audio_source)
                try:
                    print("Listening...")
                    audio = self.recognizer.listen(audio_source)
                    text = self.recognizer.recognize_google(audio).lower()
                    if self.word_to_track in text:
                        self.count += text.split().count(self.word_to_track)
                        print(f"Detected '{self.word_to_track}'! Count: {self.count}")
                        self.save_count()
                        self.update_label()
                except sr.UnknownValueError:
                    continue


def create_icon(counter, root):
    def quit_program(icon, item):
        counter.running = False
        counter.save_count()
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


if __name__ == "__main__":
    exe_dir = os.path.dirname(sys.argv[0])
    save_file = os.path.join(exe_dir, "swear_counter.json")
    word_to_track = "example"  # Change this to your desired word

    # Create the tkinter window
    root = tk.Tk()
    root.title("Word Counter")
    root.overrideredirect(True)  # Make the window borderless
    label = tk.Label(root, text="Count: 0", font=("Helvetica", 16))
    label.pack(pady=20)

    audio_source_var = tk.StringVar(value="mic")
    mic_radio = tk.Radiobutton(
        root, text="Microphone", variable=audio_source_var, value="mic"
    )
    desktop_radio = tk.Radiobutton(
        root, text="Desktop Audio", variable=audio_source_var, value="desktop"
    )
    mic_radio.pack()
    desktop_radio.pack()

    counter = WordCounter(save_file, word_to_track, label, audio_source_var)

    # Run in a separate thread
    threading.Thread(target=counter.listen_and_count).start()

    # Create taskbar icon
    icon = create_icon(counter, root)
    threading.Thread(target=icon.run).start()

    # Start the tkinter main loop
    root.mainloop()

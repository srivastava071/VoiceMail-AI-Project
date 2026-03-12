
import subprocess
import speech_recognition as sr
import sounddevice as sd
import scipy.io.wavfile as wav


def speak(text):
    try:
        clean_text = text.replace('"', '').replace("'", "")
        print("Speaking:", clean_text)

        subprocess.run([
            "powershell",
            "-Command",
            f"Add-Type -AssemblyName System.Speech; "
            f"$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$speak.Speak('{clean_text}');"
        ])

    except Exception as e:
        print("TTS Error:", e)


def stop_speaking():
    pass


def take_voice_input():
    samplerate = 16000
    duration = 5

    print("Listening...")

    recording = sd.rec(
        int(duration * samplerate),
        samplerate=samplerate,
        channels=1,
        dtype="int16",
        device=1
    )

    sd.wait()
    wav.write("voice.wav", samplerate, recording)

    recognizer = sr.Recognizer()

    try:
        with sr.AudioFile("voice.wav") as source:
            audio = recognizer.record(source)

        text = recognizer.recognize_google(audio)
        print("Recognized:", text)
        return text.lower()

    except Exception as e:
        print("STT Error:", e)
        return None

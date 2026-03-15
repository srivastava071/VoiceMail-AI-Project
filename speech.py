import os
import tempfile
import speech_recognition as sr
import sounddevice as sd
import scipy.io.wavfile as wav

# Global language setting
_current_language = "en-IN"


def set_language(lang):
    global _current_language
    _current_language = lang
    print(f"Language set to: {lang}")


def get_language():
    return _current_language


def speak(text, lang=None):
    """Speak using gTTS + playsound for BOTH English and Hindi. No PowerShell."""
    try:
        use_lang = lang or _current_language
        print(f"Speaking [{use_lang}]: {text}")

        from gtts import gTTS
        from playsound import playsound

        # Map our lang codes to gTTS lang codes
        gtts_lang = "hi" if use_lang == "hi-IN" else "en"

        tmp_mp3 = os.path.join(tempfile.gettempdir(), "tts_output.mp3")

        # Remove old file first to avoid playsound lock
        if os.path.exists(tmp_mp3):
            try:
                os.remove(tmp_mp3)
            except:
                pass

        tts = gTTS(text=text, lang=gtts_lang, slow=False)
        tts.save(tmp_mp3)
        playsound(tmp_mp3)

    except Exception as e:
        print(f"TTS Error: {e}")


def stop_speaking():
    """Stop any ongoing TTS by removing the mp3 file."""
    try:
        tmp_mp3 = os.path.join(tempfile.gettempdir(), "tts_output.mp3")
        if os.path.exists(tmp_mp3):
            os.remove(tmp_mp3)
        print("Speaking stopped.")
    except Exception as e:
        print(f"Stop Error: {e}")


def take_voice_input(lang=None):
    """Record and recognise speech. Supports en-IN and hi-IN."""
    samplerate = 16000
    duration = 5

    use_lang = lang or _current_language
    print(f"Listening [{use_lang}]...")

    try:
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

        with sr.AudioFile("voice.wav") as source:
            audio = recognizer.record(source)

        text = recognizer.recognize_google(audio, language=use_lang)
        print(f"Recognized [{use_lang}]: {text}")
        return text.lower()

    except sr.UnknownValueError:
        print("Could not understand audio.")
        return None
    except sr.RequestError as e:
        print(f"Google STT Error: {e}")
        return None
    except Exception as e:
        print("STT Error:", e)
        return None
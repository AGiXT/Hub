import ffmpeg
import numpy as np
from whispercpp import Whisper
import sounddevice as sd
import soundfile as sf
import requests
import os


class whisper_stt:
    def __init__(self, WHISPER_MODEL="base.en"):
        self.commands = {
            "Record Audio and Convert to Text": self.record_and_convert_to_text,
            "Read Audio from File": self.read_audio_from_file,
        }
        # https://huggingface.co/ggerganov/whisper.cpp
        # Models: tiny, tiny.en, base, base.en, small, small.en, medium, medium.en, large, large-v1
        os.makedirs(os.path.join(os.getcwd(), "models", "whispercpp"), exist_ok=True)
        model_path = os.path.join(
            os.getcwd(), "models", "whispercpp", f"ggml-{WHISPER_MODEL}.bin"
        )
        if not os.path.exists(model_path):
            r = requests.get(
                f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-{WHISPER_MODEL}.bin",
                allow_redirects=True,
            )
            open(model_path, "wb").write(r.content)
        self.w = Whisper.from_pretrained(
            model_name=WHISPER_MODEL, basedir=os.path.join(os.getcwd(), "models")
        )

    def record_audio(self, duration_in_seconds: int = 10, filename="recording.wav"):
        if not filename.startswith(os.path.join(os.getcwd(), "WORKSPACE")):
            filename = os.path.join(os.getcwd(), "WORKSPACE", filename)
        samplerate = 44100
        data = sd.rec(
            frames=duration_in_seconds * samplerate, samplerate=samplerate, channels=1
        )
        sd.wait()
        sf.write(filename, data=data, samplerate=samplerate)
        print(f"The {duration_in_seconds} second recording was saved as '{filename}'.")
        return data

    def read_audio_from_file(self, filename: str):
        if not filename.startswith(os.path.join(os.getcwd(), "WORKSPACE")):
            filename = os.path.join(os.getcwd(), "WORKSPACE", filename)
        try:
            y, _ = (
                ffmpeg.input(filename, threads=0)
                .output("-", format="s16le", acodec="pcm_s16le", ac=1, ar=16000)
                .run(
                    cmd=["ffmpeg", "-nostdin"], capture_stdout=True, capture_stderr=True
                )
            )
        except ffmpeg.Error as e:
            raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e

        arr = np.frombuffer(y, np.int16).flatten().astype(np.float32) / 32768.0

        return self.w.transcribe(arr)

    def record_and_convert_to_text(
        self, duration_in_seconds: int = 10, filename="recording.wav"
    ):
        if not filename.startswith(os.path.join(os.getcwd(), "WORKSPACE")):
            filename = os.path.join(os.getcwd(), "WORKSPACE", filename)
        data = self.record_audio(
            duration_in_seconds=duration_in_seconds, filename=filename
        )
        text = self.read_audio_from_file(filename=filename)
        return text
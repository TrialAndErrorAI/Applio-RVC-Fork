import librosa
import numpy as np
import av
from io import BytesIO
import ffmpeg
import os
import traceback
import sys
import requests
import uuid
import base64

from lib.infer.infer_libs.csvutil import CSVutil
#import csv

platform_stft_mapping = {
    'linux': 'stftpitchshift',
    'darwin': 'stftpitchshift',
    'win32': 'stftpitchshift.exe',
}

stft = platform_stft_mapping.get(sys.platform)

def wav2(i, o, format):
    inp = av.open(i, 'rb')
    if format == "m4a": format = "mp4"
    out = av.open(o, 'wb', format=format)
    if format == "ogg": format = "libvorbis"
    if format == "mp4": format = "aac"

    ostream = out.add_stream(format)

    for frame in inp.decode(audio=0):
        for p in ostream.encode(frame): out.mux(p)

    for p in ostream.encode(None): out.mux(p)

    out.close()
    inp.close()

def audio2(i, o, format, sr):
    inp = av.open(i, 'rb')
    out = av.open(o, 'wb', format=format)
    if format == "ogg": format = "libvorbis"
    if format == "f32le": format = "pcm_f32le"

    ostream = out.add_stream(format, channels=1)
    ostream.sample_rate = sr

    for frame in inp.decode(audio=0):
        for p in ostream.encode(frame): out.mux(p)

    out.close()
    inp.close()

def load_audion(file, sr):
    try:
        file = (
            file.strip(" ").strip('"').strip("\n").strip('"').strip(" ")
        )  # 防止小白拷路径头尾带了空格和"和回车
        with open(file, "rb") as f:
            with BytesIO() as out:
                audio2(f, out, "f32le", sr)
                return np.frombuffer(out.getvalue(), np.float32).flatten()

    except AttributeError:
        audio = file[1] / 32768.0
        if len(audio.shape) == 2:
            audio = np.mean(audio, -1)
        return librosa.resample(audio, orig_sr=file[0], target_sr=16000)

    except Exception as e:
        raise RuntimeError(f"Failed to load audio: {e}")




def load_audio(file, sr, DoFormant=False, Quefrency=1.0, Timbre=1.0):
    # Directory where temporary files will be stored
    input = file
    isNotFile = False
    assets_dir = os.path.join(os.getcwd(), 'assets', 'audios')
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)

    temp_file_name = str(uuid.uuid4())
    temp_file_extension = None
    temp_file = os.path.join(assets_dir, f"{temp_file_name}")

    if isinstance(input, str):
        # Check if input is a URL
        if input.startswith('http://') or input.startswith('https://'):
            response = requests.get(input)
            if response.status_code != 200:
                return "Error downloading the file from URL", None
            isNotFile = True
            file_extension = os.path.splitext(input.split("/")[-1])[1]
            temp_file_extension = "wav"
            file = f"{temp_file}.wav"
            with open(file, 'wb') as f:
                f.write(response.content)
        # Check if input is a base64 string
        elif input.startswith('data:'):
            isNotFile = True
            header, encoded = input.split(',', 1)
            file_extension = header.split('/')[1].split(';')[0]
            temp_file_extension = file_extension
            file = f"{temp_file}.{file_extension}"
            with open(file, "wb") as f:
                f.write(base64.b64decode(encoded))
        # Otherwise, consider it a file path
        else:
            file = input.strip(" ").strip('"').strip("\n").strip('"').strip(" ")
            if not os.path.exists(file):
                return "Audio was not properly selected or doesn't exist", None
    else:
        return "Input should be a string (file path, URL, or base64)", None

    converted = False

    if isNotFile:
        # replace and only keep the file name with assets/audios/
        file = "assets/audios/" + f"{temp_file_name}.{temp_file_extension}"

    print("File path processed: ", file, "\n")

    try:
        if not file.endswith(".wav"):
            converted = True
            converting = (
                ffmpeg.input(file, threads=0)
                .output(f"{file}.wav")
                .run(cmd=["ffmpeg", "-nostdin"], capture_stdout=True, capture_stderr=True)
            )
            file = f"{file}.wav"
            print(f" · File converted to Wav format: {file}\n")

        if DoFormant:
            command = (
                f'{stft} -i "{file}" -q "{Quefrency}" '
                f'-t "{Timbre}" -o "{file}FORMANTED.wav"'
            )
            os.system(command)
            file = f"{file}FORMANTED.wav"
            print(f" · Formanted {file}!\n")

        print("Getting audio data...")
        with open(file, "rb") as f:
            with BytesIO() as out:
                audio2(f, out, "f32le", sr)
                audio_data = np.frombuffer(out.getvalue(), np.float32).flatten()

        print("Audio data loaded!\n")

        if converted:
            try:
                os.remove(file)
            except Exception as e:
                print(f"Error in removing file: {e}")
            converted = False

        print("Audio data removed if converted!\n")

        if isNotFile:
            return audio_data, file
        else:
            return audio_data
    except Exception as e:
        print("An error occurred: ", traceback.format_exc())
        raise RuntimeError(traceback.format_exc())


def check_audio_duration(file):
    try:
        file = file.strip(" ").strip('"').strip("\n").strip('"').strip(" ")

        probe = ffmpeg.probe(file)

        duration = float(probe['streams'][0]['duration'])

        if duration < 0.76:
            print(
                f"Audio file, {file.split('/')[-1]}, under ~0.76s detected - file is too short. Target at least 1-2s for best results."
            )
            return False

        return True
    except Exception as e:
        raise RuntimeError(f"Failed to check audio duration: {e}")
import speech_recognition as sr
import faster_whisper
from gtts import gTTS
import os
import asyncio
from datetime import datetime
import time
from gpiozero import LED

# 全域變數與模型初始化
recognizer = sr.Recognizer()
model = faster_whisper.WhisperModel("small", device="cpu")
led1 = LED(17)


if not os.path.exists("turnoff.mp3"):
    gTTS(text="關閉電燈", lang="zh-tw").save("turnoff.mp3")
if not os.path.exists("turnon.mp3"):
    gTTS(text="打開電燈", lang="zh-tw").save("turnon.mp3")
if not os.path.exists("hey_pi.mp3"):
    gTTS(text="有何吩咐，2秒後再發問", lang="zh-tw").save("hey_pi.mp3")

# 播放音效的非同步函式
def play_audio(file):
    # 這裡依照你的環境選擇播放方法，例如 afplay, aplay 或其他工具
    os.system(f"{audio_to_play_music} {file}")

# 定義一個同步的函式來取得錄音
def get_audio_from_mic():
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source)
        return recognizer.listen(source)

# 異步處理錄音檔案辨識
async def do_task(audio):
    global playing_audio
    # 儲存第一段錄音
    date_time_precise = datetime.now().strftime("%Y%m%d%H%M%S%f")
    file_name = f"input_{date_time_precise}.wav"
    with open(file_name, "wb") as f:
        f.write(audio.get_wav_data())

    try:
        segments, info = model.transcribe(
            file_name,
            beam_size=1,  
            vad_filter=True, 
            vad_parameters=dict(min_silence_duration_ms=500),
            language="en"
        )
        segments = list(segments)
        result = " ".join([s.text for s in segments])
        print("You said: " + result)

        if "turn off the light" in result.lower():
            playing_audio = True
            led1.off()
            play_audio("turnoff.mp3")
            playing_audio = False 
        elif "turn on the light" in result.lower():
            playing_audio = True
            led1.on()
            play_audio("turnon.mp3")
            playing_audio = False
        elif is_python_command(result):
            playing_audio = True
            play_audio("hey_pi.mp3")

            with sr.Microphone() as source2:
                recognizer.adjust_for_ambient_noise(source2)
                audio2 = recognizer.listen(source2)

            # 將 audio2 存成檔案
            date_time_precise2 = datetime.now().strftime("%Y%m%d%H%M%S%f")
            file_name2 = f"input2_{date_time_precise2}.wav"
            with open(file_name2, "wb") as f:
                f.write(audio2.get_wav_data())

            segments2, _ = model.transcribe(
                file_name2,
                beam_size=1,  
                vad_filter=True, 
                vad_parameters=dict(min_silence_duration_ms=500),
                language="en"
            )
            segments2 = list(segments2)
            result2 = " ".join([s.text for s in segments2])
            print("python command: " + result2)

            os.remove(file_name2)
            time.sleep(0.5)
            playing_audio = False

    except Exception as e:
        print(f"Error: {e}")
    finally:
        os.remove(file_name)

def is_python_command(result : str) -> bool:
    return "okay python" in result.lower().replace(",","") or "okay pysad" in result.lower().replace(",","") or "ok python" in result.lower().replace(",","")

# 主持續監聽的非同步迴圈
async def listen_continuously():
    with sr.Microphone() as source:
        # 初次調整背景噪音
        recognizer.adjust_for_ambient_noise(source)
        while True:
            if not playing_audio:
                print("Listening...")
                audio = await asyncio.to_thread(recognizer.listen, source)
                asyncio.create_task(do_task(audio))
            else:
                await asyncio.sleep(0.1)

# 控制播放與錄音的旗標，避免同時發生
playing_audio = False
audio_to_play_music = "aplay"

asyncio.run(listen_continuously())

import requests
import base64
import os
import sys

url = "http://localhost:8001/chat/speech"
wav_path = "test_audio.wav"

if not os.path.exists(wav_path):
    import numpy as np
    import soundfile as sf
    print("Tạo file âm thanh giả lập...")
    samples = np.random.uniform(-0.1, 0.1, 16000 * 2).astype(np.float32)
    sf.write(wav_path, samples, 16000)

print(f"Đang gửi request POST tới {url} với file âm thanh...")
try:
    with open(wav_path, "rb") as f:
        files = {"audio": ("test_audio.wav", f, "audio/wav")}
        response = requests.post(url, files=files)
        
    print(f"HTTP Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("\n--- KẾT QUẢ TỪ SERVER ---")
        print(f"Trạng thái: {data.get('success')}")
        print(f"[STT] Người dùng nói: {data.get('user_text')}")
        print(f"[LLM] Bot trả lời   : {data.get('ai_text')}")
        
        audio_b64 = data.get("ai_audio_base64")
        if audio_b64:
            with open("output_ai_audio.mp3", "wb") as out:
                out.write(base64.b64decode(audio_b64))
            print("Đã lưu âm thanh TTS (Bot Voice) vào 'output_ai_audio.mp3'")
    else:
        print("Lỗi từ server:", response.text)
except Exception as e:
    print(f"Không thể kết nối đến server: {e}")
    print("Bạn đã chạy 'uvicorn main:app --port 8001' chưa?")

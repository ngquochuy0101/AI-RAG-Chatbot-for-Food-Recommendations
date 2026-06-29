import os
import sys
from gtts import gTTS
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import soundfile as sf

print("1. Tạo file âm thanh mẫu (tiếng ồn trắng để test model load)...")
samples = np.random.uniform(-1, 1, 16000 * 2).astype(np.float32) # 2 giây noise
sf.write("test_audio.wav", samples, 16000)

import logging
logging.basicConfig(level=logging.INFO)

print("2. Đang nạp hệ thống STT và thử nghiệm...")
from local_asr import process_audio_sherpa
res = process_audio_sherpa("test_audio.wav")
print("\n" + "="*50)
print("KẾT QUẢ STT TỪ SHERPA:")
print(res)
print("="*50)

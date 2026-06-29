import os
import sys
import numpy as np
from pydub import AudioSegment
import sherpa_onnx
import logging

logger = logging.getLogger(__name__)

# Thêm đường dẫn tới thư viện sherpa-vietnamese-asr
SHERPA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sherpa-vietnamese-asr"))
sys.path.append(SHERPA_ROOT)

from core.punctuation_restorer_improved import ImprovedPunctuationRestorer

MODEL_DIR = os.path.join(SHERPA_ROOT, "models", "zipformer-30m-rnnt-6000h")

recognizer = None
punct_restorer = None

def init_models():
    global recognizer, punct_restorer
    if recognizer is None:
        logger.info("Đang tải mô hình Sherpa-ONNX STT...")
        recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=os.path.join(MODEL_DIR, "encoder-epoch-20-avg-10.onnx"),
            decoder=os.path.join(MODEL_DIR, "decoder-epoch-20-avg-10.onnx"),
            joiner=os.path.join(MODEL_DIR, "joiner-epoch-20-avg-10.onnx"),
            tokens=os.path.join(MODEL_DIR, "tokens.txt"),
            num_threads=4,
            sample_rate=16000,
            feature_dim=80,
            decoding_method="modified_beam_search",
            max_active_paths=4
        )
        logger.info("Đã tải xong Sherpa-ONNX.")
    
    if punct_restorer is None:
        logger.info("Đang tải mô hình ViBERT Punctuation Restorer...")
        punct_restorer = ImprovedPunctuationRestorer(confidence=0.3)
        logger.info("Đã tải xong Punctuation Restorer.")

def process_audio_sherpa(audio_file_path: str) -> str:
    init_models()
    logger.info(f"Đang xử lý STT (Sherpa) cho file: {audio_file_path}")
    
    import numpy as np
    import subprocess
    import tempfile
    import soundfile as sf
    import os

    # Use direct ffmpeg subprocess to robustly decode WebM/Opus without relying on ffprobe duration
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
        temp_wav_name = temp_wav.name
        
    try:
        cmd = [
            "ffmpeg", "-y", "-i", audio_file_path, 
            "-ac", "1", "-ar", "16000", "-f", "wav", temp_wav_name
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        samples, _ = sf.read(temp_wav_name, dtype='float32')
    except Exception as e:
        logger.error(f"Error decoding audio with ffmpeg: {e}")
        samples = np.array([], dtype=np.float32)
    finally:
        if os.path.exists(temp_wav_name):
            os.remove(temp_wav_name)
    
    # Prevent crashing on short audio (< 0.5s) which causes zipformer convolution shape errors
    if len(samples) < 8000:
        logger.warning("Audio is too short, ignoring.")
        return ""
    
    stream = recognizer.create_stream()
    stream.accept_waveform(16000, samples)
    recognizer.decode_stream(stream)
    text = stream.result.text.strip()
    
    if not text:
        return ""
    
    # Khôi phục dấu câu
    logger.info("Đang thêm dấu câu...")
    final_text = punct_restorer.restore(text)
    logger.info(f"Kết quả STT (có dấu): {final_text}")
    return final_text

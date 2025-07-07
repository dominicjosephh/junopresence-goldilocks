import whisper
import tempfile
import os
from pathlib import Path
import logging
from typing import Optional, Dict, Any

# Set up logging to match your existing format
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class SpeechRecognitionService:
    """Handles speech-to-text conversion using OpenAI Whisper"""
    
    def __init__(self, model_size: str = "base"):
        """
        Initialize Whisper model
        
        Args:
            model_size: Whisper model size ("tiny", "base", "small", "medium", "large")
                       - tiny: Fastest, least accurate (~39 MB)
                       - base: Good balance (~74 MB) - RECOMMENDED FOR START
                       - small: Better accuracy (~244 MB)
                       - medium: Even better (~769 MB)
                       - large: Best accuracy (~1550 MB)
        """
        self.model_size = model_size
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the Whisper model (lazy loading for faster startup)"""
        try:
            logger.info(f"Loading Whisper model: {self.model_size}")
            self.model = whisper.load_model(self.model_size)
            logger.info(f"✅ Whisper {self.model_size} model loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load Whisper model: {e}")
            raise
    
    def transcribe_audio(self, audio_data: bytes, language: str = None) -> Dict[str, Any]:
        """
        Transcribe audio data to text
        
        Args:
            audio_data: Raw audio bytes (supports m4a, mp3, wav, etc.)
            language: Optional language code ('en', 'es', 'fr', etc.)
        
        Returns:
            Dict containing transcription results
        """
        if not self.model:
            self._load_model()
        
        # Create temporary file for audio data
        with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name
        
        try:
            logger.info(f"🎙️ Transcribing audio file: {len(audio_data)} bytes")
            
            # Transcribe with Whisper
            options = {
                "fp16": False,  # Use FP32 for better compatibility
                "language": language,  # Auto-detect if None
                "task": "transcribe"  # vs "translate"
            }
            
            result = self.model.transcribe(temp_file_path, **options)
            
            # Extract key information
            transcription = {
                "text": result["text"].strip(),
                "language": result.get("language", "unknown"),
                "confidence": self._calculate_confidence(result),
                "segments": result.get("segments", []),
                "detected_language": result.get("language"),
                "processing_time": None  # You can add timing if needed
            }
            
            logger.info(f"✅ Transcription successful: '{transcription['text'][:50]}...'")
            logger.info(f"🌍 Detected language: {transcription['language']}")
            
            return transcription
            
        except Exception as e:
            logger.error(f"❌ Transcription failed: {e}")
            return {
                "text": "",
                "language": "unknown",
                "confidence": 0.0,
                "error": str(e),
                "segments": [],
                "detected_language": None
            }
        
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"⚠️ Failed to delete temp file: {e}")
    
    def _calculate_confidence(self, whisper_result: Dict) -> float:
        """
        Calculate confidence score from Whisper segments
        
        Args:
            whisper_result: Raw Whisper transcription result
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        segments = whisper_result.get("segments", [])
        if not segments:
            return 0.5  # Default confidence if no segments
        
        # Average the "no_speech_prob" scores (lower = more confident)
        no_speech_probs = []
        for segment in segments:
            if "no_speech_prob" in segment:
                no_speech_probs.append(segment["no_speech_prob"])
        
        if not no_speech_probs:
            return 0.7  # Default confidence
        
        # Convert no_speech_prob to confidence (invert and normalize)
        avg_no_speech = sum(no_speech_probs) / len(no_speech_probs)
        confidence = 1.0 - avg_no_speech
        
        # Ensure confidence is between 0.0 and 1.0
        return max(0.0, min(1.0, confidence))
    
    def is_audio_silent(self, audio_data: bytes, threshold: float = 0.01) -> bool:
        """
        Check if audio data is mostly silent
        
        Args:
            audio_data: Raw audio bytes
            threshold: Silence threshold (0.0 to 1.0)
            
        Returns:
            True if audio is considered silent
        """
        # Simple implementation - you could use librosa for more sophisticated detection
        try:
            import numpy as np
            
            # Convert bytes to numpy array (basic approach)
            # Note: This is a simplified approach. For production, use librosa or pydub
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            if len(audio_array) == 0:
                return True
            
            # Calculate RMS (Root Mean Square) amplitude
            rms = np.sqrt(np.mean(audio_array.astype(float) ** 2))
            max_possible = 32767  # For 16-bit audio
            normalized_rms = rms / max_possible
            
            is_silent = normalized_rms < threshold
            logger.info(f"🔊 Audio RMS: {normalized_rms:.4f}, Silent: {is_silent}")
            
            return is_silent
            
        except Exception as e:
            logger.warning(f"⚠️ Could not analyze audio silence: {e}")
            return False  # Assume not silent if we can't analyze
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        return {
            "model_size": self.model_size,
            "is_loaded": self.model is not None,
            "supported_languages": whisper.tokenizer.LANGUAGES if hasattr(whisper, 'tokenizer') else []
        }

# Global instance (singleton pattern for efficiency)
speech_service = None

def get_speech_service(model_size: str = "base") -> SpeechRecognitionService:
    """Get or create the global speech recognition service instance"""
    global speech_service
    
    if speech_service is None or speech_service.model_size != model_size:
        logger.info(f"🔄 Initializing speech service with model: {model_size}")
        speech_service = SpeechRecognitionService(model_size)
    
    return speech_service

# Installation requirements:
"""
Add to your requirements.txt:

openai-whisper>=20231117
torch>=2.0.0
numpy>=1.21.0
"""

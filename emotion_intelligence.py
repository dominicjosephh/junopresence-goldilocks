import os
import time
import librosa
import numpy as np
from sklearn.preprocessing import StandardScaler
from scipy.stats import skew, kurtosis
from typing import Dict, Tuple, Any
import warnings
from fastapi.responses import JSONResponse
from fastapi import UploadFile

warnings.filterwarnings('ignore')

# Emotional Intelligence Configuration
EMOTION_DETECTION_ENABLED = os.getenv('EMOTION_DETECTION_ENABLED', 'true').lower() == 'true'
EMOTION_ADAPTATION_ENABLED = os.getenv('EMOTION_ADAPTATION_ENABLED', 'true').lower() == 'true'
VOICE_ANALYSIS_CACHE_TTL = 300  # 5 minutes

class VoiceEmotionAnalyzer:
    def __init__(self):
        self.feature_scaler = StandardScaler()
        self.is_trained = False
        self.emotion_history = []
        self.emotion_mapping = {
            'happy': ['joy', 'excitement', 'enthusiasm'],
            'sad': ['sadness', 'melancholy', 'depression'],
            'angry': ['anger', 'frustration', 'irritation'],
            'calm': ['relaxed', 'peaceful', 'content'],
            'excited': ['energetic', 'hyped', 'animated'],
            'stressed': ['anxious', 'worried', 'tense'],
            'neutral': ['normal', 'baseline', 'default']
        }

    def extract_audio_features(self, audio_data: bytes) -> Dict[str, float]:
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.float32)
            if len(audio_array) < 1024:
                return self._get_default_features()
            sample_rate = 22050
            features = {}
            spectral_centroids = librosa.feature.spectral_centroid(y=audio_array, sr=sample_rate)[0]
            features['spectral_centroid_mean'] = np.mean(spectral_centroids)
            features['spectral_centroid_std'] = np.std(spectral_centroids)
            rolloff = librosa.feature.spectral_rolloff(y=audio_array, sr=sample_rate)[0]
            features['spectral_rolloff_mean'] = np.mean(rolloff)
            features['spectral_rolloff_std'] = np.std(rolloff)
            zcr = librosa.feature.zero_crossing_rate(audio_array)[0]
            features['zero_crossing_rate_mean'] = np.mean(zcr)
            features['zero_crossing_rate_std'] = np.std(zcr)
            mfccs = librosa.feature.mfcc(y=audio_array, sr=sample_rate, n_mfcc=13)
            for i in range(13):
                features[f'mfcc_{i}_mean'] = np.mean(mfccs[i])
                features[f'mfcc_{i}_std'] = np.std(mfccs[i])
            chroma = librosa.feature.chroma_stft(y=audio_array, sr=sample_rate)
            features['chroma_mean'] = np.mean(chroma)
            features['chroma_std'] = np.std(chroma)
            tonnetz = librosa.feature.tonnetz(y=audio_array, sr=sample_rate)
            features['tonnetz_mean'] = np.mean(tonnetz)
            features['tonnetz_std'] = np.std(tonnetz)
            rms = librosa.feature.rms(y=audio_array)[0]
            features['rms_energy_mean'] = np.mean(rms)
            features['rms_energy_std'] = np.std(rms)
            tempo, _ = librosa.beat.beat_track(y=audio_array, sr=sample_rate)
            features['tempo'] = tempo
            bandwidth = librosa.feature.spectral_bandwidth(y=audio_array, sr=sample_rate)[0]
            features['spectral_bandwidth_mean'] = np.mean(bandwidth)
            features['spectral_bandwidth_std'] = np.std(bandwidth)
            features['audio_mean'] = np.mean(audio_array)
            features['audio_std'] = np.std(audio_array)
            features['audio_skew'] = skew(audio_array)
            features['audio_kurtosis'] = kurtosis(audio_array)
            return features
        except Exception as e:
            print(f"🔴 Feature extraction error: {e}")
            return self._get_default_features()

    def _get_default_features(self) -> Dict[str, float]:
        return {
            'spectral_centroid_mean': 0.5, 'spectral_centroid_std': 0.1,
            'spectral_rolloff_mean': 0.5, 'spectral_rolloff_std': 0.1,
            'zero_crossing_rate_mean': 0.1, 'zero_crossing_rate_std': 0.05,
            'rms_energy_mean': 0.1, 'rms_energy_std': 0.05,
            'tempo': 120.0, 'spectral_bandwidth_mean': 0.5,
            'spectral_bandwidth_std': 0.1, 'audio_mean': 0.0,
            'audio_std': 0.1, 'audio_skew': 0.0, 'audio_kurtosis': 0.0,
            'chroma_mean': 0.5, 'chroma_std': 0.1,
            'tonnetz_mean': 0.0, 'tonnetz_std': 0.1
        }

    def analyze_emotion_heuristic(self, features: Dict[str, float]) -> Dict[str, float]:
        emotion_scores = {
            'happy': 0.0,
            'sad': 0.0,
            'angry': 0.0,
            'calm': 0.0,
            'excited': 0.0,
            'stressed': 0.0,
            'neutral': 0.5
        }
        try:
            if features.get('spectral_centroid_mean', 0) > 0.6 and features.get('rms_energy_mean', 0) > 0.15:
                emotion_scores['happy'] += 0.4
            if features.get('tempo', 120) > 130:
                emotion_scores['happy'] += 0.2
            if features.get('rms_energy_mean', 0) < 0.08:
                emotion_scores['sad'] += 0.3
            if features.get('spectral_centroid_mean', 0) < 0.4:
                emotion_scores['sad'] += 0.3
            if features.get('rms_energy_mean', 0) > 0.2:
                emotion_scores['angry'] += 0.3
            if features.get('zero_crossing_rate_mean', 0) > 0.15:
                emotion_scores['angry'] += 0.3
            if (features.get('rms_energy_mean', 0) > 0.18 and 
                features.get('tempo', 120) > 140 and 
                features.get('spectral_centroid_mean', 0) > 0.65):
                emotion_scores['excited'] += 0.5
            if (0.05 < features.get('rms_energy_mean', 0) < 0.12 and 
                features.get('spectral_centroid_std', 0) < 0.15):
                emotion_scores['calm'] += 0.4
            if (features.get('rms_energy_std', 0) > 0.1 and 
                features.get('zero_crossing_rate_std', 0) > 0.08):
                emotion_scores['stressed'] += 0.4
            total_score = sum(emotion_scores.values())
            if total_score > 0:
                emotion_scores = {k: v/total_score for k, v in emotion_scores.items()}
            return emotion_scores
        except Exception as e:
            print(f"🔴 Emotion analysis error: {e}")
            return emotion_scores

    def get_dominant_emotion(self, emotion_scores: Dict[str, float]) -> Tuple[str, float]:
        if not emotion_scores:
            return 'neutral', 0.5
        dominant_emotion = max(emotion_scores.keys(), key=lambda k: emotion_scores[k])
        confidence = emotion_scores[dominant_emotion]
        return dominant_emotion, confidence

    def analyze_voice_emotion(self, audio_data: bytes) -> Dict[str, Any]:
        if not EMOTION_DETECTION_ENABLED:
            return {
                'emotion': 'neutral',
                'confidence': 0.5,
                'scores': {'neutral': 0.5},
                'features': {},
                'analysis_time': 0.0
            }
        start_time = time.time()
        try:
            features = self.extract_audio_features(audio_data)
            emotion_scores = self.analyze_emotion_heuristic(features)
            dominant_emotion, confidence = self.get_dominant_emotion(emotion_scores)
            analysis_time = time.time() - start_time
            result = {
                'emotion': dominant_emotion,
                'confidence': round(confidence, 3),
                'scores': {k: round(v, 3) for k, v in emotion_scores.items()},
                'features': {k: round(v, 4) for k, v in features.items()},
                'analysis_time': round(analysis_time, 3)
            }
            self.emotion_history.append({
                'timestamp': time.time(),
                'emotion': dominant_emotion,
                'confidence': confidence,
                'scores': emotion_scores
            })
            if len(self.emotion_history) > 20:
                self.emotion_history = self.emotion_history[-20:]
            print(f"🎭 Emotion detected: {dominant_emotion} ({confidence:.2f} confidence) in {analysis_time:.3f}s")
            return result
        except Exception as e:
            print(f"🔴 Voice emotion analysis failed: {e}")
            return {
                'emotion': 'neutral',
                'confidence': 0.5,
                'scores': {'neutral': 0.5},
                'features': {},
                'analysis_time': time.time() - start_time,
                'error': str(e)
            }

    def get_emotion_pattern(self) -> Dict[str, Any]:
        if not self.emotion_history:
            return {'pattern': 'insufficient_data', 'dominant_emotions': [], 'mood_stability': 0.5}
        recent_emotions = [entry['emotion'] for entry in self.emotion_history[-10:]]
        emotion_counts = {}
        for emotion in recent_emotions:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        dominant_emotions = sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        unique_emotions = len(set(recent_emotions))
        mood_stability = unique_emotions / len(recent_emotions) if recent_emotions else 0.5
        if len(dominant_emotions) > 0:
            most_common = dominant_emotions[0][0]
            frequency = dominant_emotions[0][1] / len(recent_emotions)
            if frequency > 0.7:
                pattern = f"consistently_{most_common}"
            elif frequency > 0.4:
                pattern = f"mostly_{most_common}"
            else:
                pattern = "varied_emotions"
        else:
            pattern = "neutral"
        return {
            'pattern': pattern,
            'dominant_emotions': dominant_emotions,
            'mood_stability': round(mood_stability, 3),
            'recent_count': len(recent_emotions),
            'emotion_distribution': emotion_counts
        }

class EmotionalResponseAdapter:
    def __init__(self):
        self.adaptation_rules = {
            'happy': {
                'amplify': ['Joy', 'Hype'],
                'maintain': ['Base', 'Sassy'],
                'tone_shift': 'more energetic and celebratory',
                'avoid': ['sadness', 'negativity']
            },
            'sad': {
                'amplify': ['Empathy'],
                'soften': ['Sassy', 'Challenger', 'Assert'],
                'tone_shift': 'gentle, supportive, and understanding',
                'add_elements': ['comfort', 'validation', 'hope']
            },
            'angry': {
                'amplify': ['Empathy'],
                'soften': ['Sassy', 'Challenger'],
                'tone_shift': 'calm, validating, and de-escalating',
                'avoid': ['confrontation', 'criticism']
            },
            'excited': {
                'amplify': ['Hype', 'Joy'],
                'maintain': ['Sassy'],
                'tone_shift': 'match the energy and enthusiasm',
                'add_elements': ['encouragement', 'celebration']
            },
            'stressed': {
                'amplify': ['Empathy'],
                'soften': ['Assert', 'Challenger'],
                'tone_shift': 'calming, reassuring, and practical',
                'add_elements': ['solutions', 'breathing_space']
            },
            'calm': {
                'maintain': ['all'],
                'tone_shift': 'maintain the peaceful energy',
                'add_elements': ['mindfulness', 'presence']
            }
        }

    def adapt_voice_mode(self, detected_emotion: str, current_voice_mode: str, 
                         confidence: float) -> Tuple[str, str]:
        if not EMOTION_ADAPTATION_ENABLED or confidence < 0.6:
            return current_voice_mode, "no_adaptation"
        adaptation_rule = self.adaptation_rules.get(detected_emotion, {})
        if current_voice_mode in adaptation_rule.get('amplify', []):
            return current_voice_mode, f"amplify_{current_voice_mode.lower()}"
        if current_voice_mode in adaptation_rule.get('soften', []):
            if detected_emotion in ['sad', 'stressed', 'angry']:
                return 'Empathy', f"soften_to_empathy"
            else:
                return 'Base', f"soften_to_base"
        optimal_modes = {
            'happy': 'Joy',
            'excited': 'Hype', 
            'sad': 'Empathy',
            'angry': 'Empathy',
            'stressed': 'Empathy',
            'calm': current_voice_mode
        }
        suggested_mode = optimal_modes.get(detected_emotion, current_voice_mode)
        adaptation_reason = f"emotion_optimized_for_{detected_emotion}"
        return suggested_mode, adaptation_reason

    def generate_emotion_aware_prompt_addition(self, emotion_data: Dict[str, Any], voice_mode: str) -> str:
        if not emotion_data or not EMOTION_ADAPTATION_ENABLED:
            return ""
        emotion = emotion_data.get('emotion', 'neutral')
        confidence = emotion_data.get('confidence', 0.5)
        if confidence < 0.6:
            return ""
        adaptation_rule = self.adaptation_rules.get(emotion, {})
        tone_shift = adaptation_rule.get('tone_shift', '')
        add_elements = adaptation_rule.get('add_elements', [])
        avoid_elements = adaptation_rule.get('avoid', [])
        prompt_parts = []
        if tone_shift:
            prompt_parts.append(f"EMOTIONAL CONTEXT: The user seems {emotion} (confidence: {confidence:.2f}). Respond with a {tone_shift} tone.")
        if add_elements:
            elements_text = ', '.join(add_elements)
            prompt_parts.append(f"Include elements of: {elements_text}.")
        if avoid_elements:
            avoid_text = ', '.join(avoid_elements)
            prompt_parts.append(f"Avoid: {avoid_text}.")
        if prompt_parts:
            return "\n\nEMOTIONAL INTELLIGENCE: " + " ".join(prompt_parts)
        return ""

voice_emotion_analyzer = VoiceEmotionAnalyzer()
emotional_adapter = EmotionalResponseAdapter()

# FastAPI endpoints (import these in main.py and use as handlers)
async def get_emotion_analysis():
    emotion_pattern = voice_emotion_analyzer.get_emotion_pattern()
    return JSONResponse(content={
        "emotion_detection_enabled": EMOTION_DETECTION_ENABLED,
        "emotion_adaptation_enabled": EMOTION_ADAPTATION_ENABLED,
        "recent_emotion_pattern": emotion_pattern,
        "emotion_history_count": len(voice_emotion_analyzer.emotion_history),
        "supported_emotions": list(voice_emotion_analyzer.emotion_mapping.keys()),
        "adaptation_rules": emotional_adapter.adaptation_rules,
        "cache_ttl": VOICE_ANALYSIS_CACHE_TTL
    })

async def get_emotion_history():
    return JSONResponse(content={
        "emotion_history": voice_emotion_analyzer.emotion_history[-10:],
        "pattern_analysis": voice_emotion_analyzer.get_emotion_pattern()
    })

async def test_emotion_analysis(audio: UploadFile):
    try:
        contents = await audio.read()
        if len(contents) == 0:
            return JSONResponse(content={"error": "Empty audio file"}, status_code=400)
        emotion_data = voice_emotion_analyzer.analyze_voice_emotion(contents)
        suggested_mode, adaptation_reason = emotional_adapter.adapt_voice_mode(
            emotion_data['emotion'], 'Base', emotion_data['confidence']
        )
        emotion_prompt = emotional_adapter.generate_emotion_aware_prompt_addition(emotion_data, 'Base')
        return JSONResponse(content={
            "emotion_analysis": emotion_data,
            "suggested_voice_mode": suggested_mode,
            "adaptation_reason": adaptation_reason,
            "emotion_prompt_addition": emotion_prompt,
            "test_timestamp": time.time()
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

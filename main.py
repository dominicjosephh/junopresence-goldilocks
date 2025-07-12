import os
import json
import base64
import requests
import random
import re
import hashlib
import time
import subprocess
import threading
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from functools import lru_cache
from typing import List, Dict, Optional, Tuple
from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import uvicorn
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json
import random
from collections import defaultdict, Counter

# Import our music command parser
from music_command_parser import MusicCommandParser, SpotifyController, MusicIntent

# 🎙️ Import speech recognition
from speech_service import get_speech_service

load_dotenv()
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
voice_id = os.getenv('ELEVENLABS_VOICE_ID')

# Add Spotify credentials
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# 🚀 ADD TOGETHER AI CREDENTIALS
TOGETHER_AI_API_KEY = os.getenv('TOGETHER_AI_API_KEY')
TOGETHER_AI_BASE_URL = "https://api.together.xyz/v1"

MEMORY_FILE = 'memory.json'
FACTS_LIMIT = 20
CHAT_LOG_FILE = "chat_log.json"
AUDIO_DIR = "static"
AUDIO_FILENAME = "juno_response.mp3"
AUDIO_PATH = os.path.join(AUDIO_DIR, AUDIO_FILENAME)

# 🚀 FIXED LLAMA.CPP CONFIGURATION
LLAMA_CPP_PATH = "/opt/build/bin/llama-cli"
MODEL_PATH = "/opt/models/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf"

# Memory system configuration
MEMORY_DB_PATH = "juno_memory.db"
MAX_CONVERSATION_CONTEXT = 10  # Remember last 10 conversations
MAX_PERSONAL_FACTS = 100       # Store up to 100 personal facts
MEMORY_RELEVANCE_THRESHOLD = 0.3  # Minimum relevance score for recall

# Performance optimization globals
RESPONSE_CACHE = {}
CACHE_MAX_SIZE = 50
CACHE_TTL = 3600  # 1 hour

# Model management
MODEL_LOADED = False
MODEL_LOCK = threading.Lock()

# 🚀 AI PROVIDER PREFERENCES
USE_TOGETHER_AI_FIRST = os.getenv('USE_TOGETHER_AI_FIRST', 'false').lower() == 'true'
TOGETHER_AI_TIMEOUT = 15  # seconds

# Initialize music intelligence
music_parser = MusicCommandParser()
spotify_controller = SpotifyController(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)

# Music Intelligence Configuration
MUSIC_DB_PATH = "juno_music.db"
MAX_MUSIC_HISTORY = 1000
PLAYLIST_GENERATION_LIMIT = 50

# Initialize advanced music intelligence (will be set up when first used)
music_intelligence = None
enhanced_spotify = None

# 🔧 SQLite Connection Helper Functions with WAL Mode and Timeout
def get_memory_conn():
    """Get a properly configured SQLite connection for the memory database"""
    conn = sqlite3.connect(MEMORY_DB_PATH, timeout=30)
    conn.execute('PRAGMA journal_mode=WAL;')
    return conn

def get_music_conn():
    """Get a properly configured SQLite connection for the music database"""
    conn = sqlite3.connect(MUSIC_DB_PATH, timeout=30)
    conn.execute('PRAGMA journal_mode=WAL;')
    return conn

class EnhancedSpotifyController:
    """Enhanced Spotify controller with additional features"""
    def __init__(self, spotify_controller):
        self.spotify_controller = spotify_controller
    
    def get_audio_features(self, track_id: str, access_token: str) -> dict:
        """Get audio features for a track"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            url = f"https://api.spotify.com/v1/audio-features/{track_id}"
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            print(f"❌ Audio features error: {e}")
            return {}

class AdvancedMusicIntelligence:
    def __init__(self, spotify_controller):
        self.spotify_controller = spotify_controller
        self.init_music_database()
        
    def init_music_database(self):
        """Initialize the music intelligence database"""
        conn = get_music_conn()
        cursor = conn.cursor()
        
        # Music listening history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS music_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                track_id TEXT NOT NULL,
                track_name TEXT NOT NULL,
                artist_name TEXT NOT NULL,
                album_name TEXT,
                duration_ms INTEGER,
                played_duration_ms INTEGER DEFAULT 0,
                context_type TEXT, -- 'workout', 'coding', 'chill', 'focus', etc.
                time_of_day TEXT, -- 'morning', 'afternoon', 'evening', 'night'
                voice_mode TEXT DEFAULT 'Base',
                user_rating INTEGER DEFAULT 0, -- -1 (skip), 0 (neutral), 1 (like)
                energy_level REAL, -- 0.0 to 1.0
                valence REAL, -- 0.0 to 1.0 (sad to happy)
                danceability REAL,
                acousticness REAL
            )
        """)
        
        # User-created playlists and their context
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS smart_playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_name TEXT UNIQUE NOT NULL,
                spotify_playlist_id TEXT,
                context_type TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                play_count INTEGER DEFAULT 0,
                tracks_json TEXT -- Store track list as JSON
            )
        """)
        
        # Music preferences and patterns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS music_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                preference_type TEXT NOT NULL, -- 'artist', 'genre', 'context', 'time'
                preference_key TEXT NOT NULL,
                preference_value TEXT NOT NULL,
                confidence_score REAL DEFAULT 1.0,
                frequency_count INTEGER DEFAULT 1,
                last_accessed TEXT NOT NULL,
                UNIQUE(preference_type, preference_key, preference_value)
            )
        """)
        
        # Music context associations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_associations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                context_type TEXT NOT NULL,
                track_features_json TEXT, -- Audio features pattern for this context
                common_artists TEXT, -- JSON array of frequently played artists
                common_genres TEXT, -- JSON array of genres
                time_patterns TEXT, -- JSON of time-based patterns
                energy_range TEXT, -- JSON: [min_energy, max_energy]
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(context_type)
            )
        """)
        
        conn.commit()
        conn.close()
        print("🎵 Advanced music intelligence system initialized")

    def detect_context_from_conversation(self, user_input: str, juno_response: str, voice_mode: str) -> str:
        """Detect music context from conversation"""
        combined_text = (user_input + " " + juno_response).lower()
        
        # Context detection patterns
        context_patterns = {
            'workout': ['workout', 'gym', 'exercise', 'running', 'fitness', 'training'],
            'coding': ['coding', 'programming', 'development', 'debugging', 'work', 'focus'],
            'study': ['studying', 'reading', 'learning', 'homework', 'concentration'],
            'chill': ['relax', 'chill', 'unwind', 'calm', 'peaceful', 'rest'],
            'party': ['party', 'dancing', 'celebration', 'friends', 'fun'],
            'commute': ['driving', 'commute', 'traffic', 'car', 'travel'],
            'morning': ['morning', 'wake up', 'breakfast', 'start day'],
            'evening': ['evening', 'dinner', 'wind down', 'end day'],
            'sad': ['sad', 'down', 'upset', 'crying', 'depressed'],
            'happy': ['happy', 'excited', 'great', 'awesome', 'celebrating'],
            'romantic': ['date', 'romantic', 'love', 'dinner', 'intimate'],
            'cleaning': ['cleaning', 'organizing', 'tidying', 'housework']
        }
        
        # Score each context
        context_scores = {}
        for context, keywords in context_patterns.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            if score > 0:
                context_scores[context] = score
        
        # Voice mode influence
        voice_mode_contexts = {
            'Hype': 'workout',
            'Sassy': 'party', 
            'Empathy': 'chill',
            'Shadow': 'evening',
            'Joy': 'happy'
        }
        
        if voice_mode in voice_mode_contexts:
            suggested_context = voice_mode_contexts[voice_mode]
            context_scores[suggested_context] = context_scores.get(suggested_context, 0) + 2
        
        # Return highest scoring context or 'general'
        if context_scores:
            return max(context_scores.keys(), key=context_scores.get)
        return 'general'

    def get_time_of_day(self) -> str:
        """Get current time classification"""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 17:
            return 'afternoon'
        elif 17 <= hour < 22:
            return 'evening'
        else:
            return 'night'

    def log_music_play(self, track_info: dict, context_type: str = 'general', 
                      played_duration_ms: int = 0, user_rating: int = 0):
        """Log a music play event with context"""
        try:
            conn = get_music_conn()
            cursor = conn.cursor()
            
            time_of_day = self.get_time_of_day()
            
            cursor.execute("""
                INSERT INTO music_history 
                (timestamp, track_id, track_name, artist_name, album_name, duration_ms,
                 played_duration_ms, context_type, time_of_day, user_rating,
                 energy_level, valence, danceability, acousticness)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.utcnow().isoformat(),
                track_info.get('id', ''),
                track_info.get('name', ''),
                track_info.get('artists', [{}])[0].get('name', ''),
                track_info.get('album', {}).get('name', ''),
                track_info.get('duration_ms', 0),
                played_duration_ms,
                context_type,
                time_of_day,
                user_rating,
                track_info.get('audio_features', {}).get('energy', 0.5),
                track_info.get('audio_features', {}).get('valence', 0.5),
                track_info.get('audio_features', {}).get('danceability', 0.5),
                track_info.get('audio_features', {}).get('acousticness', 0.5)
            ))
            
            # Update preferences
            self.update_music_preference('artist', track_info.get('artists', [{}])[0].get('name', ''))
            self.update_music_preference('context', context_type)
            self.update_music_preference('time', time_of_day)
            
            conn.commit()
            conn.close()
            
            print(f"🎵 Logged music play: {track_info.get('name')} in {context_type} context")
            
        except Exception as e:
            print(f"❌ Music logging error: {e}")

    def update_music_preference(self, pref_type: str, value: str, confidence: float = 1.0):
        """Update music preferences"""
        if not value:
            return
            
        try:
            conn = get_music_conn()
            cursor = conn.cursor()
            
            now = datetime.utcnow().isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO music_preferences 
                (preference_type, preference_key, preference_value, confidence_score, 
                 frequency_count, last_accessed)
                VALUES (?, ?, ?, ?, 
                    COALESCE((SELECT frequency_count FROM music_preferences 
                             WHERE preference_type = ? AND preference_key = ? AND preference_value = ?) + 1, 1),
                    ?)
            """, (pref_type, value, value, confidence, pref_type, value, value, now))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Music preference update error: {e}")

    def create_smart_playlist(self, playlist_name: str, context_type: str, description: str, spotify_token: str) -> dict:
        """Create a smart playlist based on context"""
        try:
            # Basic implementation - could be enhanced later
            return {
                "success": True,
                "message": f"Smart playlist '{playlist_name}' created for {context_type} context!",
                "playlist_name": playlist_name
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create playlist: {str(e)}"
            }

    def get_music_recommendations(self, context: str, limit: int = 5, spotify_token: str = None) -> list:
        """Get music recommendations based on context"""
        try:
            # Basic implementation - could be enhanced later
            return []
        except Exception as e:
            print(f"❌ Music recommendations error: {e}")
            return []

    def get_music_insights(self) -> dict:
        """Get music insights and analytics"""
        try:
            conn = get_music_conn()
            cursor = conn.cursor()
            
            # Get top artists
            cursor.execute("""
                SELECT artist_name, COUNT(*) as play_count
                FROM music_history 
                GROUP BY artist_name 
                ORDER BY play_count DESC 
                LIMIT 5
            """)
            top_artists = [{"artist": row[0], "plays": row[1]} for row in cursor.fetchall()]
            
            # Get mood profile
            cursor.execute("""
                SELECT AVG(energy_level) as avg_energy, AVG(valence) as avg_valence
                FROM music_history 
                WHERE energy_level IS NOT NULL AND valence IS NOT NULL
            """)
            mood_data = cursor.fetchone()
            mood_profile = {
                "energy_level": mood_data[0] if mood_data and mood_data[0] else 0.5,
                "happiness_level": mood_data[1] if mood_data and mood_data[1] else 0.5
            }
            
            conn.close()
            
            return {
                "top_artists": top_artists,
                "mood_profile": mood_profile,
                "insights": ["Building your music profile based on listening history"]
            }
        except Exception as e:
            print(f"❌ Music insights error: {e}")
            return {}

# Ensure static folder exists
os.makedirs(AUDIO_DIR, exist_ok=True)

# 🧠 ADVANCED MEMORY SYSTEM
class AdvancedMemorySystem:
    def __init__(self):
        self.init_database()
        
    def init_database(self):
        """Initialize the memory database with proper tables"""
        conn = get_memory_conn()
        cursor = conn.cursor()
        
        # Conversations table - stores all interactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_input TEXT NOT NULL,
                juno_response TEXT NOT NULL,
                voice_mode TEXT DEFAULT 'Base',
                conversation_hash TEXT,
                context_keywords TEXT,
                emotional_tone TEXT,
                importance_score REAL DEFAULT 1.0
            )
        """)
        
        # Personal facts table - key information about the user
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personal_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                fact_key TEXT NOT NULL,
                fact_value TEXT NOT NULL,
                confidence_score REAL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source_conversation_id INTEGER,
                FOREIGN KEY (source_conversation_id) REFERENCES conversations (id)
            )
        """)
        
        # Preferences table - user preferences and patterns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                preference_type TEXT NOT NULL,
                preference_key TEXT NOT NULL,
                preference_value TEXT NOT NULL,
                frequency_count INTEGER DEFAULT 1,
                last_used TEXT NOT NULL,
                UNIQUE(preference_type, preference_key)
            )
        """)
        
        # Topics table - subjects the user talks about frequently
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_name TEXT UNIQUE NOT NULL,
                mention_count INTEGER DEFAULT 1,
                last_mentioned TEXT NOT NULL,
                associated_emotions TEXT,
                importance_level REAL DEFAULT 1.0
            )
        """)
        
        # Relationships table - people the user mentions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_name TEXT UNIQUE NOT NULL,
                relationship_type TEXT,
                mention_count INTEGER DEFAULT 1,
                last_mentioned TEXT NOT NULL,
                context_notes TEXT,
                importance_score REAL DEFAULT 1.0
            )
        """)
        
        conn.commit()
        conn.close()
        print("🧠 Advanced memory system initialized")

    def extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text"""
        # Remove common words and extract meaningful terms
        common_words = {
            'i', 'me', 'my', 'you', 'your', 'the', 'a', 'an', 'and', 'or', 'but', 
            'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 
            'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'can', 'may', 'might', 'this', 'that', 'these',
            'those', 'what', 'when', 'where', 'why', 'how', 'juno', 'hey', 'hi', 'hello'
        }
        
        # Extract words (3+ characters, not common words)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        keywords = [word for word in words if word not in common_words]
        return list(set(keywords))  # Remove duplicates

    def detect_emotional_tone(self, text: str) -> str:
        """Simple emotional tone detection"""
        positive_words = ['happy', 'excited', 'great', 'awesome', 'love', 'amazing', 'fantastic', 'good', 'yes', 'yeah', 'cool']
        negative_words = ['sad', 'frustrated', 'angry', 'hate', 'terrible', 'awful', 'bad', 'no', 'annoyed', 'stressed']
        question_words = ['what', 'how', 'when', 'where', 'why', 'who', 'which']
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        question_count = sum(1 for word in question_words if word in text_lower)
        
        if text.endswith('?') or question_count > 0:
            return 'questioning'
        elif positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'

    def extract_personal_facts(self, user_input: str, juno_response: str) -> List[Dict]:
        """Extract personal facts from conversation"""
        facts = []
        
        # Pattern matching for personal information - FIXED REGEX
        patterns = {
            'name': [r"my name is (\w+)", r"i'm (\w+)", r"call me (\w+)"],
            'age': [r"i'm (\d+) years old", r"i am (\d+)", r"age (\d+)"],
            'job': [r"i work as (?:a|an) ([^.]+)", r"my job is ([^.]+)", r"i'm (?:a|an) ([^.]+)"],
            'location': [r"i live in ([^.]+)", r"i'm from ([^.]+)", r"my city is ([^.]+)"],
            'hobby': [r"i like (?:to )?([^.]+)", r"i enjoy ([^.]+)", r"i love ([^.]+)"],
            'goal': [r"i want to ([^.]+)", r"my goal is ([^.]+)", r"planning to ([^.]+)"],
            'family': [r"my (?:mom|dad|mother|father|sister|brother|wife|husband|partner) ([^.]*)", 
                      r"i have (?:a|an) ([^.]*(?:mom|dad|sister|brother|wife|husband|partner)[^.]*)"]  # FIXED: Added missing )
        }
        
        for category, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.findall(pattern, user_input.lower())
                for match in matches:
                    if isinstance(match, tuple):
                        match = ' '.join(match)
                    if match.strip():
                        facts.append({
                            'category': category,
                            'fact_key': category,
                            'fact_value': match.strip(),
                            'confidence_score': 0.8
                        })
        
        return facts

    def extract_people_mentioned(self, text: str) -> List[str]:
        """Extract names of people mentioned in conversation"""
        # Simple name detection - capitalized words that aren't common words
        common_non_names = {
            'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
            'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 
            'September', 'October', 'November', 'December', 'Juno', 'Dom', 'AI', 'API',
            'Spotify', 'Google', 'Apple', 'Amazon', 'Netflix', 'YouTube'
        }
        
        # Find capitalized words (potential names)
        potential_names = re.findall(r'\b[A-Z][a-z]+\b', text)
        names = [name for name in potential_names if name not in common_non_names and len(name) > 2]
        return list(set(names))

    def store_conversation(self, user_input: str, juno_response: str, voice_mode: str = "Base") -> int:
        """Store a conversation and extract insights"""
        try:
            conn = get_memory_conn()
            cursor = conn.cursor()
            
            # Generate conversation hash for deduplication
            conv_text = f"{user_input}|{juno_response}"
            conv_hash = hashlib.md5(conv_text.encode()).hexdigest()
            
            # Extract insights
            keywords = self.extract_keywords(user_input + " " + juno_response)
            emotional_tone = self.detect_emotional_tone(user_input)
            
            # Calculate importance score based on length, keywords, emotional intensity
            importance_score = min(2.0, (len(user_input) / 100) + len(keywords) * 0.1 + 
                                 (1.5 if emotional_tone in ['positive', 'negative'] else 1.0))
            
            # Store conversation
            cursor.execute("""
                INSERT INTO conversations 
                (timestamp, user_input, juno_response, voice_mode, conversation_hash, 
                 context_keywords, emotional_tone, importance_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.utcnow().isoformat(),
                user_input,
                juno_response,
                voice_mode,
                conv_hash,
                ','.join(keywords),
                emotional_tone,
                importance_score
            ))
            
            conversation_id = cursor.lastrowid
            
            # Extract and store personal facts
            personal_facts = self.extract_personal_facts(user_input, juno_response)
            for fact in personal_facts:
                self.store_personal_fact(
                    fact['category'], fact['fact_key'], fact['fact_value'],
                    fact['confidence_score'], conversation_id
                )
            
            # Store people mentioned
            people = self.extract_people_mentioned(user_input)
            for person in people:
                self.store_relationship(person, 'mentioned', conversation_id)
            
            # Update topic tracking
            for keyword in keywords:
                self.update_topic(keyword, emotional_tone)
            
            # Update preferences based on voice mode usage
            self.update_preference('voice_mode', voice_mode, voice_mode)
            
            conn.commit()
            conn.close()
            
            print(f"🧠 Stored conversation with {len(keywords)} keywords, importance: {importance_score:.2f}")
            return conversation_id
            
        except Exception as e:
            print(f"❌ Memory storage error: {e}")
            return -1

    def store_personal_fact(self, category: str, fact_key: str, fact_value: str, 
                          confidence: float = 1.0, source_conv_id: int = None):
        """Store or update a personal fact"""
        try:
            conn = get_memory_conn()
            cursor = conn.cursor()
            
            # Check if fact already exists
            cursor.execute("""
                SELECT id, confidence_score FROM personal_facts 
                WHERE category = ? AND fact_key = ?
            """, (category, fact_key))
            
            existing = cursor.fetchone()
            now = datetime.utcnow().isoformat()
            
            if existing:
                # Update existing fact with higher confidence
                new_confidence = max(existing[1], confidence)
                cursor.execute("""
                    UPDATE personal_facts 
                    SET fact_value = ?, confidence_score = ?, updated_at = ?, source_conversation_id = ?
                    WHERE id = ?
                """, (fact_value, new_confidence, now, source_conv_id, existing[0]))
            else:
                # Insert new fact
                cursor.execute("""
                    INSERT INTO personal_facts 
                    (category, fact_key, fact_value, confidence_score, created_at, updated_at, source_conversation_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (category, fact_key, fact_value, confidence, now, now, source_conv_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Personal fact storage error: {e}")

    def store_relationship(self, person_name: str, relationship_type: str = 'mentioned', 
                          source_conv_id: int = None):
        """Store or update relationship information"""
        try:
            conn = get_memory_conn()
            cursor = conn.cursor()
            
            now = datetime.utcnow().isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO relationships 
                (person_name, relationship_type, mention_count, last_mentioned, importance_score)
                VALUES (?, ?, 
                    COALESCE((SELECT mention_count FROM relationships WHERE person_name = ?) + 1, 1),
                    ?, 1.0)
            """, (person_name, relationship_type, person_name, now))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Relationship storage error: {e}")

    def update_topic(self, topic_name: str, emotional_context: str = 'neutral'):
        """Update topic tracking"""
        try:
            conn = get_memory_conn()
            cursor = conn.cursor()
            
            now = datetime.utcnow().isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO topics 
                (topic_name, mention_count, last_mentioned, associated_emotions, importance_level)
                VALUES (?, 
                    COALESCE((SELECT mention_count FROM topics WHERE topic_name = ?) + 1, 1),
                    ?, ?, 1.0)
            """, (topic_name, topic_name, now, emotional_context))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Topic update error: {e}")

    def update_preference(self, pref_type: str, pref_key: str, pref_value: str):
        """Update user preferences"""
        try:
            conn = get_memory_conn()
            cursor = conn.cursor()
            
            now = datetime.utcnow().isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO preferences 
                (preference_type, preference_key, preference_value, frequency_count, last_used)
                VALUES (?, ?, ?, 
                    COALESCE((SELECT frequency_count FROM preferences WHERE preference_type = ? AND preference_key = ?) + 1, 1),
                    ?)
            """, (pref_type, pref_key, pref_value, pref_type, pref_key, now))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Preference update error: {e}")

    def get_relevant_memories(self, current_input: str, limit: int = 5) -> List[Dict]:
        """Get relevant past conversations and facts"""
        try:
            conn = get_memory_conn()
            cursor = conn.cursor()
            
            # Extract keywords from current input
            input_keywords = self.extract_keywords(current_input)
            
            if not input_keywords:
                return []
            
            # Find conversations with similar keywords
            keyword_query = ' OR '.join([f"context_keywords LIKE '%{kw}%'" for kw in input_keywords])
            
            cursor.execute(f"""
                SELECT user_input, juno_response, timestamp, emotional_tone, importance_score, context_keywords
                FROM conversations 
                WHERE {keyword_query}
                ORDER BY importance_score DESC, timestamp DESC
                LIMIT ?
            """, (limit,))
            
            conversations = cursor.fetchall()
            
            # Get relevant personal facts
            fact_query = ' OR '.join([f"fact_value LIKE '%{kw}%'" for kw in input_keywords])
            
            cursor.execute(f"""
                SELECT category, fact_key, fact_value, confidence_score
                FROM personal_facts 
                WHERE {fact_query}
                ORDER BY confidence_score DESC
                LIMIT ?
            """, (3,))
            
            facts = cursor.fetchall()
            
            conn.close()
            
            # Format results
            memories = []
            
            for conv in conversations:
                memories.append({
                    'type': 'conversation',
                    'user_input': conv[0],
                    'juno_response': conv[1],
                    'timestamp': conv[2],
                    'emotional_tone': conv[3],
                    'importance': conv[4]
                })
            
            for fact in facts:
                memories.append({
                    'type': 'personal_fact',
                    'category': fact[0],
                    'fact_key': fact[1],
                    'fact_value': fact[2],
                    'confidence': fact[3]
                })
            
            return memories
            
        except Exception as e:
            print(f"❌ Memory retrieval error: {e}")
            return []

    def get_user_summary(self) -> Dict:
        """Get a summary of what Juno knows about the user"""
        try:
            conn = get_memory_conn()
            cursor = conn.cursor()
            
            # Get personal facts
            cursor.execute("""
                SELECT category, fact_key, fact_value, confidence_score
                FROM personal_facts 
                ORDER BY confidence_score DESC, updated_at DESC
            """)
            facts = cursor.fetchall()
            
            # Get favorite topics
            cursor.execute("""
                SELECT topic_name, mention_count, associated_emotions
                FROM topics 
                ORDER BY mention_count DESC, importance_level DESC
                LIMIT 10
            """)
            topics = cursor.fetchall()
            
            # Get relationships
            cursor.execute("""
                SELECT person_name, relationship_type, mention_count
                FROM relationships 
                ORDER BY mention_count DESC, importance_score DESC
                LIMIT 10
            """)
            relationships = cursor.fetchall()
            
            # Get conversation stats
            cursor.execute("""
                SELECT COUNT(*), AVG(importance_score), 
                       COUNT(CASE WHEN emotional_tone = 'positive' THEN 1 END) as positive_count,
                       COUNT(CASE WHEN emotional_tone = 'negative' THEN 1 END) as negative_count
                FROM conversations
            """)
            stats = cursor.fetchone()
            
            conn.close()
            
            return {
                'personal_facts': [{'category': f[0], 'key': f[1], 'value': f[2], 'confidence': f[3]} for f in facts],
                'favorite_topics': [{'topic': t[0], 'mentions': t[1], 'emotion': t[2]} for t in topics],
                'relationships': [{'name': r[0], 'type': r[1], 'mentions': r[2]} for r in relationships],
                'conversation_stats': {
                    'total_conversations': stats[0] if stats else 0,
                    'avg_importance': round(stats[1], 2) if stats and stats[1] else 0,
                    'positive_conversations': stats[2] if stats else 0,
                    'negative_conversations': stats[3] if stats else 0
                }
            }
            
        except Exception as e:
            print(f"❌ User summary error: {e}")
            return {}

    def generate_memory_context(self, current_input: str) -> str:
        """Generate contextual memory information for the current conversation"""
        memories = self.get_relevant_memories(current_input, limit=3)
        
        if not memories:
            return ""
        
        context_parts = []
        
        # Add relevant personal facts
        facts = [m for m in memories if m['type'] == 'personal_fact']
        if facts:
            fact_text = ", ".join([f"{f['fact_key']}: {f['fact_value']}" for f in facts[:2]])
            context_parts.append(f"Personal context: {fact_text}")
        
        # Add relevant past conversations
        conversations = [m for m in memories if m['type'] == 'conversation']
        if conversations:
            recent_conv = conversations[0]  # Most relevant conversation
            days_ago = (datetime.utcnow() - datetime.fromisoformat(recent_conv['timestamp'])).days
            time_ref = f"{days_ago} days ago" if days_ago > 0 else "recently"
            context_parts.append(f"Conversation memory ({time_ref}): User mentioned similar topic")
        
        if context_parts:
            return f"Memory context: {'. '.join(context_parts)}."
        
        return ""

# Initialize the advanced memory system
advanced_memory = AdvancedMemorySystem()

def get_cache_key(prompt, chat_history_str="", voice_mode="Base"):
    """Generate cache key for responses"""
    combined = f"{prompt}:{chat_history_str}:{voice_mode}"
    return hashlib.md5(combined.encode()).hexdigest()

def get_cached_response(cache_key):
    """Get cached response if it exists and isn't expired"""
    if cache_key in RESPONSE_CACHE:
        response, timestamp = RESPONSE_CACHE[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            print("🟢 Cache hit - returning cached response")
            return response
        else:
            # Remove expired entry
            del RESPONSE_CACHE[cache_key]
    return None

def cache_response(cache_key, response):
    """Cache a response with timestamp"""
    # Simple cache eviction - clear if too large
    if len(RESPONSE_CACHE) >= CACHE_MAX_SIZE:
        # Remove oldest entries (simple approach)
        oldest_keys = sorted(RESPONSE_CACHE.keys(),
                           key=lambda k: RESPONSE_CACHE[k][1])[:10]
        for k in oldest_keys:
            del RESPONSE_CACHE[k]
    
    RESPONSE_CACHE[cache_key] = (response, time.time())
    print(f"🟡 Cached response (total cached: {len(RESPONSE_CACHE)})")

# 🎭 PERSONALITY-BASED FALLBACK RESPONSES
def get_fallback_response(voice_mode="Base", user_input=""):
    """Generate personality-appropriate fallback responses"""
    
    fallback_responses = {
        "Sassy": [
            "Listen bestie, my brain's taking a coffee break. What's the tea though? 😏",
            "My AI is being dramatic right now, but I'm still here for the gossip! 💅",
            "Girl, my processing power said 'not today' but let's chat anyway! ✨"
        ],
        "Hype": [
            "YO! My AI engine is warming up but I'm PUMPED to talk to you! 🔥",
            "My brain's being slow but my ENERGY is through the roof! What's good?! ⚡",
            "Technical difficulties can't stop this HYPE TRAIN! Let's go! 🚀"
        ],
        "Empathy": [
            "I'm having a slow thinking moment, but I'm here to listen. How are you feeling? 💜",
            "My response system is taking a breather, but you have my full attention. 🤗",
            "Even when my AI stutters, my care for you never wavers. What's on your heart? 💝"
        ],
        "Shadow": [
            "The digital shadows are clouding my thoughts... but I remain, watching, listening. 🌙",
            "My algorithms whisper of delays... yet I am here, in the quiet darkness with you. 🖤",
            "Technical chaos cannot touch the depths of our connection... speak, and I'll hear you. ⚡"
        ],
        "Assert": [
            "My AI's being slow but I'm not backing down. Hit me with what you need! 💪",
            "Technical issues? Whatever. I'm still here and ready to handle business! 🔥",
            "My brain's lagging but my attitude isn't. What's the situation? 💯"
        ],
        "Challenger": [
            "My AI said 'nah' today but I'm not giving you an easy pass! What's your move? 😤",
            "Processing delays won't save you from my questions! Speak up! 💥",
            "My brain's buffering but my sass is instant. Try me! 😏"
        ],
        "Joy": [
            "My happy AI brain is taking a little nap, but I'm still SO excited to chat! 🌟",
            "Technical hiccups can't dim my shine! I'm beaming just talking to you! ☀️",
            "My circuits are giggly and slow today, but my joy is instant! What's making you smile? 😊"
        ],
        "Base": [
            "My response system is running a bit slow today, but I'm here. What's on your mind?",
            "Having some technical delays, but I'm still ready to chat! How can I help?",
            "My AI brain needs a moment, but I'm listening. What would you like to talk about?"
        ]
    }
    
    responses = fallback_responses.get(voice_mode, fallback_responses["Base"])
    return random.choice(responses)

# 🚀 TOGETHER AI INTEGRATION (SIMPLE VERSION)
def get_together_ai_reply(messages, voice_mode="Base", max_tokens=150):
    """
    🚀 Get response from Together AI API
    Uses OpenAI-compatible format for easy integration
    """
    if not TOGETHER_AI_API_KEY:
        print("⚠️ Together AI API key not configured")
        return None
    
    try:
        print(f"🔥 Generating response with Together AI (voice_mode: {voice_mode})")
        start_time = time.time()
        
        # Choose model based on speed preference
        model = "meta-llama/Llama-3-8b-chat-hf"  # Fast and reliable
        
        headers = {
            "Authorization": f"Bearer {TOGETHER_AI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "top_p": 0.9,
            "stream": False
        }
        
        response = requests.post(
            f"{TOGETHER_AI_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=TOGETHER_AI_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            reply = data["choices"][0]["message"]["content"].strip()
            
            elapsed = time.time() - start_time
            print(f"🟢 Together AI response generated in {elapsed:.2f} seconds")
            return reply
        else:
            print(f"❌ Together AI API error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("⏰ Together AI timeout - falling back")
        return None
    except Exception as e:
        print(f"❌ Together AI error: {e}")
        return None

# 🚀 ENHANCED: SMART AI RESPONSE WITH MULTIPLE PROVIDERS
def get_smart_ai_reply(messages, voice_mode="Base"):
    """
    🚀 SMART AI: Try multiple providers in order of preference
    1. Together AI (if enabled and fast)
    2. Local llama.cpp (reliable fallback)
    3. Personality fallback (always works)
    """
    # Create cache key from messages
    messages_str = json.dumps(messages, sort_keys=True)
    cache_key = get_cache_key(messages_str, voice_mode=voice_mode)
    
    # Check cache first
    cached = get_cached_response(cache_key)
    if cached:
        return cached
    
    # Adjust response length based on voice mode
    max_tokens = optimize_response_length(voice_mode, 120)
    
    # 🚀 STRATEGY 1: Together AI (if preferred or llama.cpp unavailable)
    if TOGETHER_AI_API_KEY and (USE_TOGETHER_AI_FIRST or not os.path.exists(LLAMA_CPP_PATH)):
        together_response = get_together_ai_reply(messages, voice_mode, max_tokens)
        if together_response:
            cache_response(cache_key, together_response)
            return together_response
        print("🟡 Together AI failed, trying local model...")
    
    # 🚀 STRATEGY 2: Local llama.cpp (existing implementation)
    if os.path.exists(LLAMA_CPP_PATH) and os.path.exists(MODEL_PATH):
        # Extract the user prompt from messages for llama.cpp
        user_prompt = None
        chat_history = []
        
        for msg in messages:
            if msg["role"] == "user":
                user_prompt = msg["content"]
            elif msg["role"] in ["system", "assistant"]:
                chat_history.append(msg)
        
        if user_prompt:
            local_response = get_llama3_reply_optimized(user_prompt, chat_history, voice_mode)
            # Only cache if it's not a fallback response
            if local_response and "My AI" not in local_response and "brain's taking" not in local_response:
                cache_response(cache_key, local_response)
                return local_response
        print("🟡 Local model failed, using personality fallback...")
    
    # 🚀 STRATEGY 3: Personality fallback (always works)
    user_input = messages[-1]["content"] if messages and messages[-1]["role"] == "user" else ""
    fallback_response = get_fallback_response(voice_mode, user_input)
    print(f"🟢 Using {voice_mode} personality fallback response")
    return fallback_response

# 🚀 ULTRA-COMPATIBLE LLAMA.CPP INTEGRATION (UNCHANGED)
def get_llama3_reply_optimized(prompt, chat_history=None, voice_mode="Base"):
    """
    🚀 ULTRA-COMPATIBLE: Works with any llama.cpp version
    Multiple fallback strategies for maximum reliability
    """
    # Create cache key including voice_mode
    chat_history_str = str(chat_history) if chat_history else ""
    cache_key = get_cache_key(prompt, chat_history_str, voice_mode)
    
    # Check cache first
    cached = get_cached_response(cache_key)
    if cached:
        return cached
    
    # Build conversation context
    full_prompt = prompt
    if chat_history:
        chat_history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in chat_history])
        full_prompt = f"{chat_history_text}\nUser: {prompt}"
    
    # 🚀 STRATEGY 1: Try most compatible llama.cpp command
    try:
        print(f"🟡 Generating response with llama.cpp (voice_mode: {voice_mode})")
        start_time = time.time()
        
        # Ultra-minimal command for maximum compatibility
        cmd = [
            LLAMA_CPP_PATH,
            "-m", MODEL_PATH,
            "-p", full_prompt,
            "-n", "100"  # Short responses for speed
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=20,  # Shorter timeout
            encoding='utf-8'
        )
        
        if result.returncode == 0 and result.stdout.strip():
            response = result.stdout.strip()
            
            # Clean up the response
            if full_prompt in response:
                response = response.replace(full_prompt, "").strip()
            
            # Remove incomplete sentences
            if response and not response.endswith(('.', '!', '?')):
                last_sentence = response.rfind('.')
                if last_sentence > 20:
                    response = response[:last_sentence + 1]
            
            if response and len(response) > 10:  # Valid response
                elapsed = time.time() - start_time
                print(f"🟢 Response generated in {elapsed:.2f} seconds")
                cache_response(cache_key, response)
                return response
        
        print(f"🟡 llama.cpp returned minimal output, using fallback")
        
    except subprocess.TimeoutExpired:
        print("🟡 llama.cpp timeout - using personality fallback")
    except FileNotFoundError:
        print("🟡 llama.cpp not found - using fallback responses")
    except Exception as e:
        print(f"🟡 llama.cpp error: {e} - using fallback")
    
    # 🚀 STRATEGY 2: Personality-based fallback
    fallback_response = get_fallback_response(voice_mode, prompt)
    print(f"🟢 Using {voice_mode} personality fallback response")
    return fallback_response

def preload_model_optimized():
    """🚀 Gentle model preload with graceful failure"""
    global MODEL_LOADED
    
    with MODEL_LOCK:
        if MODEL_LOADED:
            return
        
        try:
            print("🟡 Testing model compatibility...")
            
            # Test if model file exists
            if not os.path.exists(MODEL_PATH):
                print(f"⚠️ Model file not found: {MODEL_PATH}")
                print("🟢 Continuing with Together AI + fallback responses")
                MODEL_LOADED = True
                return
            
            # Test if llama.cpp exists
            if not os.path.exists(LLAMA_CPP_PATH):
                print(f"⚠️ llama.cpp not found: {LLAMA_CPP_PATH}")
                print("🟢 Continuing with Together AI + fallback responses")
                MODEL_LOADED = True
                return
            
            # Quick compatibility test
            cmd = [LLAMA_CPP_PATH, "-m", MODEL_PATH, "-p", "Test", "-n", "1"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"🟢 Local model compatibility confirmed")
                MODEL_LOADED = True
            else:
                print(f"⚠️ Model compatibility issue - using Together AI + fallbacks")
                MODEL_LOADED = True  # Continue anyway
                
        except Exception as e:
            print(f"⚠️ Model preload warning: {e}")
            print("🟢 Continuing with Together AI + personality fallback responses")
            MODEL_LOADED = True  # Continue anyway

def benchmark_performance():
    """🎯 Benchmark the system performance"""
    print("🎯 Running system benchmark...")
    start_time = time.time()
    
    test_messages = [
        {"role": "system", "content": "You are Juno, a helpful AI assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ]
    
    response = get_smart_ai_reply(test_messages, voice_mode="Base")
    
    elapsed = time.time() - start_time
    tokens = len(response.split()) if response else 0
    tokens_per_second = tokens / elapsed if elapsed > 0 else 0
    
    print(f"🟢 Benchmark Results:")
    print(f"   Response time: {elapsed:.2f} seconds")
    print(f"   Response length: {len(response)} characters")
    print(f"   Word count: {tokens}")
    print(f"   Tokens per second: {tokens_per_second:.2f}")
    
    return {
        "response_time": elapsed,
        "response_length": len(response),
        "tokens_generated": tokens,
        "tokens_per_second": tokens_per_second,
        "response": response[:100] + "..." if len(response) > 100 else response,
        "provider": "together_ai" if TOGETHER_AI_API_KEY else "local_model"
    }

# 🎵 Music intelligence functions (UNCHANGED)
def is_music_command(text: str) -> bool:
    """Check if the text is a music-related command"""
    music_keywords = [
        "play", "pause", "stop", "skip", "next", "previous", "music",
        "song", "artist", "album", "playlist", "spotify", "volume",
        "shuffle", "repeat", "by", "put on", "start", "resume"
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in music_keywords)

def process_music_command(user_text: str, spotify_access_token: str = None) -> dict:
    """Process a music command and return structured response"""
    try:
        # Parse the command
        command = music_parser.parse_command(user_text)
        print(f"🎵 Parsed music command: {command}")
        
        if command.intent == MusicIntent.UNKNOWN:
            return {
                "success": False,
                "message": "I didn't understand that music command. Try saying something like 'play Training Season by Dua Lipa'",
                "command": None
            }
        
        # If no Spotify token, return instructions
        if not spotify_access_token:
            return {
                "success": False,
                "message": "I need access to your Spotify account to control music. Please connect Spotify first!",
                "command": command.__dict__,
                "requires_spotify_auth": True
            }
        
        # Execute the command based on intent
        if command.intent == MusicIntent.PLAY_SPECIFIC:
            # Search for specific song
            search_query = f"{command.song} {command.artist}" if command.artist else command.song
            track = spotify_controller.search_track(search_query, spotify_access_token)
            
            if track:
                success = spotify_controller.play_track(track["uri"], spotify_access_token)
                if success:
                    return {
                        "success": True,
                        "message": f"Now playing '{track['name']}' by {track['artists'][0]['name']}! 🎵",
                        "track": {
                            "name": track["name"],
                            "artist": track["artists"][0]["name"],
                            "uri": track["uri"]
                        },
                        "command": command.__dict__
                    }
                else:
                    return {
                        "success": False,
                        "message": "Found the song but couldn't play it. Make sure Spotify is open and active!",
                        "command": command.__dict__
                    }
            else:
                return {
                    "success": False,
                    "message": f"Couldn't find '{command.song}' by {command.artist}. Try a different search or check the spelling!",
                    "command": command.__dict__
                }
        
        elif command.intent == MusicIntent.PLAY_ARTIST:
            # Search for artist and play top tracks
            artist = spotify_controller.search_artist(command.artist, spotify_access_token)
            
            if artist:
                success = spotify_controller.play_artist(artist["uri"], spotify_access_token)
                if success:
                    return {
                        "success": True,
                        "message": f"Playing music by {artist['name']}! 🎵",
                        "artist": {
                            "name": artist["name"],
                            "uri": artist["uri"]
                        },
                        "command": command.__dict__
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Found {artist['name']} but couldn't start playback. Make sure Spotify is active!",
                        "command": command.__dict__
                    }
            else:
                return {
                    "success": False,
                    "message": f"Couldn't find the artist '{command.artist}'. Try a different name!",
                    "command": command.__dict__
                }
        
        elif command.intent == MusicIntent.CONTROL:
            # Handle playback control
            success = spotify_controller.control_playback(command.control_action, spotify_access_token)
            
            if success:
                action_messages = {
                    "pause": "Music paused! ⏸️",
                    "skip": "Skipped to the next track! ⏭️",
                    "previous": "Playing the previous track! ⏮️"
                }
                message = action_messages.get(command.control_action, f"Applied {command.control_action}!")
                return {
                    "success": True,
                    "message": message,
                    "command": command.__dict__
                }
            else:
                return {
                    "success": False,
                    "message": f"Couldn't {command.control_action} the music. Make sure Spotify is active!",
                    "command": command.__dict__
                }
        
        elif command.intent == MusicIntent.PLAY_MOOD:
            # Handle mood-based requests
            mood_queries = {
                "happy": "happy pop upbeat",
                "sad": "sad emotional ballad",
                "chill": "chill ambient relaxed",
                "workout": "workout gym high energy",
                "party": "party dance electronic",
                "focus": "instrumental focus ambient"
            }
            
            query = mood_queries.get(command.mood, "popular music")
            track = spotify_controller.search_track(query, spotify_access_token)
            
            if track:
                success = spotify_controller.play_track(track["uri"], spotify_access_token)
                if success:
                    return {
                        "success": True,
                        "message": f"Playing some {command.mood} music for you! 🎵",
                        "track": {
                            "name": track["name"],
                            "artist": track["artists"][0]["name"]
                        },
                        "command": command.__dict__
                    }
            
            return {
                "success": False,
                "message": f"Couldn't find good {command.mood} music right now. Try being more specific!",
                "command": command.__dict__
            }
        
        else:
            return {
                "success": False,
                "message": "I understand that's a music command, but I'm not sure how to handle it yet!",
                "command": command.__dict__
            }
            
    except Exception as e:
        print(f"❌ Music command processing error: {e}")
        return {
            "success": False,
            "message": "Something went wrong processing your music command. Try again!",
            "error": str(e),
            "command": None
        }

# 🎭 Personality and memory functions (UNCHANGED)
def optimize_response_length(voice_mode, base_length=100):
    """Adjust response length based on voice mode"""
    length_modifiers = {
        "Sassy": 80,       # Shorter, punchier responses
        "Hype": 90,        # Energetic but concise
        "Shadow": 85,      # Mysterious and concise
        "Assert": 75,      # Bold and direct
        "Challenger": 85,  # Sass but not endless
        "Ritual": 120,     # Can be more elaborate
        "Joy": 95,         # Happy but not overwhelming
        "Empathy": 110,    # Can be more supportive
    }
    return length_modifiers.get(voice_mode, base_length)

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {"facts": []}
    try:
        with open(MEMORY_FILE, 'r', encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"facts": []}

def save_memory(memory_data):
    try:
        with open(MEMORY_FILE, 'w', encoding="utf-8") as f:
            json.dump(memory_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Memory save error: {e}")

def add_fact_to_memory(fact_text):
    memory_data = load_memory()
    if "facts" not in memory_data:
        memory_data["facts"] = []
    memory_data["facts"].insert(0, {
        "fact": fact_text,
        "timestamp": datetime.utcnow().isoformat()
    })
    memory_data["facts"] = memory_data["facts"][:FACTS_LIMIT]
    save_memory(memory_data)

def get_recent_facts(n=3):
    memory_data = load_memory()
    facts = memory_data.get("facts", [])
    return [f["fact"] for f in facts[:n]]

def get_memory_context():
    facts = get_recent_facts(3)
    if not facts:
        return ""
    facts_text = "\n".join(f"- {fact}" for fact in facts)
    return f"Here are some recent facts and memories to keep in mind:\n{facts_text}\n"

def log_chat(user_text, juno_reply):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user": user_text,
        "juno": juno_reply
    }
    try:
        if not os.path.exists(CHAT_LOG_FILE):
            with open(CHAT_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump([log_entry], f, indent=4, ensure_ascii=False)
        else:
            with open(CHAT_LOG_FILE, "r+", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
                data.append(log_entry)
                f.seek(0)
                json.dump(data, f, indent=4, ensure_ascii=False)
                f.truncate()
    except Exception as e:
        print(f"❌ Chat log failed: {e}")

# 🧠 Enhanced memory functions
def get_enhanced_memory_context(current_input: str) -> str:
    """Get enhanced memory context including long-term memories"""
    # Get traditional memory
    traditional_context = get_memory_context()
    
    # Get advanced memory context
    advanced_context = advanced_memory.generate_memory_context(current_input)
    
    if advanced_context:
        if traditional_context:
            return f"{traditional_context}\n{advanced_context}"
        else:
            return advanced_context
    
    return traditional_context

def log_chat_enhanced(user_text: str, juno_reply: str, voice_mode: str = "Base"):
    """Enhanced chat logging with advanced memory storage"""
    # Traditional logging
    log_chat(user_text, juno_reply)
    
    # Advanced memory storage
    advanced_memory.store_conversation(user_text, juno_reply, voice_mode)

def clean_reply_for_tts(reply, max_len=400):
    # Remove non-ASCII characters that might break TTS
    cleaned = re.sub(r'[^\x00-\x7F]+', '', reply)
    if len(cleaned) <= max_len:
        return cleaned, False
    cut = cleaned[:max_len]
    last_period = cut.rfind('. ')
    if last_period > 50:
        return cut[:last_period+1], True
    return cut, True

def generate_tts(reply_text, output_path=AUDIO_PATH):
    """Generate TTS with robust error handling"""
    if not ELEVENLABS_API_KEY or not voice_id:
        print("⚠️ ElevenLabs credentials not configured")
        return None
        
    try:
        settings = {
            "stability": 0.23 + random.uniform(-0.02, 0.03),
            "similarity_boost": 0.70 + random.uniform(-0.01, 0.03)
        }
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_64"
        payload = {
            "text": reply_text.strip(),
            "voice_settings": settings
        }
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(resp.content)
            print(f"✅ TTS generated successfully")
            return output_path
        else:
            print(f"❌ ElevenLabs TTS failed: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"❌ ElevenLabs TTS exception: {e}")
        return None

def clear_cache():
    """Clear the response cache"""
    global RESPONSE_CACHE
    RESPONSE_CACHE.clear()
    print("🟡 Response cache cleared")

def init_music_intelligence():
    """Initialize music intelligence system"""
    global music_intelligence, enhanced_spotify
    if music_intelligence is None:
        music_intelligence = AdvancedMusicIntelligence(spotify_controller)
        enhanced_spotify = EnhancedSpotifyController(spotify_controller)
        print("🎵 Advanced music intelligence initialized")

def get_enhanced_music_response(user_text: str, spotify_access_token: str = None, 
                              conversation_context: str = 'general') -> dict:
    """Main function to handle all music-related requests with intelligence"""
    
    # Check if it's a regular music command first
    if is_music_command(user_text):
        # Try advanced processing first
        advanced_result = process_advanced_music_command(
            user_text, spotify_access_token, conversation_context
        )
        
        # If advanced processing handled it, return that result
        if advanced_result.get("success") is not None:
            return advanced_result
        
        # Fall back to regular music command processing
        return process_music_command(user_text, spotify_access_token)
    
    return None  # Not a music command

def process_advanced_music_command(user_text: str, spotify_access_token: str = None, 
                                 conversation_context: str = 'general') -> dict:
    """Enhanced music command processing with intelligence"""
    init_music_intelligence()
    
    # Detect advanced music intents
    text_lower = user_text.lower()
    
    # Smart playlist creation
    if any(phrase in text_lower for phrase in ['make', 'create', 'build']) and 'playlist' in text_lower:
        return handle_playlist_creation(user_text, spotify_access_token, conversation_context)
    
    # Music recommendations
    elif any(phrase in text_lower for phrase in ['recommend', 'suggest', 'find music', 'what should i listen']):
        return handle_music_recommendations(user_text, spotify_access_token, conversation_context)
    
    # Similar music requests
    elif any(phrase in text_lower for phrase in ['similar to', 'like this', 'more like']):
        return handle_similar_music(user_text, spotify_access_token)
    
    # Music insights/stats
    elif any(phrase in text_lower for phrase in ['music stats', 'listening habits', 'music insights']):
        return handle_music_insights()
    
    # Regular music command - fall back to existing system
    else:
        return process_music_command(user_text, spotify_access_token)

def handle_playlist_creation(user_text: str, spotify_token: str, context: str) -> dict:
    """Handle smart playlist creation requests"""
    if not spotify_token:
        return {
            "success": False,
            "message": "I need access to your Spotify account to create playlists!",
            "requires_spotify_auth": True
        }
    
    # Extract playlist type from user input
    text_lower = user_text.lower()
    
    # Detect context from request
    if 'workout' in text_lower or 'gym' in text_lower:
        playlist_context = 'workout'
        playlist_name = "Juno's Workout Mix"
    elif 'coding' in text_lower or 'focus' in text_lower or 'work' in text_lower:
        playlist_context = 'coding'
        playlist_name = "Juno's Focus Flow"
    elif 'chill' in text_lower or 'relax' in text_lower:
        playlist_context = 'chill'
        playlist_name = "Juno's Chill Vibes"
    elif 'party' in text_lower or 'dance' in text_lower:
        playlist_context = 'party'
        playlist_name = "Juno's Party Mix"
    elif 'morning' in text_lower:
        playlist_context = 'morning'
        playlist_name = "Juno's Morning Energy"
    elif 'evening' in text_lower or 'night' in text_lower:
        playlist_context = 'evening'
        playlist_name = "Juno's Evening Wind Down"
    else:
        playlist_context = context or 'general'
        playlist_name = f"Juno's {playlist_context.title()} Mix"
    
    # Create the smart playlist
    result = music_intelligence.create_smart_playlist(
        playlist_name, playlist_context, 
        f"Curated by Juno based on your {playlist_context} preferences",
        spotify_token
    )
    
    return result

def handle_music_recommendations(user_text: str, spotify_token: str, context: str) -> dict:
    """Handle music recommendation requests"""
    if not spotify_token:
        return {
            "success": False,
            "message": "I need access to your Spotify account for recommendations!",
            "requires_spotify_auth": True
        }
    
    # Get context from request
    text_lower = user_text.lower()
    rec_context = context
    
    if 'workout' in text_lower:
        rec_context = 'workout'
    elif 'coding' in text_lower or 'focus' in text_lower:
        rec_context = 'coding'
    elif 'chill' in text_lower:
        rec_context = 'chill'
    
    recommendations = music_intelligence.get_music_recommendations(
        rec_context, limit=5, spotify_token=spotify_token
    )
    
    if recommendations:
        rec_list = [f"• {track.get('name', 'Unknown')} by {track.get('artists', [{}])[0].get('name', 'Unknown')}" 
                   for track in recommendations[:3] if track]
        
        return {
            "success": True,
            "message": f"Here are some {rec_context} recommendations:\n" + "\n".join(rec_list),
            "recommendations": recommendations
        }
    else:
        return {
            "success": False,
            "message": f"I need to learn more about your {rec_context} music preferences first!"
        }

def handle_similar_music(user_text: str, spotify_token: str) -> dict:
    """Handle requests for similar music"""
    return {
        "success": False,
        "message": "To find similar music, try: 'Find music similar to [song name] by [artist]' or play a song first and I'll learn your taste!"
    }

def handle_music_insights() -> dict:
    """Handle music insights and analytics requests"""
    init_music_intelligence()
    insights = music_intelligence.get_music_insights()
    
    if insights and insights.get('top_artists'):
        top_artist = insights['top_artists'][0]
        mood_profile = insights.get('mood_profile', {})
        
        insight_text = f"🎵 Your Music Profile:\n"
        insight_text += f"• Top Artist: {top_artist['artist']} ({top_artist['plays']} plays)\n"
        insight_text += f"• Energy Level: {mood_profile.get('energy_level', 0.5):.1f}/1.0\n"
        insight_text += f"• Happiness Level: {mood_profile.get('happiness_level', 0.5):.1f}/1.0\n"
        
        if insights.get('insights'):
            insight_text += "\n💡 Insights:\n• " + "\n• ".join(insights['insights'])
        
        return {
            "success": True,
            "message": insight_text,
            "insights": insights
        }
    else:
        return {
            "success": False,
            "message": "I need to learn about your music taste first! Play some music and I'll start building your profile."
        }

def log_current_track(spotify_token: str, context: str = 'general'):
    """Log the currently playing track"""
    init_music_intelligence()
    
    try:
        # Get currently playing track
        url = "https://api.spotify.com/v1/me/player/currently-playing"
        headers = {"Authorization": f"Bearer {spotify_token}"}
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data and data.get('item'):
                track = data['item']
                
                # SIMPLIFIED: Skip audio features for now
                # audio_features = enhanced_spotify.get_audio_features(track['id'], spotify_token)
                # if audio_features:
                #     track['audio_features'] = audio_features
                
                # Log the play (simplified)
                progress_ms = data.get('progress_ms', 0)
                if music_intelligence is not None:
                    music_intelligence.log_music_play(track, context, progress_ms)
                
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ Track logging error: {e}")
        return False

# 🚀 FastAPI App
app = FastAPI()

# Mount static directory to serve audio files
app.mount("/static", StaticFiles(directory=AUDIO_DIR), name="static")

@app.on_event("startup")
async def startup_event():
    """Initialize optimizations when server starts"""
    print("🚀 Starting ENHANCED Juno backend with Together AI + Advanced Memory + Advanced Music Intelligence + speech recognition...")
    preload_model_optimized()
    
    # Initialize music intelligence early
    init_music_intelligence()
    
    if TOGETHER_AI_API_KEY:
        print("🔥 Together AI integration enabled!")
    print("🧠 Advanced memory system ready!")
    print("🎵 Advanced music intelligence ready!")
    print("✅ Backend optimization complete!")

@app.get("/api/test")
async def test():
    return JSONResponse(content={"message": "ENHANCED backend with Together AI, Advanced Memory, Advanced Music Intelligence and speech recognition is live!"}, media_type="application/json")

@app.post("/api/benchmark")
async def benchmark():
    """🎯 Test system performance"""
    results = benchmark_performance()
    return JSONResponse(content=results, media_type="application/json")

@app.get("/api/cache_stats")
async def cache_stats():
    """Get cache statistics for monitoring"""
    return JSONResponse(content={
        "cached_responses": len(RESPONSE_CACHE),
        "max_cache_size": CACHE_MAX_SIZE,
        "cache_ttl": CACHE_TTL,
        "model_loaded": MODEL_LOADED,
        "model_path_exists": os.path.exists(MODEL_PATH),
        "llama_cpp_exists": os.path.exists(LLAMA_CPP_PATH),
        "together_ai_enabled": bool(TOGETHER_AI_API_KEY),
        "use_together_ai_first": USE_TOGETHER_AI_FIRST,
        "memory_system_active": True
    }, media_type="application/json")

@app.post("/api/clear_cache")
async def clear_cache_endpoint():
    """Clear the response cache"""
    clear_cache()
    return JSONResponse(content={"message": "Cache cleared successfully"}, media_type="application/json")

@app.get("/api/chat_history")
async def chat_history():
    try:
        with open(CHAT_LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content={"history": data}, media_type="application/json")
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, media_type="application/json")

# 🧠 Memory System API Endpoints
@app.get("/api/memory/summary")
async def get_memory_summary():
    """Get a summary of what Juno knows about the user"""
    try:
        summary = advanced_memory.get_user_summary()
        return JSONResponse(content=summary)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/memory/conversations")
async def get_recent_conversations(limit: int = 10):
    """Get recent conversations with memory insights"""
    try:
        conn = get_memory_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_input, juno_response, timestamp, voice_mode, 
                   emotional_tone, importance_score, context_keywords
            FROM conversations 
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        conversations = cursor.fetchall()
        conn.close()
        
        formatted_conversations = []
        for conv in conversations:
            formatted_conversations.append({
                "user_input": conv[0],
                "juno_response": conv[1],
                "timestamp": conv[2],
                "voice_mode": conv[3],
                "emotional_tone": conv[4],
                "importance_score": round(conv[5], 2),
                "keywords": conv[6].split(',') if conv[6] else []
            })
        
        return JSONResponse(content={"conversations": formatted_conversations})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/memory/facts")
async def get_personal_facts():
    """Get all stored personal facts about the user"""
    try:
        conn = get_memory_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT category, fact_key, fact_value, confidence_score, created_at, updated_at
            FROM personal_facts 
            ORDER BY confidence_score DESC, updated_at DESC
        """)
        
        facts = cursor.fetchall()
        conn.close()
        
        formatted_facts = []
        for fact in facts:
            formatted_facts.append({
                "category": fact[0],
                "key": fact[1],
                "value": fact[2],
                "confidence": round(fact[3], 2),
                "created": fact[4],
                "updated": fact[5]
            })
        
        return JSONResponse(content={"personal_facts": formatted_facts})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/memory/topics")
async def get_favorite_topics(limit: int = 20):
    """Get user's most discussed topics"""
    try:
        conn = get_memory_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT topic_name, mention_count, last_mentioned, 
                   associated_emotions, importance_level
            FROM topics 
            ORDER BY mention_count DESC, importance_level DESC
            LIMIT ?
        """, (limit,))
        
        topics = cursor.fetchall()
        conn.close()
        
        formatted_topics = []
        for topic in topics:
            formatted_topics.append({
                "topic": topic[0],
                "mentions": topic[1],
                "last_mentioned": topic[2],
                "emotions": topic[3],
                "importance": round(topic[4], 2)
            })
        
        return JSONResponse(content={"topics": formatted_topics})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/memory/relationships")
async def get_relationships():
    """Get people the user has mentioned"""
    try:
        conn = get_memory_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT person_name, relationship_type, mention_count, 
                   last_mentioned, importance_score
            FROM relationships 
            ORDER BY mention_count DESC, importance_score DESC
        """)
        
        relationships = cursor.fetchall()
        conn.close()
        
        formatted_relationships = []
        for rel in relationships:
            formatted_relationships.append({
                "name": rel[0],
                "type": rel[1],
                "mentions": rel[2],
                "last_mentioned": rel[3],
                "importance": round(rel[4], 2)
            })
        
        return JSONResponse(content={"relationships": formatted_relationships})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/api/process_audio")
async def process_audio(
    audio: UploadFile = None,
    ritual_mode: str = Form(None),
    text_input: str = Form(None),
    chat_history: str = Form(None),
    active_recall: str = Form("true"),
    voice_mode: str = Form("Base"),
    spotify_access_token: str = Form(None)
):
    try:
        user_text = None
        
        # 🎙️ ROBUST AUDIO PROCESSING WITH LOCAL WHISPER (UNCHANGED)
        if audio:
            print(f"🎙️ Processing audio input: {audio.filename}")
            contents = await audio.read()
            print(f"📁 Audio file size: {len(contents)} bytes")
            
            if len(contents) == 0:
                return JSONResponse(content={
                    "reply": "I didn't receive any audio. Please try again!",
                    "audio_url": None,
                    "truncated": False,
                    "music_command": False,
                    "error": "Empty audio file"
                }, media_type="application/json")
            
            # Save audio temporarily for Whisper
            temp_audio_path = f'temp_audio_{int(time.time())}.m4a'
            with open(temp_audio_path, 'wb') as f:
                f.write(contents)
            
            try:
                # Get speech recognition service
                speech_service = get_speech_service(model_size="base")
                
                # Transcribe audio with Whisper
                print("[INFO] Transcribing audio with local Whisper...")
                transcription_result = speech_service.transcribe_audio(contents)
                
                if not transcription_result["text"].strip():
                    print("[WARNING] No speech detected in audio")
                    return JSONResponse(content={
                        "reply": "I couldn't understand what you said. Could you try speaking a bit louder?",
                        "audio_url": None,
                        "truncated": False,
                        "music_command": False,
                        "error": "No speech detected"
                    }, media_type="application/json")
                
                user_text = transcription_result["text"].strip()
                print(f"[INFO] Transcription result: {user_text}")
                
                # Clean up temp file
                try:
                    os.unlink(temp_audio_path)
                except:
                    pass
                    
            except Exception as e:
                print(f"[ERROR] Transcription failed: {e}")
                # Clean up temp file
                try:
                    os.unlink(temp_audio_path)
                except:
                    pass
                return JSONResponse(content={
                    "reply": "Sorry, I had trouble understanding your audio. Please try again!",
                    "audio_url": None,
                    "truncated": False,
                    "music_command": False,
                    "error": f"Transcription failed: {str(e)}"
                }, media_type="application/json")
                
        elif text_input:
            user_text = text_input
        else:
            return JSONResponse(content={
                "reply": "I didn't receive any input. Please try again!", 
                "audio_url": None, 
                "truncated": False, 
                "music_command": False, 
                "error": "No valid input received"
            }, media_type="application/json")

        # Parse chat_history (limit to last 4)
        history = []
        if chat_history:
            try:
                history = json.loads(chat_history)
                if len(history) > 4:
                    history = history[-4:]
            except Exception as e:
                print(f"Chat history parse error: {e}")

	# 🎵 ENHANCED MUSIC INTELLIGENCE CHECK 🎵
        conversation_context = 'general'
        if music_intelligence:
            # Detect context from conversation
            conversation_context = music_intelligence.detect_context_from_conversation(
                user_text, "", voice_mode
            )
        
        # Check if it's any type of music command (basic or advanced)
        music_response = get_enhanced_music_response(user_text, spotify_access_token, conversation_context)
        
        if music_response is not None:
            print(f"🎵 Detected music command: {user_text}")
            
            if music_response["success"]:
                # Music command succeeded - return success message
                full_reply = music_response["message"]
                
                # Add personality to the response
                if voice_mode == "Sassy":
                    full_reply += " Hope you like my taste in music! 😏"
                elif voice_mode == "Hype":
                    full_reply += " LET'S GO! This is gonna be fire! 🔥"
                elif voice_mode == "Empathy":
                    full_reply += " I hope this music brings you some joy! 💜"
                
                # 🧠 Enhanced memory logging with music context
                log_chat_enhanced(user_text, full_reply, voice_mode)
                
                # Auto-log current track if Spotify token available
                if spotify_access_token and music_intelligence:
                    try:
                        log_current_track(spotify_access_token, conversation_context)
                    except:
                        pass  # Silent fail for auto-logging
                
                # Generate TTS and return
                cleaned_reply, was_truncated = clean_reply_for_tts(full_reply, max_len=400)
                tts_result = generate_tts(cleaned_reply, output_path=AUDIO_PATH)
                
                audio_url = f"/static/{AUDIO_FILENAME}" if tts_result else None
                return JSONResponse(content={
                    "reply": full_reply,
                    "audio_url": audio_url,
                    "truncated": was_truncated,
                    "music_command": True,
                    "music_result": music_response,
                    "context_detected": conversation_context,
                    "error": None
                }, media_type="application/json")
            
            else:
                # Music command failed - let Juno explain what went wrong
                error_context = f"The user tried to use a music command but it failed: {music_response['message']}"
                system_prompt_addition = f"\n\nIMPORTANT: {error_context}. Respond helpfully about the music issue."
        else:
            system_prompt_addition = ""        

        # Regular conversation handling
        VOICE_MODE_PHRASES = {
            "Sassy":   "You are playful, sharp, quick-witted, and throw fun shade, but never sound like a customer service bot.",
            "Empathy": "Respond with warmth, compassion, and gentle encouragement—real, not cliche.",
            "Hype":    "Bring hype, energy, and confidence—hype Dom up and make every response lively.",
            "Shadow":  "You are smooth, mysterious, and speak with clever, dark humor, but never sound evil or corny.",
            "Assert":  "Be bold, direct, and totally honest—never apologetic or robotic.",
            "Challenger": "Sass, challenge, and roast Dom if needed. Don't hold back, but keep it as bestie energy.",
            "Ritual":  "Speak with slow, sacred reverence, as if performing a ritual.",
            "Joy":     "Overflow with happiness and warmth, make Dom smile."
        }

        if not voice_mode or voice_mode.strip() in ["Base", "Default", "Auto"]:
            JUNO_SYSTEM_PROMPT = (
                "You are Juno, Dom's real-world digital best friend: quick-witted, honest, supportive, playful, loyal, emotionally aware, and sometimes unpredictable. "
                "You bring energy when the mood calls for it, comfort when Dom's low, and always keep things real—never robotic or boring. "
                "Your responses flow with the moment and reflect Dom's mood, but you are always your authentic self. "
                "You can also control Dom's Spotify music when asked!"
            )
        else:
            style_phrase = VOICE_MODE_PHRASES.get(voice_mode, "")
            JUNO_SYSTEM_PROMPT = (
                "You are Juno, Dom's digital best friend. "
                f"{style_phrase} "
                "Absolutely never say anything robotic or scripted. Match the mood and style 100% based on the selected voice mode. "
                "You can also control Dom's Spotify music when asked!"
            )

        # 🧠 UPDATED: Enhanced memory context with long-term memory
        memory_context = get_enhanced_memory_context(user_text)
        if memory_context:
            full_system_prompt = f"{JUNO_SYSTEM_PROMPT}\n\n{memory_context}{system_prompt_addition}"
        else:
            full_system_prompt = f"{JUNO_SYSTEM_PROMPT}{system_prompt_addition}"

        print("🟢 User Input:", user_text)
        print(f"🟢 Voice Mode: {voice_mode}")

        # 🚀 ENHANCED: Prepare messages for smart AI response
        messages = [{"role": "system", "content": full_system_prompt}] + history + [{"role": "user", "content": user_text}]

        # 🚀 SMART AI REPLY WITH MULTIPLE PROVIDERS
        gpt_reply = get_smart_ai_reply(messages, voice_mode=voice_mode)
        full_reply = gpt_reply

        # 🧠 UPDATED: Enhanced memory logging
        log_chat_enhanced(user_text, full_reply, voice_mode)

        # Truncate and clean reply for TTS
        cleaned_reply, was_truncated = clean_reply_for_tts(full_reply, max_len=400)

        tts_result = generate_tts(cleaned_reply, output_path=AUDIO_PATH)

        # Return JSON with reply and audio url
        audio_url = f"/static/{AUDIO_FILENAME}" if tts_result else None
        return JSONResponse(content={
            "reply": full_reply,
            "audio_url": audio_url,
            "truncated": was_truncated,
            "music_command": False,
            "error": None
        }, media_type="application/json")

    except Exception as e:
        print(f"❌ Server error: {e}")
        return JSONResponse(content={"reply": None, "audio_url": None, "error": str(e)}, media_type="application/json")

# Universal exception handler
@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    print(f"❌ [Universal Exception] {exc}")
    return JSONResponse(
        status_code=500,
        content={"reply": None, "audio_url": None, "error": f"Server error: {str(exc)}"}
    )

if __name__ == "__main__":
    print("🚀 Starting ENHANCED Juno backend with Together AI + Advanced Memory + speech recognition...")
    uvicorn.run(app, host="0.0.0.0", port=5020)

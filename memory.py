import os
import sqlite3
import re
import hashlib
from datetime import datetime
from typing import List, Dict
import utf8_validation
import logging

logger = logging.getLogger(__name__)

MEMORY_DB_PATH = "juno_memory.db"

def get_memory_conn():
    conn = sqlite3.connect(MEMORY_DB_PATH, timeout=30)
    conn.execute('PRAGMA journal_mode=WAL;')
    # Ensure UTF-8 encoding for text storage
    conn.execute('PRAGMA encoding="UTF-8";')
    return conn

class AdvancedMemorySystem:
    def __init__(self):
        self.init_database()

    def init_database(self):
        conn = get_memory_conn()
        cursor = conn.cursor()
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personal_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                fact_key TEXT NOT NULL,
                fact_value TEXT NOT NULL,
                confidence_score REAL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source_conversation_id INTEGER
            )
        """)
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

    def extract_keywords(self, text: str) -> List[str]:
        common_words = {'i', 'me', 'my', 'you', 'your', 'the', 'a', 'an', 'and', 'or', 'but','in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was','were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will','would', 'could', 'should', 'can', 'may', 'might', 'this', 'that', 'these','those', 'what', 'when', 'where', 'why', 'how', 'juno', 'hey', 'hi', 'hello'}
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        keywords = [word for word in words if word not in common_words]
        return list(set(keywords))

    def detect_emotional_tone(self, text: str) -> str:
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

    def store_conversation(self, user_input: str, juno_response: str, voice_mode: str = "Base") -> int:
        try:
            # Sanitize all text inputs to ensure UTF-8 safety
            user_input = utf8_validation.sanitize_text(user_input)
            juno_response = utf8_validation.sanitize_text(juno_response)
            voice_mode = utf8_validation.sanitize_text(voice_mode)
            
            conn = get_memory_conn()
            cursor = conn.cursor()
            conv_text = f"{user_input}|{juno_response}"
            conv_hash = hashlib.md5(conv_text.encode('utf-8')).hexdigest()
            keywords = self.extract_keywords(user_input + " " + juno_response)
            emotional_tone = self.detect_emotional_tone(user_input)
            importance_score = min(2.0, (len(user_input) / 100) + len(keywords) * 0.1 + (1.5 if emotional_tone in ['positive', 'negative'] else 1.0))
            
            cursor.execute("""
                INSERT INTO conversations 
                (timestamp, user_input, juno_response, voice_mode, conversation_hash, context_keywords, emotional_tone, importance_score)
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
            conn.commit()
            conn.close()
            logger.info(f"Stored conversation {conversation_id} safely")
            return conversation_id
        except Exception as e:
            utf8_validation.log_encoding_issue("memory_store_conversation", locals(), e)
            logger.error(f"Memory storage error: {e}")
            return -1

    def get_user_summary(self) -> Dict:
        try:
            conn = get_memory_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT category, fact_key, fact_value, confidence_score FROM personal_facts ORDER BY confidence_score DESC, updated_at DESC")
            facts = cursor.fetchall()
            cursor.execute("SELECT topic_name, mention_count, associated_emotions FROM topics ORDER BY mention_count DESC, importance_level DESC LIMIT 10")
            topics = cursor.fetchall()
            cursor.execute("SELECT person_name, relationship_type, mention_count FROM relationships ORDER BY mention_count DESC, importance_score DESC LIMIT 10")
            relationships = cursor.fetchall()
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

    def get_recent_conversations(self, limit=10):
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
            return formatted_conversations
        except Exception as e:
            print(f"❌ Recent conversations error: {e}")
            return []
    
    def get_personal_facts(self):
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
            return formatted_facts
        except Exception as e:
            print(f"❌ Personal facts error: {e}")
            return []
    
    def get_favorite_topics(self, limit=20):
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
            return formatted_topics
        except Exception as e:
            print(f"❌ Topics error: {e}")
            return []
    
    def get_relationships(self):
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
            return formatted_relationships
        except Exception as e:
            print(f"❌ Relationships error: {e}")
            return []

# --- Instance for use in endpoints ---
_memory_sys = AdvancedMemorySystem()

# --- Functions for main.py endpoints ---

def store_memory(key, value):
    # This could be adapted to use personal facts or a generic store
    _memory_sys.store_conversation(key, value)

def retrieve_memory(key):
    # Not implemented for now
    return None

def get_memory_summary():
    return _memory_sys.get_user_summary()

def get_recent_conversations(limit=10):
    return _memory_sys.get_recent_conversations(limit)

def get_personal_facts():
    return _memory_sys.get_personal_facts()

def get_favorite_topics():
    return _memory_sys.get_favorite_topics()

def get_relationships():
    return _memory_sys.get_relationships()

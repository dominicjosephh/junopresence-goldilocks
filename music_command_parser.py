import re
import requests
from enum import Enum
from typing import Optional, Dict, Any
import urllib.parse

class MusicIntent(Enum):
    PLAY_SPECIFIC = "play_specific"
    PLAY_ARTIST = "play_artist"
    PLAY_MOOD = "play_mood"
    PLAY_GENRE = "play_genre"
    CONTROL = "control"
    UNKNOWN = "unknown"

class MusicCommand:
    def __init__(self):
        self.intent = MusicIntent.UNKNOWN
        self.song = None
        self.artist = None
        self.genre = None
        self.mood = None
        self.control_action = None
        self.confidence = 0.0
        self.raw_text = ""

class MusicCommandParser:
    def __init__(self):
        self.artists = [
            "dua lipa", "taylor swift", "drake", "billie eilish", "becky hill",
            "miley cyrus", "harry styles", "the weeknd", "ariana grande"
        ]
        
        self.songs = [
            "training season", "anti-hero", "flowers", "unholy", "as it was"
        ]
        
        self.control_words = {
            "pause": "pause",
            "stop": "pause",
            "skip": "next",
            "next": "next",
            "previous": "previous",
            "prev": "previous"
        }

    def parse_command(self, text: str) -> MusicCommand:
        command = MusicCommand()
        command.raw_text = text
        text_lower = text.lower().strip()
        
        # Control commands
        for word, action in self.control_words.items():
            if word in text_lower:
                command.intent = MusicIntent.CONTROL
                command.control_action = action
                command.confidence = 0.9
                return command
        
        # Play commands
        if "play" in text_lower:
            # Check for "by" pattern: "play [song] by [artist]"
            by_match = re.search(r"play\s+(.+?)\s+by\s+(.+)", text_lower)
            if by_match:
                command.intent = MusicIntent.PLAY_SPECIFIC
                command.song = by_match.group(1).strip()
                command.artist = by_match.group(2).strip()
                command.confidence = 0.95
                return command
            
            # Check for artist
            for artist in self.artists:
                if artist in text_lower:
                    command.intent = MusicIntent.PLAY_ARTIST
                    command.artist = artist
                    command.confidence = 0.8
                    return command
            
            # Check for specific song
            for song in self.songs:
                if song in text_lower:
                    command.intent = MusicIntent.PLAY_SPECIFIC
                    command.song = song
                    command.confidence = 0.7
                    return command
            
            # Generic play command
            play_match = re.search(r"play\s+(.+)", text_lower)
            if play_match:
                query = play_match.group(1).strip()
                command.intent = MusicIntent.PLAY_SPECIFIC
                command.song = query
                command.confidence = 0.6
                return command
        
        return command

class SpotifyController:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://api.spotify.com/v1"

    def search_track(self, query: str, access_token: str) -> Optional[Dict]:
        """Search for a track on Spotify"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            params = {
                "q": query,
                "type": "track",
                "limit": 1
            }
            
            response = requests.get(
                f"{self.base_url}/search",
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                tracks = data.get("tracks", {}).get("items", [])
                if tracks:
                    return tracks[0]
            
            return None
        except Exception as e:
            print(f"❌ Spotify track search error: {e}")
            return None

    def search_artist(self, artist_name: str, access_token: str) -> Optional[Dict]:
        """Search for an artist on Spotify"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            params = {
                "q": artist_name,
                "type": "artist",
                "limit": 1
            }
            
            response = requests.get(
                f"{self.base_url}/search",
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                artists = data.get("artists", {}).get("items", [])
                if artists:
                    return artists[0]
            
            return None
        except Exception as e:
            print(f"❌ Spotify artist search error: {e}")
            return None

    def play_track(self, track_uri: str, access_token: str) -> bool:
        """Play a specific track"""
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            data = {"uris": [track_uri]}
            
            response = requests.put(
                f"{self.base_url}/me/player/play",
                headers=headers,
                json=data,
                timeout=10
            )
            
            return response.status_code in [200, 202, 204]
        except Exception as e:
            print(f"❌ Spotify play track error: {e}")
            return False

    def play_artist(self, artist_uri: str, access_token: str) -> bool:
        """Play an artist's top tracks"""
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            data = {"context_uri": artist_uri}
            
            response = requests.put(
                f"{self.base_url}/me/player/play",
                headers=headers,
                json=data,
                timeout=10
            )
            
            return response.status_code in [200, 202, 204]
        except Exception as e:
            print(f"❌ Spotify play artist error: {e}")
            return False

    def control_playback(self, action: str, access_token: str) -> bool:
        """Control playback (pause, next, previous)"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            
            endpoint_map = {
                "pause": f"{self.base_url}/me/player/pause",
                "next": f"{self.base_url}/me/player/next",
                "previous": f"{self.base_url}/me/player/previous"
            }
            
            endpoint = endpoint_map.get(action)
            if not endpoint:
                return False
            
            if action == "pause":
                response = requests.put(endpoint, headers=headers, timeout=10)
            else:
                response = requests.post(endpoint, headers=headers, timeout=10)
            
            return response.status_code in [200, 202, 204]
        except Exception as e:
            print(f"❌ Spotify control playback error: {e}")
            return False

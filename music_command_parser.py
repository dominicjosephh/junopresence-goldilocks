from enum import Enum

class MusicIntent(Enum):
    CONTROL = "control"
    UNKNOWN = "unknown"

class MusicCommand:
    def __init__(self):
        self.raw_text = ""
        self.intent = MusicIntent.UNKNOWN
        self.control_action = None
        self.confidence = 0.0

class MusicCommandParser:
    def __init__(self):
        # Example control words dictionary
        self.control_words = {
            "play": "play",
            "pause": "pause",
            "stop": "stop"
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
        # Add more parsing logic as needed
        command.intent = MusicIntent.UNKNOWN
        command.confidence = 0.5
        return command

# --- TOP LEVEL FUNCTION FOR EASY IMPORT ---
def parse_music_command(text: str) -> MusicCommand:
    parser = MusicCommandParser()
    return parser.parse_command(text)

from music_command_parser import parse_music_command
from SpotifyController import SpotifyController

spotify = SpotifyController()

def handle_music_command(command: str):
    parsed = parse_music_command(command)
    # Example: parsed = {"action": "play", "track": "Muse"}
    if parsed["action"] == "play":
        return spotify.play(parsed["track"])
    elif parsed["action"] == "pause":
        return spotify.pause()
    # Add more as needed
    return "Unknown music command"

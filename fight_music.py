import random
import threading
import time
from pynput import mouse
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Spotify API Credentials (get these from https://developer.spotify.com/dashboard)
CLIENT_ID = "your_client_id_here"
CLIENT_SECRET = "your_client_secret_here"
REDIRECT_URI = "http://localhost:8888/callback"

# Configuration
FADE_IN_DURATION_SEC = 2.0  # Fade in duration in seconds (changeable)
FADE_OUT_DURATION_SEC = 3.0  # Fade out duration in seconds
FADE_STEPS = 20  # Number of volume steps during fade

# Songs list: each entry is (spotify_track_uri, start_timestamp_in_milliseconds)
# You can use Spotify URIs (spotify:track:xxx) or Spotify URLs
SONGS = [
    ("spotify:track:4cOdK2wGLETKBW3PvgPWqT", 30000),   # Rick Astley - Never Gonna Give You Up, starts at 30s
    ("spotify:track:7GhIk7Il098yCjg4BQjzvb", 45000),   # Example song, starts at 45s
    ("spotify:track:0VjIjW4GlUZAMYd2vXMi3b", 60000),   # Example song, starts at 60s
]

# State
music_playing = False
fade_thread = None
stopping = False
sp = None

def init_spotify():
    """Initialize Spotify client with OAuth"""
    global sp
    scope = "user-modify-playback-state user-read-playback-state"
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=scope
    ))
    print("Spotify authenticated successfully!")

def get_active_device():
    """Get the first active Spotify device"""
    devices = sp.devices()
    if devices['devices']:
        for device in devices['devices']:
            if device['is_active']:
                return device['id']
        # If no active device, return the first one
        return devices['devices'][0]['id']
    return None

def fade_in(duration_sec):
    """Gradually increase volume from 0 to 100"""
    global music_playing
    step_duration = duration_sec / FADE_STEPS
    for i in range(FADE_STEPS + 1):
        if not music_playing or stopping:
            break
        volume = int((i / FADE_STEPS) * 100)
        try:
            sp.volume(volume)
        except Exception:
            pass
        time.sleep(step_duration)

def fade_out(duration_sec):
    """Gradually decrease volume from current to 0, then pause"""
    global music_playing, stopping
    stopping = True

    try:
        current = sp.current_playback()
        current_volume = current['device']['volume_percent'] if current else 100
    except Exception:
        current_volume = 100

    step_duration = duration_sec / FADE_STEPS
    for i in range(FADE_STEPS + 1):
        volume = int(current_volume * (1 - i / FADE_STEPS))
        try:
            sp.volume(volume)
        except Exception:
            pass
        time.sleep(step_duration)

    try:
        sp.pause_playback()
    except Exception:
        pass

    music_playing = False
    stopping = False

def play_random_song():
    """Pick a random song and play it from its unique timestamp with fade in"""
    global music_playing, fade_thread

    device_id = get_active_device()
    if not device_id:
        print("No Spotify device found! Open Spotify and play something first.")
        return

    track_uri, start_ms = random.choice(SONGS)

    # Convert URL to URI if needed
    if "open.spotify.com" in track_uri:
        # Extract track ID from URL like https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT
        track_id = track_uri.split("/track/")[1].split("?")[0]
        track_uri = f"spotify:track:{track_id}"

    try:
        # Set volume to 0 before starting
        sp.volume(0, device_id=device_id)

        # Start playback at the specified position
        sp.start_playback(device_id=device_id, uris=[track_uri], position_ms=start_ms)
        music_playing = True

        # Start fade in on a separate thread
        fade_thread = threading.Thread(target=fade_in, args=(FADE_IN_DURATION_SEC,))
        fade_thread.start()

        # Get track name for display
        track_info = sp.track(track_uri)
        print(f"Playing: {track_info['name']} by {track_info['artists'][0]['name']} from {start_ms // 1000}s")
    except spotipy.exceptions.SpotifyException as e:
        print(f"Spotify error: {e}")
        music_playing = False
    except Exception as e:
        print(f"Error: {e}")
        music_playing = False

def stop_with_fade():
    """Stop the current song with fade out"""
    global fade_thread

    fade_thread = threading.Thread(target=fade_out, args=(FADE_OUT_DURATION_SEC,))
    fade_thread.start()
    print("Fading out...")

def on_click(x, y, button, pressed):
    """Handle mouse button clicks"""
    global music_playing

    # Mouse button 4 is typically Button.x1 (side button)
    if button == mouse.Button.x1 and pressed:
        if music_playing and not stopping:
            stop_with_fade()
        elif not music_playing and not stopping:
            play_random_song()

def main():
    init_spotify()
    print("\nFight Music Controller Started")
    print("Press Mouse Button 4 (side button) to play/stop music")
    print("Make sure Spotify is open and active!")
    print("Press Ctrl+C to exit\n")

    # Start listening for mouse events
    with mouse.Listener(on_click=on_click) as listener:
        listener.join()

if __name__ == "__main__":
    main()

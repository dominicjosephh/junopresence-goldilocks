#!/usr/bin/env python3
"""
Test to verify music intelligence initialization without external dependencies
"""
import sys
import os

# Mock the problematic modules before importing main
class MockWhisper:
    @staticmethod
    def load_model(model_size):
        return None

class MockSpeechService:
    @staticmethod
    def get_speech_service(model_size="base"):
        return MockSpeechService()
    
    def transcribe_audio(self, audio_data):
        return {"text": "test transcription"}

# Add mocks to sys.modules
sys.modules['whisper'] = MockWhisper()
sys.modules['speech_service'] = MockSpeechService()

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_music_intelligence_initialization():
    """Test that music intelligence can be initialized without errors"""
    print("🧪 Testing music intelligence initialization...")
    
    try:
        # Import after mocking
        from main import init_music_intelligence, enhanced_spotify, music_intelligence
        
        # Check initial state
        print(f"  Initial enhanced_spotify: {enhanced_spotify}")
        print(f"  Initial music_intelligence: {music_intelligence}")
        
        # Call init function
        init_music_intelligence()
        
        # Import again to get updated values
        from main import enhanced_spotify as updated_enhanced_spotify
        from main import music_intelligence as updated_music_intelligence
        
        print(f"  After init enhanced_spotify: {updated_enhanced_spotify}")
        print(f"  After init music_intelligence: {updated_music_intelligence}")
        
        # Check that enhanced_spotify is now available
        if updated_enhanced_spotify is not None and updated_music_intelligence is not None:
            print("✅ Music intelligence initialization test passed!")
            return True
        else:
            print("❌ Music intelligence objects are still None after initialization")
            return False
            
    except Exception as e:
        print(f"❌ Music intelligence initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enhanced_spotify_controller():
    """Test that EnhancedSpotifyController is properly defined"""
    print("🧪 Testing EnhancedSpotifyController class...")
    
    try:
        from main import EnhancedSpotifyController, SpotifyController
        
        # Create a mock spotify controller
        mock_spotify = SpotifyController("test_id", "test_secret")
        
        # Create EnhancedSpotifyController
        enhanced = EnhancedSpotifyController(mock_spotify)
        
        # Check that it has the expected methods
        assert hasattr(enhanced, 'get_audio_features'), "Missing get_audio_features method"
        assert hasattr(enhanced, 'spotify_controller'), "Missing spotify_controller attribute"
        
        print("✅ EnhancedSpotifyController class test passed!")
        return True
        
    except Exception as e:
        print(f"❌ EnhancedSpotifyController test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Testing Music Intelligence and EnhancedSpotifyController")
    print("=" * 60)
    
    try:
        # Run tests
        test1 = test_enhanced_spotify_controller()
        test2 = test_music_intelligence_initialization()
        
        if test1 and test2:
            print("\n🎉 All music intelligence tests passed!")
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
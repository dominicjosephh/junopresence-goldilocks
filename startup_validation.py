# Enhanced Startup Script with Validation
# Save this as: start_juno_phase2.py

import os
import sys
import time
import subprocess
import requests
import redis
import uvicorn
from pathlib import Path

def check_redis_connection():
    """Check if Redis is running and accessible"""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis connection successful")
        return True
    except redis.ConnectionError:
        print("❌ Redis connection failed")
        print("   Please start Redis:")
        print("   - Linux/Mac: redis-server")
        print("   - Windows: redis-server.exe")
        return False
    except Exception as e:
        print(f"⚠️ Redis check error: {e}")
        return False

def check_dependencies():
    """Check if all Phase 2 dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    required_packages = {
        'redis': 'Redis client',
        'librosa': 'Audio processing',
        'sklearn': 'Machine learning',
        'psutil': 'System monitoring',
        'numpy': 'Numerical computing',
        'scipy': 'Scientific computing'
    }
    
    missing_packages = []
    
    for package, description in required_packages.items():
        try:
            __import__(package)
            print(f"   ✅ {package} ({description})")
        except ImportError:
            print(f"   ❌ {package} ({description}) - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("   Run: pip install -r requirements_phase2.txt")
        return False
    
    print("✅ All dependencies installed")
    return True

def check_environment_variables():
    """Check if required environment variables are set"""
    print("🔧 Checking environment variables...")
    
    # Critical variables
    critical_vars = ['ELEVENLABS_API_KEY', 'ELEVENLABS_VOICE_ID']
    # Optional but recommended
    optional_vars = ['TOGETHER_AI_API_KEY', 'SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET']
    # Phase 2 specific
    phase2_vars = ['REDIS_HOST', 'REDIS_PORT', 'EMOTION_DETECTION_ENABLED']
    
    all_good = True
    
    for var in critical_vars:
        if os.getenv(var):
            print(f"   ✅ {var} is set")
        else:
            print(f"   ❌ {var} is missing (CRITICAL)")
            all_good = False
    
    for var in optional_vars:
        if os.getenv(var):
            print(f"   ✅ {var} is set")
        else:
            print(f"   ⚠️ {var} is missing (optional)")
    
    for var in phase2_vars:
        value = os.getenv(var, 'default')
        print(f"   ✅ {var}: {value}")
    
    return all_good

def validate_audio_processing():
    """Test audio processing capabilities"""
    print("🎙️ Validating audio processing...")
    
    try:
        import librosa
        import numpy as np
        
        # Create a test audio signal
        sample_rate = 22050
        duration = 1  # 1 second
        t = np.linspace(0, duration, int(sample_rate * duration))
        test_audio = 0.5 * np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
        
        # Test feature extraction
        mfccs = librosa.feature.mfcc(y=test_audio, sr=sample_rate, n_mfcc=13)
        spectral_centroid = librosa.feature.spectral_centroid(y=test_audio, sr=sample_rate)
        
        if mfccs.shape[0] == 13 and spectral_centroid.shape[0] == 1:
            print("   ✅ Audio feature extraction working")
            return True
        else:
            print("   ❌ Audio feature extraction failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Audio processing validation failed: {e}")
        return False

def start_server_with_validation():
    """Start the server and run validation tests"""
    print("🚀 Starting Enhanced Juno Server (Phase 2)")
    print("=" * 50)
    
    # Pre-flight checks
    deps_ok = check_dependencies()
    env_ok = check_environment_variables()
    redis_ok = check_redis_connection()
    audio_ok = validate_audio_processing()
    
    if not deps_ok:
        print("\n❌ Dependencies check failed. Please install missing packages.")
        sys.exit(1)
    
    if not env_ok:
        print("\n⚠️ Environment variables missing. Server may not work correctly.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    if not redis_ok:
        print("\n⚠️ Redis not available. Server will use local caching fallback.")
        response = input("Continue without Redis? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    if not audio_ok:
        print("\n⚠️ Audio processing validation failed. Emotion analysis may not work.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    print("\n🟢 Pre-flight checks completed")
    print("🚀 Starting server on http://localhost:5020")
    print("\nServer features enabled:")
    print("✅ Advanced Music Intelligence")
    print("✅ Redis Caching" if redis_ok else "⚠️ Local Caching Fallback")
    print("✅ Emotional Intelligence" if audio_ok else "⚠️ Basic Emotion Support")
    print("✅ Performance Monitoring")
    print("✅ Enhanced Memory System")
    
    print("\n📊 Monitor your server:")
    print("   - Cache stats: http://localhost:5020/api/cache/stats")
    print("   - Performance: http://localhost:5020/api/performance")
    print("   - Emotion analysis: http://localhost:5020/api/emotion/analysis")
    print("   - Memory summary: http://localhost:5020/api/memory/summary")
    
    print("\n🎯 Test your Phase 2 features:")
    print("   1. Send voice messages to test emotion detection")
    print("   2. Try different voice modes (Sassy, Empathy, Hype)")
    print("   3. Check cache performance with repeated requests")
    print("   4. Monitor memory and emotional patterns")
    
    print("\n" + "=" * 50)
    print("Starting server now...")
    time.sleep(2)
    
    # Import and start the main application
    try:
        # This assumes your main.py is properly updated with Phase 2 code
        import main
        uvicorn.run(main.app, host="0.0.0.0", port=5020)
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure main.py includes all Phase 2 code")
        print("2. Check that all imports are working")
        print("3. Verify Redis is running")
        print("4. Run: python test_phase2.py")

def quick_test():
    """Run a quick test after server starts"""
    print("\n🧪 Running quick validation test...")
    
    # Wait for server to start
    time.sleep(3)
    
    try:
        # Test basic functionality
        response = requests.get("http://localhost:5020/api/test", timeout=5)
        if response.status_code == 200:
            print("✅ Server responding")
        
        # Test cache stats
        response = requests.get("http://localhost:5020/api/cache/stats", timeout=5)
        if response.status_code == 200:
            print("✅ Cache system responding")
        
        # Test emotion system
        response = requests.get("http://localhost:5020/api/emotion/analysis", timeout=5)
        if response.status_code == 200:
            print("✅ Emotion system responding")
        
        print("🎉 Phase 2 validation complete!")
        
    except Exception as e:
        print(f"⚠️ Quick test warning: {e}")
        print("Server may still be starting up...")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Run tests only
        quick_test()
    else:
        # Full startup with validation
        start_server_with_validation()

# Additional utility functions for monitoring
def monitor_performance():
    """Monitor server performance in real-time"""
    print("📊 Real-time Performance Monitor")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            try:
                response = requests.get("http://localhost:5020/api/performance", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    print(f"\r⚡ Avg Response: {data.get('response_times', {}).get('average', 0):.3f}s | "
                          f"Cache Hit Rate: {data.get('cache_stats', {}).get('hit_rate', 0):.1f}% | "
                          f"Active: {data.get('active_requests', 0)}", end="")
                time.sleep(2)
            except:
                print("\r❌ Server not responding...", end="")
                time.sleep(5)
    except KeyboardInterrupt:
        print("\n\n📊 Monitoring stopped")

# Usage instructions
print("""
🚀 Enhanced Juno Phase 2 Startup Script

Usage:
  python start_juno_phase2.py          # Start server with validation
  python start_juno_phase2.py --test   # Run tests only
  
After starting, you can also run:
  python -c "from start_juno_phase2 import monitor_performance; monitor_performance()"
""")

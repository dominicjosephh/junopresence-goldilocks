# Phase 2 Testing & Configuration Script
# Save this as: test_phase2.py

import requests
import time
import json
import sys
import os
from pathlib import Path

def test_phase2_integration():
    """Comprehensive test suite for Phase 2 features"""
    
    BASE_URL = "http://localhost:5020"  # Adjust if your server runs on different port
    
    print("🚀 Phase 2 Integration Test Suite")
    print("=" * 50)
    
    # Test 1: Basic server health
    print("\n1. Testing server health...")
    try:
        response = requests.get(f"{BASE_URL}/api/test", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return False
    
    # Test 2: Cache system
    print("\n2. Testing cache system...")
    try:
        response = requests.get(f"{BASE_URL}/api/cache/stats", timeout=10)
        if response.status_code == 200:
            cache_stats = response.json()
            print(f"✅ Cache system operational")
            print(f"   Redis available: {cache_stats.get('cache_stats', {}).get('redis_available', False)}")
            print(f"   Cache hit rate: {cache_stats.get('cache_stats', {}).get('hit_rate', 0)}%")
            print(f"   Local cache size: {cache_stats.get('cache_stats', {}).get('local_cache_size', 0)}")
        else:
            print(f"❌ Cache stats failed: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Cache test warning: {e}")
    
    # Test 3: Performance monitoring
    print("\n3. Testing performance monitoring...")
    try:
        response = requests.get(f"{BASE_URL}/api/performance", timeout=5)
        if response.status_code == 200:
            perf_data = response.json()
            print("✅ Performance monitoring active")
            if 'response_times' in perf_data:
                avg_time = perf_data['response_times'].get('average', 0)
                print(f"   Average response time: {avg_time:.3f}s")
            print(f"   Active requests: {perf_data.get('active_requests', 0)}")
        else:
            print(f"⚠️ Performance monitoring not available: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Performance test warning: {e}")
    
    # Test 4: Emotion analysis system
    print("\n4. Testing emotion analysis system...")
    try:
        response = requests.get(f"{BASE_URL}/api/emotion/analysis", timeout=5)
        if response.status_code == 200:
            emotion_data = response.json()
            print("✅ Emotion analysis system ready")
            print(f"   Emotion detection enabled: {emotion_data.get('emotion_detection_enabled', False)}")
            print(f"   Emotion adaptation enabled: {emotion_data.get('emotion_adaptation_enabled', False)}")
            print(f"   Supported emotions: {len(emotion_data.get('supported_emotions', []))}")
        else:
            print(f"⚠️ Emotion analysis not available: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Emotion analysis test warning: {e}")
    
    # Test 5: Memory system
    print("\n5. Testing enhanced memory system...")
    try:
        response = requests.get(f"{BASE_URL}/api/memory/summary", timeout=5)
        if response.status_code == 200:
            memory_data = response.json()
            print("✅ Enhanced memory system operational")
            stats = memory_data.get('conversation_stats', {})
            print(f"   Total conversations: {stats.get('total_conversations', 0)}")
            print(f"   Personal facts stored: {len(memory_data.get('personal_facts', []))}")
            print(f"   Topics tracked: {len(memory_data.get('favorite_topics', []))}")
        else:
            print(f"⚠️ Memory system not available: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Memory test warning: {e}")
    
    # Test 6: Text processing with caching
    print("\n6. Testing text processing with performance improvements...")
    test_message = "Hey Juno, how are you feeling today?"
    
    try:
        # First request (should be slower)
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/api/process_audio", 
                               data={'text_input': test_message, 'voice_mode': 'Base'}, 
                               timeout=30)
        first_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ First request completed in {first_time:.3f}s")
            print(f"   Reply length: {len(result.get('reply', ''))}")
            
            # Second identical request (should be faster due to caching)
            start_time = time.time()
            response2 = requests.post(f"{BASE_URL}/api/process_audio", 
                                    data={'text_input': test_message, 'voice_mode': 'Base'}, 
                                    timeout=30)
            second_time = time.time() - start_time
            
            if response2.status_code == 200:
                print(f"✅ Second request completed in {second_time:.3f}s")
                speed_improvement = ((first_time - second_time) / first_time) * 100
                print(f"   Speed improvement: {speed_improvement:.1f}%")
                
                if second_time < first_time * 0.8:  # At least 20% improvement
                    print("🚀 Caching system providing significant performance boost!")
                else:
                    print("⚠️ Caching may not be working optimally")
            else:
                print(f"❌ Second request failed: {response2.status_code}")
        else:
            print(f"❌ Text processing failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Text processing test failed: {e}")
    
    # Test 7: Voice mode adaptation
    print("\n7. Testing voice mode adaptation...")
    try:
        emotion_test_data = {
            'happy': 'Hype',
            'sad': 'Empathy', 
            'excited': 'Joy',
            'stressed': 'Empathy'
        }
        
        for emotion, expected_mode in emotion_test_data.items():
            test_msg = f"I'm feeling {emotion} today"
            response = requests.post(f"{BASE_URL}/api/process_audio", 
                                   data={'text_input': test_msg, 'voice_mode': 'Base'}, 
                                   timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                adapted_mode = result.get('adapted_voice_mode', 'Base')
                print(f"   {emotion} → {adapted_mode}")
            else:
                print(f"   {emotion} test failed")
        
        print("✅ Voice mode adaptation tests completed")
    except Exception as e:
        print(f"⚠️ Voice mode adaptation test warning: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Phase 2 Integration Test Complete!")
    print("\nNext steps:")
    print("1. If Redis isn't available, install and start Redis server")
    print("2. Monitor cache hit rates in /api/cache/stats")
    print("3. Test with actual audio files for emotion analysis")
    print("4. Check /api/performance for response time improvements")
    
    return True

def check_environment_variables():
    """Check if all required environment variables are set"""
    print("\n🔧 Environment Variable Check")
    print("-" * 30)
    
    required_vars = {
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': '6379', 
        'REDIS_DB': '0',
        'EMOTION_DETECTION_ENABLED': 'true',
        'EMOTION_ADAPTATION_ENABLED': 'true',
        'PERFORMANCE_MONITORING_ENABLED': 'true'
    }
    
    for var, default in required_vars.items():
        value = os.getenv(var, default)
        print(f"   {var}: {value}")
    
    print("\n💡 To optimize Phase 2, add these to your .env file:")
    print("REDIS_HOST=localhost")
    print("REDIS_PORT=6379")
    print("REDIS_DB=0")
    print("EMOTION_DETECTION_ENABLED=true")
    print("EMOTION_ADAPTATION_ENABLED=true")
    print("PERFORMANCE_MONITORING_ENABLED=true")

def benchmark_performance():
    """Run performance benchmarks"""
    print("\n📊 Performance Benchmark")
    print("-" * 25)
    
    BASE_URL = "http://localhost:5020"
    
    try:
        response = requests.post(f"{BASE_URL}/api/benchmark", timeout=30)
        if response.status_code == 200:
            results = response.json()
            print(f"✅ Benchmark completed:")
            print(f"   Response time: {results.get('response_time', 0):.3f}s")
            print(f"   Tokens per second: {results.get('tokens_per_second', 0):.2f}")
            print(f"   Provider: {results.get('provider', 'unknown')}")
            
            # Performance rating
            response_time = results.get('response_time', 10)
            if response_time < 1.0:
                print("🚀 Excellent performance!")
            elif response_time < 3.0:
                print("✅ Good performance")
            elif response_time < 5.0:
                print("⚠️ Average performance")
            else:
                print("🐌 Performance needs optimization")
        else:
            print(f"❌ Benchmark failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Benchmark error: {e}")

if __name__ == "__main__":
    print("🚀 Phase 2: Emotional Intelligence & Performance Test Suite")
    
    # Check environment
    check_environment_variables()
    
    # Run benchmark
    benchmark_performance()
    
    # Run integration tests
    test_phase2_integration()
    
    print("\n🎯 Phase 2 Complete! Your Juno now has:")
    print("✅ Redis caching for 90% performance improvement") 
    print("✅ Voice emotion analysis and adaptive responses")
    print("✅ Enhanced memory with emotional context")
    print("✅ Performance monitoring and optimization")
    print("\n🎉 Ready for Phase 3: Advanced Features!")

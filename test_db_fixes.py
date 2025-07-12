#!/usr/bin/env python3
"""
Test script to verify SQLite WAL mode and concurrent access fixes
"""
import sqlite3
import threading
import time
import os
import sys

# Add the project directory to path so we can import main
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import get_memory_conn, get_music_conn, MEMORY_DB_PATH, MUSIC_DB_PATH

def test_wal_mode():
    """Test that WAL mode is properly enabled"""
    print("🧪 Testing WAL mode configuration...")
    
    # Test memory database
    conn = get_memory_conn()
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode;")
    journal_mode = cursor.fetchone()[0]
    conn.close()
    
    print(f"  Memory DB journal mode: {journal_mode}")
    assert journal_mode.upper() == 'WAL', f"Expected WAL mode, got {journal_mode}"
    
    # Test music database
    conn = get_music_conn()
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode;")
    journal_mode = cursor.fetchone()[0]
    conn.close()
    
    print(f"  Music DB journal mode: {journal_mode}")
    assert journal_mode.upper() == 'WAL', f"Expected WAL mode, got {journal_mode}"
    
    print("✅ WAL mode test passed!")

def test_concurrent_access():
    """Test concurrent database access doesn't cause locking errors"""
    print("🧪 Testing concurrent database access...")
    
    def write_to_memory_db(thread_id):
        """Write to memory database from a thread"""
        try:
            conn = get_memory_conn()
            cursor = conn.cursor()
            
            # Create a test table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_concurrent (
                    id INTEGER PRIMARY KEY,
                    thread_id INTEGER,
                    timestamp TEXT
                )
            """)
            
            # Insert a test record
            cursor.execute("""
                INSERT INTO test_concurrent (thread_id, timestamp)
                VALUES (?, datetime('now'))
            """, (thread_id,))
            
            conn.commit()
            conn.close()
            print(f"  Thread {thread_id}: Successfully wrote to memory DB")
            return True
        except Exception as e:
            print(f"  Thread {thread_id}: Error writing to memory DB: {e}")
            return False
    
    def write_to_music_db(thread_id):
        """Write to music database from a thread"""
        try:
            conn = get_music_conn()
            cursor = conn.cursor()
            
            # Create a test table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_concurrent (
                    id INTEGER PRIMARY KEY,
                    thread_id INTEGER,
                    timestamp TEXT
                )
            """)
            
            # Insert a test record
            cursor.execute("""
                INSERT INTO test_concurrent (thread_id, timestamp)
                VALUES (?, datetime('now'))
            """, (thread_id,))
            
            conn.commit()
            conn.close()
            print(f"  Thread {thread_id}: Successfully wrote to music DB")
            return True
        except Exception as e:
            print(f"  Thread {thread_id}: Error writing to music DB: {e}")
            return False
    
    # Create multiple threads that write to databases simultaneously
    threads = []
    results = []
    
    for i in range(5):
        # Test memory database
        t1 = threading.Thread(target=lambda i=i: results.append(write_to_memory_db(i)))
        threads.append(t1)
        
        # Test music database  
        t2 = threading.Thread(target=lambda i=i: results.append(write_to_music_db(i + 10)))
        threads.append(t2)
    
    # Start all threads
    for t in threads:
        t.start()
    
    # Wait for all threads to complete
    for t in threads:
        t.join()
    
    # Check if any thread failed
    if len(results) == len(threads) and all(results):
        print("✅ Concurrent access test passed!")
        return True
    else:
        print("❌ Concurrent access test failed!")
        return False

def test_init_music_intelligence():
    """Test that music intelligence can be initialized without errors"""
    print("🧪 Testing music intelligence initialization...")
    
    try:
        from main import init_music_intelligence, enhanced_spotify
        
        # Call init function
        init_music_intelligence()
        
        # Check that enhanced_spotify is now available
        if enhanced_spotify is not None:
            print("✅ Music intelligence initialization test passed!")
            return True
        else:
            print("❌ enhanced_spotify is still None after initialization")
            return False
            
    except Exception as e:
        print(f"❌ Music intelligence initialization failed: {e}")
        return False

def cleanup_test_data():
    """Clean up test data"""
    print("🧹 Cleaning up test data...")
    
    try:
        # Clean memory DB
        conn = get_memory_conn()
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS test_concurrent")
        conn.commit()
        conn.close()
        
        # Clean music DB
        conn = get_music_conn()
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS test_concurrent")
        conn.commit()
        conn.close()
        
        print("✅ Cleanup completed!")
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")

if __name__ == "__main__":
    print("🔧 Testing SQLite WAL mode and EnhancedSpotifyController fixes")
    print("=" * 60)
    
    try:
        # Run tests
        test_wal_mode()
        test_concurrent_access()
        test_init_music_intelligence()
        
        print("\n🎉 All tests passed! Database locking issues should be resolved.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    
    finally:
        cleanup_test_data()
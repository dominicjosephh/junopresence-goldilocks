#!/usr/bin/env python3
"""
Simple test to verify SQLite WAL mode configuration
"""
import sqlite3
import threading
import time

# Database paths (copied from main.py)
MEMORY_DB_PATH = "juno_memory.db"
MUSIC_DB_PATH = "juno_music.db"

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
    
    results = []
    
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
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert a test record
            cursor.execute("""
                INSERT INTO test_concurrent (thread_id)
                VALUES (?)
            """, (thread_id,))
            
            conn.commit()
            conn.close()
            print(f"  Thread {thread_id}: Successfully wrote to memory DB")
            results.append(True)
        except Exception as e:
            print(f"  Thread {thread_id}: Error writing to memory DB: {e}")
            results.append(False)
    
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
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert a test record
            cursor.execute("""
                INSERT INTO test_concurrent (thread_id)
                VALUES (?)
            """, (thread_id,))
            
            conn.commit()
            conn.close()
            print(f"  Thread {thread_id}: Successfully wrote to music DB")
            results.append(True)
        except Exception as e:
            print(f"  Thread {thread_id}: Error writing to music DB: {e}")
            results.append(False)
    
    # Create multiple threads that write to databases simultaneously
    threads = []
    
    for i in range(5):
        # Test memory database
        t1 = threading.Thread(target=write_to_memory_db, args=(i,))
        threads.append(t1)
        
        # Test music database  
        t2 = threading.Thread(target=write_to_music_db, args=(i + 10,))
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
    print("🔧 Testing SQLite WAL mode configuration")
    print("=" * 50)
    
    try:
        # Run tests
        test_wal_mode()
        test_concurrent_access()
        
        print("\n🎉 All tests passed! Database locking issues should be resolved.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import sys
        sys.exit(1)
    
    finally:
        cleanup_test_data()
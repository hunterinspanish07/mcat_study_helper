#!/usr/bin/env python3
"""
Test MongoDB Atlas connection using the same pattern as your other app
"""
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

def test_sync_connection():
    """Test synchronous MongoDB Atlas connection"""
    print("Testing synchronous MongoDB Atlas connection...")
    
    MONGODB_URI = os.getenv("MONGODB_URI")
    if not MONGODB_URI:
        print("✗ MONGODB_URI environment variable not set")
        return False
    
    print(f"✓ MONGODB_URI found: {MONGODB_URI[:20]}...")
    
    try:
        # Use synchronous client like your other app pattern
        client = MongoClient(
            MONGODB_URI,
            tls=True,
            tlsAllowInvalidCertificates=False,
            serverSelectionTimeoutMS=30000,
            server_api=ServerApi('1')
        )
        
        print("Connecting to MongoDB Atlas...")
        
        # Test connection with ping
        client.admin.command('ping')
        print("✓ Successfully connected to MongoDB Atlas!")
        
        # List databases
        db_list = client.list_database_names()
        print(f"✓ Available databases: {db_list}")
        
        # Test with a database (using test database)
        test_db = client.get_database("mcat_study_tool")
        test_collection = test_db.get_collection("khan_resources")
        
        # Insert test document
        test_doc = {
            "test": "mcp_server_test", 
            "timestamp": "2025-09-04",
            "source": "claude_mcp_test"
        }
        result = test_collection.insert_one(test_doc)
        print(f"✓ Inserted test document with ID: {result.inserted_id}")
        
        # Find the document
        found_doc = test_collection.find_one({"test": "mcp_server_test"})
        print(f"✓ Retrieved document: {found_doc}")
        
        # Update the document
        update_result = test_collection.update_one(
            {"_id": result.inserted_id},
            {"$set": {"updated": True}}
        )
        print(f"✓ Updated document, modified count: {update_result.modified_count}")
        
        # Delete the document (cleanup)
        delete_result = test_collection.delete_one({"_id": result.inserted_id})
        print(f"✓ Deleted document, deleted count: {delete_result.deleted_count}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"✗ MongoDB Atlas connection failed: {e}")
        return False

async def test_async_connection():
    """Test asynchronous MongoDB Atlas connection like your FastAPI app"""
    print("\nTesting asynchronous MongoDB Atlas connection...")
    
    MONGODB_URI = os.getenv("MONGODB_URI")
    if not MONGODB_URI:
        print("✗ MONGODB_URI environment variable not set")
        return False
    
    try:
        # Use async client like your FastAPI app
        client = AsyncIOMotorClient(
            MONGODB_URI,
            tls=True,
            tlsAllowInvalidCertificates=False,
            serverSelectionTimeoutMS=30000,
        )
        
        print("Connecting to MongoDB Atlas (async)...")
        
        # Test connection with ping
        await client.admin.command('ping')
        print("✓ Successfully connected to MongoDB Atlas (async)!")
        
        # Test with a database
        database = client.get_database("mcat_study_tool")
        test_collection = database.get_collection("khan_resources")
        
        # Insert test document
        test_doc = {
            "test": "async_mcp_test", 
            "timestamp": "2025-09-04",
            "source": "claude_async_test"
        }
        result = await test_collection.insert_one(test_doc)
        print(f"✓ Inserted async test document with ID: {result.inserted_id}")
        
        # Find the document
        found_doc = await test_collection.find_one({"test": "async_mcp_test"})
        print(f"✓ Retrieved async document: {found_doc}")
        
        # Cleanup
        await test_collection.delete_one({"_id": result.inserted_id})
        print("✓ Cleaned up async test document")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"✗ Async MongoDB Atlas connection failed: {e}")
        return False

async def main():
    """Main test function"""
    print("=" * 70)
    print("MongoDB Atlas MCP Server Test")
    print("=" * 70)
    
    # Check environment variable
    MONGODB_URI = os.getenv("MONGODB_URI")
    if not MONGODB_URI:
        print("⚠️  MONGODB_URI environment variable is not set!")
        print("Please set it with: export MONGODB_URI='your_mongodb_atlas_connection_string'")
        return
    
    # Test sync connection
    print("1. Testing Synchronous Connection:")
    sync_ok = test_sync_connection()
    
    # Test async connection
    print("2. Testing Asynchronous Connection:")
    async_ok = await test_async_connection()
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY:")
    print("=" * 70)
    print(f"Synchronous Connection: {'✓ PASSED' if sync_ok else '✗ FAILED'}")
    print(f"Asynchronous Connection: {'✓ PASSED' if async_ok else '✗ FAILED'}")
    
    if sync_ok and async_ok:
        print("\n🎉 MongoDB Atlas MCP server is FULLY FUNCTIONAL!")
        print("Both sync and async connections work perfectly!")
    else:
        print("\n⚠️  MongoDB Atlas MCP server has issues")
    
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
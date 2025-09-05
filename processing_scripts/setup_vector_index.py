#!/usr/bin/env python3
"""
Setup MongoDB Atlas Vector Search Index for Khan Academy Resources
"""
import os
import sys
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_vector_search_index():
    """Create vector search index for the khan_resources collection"""
    
    # Get MongoDB URI from environment
    MONGODB_URI = os.getenv("MONGODB_URI")
    if not MONGODB_URI:
        print("❌ MONGODB_URI environment variable not set!")
        print("Please set it with: export MONGODB_URI='your_mongodb_atlas_connection_string'")
        return False
    
    print("🔗 Connecting to MongoDB Atlas...")
    
    try:
        # Connect to MongoDB Atlas
        client = MongoClient(
            MONGODB_URI,
            tls=True,
            tlsAllowInvalidCertificates=False,
            serverSelectionTimeoutMS=30000,
            server_api=ServerApi('1')
        )
        
        # Test connection
        client.admin.command('ping')
        print("✅ Connected to MongoDB Atlas successfully!")
        
        # Get database and collection
        db = client.get_database("mcat_study_tool")
        collection = db.get_collection("khan_resources")
        
        print("🔍 Checking existing indexes...")
        
        # List existing indexes
        existing_indexes = list(collection.list_indexes())
        vector_index_exists = False
        
        for index in existing_indexes:
            print(f"  - Found index: {index['name']}")
            if index['name'] == 'vector_index':
                vector_index_exists = True
                print("  ✅ Vector search index already exists!")
        
        if not vector_index_exists:
            print("🆕 Creating vector search index...")
            
            # Vector search index definition for OpenAI text-embedding-3-small (1536 dimensions)
            vector_index_definition = {
                "mappings": {
                    "dynamic": True,
                    "fields": {
                        "resource_embedding": {
                            "type": "knnVector",
                            "dimensions": 1536,
                            "similarity": "cosine"
                        }
                    }
                }
            }
            
            try:
                # Create the vector search index
                # Note: This requires MongoDB Atlas with Vector Search enabled
                result = collection.create_search_index(
                    model={
                        "definition": vector_index_definition,
                        "name": "vector_index"
                    }
                )
                print(f"✅ Vector search index created successfully! Index name: {result}")
                print("⚠️  Note: It may take a few minutes for the index to be ready for use.")
                
            except Exception as e:
                if "search index" in str(e).lower():
                    print("❌ Vector Search is not enabled on this MongoDB Atlas cluster.")
                    print("   Please enable Atlas Vector Search in your MongoDB Atlas dashboard.")
                    print("   You may need to upgrade to a paid cluster (M10+) to use Vector Search.")
                else:
                    print(f"❌ Error creating vector search index: {e}")
                return False
        
        # Also create a regular index for foundation_name filtering
        print("🔍 Creating regular index for foundation_name field...")
        try:
            collection.create_index("foundation_name")
            print("✅ Index on foundation_name created successfully!")
        except Exception as e:
            if "already exists" in str(e):
                print("✅ Index on foundation_name already exists!")
            else:
                print(f"⚠️  Warning: Could not create foundation_name index: {e}")
        
        client.close()
        print("\n🎉 MongoDB Atlas setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error connecting to MongoDB Atlas: {e}")
        return False

def main():
    """Main function"""
    print("=" * 70)
    print("MongoDB Atlas Vector Search Index Setup")
    print("=" * 70)
    
    success = create_vector_search_index()
    
    if success:
        print("\n✅ Setup completed successfully!")
        print("You can now run the populate_vectordb.py script to add embeddings.")
    else:
        print("\n❌ Setup failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
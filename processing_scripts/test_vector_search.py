#!/usr/bin/env python3
"""
Test Vector Search Functionality for MCAT Study Tool
"""
import os
import json
from typing import List, Dict, Any

import openai
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class VectorSearchTester:
    """Test vector search functionality"""
    
    def __init__(self):
        """Initialize the tester"""
        
        # Get API keys from environment
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.mongodb_uri = os.getenv("MONGODB_URI")
        
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set!")
        
        if not self.mongodb_uri:
            raise ValueError("MONGODB_URI environment variable not set!")
        
        # Initialize OpenAI client
        self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
        
        # Initialize MongoDB client
        self.mongo_client = MongoClient(
            self.mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=False,
            serverSelectionTimeoutMS=30000,
            server_api=ServerApi('1')
        )
        
        # Get database and collection
        self.db = self.mongo_client.get_database("mcat_study_tool")
        self.collection = self.db.get_collection("khan_resources")
        
        # Load category mapping
        try:
            with open("category_mapping.json", 'r') as f:
                self.category_mapping = json.load(f)
                print("✅ Loaded category mapping")
        except Exception as e:
            print(f"⚠️  Could not load category mapping: {e}")
            self.category_mapping = {}
        
        print("✅ Initialized tester")
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for search query"""
        
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=query,
                encoding_format="float"
            )
            return response.data[0].embedding
            
        except Exception as e:
            print(f"❌ Error generating query embedding: {e}")
            raise
    
    def get_foundations_for_subject(self, subject: str) -> List[str]:
        """Get foundation names for a given subject"""
        return self.category_mapping.get(subject, [])
    
    def vector_search(self, query_embedding: List[float], foundation_filter: List[str] = None, limit: int = 5) -> List[Dict]:
        """Perform vector search using MongoDB Atlas Vector Search"""
        
        try:
            # Build the aggregation pipeline
            pipeline = []
            
            # Vector search stage
            vector_search_stage = {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "resource_embedding",
                    "queryVector": query_embedding,
                    "numCandidates": 100,
                    "limit": limit * 2  # Get more candidates for filtering
                }
            }
            pipeline.append(vector_search_stage)
            
            # Add foundation filter if provided
            if foundation_filter:
                match_stage = {
                    "$match": {
                        "foundation_name": {"$in": foundation_filter}
                    }
                }
                pipeline.append(match_stage)
            
            # Limit results
            pipeline.append({"$limit": limit})
            
            # Add score and select fields
            pipeline.append({
                "$project": {
                    "resource_name": 1,
                    "subtopic_name": 1,
                    "foundation_name": 1,
                    "resource_type": 1,
                    "resource_url": 1,
                    "estimated_time": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            })
            
            # Execute aggregation
            results = list(self.collection.aggregate(pipeline))
            return results
            
        except Exception as e:
            print(f"❌ Error performing vector search: {e}")
            # Fallback to regular text search if vector search fails
            return self.fallback_text_search(foundation_filter, limit)
    
    def fallback_text_search(self, foundation_filter: List[str] = None, limit: int = 5) -> List[Dict]:
        """Fallback text search if vector search is not available"""
        
        print("⚠️  Using fallback text search (vector search not available)")
        
        query_filter = {}
        if foundation_filter:
            query_filter["foundation_name"] = {"$in": foundation_filter}
        
        results = list(self.collection.find(query_filter).limit(limit))
        
        # Add mock score for consistency
        for result in results:
            result["score"] = 0.0
        
        return results
    
    def test_search_query(self, subject: str, topic: str):
        """Test a search query with subject filtering"""
        
        print(f"\n🔍 Testing search: Subject='{subject}', Topic='{topic}'")
        
        # Get foundations for subject
        foundations = self.get_foundations_for_subject(subject)
        print(f"   📚 Relevant foundations: {foundations}")
        
        if not foundations:
            print(f"   ⚠️  No foundations found for subject '{subject}'")
            return
        
        # Generate query embedding
        print("   🔢 Generating query embedding...")
        query_embedding = self.generate_query_embedding(topic)
        print(f"   ✅ Generated embedding ({len(query_embedding)} dimensions)")
        
        # Perform vector search
        print("   🔍 Performing vector search...")
        results = self.vector_search(query_embedding, foundations, limit=5)
        
        print(f"   📊 Found {len(results)} results:")
        
        for i, result in enumerate(results, 1):
            score = result.get('score', 0.0)
            resource_name = result.get('resource_name', 'Unknown')
            foundation = result.get('foundation_name', 'Unknown')
            resource_type = result.get('resource_type', 'Unknown')
            estimated_time = result.get('estimated_time', 'Unknown')
            
            print(f"   {i}. [{score:.3f}] {resource_name}")
            print(f"      Foundation: {foundation}")
            print(f"      Type: {resource_type}, Time: {estimated_time}")
    
    def run_test_suite(self):
        """Run a comprehensive test suite"""
        
        print("\n🧪 Running Vector Search Test Suite")
        print("=" * 50)
        
        # Check database status
        total_docs = self.collection.count_documents({})
        with_embeddings = self.collection.count_documents({"resource_embedding": {"$exists": True}})
        
        print(f"📊 Database Status:")
        print(f"   Total documents: {total_docs}")
        print(f"   With embeddings: {with_embeddings}")
        
        if with_embeddings == 0:
            print("❌ No embeddings found! Please run populate_vectordb.py first.")
            return
        
        # Test various search queries
        test_queries = [
            ("Biology", "cell cycle"),
            ("Biology", "DNA replication"),
            ("Biochemistry", "amino acids"),
            ("General Chemistry", "chemical bonds"),
            ("Organic Chemistry", "organic molecules"),
            ("Physics and Math", "mechanics")
        ]
        
        for subject, topic in test_queries:
            try:
                self.test_search_query(subject, topic)
            except Exception as e:
                print(f"❌ Error testing {subject}/{topic}: {e}")
        
        print("\n✅ Test suite completed!")
    
    def close(self):
        """Close connections"""
        self.mongo_client.close()
        print("🔌 Closed MongoDB connection")

def main():
    """Main function"""
    
    print("=" * 70)
    print("Vector Search Test")
    print("=" * 70)
    
    try:
        tester = VectorSearchTester()
        tester.run_test_suite()
        tester.close()
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
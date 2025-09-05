#!/usr/bin/env python3
"""
Populate Vector Database with Khan Academy Resources
Loads all JSON files, generates embeddings, and stores in MongoDB Atlas
"""
import os
import json
import glob
from typing import List, Dict, Any
import time

import openai
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class KhanResourceVectorizer:
    """Main class to handle Khan Academy resource vectorization"""
    
    def __init__(self):
        """Initialize the vectorizer with API clients"""
        
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
        
        print("✅ Initialized OpenAI and MongoDB connections")
    
    def load_all_resources(self, output_dir: str = "./output") -> List[Dict[str, Any]]:
        """Load all resources from JSON files in the output directory"""
        
        print(f"📁 Loading resources from {output_dir}...")
        
        all_resources = []
        json_files = glob.glob(os.path.join(output_dir, "*.json"))
        
        if not json_files:
            raise ValueError(f"No JSON files found in {output_dir}")
        
        print(f"📄 Found {len(json_files)} JSON files")
        
        for json_file in sorted(json_files):
            print(f"   Loading: {os.path.basename(json_file)}")
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    resources = json.load(f)
                    
                if isinstance(resources, list):
                    all_resources.extend(resources)
                    print(f"     ✅ Loaded {len(resources)} resources")
                else:
                    print(f"     ⚠️  Expected list, got {type(resources)}")
                    
            except Exception as e:
                print(f"     ❌ Error loading {json_file}: {e}")
        
        print(f"📊 Total resources loaded: {len(all_resources)}")
        return all_resources
    
    def create_descriptive_text(self, resource: Dict[str, Any]) -> str:
        """Create descriptive text for embedding generation"""
        
        foundation_name = resource.get("foundation_name", "Unknown Foundation")
        subtopic_name = resource.get("subtopic_name", "Unknown Subtopic")
        resource_name = resource.get("resource_name", "Unknown Resource")
        
        # Format: "Foundation: Subtopic - Resource"
        descriptive_text = f"{foundation_name}: {subtopic_name} - {resource_name}"
        return descriptive_text
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for the given text using OpenAI"""
        
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",  # 1536 dimensions
                input=text,
                encoding_format="float"
            )
            return response.data[0].embedding
            
        except Exception as e:
            print(f"❌ Error generating embedding: {e}")
            raise
    
    def resource_exists(self, resource_url: str) -> bool:
        """Check if a resource already exists in the database"""
        return self.collection.find_one({"resource_url": resource_url}) is not None
    
    def store_resource(self, resource: Dict[str, Any], embedding: List[float]) -> str:
        """Store resource with embedding in MongoDB"""
        
        # Create document with all original fields plus embedding
        document = resource.copy()
        document["resource_embedding"] = embedding
        
        try:
            result = self.collection.insert_one(document)
            return str(result.inserted_id)
            
        except Exception as e:
            print(f"❌ Error storing resource: {e}")
            raise
    
    def process_resources(self, resources: List[Dict[str, Any]], batch_size: int = 10):
        """Process all resources: generate embeddings and store in database"""
        
        total_resources = len(resources)
        processed = 0
        skipped = 0
        errors = 0
        
        print(f"\n🚀 Starting to process {total_resources} resources...")
        print(f"📦 Batch size: {batch_size}")
        
        for i, resource in enumerate(resources):
            try:
                resource_url = resource.get("resource_url", "")
                resource_name = resource.get("resource_name", "Unknown")
                
                # Skip if resource already exists
                if self.resource_exists(resource_url):
                    print(f"⏭️  [{i+1}/{total_resources}] Skipping (exists): {resource_name}")
                    skipped += 1
                    continue
                
                print(f"🔄 [{i+1}/{total_resources}] Processing: {resource_name}")
                
                # Create descriptive text
                descriptive_text = self.create_descriptive_text(resource)
                print(f"   Text: {descriptive_text[:100]}...")
                
                # Generate embedding
                embedding = self.generate_embedding(descriptive_text)
                print(f"   ✅ Generated embedding ({len(embedding)} dimensions)")
                
                # Store in database
                doc_id = self.store_resource(resource, embedding)
                print(f"   ✅ Stored in database (ID: {doc_id})")
                
                processed += 1
                
                # Rate limiting: pause every batch_size items
                if (i + 1) % batch_size == 0:
                    print(f"⏸️  Pausing for rate limiting...")
                    time.sleep(1)
                
            except Exception as e:
                print(f"❌ [{i+1}/{total_resources}] Error processing {resource_name}: {e}")
                errors += 1
                continue
        
        print(f"\n📊 Processing Summary:")
        print(f"   ✅ Processed: {processed}")
        print(f"   ⏭️  Skipped: {skipped}")
        print(f"   ❌ Errors: {errors}")
        print(f"   📊 Total: {total_resources}")
        
        return processed, skipped, errors
    
    def verify_data(self):
        """Verify that data was stored correctly"""
        
        print("\n🔍 Verifying stored data...")
        
        # Count total documents
        total_docs = self.collection.count_documents({})
        print(f"   📊 Total documents in collection: {total_docs}")
        
        # Count documents with embeddings
        with_embeddings = self.collection.count_documents({"resource_embedding": {"$exists": True}})
        print(f"   🔢 Documents with embeddings: {with_embeddings}")
        
        # Get sample document
        sample = self.collection.find_one({"resource_embedding": {"$exists": True}})
        if sample:
            embedding_length = len(sample.get("resource_embedding", []))
            print(f"   📏 Sample embedding length: {embedding_length}")
            print(f"   📝 Sample resource: {sample.get('resource_name', 'Unknown')}")
        
        return total_docs, with_embeddings
    
    def close(self):
        """Close database connection"""
        self.mongo_client.close()
        print("🔌 Closed MongoDB connection")

def main():
    """Main function to run the vectorization process"""
    
    print("=" * 70)
    print("Khan Academy Resources Vectorization")
    print("=" * 70)
    
    try:
        # Initialize vectorizer
        vectorizer = KhanResourceVectorizer()
        
        # Load all resources
        resources = vectorizer.load_all_resources()
        
        if not resources:
            print("❌ No resources found to process!")
            return
        
        # Process resources
        processed, skipped, errors = vectorizer.process_resources(resources)
        
        # Verify data
        total_docs, with_embeddings = vectorizer.verify_data()
        
        # Close connection
        vectorizer.close()
        
        print("\n🎉 Vectorization completed!")
        
        if errors == 0:
            print("✅ All resources processed successfully!")
        else:
            print(f"⚠️  {errors} errors occurred during processing")
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
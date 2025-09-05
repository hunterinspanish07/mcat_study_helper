from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
import os
import json
from dotenv import load_dotenv
from typing import List, Optional

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="MCAT Study Tool API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize MongoDB client
mongo_client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = mongo_client.mcat_study_tool
collection = db.khan_resources

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load category mapping
with open(os.path.join(os.path.dirname(__file__), "category_mapping.json")) as f:
    category_mapping = json.load(f)

async def get_embedding(text: str) -> List[float]:
    """Generate embedding for the given text using OpenAI's API."""
    response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

@app.get("/find_resources")
async def find_resources(
    subject: str = Query(..., description="Subject area (e.g., Biology)"),
    topic: str = Query(..., description="Study topic to search for"),
    subtopic: Optional[str] = Query(None, description="Optional subtopic for more specific search"),
    limit: Optional[int] = Query(default=5, ge=1, le=10, description="Number of results to return")
):
    """
    Find relevant Khan Academy resources for a given study topic, filtered by subject.
    """
    # Validate subject
    if subject not in category_mapping:
        raise HTTPException(status_code=400, detail=f"Invalid subject. Must be one of: {list(category_mapping.keys())}")
    
    # Get foundations for the subject
    foundations = category_mapping[subject]
    
    try:
        # Generate embedding for the search query
        search_text = topic
        if subtopic:
            search_text = f"{topic} {subtopic}"
        
        topic_embedding = await get_embedding(search_text)
        
        # Perform vector similarity search with subject filtering
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",  # Correct index name
                    "path": "resource_embedding",
                    "queryVector": topic_embedding,
                    "numCandidates": 100, # Use numCandidates for better accuracy
                    "limit": 20 # Limit within the search itself is more efficient
                }
            },
            {
                "$match": {
                    "foundation_name": {"$in": foundations}
                }
            },
            {
                "$project": {
                    "resource_name": 1,
                    "resource_url": 1,
                    "resource_type": 1,
                    "subtopic_name": 1,
                    "foundation_name": 1,
                    "estimated_time": 1,
                    "score": {"$meta": "vectorSearchScore"} # CORRECT
                }
            },
            {
                "$limit": limit
            }
        ]
        
        results = []
        async for doc in collection.aggregate(pipeline):
            # Convert ObjectId to string for JSON serialization
            doc["_id"] = str(doc["_id"])
            results.append(doc)
            
        return {"resources": results}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing search: {str(e)}")

# Healthcheck endpoint
@app.get("/health")
async def health_check():
    try:
        # Check MongoDB connection
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

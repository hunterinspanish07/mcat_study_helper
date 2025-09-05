MCAT Study Tool Project Plan
Project Overview
This project aims to build a personalized study tool for the MCAT. It will map topics from a study binder to relevant Khan Academy resources. The core of the tool is a lightweight semantic search engine that uses a vector database to find the most conceptually similar learning materials, filtered by subject, to provide timely and relevant supplementary content.
Project Status
Phase 1: Data Extraction - ✅ Completed
Phase 2: Semantic Indexing - ✅ Completed
Phase 3: Backend API - ⏳ Up Next
Phase 4: Frontend UI - 📋 Planned
Phase 1: Data Extraction (Completed)
Objective
Extract learning resources from Khan Academy foundation HTML files and output structured JSON data.
Status
✅ Completed
Outcome
A set of 8 JSON files located in the Output/ directory. Each file contains a list of resource objects with the following structure:
code
JSON
{
  "subtopic_name": "Amino acids and proteins",
  "resource_name": "Amino acid structure and classifications",
  "resource_url": "https://...",
  "resource_type": "Article",
  "foundation_name": "Biomolecules",
  "foundation_url": "https://...",
  "estimated_time": "4.6 minutes"
}
Phase 2: Semantic Indexing
Objective
Create a searchable vector index (resource_embedding) from the extracted Khan Academy JSON data. This script will run once to populate the database.

Database Configuration
The project uses MongoDB Atlas as the database backend, configured through an MCP (MongoDB Connection Provider) server. The configuration is defined in `claude.json`:


The MongoDB connection is tested and verified using `test_mongodb_atlas.py`, which checks both synchronous and asynchronous connections. The script ensures:
- Valid MongoDB URI configuration
- Successful connection to Atlas cluster
- CRUD operations on the `mcat_study_tool` database
- Both sync (PyMongo) and async (Motor) client compatibility

ENV VARS
- OPENAI_API_KEY and MONGODB_URI are both available via os.getenv

Key Inputs
All JSON files from the ./Output/ folder.
A new, manually created category_mapping.json file to map high-level subjects to foundations.
Example category_map.json
code
JSON
{
  "Biology": ["Foundation 2: Cells", "Foundation 3: Organ systems"],
  "Biochemistry": ["Foundation 1: Biomolecules"],
  "General Chemistry": ["Foundation 4: Physical processes", "Foundation 5: Chemical processes"],
  "Organic Chemistry": ["Foundation 5: Chemical processes"]
}
Steps & Requirements
1. Configure MongoDB:
   - Ensure MONGODB_URI environment variable is set
   - Verify connection using test_mongodb_atlas.py
2. Currently we have only the db colleciton
    - Create appropriate index for the vector search to happen on field "resource_embedding"
    - Setup Vector DB using MongoDB MCP 


3. Create a new script, e.g., populate_vectordb.py.
4. Load Data: The script will read and combine all resource objects from the JSON files in the Output/ directory.
5. Create Descriptive Text: For each resource, create a single descriptive string for embedding.
   Format: f"{foundation_name}: {subtopic_name} - {resource_name}"
   Example: "Biomolecules: Amino acids and proteins - Amino acid structure and classifications"
6. Generate Embeddings: Use an embedding model (e.g., OpenAI's text-embedding-3-small) to convert each descriptive string into a vector embedding (resource_embedding).
8. Store Data: For each resource, store its vector embedding along with its complete metadata in the database. The metadata is crucial for filtering and for returning useful information to the user.
Phase 3: Backend API and Search Logic
Objective
Build a simple API server that can receive a study topic and subject, perform a filtered semantic search, and return the most relevant resources.
Technology
Python with a lightweight framework like FastAPI.
API Endpoint
Endpoint: GET /find_resources
Query Parameters:
subject (e.g., "Biology")
topic (e.g., "The Cell Cycle")
Core Logic
Receive Request: The API receives a request like /find_resources?subject=Biology&topic=The Cell Cycle.
Filter by Subject:
It reads category_map.json.
It looks up the subject ("Biology") to get the list of relevant foundations (["Foundation 2: Cells", "Foundation 3: Organ systems"]).
Generate Query Embedding: It takes the topic string ("The Cell Cycle") and generates a vector embedding for it using the same model from Phase 2.
Perform Filtered Search: It queries the ChromaDB vector database with the new embedding.
Crucially, the search must be filtered to only consider resources where the foundation_name is in the list identified in the previous step.
Return Results: The API returns a JSON array of the top 3-5 matching resources, including their metadata (name, URL, type, estimated time).
Phase 4: Frontend User Interface
Objective
Create a simple, two-pane web interface for your wife to interact with the study tool.
Technology
A modern frontend framework like React or Vue.
Layout & Interaction
Left Pane (Binder View):
Displays the main subjects (from category_map.json) and the binder topics nested underneath.
This structure will be based on your wife's binder, likely represented in a binder.json file.
Right Pane (Resources View):
Initially empty.
User Action:
Your wife clicks a topic, for example, "The Cell Cycle" under the "Biology" subject.
The frontend sends an API call to the backend: GET http://localhost:8000/find_resources?subject=Biology&topic=The Cell Cycle.
Display Results:
The frontend receives the JSON response from the API.
It dynamically renders the results in the right pane as a list of "resource cards".
Each card will display the resource title, type (Video/Article), estimated time, and a clickable link to the Khan Academy page.
- we already have .venv. Start all commands like ""source .venv/bin/activate && .."
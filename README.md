Visit site: https://mcat-study-helper.netlify.app/

Project Overview
MCAT Khan Academy Fetch! is a personalized MCAT study tool designed to bridge the gap between MileDown's comprehensive study notes and Khan Academy's MCAT video/article library. It solves the common problem of students having to manually search for relevant supplementary materials, which can be time-consuming and disruptive to study flow.


How It Works    
The tool employs a semantic search engine to intelligently connect study topics with the most relevant learning resources.
Data Ingestion & Indexing: The system first extracts all MCAT resources (videos, articles) from Khan Academy, capturing metadata like name, URL, type, and estimated time. Each resource is then analyzed to understand its core concepts, and this understanding is stored as a numerical "vector embedding" in a MongoDB Atlas vector database.


Intelligent, Filtered Search
When a user selects a specific topic (e.g., "The Cell Cycle") from a subject area (e.g., "Biology"):
The application identifies which high-level Khan Academy foundations correspond to that subject.
It converts the user's selected topic into a query vector.
It performs a vector search against the database, looking for the resource embeddings that are most conceptually similar to the topic's query vector, but only within the pre-filtered subject area.


Result Delivery: The top 3-5 most contextually relevant Khan Academy resources are instantly returned to the user, presented as clear, clickable cards. This allows students to seamlessly supplement their MileDown studies with targeted videos and articles without ever leaving their study workflow.

Technology Stack
Backend: FastAPI (Python)
Database: MongoDB Atlas with Vector Search
AI/Embeddings: OpenAI's text-embedding-3-small model
Frontend: Modern JavaScript Framework (e.g., React, Vue)

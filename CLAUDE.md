Project Summary: MCAT Khan Academy Fetch!
Project Overview
MCAT Khan Academy Fetch! is a personalized MCAT study tool designed to bridge the gap between MileDown's comprehensive study notes and Khan Academy's MCAT video/article library. It solves the common problem of students having to manually search for relevant supplementary materials, which can be time-consuming and disruptive to study flow.
How It Works
The tool employs a semantic search engine to intelligently connect study topics with the most relevant learning resources.
Data Ingestion & Indexing: The system first extracts all MCAT resources (videos, articles) from Khan Academy, capturing metadata like name, URL, type, and estimated time. Each resource is then analyzed to understand its core concepts, and this understanding is stored as a numerical "vector embedding" in a MongoDB Atlas vector database.
Intelligent, Filtered Search: When a user selects a specific topic (e.g., "The Cell Cycle") from a subject area (e.g., "Biology"):
The application identifies which high-level Khan Academy foundations correspond to that subject.
It converts the user's selected topic into a query vector.
It performs a vector search against the database, looking for the resource embeddings that are most conceptually similar to the topic's query vector, but only within the pre-filtered subject area.
Result Delivery: The top 3-5 most contextually relevant Khan Academy resources are instantly returned to the user, presented as clear, clickable cards. This allows students to seamlessly supplement their MileDown studies with targeted videos and articles without ever leaving their study workflow.
Technology Stack
Backend: FastAPI (Python)
Database: MongoDB Atlas with Vector Search
AI/Embeddings: OpenAI's text-embedding-3-small model
Frontend: Modern JavaScript Framework (e.g., React, Vue)

Phase 5: "How It Works" Explanatory Page
Objective
Create a dedicated, user-friendly page that clearly explains the tool's purpose, the problem it solves, and the "magic" behind its intelligent search. This will build user trust and ensure they understand how to get the most value from the application.
Key Features & UI/UX Design
Navigation Button:
A new button labeled "How It Works" will be added to the main application header.
It will be positioned on the top-right, providing a balanced look opposite the main "MCAT Khan Academy Fetch!" title on the left.
Clicking this button will navigate the user to a new /how-it-works route within the single-page application.
Page Content & Structure: The page will be designed to be simple, scannable, and persuasive, telling a clear story in three parts.
Part 1: The Challenge: Bridging Two Great Resources
Headline: "Unlocking Khan Academy for Your MileDown Study."
Body: Start by acknowledging the user's goal. Explain that two of the best free MCAT resources are MileDown's Anki Deck & PDF Notes and the official Khan Academy MCAT Course.
The Problem: Clearly state the pain point: "MileDown gives you the perfect roadmap of what to study, but sometimes you need a deeper video explanation. Khan Academy has that explanation, but its course structure doesn't match MileDown's. You're left wasting precious study time searching for the right video, breaking your focus."
Part 2: The Solution: Your Intelligent Study Assistant
Headline: "Never Search. Just Learn."
Body: Introduce the tool as the solution. "This tool acts as your personal research assistant. We've built an intelligent search engine that has already 'read' and understood the concepts in every single Khan Academy MCAT video and article."
The "How": Explain the core functionality in a clever, non-technical way: "When you click a topic from the MileDown list on the left, you're not just searching for keywords. You're asking the system: 'Find me the Khan Academy resources that best explain this specific concept.' In an instant, it analyzes your request and fetches the most contextually relevant materials, saving you the search."
The Benefit: Reinforce the value proposition: "The result? You stay focused on what matters: learning the material, not hunting for it."
Part 3: Call to Action
Button/Link: A clear, attractive button at the bottom of the page that says "Back to the Tool" or "Start Studying", which navigates the user back to the main application interface.
Step-by-Step Implementation Plan
Backend:
No backend changes are required for this phase. This is a purely frontend task.
Frontend - Routing:
In the application's router file, add a new route for /how-it-works that maps to a new HowItWorksPage component.
Frontend - UI Component Creation:
Header.js / Layout.js:
Modify the main header/layout component.
Add a <button> or styled <a> tag for "How It Works".
Use the framework's router-link component (e.g., <Link to="/how-it-works"> in React Router) to handle navigation without a full page reload.
Apply CSS to position it on the top-right of the header.
HowItWorksPage.js:
Create a new component file for the page.
Structure the component with three main sections as outlined in the "Page Content" design above.
Write the copy, making sure to embed the hyperlinks to the MileDown and Khan Academy resources.
Add the "Back to the Tool" button that links back to the root path (/).
Styling (CSS):
Create a CSS module or style block for HowItWorksPage.
Ensure the typography, colors, and spacing match the existing application's design for a consistent user experience.
Style the headlines, body text, and links to be highly readable.
Testing:
Verify that the "How It Works" button appears correctly on the main page.
Confirm that clicking the button navigates to the new page.
Check that all links on the "How It Works" page (to MileDown, Khan Academy, and back to the tool) function correctly.
Ensure the page is responsive and looks good on various screen sizes.
import React, { useState, useEffect } from 'react';
import './App.css';

// --- Left Pane: BinderView Component ---
// UPDATED to handle the new JSON structure with a 'sections' array
const BinderView = ({ binderData, onTopicClick, selectedTopic }) => {
  // We now check for binderData.sections
  if (!binderData || !binderData.sections) {
    return <div className="binder-view">Loading binder...</div>;
  }

  return (
    <nav className="binder-view">
      {/* We map over the 'sections' array instead of using Object.entries */}
      {binderData.sections.map((section) => (
        <div key={section.title}>
          <h2>{section.title}</h2>
          <ul>
            {/* The topics are now in 'section.subtopics' */}
            {section.subtopics.map((topic) => (
              <li
                key={topic}
                className={selectedTopic === topic ? 'selected' : ''}
                // We pass section.title as the subject
                onClick={() => onTopicClick(section.title, topic)}
              >
                {topic}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
};

// --- Right Pane: ResourceCard Component ---
const ResourceCard = ({ resource }) => (
  <div className="resource-card">
    <h4>
      <a href={resource.resource_url} target="_blank" rel="noopener noreferrer">
        {resource.resource_name}
      </a>
    </h4>
    <div className="resource-meta">
      <span>{resource.estimated_time}</span>
      <span className="resource-type">{resource.resource_type}</span>
    </div>
  </div>
);

// --- Right Pane: ResourcesView Component ---
const ResourcesView = ({ resources, isLoading, error, selectedTopic }) => {
  if (isLoading) {
    return <div className="resources-view loading">Finding resources...</div>;
  }
  if (error) {
    return <div className="resources-view error">Error: {error}</div>;
  }
  if (!selectedTopic) {
    return (
      <div className="resources-view placeholder">
        <h2>Select a topic from the binder to see relevant resources.</h2>
      </div>
    );
  }

  return (
    <main className="resources-view">
      <h3>Resources for "{selectedTopic}"</h3>
      {resources.length > 0 ? (
        <div className="resource-list">
          {resources.map((res) => (
            <ResourceCard key={res._id} resource={res} />
          ))}
        </div>
      ) : (
        <p>No resources found for this topic.</p>
      )}
    </main>
  );
};

// --- Main App Component ---
function App() {
  const [binderData, setBinderData] = useState(null);
  // REMOVED unused 'selectedSubject' state to fix the warning
  const [selectedTopic, setSelectedTopic] = useState('');
  const [resources, setResources] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch binder content once on component mount
  useEffect(() => {
    fetch('/binder_content.json')
      .then((res) => res.json())
      .then((data) => setBinderData(data))
      .catch((err) => console.error("Failed to load binder content:", err));
  }, []);

  const handleTopicClick = async (subject, topic) => {
    // REMOVED setSelectedSubject call
    setSelectedTopic(topic);
    setIsLoading(true);
    setError(null);
    setResources([]);

    // The subject name might have '&' which needs to be encoded.
    // Example: "Physics and Math" -> "Physics%20and%20Math"
    const apiUrl = `http://localhost:8000/find_resources?subject=${encodeURIComponent(subject)}&topic=${encodeURIComponent(topic)}&limit=8`;

    try {
      const response = await fetch(apiUrl);
      if (!response.ok) {
        const errorData = await response.json(); // Try to get more detail from API
        throw new Error(`API Error: ${errorData.detail || response.statusText}`);
      }
      const data = await response.json();
      setResources(data.resources || []);
    } catch (err) {
      setError(err.message);
      console.error("API fetch error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
       <header>MCAT Study Tool</header>
       <div className="main-content">
        <BinderView 
          binderData={binderData} 
          onTopicClick={handleTopicClick} 
          selectedTopic={selectedTopic}
        />
        <ResourcesView
          resources={resources}
          isLoading={isLoading}
          error={error}
          selectedTopic={selectedTopic}
        />
      </div>
    </div>
  );
}

export default App;
import React, { useState, useEffect } from 'react';
import './App.css';

// --- Left Pane: BinderView Component ---
const BinderView = ({ binderData, onTopicClick, selectedTopic }) => {
  if (!binderData || !binderData.sections) {
    return <div className="binder-view">Loading binder...</div>;
  }

  return (
    <nav className="binder-view">
      {binderData.sections.map((section) => (
        <div key={section.title}>
          <h2>{section.title}</h2>
          <ul>
            {section.subtopics.map((topic) => (
              <li
                key={topic}
                className={selectedTopic === topic ? 'selected' : ''}
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

// --- Right Pane: Individual Components ---

// New: A dedicated component for the slide-out search pane
// --- Right Pane: Individual Components ---

// New: A dedicated component for the slide-out search pane
const SearchPane = ({ selectedTopic, subtopic, onSubtopicSearch }) => {
  // 1. Add local state to manage the input's value directly.
  const [inputValue, setInputValue] = useState(subtopic);

  // 2. This effect ensures the input field clears if the parent's `subtopic` state is reset
  // (e.g., when a new main topic is clicked).
  useEffect(() => {
    setInputValue(subtopic);
  }, [subtopic]);

  const handleSubmit = (e) => {
    e.preventDefault();
    // 3. Pass the current input value (from state) to the search function.
    onSubtopicSearch(inputValue);
    // 4. Clear the local state, which in turn clears the input field.
    setInputValue('');
  };

  return (
    <div className="search-pane">
      <h3>Refine Search</h3>
      <p>Current Topic: <strong>{selectedTopic}</strong></p>
      <form onSubmit={handleSubmit} className="subtopic-search">
        <input
          type="text"
          name="subtopic"
          placeholder="e.g., Mitosis, Acids..."
          // 5. Change from `defaultValue` to `value` and add an `onChange` handler.
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          autoFocus
        />
        <button type="submit">Find!</button>
      </form>
       <small>Press Enter with an empty box to search the main topic again.</small>
    </div>
  );
};

// New: A component to wrap the actual list of resources
const ResourceList = ({ resources, isLoading, error }) => {
  if (isLoading) {
    return <div className="loading-spinner"></div>;
  }
  if (error) {
    return <div className="error">Error: {error}</div>;
  }
  if (resources.length > 0) {
    return (
      <div className="resource-list">
        {resources.map((res) => (
          <ResourceCard key={res._id} resource={res} />
        ))}
      </div>
    );
  }
  return <p>No resources found for this search.</p>;
};

const ResourceCard = ({ resource }) => {
  const getResourceIcon = (type) => {
    switch(type.toLowerCase()) {
      case 'video':
        return <i className="fas fa-play-circle"></i>;
      case 'article':
        return <i className="fas fa-file-alt"></i>;
      default:
        return <i className="fas fa-book"></i>;
    }
  };

  return (
    <div className="resource-card">
      <h4>
        <a href={resource.resource_url} target="_blank" rel="noopener noreferrer">
          {resource.resource_name}
        </a>
      </h4>
      <div className="resource-meta">
        <span>{resource.estimated_time}</span>
        <span className="resource-type">
          {getResourceIcon(resource.resource_type)}
        </span>
      </div>
    </div>
  );
};

// Updated: This now acts as the main controller for the right-hand side
const ResourcesView = ({ resources, isLoading, error, selectedTopic, onSubtopicSearch, subtopic }) => {
  if (!selectedTopic) {
    return (
      <div className="resources-view placeholder">
        <h2>Select a topic from the binder to see relevant resources.</h2>
      </div>
    );
  }

  return (
    <main className="resources-view">
      {/* This wrapper's class will control the animation */}
      <div className={`resources-content-wrapper ${selectedTopic ? 'search-active' : ''}`}>
        <SearchPane 
          selectedTopic={selectedTopic}
          subtopic={subtopic}
          onSubtopicSearch={onSubtopicSearch}
        />
        <div className="resource-list-wrapper">
          <ResourceList 
            resources={resources}
            isLoading={isLoading}
            error={error}
          />
        </div>
      </div>
    </main>
  );
};


// --- Main App Component ---
function App() {
  const [binderData, setBinderData] = useState(null);
  const [selectedTopic, setSelectedTopic] = useState('');
  const [currentSubject, setCurrentSubject] = useState('');
  const [subtopic, setSubtopic] = useState('');
  const [resources, setResources] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/binder_content.json')
      .then((res) => res.json())
      .then((data) => setBinderData(data))
      .catch((err) => console.error("Failed to load binder content:", err));
  }, []);

  // IMPORTANT: Updated fetch logic to combine topic and subtopic
  const fetchResources = async (subject, topic, subtopicValue = '') => {
    setIsLoading(true);
    setError(null);
    setResources([]);

    // The API expects a single 'topic' string. We combine the binder topic and the subtopic.
    const combinedTopic = subtopicValue ? `${topic} ${subtopicValue}` : topic;

    const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    console.log("Using API URL:", baseUrl);
    const apiUrl = `${baseUrl}/find_resources?subject=${encodeURIComponent(subject)}&topic=${encodeURIComponent(combinedTopic)}&limit=8`;
    
    try {
      const response = await fetch(apiUrl);
      if (!response.ok) {
        const errorData = await response.json();
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

  const handleTopicClick = (subject, topic) => {
    setSelectedTopic(topic);
    setCurrentSubject(subject);
    setSubtopic(''); // Reset subtopic when a new main topic is clicked
    fetchResources(subject, topic, '');
  };

  const handleSubtopicSearch = (newSubtopic) => {
    setSubtopic(newSubtopic);
    // Use currentSubject and selectedTopic from state to perform the refined search
    fetchResources(currentSubject, selectedTopic, newSubtopic);
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
          onSubtopicSearch={handleSubtopicSearch}
          subtopic={subtopic}
        />
      </div>
    </div>
  );
}

export default App;
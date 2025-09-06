import React from 'react';
import { Link } from 'react-router-dom';

const HowItWorksPage = () => {
  return (
    <div className="how-it-works-page">
      <div className="how-it-works-container">
        {/* Header */}
        <header className="how-it-works-header">
          <h1>How It Works</h1>
          <p className="subtitle">Your Intelligent MCAT Study Assistant</p>
        </header>

        {/* Part 1: The Challenge */}
        <section className="challenge-section">
          <h2>The Perfect Study Plan Meets the Perfect Video Library</h2>
          <p>
            Two of the best free MCAT resources are{' '}
            <a 
              href="https://www.reddit.com/r/Mcat/comments/cckw41/my_anki_deck/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="external-link"
            >
              MileDown's Anki Deck & PDF Notes
            </a>{' '}
            and the official{' '}
            <a 
              href="https://www.khanacademy.org/test-prep/mcat" 
              target="_blank" 
              rel="noopener noreferrer"
              className="external-link"
            >
              Khan Academy MCAT Course
            </a>.
          </p>
          <div className="problem-highlight">
            <h3>The Problem:</h3>
            <p>
              MileDown gives you the perfect roadmap of what to study, but sometimes you need a deeper video explanation. 
              Khan Academy has that explanation, but its course structure doesn't match MileDown's. You're left wasting 
              precious study time searching for the right video, breaking your focus.
            </p>
          </div>
        </section>

        {/* Part 2: The Solution */}
        <section className="solution-section">
          <h2>Never Search. Just Learn.</h2>
          <p>
            This tool acts as your personal research assistant. We've built an intelligent search engine that has 
            already "read" and understood the concepts in every single Khan Academy MCAT video and article.
          </p>
          
          <div className="how-it-works-explanation">
            <h3>The "How":</h3>
            <p>
              When you click a topic from the MileDown list on the left, you're not just searching for keywords. 
              You're asking the system: <em>"Find me the Khan Academy resources that best explain this specific concept."</em> 
              In an instant, it analyzes your request and fetches the most contextually relevant materials, saving you the search.
            </p>
          </div>

          <div className="benefit-highlight">
            <h3>The Benefit:</h3>
            <p>
              The result? You stay focused on what matters: <strong>learning the material, not hunting for it.</strong>
            </p>
          </div>
        </section>

        {/* Part 3: Call to Action */}
        <section className="cta-section">
          <Link to="/" className="back-to-tool-btn">
            Back to the Tool
          </Link>
          <p className="cta-text">Ready to supercharge your MCAT prep? Start studying smarter, not harder.</p>
        </section>
      </div>
    </div>
  );
};

export default HowItWorksPage;

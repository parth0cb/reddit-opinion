import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { jwtDecode } from 'jwt-decode';
import DOMPurify from 'dompurify';
import MarkdownIt from 'markdown-it';
import './App.css';

// Initialize MarkdownIt
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true
});

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [credentials, setCredentials] = useState({
    api_key: '',
    base_url: 'https://api.openai.com/v1',
    model: 'gpt-3.5-turbo'
  });
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState('');
  const [status, setStatus] = useState('');
  const [errorLog, setError] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [tokenUsage, setTokenUsage] = useState({ input_tokens: 0, output_tokens: 0 });
  const [eventSource, setEventSource] = useState(null);

  // check if user is already logged in
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const decoded = jwtDecode(token);
      } catch (error) {
        localStorage.removeItem('token');
      }
    }
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post('http://localhost:8000/auth/login', credentials);
      localStorage.setItem('token', response.data.access_token);
      setIsLoggedIn(true);
    } catch (error) {
      setError('Login failed: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsLoggedIn(false);
    setCredentials({
      api_key: '',
      base_url: 'https://api.openai.com/v1',
      model: 'gpt-3.5-turbo'
    });
  };

  const handleQuerySubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setError('');
    setIsProcessing(true);
    setResponse('');
    setStatus('Starting query processing...');
    setTokenUsage({ input_tokens: 0, output_tokens: 0 });

    const token = localStorage.getItem('token');
    if (!token) {
      setStatus('');
      setIsProcessing(false);
      setIsLoggedIn(false);
      return;
    }

    try {
      // use fetch with streaming for POST requests
      const response = await fetch('http://localhost:8000/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ query: query })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // streaming response
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let done = false;

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        if (value) {
          buffer += decoder.decode(value, { stream: true });

          let lines = buffer.split('\n');
          buffer = lines.pop() || ''; // keep incomplete line

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;

            const dataStr = line.slice(6).trim();

            if (dataStr === '[DONE]') {
              // final token usage comes after [DONE]
              continue;
            }

            try {
              const data = JSON.parse(dataStr);

              switch (data.status) {
                case 'info':
                  setStatus(data.message);
                  break;
                case 'stream':
                  setStatus('');
                  setResponse(prev => prev + data.content);
                  break;
                case 'token_usage':
                  console.log("Token usage update:", data);
                  setTokenUsage({
                    input_tokens: data.input_tokens,
                    output_tokens: data.output_tokens
                  });
                  break;
                case 'cancelled':
                case 'error':
                  setStatus('');
                  setError(data.message);
                  setIsProcessing(false);
                  return;
              }
            } catch (err) {
              console.error('Invalid JSON:', dataStr, err);
              continue; // no crash on malformed data
            }
          }
        }
        done = readerDone;
      }

      // handling of remaining buffer
      if (buffer.startsWith('data: ')) {
        const dataStr = buffer.slice(6).trim();
        if (dataStr !== '[DONE]') {
          try {
            const data = JSON.parse(dataStr);
            if (data.status === 'token_usage') {
              setTokenUsage({
                input_tokens: data.input_tokens,
                output_tokens: data.output_tokens
              });
            }
          } catch (err) {
            console.error('Final JSON parse error:', err);
          }
        }
      }

      setIsProcessing(false);
      setStatus('');
    } catch (error) {
      setStatus('');
      setError('Query failed: ' + (error.message || 'Unknown error'));
      setIsProcessing(false);
    }
  };

  const handleStop = async () => {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
      setStatus('Cancelling...');
      await axios.post('http://localhost:8000/query/stop', {}, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (eventSource) {
        eventSource.close();
        setEventSource(null);
      }
      
      setIsProcessing(false);
    } catch (error) {
      setStatus('Stop request failed: ' + (error.response?.data?.detail || error.message));
    }
  };

  if (!isLoggedIn) {
    return (
      <div className="app">
        <header className="app-header">
          <h1>Reddit Opinion</h1>
        </header>
        <main className="login-container">
          <h2>Enter Your LLM Credentials</h2>
          <form onSubmit={handleLogin} className="login-form">
            <div className="form-group">
              <label htmlFor="api_key">API Key:</label>
              <input
                type="password"
                id="api_key"
                value={credentials.api_key}
                onChange={(e) => setCredentials({...credentials, api_key: e.target.value})}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="base_url">Base URL:</label>
              <input
                type="text"
                id="base_url"
                value={credentials.base_url}
                onChange={(e) => setCredentials({...credentials, base_url: e.target.value})}
              />
            </div>
            <div className="form-group">
              <label htmlFor="model">Model:</label>
              <input
                type="text"
                id="model"
                value={credentials.model}
                onChange={(e) => setCredentials({...credentials, model: e.target.value})}
              />
            </div>
            <button type="submit" className="login-button">Login</button>
          </form>
        </main>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Reddit Opinion</h1>
      </header>
      <main className="query-container">
        <button onClick={handleLogout} className="change-lm-button">Change Language Model</button>
        <form onSubmit={handleQuerySubmit} className="query-form">
          <div className="form-group">
            <label htmlFor="query">Your question:</label>
            <textarea
              id="query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., 'what are best practices for remote work?', 'what are latest trends in AI?'"
              disabled={isProcessing}
              rows="3"
            />
          </div>
          <div className="button-group">
          {isProcessing ? (
            <button type="button" onClick={handleStop} className="stop-button">
              x
            </button>
          ) : (
            <button type="submit" className="submit-button">
              {'>'}
            </button>
          )}
          </div>
        </form>
                
          <div className="token-usage">
            <span>Input Tokens: {tokenUsage.input_tokens}</span>
            <span>Output Tokens: {tokenUsage.output_tokens}</span>
          </div>

        {status && <div className='status-wrapper'> <div className='spinner'></div><div className="status-message">{status}</div> </div>}

        {errorLog && <div className="error-message">{errorLog}</div>}
        
        {response && (
          <div className="response-container">
            <div
              className="response-content"
              dangerouslySetInnerHTML={{
                __html: DOMPurify.sanitize(
                  md.render(preprocessResponse(response)),
                  { ADD_ATTR: ['target', 'rel'] }
                )
              }}
            />
          </div>
        )}
      </main>
    </div>
  );
}

function preprocessResponse(text) {
  return text.replace(/\[Source:\s*(https?:\/\/[^\]\s]+)\]/gi, (match, url) => {
    try {
      const parsedUrl = new URL(url);
      const domain = parsedUrl.hostname.replace(/^www\./, '');

      if (domain === 'reddit.com') {
        const pathParts = parsedUrl.pathname.split('/');
        const subredditIndex = pathParts.findIndex(part => part.toLowerCase() === 'r');
        if (subredditIndex !== -1 && pathParts.length > subredditIndex + 1) {
          const subreddit = pathParts[subredditIndex + 1];
          return `<a href="${url}" class="citation-link" target="_blank" rel="noopener noreferrer">r/${subreddit}</a>`;
        }
      }

      return `<a href="${url}" class="citation-link" target="_blank" rel="noopener noreferrer">${domain}</a>`;
    } catch (err) {
      return match;
    }
  });
}

export default App;

import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
    Upload,
    Send,
    FileText,
    Trash2,
    TrendingUp,
    MessageSquare,
    X,
    BarChart,
    Award,
    CheckCircle,
    Check
} from 'lucide-react';
import './App.css';

// API Configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

function App() {
    // State Management
    const [papers, setPapers] = useState([]);
    const [selectedPapers, setSelectedPapers] = useState([]); // Changed to array
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [popularPapers, setPopularPapers] = useState([]);
    const [showStats, setShowStats] = useState(false);
    const [currentStats, setCurrentStats] = useState(null);
    const [error, setError] = useState(null);
    const [successMessage, setSuccessMessage] = useState(null);
    const [queryCounter, setQueryCounter] = useState(0);
    const [rawResponses, setRawResponses] = useState({
        upload: null,
        papers: null,
        stats: null,
        query: null,
        popular: null,
        delete: null
    });
    const [showDebug, setShowDebug] = useState(true);
    const messagesEndRef = useRef(null);
    const fileInputRef = useRef(null);
    const [responseTime, setResponseTime] = useState(null); // Add this
    const [popularTopicsSummary, setPopularTopicsSummary] = useState('');
    const [paperStatsSummaries, setPaperStatsSummaries] = useState({}); // { paper_id: summary }
    const [hoveredPaper, setHoveredPaper] = useState(null);
    const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
    // Fetch papers on mount
    useEffect(() => {
        fetchPapers();
        fetchPopularPapers();
    }, []);

    // Auto-scroll to bottom of messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Auto-clear success message after 3 seconds
    useEffect(() => {
        if (successMessage) {
            const timer = setTimeout(() => {
                setSuccessMessage(null);
            }, 3000);
            return () => clearTimeout(timer);
        }
    }, [successMessage]);

    // API Functions
    const fetchPapers = async () => {
        try {
            console.log('🔍 Fetching papers from:', `${API_BASE_URL}/papers`);
            const response = await axios.get(`${API_BASE_URL}/papers`);
            console.log('✅ Papers fetched:', response.data);
            setRawResponses(prev => ({ ...prev, papers: response.data }));
            setPapers(response.data);
        } catch (err) {
            console.error('❌ Error fetching papers:', err);
            console.error('Error response:', err.response);
            setRawResponses(prev => ({ ...prev, papers: { error: err.message, details: err.response?.data } }));
            setError('Failed to load papers');
        }
    };

    const fetchPopularPapers = async () => {
        try {
            console.log('🔍 Fetching popular papers');
            const response = await axios.get(`${API_BASE_URL}/analytics/popular?days=30&limit=3`);
            console.log('✅ Popular papers fetched:', response.data);
            setRawResponses(prev => ({ ...prev, popular: response.data }));

            // Handle new response format
            if (response.data.topics) {
                setPopularPapers(response.data.topics);
            } else {
                setPopularPapers(response.data);
            }

            // Store summary
            if (response.data.summary) {
                setPopularTopicsSummary(response.data.summary);
            }
        } catch (err) {
            console.error('❌ Error fetching popular papers:', err);
            setRawResponses(prev => ({ ...prev, popular: { error: err.message, details: err.response?.data } }));
        }
    };
    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        setIsUploading(true);
        setError(null);
        setSuccessMessage(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            console.log('📤 Uploading file:', file.name);
            const response = await axios.post(`${API_BASE_URL}/papers/upload`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            console.log('✅ Upload successful:', response.data);
            setRawResponses(prev => ({ ...prev, upload: response.data }));
            setSuccessMessage(`✅ Successfully uploaded: ${file.name}`);

            await fetchPapers();
            await fetchPopularPapers();

            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        } catch (err) {
            console.error('❌ Upload Error:', err);
            console.error('Error response:', err.response?.data);
            setRawResponses(prev => ({ ...prev, upload: { error: err.message, details: err.response?.data } }));
            setError(err.response?.data?.detail || 'Failed to upload file');
        } finally {
            setIsUploading(false);
        }
    };

    const handleDeletePaper = async (paperId, event) => {
        event.stopPropagation();

        if (!window.confirm('Are you sure you want to delete this paper?')) {
            return;
        }

        try {
            console.log('🗑️ Deleting paper with ID:', paperId);
            const response = await axios.delete(`${API_BASE_URL}/papers/${paperId}`);
            setRawResponses(prev => ({ ...prev, delete: response.data }));
            setSuccessMessage('✅ Paper deleted successfully');

            await fetchPapers();
            await fetchPopularPapers();

            // Remove from selected papers if it was selected
            setSelectedPapers(prev => prev.filter(p => p.file_name !== paperId));
        } catch (err) {
            console.error('❌ Error deleting paper:', err);
            setRawResponses(prev => ({ ...prev, delete: { error: err.message, details: err.response?.data } }));
            setError('Failed to delete paper');
        }
    };

    const fetchPaperStats = async (paperId) => {
        try {
            console.log('📊 Fetching stats for paper:', paperId);
            const response = await axios.get(`${API_BASE_URL}/papers/${paperId}/stats`);
            console.log('✅ Stats fetched:', response.data);
            setRawResponses(prev => ({ ...prev, stats: response.data }));

            // Handle new response format
            if (response.data.stats) {
                setCurrentStats(response.data.stats);
            } else {
                setCurrentStats(response.data);
            }

            // Store summary for tooltip
            if (response.data.summary) {
                setPaperStatsSummaries(prev => ({
                    ...prev,
                    [paperId]: response.data.summary
                }));
            }

            setShowStats(true);
        } catch (err) {
            console.error('❌ Error fetching stats:', err);
            console.error('Error response:', err.response);
            setRawResponses(prev => ({ ...prev, stats: { error: err.message, details: err.response?.data } }));
            if (err.response?.status !== 404) {
                setError('Failed to load paper statistics');
            }
        }
    };


    const handlePaperHover = async (paper, event) => {
        setHoveredPaper(paper.file_name);

        // Update tooltip position
        const rect = event.currentTarget.getBoundingClientRect();
        setTooltipPosition({
            x: rect.left + rect.width / 2,
            y: rect.top - 10
        });

        // Fetch stats if not already cached
        if (!paperStatsSummaries[paper.file_name]) {
            try {
                const response = await axios.get(`${API_BASE_URL}/papers/${paper.file_name}/stats`);
                if (response.data.summary) {
                    setPaperStatsSummaries(prev => ({
                        ...prev,
                        [paper.file_name]: response.data.summary
                    }));
                }
            } catch (err) {
                console.error('Failed to fetch stats for tooltip:', err);
            }
        }
    };

    const handlePaperLeave = () => {
        setHoveredPaper(null);
    };

    const handlePaperClick = (paper) => {
        // Toggle paper selection
        setSelectedPapers(prev => {
            const isSelected = prev.some(p => p.file_name === paper.file_name);
            if (isSelected) {
                // Deselect
                return prev.filter(p => p.file_name !== paper.file_name);
            } else {
                // Select
                return [...prev, paper];
            }
        });
    };

    const handleSendMessage = async () => {
        if (!inputValue.trim() || isLoading) return;

        if (selectedPapers.length === 0) {
            setError('Please select at least one paper before asking a question');
            return;
        }

        // Increment query counter
        const currentQueryId = queryCounter + 1;
        setQueryCounter(currentQueryId);

        const userMessage = {
            role: 'user',
            content: inputValue,
            selectedPapers: selectedPapers.map(p => p.file_name),
            timestamp: new Date().toISOString(), // Add timestamp
        };

        setMessages(prev => [...prev, userMessage]);
        setInputValue('');
        setIsLoading(true);
        setError(null);

        const startTime = performance.now(); // Track start time

        try {
            const requestData = {
                id: currentQueryId,
                question: inputValue,
                expected_papers: selectedPapers.map(p => p.file_name),
                difficulty: "medium",
                type: selectedPapers.length === 1 ? "single-paper" : "multi-paper"
            };

            console.log('💬 Sending query:', requestData);
            const response = await axios.post(`${API_BASE_URL}/query`, requestData);
            console.log('✅ Query response:', response.data);

            const endTime = performance.now(); // Track end time
            const responseTimeMs = endTime - startTime;

            setRawResponses(prev => ({ ...prev, query: response.data }));

            const assistantMessage = {
                role: 'assistant',
                content: response.data.answer,
                responseTime: (responseTimeMs / 1000).toFixed(2), // Convert to seconds
                timestamp: new Date().toISOString(),
            };

            setMessages(prev => [...prev, assistantMessage]);
            fetchPopularPapers().catch(err => console.log('Popular papers fetch failed (ignored):', err));

        } catch (err) {
            console.error('❌ Query Error:', err);
            console.error('Error response:', err.response?.data);

            const endTime = performance.now();
            const responseTimeMs = endTime - startTime;

            let errorMessage = 'Failed to process your question';

            if (err.response?.data) {
                const errorData = err.response.data;

                if (Array.isArray(errorData.detail)) {
                    errorMessage = errorData.detail.map(e => `${e.loc?.join('.')}: ${e.msg}`).join(', ');
                }
                else if (typeof errorData.detail === 'string') {
                    errorMessage = errorData.detail;
                }
                else if (typeof errorData.detail === 'object') {
                    errorMessage = JSON.stringify(errorData.detail);
                }
            }

            setRawResponses(prev => ({
                ...prev,
                query: {
                    error: err.message,
                    status: err.response?.status,
                    details: err.response?.data
                }
            }));

            setError(errorMessage);

            const errorMsgObj = {
                role: 'assistant',
                content: 'Sorry, I encountered an error processing your question. Please try again.',
                responseTime: (responseTimeMs / 1000).toFixed(2),
                timestamp: new Date().toISOString(),
            };
            setMessages(prev => [...prev, errorMsgObj]);
        } finally {
            setIsLoading(false);
        }
    };
    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    const clearSelectedPapers = () => {
        setSelectedPapers([]);
    };

    const isPaperSelected = (paper) => {
        return selectedPapers.some(p => p.file_name === paper.file_name);
    };

    return (
        <div className="app-container">
            {/* Left Sidebar - Papers */}
            <aside className="sidebar left-sidebar">
                {/* Header */}
                <div className="sidebar-header">
                    <h1>Research Assistant</h1>
                    <p>RAG-powered paper analysis</p>
                </div>

                {/* Upload Section */}
                <div className="upload-section">
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept=".pdf"
                        onChange={handleFileUpload}
                        className="file-input"
                        id="file-upload"
                    />
                    <label htmlFor="file-upload">
                        <button
                            className="upload-button"
                            disabled={isUploading}
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <Upload size={18} />
                            {isUploading ? 'Uploading...' : 'Upload PDF'}
                        </button>
                    </label>
                </div>

                {/* Success Message */}
                {successMessage && (
                    <div className="success-banner">
                        <CheckCircle size={16} />
                        {successMessage}
                    </div>
                )}

                {/* Selected Papers Section */}
                {selectedPapers.length > 0 && (
                    <div className="selected-papers-section">
                        <div className="selected-header">
                            <h3>📎 Selected Papers ({selectedPapers.length})</h3>
                            <button className="clear-selection" onClick={clearSelectedPapers} title="Clear selection">
                                <X size={14} />
                            </button>
                        </div>
                        <div className="selected-papers-list">
                            {selectedPapers.map(paper => (
                                <div key={paper.file_name} className="selected-paper-chip">
                                    <Check size={12} />
                                    <span>{paper.file_name}</span>
                                    <button
                                        className="remove-chip"
                                        onClick={() => handlePaperClick(paper)}
                                    >
                                        <X size={12} />
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Papers List */}
                <div className="papers-list">
                    <h3>📚 All Papers ({papers.length})</h3>
                    {papers.length === 0 ? (
                        <p style={{ fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center', marginTop: '20px' }}>
                            No papers uploaded yet
                        </p>
                    ) : (
                        papers.map(paper => (
                            <div
                                key={paper.file_name}
                                className={`paper-item ${isPaperSelected(paper) ? 'selected' : ''}`}
                                onClick={() => handlePaperClick(paper)}
                                onMouseEnter={(e) => handlePaperHover(paper, e)}
                                onMouseLeave={handlePaperLeave}
                            >
                                <div className="paper-info">
                                    <div className="paper-name">
                                        {isPaperSelected(paper) ? (
                                            <CheckCircle size={14} style={{ display: 'inline', marginRight: '6px', color: 'var(--accent-green)' }} />
                                        ) : (
                                            <FileText size={14} style={{ display: 'inline', marginRight: '6px' }} />
                                        )}
                                        {paper.file_name}
                                    </div>
                                    <div className="paper-meta">
                                        <span>{paper.page_count} pages</span>
                                        <span>{paper.vector_count} vectors</span>
                                    </div>
                                </div>
                                <button
                                    className="delete-button"
                                    onClick={(e) => handleDeletePaper(paper.file_name, e)}
                                    title="Delete paper"
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        ))
                    )}
                </div>

                {/* Tooltip Portal */}
                {hoveredPaper && paperStatsSummaries[hoveredPaper] && (
                    <div
                        className="paper-tooltip"
                        style={{
                            left: `${tooltipPosition.x}px`,
                            top: `${tooltipPosition.y}px`,
                        }}
                    >
                        <div className="tooltip-arrow"></div>
                        <div className="tooltip-content">
                            <strong>{hoveredPaper}</strong>
                            <p>{paperStatsSummaries[hoveredPaper]}</p>
                        </div>
                    </div>
                )}
            </aside>

            {/* Main Content - Chat */}
            <main className="main-content">
                {/* Header */}
                <div className="main-header">
                    <h2>
                        {selectedPapers.length > 0
                            ? `Chatting about: ${selectedPapers.map(p => p.file_name).join(', ')}`
                            : 'Select papers to start chatting'}
                    </h2>
                    <div className="header-actions">
                        {selectedPapers.length > 0 && (
                            <button
                                className="icon-button"
                                onClick={clearSelectedPapers}
                                title="Clear selection"
                            >
                                <X size={18} />
                            </button>
                        )}
                    </div>
                </div>

                {/* Chat Container */}
                <div className="chat-container">
                    {/* Messages */}
                    <div className="messages-container">
                        {error && (
                            <div className="error-banner">
                                <X size={16} />
                                {error}
                            </div>
                        )}

                        {messages.length === 0 ? (
                            <div className="empty-state">
                                <MessageSquare size={64} />
                                <h3>Start a Conversation</h3>
                                <p>
                                    {selectedPapers.length === 0
                                        ? 'Select at least one paper from the sidebar to begin'
                                        : 'Ask questions about your selected papers'}
                                </p>
                            </div>
                        ) : (
                            messages.map((message, index) => (
                                <div key={index} className={`message ${message.role}`}>
                                    <div className="message-header">
                                        <span className="message-role">
                                            {message.role === 'user' ? '👤 You' : '🤖 Assistant'}
                                        </span>
                                        {message.selectedPapers && (
                                            <span className="message-papers">
                                                📎 {message.selectedPapers.join(', ')}
                                            </span>
                                        )}
                                    </div>
                                    <div className="message-content">
                                        {message.content}

                                        {/* Response Time - Only for assistant messages */}
                                        {message.role === 'assistant' && message.responseTime && (
                                            <div className="response-time">
                                                ⏱️ Response time: {message.responseTime}s
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))
                        )}

                        {isLoading && (
                            <div className="loading-message">
                                <div className="loading-spinner"></div>
                                <span>Thinking...</span>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input Section */}
                    <div className="input-section">
                        {selectedPapers.length === 0 && (
                            <div className="input-warning">
                                ⚠️ Please select at least one paper from the sidebar before asking questions
                            </div>
                        )}
                        <div className="input-wrapper">
                            <div className="input-container">
                                <textarea
                                    className="chat-input"
                                    placeholder={
                                        selectedPapers.length === 0
                                            ? "Select papers first..."
                                            : selectedPapers.length === 1
                                                ? `Ask about ${selectedPapers[0].file_name}...`
                                                : `Ask about ${selectedPapers.length} selected papers...`
                                    }
                                    value={inputValue}
                                    onChange={(e) => setInputValue(e.target.value)}
                                    onKeyPress={handleKeyPress}
                                    rows={1}
                                    disabled={isLoading || selectedPapers.length === 0}
                                />
                            </div>
                            <button
                                className="send-button"
                                onClick={handleSendMessage}
                                disabled={!inputValue.trim() || isLoading || selectedPapers.length === 0}
                            >
                                <Send size={18} />
                                Send
                            </button>
                        </div>
                    </div>
                </div>
            </main>

            {/* Right Sidebar - Analytics */}
            <aside className="sidebar right-sidebar">
                <div className="analytics-panel">
                    {/* <h2>📊 Analytics</h2>

                    Analytics Summary
                    {popularTopicsSummary && (
                        <div className="analytics-section">
                            <h3>💡 Insights</h3>
                            <div className="summary-card">
                                <p>{popularTopicsSummary}</p>
                            </div>
                        </div>
                    )} */}

                    {/* Popular Questions */}
                    {popularPapers.length > 0 && (
                        <div className="analytics-section">
                            <h3>🔥 Most Popular Questions</h3>
                            <div className="popular-questions-list">
                                {popularPapers.map((item, index) => (
                                    <div key={index} className="popular-question-card">
                                        <div className="question-header">
                                            {index === 0 && <Award size={16} className="trophy-icon" />}
                                            <span className="question-rank">#{index + 1}</span>
                                        </div>
                                        <div className="question-text">
                                            {item.topic}
                                        </div>
                                        <div className="question-stats">
                                            <span className="stat-badge">
                                                <MessageSquare size={12} />
                                                {item.query_count} queries
                                            </span>
                                            <span className="stat-badge">
                                                <TrendingUp size={12} />
                                                {item.avg_response_time?.toFixed(2)}s
                                            </span>
                                            <span className="stat-badge success">
                                                ✓ {(item.success_rate * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Paper Stats (if viewing) */}
                    {showStats && currentStats && (
                        <div className="analytics-section">
                            <div className="section-header">
                                <h3>📄 Paper Statistics</h3>
                                <button className="close-stats" onClick={() => setShowStats(false)}>
                                    <X size={16} />
                                </button>
                            </div>
                            <div className="stats-grid">
                                <div className="stat-box">
                                    <div className="stat-label">Total Queries</div>
                                    <div className="stat-value">{currentStats.total_queries}</div>
                                </div>
                                <div className="stat-box">
                                    <div className="stat-label">Citations</div>
                                    <div className="stat-value">{currentStats.total_citations}</div>
                                </div>
                                <div className="stat-box">
                                    <div className="stat-label">Avg Relevance</div>
                                    <div className="stat-value">{currentStats.avg_relevance_score?.toFixed(2)}</div>
                                </div>
                                <div className="stat-box">
                                    <div className="stat-label">Last Query</div>
                                    <div className="stat-value" style={{ fontSize: '11px' }}>
                                        {currentStats.last_queried ? new Date(currentStats.last_queried).toLocaleDateString() : 'N/A'}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </aside>
        </div>
    );
}

export default App;
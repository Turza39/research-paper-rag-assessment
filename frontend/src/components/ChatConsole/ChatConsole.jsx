import React, { useState, useRef, useEffect } from 'react';
import { Send, AlertCircle, Loader, Sparkles, BookOpen, FileText } from 'lucide-react';
import './ChatConsole.css';

function ChatConsole({
    messages,
    isLoading,
    chatMode,
    activeResearch,
    papers,
    researches,
    onSendMessage
}) {
    const [inputValue, setInputValue] = useState('');
    const messagesEndRef = useRef(null);
    const textareaRef = useRef(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            const newHeight = Math.min(textareaRef.current.scrollHeight, 200);
            textareaRef.current.style.height = newHeight + 'px';
        }
    }, [inputValue]);

    const handleSendMessage = () => {
        if (!inputValue.trim() || isLoading) return;

        let selectedPapers = [];

        if (chatMode === 'research' && activeResearch) {
            selectedPapers = activeResearch.papers;
        }

        onSendMessage(inputValue, selectedPapers);
        setInputValue('');
        
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    const getContextInfo = () => {
        if (chatMode === 'general') {
            return {
                title: 'General Chat',
                description: 'Ask me anything',
                icon: '💬',
                papers: []
            };
        }

        if (activeResearch) {
            return {
                title: activeResearch.name,
                description: `${activeResearch.papers.length} paper${activeResearch.papers.length !== 1 ? 's' : ''} selected`,
                icon: '🔬',
                papers: activeResearch.papers
            };
        }

        return {
            title: 'Research Assistant',
            description: 'Select a research topic to begin',
            icon: '📚',
            papers: []
        };
    };

    const contextInfo = getContextInfo();
    const canSendMessage = chatMode === 'general' || (chatMode === 'research' && activeResearch && activeResearch.papers.length > 0);

    return (
        <div className="chat-console">
            <div className="messages-wrapper">
                {messages.length === 0 ? (
                    <div className="empty-chat-state">
                        <div className="empty-content">
                            <div className="empty-icon-large">{contextInfo.icon}</div>
                            <h2>{contextInfo.title}</h2>
                            <p className="empty-description">
                                {chatMode === 'general'
                                    ? 'Start a conversation with the AI assistant. Ask questions, explore ideas, or discuss research topics.'
                                    : activeResearch
                                        ? `Ready to discuss ${activeResearch.name}. Ask questions about the attached papers.`
                                        : 'Select a research topic from the sidebar to start analyzing papers with AI assistance.'}
                            </p>
                            {chatMode === 'research' && activeResearch && activeResearch.papers.length === 0 && (
                                <div className="empty-warning">
                                    <AlertCircle size={18} />
                                    <span>Add papers to this research topic to enable AI analysis</span>
                                </div>
                            )}
                            {contextInfo.papers.length > 0 && (
                                <div className="context-papers">
                                    <div className="papers-label">Selected Papers:</div>
                                    <div className="papers-list-inline">
                                        {contextInfo.papers.map((paper, index) => (
                                            <span key={index} className="paper-chip">{paper}</span>
                                        ))}
                                    </div>
                                </div>
                            )}
                            <div className="suggestions">
                                <div className="suggestions-title">Suggestions:</div>
                                <div className="suggestion-cards">
                                    {chatMode === 'general' ? (
                                        <>
                                            <div className="suggestion-card">
                                                <span className="suggestion-icon">💡</span>
                                                <span>Explain research methodologies</span>
                                            </div>
                                            <div className="suggestion-card">
                                                <span className="suggestion-icon">📊</span>
                                                <span>Compare different approaches</span>
                                            </div>
                                            <div className="suggestion-card">
                                                <span className="suggestion-icon">✨</span>
                                                <span>Brainstorm research ideas</span>
                                            </div>
                                        </>
                                    ) : (
                                        <>
                                            <div className="suggestion-card">
                                                <span className="suggestion-icon">📝</span>
                                                <span>Summarize key findings</span>
                                            </div>
                                            <div className="suggestion-card">
                                                <span className="suggestion-icon">🔍</span>
                                                <span>Compare methodologies</span>
                                            </div>
                                            <div className="suggestion-card">
                                                <span className="suggestion-icon">💭</span>
                                                <span>Generate research questions</span>
                                            </div>
                                        </>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="messages-container">
                        {messages.map((message, index) => (
                            <div key={index} className={`message-row ${message.role}`}>
                                <div className="message-content-wrapper">
                                    <div className="message-avatar">
                                        {message.role === 'user' ? (
                                            <div className="avatar-user">You</div>
                                        ) : (
                                            <div className="avatar-assistant">
                                                <Sparkles size={16} />
                                            </div>
                                        )}
                                    </div>
                                    <div className="message-content">
                                        <div className="message-text">
                                            {message.content}
                                        </div>
                                        
                                        {/* ✅ Display Citations */}
                                        {message.citations && message.citations.length > 0 && (
                                            <div className="message-citations">
                                                <div className="citations-header">
                                                    <BookOpen size={14} />
                                                    <span>References:</span>
                                                </div>
                                                <div className="citations-list">
                                                    {message.citations.map((citation, citIndex) => (
                                                        <div key={citIndex} className="citation-item">
                                                            <div className="citation-content">
                                                                <div className="citation-paper">
                                                                    <FileText size={13} />
                                                                    <span className="citation-title">
                                                                        {citation.paper_title}
                                                                    </span>
                                                                </div>
                                                                <div className="citation-details">
                                                                    <span className="citation-section">
                                                                        {citation.section}
                                                                    </span>
                                                                    <span className="citation-page">
                                                                        Page {citation.page}
                                                                    </span>
                                                                    <span className="citation-score">
                                                                        Relevance: {(citation.relevance_score * 100).toFixed(0)}%
                                                                    </span>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                        
                                        {message.responseTime && (
                                            <div className="message-footer">
                                                <span className="response-time">
                                                    ⏱️ Response: {message.response_time_ms ? `${message.response_time_ms.toFixed(0)}ms` : `${message.responseTime}s`}
                                                </span>
                                                {message.timestamp && (
                                                    <span className="message-timestamp">
                                                        📅 {new Date(message.timestamp).toLocaleString()}
                                                    </span>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}

                        {isLoading && (
                            <div className="message-row assistant">
                                <div className="message-content-wrapper">
                                    <div className="message-avatar">
                                        <div className="avatar-assistant">
                                            <Sparkles size={16} />
                                        </div>
                                    </div>
                                    <div className="message-content">
                                        <div className="typing-indicator">
                                            <span></span>
                                            <span></span>
                                            <span></span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>
                )}
            </div>

            <div className="input-section">
                <div className="input-container-wrapper">
                    {!canSendMessage && (
                        <div className="input-disabled-overlay">
                            <AlertCircle size={18} />
                            <span>
                                {chatMode === 'research'
                                    ? activeResearch
                                        ? 'Add papers to start chatting'
                                        : 'Select a research topic to start'
                                    : 'Chat unavailable'}
                            </span>
                        </div>
                    )}
                    
                    <div className={`input-box ${!canSendMessage ? 'disabled' : ''}`}>
                        <textarea
                            ref={textareaRef}
                            className="message-input"
                            placeholder="Message Research Assistant..."
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyDown={handleKeyPress}
                            disabled={!canSendMessage || isLoading}
                            rows={1}
                        />
                        <button
                            className={`send-btn ${inputValue.trim() && canSendMessage && !isLoading ? 'active' : ''}`}
                            onClick={handleSendMessage}
                            disabled={!inputValue.trim() || !canSendMessage || isLoading}
                        >
                            {isLoading ? (
                                <Loader size={20} className="spinner" />
                            ) : (
                                <Send size={20} />
                            )}
                        </button>
                    </div>
                    
                    <div className="input-footer">
                        <span className="context-indicator">
                            {contextInfo.icon} {contextInfo.title}
                        </span>
                        {contextInfo.papers.length > 0 && (
                            <span className="papers-count">
                                · {contextInfo.papers.length} paper{contextInfo.papers.length !== 1 ? 's' : ''}
                            </span>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default ChatConsole;
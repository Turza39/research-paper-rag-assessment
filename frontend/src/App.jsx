import React, { useState, useEffect } from 'react';
import axios from 'axios';
import LeftSidebar from './components/LeftSidebar/LeftSidebar';
import ChatConsole from './components/ChatConsole/ChatConsole';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

function App() {
    // Global State
    const [papers, setPapers] = useState([]);
    const [researches, setResearches] = useState([]);
    const [activeResearch, setActiveResearch] = useState(null);
    const [chatMode, setChatMode] = useState('general');
    const [messages, setMessages] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [queryCounter, setQueryCounter] = useState(0);

    // Fetch papers on mount
    useEffect(() => {
        fetchPapers();
        loadResearches();
    }, []);

    // Load chat history when mode changes
    useEffect(() => {
        loadChatHistory();
    }, [chatMode, activeResearch]);

    const fetchPapers = async () => {
        try {
            const response = await axios.get(`${API_BASE_URL}/papers`);
            console.log('✅ Papers fetched:', response.data);
            setPapers(response.data);
        } catch (err) {
            console.error('❌ Error fetching papers:', err);
        }
    };

    const loadResearches = () => {
        const saved = localStorage.getItem('researches');
        if (saved) {
            setResearches(JSON.parse(saved));
        }
    };

    const saveResearches = (newResearches) => {
        setResearches(newResearches);
        localStorage.setItem('researches', JSON.stringify(newResearches));
    };

    const loadChatHistory = async () => {
        setMessages([]);

        try {
            if (chatMode === 'general') {
                console.log('📥 Loading general chat history...');

                try {
                    const response = await axios.get(
                        `${API_BASE_URL}/chat/general/history`,
                        {
                            params: { limit: 50, skip: 0 },
                            timeout: 10000
                        }
                    );

                    console.log('✅ General chat history loaded:', response.data);

                    if (Array.isArray(response.data) && response.data.length > 0) {
                        const formattedMessages = response.data.flatMap(entry => {
                            const userMsg = {
                                role: 'user',
                                content: entry.question,
                                timestamp: entry.timestamp,
                            };

                            const assistantMsg = {
                                role: 'assistant',
                                content: entry.answer,
                                responseTime: entry.response_time?.toFixed(2),
                                timestamp: entry.timestamp,
                                entryId: entry.id,
                            };

                            return [userMsg, assistantMsg];
                        });

                        setMessages(formattedMessages);
                    } else {
                        console.log('ℹ️ No general chat history found');
                        setMessages([]);
                    }
                } catch (err) {
                    console.error('❌ Error loading general chat history:', err.message);
                    setMessages([]);
                }
            } else if (chatMode === 'research' && activeResearch) {
                console.log(`📥 Loading research chat history for: ${activeResearch.id}`);

                try {
                    const response = await axios.get(
                        `${API_BASE_URL}/research/${activeResearch.id}/chat-history`,
                        {
                            params: { limit: 50, skip: 0 },
                            timeout: 10000
                        }
                    );

                    console.log('✅ Research chat history loaded:', response.data);

                    if (Array.isArray(response.data) && response.data.length > 0) {
                        const formattedMessages = response.data.flatMap(entry => {
                            const userMsg = {
                                role: 'user',
                                content: entry.question,
                                timestamp: entry.timestamp,
                            };

                            const assistantMsg = {
                                role: 'assistant',
                                content: entry.answer,
                                responseTime: entry.response_time?.toFixed(2),
                                timestamp: entry.timestamp,
                                citations: entry.citations || [],
                                papers_referenced: entry.papers_referenced || [],
                                entryId: entry.id,
                            };

                            return [userMsg, assistantMsg];
                        });

                        setMessages(formattedMessages);
                    } else {
                        console.log('ℹ️ No chat history found for this research');
                        setMessages([]);
                    }
                } catch (err) {
                    console.error('❌ Error loading research chat history:', err.message);
                    setMessages([]);
                }
            }
        } catch (err) {
            console.error('❌ Unexpected error in loadChatHistory:', err);
            setMessages([]);
        }
    };
    const handleFileUpload = async (file) => {
        const formData = new FormData();
        formData.append('file', file);

        try {
            console.log('📤 Uploading file:', file.name);
            await axios.post(`${API_BASE_URL}/papers/upload`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            console.log('✅ Upload successful');
            await fetchPapers();
            return { success: true };
        } catch (err) {
            console.error('❌ Upload error:', err);
            return { success: false, error: err.response?.data?.detail || 'Upload failed' };
        }
    };

    const handleDeletePaper = async (paperId) => {
        try {
            console.log('🗑️ Deleting paper:', paperId);
            await axios.delete(`${API_BASE_URL}/papers/${paperId}`);
            await fetchPapers();

            // Remove from all researches
            const updatedResearches = researches.map(research => ({
                ...research,
                papers: research.papers.filter(p => p !== paperId)
            }));
            saveResearches(updatedResearches);

            return { success: true };
        } catch (err) {
            console.error('❌ Delete error:', err);
            return { success: false, error: 'Delete failed' };
        }
    };

    const handleDeleteChatHistory = async () => {
        if (chatMode === 'research' && activeResearch) {
            if (!window.confirm(`Delete all chat history for "${activeResearch.name}"? This cannot be undone.`)) {
                return { success: false };
            }

            try {
                console.log(`🗑️ Deleting research chat history for: ${activeResearch.id}`);
                const response = await axios.delete(
                    `${API_BASE_URL}/research/${activeResearch.id}/chat-history`,
                    { data: { confirm: true } }
                );

                console.log('✅ Research chat history deleted:', response.data);
                setMessages([]);
                return { success: true, message: response.data.message };
            } catch (err) {
                console.error('❌ Error deleting research chat history:', err);
                return { success: false, error: 'Failed to delete chat history' };
            }
        }
        return { success: false };
    };

    const handleSendMessage = async (message, selectedPapers) => {
        setIsLoading(true);

        const currentQueryId = queryCounter + 1;
        setQueryCounter(currentQueryId);

        const userMessage = {
            role: 'user',
            content: message,
            timestamp: new Date().toISOString(),
        };
        setMessages(prev => [...prev, userMessage]);

        const startTime = performance.now();

        try {
            if (chatMode === 'general') {
                // ✅ General Chat - queries all papers
                console.log('📤 Sending general chat message:', message);

                const response = await axios.post(`${API_BASE_URL}/query`, {
                    id: currentQueryId,
                    question: message,
                    expected_papers: papers.map(p => p.file_name), // All papers
                    difficulty: "medium",
                    type: "multi-paper"
                });

                const endTime = performance.now();
                const responseTimeMs = endTime - startTime;

                console.log('✅ General chat response:', response.data);

                const assistantMessage = {
                    role: 'assistant',
                    content: response.data.answer,
                    responseTime: (responseTimeMs / 1000).toFixed(2),
                    timestamp: new Date().toISOString(),
                    citations: response.data.citations,
                    sources_used: response.data.sources_used,
                };
                setMessages(prev => [...prev, assistantMessage]);

            } else {
                // ✅ Research Chat
                const paperFileNames = Array.isArray(selectedPapers)
                    ? selectedPapers.filter(p => typeof p === 'string')
                    : [];

                console.log('📤 Sending research query:', {
                    id: currentQueryId,
                    question: message,
                    research_id: activeResearch?.id,
                    research_name: activeResearch?.name,
                    expected_papers: paperFileNames,
                });

                const response = await axios.post(`${API_BASE_URL}/query`, {
                    id: currentQueryId,
                    question: message,
                    research_id: activeResearch?.id,
                    research_name: activeResearch?.name,
                    expected_papers: paperFileNames,
                    difficulty: "medium",
                    type: paperFileNames.length === 1 ? "single-paper" : "multi-paper"
                });

                const endTime = performance.now();
                const responseTimeMs = endTime - startTime;

                console.log('✅ Query response:', response.data);

                const assistantMessage = {
                    role: 'assistant',
                    content: response.data.answer,
                    responseTime: (responseTimeMs / 1000).toFixed(2),
                    timestamp: new Date().toISOString(),
                    citations: response.data.citations,
                    sources_used: response.data.sources_used,
                };
                setMessages(prev => [...prev, assistantMessage]);
            }

        } catch (err) {
            console.error('❌ Query Error:', err);
            console.error('Error details:', err.response?.data);

            const endTime = performance.now();
            const responseTimeMs = endTime - startTime;

            let errorMessage = 'Sorry, I encountered an error processing your question.';

            if (err.response?.data?.detail) {
                if (Array.isArray(err.response.data.detail)) {
                    errorMessage = err.response.data.detail.map(e =>
                        `${e.loc?.join('.')}: ${e.msg}`
                    ).join(', ');
                } else if (typeof err.response.data.detail === 'string') {
                    errorMessage = err.response.data.detail;
                }
            }

            const errorMsgObj = {
                role: 'assistant',
                content: errorMessage,
                responseTime: (responseTimeMs / 1000).toFixed(2),
                timestamp: new Date().toISOString(),
            };
            setMessages(prev => [...prev, errorMsgObj]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="app-container">
            <LeftSidebar
                papers={papers}
                researches={researches}
                activeResearch={activeResearch}
                chatMode={chatMode}
                onFileUpload={handleFileUpload}
                onDeletePaper={handleDeletePaper}
                onResearchesChange={saveResearches}
                onActiveResearchChange={setActiveResearch}
                onChatModeChange={setChatMode}
                onMessagesReset={() => setMessages([])}
                onDeleteChatHistory={handleDeleteChatHistory}
            />
            <ChatConsole
                messages={messages}
                isLoading={isLoading}
                chatMode={chatMode}
                activeResearch={activeResearch}
                papers={papers}
                researches={researches}
                onSendMessage={handleSendMessage}
            />
        </div>
    );
}

export default App;
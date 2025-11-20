import React, { useState } from 'react';
import axios from 'axios';
import {
    ChevronRight,
    ChevronDown,
    Plus,
    Trash2,
    FileText,
    FolderOpen,
    Folder,
    X,
    Edit2,
    Check
} from 'lucide-react';
import './ResearchesSection.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

function ResearchesSection({
    papers,
    researches,
    activeResearch,
    onResearchesChange,
    onActiveResearchChange,
    onDeletePaper
}) {
    const [expandedResearches, setExpandedResearches] = useState({});
    const [showNewResearch, setShowNewResearch] = useState(false);
    const [newResearchName, setNewResearchName] = useState('');
    const [editingResearch, setEditingResearch] = useState(null);
    const [editName, setEditName] = useState('');
    const [showAddPapers, setShowAddPapers] = useState(null);
    const [isLoading, setIsLoading] = useState(false);

    const toggleExpanded = (researchId) => {
        setExpandedResearches(prev => ({
            ...prev,
            [researchId]: !prev[researchId]
        }));
    };

    const handleCreateResearch = async () => {
        if (!newResearchName.trim()) return;

        setIsLoading(true);
        try {
            console.log('📝 Creating new research topic...');
            const response = await axios.post(`${API_BASE_URL}/researches`, {
                name: newResearchName.trim(),
                description: '',
                papers: [],
                tags: []
            });

            console.log('✅ Research created:', response.data);
            
            // Add to researches list
            onResearchesChange([...researches, response.data]);
            setNewResearchName('');
            setShowNewResearch(false);
            setExpandedResearches(prev => ({ ...prev, [response.data._id]: true }));
        } catch (err) {
            console.error('❌ Error creating research:', err);
            alert('Failed to create research topic. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleDeleteResearch = async (researchId, event) => {
        event.stopPropagation();
        if (window.confirm('Delete this research topic?')) {
            setIsLoading(true);
            try {
                console.log('🗑️ Deleting research:', researchId);
                await axios.delete(`${API_BASE_URL}/researches/${researchId}`);
                console.log('✅ Research deleted');

                onResearchesChange(researches.filter(r => r._id !== researchId));
                if (activeResearch?._id === researchId) {
                    onActiveResearchChange(null);
                }
            } catch (err) {
                console.error('❌ Error deleting research:', err);
                alert('Failed to delete research topic. Please try again.');
            } finally {
                setIsLoading(false);
            }
        }
    };

    const handleRenameResearch = async (researchId) => {
        if (!editName.trim()) return;

        setIsLoading(true);
        try {
            console.log('✏️ Renaming research:', researchId);
            const response = await axios.put(`${API_BASE_URL}/researches/${researchId}`, {
                name: editName.trim()
            });

            console.log('✅ Research renamed:', response.data);

            onResearchesChange(
                researches.map(r => 
                    r._id === researchId ? response.data : r
                )
            );

            // Update active research if it's the one being renamed
            if (activeResearch?._id === researchId) {
                onActiveResearchChange(response.data);
            }

            setEditingResearch(null);
            setEditName('');
        } catch (err) {
            console.error('❌ Error renaming research:', err);
            alert('Failed to rename research topic. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleAddPaperToResearch = async (researchId, paperId) => {
        setIsLoading(true);
        try {
            console.log('➕ Adding paper to research:', paperId, 'to', researchId);
            await axios.post(`${API_BASE_URL}/researches/${researchId}/papers/${paperId}`);
            console.log('✅ Paper added');

            // Update the research in state
            const updatedResearches = researches.map(r => {
                if (r._id === researchId) {
                    return { ...r, papers: [...r.papers, paperId] };
                }
                return r;
            });
            onResearchesChange(updatedResearches);

            // Update active research if it's the one being modified
            if (activeResearch?._id === researchId) {
                onActiveResearchChange(updatedResearches.find(r => r._id === researchId));
            }

            setShowAddPapers(null);
        } catch (err) {
            console.error('❌ Error adding paper to research:', err);
            alert('Failed to add paper to research. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleRemovePaperFromResearch = async (researchId, paperId, event) => {
        event.stopPropagation();
        setIsLoading(true);
        try {
            console.log('➖ Removing paper from research:', paperId, 'from', researchId);
            await axios.delete(`${API_BASE_URL}/researches/${researchId}/papers/${paperId}`);
            console.log('✅ Paper removed');

            // Update the research in state
            const updatedResearches = researches.map(r =>
                r._id === researchId
                    ? { ...r, papers: r.papers.filter(p => p !== paperId) }
                    : r
            );
            onResearchesChange(updatedResearches);

            // Update active research if it's the one being modified
            if (activeResearch?._id === researchId) {
                onActiveResearchChange(updatedResearches.find(r => r._id === researchId));
            }
        } catch (err) {
            console.error('❌ Error removing paper from research:', err);
            alert('Failed to remove paper from research. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    const getPaperById = (paperId) => {
        return papers.find(p => p.file_name === paperId);
    };

    const getAvailablePapers = (researchId) => {
        const research = researches.find(r => r._id === researchId);
        if (!research) return papers;
        return papers.filter(p => !research.papers.includes(p.file_name));
    };

    return (
        <div className="sidebar-section researches-section">
            <div className="section-header">
                <div className="section-title">
                    <span className="section-title-icon">🔬</span>
                    <span>Research Topics</span>
                    <span className="count-badge">{researches.length}</span>
                </div>
                <button
                    className="icon-button add-research-btn"
                    onClick={(e) => {
                        e.stopPropagation();
                        setShowNewResearch(true);
                    }}
                    disabled={isLoading}
                    title="New research topic"
                >
                    <Plus size={16} />
                </button>
            </div>

            <div className="section-content researches-content">
                {/* New Research Input */}
                {showNewResearch && (
                    <div className="new-research-form">
                        <input
                            type="text"
                            placeholder="Enter research topic name..."
                            value={newResearchName}
                            onChange={(e) => setNewResearchName(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleCreateResearch()}
                            autoFocus
                            className="research-name-input"
                        />
                        <div className="form-actions">
                            <button
                                className="btn-small btn-primary"
                                onClick={handleCreateResearch}
                                disabled={!newResearchName.trim() || isLoading}
                            >
                                <Check size={14} />
                                Create
                            </button>
                            <button
                                className="btn-small btn-secondary"
                                onClick={() => {
                                    setShowNewResearch(false);
                                    setNewResearchName('');
                                }}
                                disabled={isLoading}
                            >
                                <X size={14} />
                                Cancel
                            </button>
                        </div>
                    </div>
                )}

                {/* Research Topics List */}
                <div className="researches-list">
                    {researches.length === 0 && !showNewResearch ? (
                        <div className="empty-state-small">
                            <FolderOpen size={32} />
                            <p>No research topics yet</p>
                            <button
                                className="btn-small btn-primary"
                                onClick={() => setShowNewResearch(true)}
                                disabled={isLoading}
                            >
                                <Plus size={14} />
                                Create First Topic
                            </button>
                        </div>
                    ) : (
                        researches.map(research => (
                            <div
                                key={research._id}
                                className={`research-item ${activeResearch?._id === research._id ? 'active' : ''}`}
                            >
                                {/* Research Header */}
                                <div
                                    className="research-header"
                                    onClick={() => {
                                        onActiveResearchChange(research);
                                    }}
                                >
                                    <button
                                        className="expand-button"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            toggleExpanded(research._id);
                                        }}
                                    >
                                        {expandedResearches[research._id] ? (
                                            <ChevronDown size={16} />
                                        ) : (
                                            <ChevronRight size={16} />
                                        )}
                                    </button>

                                    <Folder size={16} className="folder-icon" />

                                    {editingResearch === research._id ? (
                                        <input
                                            type="text"
                                            value={editName}
                                            onChange={(e) => setEditName(e.target.value)}
                                            onKeyPress={(e) => {
                                                if (e.key === 'Enter') handleRenameResearch(research._id);
                                                if (e.key === 'Escape') {
                                                    setEditingResearch(null);
                                                    setEditName('');
                                                }
                                            }}
                                            onClick={(e) => e.stopPropagation()}
                                            className="research-name-input-inline"
                                            autoFocus
                                            disabled={isLoading}
                                        />
                                    ) : (
                                        <span className="research-name">{research.name}</span>
                                    )}

                                    <div className="research-actions">
                                        {editingResearch === research._id ? (
                                            <>
                                                <button
                                                    className="icon-button"
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        handleRenameResearch(research._id);
                                                    }}
                                                    disabled={isLoading}
                                                    title="Save"
                                                >
                                                    <Check size={14} />
                                                </button>
                                                <button
                                                    className="icon-button"
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        setEditingResearch(null);
                                                        setEditName('');
                                                    }}
                                                    disabled={isLoading}
                                                    title="Cancel"
                                                >
                                                    <X size={14} />
                                                </button>
                                            </>
                                        ) : (
                                            <>
                                                <button
                                                    className="icon-button"
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        setEditingResearch(research._id);
                                                        setEditName(research.name);
                                                    }}
                                                    disabled={isLoading}
                                                    title="Rename"
                                                >
                                                    <Edit2 size={14} />
                                                </button>
                                                <button
                                                    className="icon-button delete-btn"
                                                    onClick={(e) => handleDeleteResearch(research._id, e)}
                                                    disabled={isLoading}
                                                    title="Delete"
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            </>
                                        )}
                                    </div>
                                </div>

                                {/* Research Papers */}
                                {expandedResearches[research._id] && (
                                    <div className="research-papers">
                                        {research.papers.length === 0 ? (
                                            <div className="empty-papers">
                                                <FileText size={24} />
                                                <p>No papers attached</p>
                                            </div>
                                        ) : (
                                            research.papers.map(paperId => {
                                                const paper = getPaperById(paperId);
                                                if (!paper) return null;
                                                return (
                                                    <div key={paperId} className="paper-item-small">
                                                        <FileText size={14} />
                                                        <span className="paper-name-small">{paper.file_name}</span>
                                                        <button
                                                            className="icon-button delete-btn"
                                                            onClick={(e) => handleRemovePaperFromResearch(research._id, paperId, e)}
                                                            disabled={isLoading}
                                                            title="Remove from research"
                                                        >
                                                            <X size={12} />
                                                        </button>
                                                    </div>
                                                );
                                            })
                                        )}

                                        {/* Add Papers Button */}
                                        {showAddPapers === research._id ? (
                                            <div className="add-papers-dropdown">
                                                <div className="dropdown-header">
                                                    <span>Select papers to add</span>
                                                    <button
                                                        className="icon-button"
                                                        onClick={() => setShowAddPapers(null)}
                                                        disabled={isLoading}
                                                    >
                                                        <X size={14} />
                                                    </button>
                                                </div>
                                                <div className="papers-dropdown-list">
                                                    {getAvailablePapers(research._id).length === 0 ? (
                                                        <div className="no-papers-available">
                                                            All papers already added
                                                        </div>
                                                    ) : (
                                                        getAvailablePapers(research._id).map(paper => (
                                                            <div
                                                                key={paper.file_name}
                                                                className="paper-dropdown-item"
                                                                onClick={() => handleAddPaperToResearch(research._id, paper.file_name)}
                                                                style={{ cursor: isLoading ? 'not-allowed' : 'pointer', opacity: isLoading ? 0.6 : 1 }}
                                                            >
                                                                <FileText size={14} />
                                                                <span>{paper.file_name}</span>
                                                                <Plus size={14} />
                                                            </div>
                                                        ))
                                                    )}
                                                </div>
                                            </div>
                                        ) : (
                                            <button
                                                className="add-paper-button"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    setShowAddPapers(research._id);
                                                }}
                                                disabled={isLoading}
                                            >
                                                <Plus size={14} />
                                                Add Papers
                                            </button>
                                        )}
                                    </div>
                                )}
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}

export default ResearchesSection;
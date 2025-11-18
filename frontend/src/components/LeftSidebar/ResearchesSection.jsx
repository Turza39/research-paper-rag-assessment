import React, { useState } from 'react';
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
    const [showAllFiles, setShowAllFiles] = useState(false);
    const [editingResearch, setEditingResearch] = useState(null);
    const [editName, setEditName] = useState('');
    const [showAddPapers, setShowAddPapers] = useState(null);

    const toggleExpanded = (researchId) => {
        setExpandedResearches(prev => ({
            ...prev,
            [researchId]: !prev[researchId]
        }));
    };

    const handleCreateResearch = () => {
        if (!newResearchName.trim()) return;

        const newResearch = {
            id: Date.now().toString(),
            name: newResearchName.trim(),
            papers: [],
            createdAt: new Date().toISOString()
        };

        onResearchesChange([...researches, newResearch]);
        setNewResearchName('');
        setShowNewResearch(false);
        setExpandedResearches(prev => ({ ...prev, [newResearch.id]: true }));
    };

    const handleDeleteResearch = (researchId, event) => {
        event.stopPropagation();
        if (window.confirm('Delete this research topic?')) {
            onResearchesChange(researches.filter(r => r.id !== researchId));
            if (activeResearch?.id === researchId) {
                onActiveResearchChange(null);
            }
        }
    };

    const handleRenameResearch = (researchId) => {
        if (!editName.trim()) return;
        
        onResearchesChange(
            researches.map(r => 
                r.id === researchId ? { ...r, name: editName.trim() } : r
            )
        );
        setEditingResearch(null);
        setEditName('');
    };

    const handleAddPaperToResearch = (researchId, paperId) => {
        onResearchesChange(
            researches.map(r => {
                if (r.id === researchId) {
                    if (!r.papers.includes(paperId)) {
                        return { ...r, papers: [...r.papers, paperId] };
                    }
                }
                return r;
            })
        );
        setShowAddPapers(null);
    };

    const handleRemovePaperFromResearch = (researchId, paperId, event) => {
        event.stopPropagation();
        onResearchesChange(
            researches.map(r =>
                r.id === researchId
                    ? { ...r, papers: r.papers.filter(p => p !== paperId) }
                    : r
            )
        );
    };

    const getPaperById = (paperId) => {
        return papers.find(p => p.file_name === paperId);
    };

    const getAvailablePapers = (researchId) => {
        const research = researches.find(r => r.id === researchId);
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
                                disabled={!newResearchName.trim()}
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
                            >
                                <Plus size={14} />
                                Create First Topic
                            </button>
                        </div>
                    ) : (
                        researches.map(research => (
                            <div
                                key={research.id}
                                className={`research-item ${activeResearch?.id === research.id ? 'active' : ''}`}
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
                                            toggleExpanded(research.id);
                                        }}
                                    >
                                        {expandedResearches[research.id] ? (
                                            <ChevronDown size={16} />
                                        ) : (
                                            <ChevronRight size={16} />
                                        )}
                                    </button>

                                    <Folder size={16} className="folder-icon" />

                                    {editingResearch === research.id ? (
                                        <input
                                            type="text"
                                            value={editName}
                                            onChange={(e) => setEditName(e.target.value)}
                                            onKeyPress={(e) => {
                                                if (e.key === 'Enter') handleRenameResearch(research.id);
                                                if (e.key === 'Escape') {
                                                    setEditingResearch(null);
                                                    setEditName('');
                                                }
                                            }}
                                            onClick={(e) => e.stopPropagation()}
                                            className="research-name-input-inline"
                                            autoFocus
                                        />
                                    ) : (
                                        <span className="research-name">{research.name}</span>
                                    )}

                                    <div className="research-actions">
                                        {editingResearch === research.id ? (
                                            <>
                                                <button
                                                    className="icon-button"
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        handleRenameResearch(research.id);
                                                    }}
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
                                                        setEditingResearch(research.id);
                                                        setEditName(research.name);
                                                    }}
                                                    title="Rename"
                                                >
                                                    <Edit2 size={14} />
                                                </button>
                                                <button
                                                    className="icon-button delete-btn"
                                                    onClick={(e) => handleDeleteResearch(research.id, e)}
                                                    title="Delete"
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            </>
                                        )}
                                    </div>
                                </div>

                                {/* Research Papers */}
                                {expandedResearches[research.id] && (
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
                                                            onClick={(e) => handleRemovePaperFromResearch(research.id, paperId, e)}
                                                            title="Remove from research"
                                                        >
                                                            <X size={12} />
                                                        </button>
                                                    </div>
                                                );
                                            })
                                        )}

                                        {/* Add Papers Button */}
                                        {showAddPapers === research.id ? (
                                            <div className="add-papers-dropdown">
                                                <div className="dropdown-header">
                                                    <span>Select papers to add</span>
                                                    <button
                                                        className="icon-button"
                                                        onClick={() => setShowAddPapers(null)}
                                                    >
                                                        <X size={14} />
                                                    </button>
                                                </div>
                                                <div className="papers-dropdown-list">
                                                    {getAvailablePapers(research.id).length === 0 ? (
                                                        <div className="no-papers-available">
                                                            All papers already added
                                                        </div>
                                                    ) : (
                                                        getAvailablePapers(research.id).map(paper => (
                                                            <div
                                                                key={paper.file_name}
                                                                className="paper-dropdown-item"
                                                                onClick={() => handleAddPaperToResearch(research.id, paper.file_name)}
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
                                                    setShowAddPapers(research.id);
                                                }}
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

                {/* All Files Section */}
                <div className="all-files-section">
                    <div
                        className="all-files-header"
                        onClick={() => setShowAllFiles(!showAllFiles)}
                    >
                        <button className="expand-button">
                            {showAllFiles ? (
                                <ChevronDown size={16} />
                            ) : (
                                <ChevronRight size={16} />
                            )}
                        </button>
                        <FileText size={16} />
                        <span className="all-files-title">All Uploaded Files</span>
                        <span className="count-badge">{papers.length}</span>
                    </div>

                    {showAllFiles && (
                        <div className="all-files-list">
                            {papers.length === 0 ? (
                                <div className="empty-state-small">
                                    <FileText size={24} />
                                    <p>No files uploaded</p>
                                </div>
                            ) : (
                                papers.map(paper => (
                                    <div key={paper.file_name} className="file-item">
                                        <FileText size={14} />
                                        <div className="file-info">
                                            <span className="file-name">{paper.file_name}</span>
                                            <span className="file-meta">
                                                {paper.page_count} pages · {paper.vector_count} vectors
                                            </span>
                                        </div>
                                        <button
                                            className="icon-button delete-btn"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                if (window.confirm(`Delete ${paper.file_name}?`)) {
                                                    onDeletePaper(paper.file_name);
                                                }
                                            }}
                                            title="Delete file"
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                    </div>
                                ))
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default ResearchesSection;
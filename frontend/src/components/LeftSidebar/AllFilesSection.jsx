import React, { useState } from 'react';
import { ChevronRight, ChevronDown, FileText, Trash2 } from 'lucide-react';
import './AllFilesSection.css';

function AllFilesSection({ papers, onDeletePaper }) {
    const [showAllFiles, setShowAllFiles] = useState(false);

    return (
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
    );
}

export default AllFilesSection;

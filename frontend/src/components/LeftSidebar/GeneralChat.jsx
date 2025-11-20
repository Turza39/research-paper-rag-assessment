import React from 'react';
import './GeneralChat.css';

function GeneralChat({ isActive, onActivate }) {
    return (
        <div
            className={`sidebar-section general-chat-section ${isActive ? 'active' : ''}`}
            onClick={onActivate}
        >
            <div className="section-header">
                <div className="section-title">
                    <span className="section-title-icon">💬</span>
                    <span>General Chat</span>
                </div>
                {isActive && <div className="active-indicator">●</div>}
            </div>
        </div>
    );
}

export default GeneralChat;
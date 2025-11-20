import React from 'react';
import FileUpload from './FileUpload';
import GeneralChat from './GeneralChat';
import ResearchesSection from './ResearchesSection';
import AllFilesSection from './AllFilesSection';
import './LeftSidebar.css';

function LeftSidebar({
    papers,
    researches,
    activeResearch,
    chatMode,
    onFileUpload,
    onDeletePaper,
    onResearchesChange,
    onActiveResearchChange,
    onChatModeChange,
    onMessagesReset
}) {
    return (
        <div className="left-sidebar">
            <div className="sidebar-header">
                <div className="header-content">
                    <div className="logo">
                        <div className="logo-icon">📚</div>
                        <div className="logo-text">
                            <h1>Research Hub</h1>
                            <p>AI-Powered Analysis</p>
                        </div>
                    </div>
                </div>
            </div>

            <div className="sidebar-content">
                <FileUpload onFileUpload={onFileUpload} />
                
                <GeneralChat
                    isActive={chatMode === 'general'}
                    onActivate={() => {
                        onChatModeChange('general');
                        onActiveResearchChange(null);
                        onMessagesReset();
                    }}
                />
                
                <ResearchesSection
                    papers={papers}
                    researches={researches}
                    activeResearch={activeResearch}
                    onResearchesChange={onResearchesChange}
                    onActiveResearchChange={(research) => {
                        onActiveResearchChange(research);
                        onChatModeChange('research');
                        onMessagesReset();
                    }}
                />
            </div>

            <AllFilesSection
                papers={papers}
                onDeletePaper={onDeletePaper}
            />
        </div>
    );
}

export default LeftSidebar;
import React, { useRef, useState } from 'react';
import { Upload, CheckCircle, AlertCircle } from 'lucide-react';
import './FileUpload.css';

function FileUpload({ onFileUpload }) {
    const fileInputRef = useRef(null);
    const [isUploading, setIsUploading] = useState(false);
    const [message, setMessage] = useState(null);

    const handleFileChange = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        setIsUploading(true);
        setMessage(null);

        const result = await onFileUpload(file);

        if (result.success) {
            setMessage({ type: 'success', text: `✓ ${file.name} uploaded successfully` });
        } else {
            setMessage({ type: 'error', text: result.error });
        }

        setIsUploading(false);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }

        // Clear message after 3 seconds
        setTimeout(() => setMessage(null), 3000);
    };

    return (
        <div className="sidebar-section file-upload-section">
            <div className="section-header">
                <div className="section-title">
                    <span className="section-title-icon">📤</span>
                    <span>Upload Documents</span>
                </div>
            </div>
            <div className="section-content">
                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf"
                    onChange={handleFileChange}
                    className="file-input-hidden"
                    id="file-upload-input"
                    disabled={isUploading}
                />
                <label htmlFor="file-upload-input" className="file-upload-label">
                    <button
                        className="upload-button"
                        disabled={isUploading}
                        onClick={() => fileInputRef.current?.click()}
                        type="button"
                    >
                        {isUploading ? (
                            <>
                                <div className="spinner"></div>
                                <span>Uploading...</span>
                            </>
                        ) : (
                            <>
                                <Upload size={18} />
                                <span>Choose PDF File</span>
                            </>
                        )}
                    </button>
                </label>

                {message && (
                    <div className={`upload-message ${message.type}`}>
                        {message.type === 'success' ? (
                            <CheckCircle size={16} />
                        ) : (
                            <AlertCircle size={16} />
                        )}
                        <span>{message.text}</span>
                    </div>
                )}

                <p className="upload-hint">
                    Upload research papers in PDF format
                </p>
            </div>
        </div>
    );
}

export default FileUpload;
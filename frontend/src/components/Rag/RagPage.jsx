import React, { useEffect, useState } from 'react';
import './RagPage.css';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const ACCEPTED_TYPES = {
  'application/pdf': '.pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
  'text/plain': '.txt',
};

export default function RagPage() {
  const [documents, setDocuments] = useState([]);
  const [stats, setStats] = useState(null);
  const [projectInput, setProjectInput] = useState('General');
  const [collectionType, setCollectionType] = useState('knowledge_base');
  const [projects, setProjects] = useState([]);

  // Filters for each column
  const [uploadedFilters, setUploadedFilters] = useState({
    collection: 'all',
    usage: 'all',
    sortBy: 'date_desc'
  });

  const [generatedFilters, setGeneratedFilters] = useState({
    collection: 'all',
    usage: 'all',
    sortBy: 'date_desc'
  });

  // Modals
  const [showAddProjectModal, setShowAddProjectModal] = useState(false);
  const [selectedDocForProject, setSelectedDocForProject] = useState(null);
  const [selectedProjectToAdd, setSelectedProjectToAdd] = useState('');

  const fetchDocuments = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/rag/documents`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/rag/stats`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/projects`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setProjects(data);
      }
    } catch (err) {
      console.error('Failed to fetch projects:', err);
    }
  };

  useEffect(() => {
    fetchDocuments();
    fetchStats();
    fetchProjects();
    const interval = setInterval(() => {
      fetchDocuments();
      fetchStats();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleUpload = async (files) => {
    for (const file of Array.from(files)) {
      if (!Object.keys(ACCEPTED_TYPES).includes(file.type)) continue;
      const formData = new FormData();
      formData.append('file', file);
      formData.append('project', projectInput || 'General');
      formData.append('collection', collectionType);
      await fetch(`${API_BASE}/api/rag/documents`, { method: 'POST', body: formData, credentials: 'include' });
    }
    setProjectInput('General');
    fetchDocuments();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    handleUpload(e.dataTransfer.files);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this document?')) return;

    try {
      const response = await fetch(`${API_BASE}/api/rag/documents/${id}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (response.ok) {
        fetchDocuments();
        fetchStats();
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        alert(`Failed to delete document: ${errorData.detail || response.statusText}`);
      }
    } catch (error) {
      console.error('Delete failed:', error);
      alert(`Failed to delete document: ${error.message}`);
    }
  };

  const handleAddProject = (docId, currentProjects) => {
    setSelectedDocForProject({ id: docId, projects: currentProjects });
    setSelectedProjectToAdd('');
    setShowAddProjectModal(true);
  };

  const confirmAddProject = async () => {
    if (!selectedProjectToAdd || !selectedDocForProject) return;

    const updatedProjects = [...selectedDocForProject.projects, selectedProjectToAdd];
    try {
      const response = await fetch(`${API_BASE}/api/rag/documents/${selectedDocForProject.id}/projects`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedProjects),
        credentials: 'include'
      });

      if (response.ok) {
        fetchDocuments();
        setShowAddProjectModal(false);
        setSelectedDocForProject(null);
        setSelectedProjectToAdd('');
      } else {
        alert('Failed to add project');
      }
    } catch (error) {
      console.error('Error adding project:', error);
      alert('Failed to add project');
    }
  };

  const handleRemoveProject = async (docId, currentProjects, projectToRemove) => {
    if (!window.confirm(`Remove project "${projectToRemove}" from this document?`)) return;

    const updatedProjects = currentProjects.filter(p => p !== projectToRemove);
    if (updatedProjects.length === 0) updatedProjects.push('General');

    try {
      const response = await fetch(`${API_BASE}/api/rag/documents/${docId}/projects`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedProjects),
        credentials: 'include'
      });

      if (response.ok) {
        fetchDocuments();
      } else {
        alert('Failed to remove project');
      }
    } catch (error) {
      console.error('Error removing project:', error);
      alert('Failed to remove project');
    }
  };

  // Categorize documents by source
  const uploadedDocs = documents.filter(doc => !doc.filename.startsWith('main_content_'));
  const generatedDocs = documents.filter(doc => doc.filename.startsWith('main_content_'));

  // Apply filters
  const filterDocs = (docs, filters) => {
    return docs.filter(doc => {
      // Collection filter
      if (filters.collection !== 'all' && doc.collection !== filters.collection) return false;

      // Usage filter (check if doc has associated projects beyond 'General')
      if (filters.usage === 'used' && (!doc.projects || doc.projects.length === 0 || (doc.projects.length === 1 && doc.projects[0] === 'General'))) {
        return false;
      }
      if (filters.usage === 'unused' && doc.projects && doc.projects.length > 0 && (doc.projects.length > 1 || doc.projects[0] !== 'General')) {
        return false;
      }

      return true;
    });
  };

  // Sort documents
  const sortDocs = (docs, sortBy) => {
    const sorted = [...docs];
    if (sortBy === 'date_desc') {
      sorted.sort((a, b) => new Date(b.upload_date || b.created_at) - new Date(a.upload_date || a.created_at));
    } else if (sortBy === 'date_asc') {
      sorted.sort((a, b) => new Date(a.upload_date || a.created_at) - new Date(b.upload_date || b.created_at));
    } else if (sortBy === 'name') {
      sorted.sort((a, b) => (a.original_filename || a.filename).localeCompare(b.original_filename || b.filename));
    }
    return sorted;
  };

  const filteredUploadedDocs = sortDocs(filterDocs(uploadedDocs, uploadedFilters), uploadedFilters.sortBy);
  const filteredGeneratedDocs = sortDocs(filterDocs(generatedDocs, generatedFilters), generatedFilters.sortBy);

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  const renderDocumentCard = (doc, isGenerated = false) => (
    <div key={doc.id} className="document-card">
      <div className="doc-header">
        <div className="doc-title">
          <span className="doc-filename">{doc.original_filename || doc.filename}</span>
          <span className={`doc-badge ${doc.collection === 'brand_voice' ? 'badge-voice' : 'badge-knowledge'}`}>
            {doc.collection === 'brand_voice' ? '🎨 Style' : '📚 Knowledge'}
          </span>
          {isGenerated && (
            <span className="doc-badge badge-generated">
              ✨ Auto-Generated
            </span>
          )}
        </div>
        <span className={`doc-status status-${doc.status}`}>
          {doc.status}
        </span>
      </div>

      <div className="doc-meta">
        <span>{formatBytes(doc.file_size)}</span>
        <span>•</span>
        <span>{formatDate(doc.upload_date || doc.created_at)}</span>
        <span>•</span>
        <span>{doc.file_type?.toUpperCase()}</span>
        {doc.chunks_count > 0 && (
          <>
            <span>•</span>
            <span>{doc.chunks_count} chunks</span>
          </>
        )}
      </div>

      {doc.projects && doc.projects.length > 0 && (
        <div className="doc-projects">
          {doc.projects.map((project, idx) => (
            project && project !== 'General' && (
              <span key={idx} className="project-tag">
                📁 {project}
                <button
                  onClick={() => handleRemoveProject(doc.id, doc.projects, project)}
                  className="remove-project-btn"
                  title={`Remove ${project}`}
                >
                  ×
                </button>
              </span>
            )
          ))}
          <button
            onClick={() => handleAddProject(doc.id, doc.projects || [doc.project])}
            className="add-project-btn"
            title="Add to another project"
          >
            + Add Project
          </button>
        </div>
      )}

      <div className="doc-actions">
        <button onClick={() => handleDelete(doc.id)} className="delete-btn">
          🗑️ Delete
        </button>
      </div>
    </div>
  );

  return (
    <div className="rag-page">
      <div className="page-header">
        <h2>📚 Knowledge Base</h2>
        <p className="page-description">
          Manage uploaded documents and auto-generated campaign content for RAG system
        </p>
      </div>

      {/* Stats Summary */}
      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">Total Documents</div>
            <div className="stat-value">{stats.total_documents}</div>
          </div>
          <div className="stat-card stat-success">
            <div className="stat-label">Completed</div>
            <div className="stat-value">{stats.completed}</div>
          </div>
          <div className="stat-card stat-warning">
            <div className="stat-label">Processing</div>
            <div className="stat-value">{stats.processing}</div>
          </div>
          <div className="stat-card stat-info">
            <div className="stat-label">Total Chunks</div>
            <div className="stat-value">{stats.total_chunks}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Uploaded</div>
            <div className="stat-value">{uploadedDocs.length}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Generated</div>
            <div className="stat-value">{generatedDocs.length}</div>
          </div>
        </div>
      )}

      {/* Upload Section */}
      <div className="upload-section">
        <div className="collection-selector">
          <label className="selector-label">Document Type:</label>
          <div className="radio-group">
            <label className="radio-option">
              <input
                type="radio"
                name="collectionType"
                value="knowledge_base"
                checked={collectionType === 'knowledge_base'}
                onChange={(e) => setCollectionType(e.target.value)}
              />
              <span>📚 Knowledge Base - Factual information and content</span>
            </label>
            <label className="radio-option">
              <input
                type="radio"
                name="collectionType"
                value="brand_voice"
                checked={collectionType === 'brand_voice'}
                onChange={(e) => setCollectionType(e.target.value)}
              />
              <span>🎨 Style/Voice - Writing style and tone examples</span>
            </label>
          </div>
        </div>

        <div
          className="drop-zone"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
        >
          <div className="drop-zone-icon">📤</div>
          <div className="drop-zone-text">Drag & drop PDF, DOCX, or TXT files here</div>
          <div className="drop-zone-or">or</div>
          <label className="file-input-label">
            <input
              type="file"
              multiple
              accept={Object.values(ACCEPTED_TYPES).join(',')}
              onChange={(e) => handleUpload(e.target.files)}
              style={{ display: 'none' }}
            />
            <span className="file-input-btn">Browse Files</span>
          </label>
        </div>

        <div className="project-selector">
          <label className="selector-label">Associate with Project:</label>
          <select
            value={projectInput}
            onChange={(e) => setProjectInput(e.target.value)}
            className="project-select"
          >
            <option value="General">General (No specific project)</option>
            {projects.map(project => (
              <option key={project.id} value={project.name}>
                {project.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="documents-grid">
        {/* Uploaded Documents Column */}
        <div className="documents-column">
          <div className="column-header">
            <div className="header-title">
              <h3>📤 Uploaded Documents</h3>
              <span className="count-badge">{filteredUploadedDocs.length}</span>
            </div>
          </div>

          {/* Filters for Uploaded Column */}
          <div className="column-filters">
            <select
              value={uploadedFilters.collection}
              onChange={(e) => setUploadedFilters({...uploadedFilters, collection: e.target.value})}
              className="filter-select"
            >
              <option value="all">All Types</option>
              <option value="knowledge_base">📚 Knowledge</option>
              <option value="brand_voice">🎨 Style</option>
            </select>

            <select
              value={uploadedFilters.usage}
              onChange={(e) => setUploadedFilters({...uploadedFilters, usage: e.target.value})}
              className="filter-select"
            >
              <option value="all">All Usage</option>
              <option value="used">✅ Used</option>
              <option value="unused">⭕ Unused</option>
            </select>

            <select
              value={uploadedFilters.sortBy}
              onChange={(e) => setUploadedFilters({...uploadedFilters, sortBy: e.target.value})}
              className="filter-select"
            >
              <option value="date_desc">📅 Newest</option>
              <option value="date_asc">📅 Oldest</option>
              <option value="name">🔤 Name</option>
            </select>
          </div>

          <div className="documents-list">
            {filteredUploadedDocs.length > 0 ? (
              filteredUploadedDocs.map(doc => renderDocumentCard(doc, false))
            ) : (
              <div className="empty-state">
                <div className="empty-icon">📭</div>
                <p>No uploaded documents match your filters</p>
              </div>
            )}
          </div>
        </div>

        {/* Generated Documents Column */}
        <div className="documents-column">
          <div className="column-header">
            <div className="header-title">
              <h3>✨ Auto-Generated Content</h3>
              <span className="count-badge">{filteredGeneratedDocs.length}</span>
            </div>
          </div>

          {/* Filters for Generated Column */}
          <div className="column-filters">
            <select
              value={generatedFilters.collection}
              onChange={(e) => setGeneratedFilters({...generatedFilters, collection: e.target.value})}
              className="filter-select"
            >
              <option value="all">All Types</option>
              <option value="knowledge_base">📚 Knowledge</option>
              <option value="brand_voice">🎨 Style</option>
            </select>

            <select
              value={generatedFilters.usage}
              onChange={(e) => setGeneratedFilters({...generatedFilters, usage: e.target.value})}
              className="filter-select"
            >
              <option value="all">All Usage</option>
              <option value="used">✅ Used</option>
              <option value="unused">⭕ Unused</option>
            </select>

            <select
              value={generatedFilters.sortBy}
              onChange={(e) => setGeneratedFilters({...generatedFilters, sortBy: e.target.value})}
              className="filter-select"
            >
              <option value="date_desc">📅 Newest</option>
              <option value="date_asc">📅 Oldest</option>
              <option value="name">🔤 Name</option>
            </select>
          </div>

          <div className="documents-list">
            {filteredGeneratedDocs.length > 0 ? (
              filteredGeneratedDocs.map(doc => renderDocumentCard(doc, true))
            ) : (
              <div className="empty-state">
                <div className="empty-icon">✨</div>
                <p>No auto-generated content yet</p>
                <small>Publish main content in an integrated campaign to see it here</small>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Add Project Modal */}
      {showAddProjectModal && (
        <div className="modal-overlay" onClick={() => setShowAddProjectModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Add Document to Project</h3>
            <p className="modal-description">
              Select a project to associate this document with:
            </p>
            <select
              value={selectedProjectToAdd}
              onChange={(e) => setSelectedProjectToAdd(e.target.value)}
              className="modal-select"
            >
              <option value="">-- Select a project --</option>
              <option value="General">General</option>
              {projects
                .filter(p => !selectedDocForProject?.projects.includes(p.name))
                .map(project => (
                  <option key={project.id} value={project.name}>
                    {project.name}
                  </option>
                ))}
            </select>
            <div className="modal-actions">
              <button onClick={() => setShowAddProjectModal(false)} className="btn-secondary">
                Cancel
              </button>
              <button
                onClick={confirmAddProject}
                disabled={!selectedProjectToAdd}
                className="btn-primary"
              >
                Add Project
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

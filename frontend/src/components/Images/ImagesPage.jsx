import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Download, Trash2, ExternalLink, Eye, X, ChevronLeft, ChevronRight, Upload } from 'lucide-react';
import { format } from 'date-fns';
import toast, { Toaster } from 'react-hot-toast';
import { fetchWithRetry } from '../../utils/fetchWithRetry';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function ImagesPage() {
  const navigate = useNavigate();

  // State
  const [images, setImages] = useState([]);
  const [topics, setTopics] = useState([]);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedImage, setSelectedImage] = useState(null);

  // Project management state
  const [showAddProjectModal, setShowAddProjectModal] = useState(false);
  const [selectedImageForProject, setSelectedImageForProject] = useState(null);
  const [selectedProjectToAdd, setSelectedProjectToAdd] = useState('');

  // Filters
  const [modelFilter, setModelFilter] = useState('all');
  const [contentTypeFilter, setContentTypeFilter] = useState('all');
  const [topicFilter, setTopicFilter] = useState('all');
  const [sortBy, setSortBy] = useState('newest');

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  // Upload state
  const [showUpload, setShowUpload] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadPreview, setUploadPreview] = useState('');
  const [uploadPrompt, setUploadPrompt] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  // Expanded prompts state (track which prompts are expanded)
  const [expandedPrompts, setExpandedPrompts] = useState(new Set());

  // Load topics and projects
  useEffect(() => {
    loadTopics();
    loadProjects();
  }, []);

  // Load images when filters or page change
  useEffect(() => {
    loadImages();
  }, [modelFilter, contentTypeFilter, topicFilter, sortBy, currentPage]);

  const loadTopics = async () => {
    try {
      const response = await fetchWithRetry(`${API_BASE}/api/images/topics`, {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        setTopics(data);
      } else {
        console.error('Failed to load topics:', response.status);
        toast.error('Failed to load topics');
      }
    } catch (error) {
      console.error('Failed to load topics:', error);
      toast.error('Unable to load topics. Please check your connection.');
    }
  };

  const loadProjects = async () => {
    try {
      const response = await fetchWithRetry(`${API_BASE}/api/projects`, {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        setProjects(data);
      } else {
        console.error('Failed to load projects:', response.status);
      }
    } catch (error) {
      console.error('Failed to load projects:', error);
    }
  };

  const handleAddProject = (image) => {
    setSelectedImageForProject(image);
    setSelectedProjectToAdd('');
    setShowAddProjectModal(true);
  };

  const confirmAddProject = async () => {
    if (!selectedProjectToAdd || !selectedImageForProject) return;

    try {
      // Get current project IDs
      const currentProjectIds = selectedImageForProject.projects?.map(p => p.id) || [];

      // Add the new project ID
      const updatedProjectIds = [...new Set([...currentProjectIds, parseInt(selectedProjectToAdd)])];

      const response = await fetchWithRetry(`${API_BASE}/api/images/${selectedImageForProject.id}/projects`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(updatedProjectIds),
      });

      if (response.ok) {
        toast.success('Project added successfully!');
        setShowAddProjectModal(false);
        setSelectedImageForProject(null);
        setSelectedProjectToAdd('');
        loadImages();
      } else {
        toast.error('Failed to add project');
      }
    } catch (error) {
      console.error('Failed to add project:', error);
      toast.error('Unable to add project. Please check your connection.');
    }
  };

  const handleRemoveProject = async (image, projectId) => {
    if (!window.confirm('Remove this project from the image?')) return;

    try {
      // Remove the project ID from the array
      const updatedProjectIds = (image.projects?.map(p => p.id) || []).filter(id => id !== projectId);

      const response = await fetchWithRetry(`${API_BASE}/api/images/${image.id}/projects`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(updatedProjectIds),
      });

      if (response.ok) {
        toast.success('Project removed successfully!');
        loadImages();
      } else {
        toast.error('Failed to remove project');
      }
    } catch (error) {
      console.error('Failed to remove project:', error);
      toast.error('Unable to remove project. Please check your connection.');
    }
  };

  const loadImages = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        sortBy,
        page: currentPage,
        limit: 20,
      });

      if (modelFilter !== 'all') {
        params.append('model', modelFilter);
      }
      if (contentTypeFilter !== 'all') {
        params.append('contentType', contentTypeFilter);
      }
      if (topicFilter !== 'all') {
        params.append('topicId', topicFilter);
      }

      const response = await fetchWithRetry(`${API_BASE}/api/images/list?${params}`, {
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        setImages(data.images || []);
        setTotal(data.pagination?.total || 0);
        setTotalPages(data.pagination?.totalPages || 1);
      } else {
        console.error('Failed to load images:', response.status);
        toast.error('Failed to load images');
        setImages([]);
      }
    } catch (error) {
      console.error('Failed to load images:', error);
      toast.error('Unable to load images. Please check your connection.');
      setImages([]);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this image?')) return;

    try {
      const response = await fetchWithRetry(`${API_BASE}/api/images/${id}`, {
        method: 'DELETE',
        credentials: 'include',
      });

      if (response.ok) {
        toast.success('Image deleted successfully!');
        loadImages();
      } else {
        toast.error('Failed to delete image');
      }
    } catch (error) {
      console.error('Failed to delete image:', error);
      toast.error('Unable to delete image. Please check your connection.');
    }
  };

  const handleDownload = (image) => {
    const link = document.createElement('a');
    link.href = `${API_BASE}/api/images/${image.id}`;
    link.download = image.filename || `image-${image.id}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadFile(file);
      const url = URL.createObjectURL(file);
      setUploadPreview(url);
    }
  };

  const handleUpload = async () => {
    if (!uploadFile || !uploadPrompt.trim()) {
      toast.error('Please select a file and provide a description');
      return;
    }

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('prompt', uploadPrompt);
      formData.append('source', 'manual-upload');

      const response = await fetchWithRetry(`${API_BASE}/api/images/upload`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });

      if (response.ok) {
        toast.success('Image uploaded successfully!');

        // Reset form
        setUploadFile(null);
        setUploadPreview('');
        setUploadPrompt('');
        setShowUpload(false);

        // Reload images
        loadImages();
      } else {
        toast.error('Failed to upload image');
      }
    } catch (error) {
      console.error('Upload failed:', error);
      toast.error('Unable to upload image. Please check your connection.');
    } finally {
      setIsUploading(false);
    }
  };

  const getModelLabel = (image) => {
    if (image.openaiModel) {
      return image.openaiModel;
    } else if (image.source === 'comfyui') {
      return 'ComfyUI (SDXL)';
    } else if (image.source === 'stable-diffusion') {
      return 'Stable Diffusion';
    } else if (image.source === 'manual-upload') {
      return 'Uploaded by user';
    }
    return 'Unknown';
  };

  const getContentInfo = (image) => {
    // Only show content info if there's a valid project and pipeline execution
    if (image.pipelineExecution && image.projects && image.projects.length > 0) {
      return {
        type: image.pipelineExecution.contentType || 'Content',
        id: image.pipelineExecution.id,
        topic: image.pipelineExecution.topic,
        pipelineId: image.pipelineExecution.pipelineId,
        status: image.pipelineExecution.status,
      };
    }
    return null;
  };

  const togglePromptExpansion = (imageId) => {
    setExpandedPrompts((prev) => {
      const next = new Set(prev);
      if (next.has(imageId)) {
        next.delete(imageId);
      } else {
        next.add(imageId);
      }
      return next;
    });
  };

  const isPromptExpanded = (imageId) => expandedPrompts.has(imageId);

  // Check if prompt needs truncation (roughly 100 characters = ~2 lines at typical widths)
  const needsTruncation = (prompt) => prompt && prompt.length > 100;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Toaster position="top-right" />

      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Images Gallery</h1>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {total} {total === 1 ? 'image' : 'images'} total
              </p>
            </div>
            <button
              onClick={() => setShowUpload(!showUpload)}
              className="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
            >
              <Upload className="w-4 h-4 mr-2" />
              Upload Image
            </button>
          </div>
        </div>
      </div>

      {/* Upload Section */}
      {showUpload && (
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="container mx-auto px-4 py-6">
            <div className="max-w-2xl mx-auto">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Upload Image to Library
              </h2>
              <div className="space-y-4">
                {/* File Upload */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Select Image
                  </label>
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={handleFileSelect}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    JPG, PNG or WebP. Max 10MB.
                  </p>
                </div>

                {/* Preview */}
                {uploadPreview && (
                  <div className="border border-gray-300 dark:border-gray-600 rounded-lg p-4">
                    <img
                      src={uploadPreview}
                      alt="Preview"
                      className="max-w-full h-auto max-h-64 mx-auto rounded"
                    />
                  </div>
                )}

                {/* Prompt */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Image Description
                  </label>
                  <input
                    type="text"
                    value={uploadPrompt}
                    onChange={(e) => setUploadPrompt(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    placeholder="Describe the image..."
                  />
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <button
                    onClick={handleUpload}
                    disabled={!uploadFile || !uploadPrompt.trim() || isUploading}
                    className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors"
                  >
                    {isUploading ? 'Uploading...' : 'Upload to Library'}
                  </button>
                  <button
                    onClick={() => {
                      setShowUpload(false);
                      setUploadFile(null);
                      setUploadPreview('');
                      setUploadPrompt('');
                    }}
                    className="px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-600 dark:hover:bg-gray-500 text-gray-800 dark:text-white font-medium rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="container mx-auto px-4 py-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Model Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Model
              </label>
              <select
                value={modelFilter}
                onChange={(e) => {
                  setModelFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="all">All Models</option>
                <option value="gpt-image-1">gpt-image-1</option>
                <option value="gpt-image-1-mini">gpt-image-1-mini</option>
                <option value="dall-e-3">DALL-E 3</option>
                <option value="comfyui">ComfyUI (SDXL)</option>
                <option value="stable-diffusion">Stable Diffusion</option>
              </select>
            </div>

            {/* Content Type Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Content Type
              </label>
              <select
                value={contentTypeFilter}
                onChange={(e) => {
                  setContentTypeFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="all">All Content</option>
                <option value="blog post">Blog Posts</option>
                <option value="social media">Social Media</option>
                <option value="marketing">Marketing</option>
              </select>
            </div>

            {/* Topic Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Topic
              </label>
              <select
                value={topicFilter}
                onChange={(e) => {
                  setTopicFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="all">All Topics</option>
                {topics.map((topic) => (
                  <option key={topic.id} value={topic.id}>
                    {topic.topic?.substring(0, 50)}...
                  </option>
                ))}
              </select>
            </div>

            {/* Sort Order */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Sort By
              </label>
              <select
                value={sortBy}
                onChange={(e) => {
                  setSortBy(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="newest">Newest First</option>
                <option value="oldest">Oldest First</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="container mx-auto px-4 py-6">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-gray-500 dark:text-gray-400">Loading images...</div>
          </div>
        ) : images.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64">
            <p className="text-gray-500 dark:text-gray-400 text-lg mb-2">No images found for this filter</p>
            <p className="text-gray-400 dark:text-gray-500 text-sm">Try adjusting your filters</p>
          </div>
        ) : (
          <>
            {/* Image Grid - 4 columns */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {images.map((image) => {
                const contentInfo = getContentInfo(image);
                return (
                  <div
                    key={image.id}
                    className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden hover:shadow-md transition-shadow"
                  >
                    {/* Image Thumbnail */}
                    <div
                      className="relative aspect-square bg-gray-100 dark:bg-gray-700 cursor-pointer"
                      onClick={() => setSelectedImage(image)}
                    >
                      <img
                        src={`${API_BASE}/api/images/${image.id}`}
                        alt={image.prompt}
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute inset-0 bg-black bg-opacity-0 hover:bg-opacity-20 transition-opacity flex items-center justify-center">
                        <Eye className="w-8 h-8 text-white opacity-0 hover:opacity-100 transition-opacity" />
                      </div>
                    </div>

                    {/* Card Content */}
                    <div className="p-4">
                      {/* Model Badge */}
                      <div className="mb-2">
                        <span className="inline-block px-2 py-1 text-xs font-medium bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded">
                          {getModelLabel(image)}
                        </span>
                      </div>

                      {/* Prompt - Expandable */}
                      <div className="mb-3">
                        <p
                          className={`text-sm text-gray-700 dark:text-gray-300 ${
                            !isPromptExpanded(image.id) && needsTruncation(image.prompt) ? 'line-clamp-2' : ''
                          }`}
                        >
                          {image.prompt}
                        </p>
                        {needsTruncation(image.prompt) && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              togglePromptExpansion(image.id);
                            }}
                            className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 mt-1 font-medium"
                          >
                            {isPromptExpanded(image.id) ? 'Show less' : 'Show more'}
                          </button>
                        )}
                      </div>

                      {/* Project Badges - Show all associated projects */}
                      <div className="mb-2">
                        {image.projects && image.projects.length > 0 && (
                          <div className="flex flex-wrap gap-1 mb-1">
                            {image.projects.map((project, idx) => (
                              <span
                                key={idx}
                                className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 rounded"
                              >
                                📁 {project.name}
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleRemoveProject(image, project.id);
                                  }}
                                  className="ml-1 hover:text-red-600 dark:hover:text-red-400"
                                  title="Remove project"
                                >
                                  ×
                                </button>
                              </span>
                            ))}
                          </div>
                        )}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleAddProject(image);
                          }}
                          className="text-xs text-purple-600 dark:text-purple-400 hover:text-purple-800 dark:hover:text-purple-300 font-medium"
                        >
                          + Add Project
                        </button>
                      </div>

                      {/* Content Info - Only show if project exists */}
                      {contentInfo && (
                        <div className="mb-3 p-2 bg-gray-50 dark:bg-gray-700 rounded">
                          <div className="flex items-center justify-between">
                            <div className="flex-1 min-w-0">
                              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
                                {contentInfo.type}
                              </p>
                              <p className="text-sm text-gray-900 dark:text-white truncate">
                                {contentInfo.topic}
                              </p>
                            </div>
                            <button
                              onClick={() => navigate(`/content/view/${contentInfo.pipelineId}`)}
                              className="ml-2 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
                              title="View content"
                            >
                              <ExternalLink className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Metadata */}
                      <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1 mb-3">
                        <p>
                          <span className="font-medium">Size:</span> {image.width} x {image.height}
                        </p>
                        <p>
                          <span className="font-medium">Created:</span>{' '}
                          {image.createdAt ? format(new Date(image.createdAt), 'MMM d, yyyy') : 'Unknown'}
                        </p>
                      </div>

                      {/* Actions */}
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleDownload(image)}
                          className="flex-1 inline-flex items-center justify-center px-3 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-600 dark:hover:bg-gray-500 text-gray-700 dark:text-white rounded transition-colors"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setSelectedImage(image)}
                          className="flex-1 inline-flex items-center justify-center px-3 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-600 dark:hover:bg-gray-500 text-gray-700 dark:text-white rounded transition-colors"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(image.id)}
                          className="inline-flex items-center justify-center px-3 py-2 bg-red-100 hover:bg-red-200 dark:bg-red-900 dark:hover:bg-red-800 text-red-700 dark:text-red-200 rounded transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-8 flex items-center justify-center gap-2">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="inline-flex items-center px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 disabled:opacity-50 text-gray-700 dark:text-white rounded transition-colors"
                >
                  <ChevronLeft className="w-4 h-4 mr-1" />
                  Previous
                </button>
                <span className="text-sm text-gray-600 dark:text-gray-400 px-4">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="inline-flex items-center px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 disabled:opacity-50 text-gray-700 dark:text-white rounded transition-colors"
                >
                  Next
                  <ChevronRight className="w-4 h-4 ml-1" />
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Full-size Image Modal */}
      {selectedImage && (
        <div
          className="fixed inset-0 z-50 bg-black bg-opacity-90 flex items-center justify-center p-4"
          onClick={() => setSelectedImage(null)}
        >
          <button
            className="absolute top-4 right-4 text-white hover:text-gray-300"
            onClick={() => setSelectedImage(null)}
          >
            <X className="w-8 h-8" />
          </button>
          <img
            src={`${API_BASE}/api/images/${selectedImage.id}`}
            alt={selectedImage.prompt}
            className="max-w-full max-h-full object-contain"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}

      {/* Add Project Modal */}
      {showAddProjectModal && selectedImageForProject && (
        <div
          className="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center p-4"
          onClick={() => setShowAddProjectModal(false)}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Add Project to Image
              </h3>
              <button
                onClick={() => setShowAddProjectModal(false)}
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Select Project
              </label>
              <select
                value={selectedProjectToAdd}
                onChange={(e) => setSelectedProjectToAdd(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="">Choose a project...</option>
                {projects
                  .filter(project => !selectedImageForProject.projects?.some(p => p.id === project.id))
                  .map(project => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
              </select>
            </div>

            <div className="flex gap-2">
              <button
                onClick={confirmAddProject}
                disabled={!selectedProjectToAdd}
                className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors"
              >
                Add Project
              </button>
              <button
                onClick={() => setShowAddProjectModal(false)}
                className="px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-600 dark:hover:bg-gray-500 text-gray-800 dark:text-white font-medium rounded-lg transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

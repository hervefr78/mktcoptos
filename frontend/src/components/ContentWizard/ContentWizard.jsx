import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import StepSubject from './StepSubject';
import StepResearch from './StepResearch';
import StepGeneration from './StepGeneration';
import StepReview from './StepReview';
import StepPublish from './StepPublish';
import './wizard.css';

const WIZARD_STORAGE_KEY = 'content_wizard_state';

const STEPS = [
  { id: 1, label: 'Subject & Strategy', component: StepSubject },
  { id: 2, label: 'Research & Context', component: StepResearch },
  { id: 3, label: 'Content Generation', component: StepGeneration },
  { id: 4, label: 'Review & Edit', component: StepReview },
  { id: 5, label: 'Preview & Publish', component: StepPublish },
];

export default function ContentWizard() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // Get project context from URL params
  const projectId = searchParams.get('projectId');
  const projectName = searchParams.get('projectName');
  const resumePipelineId = searchParams.get('resume');
  const startNew = searchParams.get('new'); // Add ?new=true to start fresh
  const initialStep = searchParams.get('step'); // Add ?step=4 to jump to specific step

  const [currentStep, setCurrentStep] = useState(initialStep ? parseInt(initialStep) : 1);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize wizard data with defaults
  const getInitialWizardData = () => ({
    // Project context
    projectId: projectId ? parseInt(projectId) : null,
    projectName: projectName || '',
    pipelineId: resumePipelineId || null,

    // Step 1: Subject & Strategy
    topic: '',
    contentType: 'blog',
    targetAudience: '',
    tone: 'professional',
    keywords: '',

    // Step 2: Research & Context
    additionalContext: '',
    referenceFiles: [],
    knowledgeBaseIds: [],
    researchComplete: false,
    researchBrief: null,

    // Step 3: Content Generation
    generatedContent: '',
    generatedImages: [],
    isGenerating: false,

    // Step 4: Review & Edit
    editedContent: '',
    suggestions: [],

    // Step 5: Publish
    scheduledDate: null,
    deliveryChannels: [],
    exportFormat: 'md',
  });

  // Wizard data state
  const [wizardData, setWizardData] = useState(getInitialWizardData);

  // Load saved state from localStorage on mount
  useEffect(() => {
    const loadSavedState = () => {
      try {
        // Clear state if explicitly starting new content
        if (startNew === 'true') {
          localStorage.removeItem(WIZARD_STORAGE_KEY);
          setIsLoading(false);
          return;
        }

        // Try to restore saved state
        const savedState = localStorage.getItem(WIZARD_STORAGE_KEY);
        if (savedState) {
          let parsed;
          try {
            parsed = JSON.parse(savedState);
          } catch (parseError) {
            console.error('Failed to parse saved wizard state, clearing corrupted data:', parseError);
            localStorage.removeItem(WIZARD_STORAGE_KEY);
            setIsLoading(false);
            return;
          }

          // Check if saved state matches the current context
          // If resuming a specific pipeline, ONLY use saved state if pipeline IDs match
          if (resumePipelineId) {
            const samePipeline = parsed.pipelineId === resumePipelineId;
            if (!samePipeline) {
              // Don't load saved state - wrong pipeline
              setIsLoading(false);
              return;
            }
          }

          // Check if saved state is for same project context
          const sameProject = !projectId || parsed.projectId === parseInt(projectId);
          const samePipeline = resumePipelineId && parsed.pipelineId === resumePipelineId;

          if (sameProject || samePipeline) {
            setWizardData(prev => ({
              ...prev,
              ...parsed,
              // Always use URL params for project context
              projectId: projectId ? parseInt(projectId) : parsed.projectId,
              projectName: projectName || parsed.projectName,
            }));
            if (parsed.currentStep) {
              setCurrentStep(parsed.currentStep);
            }
          }
        }
      } catch (e) {
        console.error('Failed to load saved wizard state:', e);
        localStorage.removeItem(WIZARD_STORAGE_KEY);
      }
      setIsLoading(false);
    };

    loadSavedState();
  }, [projectId, projectName, resumePipelineId, startNew]);

  // Fetch pipeline data from API when resuming with a specific pipeline ID
  useEffect(() => {
    const fetchPipelineData = async () => {
      if (!resumePipelineId || isLoading) return;

      try {
        const res = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/content-pipeline/history/${resumePipelineId}?include_full_result=true`, {
          credentials: 'include',
        });
        if (res.ok) {
          const execution = await res.json();

          // Fetch timeline data to get agent metrics (stage summaries)
          let agentMetrics = {};
          try {
            const timelineRes = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/content-pipeline/history/${resumePipelineId}/timeline`, {
              credentials: 'include',
            });
            if (timelineRes.ok) {
              const timeline = await timelineRes.json();
              // Timeline.stages contains the saved agent metrics (actions, badges, diff_snippets, etc.)
              if (timeline.stages) {
                // Convert stage summaries to agentMetrics format
                agentMetrics = Object.keys(timeline.stages).reduce((acc, stage) => {
                  const stageData = timeline.stages[stage];
                  acc[stage] = {
                    status: 'complete',
                    progress: 100,
                    task: 'Complete',
                    duration: stageData.duration_seconds || 0,
                    actions: stageData.actions || [],
                    badges: stageData.badges || [],
                    details: stageData.summary || {},
                    timestamp: new Date().toISOString()
                  };
                  return acc;
                }, {});
                console.log('Restored agent metrics from timeline:', agentMetrics);
              }
            }
          } catch (timelineErr) {
            console.error('Failed to fetch timeline data:', timelineErr);
          }

          // Map pipeline execution data to wizard state
          const pipelineData = {
            pipelineId: resumePipelineId,
            projectId: execution.project_id || null,
            projectName: execution.project_name || projectName || '',

            // Extract from pipeline result if available
            topic: execution.topic || '',
            contentType: execution.content_type || 'blog',
            targetAudience: execution.audience || '',
            tone: execution.brand_voice || 'professional',

            // Content and results
            generatedContent: execution.final_content || '',
            pipelineResult: execution.result || null,

            // Agent metrics for review - RESTORED FROM DATABASE
            agentMetrics: agentMetrics,

            // Execution metadata
            executionId: execution.id,
            status: execution.status,
          };

          setWizardData(prev => ({
            ...prev,
            ...pipelineData
          }));
        } else {
          console.error('Failed to fetch pipeline data:', res.status);
        }
      } catch (err) {
        console.error('Error fetching pipeline data:', err);
      }
    };

    fetchPipelineData();
  }, [resumePipelineId, isLoading, projectName]);

  // Fetch project data to get language setting and sub-project info
  useEffect(() => {
    const fetchProjectData = async () => {
      if (!projectId || isLoading) return;

      try {
        const res = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/projects/${projectId}`, {
          credentials: 'include',
        });
        if (res.ok) {
          const project = await res.json();

          const projectData = {
            projectLanguage: project.language || 'auto',
            isSubProject: Boolean(project.parent_project_id),
            parentProjectId: project.parent_project_id,
            parentProjectName: project.parent_project_name,
            inheritTone: project.inherit_tone,
            projectContentType: project.content_type,
            // Set contentType from project for sub-projects (already selected when creating sub-project)
            ...(project.content_type && { contentType: project.content_type }),
          };

          // If this is a sub-project, fetch parent project's completed content
          if (project.parent_project_id) {
            try {
              // Fetch parent project details
              const parentRes = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/projects/${project.parent_project_id}`, {
                credentials: 'include',
              });
              if (parentRes.ok) {
                const parentProject = await parentRes.json();
                projectData.parentProject = parentProject;

                // Fetch parent project's completed content (latest completed pipeline)
                const pipelinesRes = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/content-pipeline/history?project_id=${project.parent_project_id}&status=completed&limit=1`, {
                  credentials: 'include',
                });
                if (pipelinesRes.ok) {
                  const pipelines = await pipelinesRes.json();
                  if (pipelines && pipelines.executions && pipelines.executions.length > 0) {
                    const latestPipeline = pipelines.executions[0];
                    projectData.parentContent = {
                      content: latestPipeline.final_content || '',
                      topic: latestPipeline.topic || '',
                      tone: latestPipeline.brand_voice || '',
                      audience: latestPipeline.audience || '',
                      keywords: latestPipeline.keywords || '',
                      pipelineId: latestPipeline.id,
                    };

                    // Clear any previous warning when content is successfully loaded
                    projectData.parentContentWarning = null;

                    // Pre-populate tone if inheriting
                    if (project.inherit_tone && latestPipeline.brand_voice) {
                      projectData.tone = latestPipeline.brand_voice;
                    }

                    // Pre-populate audience from parent content
                    if (latestPipeline.audience) {
                      projectData.targetAudience = latestPipeline.audience;
                    }
                  } else {
                    projectData.parentContentWarning = 'Parent project has no completed content yet';
                    projectData.parentContent = null;
                  }
                } else {
                  projectData.parentContentWarning = 'Failed to fetch parent project content';
                  projectData.parentContent = null;
                }
              }
            } catch (parentErr) {
              console.error('Error fetching parent project data:', parentErr);
              projectData.parentContentError = 'Failed to load parent project information';
            }
          }

          // Update wizard data with project information
          setWizardData(prev => ({
            ...prev,
            ...projectData
          }));
        } else {
          console.error('Failed to fetch project data:', res.status);
        }
      } catch (err) {
        console.error('Error fetching project data:', err);
      }
    };

    fetchProjectData();
  }, [projectId, isLoading]);

  // Save wizard state to localStorage on changes
  useEffect(() => {
    if (!isLoading) {
      try {
        const stateToSave = {
          ...wizardData,
          currentStep,
          savedAt: new Date().toISOString(),
        };
        localStorage.setItem(WIZARD_STORAGE_KEY, JSON.stringify(stateToSave));
      } catch (e) {
        console.error('Failed to save wizard state:', e);
      }
    }
  }, [wizardData, currentStep, isLoading]);

  // Agent activity state - matches new 7-agent pipeline
  const [agents, setAgents] = useState([
    { id: 'trends_keywords', name: 'Trends & Keywords', status: 'pending', progress: 0, task: '' },
    { id: 'tone_of_voice', name: 'Tone of Voice', status: 'pending', progress: 0, task: '' },
    { id: 'structure_outline', name: 'Structure & Outline', status: 'pending', progress: 0, task: '' },
    { id: 'writer', name: 'Writer', status: 'pending', progress: 0, task: '' },
    { id: 'seo_optimizer', name: 'SEO Optimizer', status: 'pending', progress: 0, task: '' },
    { id: 'originality_check', name: 'Originality Check', status: 'pending', progress: 0, task: '' },
    { id: 'final_review', name: 'Final Review', status: 'pending', progress: 0, task: '' },
  ]);

  const [metrics, setMetrics] = useState({
    totalTime: 0,
    tokensUsed: 0,
    estimatedCost: 0,
  });

  const updateWizardData = (updates) => {
    setWizardData(prev => ({ ...prev, ...updates }));
  };

  // Clear wizard state (call after successful publish)
  const clearWizardState = () => {
    localStorage.removeItem(WIZARD_STORAGE_KEY);
    setWizardData(getInitialWizardData());
    setCurrentStep(1);
  };

  // Navigate back to projects
  const handleBackToProjects = () => {
    navigate('/projects');
  };

  const updateAgent = (agentId, updates) => {
    setAgents(prev => prev.map(agent =>
      agent.id === agentId ? { ...agent, ...updates } : agent
    ));
  };

  const nextStep = () => {
    if (currentStep < STEPS.length) {
      setCurrentStep(prev => prev + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const goToStep = (step) => {
    if (step >= 1 && step <= STEPS.length) {
      setCurrentStep(step);
    }
  };

  const CurrentStepComponent = STEPS[currentStep - 1].component;

  // Show loading state
  if (isLoading) {
    return (
      <div className="content-wizard">
        <div className="wizard-loading">
          <div className="loading-spinner"></div>
          <p>Loading wizard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="content-wizard">
      {/* Progress Header */}
      <div className="wizard-header">
        <div className="wizard-title-section">
          {projectName && (
            <button className="back-to-projects" onClick={handleBackToProjects}>
              ← Back to Projects
            </button>
          )}
          {projectName && (
            <div style={{
              fontSize: '0.9rem',
              color: '#6b7280',
              fontWeight: '500',
              marginBottom: '0.25rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <span style={{ color: '#9ca3af' }}>Project:</span>
              <span style={{
                color: '#3b82f6',
                fontWeight: '600',
                fontSize: '1rem'
              }}>{projectName}</span>
            </div>
          )}
          <h1>Create New Content</h1>
        </div>
        <div className="wizard-progress">
          {STEPS.map((step, index) => (
            <div
              key={step.id}
              className={`progress-step ${currentStep === step.id ? 'active' : ''} ${currentStep > step.id ? 'completed' : ''}`}
              onClick={() => currentStep > step.id && goToStep(step.id)}
            >
              <div className="step-number">
                {currentStep > step.id ? '✓' : step.id}
              </div>
              <span className="step-label">{step.label}</span>
              {index < STEPS.length - 1 && <div className="step-connector" />}
            </div>
          ))}
        </div>
      </div>

      <div className="wizard-body">
        {/* Main Content Area */}
        <div className="wizard-main">
          <CurrentStepComponent
            data={wizardData}
            updateData={updateWizardData}
            agents={agents}
            updateAgent={updateAgent}
            metrics={metrics}
            setMetrics={setMetrics}
            onNext={nextStep}
            onBack={prevStep}
            currentStep={currentStep}
            totalSteps={STEPS.length}
            clearWizardState={clearWizardState}
            onBackToProjects={handleBackToProjects}
          />
        </div>
      </div>
    </div>
  );
}

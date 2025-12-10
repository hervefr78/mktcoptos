# Integrated Campaigns Implementation Guide

## Overview
This document provides a comprehensive guide for the integrated campaigns feature implementation. The feature allows users to create campaigns with multiple linked projects where sub-projects inherit tone and use main content as source material.

---

## ✅ COMPLETED (Parts 1-3)

### Part 1: Database Schema
**Files Changed:**
- `backend/alembic/versions/017_add_integrated_campaigns.py` (NEW)
- `backend/app/models.py`

**Changes:**
- Added `campaign_type` (standalone/integrated) and `default_language` to Campaign model
- Added `parent_project_id`, `is_main_project`, `inherit_tone`, `content_type` to Project model
- Added `campaign_id` to RagDocument model for campaign-scoped RAG filtering
- Created self-referential relationship for parent/sub projects

### Part 2: Backend API
**Files Changed:**
- `backend/app/campaigns_routes.py`
- `backend/app/projects_routes.py`

**Changes:**
- Updated Campaign API models to include campaign_type and hierarchy
- Updated Project API models to include parent/sub relationships
- Added validation for parent-child relationships
- Auto-inherit tone from parent when `inherit_tone` is true
- Return full project hierarchy in campaign responses

### Part 3: Frontend Campaign UI
**Files Changed:**
- `frontend/src/components/Campaigns/CampaignsPage.jsx`
- `frontend/src/components/Campaigns/CampaignModal.jsx`

**Changes:**
- Display campaign type badges (🔗 Integrated / 📄 Standalone)
- Show project hierarchy for integrated campaigns
- Add campaign type selector in create/edit modal
- Visual indicators for main projects (🎯) and sub-projects (└─►)

---

## 📋 REMAINING WORK

### Priority 1: Core Functionality

#### 1. Run Database Migration
**Location:** Backend deployment
**Command:** `alembic upgrade head`
**Description:** Apply the database schema changes before any testing

#### 2. Update ProjectsPage with Relationship Badges
**File:** `frontend/src/components/Projects/ProjectsPage.jsx`
**Required Changes:**
```javascript
// In the project card rendering:
{project.is_main_project && (
  <span className="badge" style={{background: '#dbeafe', color: '#1e40af'}}>
    🎯 Main Project
  </span>
)}
{project.parent_project_id && (
  <span className="badge" style={{background: '#fef3c7', color: '#92400e'}}>
    🔗 Sub-Project of: {project.parent_project_name}
  </span>
)}
{project.sub_projects && project.sub_projects.length > 0 && (
  <div className="sub-projects-info">
    Linked to {project.sub_projects.length} sub-project(s)
  </div>
)}
```

#### 3. Create CampaignCreation Full-Page Component
**File:** `frontend/src/components/Campaigns/CampaignCreation.jsx` (NEW)
**Purpose:** Multi-step form for creating integrated campaigns with projects

**Structure:**
```javascript
const CampaignCreation = () => {
  const [step, setStep] = useState(1); // 1: Type, 2: Details, 3: Projects
  const [campaignData, setCampaignData] = useState({});
  const [mainProjects, setMainProjects] = useState([]);

  // Step 1: Campaign Type Selection
  // Step 2: Campaign Details (name, description, category)
  // Step 3: Define Main Projects and Sub-Projects

  return (/* Multi-step form UI */);
};
```

**Key Features:**
- Step 1: Choose standalone vs integrated
- Step 2: Basic campaign info (reuse existing modal fields)
- Step 3: Add main projects with their sub-projects
- Each main project can have multiple sub-projects
- Sub-projects show inherited tone badge
- Preview campaign structure before saving

#### 4. Create CampaignDetailsPage
**File:** `frontend/src/components/Campaigns/CampaignDetailsPage.jsx` (exists but needs updates)
**Required Enhancements:**
```javascript
// Display full campaign hierarchy
// Show status for each project
// Allow adding new projects to existing campaigns
// Show content generation status
// Link to content wizard for sub-projects
```

**UI Sections:**
- Campaign header with type badge
- Main projects section (expandable)
- Each main project shows its sub-projects
- Status indicators (pending/in-progress/completed)
- Actions: Add Main Project, Add Sub-Project, Create Content

### Priority 2: Content Generation Integration

#### 5. Update ContentWizard for Sub-Projects
**File:** `frontend/src/components/ContentWizard/ContentWizard.jsx`
**Purpose:** Detect sub-project context and modify workflow

**Required Changes:**
```javascript
// In useEffect when loading project:
useEffect(() => {
  if (projectId) {
    const project = await fetchProject(projectId);
    if (project.parent_project_id) {
      // This is a sub-project
      const parentProject = await fetchProject(project.parent_project_id);
      const parentContent = await fetchCompletedContent(project.parent_project_id);

      setWizardData({
        ...wizardData,
        tone: project.inherit_tone ? parentProject.default_tone : wizardData.tone,
        parentContent: parentContent,
        contentType: project.content_type,
        isSubProject: true,
      });
    }
  }
}, [projectId]);
```

**New StepSubProject Component:**
```javascript
// Show before StepSubject for sub-projects
const StepSubProject = ({ parentContent, onNext }) => {
  return (
    <div className="wizard-step">
      <h2>Creating Sub-Content</h2>
      <div className="parent-content-summary">
        <h3>📄 Source Content: {parentContent.topic}</h3>
        <p>Your content will be based on this main project</p>
        <div className="ai-suggestions">
          <h4>💡 AI Suggestions:</h4>
          <ul>
            <li>Focus on key benefits from main content</li>
            <li>Adapt tone for {projectData.contentType}</li>
            <li>Maintain consistent messaging</li>
          </ul>
        </div>
      </div>
      <button onClick={onNext}>Continue to Subject →</button>
    </div>
  );
};
```

### Priority 3: RAG Integration

#### 6. Update RAG System for Campaign-Scoped Documents
**Files:**
- `backend/app/rag_routes.py` (if exists, or create new routes)
- Update wherever RAG documents are queried

**Required Changes:**
```python
# In RAG document retrieval:
def get_rag_documents_for_project(project_id: int, db: Session):
    project = db.query(Project).filter(Project.id == project_id).first()

    if project.parent_project_id:
        # Sub-project: get parent's completed content + campaign docs
        parent_project = db.query(Project).filter(
            Project.id == project.parent_project_id
        ).first()

        # Get completed content from parent
        parent_content = db.query(PipelineExecution).filter(
            PipelineExecution.project_id == parent_project.id,
            PipelineExecution.status == 'completed'
        ).order_by(PipelineExecution.created_at.desc()).first()

        # Add parent content to RAG
        if parent_content:
            # Store parent content as RAG document
            # Tag with campaign_id for filtering
            pass

        # Get campaign-scoped documents
        campaign_docs = db.query(RagDocument).filter(
            RagDocument.campaign_id == project.campaign_id
        ).all()

        return campaign_docs + [parent_content_as_rag_doc]

    # Regular project: get project-specific and org docs
    return db.query(RagDocument).filter(
        RagDocument.project_id == project_id
    ).all()
```

#### 7. Auto-Add Completed Main Content to RAG
**File:** Backend content pipeline completion handler
**Purpose:** When main project content is completed, automatically add to RAG

**Implementation:**
```python
# In content pipeline completion:
def on_pipeline_complete(execution: PipelineExecution, db: Session):
    project = db.query(Project).filter(Project.id == execution.project_id).first()

    if project.is_main_project and execution.status == 'completed':
        # Create RAG document from completed content
        rag_doc = RagDocument(
            filename=f"main_content_{project.id}_{execution.id}.txt",
            original_filename=f"{project.name}_content.txt",
            file_path=f"/rag/campaign_{project.campaign_id}/main_{project.id}.txt",
            organization_id=project.organization_id,
            project_id=project.id,
            campaign_id=project.campaign_id,
            user_id=execution.user_id,
            collection="knowledge_base",
            status="processing",
        )

        db.add(rag_doc)
        db.commit()

        # Process document (vectorize, chunk, etc.)
        process_rag_document(rag_doc.id)
```

### Priority 4: Polish & UX Enhancements

#### 8. Add Project Creation from Campaign Details
**Location:** CampaignDetailsPage
**Feature:** "Add Sub-Project" button next to each main project

**Flow:**
1. User clicks "Add Sub-Project" on a main project
2. Opens modal with pre-filled parent_project_id
3. Shows inherited tone (read-only or with override option)
4. User fills in sub-project name and content type
5. Creates project and returns to campaign details

#### 9. Update API Config
**File:** `frontend/src/config/api.js`
**Add if missing:**
```javascript
export const API_ENDPOINTS = {
  // ... existing endpoints
  CAMPAIGN_PROJECTS: (campaignId) => `/api/campaigns/${campaignId}/projects`,
  PROJECT_SUB_PROJECTS: (projectId) => `/api/projects/${projectId}/sub-projects`,
};
```

#### 10. Add Navigation Updates
**File:** Frontend routing
**Ensure routes exist:**
```javascript
// In App.jsx or routing file:
<Route path="/campaigns/create" element={<CampaignCreation />} />
<Route path="/campaigns/:id" element={<CampaignDetailsPage />} />
```

---

## 🧪 TESTING CHECKLIST

### Database
- [ ] Run migration successfully
- [ ] Create standalone campaign
- [ ] Create integrated campaign
- [ ] Create main project in integrated campaign
- [ ] Create sub-project linked to main project
- [ ] Verify parent_project_id foreign key works
- [ ] Verify campaign_id on rag_documents

### API
- [ ] GET /api/campaigns returns campaign_type
- [ ] GET /api/campaigns/:id shows project hierarchy
- [ ] POST /api/campaigns with campaign_type='integrated' works
- [ ] POST /api/projects with parent_project_id works
- [ ] POST /api/projects validates parent is in same campaign
- [ ] Projects inherit tone when inherit_tone=true
- [ ] PUT /api/projects updates parent relationships

### Frontend
- [ ] Campaigns page shows type badges
- [ ] Integrated campaigns display project tree
- [ ] Creating new campaign allows type selection
- [ ] Projects page shows main/sub badges
- [ ] Can navigate to campaign details
- [ ] Campaign details shows full hierarchy

### Content Generation
- [ ] Creating content for sub-project loads parent content
- [ ] Sub-project uses inherited tone
- [ ] Parent content appears in RAG context
- [ ] Generated sub-content maintains consistency

---

## 📊 PROGRESS SUMMARY

| Component | Status | Files | Progress |
|-----------|--------|-------|----------|
| Database Schema | ✅ Complete | 2 files | 100% |
| Backend API | ✅ Complete | 2 files | 100% |
| Campaign UI | ✅ Complete | 2 files | 100% |
| Projects UI | ⏳ Pending | 1 file | 0% |
| Campaign Creation Flow | ⏳ Pending | 1 file (new) | 0% |
| Campaign Details | ⏳ Pending | 1 file | 0% |
| Content Wizard | ⏳ Pending | 2 files | 0% |
| RAG Integration | ⏳ Pending | 2+ files | 0% |
| Testing | ⏳ Pending | - | 0% |

**Overall Progress:** 30% (3/10 major components)

---

## 🚀 NEXT STEPS

### Immediate (Required for MVP)
1. Run database migration
2. Update ProjectsPage with badges
3. Test creating integrated campaigns via API

### Short-term (For Full Feature)
4. Build CampaignCreation full-page component
5. Update CampaignDetailsPage
6. Integrate with ContentWizard

### Long-term (Enhancements)
7. Implement RAG campaign-scoping
8. Add auto-RAG for completed main content
9. Add bulk project creation
10. Add campaign templates

---

## 💡 IMPLEMENTATION TIPS

### When Building CampaignCreation Component
- Reuse CampaignModal logic for basic fields
- Use a wizard/stepper pattern (Material-UI Stepper or custom)
- Validate project relationships client-side before saving
- Show real-time preview of campaign structure
- Allow reordering main projects

### When Updating ContentWizard
- Check for parent_project_id early in the flow
- Fetch parent content before showing first step
- Show a special "Sub-Content" badge in wizard header
- Pre-populate fields from parent where appropriate
- Add "View Parent Content" link for reference

### For RAG Integration
- Use campaign_id as primary filter for sub-projects
- Store parent content as special RAG document type
- Add metadata: `{"source": "parent_project", "project_id": 123}`
- Weight parent content higher in relevance scoring
- Show source attribution in generated content

---

## 📝 NOTES

### Design Decisions Made
1. **Multiple Main Projects:** Campaigns can have multiple main projects (e.g., landing page + blog post), each with their own sub-projects
2. **Tone Inheritance:** Optional but defaults to true; can be overridden per sub-project
3. **Campaign Scoping:** RAG documents are scoped to campaign, not just project
4. **Validation:** Parent projects must be in the same campaign as sub-projects

### Future Enhancements (Not in Scope)
- Campaign analytics dashboard
- A/B testing between sub-project variations
- Automated scheduling for campaign rollout
- Cross-campaign content reuse
- Campaign templates library
- Multi-language campaigns with translation workflows

---

**Last Updated:** 2025-12-02
**Implementation Status:** Parts 1-3 Complete (30%)
**Next Session:** Focus on ProjectsPage badges and CampaignCreation component

# Checkpoint Mode Guide

## Overview

Checkpoint Mode is a manual approval workflow that allows you to review and approve the output of each stage in the content generation pipeline before proceeding to the next stage. This gives you full control over the content creation process and ensures quality at every step.

## Table of Contents

- [Workflow Comparison](#workflow-comparison)
- [Enabling Checkpoint Mode](#enabling-checkpoint-mode)
- [Automatic Mode Workflow](#automatic-mode-workflow)
- [Checkpoint Mode Workflow](#checkpoint-mode-workflow)
- [Reviewing Agent Work](#reviewing-agent-work)
- [Checkpoint Actions](#checkpoint-actions)

---

## Workflow Comparison

### Automatic Mode (Default)
- Pipeline runs continuously from start to finish
- All 7 agents execute sequentially without pausing
- No manual intervention required
- Fastest completion time
- Best for: Quick content generation, trusted workflows, batch processing

### Checkpoint Mode
- Pipeline pauses after each agent completes
- User reviews the agent's output
- User approves or provides feedback before continuing
- Full control over content quality
- Best for: Critical content, learning agent behavior, fine-tuning outputs

---

## Enabling Checkpoint Mode

### Step 1: Open Settings
1. Navigate to **Settings** from the sidebar
2. Click on the **Preferences** tab

### Step 2: Enable Checkpoint Mode
1. Find the checkbox labeled **"Enable Checkpoint Mode (Manual approval at each pipeline stage)"**
2. Check the box to enable checkpoint mode
3. The setting is automatically saved to your browser's localStorage

### Step 3: Verify Mode
When you start a new content generation:
1. Go to the **Content Generation** page
2. Before clicking "Start Content Generation", you'll see a mode indicator:
   - **🎯 Checkpoint Mode Active**: You will review and approve each stage before proceeding
   - **⚡ Automatic Mode**: Pipeline will run continuously without pausing

---

## Automatic Mode Workflow

```
User Clicks "Start Generation"
         ↓
    Agent 1: Trends & Keywords
         ↓
    Agent 2: Tone of Voice
         ↓
    Agent 3: Structure & Outline
         ↓
    Agent 4: Writer
         ↓
    Agent 5: SEO Optimizer
         ↓
    Agent 6: Originality Check
         ↓
    Agent 7: Final Review
         ↓
    Generation Complete
```

**Total time**: ~2-5 minutes (depending on content complexity)

**User interaction**: None during generation, review final output at the end

---

## Checkpoint Mode Workflow

```
User Clicks "Start Generation"
         ↓
    Agent 1: Trends & Keywords
         ↓
    ⏸️  CHECKPOINT: Review trends/keywords output
         ↓
    User Action: Approve / Edit / Add Instructions
         ↓
    Agent 2: Tone of Voice
         ↓
    ⏸️  CHECKPOINT: Review tone analysis
         ↓
    User Action: Approve / Edit / Add Instructions
         ↓
    Agent 3: Structure & Outline
         ↓
    ⏸️  CHECKPOINT: Review content structure
         ↓
    User Action: Approve / Edit / Add Instructions
         ↓
    Agent 4: Writer
         ↓
    ⏸️  CHECKPOINT: Review written content
         ↓
    User Action: Approve / Edit / Add Instructions
         ↓
    Agent 5: SEO Optimizer
         ↓
    ⏸️  CHECKPOINT: Review SEO optimizations
         ↓
    User Action: Approve / Edit / Add Instructions
         ↓
    Agent 6: Originality Check
         ↓
    ⏸️  CHECKPOINT: Review originality score
         ↓
    User Action: Approve / Edit / Add Instructions
         ↓
    Agent 7: Final Review
         ↓
    ⏸️  CHECKPOINT: Review final polished content
         ↓
    User Action: Approve / Complete
         ↓
    Generation Complete
```

**Total time**: Variable (depends on review time at each checkpoint)

**User interaction**: Review and approve at 7 checkpoints throughout the process

---

## Reviewing Agent Work

### Checkpoint Dialog Interface

When a checkpoint is reached, a dialog appears with:

#### 1. Agent Information
- **Agent Name**: Which agent just completed (e.g., "Trends & Keywords")
- **Stage Number**: Current progress (e.g., "Stage 2 of 7")

#### 2. Stage Output
- **Full Output**: The complete result from the agent
- **Summary**: Key findings and decisions made by the agent
- **Metrics**: Token usage, processing time, cost

#### 3. Stage Context
You can review what the agent:
- **Received as input**: Previous stage results, user requirements
- **Analyzed**: Data sources, patterns identified
- **Produced**: New content, recommendations, optimizations

### What to Look For

#### Trends & Keywords Agent
- Are the identified trends relevant to your topic?
- Do the keywords align with your target audience?
- Are search volumes and competition levels reasonable?

#### Tone of Voice Agent
- Does the tone match your brand voice?
- Is the suggested writing style appropriate?
- Are the tone characteristics well-defined?

#### Structure & Outline Agent
- Is the content structure logical and complete?
- Are headings and subheadings clear?
- Does the outline cover all required topics?

#### Writer Agent
- Is the content well-written and engaging?
- Does it follow the approved outline?
- Is the tone consistent throughout?

#### SEO Optimizer Agent
- Are SEO recommendations reasonable?
- Have keywords been naturally integrated?
- Are meta descriptions and titles optimized?

#### Originality Check Agent
- Is the originality score acceptable (typically >85%)?
- Are there any plagiarism concerns?
- Is the content sufficiently unique?

#### Final Review Agent
- Is the final content polished and professional?
- Have all previous feedback items been addressed?
- Is the content ready for publication?

---

## Checkpoint Actions

At each checkpoint, you have several options:

### 1. Approve (Continue)
```
Action: Click "Approve & Continue"
Result: Pipeline advances to the next agent
Use when: You're satisfied with the current stage output
```

### 2. Edit Output
```
Action: Click "Edit Output", modify the text, then "Save & Continue"
Result: Your edited version is passed to the next agent
Use when: Minor tweaks needed before proceeding
```

### 3. Add Instructions
```
Action: Click "Add Instructions", provide feedback/guidance, then "Continue with Instructions"
Result: Next agent receives your instructions along with current output
Use when: You want the next agent to focus on specific aspects
```

Example instructions:
- "Focus more on technical benefits rather than features"
- "Make the tone more conversational and less formal"
- "Add more data and statistics to support the arguments"
- "Keep the content shorter and more concise"

### 4. Regenerate Current Stage
```
Action: Click "Regenerate", optionally add instructions, then "Regenerate Stage"
Result: Current agent re-runs with your new instructions
Use when: The output doesn't meet expectations and needs a redo
```

### 5. Stop Pipeline
```
Action: Click "Stop Pipeline"
Result: Generation stops, you return to the content wizard
Use when: You need to make major changes to the original requirements
```

---

## Best Practices

### When to Use Checkpoint Mode

✅ **Use Checkpoint Mode when:**
- Creating high-stakes content (press releases, executive communications)
- Learning how the AI agents work
- Fine-tuning content for specific audiences
- Quality is more important than speed
- You want to guide the content direction at each stage

❌ **Skip Checkpoint Mode when:**
- Generating draft content for review
- Creating multiple variations quickly
- Time is limited
- You trust the automatic pipeline for your use case

### Tips for Effective Reviews

1. **Be Specific with Instructions**: Instead of "make it better", say "add more examples" or "reduce word count by 20%"

2. **Review Metrics**: Check token usage and costs at each stage to understand where the AI is spending effort

3. **Save Sessions**: Your checkpoint session is automatically saved, so you can resume later if needed

4. **Learn from Agents**: Use checkpoint mode to understand what each agent contributes, then switch to automatic mode once you're confident

5. **Cumulative Instructions**: Remember that instructions at early stages can affect all subsequent stages

---

## Technical Details

### Session Management
- Each checkpoint session has a unique session ID
- Sessions are stored in the database with timestamps
- Sessions automatically expire after 24 hours of inactivity
- You can have only one active checkpoint session per pipeline execution

### Data Flow
```
User Input → Agent 1 → [Checkpoint] → Agent 2 → [Checkpoint] → ... → Final Output
                ↓                      ↓
            User Review            User Review
                ↓                      ↓
          Instructions            Instructions
```

### API Endpoints
- `POST /api/checkpoint/{session_id}/action` - Submit checkpoint action
- `GET /api/checkpoint/{session_id}/status` - Get current checkpoint status
- `POST /api/checkpoint/{session_id}/cancel` - Cancel checkpoint session

### Real-time Updates
- Checkpoint dialogs appear automatically via Server-Sent Events (SSE)
- Pipeline status updates in real-time
- No page refresh needed

---

## Troubleshooting

### Checkpoint Dialog Not Appearing
1. Check browser console for errors
2. Verify your session hasn't expired (24-hour limit)
3. Ensure SSE connection is active (check network tab)

### Lost Checkpoint Session
1. Check the database for active sessions under your user ID
2. Sessions auto-expire after 24 hours
3. Starting a new generation creates a new session

### Cannot Edit Output
1. Ensure you're in checkpoint mode (check settings)
2. Verify the checkpoint dialog is active
3. Check that the stage has actually completed

---

## FAQ

**Q: Can I switch modes during generation?**
A: No, the mode is set when you start generation and cannot be changed mid-pipeline.

**Q: How long do checkpoint sessions last?**
A: Sessions expire after 24 hours of inactivity but remain active as long as you're interacting.

**Q: Can I go back to a previous checkpoint?**
A: Currently, no. You can only move forward or regenerate the current stage.

**Q: What happens if I close the browser during a checkpoint?**
A: Your session is saved in the database. When you return and refresh, you can resume from where you left off.

**Q: Do checkpoint sessions cost more?**
A: No, the token usage and costs are the same. You're just pausing to review between stages.

**Q: Can multiple users share a checkpoint session?**
A: No, checkpoint sessions are tied to a specific user and pipeline execution.

---

## Getting Started

1. **Enable checkpoint mode** in Settings → Preferences
2. **Start a new content generation** from the dashboard
3. **Verify the mode indicator** shows "🎯 Checkpoint Mode Active"
4. **Click "Start Content Generation"**
5. **Review the first checkpoint** when it appears
6. **Take one of the available actions** (Approve, Edit, Add Instructions, etc.)
7. **Continue through all 7 stages** until completion

Enjoy having full control over your content generation pipeline!

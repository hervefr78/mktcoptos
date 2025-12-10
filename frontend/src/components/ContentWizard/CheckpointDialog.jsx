import React, { useState } from 'react';

/**
 * CheckpointDialog - Modal for manual pipeline approval
 *
 * Displays when checkpoint_reached SSE event is received.
 * Shows stage output preview and action buttons.
 */
const CheckpointDialog = ({ checkpoint, onAction, onClose }) => {
  const [editMode, setEditMode] = useState(false);
  const [editedText, setEditedText] = useState('');
  const [instructions, setInstructions] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  if (!checkpoint) return null;

  const { stage, stage_output, session_id, previous_results = {} } = checkpoint;

  // Get preview text from stage output
  const getPreviewText = () => {
    if (!stage_output) return 'No output available';

    // Extract relevant text based on stage
    switch (stage) {
      case 'trends_keywords':
        const keywords = stage_output.primary_keywords || [];
        const angles = stage_output.angle_ideas || [];
        return `Keywords: ${keywords.join(', ')}\n\nAngles:\n${angles.map((a, i) => `${i + 1}. ${a.angle || a}`).join('\n')}`;

      case 'tone_of_voice':
        const profile = stage_output.style_profile || {};
        return `Tone: ${profile.tone || 'N/A'}\nFormality: ${profile.formality || 'N/A'}\nVoice: ${profile.voice_characteristics || 'N/A'}`;

      case 'structure_outline':
        const sections = stage_output.sections || [];
        return `Content Promise: ${stage_output.content_promise || 'N/A'}\n\nSections:\n${sections.map((s, i) => `${i + 1}. ${s.title || s.heading}\n   ${s.key_points?.join(', ') || ''}`).join('\n\n')}`;

      case 'writer':
        return stage_output.full_text || stage_output.text || 'No content';

      case 'seo_optimizer':
        const seo = stage_output.on_page_seo || {};
        const writerOutput = previous_results.writer || {};
        const originalText = writerOutput.full_text || '';

        // Extract original title from writer output (first H1)
        let originalTitle = '(not set)';
        if (originalText) {
          const lines = originalText.split('\n');
          for (const line of lines.slice(0, 5)) {
            if (line.trim().startsWith('# ')) {
              originalTitle = line.trim().substring(2).trim();
              break;
            }
          }
        }

        // Build detailed before/after comparison
        let output = '📊 WHAT CHANGED:\n\n';

        // 1. Focus Keyword
        output += `🎯 FOCUS KEYWORD:\n`;
        output += `   Set to: "${seo.focus_keyword || 'N/A'}"\n\n`;

        // 2. SEO & GEO Title
        output += `📝 SEO & GEO TITLE TAG:\n`;
        output += `   BEFORE: ${originalTitle}\n`;
        output += `   AFTER:  ${seo.title_tag || 'N/A'}\n`;
        output += `   Length: ${(seo.title_tag || '').length} chars ${(seo.title_tag || '').length >= 50 && (seo.title_tag || '').length <= 60 ? '✓ optimal' : '⚠️ needs adjustment'}\n\n`;

        // 3. Meta Description
        output += `📄 META DESCRIPTION (for search results):\n`;
        output += `   BEFORE: (not set)\n`;
        output += `   AFTER:  ${seo.meta_description || 'N/A'}\n`;
        output += `   Length: ${(seo.meta_description || '').length} chars ${(seo.meta_description || '').length >= 150 && (seo.meta_description || '').length <= 160 ? '✓ optimal' : '⚠️ needs adjustment'}\n\n`;

        // 4. Content preview
        output += `📰 OPTIMIZED CONTENT (first 400 chars):\n`;
        output += `${stage_output.optimized_text?.substring(0, 400) || ''}...\n\n`;

        output += `ℹ️  The SEO & GEO agent has optimized your content for search engines and AI answer engines by:\n`;
        output += `   • Setting a focus keyword to target\n`;
        output += `   • Creating an SEO & GEO-friendly title tag\n`;
        output += `   • Writing a compelling meta description\n`;
        output += `   • Integrating keywords naturally into the content\n`;
        output += `   • Structuring content for LLM extraction (TL;DR, question headings, FAQ)`;

        return output;

      case 'originality_check':
        const score = stage_output.originality_score || 'N/A';
        const flagged = stage_output.flagged_passages || [];

        let origOutput = '🔍 ORIGINALITY CHECK RESULTS:\n\n';
        origOutput += `📊 Originality Score: ${score}\n`;
        origOutput += `⚠️  Flagged Passages: ${flagged.length}\n\n`;

        if (flagged.length > 0) {
          origOutput += `📝 REWRITES MADE (showing top ${Math.min(3, flagged.length)}):\n\n`;

          flagged.slice(0, 3).forEach((passage, idx) => {
            origOutput += `${idx + 1}. ${passage.reason || 'Improved originality'}\n`;
            origOutput += `   BEFORE: ${(passage.original_text || '').substring(0, 150)}...\n`;
            origOutput += `   AFTER:  ${(passage.rewritten_text || '').substring(0, 150)}...\n\n`;
          });
        }

        origOutput += `📰 FULL REWRITTEN CONTENT (first 300 chars):\n`;
        origOutput += `${stage_output.rewritten_text?.substring(0, 300) || stage_output.text?.substring(0, 300) || ''}...`;

        return origOutput;

      case 'final_review':
        const changes = stage_output.change_log || [];
        const seoOutput = previous_results.seo_optimizer || previous_results.originality_check || {};
        const beforeFinalText = seoOutput.optimized_text || seoOutput.rewritten_text || '';

        let finalOutput = '✨ FINAL EDITORIAL REVIEW:\n\n';
        finalOutput += `📝 Editorial Changes Made: ${changes.length}\n\n`;

        if (changes.length > 0) {
          finalOutput += `CHANGES:\n`;
          changes.slice(0, 5).forEach((change, idx) => {
            finalOutput += `${idx + 1}. ${change}\n`;
          });
          finalOutput += `\n`;
        }

        // Show a sample before/after if content changed
        if (beforeFinalText && stage_output.final_text && beforeFinalText !== stage_output.final_text) {
          const beforeParas = beforeFinalText.split('\n\n');
          const afterParas = stage_output.final_text.split('\n\n');

          // Find first different paragraph
          for (let i = 0; i < Math.min(beforeParas.length, afterParas.length); i++) {
            if (beforeParas[i] !== afterParas[i] && beforeParas[i].length > 50) {
              finalOutput += `📄 EXAMPLE EDIT:\n`;
              finalOutput += `   BEFORE: ${beforeParas[i].substring(0, 150)}...\n`;
              finalOutput += `   AFTER:  ${afterParas[i].substring(0, 150)}...\n\n`;
              break;
            }
          }
        }

        finalOutput += `📰 FINAL POLISHED CONTENT (first 300 chars):\n`;
        finalOutput += `${stage_output.final_text?.substring(0, 300) || ''}...`;

        return finalOutput;

      default:
        return JSON.stringify(stage_output, null, 2).substring(0, 500) + '...';
    }
  };

  const handleApprove = async () => {
    setIsProcessing(true);
    await onAction({
      action: 'approve',
      next_agent_instructions: instructions || null
    });
    setInstructions('');
    setIsProcessing(false);
  };

  const handleEdit = () => {
    setEditMode(true);
    setEditedText(getPreviewText());
  };

  const handleSaveEdit = async () => {
    setIsProcessing(true);
    // In a real implementation, parse editedText back to structured format
    // For V1, we'll keep it simple and just pass the text
    await onAction({
      action: 'edit',
      edited_output: { ...stage_output, text: editedText },
      next_agent_instructions: instructions || null
    });
    setEditMode(false);
    setInstructions('');
    setIsProcessing(false);
  };

  const handleApproveAll = async () => {
    if (window.confirm('Approve all remaining stages automatically?')) {
      setIsProcessing(true);
      await onAction({ action: 'approve_all' });
      setIsProcessing(false);
    }
  };

  const handleCancel = async () => {
    if (window.confirm('Cancel pipeline execution?')) {
      setIsProcessing(true);
      await onAction({ action: 'cancel' });
      setIsProcessing(false);
      onClose();
    }
  };

  const handleSave = async () => {
    setIsProcessing(true);
    await onAction({ action: 'save' });
    setIsProcessing(false);
    onClose();
  };

  const stageName = stage.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        maxWidth: '900px',
        width: '100%',
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
      }}>
        {/* Header */}
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid #e5e7eb',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: '600', color: '#111827' }}>
              ⏸️ Checkpoint: {stageName}
            </h2>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.875rem', color: '#6b7280' }}>
              Review the output and choose an action to continue
            </p>
          </div>
          <span style={{
            padding: '4px 12px',
            backgroundColor: '#fef3c7',
            color: '#92400e',
            borderRadius: '12px',
            fontSize: '0.75rem',
            fontWeight: '500'
          }}>
            Waiting for approval
          </span>
        </div>

        {/* Content */}
        <div style={{
          flex: 1,
          overflow: 'auto',
          padding: '24px'
        }}>
          <div style={{ marginBottom: '20px' }}>
            <label style={{
              display: 'block',
              fontSize: '0.875rem',
              fontWeight: '500',
              color: '#374151',
              marginBottom: '8px'
            }}>
              Agent Output Preview:
            </label>
            {editMode ? (
              <textarea
                value={editedText}
                onChange={(e) => setEditedText(e.target.value)}
                style={{
                  width: '100%',
                  minHeight: '300px',
                  padding: '12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                  lineHeight: '1.5'
                }}
              />
            ) : (
              <div style={{
                padding: '12px',
                backgroundColor: '#f9fafb',
                border: '1px solid #e5e7eb',
                borderRadius: '6px',
                fontFamily: 'monospace',
                fontSize: '0.875rem',
                lineHeight: '1.6',
                whiteSpace: 'pre-wrap',
                maxHeight: '300px',
                overflow: 'auto'
              }}>
                {getPreviewText()}
              </div>
            )}
          </div>

          <div>
            <label style={{
              display: 'block',
              fontSize: '0.875rem',
              fontWeight: '500',
              color: '#374151',
              marginBottom: '8px'
            }}>
              Optional: Instructions for next agent
            </label>
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="e.g., 'Focus more on section 3' or 'Make the tone more casual'"
              style={{
                width: '100%',
                minHeight: '80px',
                padding: '12px',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '0.875rem',
                lineHeight: '1.5'
              }}
            />
          </div>
        </div>

        {/* Actions */}
        <div style={{
          padding: '20px 24px',
          borderTop: '1px solid #e5e7eb',
          display: 'flex',
          gap: '12px',
          flexWrap: 'wrap'
        }}>
          {editMode ? (
            <>
              <button
                onClick={handleSaveEdit}
                disabled={isProcessing}
                style={{
                  flex: 1,
                  padding: '10px 20px',
                  backgroundColor: '#3b82f6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  fontWeight: '500',
                  cursor: isProcessing ? 'not-allowed' : 'pointer',
                  opacity: isProcessing ? 0.5 : 1
                }}
              >
                💾 Save & Continue
              </button>
              <button
                onClick={() => setEditMode(false)}
                disabled={isProcessing}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#f3f4f6',
                  color: '#374151',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontWeight: '500',
                  cursor: isProcessing ? 'not-allowed' : 'pointer'
                }}
              >
                Cancel Edit
              </button>
            </>
          ) : (
            <>
              <button
                onClick={handleApprove}
                disabled={isProcessing}
                style={{
                  flex: 1,
                  padding: '10px 20px',
                  backgroundColor: '#10b981',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  fontWeight: '500',
                  cursor: isProcessing ? 'not-allowed' : 'pointer',
                  opacity: isProcessing ? 0.5 : 1
                }}
              >
                ✓ Approve & Continue
              </button>
              <button
                onClick={handleEdit}
                disabled={isProcessing}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#f59e0b',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  fontWeight: '500',
                  cursor: isProcessing ? 'not-allowed' : 'pointer',
                  opacity: isProcessing ? 0.5 : 1
                }}
              >
                ✏️ Edit Output
              </button>
              <button
                onClick={handleApproveAll}
                disabled={isProcessing}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#8b5cf6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  fontWeight: '500',
                  cursor: isProcessing ? 'not-allowed' : 'pointer',
                  opacity: isProcessing ? 0.5 : 1
                }}
              >
                ⚡ Approve All
              </button>
              <button
                onClick={handleSave}
                disabled={isProcessing}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#6b7280',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  fontWeight: '500',
                  cursor: isProcessing ? 'not-allowed' : 'pointer',
                  opacity: isProcessing ? 0.5 : 1
                }}
              >
                💾 Save for Later
              </button>
              <button
                onClick={handleCancel}
                disabled={isProcessing}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#ef4444',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  fontWeight: '500',
                  cursor: isProcessing ? 'not-allowed' : 'pointer',
                  opacity: isProcessing ? 0.5 : 1
                }}
              >
                ❌ Cancel Pipeline
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default CheckpointDialog;

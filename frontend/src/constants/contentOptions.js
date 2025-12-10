/**
 * Content creation options and constants
 */

export const CONTENT_TYPES = [
  {
    id: 'blog',
    label: 'Blog Post',
    icon: '📝',
    description: 'Long-form article for your website or blog',
  },
  {
    id: 'linkedin',
    label: 'LinkedIn Post',
    icon: '💼',
    description: 'Professional social media content',
  },
  {
    id: 'social-media',
    label: 'Social Media Post',
    icon: '📱',
    description: 'Social media content for various platforms',
  },
  {
    id: 'newsletter',
    label: 'Newsletter',
    icon: '📧',
    description: 'Email newsletter content',
  },
  {
    id: 'press-release',
    label: 'Press Release',
    icon: '📰',
    description: 'Official press release or announcement',
  },
  {
    id: 'web-page',
    label: 'Web Page',
    icon: '🌐',
    description: 'Website page content',
  },
  {
    id: 'other',
    label: 'Other',
    icon: '📄',
    description: 'Other types of content',
  },
];

export const TONES = [
  { id: 'professional', label: 'Professional', description: 'Formal and business-appropriate' },
  { id: 'casual', label: 'Casual', description: 'Friendly and conversational' },
  { id: 'thought-leadership', label: 'Thought Leadership', description: 'Authoritative and insightful' },
  { id: 'educational', label: 'Educational', description: 'Informative and instructional' },
  { id: 'persuasive', label: 'Persuasive', description: 'Compelling and action-oriented' },
];

export const AUDIENCES = [
  { id: 'general', label: 'General Audience', description: 'Broad public audience' },
  { id: 'technical', label: 'Technical Professionals', description: 'Developers, engineers, IT' },
  { id: 'executives', label: 'C-Suite/Executives', description: 'Decision makers and leaders' },
  { id: 'marketers', label: 'Marketing Professionals', description: 'Marketing and growth teams' },
  { id: 'small-business', label: 'Small Business Owners', description: 'Entrepreneurs and SMB owners' },
  { id: 'enterprise', label: 'Enterprise Buyers', description: 'Large organization stakeholders' },
];

export const GOALS = [
  { id: 'awareness', label: 'Brand Awareness', description: 'Increase visibility and recognition' },
  { id: 'engagement', label: 'Engagement', description: 'Drive comments, shares, and interaction' },
  { id: 'lead-gen', label: 'Lead Generation', description: 'Capture potential customer information' },
  { id: 'conversion', label: 'Conversion', description: 'Drive sales or sign-ups' },
  { id: 'education', label: 'Education', description: 'Teach and inform the audience' },
  { id: 'thought-leadership', label: 'Thought Leadership', description: 'Establish industry authority' },
];

export const LENGTH_OPTIONS = [
  { id: 'short', label: 'Short', value: '300-500 words', description: 'Quick read' },
  { id: 'medium', label: 'Medium', value: '800-1200 words', description: 'Standard article' },
  { id: 'long', label: 'Long', value: '1500-2500 words', description: 'In-depth content' },
  { id: 'comprehensive', label: 'Comprehensive', value: '3000+ words', description: 'Detailed guide' },
];

export const LANGUAGES = [
  { id: 'en', label: 'English', code: 'en' },
  { id: 'es', label: 'Spanish', code: 'es' },
  { id: 'fr', label: 'French', code: 'fr' },
  { id: 'de', label: 'German', code: 'de' },
  { id: 'it', label: 'Italian', code: 'it' },
  { id: 'pt', label: 'Portuguese', code: 'pt' },
  { id: 'nl', label: 'Dutch', code: 'nl' },
  { id: 'ja', label: 'Japanese', code: 'ja' },
  { id: 'zh', label: 'Chinese', code: 'zh' },
];

// Pipeline stages for display
export const PIPELINE_STAGES = [
  { id: 'trends_keywords', name: 'Trends & Keywords', icon: '🔍', description: 'Researching trends and keywords' },
  { id: 'tone_of_voice', name: 'Tone of Voice', icon: '🎨', description: 'Analyzing brand voice' },
  { id: 'structure_outline', name: 'Structure & Outline', icon: '📋', description: 'Creating content structure' },
  { id: 'writer', name: 'Writer', icon: '✍️', description: 'Writing content' },
  { id: 'seo_optimizer', name: 'SEO & GEO Optimizer', icon: '📈', description: 'Optimizing for SEO & GEO' },
  { id: 'originality_check', name: 'Originality Check', icon: '✅', description: 'Checking originality' },
  { id: 'final_review', name: 'Final Review', icon: '🎯', description: 'Final polish and review' },
];

// Status colors for badges
export const STATUS_COLORS = {
  completed: { background: '#dcfce7', color: '#166534' },
  running: { background: '#dbeafe', color: '#1e40af' },
  failed: { background: '#fee2e2', color: '#991b1b' },
  pending: { background: '#f3f4f6', color: '#4b5563' },
};

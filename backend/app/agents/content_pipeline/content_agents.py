"""
Content Pipeline Agents
========================

Implementation of the 7 specialized agents for the content creation pipeline:
1. TrendsKeywordsAgent
2. ToneOfVoiceAgent
3. StructureOutlineAgent
4. WriterAgent
5. SEOOptimizerAgent
6. OriginalityPlagiarismAgent
7. FinalReviewerAgent
"""

import json
import logging
import time
from typing import Any, Dict, Optional

from ...agent_prompts import get_agent_prompt_config
from ..base import BaseAgent
from ..prompts.content_pipeline_prompts import (
    FINAL_REVIEWER_AGENT_PROMPT,
    ORIGINALITY_PLAGIARISM_AGENT_PROMPT,
    SEO_OPTIMIZER_AGENT_PROMPT,
    STRUCTURE_OUTLINE_AGENT_PROMPT,
    TONE_OF_VOICE_RAG_AGENT_PROMPT,
    TRENDS_KEYWORDS_AGENT_PROMPT,
    WRITER_AGENT_PROMPT,
    format_prompt_with_variables,
)

logger = logging.getLogger(__name__)


class ContentPipelineAgent(BaseAgent):
    """Base class for content pipeline agents with common functionality."""

    def __init__(self, llm_client: Optional[Any] = None) -> None:
        super().__init__(llm_client=llm_client)
        self._system_prompt = ""
        self._temperature = 0.5
        # Logging capture
        self._last_system_prompt = ""
        self._last_user_prompt = ""
        self._last_raw_response = ""
        self._last_input_context = {}

    def get_last_call_details(self) -> Dict[str, Any]:
        """Get details of the last LLM call for logging purposes."""
        return {
            "system_prompt": self._last_system_prompt,
            "user_prompt": self._last_user_prompt,
            "raw_response": self._last_raw_response,
            "input_context": self._last_input_context,
            "temperature": self._temperature,
        }

    def _get_prompt_config(self, agent_id: str):
        """Fetch prompt overrides for the given agent if available."""

        try:
            return get_agent_prompt_config(agent_id)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to load prompt config for %s: %s", agent_id, exc)
            return None

    def _render_user_prompt(self, template: str, variables: Dict[str, Any], fallback_template: str) -> str:
        """Render a user prompt using provided variables with safe fallback."""

        chosen_template = template or fallback_template
        try:
            return chosen_template.format(**variables)
        except KeyError as exc:
            logger.warning("Missing variable %s while rendering prompt; using fallback", exc)
            return fallback_template.format(**variables)

    def _format_prompt(self, variables: Dict[str, Any]) -> str:
        """Format the system prompt with variables."""
        return format_prompt_with_variables(self._system_prompt, variables)

    def _parse_json_response(self, response: str, validate_schema: bool = True) -> Dict[str, Any]:
        """
        Parse JSON from LLM response, handling markdown code blocks.

        Args:
            response: Raw LLM response string
            validate_schema: Whether to validate with Pydantic schema (default True)

        Returns:
            Parsed and optionally validated dictionary
        """
        original_response = response

        # Check for empty or None response
        if not response:
            logger.error("Received empty response from LLM")
            logger.error(f"Agent: {self.name()}")
            logger.error(f"Last system prompt (first 200 chars): {self._last_system_prompt[:200] if hasattr(self, '_last_system_prompt') else 'N/A'}")
            logger.error(f"Last user prompt (first 200 chars): {self._last_user_prompt[:200] if hasattr(self, '_last_user_prompt') else 'N/A'}")
            raise ValueError("Empty response from LLM - model may have timed out or returned no content")

        # Remove markdown code blocks if present
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Try to find JSON (object or array) within the response if it contains extra text
        if not (cleaned.startswith('{') or cleaned.startswith('[')):
            # Look for the first { or [ character
            obj_idx = cleaned.find('{')
            arr_idx = cleaned.find('[')

            # Use whichever comes first (or the one that exists)
            if obj_idx != -1 and arr_idx != -1:
                start_idx = min(obj_idx, arr_idx)
            elif obj_idx != -1:
                start_idx = obj_idx
            elif arr_idx != -1:
                start_idx = arr_idx
            else:
                start_idx = -1

            if start_idx != -1:
                cleaned = cleaned[start_idx:]
                logger.warning(f"Found JSON start at position {start_idx}, removed leading text")

        if not (cleaned.endswith('}') or cleaned.endswith(']')):
            # Look for the last } or ] character
            obj_idx = cleaned.rfind('}')
            arr_idx = cleaned.rfind(']')

            # Use whichever comes last (or the one that exists)
            if obj_idx != -1 and arr_idx != -1:
                end_idx = max(obj_idx, arr_idx)
            elif obj_idx != -1:
                end_idx = obj_idx
            elif arr_idx != -1:
                end_idx = arr_idx
            else:
                end_idx = -1

            if end_idx != -1:
                cleaned = cleaned[:end_idx+1]
                logger.warning(f"Found JSON end at position {end_idx}, removed trailing text")

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as primary_error:
            logger.warning(f"Initial JSON parse failed: {primary_error.msg} at line {primary_error.lineno}, col {primary_error.colno}")

            # Repair Strategy 1: Advanced repair using error position analysis
            try:
                advanced_repaired = self._advanced_json_repair(cleaned, primary_error)
                if advanced_repaired != cleaned:
                    parsed = json.loads(advanced_repaired)
                    logger.warning("✓ Parsed JSON after advanced positional repair")
                    return parsed
            except json.JSONDecodeError as e:
                logger.debug(f"Advanced repair failed: {e.msg}")

            # Repair Strategy 2: Unterminated string repair (LLM forgot to close a quote)
            if "unterminated string" in primary_error.msg.lower():
                try:
                    repaired = self._repair_unterminated_strings(cleaned, primary_error)
                    if repaired != cleaned:
                        parsed = json.loads(repaired)
                        logger.warning("✓ Parsed JSON after repairing unterminated strings")
                        return parsed
                except json.JSONDecodeError as e:
                    logger.debug(f"Unterminated string repair failed: {e.msg}")

            # Repair Strategy 3: Comma repair (common LLM error: missing commas between properties)
            try:
                repaired = self._repair_json_commas(cleaned)
                if repaired != cleaned:
                    parsed = json.loads(repaired)
                    logger.warning("✓ Parsed JSON after repairing missing commas with regex")
                    logger.debug(f"Comma repairs applied: {len(repaired) - len(cleaned)} characters changed")
                    return parsed
            except json.JSONDecodeError as e:
                logger.debug(f"Comma repair failed: {e.msg}")

            # Repair Strategy 4: Escape control characters (e.g., raw newlines in strings)
            try:
                escaped_cleaned = self._escape_control_characters_in_strings(cleaned)
                if escaped_cleaned != cleaned:
                    parsed = json.loads(escaped_cleaned, strict=False)
                    logger.warning("✓ Parsed JSON after escaping control characters inside strings")
                    return parsed
            except json.JSONDecodeError as e:
                logger.debug(f"Control character escape failed: {e.msg}")

            # Repair Strategy 5: Relaxed parsing to allow common control characters
            try:
                parsed = json.loads(cleaned, strict=False)
                logger.warning("✓ Parsed JSON with relaxed rules (strict=False)")
                return parsed
            except json.JSONDecodeError as relaxed_error:
                logger.debug(f"Relaxed parsing failed: {relaxed_error.msg}")

            # All repair strategies failed - log comprehensive error information
            logger.error("=" * 80)
            logger.error(f"❌ ALL JSON REPAIR STRATEGIES FAILED for agent: {self.name()}")
            logger.error("=" * 80)
            logger.error(f"Primary error: {primary_error}")
            logger.error(f"Error location: line {primary_error.lineno}, column {primary_error.colno}")
            logger.error(f"Error message: {primary_error.msg}")
            logger.error(f"Character position: {primary_error.pos if hasattr(primary_error, 'pos') else 'N/A'}")
            logger.error("-" * 80)
            logger.error(f"Cleaned response preview (first 500 chars):\n{cleaned[:500]}")
            logger.error("-" * 80)
            logger.error(f"Original response preview (first 500 chars):\n{original_response[:500]}")
            logger.error("-" * 80)

            # Show context around error position
            if hasattr(primary_error, 'pos') and primary_error.pos and primary_error.pos < len(cleaned):
                start = max(0, primary_error.pos - 100)
                end = min(len(cleaned), primary_error.pos + 100)
                error_context = cleaned[start:end]
                # Mark the exact error position
                marker_pos = min(primary_error.pos - start, len(error_context))
                marked_context = error_context[:marker_pos] + " <<<ERROR HERE>>> " + error_context[marker_pos:]
                logger.error(f"Context around error position:\n{marked_context}")
                logger.error("-" * 80)

            # Save the problematic response to a debug file for analysis
            try:
                import tempfile
                import os
                debug_file = os.path.join(tempfile.gettempdir(), f"json_parse_error_{self.name()}_{int(time.time())}.txt")
                with open(debug_file, 'w') as f:
                    f.write(f"Agent: {self.name()}\n")
                    f.write(f"Error: {primary_error}\n")
                    f.write(f"Error location: line {primary_error.lineno}, column {primary_error.colno}\n")
                    f.write(f"\n{'='*80}\n")
                    f.write(f"Original Response:\n{original_response}\n")
                    f.write(f"\n{'='*80}\n")
                    f.write(f"Cleaned Response:\n{cleaned}\n")
                logger.error(f"Debug file saved: {debug_file}")
            except Exception as e:
                logger.warning(f"Could not save debug file: {e}")

            logger.error("=" * 80)

            raise ValueError(f"Invalid JSON response from agent: {primary_error}")

    def _repair_unterminated_strings(self, json_str: str, error: json.JSONDecodeError) -> str:
        """
        Attempt to repair unterminated strings by adding missing closing quotes.

        This handles cases where the LLM forgets to close a string with a quote.

        Strategy:
        1. Find the position where the unterminated string starts
        2. Look for likely end positions (before next quote+colon pattern, or before closing brace)
        3. Insert the missing quote
        """
        if not error.pos or error.pos >= len(json_str):
            return json_str

        # Start from the error position
        pos = error.pos

        # Look ahead for potential string termination points
        # Common patterns that indicate where a string should end:
        # 1. Newline followed by whitespace and a quote (start of next property)
        # 2. Before a closing brace }
        # 3. Before a comma

        result = list(json_str)
        search_start = pos
        search_end = min(len(json_str), pos + 500)  # Look ahead up to 500 chars

        # Look for a newline followed by quote pattern: \n  "property_name":
        import re
        remaining = json_str[search_start:search_end]

        # Pattern 1: Find newline followed by property name pattern
        match = re.search(r'\n\s*"[^"]+"\s*:', remaining)
        if match:
            insert_pos = search_start + match.start()
            result.insert(insert_pos, '"')
            logger.warning(f"Inserted missing quote at position {insert_pos} (before next property)")
            return ''.join(result)

        # Pattern 2: Find comma or closing brace
        for i in range(search_start, search_end):
            if json_str[i] in {',', '}', ']'}:
                # Insert quote before this character
                result.insert(i, '"')
                logger.warning(f"Inserted missing quote at position {i} (before {json_str[i]})")
                return ''.join(result)

        # Pattern 3: If we find another quote that looks like it starts a new string
        # This might be the closing quote of our string followed by opening quote of next
        for i in range(search_start, search_end):
            if json_str[i] == '"' and i > search_start:
                # Check if this looks like start of a new property (quote followed eventually by colon)
                lookahead = json_str[i:min(len(json_str), i + 50)]
                if ':' in lookahead:
                    # This is likely the start of a new property, so insert quote before it
                    result.insert(i, '"')
                    logger.warning(f"Inserted missing quote at position {i} (before new property)")
                    return ''.join(result)

        return json_str

    def _repair_json_commas(self, json_str: str) -> str:
        """
        Fix missing commas between object properties and array elements.

        Common LLM errors this fixes:
        - Missing comma after property: {"a": 1 "b": 2}  -> {"a": 1, "b": 2}
        - Missing comma before array property: {"slug": "x" "arr": [...]}  -> {"slug": "x", "arr": [...]}
        - Missing comma before object property: {"a": 1 "nested": {...}}  -> {"a": 1, "nested": {...}}
        - Missing comma in array: [1 2 3]  -> [1, 2, 3]
        - Trailing commas: {"a": 1,}  -> {"a": 1}
        """
        import re
        result = json_str

        # Fix missing commas between string values and next property
        # {"name": "value" "age": 30} -> {"name": "value", "age": 30}
        result = re.sub(
            r'("(?:[^"\\]|\\.)*")\s+("(?:[^"\\]|\\.)*"\s*:)',
            r'\1, \2',
            result
        )

        # Fix missing commas between numbers and next property
        # {"a": 123 "b": 456} -> {"a": 123, "b": 456}
        result = re.sub(
            r'(\d+)\s+("(?:[^"\\]|\\.)*"\s*:)',
            r'\1, \2',
            result
        )

        # Fix missing commas between boolean/null values and next property
        # {"flag": true "name": "value"} -> {"flag": true, "name": "value"}
        result = re.sub(
            r'(true|false|null)\s+("(?:[^"\\]|\\.)*"\s*:)',
            r'\1, \2',
            result
        )

        # Fix missing commas between closing structures and next property
        # {"obj": {} "arr": []} -> {"obj": {}, "arr": []}
        result = re.sub(
            r'([}\]])\s+("(?:[^"\\]|\\.)*"\s*:)',
            r'\1, \2',
            result
        )

        # Fix missing commas in arrays between elements
        # [1 2 3] -> [1, 2, 3]
        # ["a" "b"] -> ["a", "b"]
        result = re.sub(
            r'(\d+)\s+(\d+)',
            r'\1, \2',
            result
        )
        result = re.sub(
            r'("(?:[^"\\]|\\.)*")\s+("(?:[^"\\]|\\.)*")(?!\s*:)',  # Don't match "key" "value" (property)
            r'\1, \2',
            result
        )

        # Fix trailing commas before closing braces/brackets
        # {"a": 1,} -> {"a": 1}
        result = re.sub(r',(\s*[}\]])', r'\1', result)

        # Fix multiple consecutive commas (edge case from over-aggressive repairs)
        result = re.sub(r',\s*,+', ',', result)

        return result

    def _advanced_json_repair(self, json_str: str, error: json.JSONDecodeError) -> str:
        """
        Advanced JSON repair using error position and context analysis.

        This function analyzes the specific error location and applies targeted fixes
        based on common LLM JSON generation mistakes.
        """
        import re

        # Get error context
        error_pos = error.pos if hasattr(error, 'pos') and error.pos else 0
        error_msg = error.msg.lower()

        # Create a working copy
        result = json_str

        # Strategy 1: Missing comma detection using error position
        if "expecting ',' delimiter" in error_msg and error_pos > 0:
            # Look backward from error position to find the previous complete value
            # Look forward to find the start of the next property

            # Extract context around error
            context_start = max(0, error_pos - 100)
            context_end = min(len(json_str), error_pos + 100)
            context = json_str[context_start:context_end]

            # Pattern: Find where we need to insert comma
            # Common case: "value"\n  "next_property": or "value" "next_property":
            before_error = json_str[max(0, error_pos-50):error_pos]
            after_error = json_str[error_pos:min(len(json_str), error_pos+50)]

            # Check if we have a closing quote followed by whitespace and then opening quote
            # This is the "slug": "value" "suggested_links": pattern
            pattern = r'("[^"]*")\s+("[^"]*"\s*:)'
            if re.search(pattern, context):
                logger.warning(f"Detected missing comma pattern at position {error_pos}")
                # Insert comma at error position (or just before it)
                # The error position usually points right after where comma should be
                insert_pos = error_pos

                # Find the exact position: look backward for closing quote or value
                check_backwards = json_str[max(0, error_pos-20):error_pos]
                if check_backwards.rstrip().endswith('"'):
                    # Insert after the quote
                    result = json_str[:error_pos] + ',' + json_str[error_pos:]
                    logger.info(f"Inserted comma at position {error_pos}")
                elif check_backwards.rstrip().endswith(']') or check_backwards.rstrip().endswith('}'):
                    # Insert after closing bracket/brace
                    result = json_str[:error_pos] + ',' + json_str[error_pos:]
                    logger.info(f"Inserted comma after closing bracket at position {error_pos}")

        # Strategy 2: Fix trailing commas in specific contexts
        if "expecting property name" in error_msg or "expecting value" in error_msg:
            # Remove trailing commas before } or ]
            result = re.sub(r',(\s*[}\]])', r'\1', result)

        # Strategy 3: Fix unescaped quotes in string values
        if "invalid \\escape" in error_msg or "invalid escape" in error_msg:
            # This is tricky - try to escape unescaped quotes within strings
            # This is a simplified approach
            pass  # Already handled by _escape_control_characters_in_strings

        return result

    def _escape_control_characters_in_strings(self, text: str) -> str:
        """Escape raw control characters that appear inside JSON strings."""

        escaped = []
        in_string = False
        is_escaped = False

        for char in text:
            if is_escaped:
                escaped.append(char)
                is_escaped = False
                continue

            if char == "\\":
                escaped.append(char)
                is_escaped = True
                continue

            if char == '"':
                in_string = not in_string
                escaped.append(char)
                continue

            if in_string and char in {"\n", "\r", "\t"}:
                escaped.append({"\n": "\\n", "\r": "\\r", "\t": "\\t"}[char])
                continue

            escaped.append(char)

        return "".join(escaped)

    async def _generate(self, prompt: str, user_message: str, input_context: Optional[Dict[str, Any]] = None) -> str:
        """Generate response from LLM."""
        if not self.llm_client:
            raise ValueError("LLM client not configured")

        # Capture for logging
        self._last_system_prompt = prompt
        self._last_user_prompt = user_message
        self._last_input_context = input_context or {}

        logger.info(f"Calling LLM for agent: {self.name()}")
        logger.info(f"System prompt length: {len(prompt)} chars")
        logger.info(f"User message length: {len(user_message)} chars")

        # Use the llm_client's generate method
        # Higher max_tokens for marketing content generation to avoid truncation
        response = await self.llm_client.generate(
            prompt=user_message,
            system_prompt=prompt,
            temperature=self._temperature,
            max_tokens=8000
        )

        # Capture response for logging
        self._last_raw_response = response

        # Log response details with enhanced diagnostics
        if response:
            logger.info(f"LLM response received: {len(response)} chars")
            logger.info(f"Response preview (first 200 chars): {response[:200]}")
        else:
            # Enhanced error diagnostics for empty responses
            total_prompt_length = len(prompt) + len(user_message)
            estimated_tokens = total_prompt_length // 4

            error_msg = f"""
{'=' * 80}
❌ EMPTY LLM RESPONSE ERROR
{'=' * 80}
Agent: {self.name()}

Possible causes:
1. LLM timeout - Response generation took too long
2. Token limit exceeded - Prompt or response too large for model context
3. LLM API error - Service unavailable or rate limited
4. Content filter - Response blocked by safety filters
5. Model failure - Internal model error

Prompt diagnostics:
- System prompt length: {len(prompt)} chars (~{len(prompt) // 4} tokens)
- User message length: {len(user_message)} chars (~{len(user_message) // 4} tokens)
- Total prompt length: {total_prompt_length} chars (~{estimated_tokens} tokens)
- Temperature: {self._temperature}

System prompt preview (first 300 chars):
{prompt[:300]}...

User message preview (first 300 chars):
{user_message[:300]}...

Recommendations:
- If prompt is very large (>100k tokens), consider reducing input size
- Check LLM service status and rate limits
- Review recent logs for API errors
- Try reducing temperature or adjusting generation parameters
{'=' * 80}
"""
            logger.error(error_msg)
            raise ValueError(f"Empty response from LLM for {self.name()} - see logs for detailed diagnostics")

        return response


# =============================================================================
# AGENT 1: TRENDS & KEYWORDS AGENT
# =============================================================================

class TrendsKeywordsAgent(ContentPipelineAgent):
    """
    Researches trends and extracts strategic keywords for the content topic.

    Output:
    - trend_summary
    - primary_keywords
    - secondary_keywords
    - search_intent_insights
    - angle_ideas
    """

    def __init__(self, llm_client: Optional[Any] = None) -> None:
        super().__init__(llm_client=llm_client)
        self._system_prompt = TRENDS_KEYWORDS_AGENT_PROMPT
        self._temperature = 0.5

    def name(self) -> str:
        return "Trends & Keywords Agent"

    def description(self) -> str:
        return "Researches trends and extracts strategic keywords"

    async def run(
        self,
        topic: str,
        content_type: str = "blog post",
        audience: str = "general",
        goal: str = "awareness",
        brand_voice: str = "professional",
        language: str = "English",
        length_constraints: str = "1000-1500 words",
        context_summary: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze topic for trends and keywords.

        Returns:
            Dictionary with trend_summary, keywords, search_intent_insights, angle_ideas
        """
        prompt_config = self._get_prompt_config("trends_keywords")
        if prompt_config:
            self._system_prompt = prompt_config.systemPrompt

        variables = {
            "topic": topic,
            "content_type": content_type,
            "audience": audience,
            "goal": goal,
            "brand_voice": brand_voice,
            "language": language,
            "length_constraints": length_constraints,
            "context_summary": context_summary,
        }

        formatted_prompt = self._format_prompt(variables)

        context_text = context_summary if context_summary else "No additional context provided"

        # Web Search Integration - Get real-time trends using Brave Search API
        web_search_results = ""
        brave_requests = 0
        brave_results = 0
        try:
            from ..brave_search import BraveSearchService

            # Get Brave API key from kwargs (passed from orchestrator)
            brave_api_key = kwargs.get('brave_search_api_key')

            if brave_api_key:
                logger.info(f"🔍 TrendsKeywordsAgent: Using Brave Search for real-time trends on topic: {topic}")

                brave_service = BraveSearchService(api_key=brave_api_key)

                # Search for trends and recent news
                brave_requests += 1  # Track API request
                search_results = await brave_service.get_recent_news(
                    topic=topic,
                    days_back=7,
                    count=5
                )

                if search_results:
                    brave_results += len(search_results)  # Track results received
                    web_search_results = "\n\n**Real-Time Web Search Results:**\n"
                    for idx, result in enumerate(search_results[:5], 1):
                        web_search_results += f"\n{idx}. **{result.title}**\n"
                        web_search_results += f"   Source: {result.source}\n"
                        web_search_results += f"   {result.snippet}\n"
                        web_search_results += f"   URL: {result.url}\n"

                    logger.info(f"✅ Found {len(search_results)} real-time web results for topic: {topic}")

                    # Add web results to context
                    context_text = f"{context_text}\n{web_search_results}"
                else:
                    logger.warning(f"⚠️ No web search results found for topic: {topic}")
            else:
                logger.info("ℹ️ Brave Search API key not configured, skipping web search")
        except Exception as e:
            logger.warning(f"⚠️ Web search failed (continuing without it): {e}")

        default_template = (
            prompt_config.defaultUserPromptTemplate
            if prompt_config
            else (
                "Analyze the following topic and provide trend research and keyword extraction:\n\n"
                "Topic: {topic}\n"
                "Content Type: {content_type}\n"
                "Target Audience: {audience}\n"
                "Goal: {goal}\n"
                "Brand Voice: {brand_voice}\n"
                "Language: {language}\n"
                "Context: {context_summary}\n\n"
                "Provide your analysis in the specified JSON format."
            )
        )
        user_variables = {
            "topic": topic,
            "content_type": content_type,
            "audience": audience,
            "goal": goal,
            "brand_voice": brand_voice,
            "language": language,
            "context_summary": context_text,
        }

        user_message = self._render_user_prompt(
            prompt_config.userPromptTemplate if prompt_config else default_template,
            user_variables,
            default_template,
        )

        response = await self._generate(formatted_prompt, user_message)
        result = self._parse_json_response(response)

        # Add Brave metrics metadata (not part of schema, just for tracking)
        result['_brave_metrics'] = {
            'requests_made': brave_requests,
            'results_received': brave_results
        }

        return result


# =============================================================================
# AGENT 2: TONE-OF-VOICE RAG AGENT
# =============================================================================

class ToneOfVoiceAgent(ContentPipelineAgent):
    """
    Analyzes brand voice from examples and creates a style profile.

    Output:
    - style_profile with formality, person preference, sentence rhythm,
      structural preferences, rhetorical devices, do/don't rules, and examples
    """

    def __init__(self, llm_client: Optional[Any] = None) -> None:
        super().__init__(llm_client=llm_client)
        self._system_prompt = TONE_OF_VOICE_RAG_AGENT_PROMPT
        self._temperature = 0.4

    def name(self) -> str:
        return "Tone-of-Voice RAG Agent"

    def description(self) -> str:
        return "Analyzes brand voice from examples and creates style profile"

    async def run(
        self,
        topic: str,
        content_type: str = "blog post",
        audience: str = "general",
        goal: str = "awareness",
        brand_voice: str = "professional",
        language: str = "English",
        retrieved_style_chunks: str = "",
        context_summary: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze brand voice and create style profile.

        Args:
            retrieved_style_chunks: Example content from RAG retrieval

        Returns:
            Dictionary with style_profile
        """
        prompt_config = self._get_prompt_config("tone_of_voice")
        if prompt_config:
            self._system_prompt = prompt_config.systemPrompt

        variables = {
            "topic": topic,
            "content_type": content_type,
            "audience": audience,
            "goal": goal,
            "brand_voice": brand_voice,
            "language": language,
            "retrieved_style_chunks": retrieved_style_chunks,
            "context_summary": context_summary,
        }

        formatted_prompt = self._format_prompt(variables)

        style_examples = (
            retrieved_style_chunks
            if retrieved_style_chunks
            else "No style examples provided - infer from brand voice guidelines"
        )
        context_text = context_summary if context_summary else "None"
        default_template = (
            prompt_config.defaultUserPromptTemplate
            if prompt_config
            else (
                "Analyze the following brand voice examples and create a style profile:\n\n"
                "Topic: {topic}\n"
                "Content Type: {content_type}\n"
                "Target Audience: {audience}\n"
                "Goal: {goal}\n"
                "Brand Voice Guidelines: {brand_voice}\n"
                "Language: {language}\n\n"
                "Style Examples from RAG:\n{retrieved_style_chunks}\n\n"
                "Additional Context: {context_summary}\n\n"
                "Create a detailed style profile in the specified JSON format."
            )
        )
        user_variables = {
            "topic": topic,
            "content_type": content_type,
            "audience": audience,
            "goal": goal,
            "brand_voice": brand_voice,
            "language": language,
            "retrieved_style_chunks": style_examples,
            "context_summary": context_text,
        }

        user_message = self._render_user_prompt(
            prompt_config.userPromptTemplate if prompt_config else default_template,
            user_variables,
            default_template,
        )

        response = await self._generate(formatted_prompt, user_message)
        return self._parse_json_response(response)


# =============================================================================
# AGENT 3: STRUCTURE & OUTLINE AGENT
# =============================================================================

class StructureOutlineAgent(ContentPipelineAgent):
    """
    Creates detailed content structure and narrative arc.

    Output:
    - content_promise
    - hook_ideas
    - sections with id, title, objective, key_points
    """

    def __init__(self, llm_client: Optional[Any] = None) -> None:
        super().__init__(llm_client=llm_client)
        self._system_prompt = STRUCTURE_OUTLINE_AGENT_PROMPT
        self._temperature = 0.4

    def name(self) -> str:
        return "Structure & Outline Agent"

    def description(self) -> str:
        return "Designs detailed content structure and narrative arc"

    async def run(
        self,
        topic: str,
        content_type: str = "blog post",
        audience: str = "general",
        goal: str = "awareness",
        brand_voice: str = "professional",
        language: str = "English",
        length_constraints: str = "1000-1500 words",
        context_summary: str = "",
        trends_keywords: Dict[str, Any] = None,
        style_profile: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create content outline based on research and style profile.

        Args:
            trends_keywords: Output from TrendsKeywordsAgent
            style_profile: Output from ToneOfVoiceAgent

        Returns:
            Dictionary with content_promise, hook_ideas, sections
        """
        prompt_config = self._get_prompt_config("structure_outline")
        if prompt_config:
            self._system_prompt = prompt_config.systemPrompt

        variables = {
            "topic": topic,
            "content_type": content_type,
            "audience": audience,
            "goal": goal,
            "brand_voice": brand_voice,
            "language": language,
            "length_constraints": length_constraints,
            "context_summary": context_summary,
            "style_profile": style_profile or {},
        }

        formatted_prompt = self._format_prompt(variables)

        # Build user message with research data
        trends_info = ""
        if trends_keywords:
            trends_info = f"""
Trend Summary: {trends_keywords.get('trend_summary', 'N/A')}
Primary Keywords: {', '.join(trends_keywords.get('primary_keywords', []))}
Secondary Keywords: {', '.join(trends_keywords.get('secondary_keywords', []))}
Search Intent: {trends_keywords.get('search_intent_insights', 'N/A')}
Angle Ideas: {chr(10).join(trends_keywords.get('angle_ideas', []))}
"""

        style_profile_text = (
            json.dumps(style_profile, indent=2) if style_profile else "Use brand voice guidelines"
        )
        context_text = context_summary if context_summary else "None"
        default_template = (
            prompt_config.defaultUserPromptTemplate
            if prompt_config
            else (
                "Create a detailed content outline based on the following:\n\n"
                "Topic: {topic}\n"
                "Content Type: {content_type}\n"
                "Target Audience: {audience}\n"
                "Goal: {goal}\n"
                "Brand Voice: {brand_voice}\n"
                "Language: {language}\n"
                "Length: {length_constraints}\n\n"
                "Research & Keywords:\n{trends_info}\n\n"
                "Style Profile: {style_profile}\n\n"
                "Context: {context_summary}\n\n"
                "Create a conversion-oriented outline in the specified JSON format."
            )
        )
        user_variables = {
            "topic": topic,
            "content_type": content_type,
            "audience": audience,
            "goal": goal,
            "brand_voice": brand_voice,
            "language": language,
            "length_constraints": length_constraints,
            "trends_info": trends_info if trends_info else "No research data provided",
            "style_profile": style_profile_text,
            "context_summary": context_text,
        }

        user_message = self._render_user_prompt(
            prompt_config.userPromptTemplate if prompt_config else default_template,
            user_variables,
            default_template,
        )

        response = await self._generate(formatted_prompt, user_message)
        return self._parse_json_response(response)


# =============================================================================
# AGENT 4: WRITER AGENT
# =============================================================================

class WriterAgent(ContentPipelineAgent):
    """
    Writes natural, human-like content following the outline.

    Output:
    - full_text in Markdown format
    """

    def __init__(self, llm_client: Optional[Any] = None) -> None:
        super().__init__(llm_client=llm_client)
        self._system_prompt = WRITER_AGENT_PROMPT
        self._temperature = 0.7

    def name(self) -> str:
        return "Writer Agent"

    def description(self) -> str:
        return "Writes natural, human-like content following the outline"

    async def run(
        self,
        topic: str,
        content_type: str = "blog post",
        audience: str = "general",
        goal: str = "awareness",
        brand_voice: str = "professional",
        language: str = "English",
        length_constraints: str = "1000-1500 words",
        context_summary: str = "",
        trends_keywords: Dict[str, Any] = None,
        outline: Dict[str, Any] = None,
        style_profile: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Write content based on outline and style profile.

        Args:
            trends_keywords: Output from TrendsKeywordsAgent
            outline: Output from StructureOutlineAgent
            style_profile: Output from ToneOfVoiceAgent

        Returns:
            Dictionary with full_text
        """
        prompt_config = self._get_prompt_config("writer")
        if prompt_config:
            self._system_prompt = prompt_config.systemPrompt

        variables = {
            "topic": topic,
            "content_type": content_type,
            "audience": audience,
            "goal": goal,
            "brand_voice": brand_voice,
            "language": language,
            "length_constraints": length_constraints,
            "context_summary": context_summary,
            "style_profile": style_profile or {},
        }

        formatted_prompt = self._format_prompt(variables)

        # Build detailed user message
        outline_info = ""
        if outline:
            outline_info = f"""
Content Promise: {outline.get('content_promise', 'N/A')}
Hook Ideas: {chr(10).join(outline.get('hook_ideas', []))}

Sections:
"""
            for section in outline.get('sections', []):
                outline_info += f"""
{section.get('id', '')}: {section.get('title', '')}
Objective: {section.get('objective', '')}
Key Points: {chr(10).join('- ' + kp for kp in section.get('key_points', []))}
"""

        keywords_info = ""
        if trends_keywords:
            keywords_info = f"""
Primary Keywords to include: {', '.join(trends_keywords.get('primary_keywords', []))}
Secondary Keywords: {', '.join(trends_keywords.get('secondary_keywords', []))}
"""

        outline_text = outline_info if outline_info else "Create your own structure"
        keyword_text = keywords_info if keywords_info else "No specific keywords required"
        style_profile_text = (
            json.dumps(style_profile, indent=2) if style_profile else "Follow brand voice guidelines"
        )
        context_text = context_summary if context_summary else "None"
        default_template = (
            prompt_config.defaultUserPromptTemplate
            if prompt_config
            else (
                "Write the full content based on the following brief:\n\n"
                "Topic: {topic}\n"
                "Content Type: {content_type}\n"
                "Target Audience: {audience}\n"
                "Goal: {goal}\n"
                "Brand Voice: {brand_voice}\n"
                "Language: {language}\n"
                "Length: {length_constraints}\n\n"
                "Outline:\n{outline}\n\n"
                "Research & Keywords:\n{trends_info}\n\n"
                "Style Profile:\n{style_profile}\n\n"
                "Context: {context_summary}\n\n"
                "Write the complete Markdown content."
            )
        )
        user_variables = {
            "topic": topic,
            "content_type": content_type,
            "audience": audience,
            "goal": goal,
            "brand_voice": brand_voice,
            "language": language,
            "length_constraints": length_constraints,
            "outline": outline_text,
            "trends_info": keyword_text,
            "style_profile": style_profile_text,
            "context_summary": context_text,
        }

        user_message = self._render_user_prompt(
            prompt_config.userPromptTemplate if prompt_config else default_template,
            user_variables,
            default_template,
        )

        response = await self._generate(formatted_prompt, user_message)
        return self._parse_json_response(response)


# =============================================================================
# AGENT 5: SEO OPTIMIZER AGENT
# =============================================================================

class SEOOptimizerAgent(ContentPipelineAgent):
    """
    Optimizes content for SEO and readability.

    Output:
    - optimized_text
    - on_page_seo (focus_keyword, title_tag, meta_description, h1, slug, links)
    """

    def __init__(self, llm_client: Optional[Any] = None) -> None:
        super().__init__(llm_client=llm_client)
        self._system_prompt = SEO_OPTIMIZER_AGENT_PROMPT
        self._temperature = 0.3

    def name(self) -> str:
        return "SEO Optimizer Agent"

    def description(self) -> str:
        return "Optimizes content for SEO and readability"

    async def run(
        self,
        topic: str,
        content_type: str = "blog post",
        audience: str = "general",
        goal: str = "awareness",
        brand_voice: str = "professional",
        language: str = "English",
        length_constraints: str = "1000-1500 words",
        context_summary: str = "",
        trends_keywords: Dict[str, Any] = None,
        outline: Dict[str, Any] = None,
        draft: Dict[str, Any] = None,
        style_profile: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Optimize content for SEO.

        Args:
            trends_keywords: Output from TrendsKeywordsAgent
            outline: Output from StructureOutlineAgent
            draft: Output from WriterAgent
            style_profile: Output from ToneOfVoiceAgent

        Returns:
            Dictionary with optimized_text and on_page_seo
        """
        # CRITICAL DIAGNOSTIC: Verify draft content is being passed
        logger.info("=" * 80)
        logger.info("SEO OPTIMIZER AGENT - INPUT VERIFICATION")
        logger.info("=" * 80)
        logger.info(f"draft parameter type: {type(draft)}")
        logger.info(f"draft is None: {draft is None}")
        if draft:
            logger.info(f"draft keys: {list(draft.keys())}")
            logger.info(f"draft has 'full_text': {'full_text' in draft}")
            if 'full_text' in draft:
                full_text_len = len(draft.get('full_text', ''))
                logger.info(f"full_text length: {full_text_len} chars")
                logger.info(f"full_text preview (first 200 chars): {draft.get('full_text', '')[:200]}")
            else:
                logger.error("CRITICAL: draft dict does NOT contain 'full_text' key!")
        else:
            logger.error("CRITICAL: draft parameter is None!")
        logger.info("=" * 80)

        prompt_config = self._get_prompt_config("seo_optimizer")
        if prompt_config:
            self._system_prompt = prompt_config.systemPrompt

        variables = {
            "topic": topic,
            "content_type": content_type,
            "audience": audience,
            "goal": goal,
            "brand_voice": brand_voice,
            "language": language,
            "length_constraints": length_constraints,
            "context_summary": context_summary,
            "style_profile": style_profile or {},
        }

        formatted_prompt = self._format_prompt(variables)

        full_text = draft.get('full_text', '') if draft else ''
        logger.info(f"Extracted full_text: {len(full_text)} chars")
        primary_keywords = trends_keywords.get('primary_keywords', []) if trends_keywords else []
        secondary_keywords = trends_keywords.get('secondary_keywords', []) if trends_keywords else []
        style_profile_text = (
            json.dumps(style_profile, indent=2) if style_profile else "Follow brand voice guidelines"
        )
        default_template = (
            prompt_config.defaultUserPromptTemplate
            if prompt_config
            else (
                "Optimize the following draft for SEO and readability:\n\n"
                "Topic: {topic}\n"
                "Content Type: {content_type}\n"
                "Target Audience: {audience}\n"
                "Goal: {goal}\n"
                "Brand Voice: {brand_voice}\n"
                "Language: {language}\n"
                "Focus Keywords: {focus_keywords}\n\n"
                "Draft Content:\n{draft}\n\n"
                "Style Profile:\n{style_profile}\n\n"
                "Provide optimized content and on-page SEO elements in the specified JSON format."
            )
        )
        user_variables = {
            "topic": topic,
            "content_type": content_type,
            "audience": audience,
            "goal": goal,
            "brand_voice": brand_voice,
            "language": language,
            "focus_keywords": ', '.join(primary_keywords + secondary_keywords),
            "draft": full_text,
            "style_profile": style_profile_text,
        }

        user_message = self._render_user_prompt(
            prompt_config.userPromptTemplate if prompt_config else default_template,
            user_variables,
            default_template,
        )

        # DIAGNOSTIC: Log final prompt sizes before sending to LLM
        logger.info(f"SEO Optimizer - Final prompt sizes:")
        logger.info(f"  System prompt: {len(formatted_prompt)} chars")
        logger.info(f"  User message: {len(user_message)} chars")
        logger.info(f"  Total prompt size: {len(formatted_prompt) + len(user_message)} chars")

        # Check if prompt might be too large
        total_chars = len(formatted_prompt) + len(user_message)
        estimated_tokens = total_chars // 4  # Rough estimate: 4 chars per token
        logger.info(f"  Estimated tokens: ~{estimated_tokens}")
        if estimated_tokens > 100000:  # GPT-5 has 400k context but be conservative
            logger.warning(f"WARNING: Prompt is very large ({estimated_tokens} tokens). May cause issues.")

        response = await self._generate(formatted_prompt, user_message)
        return self._parse_json_response(response)


# =============================================================================
# AGENT 6: ORIGINALITY & PLAGIARISM AGENT
# =============================================================================

class OriginalityPlagiarismAgent(ContentPipelineAgent):
    """
    Checks for plagiarism risk and suggests original rewrites.

    Output:
    - originality_score
    - risk_summary
    - flagged_passages with original_excerpt, reason, rewritten_excerpt
    """

    def __init__(self, llm_client: Optional[Any] = None) -> None:
        super().__init__(llm_client=llm_client)
        self._system_prompt = ORIGINALITY_PLAGIARISM_AGENT_PROMPT
        self._temperature = 0.2

    def name(self) -> str:
        return "Originality & Plagiarism Agent"

    def description(self) -> str:
        return "Checks for plagiarism risk and suggests original rewrites"

    async def run(
        self,
        topic: str,
        audience: str = "general",
        goal: str = "awareness",
        brand_voice: str = "professional",
        language: str = "English",
        context_summary: str = "",
        seo_version: Dict[str, Any] = None,
        style_profile: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Check content originality and suggest rewrites.

        Args:
            seo_version: Output from SEOOptimizerAgent
            style_profile: Output from ToneOfVoiceAgent

        Returns:
            Dictionary with originality_score, risk_summary, flagged_passages
        """
        prompt_config = self._get_prompt_config("originality_plagiarism")
        if prompt_config:
            self._system_prompt = prompt_config.systemPrompt

        variables = {
            "style_profile": style_profile or {},
        }

        formatted_prompt = self._format_prompt(variables)

        optimized_text = seo_version.get('optimized_text', '') if seo_version else ''

        # Web Search Integration - Check for plagiarism using Brave Search API
        plagiarism_check_results = ""
        brave_requests = 0
        brave_results = 0
        try:
            from ..brave_search import BraveSearchService

            # Get Brave API key from kwargs (passed from orchestrator)
            brave_api_key = kwargs.get('brave_search_api_key')

            if brave_api_key and optimized_text:
                logger.info(f"🔍 OriginalityAgent: Using Brave Search to check for plagiarism")

                brave_service = BraveSearchService(api_key=brave_api_key)

                # Extract key sentences from content for plagiarism checking
                sentences = [s.strip() for s in optimized_text.split('.') if len(s.strip()) > 50]
                key_snippets = sentences[:3]  # Check first 3 substantial sentences

                if key_snippets:
                    brave_requests += len(key_snippets)  # Track requests (1 per snippet)
                    plagiarism_results = await brave_service.check_plagiarism(
                        content_snippets=key_snippets,
                        max_snippets=3
                    )

                    if plagiarism_results:
                        # Count total matches found across all snippets
                        for result in plagiarism_results:
                            brave_results += len(result.get('matches', []))

                        plagiarism_check_results = "\n\n**Plagiarism Check Results (Web Search):**\n"
                        for idx, result in enumerate(plagiarism_results, 1):
                            found = "⚠️  FOUND ONLINE" if result['found_online'] else "✅ Unique"
                            plagiarism_check_results += f"\n{idx}. Status: {found}\n"
                            plagiarism_check_results += f"   Snippet: \"{result['snippet'][:100]}...\"\n"
                            if result['found_online'] and result['matches']:
                                plagiarism_check_results += f"   Matching sources found:\n"
                                for match in result['matches'][:2]:
                                    plagiarism_check_results += f"   - {match['title']} ({match['source']})\n"

                        logger.info(f"✅ Completed plagiarism check for {len(plagiarism_results)} snippets")

                        # Add plagiarism check results to formatted prompt
                        formatted_prompt += f"\n\n{plagiarism_check_results}"
                else:
                    logger.info("ℹ️ No substantial sentences found for plagiarism checking")
            else:
                if not brave_api_key:
                    logger.info("ℹ️ Brave Search API key not configured, skipping plagiarism check")
        except Exception as e:
            logger.warning(f"⚠️ Plagiarism check failed (continuing without it): {e}")

        default_template = (
            prompt_config.defaultUserPromptTemplate
            if prompt_config
            else (
                "Review the optimized content for originality and plagiarism risks.\n\n"
                "Topic: {topic}\n"
                "Content Type: {content_type}\n"
                "Audience: {audience}\n"
                "Goal: {goal}\n"
                "Language: {language}\n\n"
                "Optimized Draft:\n{draft}\n\n"
                "Return an originality score and rewrite suggestions in the specified JSON format."
            )
        )
        user_variables = {
            "topic": topic,
            "content_type": "blog post",
            "audience": audience,
            "goal": goal,
            "brand_voice": brand_voice,
            "language": language,
            "draft": optimized_text,
        }

        user_message = self._render_user_prompt(
            prompt_config.userPromptTemplate if prompt_config else default_template,
            user_variables,
            default_template,
        )

        response = await self._generate(formatted_prompt, user_message)
        result = self._parse_json_response(response)

        # Add Brave metrics metadata (not part of schema, just for tracking)
        result['_brave_metrics'] = {
            'requests_made': brave_requests,
            'results_received': brave_results
        }

        return result


# =============================================================================
# AGENT 7: FINAL REVIEWER AGENT
# =============================================================================

class FinalReviewerAgent(ContentPipelineAgent):
    """
    Edits, polishes, and prepares final version for publication.

    Output:
    - final_text
    - change_log
    - editor_notes_for_user
    - suggested_variants
    """

    def __init__(self, llm_client: Optional[Any] = None) -> None:
        super().__init__(llm_client=llm_client)
        self._system_prompt = FINAL_REVIEWER_AGENT_PROMPT
        self._temperature = 0.3

    def name(self) -> str:
        return "Final Reviewer Agent"

    def description(self) -> str:
        return "Edits, polishes, and prepares final version for publication"

    async def run(
        self,
        topic: str,
        audience: str = "general",
        goal: str = "awareness",
        brand_voice: str = "professional",
        language: str = "English",
        context_summary: str = "",
        seo_version: Dict[str, Any] = None,
        originality_check: Dict[str, Any] = None,
        style_profile: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Final review and polish of content.

        Args:
            seo_version: Output from SEOOptimizerAgent
            originality_check: Output from OriginalityPlagiarismAgent
            style_profile: Output from ToneOfVoiceAgent

        Returns:
            Dictionary with final_text, change_log, editor_notes, suggested_variants
        """
        prompt_config = self._get_prompt_config("final_reviewer")
        if prompt_config:
            self._system_prompt = prompt_config.systemPrompt

        variables = {
            "language": language,
            "style_profile": style_profile or {},
        }

        formatted_prompt = self._format_prompt(variables)

        optimized_text = seo_version.get('optimized_text', '') if seo_version else ''
        on_page_seo = seo_version.get('on_page_seo', {}) if seo_version else {}

        # Build originality info
        originality_info = ""
        if originality_check:
            originality_info = f"""
Originality Score: {originality_check.get('originality_score', 'N/A')}
Risk Summary: {originality_check.get('risk_summary', 'N/A')}

Flagged Passages:
"""
            for passage in originality_check.get('flagged_passages', []):
                originality_info += f"""
- Original: {passage.get('original_excerpt', '')}
  Reason: {passage.get('reason', '')}
  Suggested Rewrite: {passage.get('rewritten_excerpt', '')}
"""

        seo_details = {
            "title_tag": on_page_seo.get('title_tag', 'N/A'),
            "meta_description": on_page_seo.get('meta_description', 'N/A'),
            "focus_keyword": on_page_seo.get('focus_keyword', 'N/A'),
        }
        default_template = (
            prompt_config.defaultUserPromptTemplate
            if prompt_config
            else (
                "Perform final editorial review of the content.\n\n"
                "Topic: {topic}\n"
                "Content Type: {content_type}\n"
                "Audience: {audience}\n"
                "Goal: {goal}\n"
                "Language: {language}\n"
                "Brand Voice: {brand_voice}\n\n"
                "Draft to Review:\n{draft}\n\n"
                "Originality Notes:\n{originality_notes}\n\n"
                "Provide the polished content and change log in the specified JSON format."
            )
        )
        user_variables = {
            "topic": topic,
            "content_type": "blog post",
            "audience": audience,
            "goal": goal,
            "language": language,
            "brand_voice": brand_voice,
            "draft": optimized_text,
            "originality_notes": originality_info if originality_info else "No issues flagged",
            "seo_title": seo_details["title_tag"],
            "seo_description": seo_details["meta_description"],
            "focus_keyword": seo_details["focus_keyword"],
        }

        user_message = self._render_user_prompt(
            prompt_config.userPromptTemplate if prompt_config else default_template,
            user_variables,
            default_template,
        )

        response = await self._generate(formatted_prompt, user_message)
        return self._parse_json_response(response)


# =============================================================================
# AGENT FACTORY
# =============================================================================

def get_content_agent(agent_id: str, llm_client: Optional[Any] = None) -> ContentPipelineAgent:
    """
    Factory function to get a content pipeline agent by ID.

    Args:
        agent_id: The agent identifier
        llm_client: Optional LLM client to inject

    Returns:
        Instantiated agent
    """
    agents = {
        "trends_keywords": TrendsKeywordsAgent,
        "tone_of_voice": ToneOfVoiceAgent,
        "structure_outline": StructureOutlineAgent,
        "writer": WriterAgent,
        "seo_optimizer": SEOOptimizerAgent,
        "originality_plagiarism": OriginalityPlagiarismAgent,
        "final_reviewer": FinalReviewerAgent,
    }

    if agent_id not in agents:
        raise ValueError(f"Unknown agent: {agent_id}")

    return agents[agent_id](llm_client=llm_client)


def get_all_content_agents(llm_client: Optional[Any] = None) -> Dict[str, ContentPipelineAgent]:
    """
    Get all content pipeline agents.

    Args:
        llm_client: Optional LLM client to inject

    Returns:
        Dictionary of agent_id -> agent instance
    """
    agent_ids = [
        "trends_keywords",
        "tone_of_voice",
        "structure_outline",
        "writer",
        "seo_optimizer",
        "originality_plagiarism",
        "final_reviewer",
    ]

    return {
        agent_id: get_content_agent(agent_id, llm_client)
        for agent_id in agent_ids
    }

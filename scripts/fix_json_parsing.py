#!/usr/bin/env python3
"""
Enhanced JSON repair utilities for fixing common LLM JSON generation errors.

This script provides aggressive JSON repair strategies that can be integrated
into the content pipeline to handle malformed JSON from LLMs.
"""

import re
import json
from typing import Any, Dict


def repair_json_commas(json_str: str) -> str:
    """
    Fix missing commas between object properties and array elements.

    Common LLM errors:
    - Missing comma after property: {"a": 1 "b": 2}  -> {"a": 1, "b": 2}
    - Missing comma in array: [1 2 3]  -> [1, 2, 3]
    - Trailing commas: {"a": 1,}  -> {"a": 1}
    """
    result = json_str

    # Fix missing commas between object properties
    # Pattern: "value" followed by whitespace and then " (start of next property)
    # {"name": "value" "age": 30} -> {"name": "value", "age": 30}
    result = re.sub(
        r'("(?:[^"\\]|\\.)*")\s+("(?:[^"\\]|\\.)*"\s*:)',
        r'\1, \2',
        result
    )

    # Fix missing commas between numbers in objects
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

    # Fix trailing commas before closing braces/brackets
    # {"a": 1,} -> {"a": 1}
    result = re.sub(r',(\s*[}\]])', r'\1', result)

    return result


def repair_json_quotes(json_str: str) -> str:
    """
    Fix unescaped quotes inside strings.

    Common LLM error: {"text": "He said "hello" there"}
    Should be: {"text": "He said \"hello\" there"}
    """
    result = []
    in_string = False
    is_escaped = False
    prev_char = None

    for i, char in enumerate(json_str):
        if is_escaped:
            result.append(char)
            is_escaped = False
            prev_char = char
            continue

        if char == '\\':
            result.append(char)
            is_escaped = True
            prev_char = char
            continue

        if char == '"':
            # Check if this looks like an unescaped quote inside a string
            # by looking ahead and behind
            if in_string and i > 0 and i < len(json_str) - 1:
                next_char = json_str[i + 1]
                # If the next char is not a comma, colon, or closing bracket,
                # and the previous char is not an opening bracket or colon,
                # this might be an unescaped quote
                if (next_char not in {',', ':', '}', ']'} and
                    prev_char not in {'{', '[', ':'}):
                    # This looks like an internal quote - escape it
                    result.append('\\')
                    result.append('"')
                    prev_char = char
                    continue

            in_string = not in_string
            result.append(char)
            prev_char = char
            continue

        result.append(char)
        prev_char = char

    return ''.join(result)


def repair_unterminated_strings(json_str: str) -> str:
    """
    Attempt to repair unterminated strings by adding missing closing quotes.

    Common LLM error: {"text": "some value
                       "next_property": ...}
    Should be: {"text": "some value",
                "next_property": ...}
    """
    # Try to parse to detect unterminated string error
    try:
        json.loads(json_str)
        return json_str  # Already valid
    except json.JSONDecodeError as e:
        if "unterminated string" not in e.msg.lower():
            return json_str  # Different error, can't help

        if not e.pos or e.pos >= len(json_str):
            return json_str

        # Start from the error position
        pos = e.pos
        result = list(json_str)
        search_start = pos
        search_end = min(len(json_str), pos + 500)

        # Pattern 1: Find newline followed by property name pattern
        remaining = json_str[search_start:search_end]
        match = re.search(r'\n\s*"[^"]+"\s*:', remaining)
        if match:
            insert_pos = search_start + match.start()
            result.insert(insert_pos, '"')
            return ''.join(result)

        # Pattern 2: Find comma or closing brace
        for i in range(search_start, search_end):
            if json_str[i] in {',', '}', ']'}:
                result.insert(i, '"')
                return ''.join(result)

        # Pattern 3: Find next quote that looks like a new property
        for i in range(search_start, search_end):
            if json_str[i] == '"' and i > search_start:
                lookahead = json_str[i:min(len(json_str), i + 50)]
                if ':' in lookahead:
                    result.insert(i, '"')
                    return ''.join(result)

        return json_str


def repair_json_aggressive(json_str: str, max_attempts: int = 5) -> str:
    """
    Aggressively try to repair JSON using multiple strategies.

    Args:
        json_str: The potentially malformed JSON string
        max_attempts: Maximum number of repair attempts

    Returns:
        Repaired JSON string (hopefully valid)
    """
    current = json_str.strip()

    # Strategy 1: Fix commas
    current = repair_json_commas(current)

    # Strategy 1.5: Fix unterminated strings
    current = repair_unterminated_strings(current)

    # Strategy 2: Fix quotes (be careful with this one)
    # current = repair_json_quotes(current)  # Disabled by default - too risky

    # Strategy 3: Remove common markdown artifacts
    if current.startswith('```json'):
        current = current[7:]
    if current.startswith('```'):
        current = current[3:]
    if current.endswith('```'):
        current = current[:-3]
    current = current.strip()

    # Strategy 4: Ensure proper start/end
    if not current.startswith('{') and not current.startswith('['):
        # Try to find the first { or [
        start_obj = current.find('{')
        start_arr = current.find('[')
        if start_obj != -1:
            current = current[start_obj:]
        elif start_arr != -1:
            current = current[start_arr:]

    if not current.endswith('}') and not current.endswith(']'):
        # Try to find the last } or ]
        end_obj = current.rfind('}')
        end_arr = current.rfind(']')
        end_pos = max(end_obj, end_arr)
        if end_pos != -1:
            current = current[:end_pos + 1]

    return current


def parse_json_with_repair(json_str: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Parse JSON with automatic repair attempts.

    Args:
        json_str: The JSON string to parse
        verbose: Print repair attempts

    Returns:
        Parsed JSON object

    Raises:
        ValueError: If JSON cannot be repaired and parsed
    """
    original = json_str

    # Try 1: Parse as-is
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        if verbose:
            print(f"Initial parse failed: {e}")

    # Try 2: Basic cleaning
    try:
        cleaned = json_str.strip()
        if cleaned.startswith('```'):
            # Remove markdown code fences
            cleaned = re.sub(r'^```(?:json)?\s*\n', '', cleaned)
            cleaned = re.sub(r'\n```\s*$', '', cleaned)
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        if verbose:
            print(f"Cleaned parse failed: {e}")

    # Try 3: Aggressive repair
    try:
        repaired = repair_json_aggressive(json_str)
        if verbose:
            print(f"Attempting to parse repaired JSON...")
            print(f"Repaired (first 500 chars): {repaired[:500]}")
        return json.loads(repaired)
    except json.JSONDecodeError as e:
        if verbose:
            print(f"Repaired parse failed: {e}")
            print(f"Error at line {e.lineno}, column {e.colno}: {e.msg}")
            if e.pos and e.pos < len(repaired):
                start = max(0, e.pos - 100)
                end = min(len(repaired), e.pos + 100)
                print(f"Context: ...{repaired[start:end]}...")

    # Try 4: Relaxed parsing
    try:
        repaired = repair_json_aggressive(json_str)
        return json.loads(repaired, strict=False)
    except json.JSONDecodeError as e:
        if verbose:
            print(f"Relaxed parse failed: {e}")

    raise ValueError(f"Could not parse or repair JSON: {original[:200]}...")


# Example usage
if __name__ == "__main__":
    # Test cases
    test_cases = [
        # Missing commas
        '{"name": "John" "age": 30}',
        '{"a": 1 "b": 2 "c": 3}',
        '[1 2 3 4]',

        # Trailing commas
        '{"name": "John", "age": 30,}',
        '[1, 2, 3,]',

        # Mixed
        '{"name": "John" "age": 30, "city": "NYC",}',

        # Markdown wrapped
        '```json\n{"valid": true}\n```',

        # Unterminated strings
        '{"text": "some value\n"next": "test"}',
        '{"description": "incomplete,\n"status": "active"}',
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test}")
        try:
            result = parse_json_with_repair(test, verbose=True)
            print(f"✅ Success: {result}")
        except Exception as e:
            print(f"❌ Failed: {e}")

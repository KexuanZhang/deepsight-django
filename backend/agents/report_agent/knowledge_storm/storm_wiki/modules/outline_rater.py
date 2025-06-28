import os
import argparse
import json
import time
import logging
import re
from typing import Dict, Any, List, Optional
from openai import OpenAI, AzureOpenAI
import toml

logger = logging.getLogger(__name__)


def read_file_content(file_path: str) -> Optional[str]:
    """Read content from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None


def parse_outline_sections(outline_text: str) -> Dict[str, str]:
    """
    Parse an outline text and extract each L1 section with all its content.

    Args:
        outline_text: The complete outline text

    Returns:
        Dictionary with L1 headings as keys and their content (including L2/L3) as values
    """
    if not outline_text:
        return {}

    # Detect if the outline uses # or ## as L1 headings
    lines = outline_text.split("\n")
    l1_pattern = "# "

    # Check if the outline starts with ## headings (incorrectly formatted)
    has_single_hash = any(
        line.strip().startswith("# ") and not line.strip().startswith("## ")
        for line in lines
    )
    has_double_hash = any(line.strip().startswith("## ") for line in lines)

    # If we only have ## headings and no # headings, treat ## as L1
    if has_double_hash and not has_single_hash:
        l1_pattern = "## "
        logger.info("Detected incorrect heading format (## as L1), adjusting parser")

    l1_sections = {}
    current_l1 = None
    current_content = []

    for i, line in enumerate(lines):
        # Check if this is an L1 heading
        if line.strip().startswith(l1_pattern) and not line.strip().startswith(
            l1_pattern + "#"
        ):
            # If we've been collecting content for a previous heading, save it
            if current_l1 and current_content:
                l1_sections[current_l1] = "\n".join(current_content)
                current_content = []

            # Start a new L1 section, but normalize the heading to use #
            heading_text = line.strip()
            if l1_pattern == "## ":
                # Convert ## to # for consistency
                normalized_heading = "# " + heading_text[3:]
            else:
                normalized_heading = heading_text

            current_l1 = normalized_heading
            current_content = [normalized_heading]  # Store normalized version
        # If we're inside an L1 section, keep collecting content
        elif current_l1:
            # Normalize heading levels in content as well
            content_line = line
            if l1_pattern == "## " and line.strip().startswith("### "):
                # Convert ### to ## for L2 content
                content_line = "## " + line.strip()[4:]
            elif l1_pattern == "## " and line.strip().startswith("#### "):
                # Convert #### to ### for L3 content
                content_line = "### " + line.strip()[5:]
            current_content.append(content_line)

        # If this is the last line and we have content, save it
        if i == len(lines) - 1 and current_l1 and current_content:
            l1_sections[current_l1] = "\n".join(current_content)

    return l1_sections


def extract_l2_headings(section_content: str) -> List[str]:
    """
    Extract L2 headings from a section content.

    Args:
        section_content: Content of an L1 section including all subheadings

    Returns:
        List of L2 headings found in the section
    """
    l2_headings = []
    for line in section_content.split("\n"):
        if line.strip().startswith("## "):
            l2_headings.append(line.strip())
    return l2_headings


def parse_outline_l2_sections(l1_section_content: str) -> Dict[str, str]:
    """
    Parse an L1 section content and extract each L2 subsection with all its content.

    Args:
        l1_section_content: Content of an L1 section including all subheadings

    Returns:
        Dictionary with L2 headings as keys and their content (including L3+) as values
    """
    if not l1_section_content:
        return {}

    l2_sections = {}
    lines = l1_section_content.split("\n")
    current_l2 = None
    current_content = []

    # Skip the L1 heading line
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("# "):
            start_idx = i + 1
            break

    for i, line in enumerate(lines[start_idx:]):
        # Check if this is an L2 heading
        if line.strip().startswith("## "):
            # If we've been collecting content for a previous heading, save it
            if current_l2 and current_content:
                l2_sections[current_l2] = "\n".join(current_content)
                current_content = []

            # Start a new L2 section
            current_l2 = line.strip()
            current_content = [line]
        # If we're inside an L2 section, keep collecting content
        elif current_l2:
            current_content.append(line)

    # Save the last section if we have one
    if current_l2 and current_content:
        l2_sections[current_l2] = "\n".join(current_content)

    return l2_sections


def rate_outline(
    client,
    old_outline: str,
    conv_history: Optional[str] = None,
    text_input: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Rate an outline using OpenAI API with JSON mode.
    Returns a dictionary with L1 headings as keys, containing scores and justifications.

    Args:
        client: The OpenAI client
        old_outline: The outline text to be rated (required)
        conv_history: Optional conversation history for context
        text_input: Optional text input content

    Returns:
        Dictionary with L1 headings as keys, each containing weighted score and justification
    """
    if not client or not old_outline:
        return {"error": "API client or outline not available"}

    try:
        # Build the context section of the prompt
        context_parts = []
        if text_input:
            context_parts.append(f"<relevant_text>\n{text_input}\n</relevant_text>")
        if conv_history:
            context_parts.append(
                f"<conversation_history>\n{conv_history}\n</conversation_history>"
            )

        context_section = "\n\n".join(context_parts)
        context_section = context_section + "\n\n" if context_section else ""

        prompt = f"""
        You are an expert evaluator tasked with assessing the importance and potential impact of technical outlines. Your goal is to provide a detailed, structured evaluation based on specific criteria. 

        CRITICAL INSTRUCTION: You must use the EXACT Level 1 headings (marked with single #) from the provided outline. DO NOT modify, abbreviate, or create new headings. You must copy them character-for-character exactly as they appear in the outline.

        Evaluation Dimensions & Weights:

        1. Novelty & Originality (Overall Weight: 20%)
        - NO1. Originality of Core Concepts & Methods (Weight: 20%)

        2. Transformative Potential (Overall Weight: 40%)
        - TP1. Magnitude of Anticipated Improvement (Weight: 20%)
        - TP2. Paradigm Shift Potential (Weight: 20%)

        3. Scope & Impact (Overall Weight: 30%)
        - SI1. Breadth of Applicability/Reach (Weight: 15%)
        - SI2. Significance of Problem Addressed / New Capabilities Enabled (Weight: 15%)

        4. Clarity & Feasibility of Vision (Overall Weight: 10%)
        - CF1. Clarity of Objectives and Proposed Path (Weight: 5%)
        - CF2. Perceived Technical Plausibility (based on outline) (Weight: 5%)

        Instructions:

        1. FIRST: Extract the EXACT Level 1 headings from the outline (lines starting with "# "). Copy them exactly as written.
        2. For each EXACT Level 1 heading:
           a. Evaluate it across the seven sub-dimensions (score 1-10 each)
           b. Calculate weighted score: (NO1*0.20) + (TP1*0.20) + (TP2*0.20) + (SI1*0.15) + (SI2*0.15) + (CF1*0.05) + (CF2*0.05)
        3. Sort by weighted scores (highest first)

        CRITICAL: In your JSON output, use the EXACT headings from the outline as keys. Do not modify them in any way.

        Output Format (JSON only):
        ```json
        {{
        "# EXACT_HEADING_FROM_OUTLINE_1": {{
            "weighted_score": X.XX,
            "overall_justification": "Brief justification (max 20 words)"
        }},
        "# EXACT_HEADING_FROM_OUTLINE_2": {{
            "weighted_score": X.XX,
            "overall_justification": "Brief justification (max 20 words)"
        }}
        }}
        ```

        {context_section}
        <outline_to_rate>
        {old_outline}
        </outline_to_rate>
        
        Remember: Use EXACT headings from the outline. Do not modify, shorten, or create new headings.
        """

        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="gpt-4.1",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0,
                    max_tokens=800,
                )

                # Parse the response
                if (
                    response
                    and response.choices
                    and response.choices[0].message.content
                ):
                    return json.loads(response.choices[0].message.content)
                else:
                    logger.warning("Empty response from API")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return {"error": "Empty API response"}

            except json.JSONDecodeError as e:
                logger.warning(f"Error parsing API response: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return {"error": f"Error parsing API response: {str(e)}"}

            except Exception as e:
                logger.warning(f"API call failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return {"error": f"API call failed: {str(e)}"}

    except Exception as e:
        logger.error(f"Error rating outline: {e}")
        return {"error": f"Error: {str(e)}"}


def rate_l2_headings(
    client,
    l1_section: str,
    l1_heading: str,
    conv_history: Optional[str] = None,
    text_input: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Rate L2 headings within a specific L1 section using OpenAI API with JSON mode.

    Args:
        client: The OpenAI client
        l1_section: The content of the L1 section including all L2/L3 headings
        l1_heading: The L1 heading text
        conv_history: Optional conversation history for context
        text_input: Optional text input content

    Returns:
        Dictionary with L2 headings as keys, each containing weighted score and justification
    """
    if not client or not l1_section:
        logger.error("API client or L1 section not available for L2 rating")
        return {"error": "API client or L1 section not available"}

    try:
        # Build the context section of the prompt
        context_parts = []
        if text_input:
            context_parts.append(f"<relevant_text>\n{text_input}\n</relevant_text>")
        if conv_history:
            context_parts.append(
                f"<conversation_history>\n{conv_history}\n</conversation_history>"
            )

        context_section = "\n\n".join(context_parts)
        context_section = context_section + "\n\n" if context_section else ""

        # Extract L2 headings for the prompt
        l2_headings = extract_l2_headings(l1_section)
        l2_headings_list = "\n".join(l2_headings)

        if not l2_headings:
            logger.warning(f"No L2 headings found in L1 section: '{l1_heading}'")
            return {}

        prompt = f"""
        You are an expert evaluator tasked with assessing the importance and potential impact of technical outline sections. 
        
        CRITICAL INSTRUCTION: You must use the EXACT L2 headings (marked with ##) from the provided L1 section. DO NOT modify, abbreviate, or create new headings. You must copy them character-for-character exactly as they appear.
        
        You are evaluating L2 headings within this L1 section: "{l1_heading}"
        
        EXACT L2 headings to evaluate:
        {l2_headings_list}
        
        Evaluation Dimensions & Weights:

        1. Novelty & Originality (Overall Weight: 20%)
        - NO1. Originality of Core Concepts & Methods (Weight: 20%)

        2. Transformative Potential (Overall Weight: 40%)
        - TP1. Magnitude of Anticipated Improvement (Weight: 20%)
        - TP2. Paradigm Shift Potential (Weight: 20%)

        3. Scope & Impact (Overall Weight: 30%)
        - SI1. Breadth of Applicability/Reach (Weight: 15%)
        - SI2. Significance of Problem Addressed / New Capabilities Enabled (Weight: 15%)

        4. Clarity & Feasibility of Vision (Overall Weight: 10%)
        - CF1. Clarity of Objectives and Proposed Path (Weight: 5%)
        - CF2. Perceived Technical Plausibility (based on outline) (Weight: 5%)

        Instructions:
        1. For each EXACT L2 heading:
           a. Evaluate across seven sub-dimensions (score 1-10 each)
           b. Calculate weighted score: (NO1*0.20) + (TP1*0.20) + (TP2*0.20) + (SI1*0.15) + (SI2*0.15) + (CF1*0.05) + (CF2*0.05)
        2. Sort by weighted scores (highest first)

        CRITICAL: In your JSON output, use the EXACT L2 headings as keys. Do not modify them in any way.

        Output Format (JSON only):
        ```json
        {{
        "## EXACT_L2_HEADING_FROM_SECTION_1": {{
            "weighted_score": X.XX,
            "overall_justification": "Brief justification (max 20 words)"
        }},
        "## EXACT_L2_HEADING_FROM_SECTION_2": {{
            "weighted_score": X.XX,
            "overall_justification": "Brief justification (max 20 words)"
        }}
        }}
        ```

        {context_section}
        <l1_section_to_rate>
        {l1_section}
        </l1_section_to_rate>
        
        Remember: Use EXACT L2 headings from the section. Do not modify, shorten, or create new headings.
        """
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="gpt-4.1",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0,
                    max_tokens=800,
                )

                # Parse the response
                if (
                    response
                    and response.choices
                    and response.choices[0].message.content
                ):
                    return json.loads(response.choices[0].message.content)
                else:
                    logger.warning("Empty response from API for L2 headings rating")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return {"error": "Empty API response"}

            except json.JSONDecodeError as e:
                logger.warning(
                    f"Error parsing API response for L2 headings rating: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return {"error": f"Error parsing API response: {str(e)}"}

            except Exception as e:
                logger.warning(f"API call failed for L2 headings rating: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return {"error": f"API call failed: {str(e)}"}

    except Exception as e:
        logger.error(f"Error rating L2 headings: {e}")
        return {"error": f"Error: {str(e)}"}


def reassemble_outline(
    original_outline: str,
    l1_ratings: Dict[str, Any],
    l2_ratings_by_l1: Dict[str, Dict[str, Any]] = None,
    heading_mapping: Dict[str, str] = None,
) -> str:
    """
    Reassemble the outline based on L1 and L2 ratings, reordering headings by their scores.
    Preserves the original heading levels (# for L1, ## for L2, etc.)

    Args:
        original_outline: The original outline text
        l1_ratings: Dictionary with L1 headings as keys, containing scores and justifications
        l2_ratings_by_l1: Dictionary with L1 headings as keys and L2 ratings as values
        heading_mapping: Dictionary mapping rated headings to original headings

    Returns:
        Reassembled outline text with reordered headings
    """
    if not original_outline or not l1_ratings:
        return original_outline

    # Parse the original outline to get all L1 sections
    l1_sections = parse_outline_sections(original_outline)

    if not l1_sections:
        return original_outline

    # Use heading mapping if provided, otherwise fall back to the old logic
    if heading_mapping:
        # Sort the rated headings by their scores, then map them to original headings
        sorted_rated_headings = sorted(
            heading_mapping.keys(),
            key=lambda h: l1_ratings[h].get("weighted_score", 0),
            reverse=True,
        )
        # Map to original headings
        sorted_l1_headings = [
            heading_mapping[h] for h in sorted_rated_headings if h in heading_mapping
        ]
    else:
        # Fallback to old logic
        # Check if any L1 heading key in l1_ratings starts with a different number of # than in the original outline
        # This might indicate a mismatch between what was rated and what's in the original outline
        original_level_marker = "#"  # Default
        for heading in l1_sections.keys():
            if heading.startswith("#"):
                match = re.match(r"^(#+)\s", heading)
                if match:
                    original_level_marker = match.group(1)
                    logger.info(
                        f"Found L1 heading format: '{original_level_marker}' from '{heading}'"
                    )
                    break

        logger.info(
            f"Using original L1 heading level marker: '{original_level_marker}'"
        )

        # Ensure all headings in l1_ratings use the correct heading level format
        # Create a mapping of potentially misformatted keys to correctly formatted keys
        heading_key_map = {}
        for heading in list(l1_ratings.keys()):
            # Remove all # symbols
            clean_heading = re.sub(r"^#+\s", "", heading)
            # Recreate with correct # level
            correct_heading = f"{original_level_marker} {clean_heading}"
            if heading != correct_heading:
                logger.warning(
                    f"Heading format mismatch: '{heading}' vs correct format '{correct_heading}'"
                )
                heading_key_map[heading] = correct_heading

        # Update l1_ratings keys if needed
        for old_key, new_key in heading_key_map.items():
            if old_key in l1_ratings and new_key not in l1_ratings:
                l1_ratings[new_key] = l1_ratings.pop(old_key)

        # Sort L1 headings by their weighted scores in descending order
        sorted_l1_headings = sorted(
            [key for key in l1_ratings.keys() if key in l1_sections],
            key=lambda h: l1_ratings[h].get("weighted_score", 0),
            reverse=True,
        )

        logger.info(f"Sorted L1 headings by score: {sorted_l1_headings}")

    # Initialize the reassembled outline
    reassembled_parts = []

    # Process each L1 section in the new order
    for l1_heading in sorted_l1_headings:
        # Get the content for this L1 section
        if l1_heading not in l1_sections:
            logger.warning(
                f"L1 heading '{l1_heading}' from ratings not found in original outline sections"
            )
            continue

        l1_content = l1_sections[l1_heading]

        # Check if we have L2 ratings for this L1 section
        if (
            l2_ratings_by_l1
            and l1_heading in l2_ratings_by_l1
            and l2_ratings_by_l1[l1_heading]
        ):
            # Parse the L2 sections from this L1 content
            l2_sections = parse_outline_l2_sections(l1_content)

            if l2_sections:
                # Sort L2 headings by their weighted scores in descending order
                l2_ratings = l2_ratings_by_l1[l1_heading]
                sorted_l2_headings = sorted(
                    [key for key in l2_ratings.keys() if key in l2_sections],
                    key=lambda h: l2_ratings[h].get("weighted_score", 0),
                    reverse=True,
                )

                # Start with the L1 heading (preserve original heading level)
                section_parts = [l1_heading]

                # Get any content between L1 heading and first L2 heading
                l1_lines = l1_content.split("\n")
                l1_to_l2_content = []
                found_l1 = False
                for line in l1_lines:
                    if line.strip() == l1_heading.strip():
                        found_l1 = True
                        continue
                    if found_l1 and line.strip().startswith("##"):
                        break
                    if found_l1:
                        l1_to_l2_content.append(line)

                # Add content between L1 and first L2 (if any)
                if l1_to_l2_content:
                    section_parts.extend(l1_to_l2_content)

                # Add each L2 section in the new order (preserve original heading levels)
                for l2_heading in sorted_l2_headings:
                    if l2_heading in l2_sections:
                        section_parts.append(l2_sections[l2_heading])

                # Join the section parts and add to reassembled_parts
                reassembled_parts.append("\n".join(section_parts))
            else:
                # No L2 sections, just add the L1 content as is
                reassembled_parts.append(l1_content)
        else:
            # No L2 ratings or empty L2 ratings, just add the L1 content as is
            reassembled_parts.append(l1_content)

    # Join all sections with double newlines
    result = "\n\n".join(reassembled_parts)

    return result


class OutlineRater:
    """Class to handle outline rating functionality."""

    def __init__(self, client=None, output_dir: Optional[str] = None):
        self.client = client or self._configure_openai_client()
        self.output_dir = output_dir

    def _configure_openai_client(self):
        """Configure OpenAI client based on environment variables or secrets.toml."""
        api_key = None
        try:
            current_script_path = os.path.abspath(__file__)
            # Navigate up four levels from the script's directory to reach the workspace root
            workspace_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(current_script_path)))
            )
            secrets_path = os.path.join(workspace_root, "secrets.toml")

            if os.path.exists(secrets_path):
                with open(secrets_path, "r") as f:
                    secrets = toml.load(f)
                api_key = secrets.get("OPENAI_API_KEY")
                if api_key:
                    logger.info("Loaded OPENAI_API_KEY from secrets.toml")
                else:
                    logger.warning(
                        "OPENAI_API_KEY not found in secrets.toml. Falling back to environment variables."
                    )
            else:
                logger.warning(
                    f"secrets.toml not found at expected path: {secrets_path}. Falling back to environment variables."
                )
        except Exception as e:
            logger.warning(
                f"Error reading secrets.toml: {e}. Falling back to environment variables."
            )

        # Fallback to environment variable if not found in secrets.toml or if there was an error
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                logger.info("Loaded OPENAI_API_KEY from environment variable.")

        api_type = os.getenv("OPENAI_API_TYPE", "openai").lower()

        if not api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables.")
            return None

        try:
            if api_type == "azure":
                api_base = os.getenv("AZURE_API_BASE")
                api_version = os.getenv("AZURE_API_VERSION")
                if not api_base or not api_version:
                    logger.warning(
                        "AZURE_API_BASE or AZURE_API_VERSION not found for Azure configuration."
                    )
                    return None

                client = AzureOpenAI(
                    api_key=api_key, api_version=api_version, azure_endpoint=api_base
                )
                logger.info("OpenAI client configured with Azure backend")
            else:
                client = OpenAI(api_key=api_key)
                logger.info("OpenAI client configured with OpenAI backend")
            return client
        except Exception as e:
            logger.warning(f"Failed to configure OpenAI client: {e}")
            return None

    def rate_and_reassemble_outline(
        self,
        outline: str,
        conv_history: Optional[str] = None,
        text_input: Optional[str] = None,
    ) -> str:
        """
        Rate and reassemble an outline based on ratings.

        Args:
            outline: The outline text to be rated and reassembled
            conv_history: Optional conversation history for context
            text_input: Optional text input content

        Returns:
            Reassembled outline text with reordered headings
        """
        if not self.client:
            logger.error("OpenAI client not available")
            return outline

        try:
            # First rate L1 headings
            logger.info("Starting L1 headings rating...")
            l1_ratings = rate_outline(
                self.client, outline, conv_history, text_input
            )
            if "error" in l1_ratings:
                logger.error(f"Error rating L1 headings: {l1_ratings['error']}")
                return outline

            # Parse the original outline to get all L1 sections
            l1_sections = parse_outline_sections(outline)
            if not l1_sections and outline:
                logger.warning(
                    f"No L1 sections found but outline exists. Outline content: {outline[:50]}..."
                )

            # Create a mapping between rated headings and original headings
            heading_mapping = {}

            # First try exact matching
            for original_heading in l1_sections.keys():
                if original_heading in l1_ratings:
                    heading_mapping[original_heading] = original_heading
                    logger.info(f"Exact match found: '{original_heading}'")
                else:
                    # Try fuzzy matching as fallback
                    original_clean = (
                        re.sub(r"^#+\s", "", original_heading).strip().lower()
                    )
                    best_match = None
                    best_score = 0

                    for rated_heading in l1_ratings.keys():
                        rated_clean = (
                            re.sub(r"^#+\s", "", rated_heading).strip().lower()
                        )
                        # Simple fuzzy matching: check if one is contained in the other
                        if (
                            rated_clean in original_clean
                            or original_clean in rated_clean
                        ):
                            score = len(rated_clean) / max(len(original_clean), 1)
                            if score > best_score:
                                best_score = score
                                best_match = rated_heading

                    if best_match and best_score > 0.3:  # Threshold for matching
                        heading_mapping[best_match] = original_heading
                        logger.info(
                            f"Fuzzy mapped rated heading '{best_match}' to original '{original_heading}'"
                        )
                    else:
                        logger.warning(
                            f"No good match found for original heading '{original_heading}'"
                        )

            # Then rate L2 headings for each L1 section using original headings
            logger.info("Starting L2 headings rating...")
            l2_ratings_by_l1 = {}

            # Only attempt L2 rating if client is available
            if self.client:
                for original_heading in l1_sections:
                    section_content = l1_sections[original_heading]
                    l2_headings = extract_l2_headings(section_content)

                    if l2_headings:  # Only rate if there are L2 headings
                        l2_ratings = rate_l2_headings(
                            self.client,
                            section_content,
                            original_heading,
                            conv_history,
                            text_input,
                        )
                        if (
                            "error" not in l2_ratings and l2_ratings
                        ):  # Check if not empty
                            l2_ratings_by_l1[original_heading] = l2_ratings
                        else:
                            if "error" in l2_ratings:
                                logger.error(
                                    f"Failed to get L2 ratings for L1 section '{original_heading}': {l2_ratings.get('error')}"
                                )
                            else:
                                logger.warning(
                                    f"L2 ratings empty for L1 section '{original_heading}'"
                                )
                    else:
                        logger.info(
                            f"No L2 headings found in section '{original_heading}', skipping L2 rating"
                        )
            else:
                logger.warning("No API client available, skipping L2 headings rating")

            # Save the ratings if output directory is provided
            if self.output_dir:
                try:
                    os.makedirs(self.output_dir, exist_ok=True)
                    ratings_json = {
                        "l1_ratings": l1_ratings,
                        "l2_ratings_by_l1": l2_ratings_by_l1,
                    }
                    ratings_path = os.path.join(self.output_dir, "outline_score.json")
                    with open(ratings_path, "w", encoding="utf-8") as f:
                        json.dump(ratings_json, f, indent=2)
                    logger.info(f"Saved ratings to {ratings_path}")
                except Exception as e:
                    logger.error(f"Error saving ratings: {e}")

            # Finally reassemble the outline
            logger.info("Reassembling outline...")
            reassembled_outline = reassemble_outline(
                outline, l1_ratings, l2_ratings_by_l1, heading_mapping
            )

            # Save the reassembled outline if output directory is provided
            if self.output_dir:
                try:
                    reordered_path = os.path.join(
                        self.output_dir, "reordered_outline.txt"
                    )
                    with open(reordered_path, "w", encoding="utf-8") as f:
                        f.write(reassembled_outline)
                    logger.info(f"Saved reordered outline to {reordered_path}")
                except Exception as e:
                    logger.error(f"Error saving reordered outline: {e}")

            return reassembled_outline

        except Exception as e:
            logger.error(f"Error in rate_and_reassemble_outline: {e}")
            return outline


def main():
    parser = argparse.ArgumentParser(
        description="Rate an outline based on direct input or file."
    )
    parser.add_argument(
        "--outline",
        required=True,
        help="Path to file containing the outline to be rated",
    )
    parser.add_argument(
        "--conv_history", help="Path to file containing conversation history (optional)"
    )
    parser.add_argument(
        "--text_input", help="Path to file containing text input (optional)"
    )
    parser.add_argument("--output", help="Path to output JSON file (optional)")
    parser.add_argument(
        "--stage",
        choices=["A", "B", "reassemble"],
        default="A",
        help="Stage A: Rate L1 headings, Stage B: Rate L2 headings within a specific L1 section, reassemble: Reorder outline based on ratings",
    )
    parser.add_argument(
        "--l1_heading", help="L1 heading to analyze in Stage B (required for Stage B)"
    )
    parser.add_argument(
        "--l1_ratings",
        help="Path to JSON file with L1 ratings (required for reassemble stage)",
    )
    parser.add_argument(
        "--l2_ratings",
        help="Path to JSON file with L2 ratings (optional for reassemble stage)",
    )
    parser.add_argument(
        "--reassembled_output",
        help="Path to save reassembled outline (required for reassemble stage)",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Read files
    outline_content = read_file_content(args.outline)
    conv_history = read_file_content(args.conv_history) if args.conv_history else None
    text_input = read_file_content(args.text_input) if args.text_input else None

    if not outline_content:
        logger.error("Outline content is required but could not be read.")
        return

    # Create OutlineRater instance
    rater = OutlineRater()
    if not rater.client and args.stage != "reassemble":
        logger.error("Failed to configure OpenAI client. Please check your API keys.")
        return

    # Processing based on stage
    if args.stage == "A":
        # Stage A: Rate L1 headings of the entire outline
        logger.info("Stage A: Rating L1 headings in the outline...")
        rating_result = rate_outline(
            rater.client, outline_content, conv_history, text_input
        )

    elif args.stage == "B":
        # Stage B: Rate L2 headings within a specific L1 heading
        if not args.l1_heading:
            # If L1 heading is not provided, automatically process all L1 sections
            logger.info(
                "Stage B: No specific L1 heading provided. Processing all L1 sections..."
            )

            # Parse the outline to get all L1 sections
            l1_sections = parse_outline_sections(outline_content)
            if not l1_sections:
                logger.error("No L1 sections found in the outline.")
                return

            # Rate each L1 section separately
            all_l1_ratings = {}
            for l1_heading, section_content in l1_sections.items():
                l2_ratings = rate_l2_headings(
                    rater.client,
                    section_content,
                    l1_heading,
                    conv_history,
                    text_input
                )
                all_l1_ratings[l1_heading] = l2_ratings
                time.sleep(1)  # Small delay between API calls

            rating_result = all_l1_ratings
        else:
            # Process just the specified L1 heading
            logger.info(f"Stage B: Rating L2 headings within '{args.l1_heading}'...")

            # Parse the outline to get all L1 sections
            l1_sections = parse_outline_sections(outline_content)

            # Find the matching L1 heading
            matching_heading = None
            for heading in l1_sections.keys():
                if args.l1_heading in heading:
                    matching_heading = heading
                    break

            if not matching_heading:
                logger.error(
                    f"L1 heading '{args.l1_heading}' not found in the outline."
                )
                return

            # Get the content for the matching L1 section
            section_content = l1_sections[matching_heading]

            # Rate the L2 headings within this L1 section
            rating_result = rate_l2_headings(
                rater.client,
                section_content,
                matching_heading,
                conv_history,
                text_input
            )

    elif args.stage == "reassemble":
        # Reassemble the outline based on L1 and L2 ratings
        logger.info("Reassembling outline based on ratings...")

        if not args.reassembled_output:
            logger.error(
                "Missing --reassembled_output parameter for saving the reassembled outline."
            )
            return

        if not args.l1_ratings:
            logger.error("Missing --l1_ratings parameter for reassembling the outline.")
            return

        # Read L1 ratings
        l1_ratings_content = read_file_content(args.l1_ratings)
        if not l1_ratings_content:
            logger.error("L1 ratings content could not be read.")
            return

        try:
            ratings_data = json.loads(l1_ratings_content)
            # Handle both old format (direct L1 ratings) and new format (nested structure)
            if "l1_ratings" in ratings_data:
                l1_ratings = ratings_data["l1_ratings"]
                # If L2 ratings are in the same file, use them
                if "l2_ratings_by_l1" in ratings_data and not args.l2_ratings:
                    l2_ratings_by_l1 = ratings_data["l2_ratings_by_l1"]
                else:
                    l2_ratings_by_l1 = None
            else:
                # Old format - direct L1 ratings
                l1_ratings = ratings_data
                l2_ratings_by_l1 = None
        except json.JSONDecodeError:
            logger.error("L1 ratings file contains invalid JSON.")
            return

        # Read L2 ratings if provided separately
        if args.l2_ratings:
            l2_ratings_content = read_file_content(args.l2_ratings)
            if l2_ratings_content:
                try:
                    l2_ratings_data = json.loads(l2_ratings_content)
                    # Handle both old format and new format
                    if "l2_ratings_by_l1" in l2_ratings_data:
                        l2_ratings_by_l1 = l2_ratings_data["l2_ratings_by_l1"]
                    else:
                        l2_ratings_by_l1 = l2_ratings_data
                except json.JSONDecodeError:
                    logger.error("L2 ratings file contains invalid JSON.")
                    # Continue without L2 ratings
                    l2_ratings_by_l1 = None

        # Reassemble the outline
        reassembled_outline = reassemble_outline(
            outline_content, l1_ratings, l2_ratings_by_l1, None
        )

        # Save the reassembled outline
        try:
            with open(args.reassembled_output, "w", encoding="utf-8") as f:
                f.write(reassembled_outline)
            logger.info(f"Reassembled outline saved to {args.reassembled_output}")
        except Exception as e:
            logger.error(f"Error writing reassembled outline: {e}")

        # No rating result to print for reassemble stage
        return

    # Output the rating result (for stages A and B)
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(rating_result, f, indent=2)
            logger.info(f"Rating saved to {args.output}")
        except Exception as e:
            logger.error(f"Error writing output file: {e}")

    # Also print the rating result (for stages A and B)
    print(json.dumps(rating_result, indent=2))


if __name__ == "__main__":
    main()

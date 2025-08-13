"""
Podcast generation utilities.

This module provides utilities for:
- XML conversation parsing for panel discussions
- Content extraction from knowledge base items
- Optimized text-to-speech audio generation
- Audio processing and concatenation
"""

import logging
import uuid
import json
import subprocess
import re
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import os   

import requests
from django.conf import settings

# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

# Voice mapping for Minimax TTS API
VOICE_MAPPING = {
    "alex": "Chinese (Mandarin)_Lyrical_Voice",
    "Ilya": "Chinese (Mandarin)_Humorous_Elder", 
    "feifei": "Chinese (Mandarin)_Kind-hearted_Antie",
    "dao": "Chinese (Mandarin)_Southern_Young_Man",
    "elon": "Chinese (Mandarin)_Unrestrained_Young_Man"
}

# Available voice types for speaker assignment
AVAILABLE_VOICES = ["alex", "Ilya", "feifei", "dao", "elon"]

# Content extraction limits
MAX_CONTENT_LENGTH = 8000
MAX_ITEM_PREVIEW_LENGTH = 500

logger = logging.getLogger(__name__)


# =============================================================================
# CONVERSATION PARSING FUNCTIONS
# =============================================================================

def parse_conversation(conversation_text: str) -> List[Dict[str, str]]:
    """
    Parse conversation into structured turns using bracket format.
    
    Expected format: [speaker_name] content
    
    Args:
        conversation_text: Raw conversation text with bracket format
        
    Returns:
        List of conversation turns with speaker and content
    """
    conversation_turns = []
    
    # Pattern to match bracket format: [speaker] content
    pattern = r'\[([^\]]+)\]\s*(.*?)(?=\n\[|$)'
    matches = re.findall(pattern, conversation_text, re.DOTALL)
    
    for speaker, content in matches:
        # Clean up speaker name and content
        speaker = speaker.strip()
        content = content.strip()
        
        # Extract just the name from role descriptions (e.g., "AI研究科学家 - 伊利亚" -> "伊利亚")
        if " - " in speaker:
            speaker = speaker.split(" - ")[-1].strip()
        
        if speaker and content:
            conversation_turns.append({
                'speaker': speaker,
                'content': content
            })
    
    logger.info(f"Extracted {len(conversation_turns)} conversation turns from bracket format")
    return conversation_turns


# =============================================================================
# CONTENT EXTRACTION FUNCTIONS
# =============================================================================

async def extract_selected_content(selected_item_ids: List[int]) -> str:
    """
    Extract content from selected knowledge base items.
    
    Args:
        selected_item_ids: List of KnowledgeBaseItem IDs selected by frontend
        
    Returns:
        Extracted content string from selected items
    """
    if not selected_item_ids:
        return "No content selected for podcast generation."
    
    try:
        from asgiref.sync import sync_to_async
        from notebooks.models import KnowledgeBaseItem
        
        content_parts = []
        
        # Get selected knowledge base items asynchronously
        kb_items = await sync_to_async(list)(
            KnowledgeBaseItem.objects.filter(id__in=selected_item_ids)
        )
        
        for item in kb_items:
            
            # Add main content
            if hasattr(item, 'content') and item.content:
                content_parts.append(f"Content: {item.content}")
            elif hasattr(item, 'summary') and item.summary:
                content_parts.append(f"Summary: {item.summary}")
            
            # Add separator between items
            content_parts.append("---")
        
        # Join all content
        full_content = "\n\n".join(content_parts)
        
        # Return truncated content if too long
        if len(full_content) > MAX_CONTENT_LENGTH:
            return full_content[:MAX_CONTENT_LENGTH] + "..."
        
        return full_content if full_content else "No content found for selected items."
        
    except Exception as e:
        logger.error(f"Content extraction failed for selected items {selected_item_ids}: {e}")
        return f"Error extracting content: {str(e)}"


# =============================================================================
# AUDIO PROCESSING FUNCTIONS
# =============================================================================

def create_speaker_voice_mapping(conversation: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Create a mapping of speakers to voice types for TTS.
    
    Args:
        conversation: List of conversation turns
        
    Returns:
        Dictionary mapping speaker names to voice identifiers
        
    Raises:
        ValueError: If number of speakers exceeds available voices
    """
    speakers = set()
    for turn in conversation:
        speaker = turn.get("speaker", "Unknown")
        speakers.add(speaker)
    
    logger.info(f"Found speakers in conversation: {sorted(speakers)}")
    
    # Check if we have enough voices for all speakers
    if len(speakers) > len(AVAILABLE_VOICES):
        raise ValueError(
            f"Too many speakers ({len(speakers)}) for available voices ({len(AVAILABLE_VOICES)}). "
            f"Speakers: {sorted(speakers)}, Available voices: {AVAILABLE_VOICES}"
        )
    
    # Create intentional speaker-to-voice mapping for better audio experience
    preferred_voice_mapping = {
        '雷克思': 'alex',         
        '伊利亚': 'Ilya',    
        '崔道': 'dao',  
        '李飞飞': 'feifei',
        '一龙': 'elon'
    }
    
    logger.info(f"Preferred voice mapping: {preferred_voice_mapping}")
    logger.info(f"Available voices: {AVAILABLE_VOICES}")
    
    # Map speakers to voices using preferred mapping with fallback
    speaker_voices = {}
    available_voices_copy = AVAILABLE_VOICES.copy()
    
    for speaker in sorted(speakers):
        logger.debug(f"Processing speaker: '{speaker}' (type: {type(speaker)})")
        if speaker in preferred_voice_mapping:
            voice_type = preferred_voice_mapping[speaker]
            speaker_voices[speaker] = voice_type
            logger.info(f"Assigned voice '{voice_type}' to speaker '{speaker}'")
            # Remove assigned voice from available list
            if voice_type in available_voices_copy:
                available_voices_copy.remove(voice_type)
        else:
            # Fallback: assign any available voice for unknown speakers
            if available_voices_copy:
                voice_type = available_voices_copy.pop(0)
                speaker_voices[speaker] = voice_type
                logger.warning(f"Speaker '{speaker}' not in preferred mapping. Assigned fallback voice '{voice_type}'")
            else:
                # Use default voice as last resort
                voice_type = "alex"
                speaker_voices[speaker] = voice_type
                logger.warning(f"No available voices left for speaker '{speaker}'. Using default voice '{voice_type}'")
    
    logger.debug(f"Final speaker_voices mapping: {speaker_voices}")
    return speaker_voices


def generate_audio_segment(
    content: str, 
    speaker: str, 
    voice: str, 
    segment_index: int, 
    audio_output_dir: Path
) -> Optional[Path]:
    """
    Generate audio segment for a single conversation turn.
    
    Args:
        content: Text content to convert
        speaker: Speaker name
        voice: Voice type to use
        segment_index: Index of this segment
        audio_output_dir: Directory for audio output
        
    Returns:
        Path to generated audio segment or None if failed
    """
    try:
        logger.debug(f"generate_audio_segment called: speaker='{speaker}', voice='{voice}', segment_index={segment_index}")
        
        # Create temporary file for this segment
        temp_filename = f"segment_{segment_index:03d}_{voice}.mp3"
        temp_file_path = audio_output_dir / temp_filename
        
        # Add a brief pause before speaker identification for naturalness
        if segment_index > 0:
            content_with_pause = f"... {content}"
        else:
            content_with_pause = content
        
        # Generate audio using Minimax TTS
        success = minimax_text_to_speech(content_with_pause, temp_file_path, voice)
        
        if success and temp_file_path.exists():
            return temp_file_path
        else:
            logger.warning(f"Failed to generate audio segment {segment_index} for {speaker}")
            return None
            
    except Exception as e:
        logger.error(f"Error generating audio segment for {speaker}: {e}")
        return None


def generate_audio_segment_bulk(
    content: str, 
    speaker: str, 
    voice: str, 
    audio_output_dir: Path
) -> Optional[Path]:
    """
    Generate audio for bulk content from a single speaker.
    
    Args:
        content: Combined text content for the speaker
        speaker: Speaker name
        voice: Voice type to use
        audio_output_dir: Directory for audio output
        
    Returns:
        Path to generated audio file or None if failed
    """
    try:
        logger.debug(f"generate_audio_segment_bulk called: speaker='{speaker}', voice='{voice}'")
        
        # Create filename for this speaker's audio
        temp_filename = f"speaker_{speaker}_{voice}_{uuid.uuid4().hex[:8]}.mp3"
        temp_file_path = audio_output_dir / temp_filename
        
        # Generate audio using Minimax TTS
        success = minimax_text_to_speech(content, temp_file_path, voice)
        
        if success and temp_file_path.exists():
            logger.info(f"Successfully generated bulk audio for speaker {speaker}")
            return temp_file_path
        else:
            logger.warning(f"Failed to generate bulk audio for speaker {speaker}")
            return None
            
    except Exception as e:
        logger.error(f"Error generating bulk audio for speaker {speaker}: {e}")
        return None


def generate_conversation_audio_optimized(
    conversation_turns: List[Dict[str, str]], 
    audio_output_dir: Path
) -> Optional[Path]:
    """
    Generate audio file from conversation turns using optimized approach:
    1. Group content by speaker
    2. Generate audio for each speaker's content in bulk
    3. Create individual segments and concatenate in original order
    
    Args:
        conversation_turns: List of conversation turns with speaker and content
        audio_output_dir: Directory for audio output
        
    Returns:
        Path to generated audio file or None if failed
    """
    try:
        # Create speaker voice mapping
        speaker_voices = create_speaker_voice_mapping(conversation_turns)
        
        # Group content by speaker while preserving order
        speaker_content = {}
        turn_to_speaker_segment = {}
        
        for i, turn in enumerate(conversation_turns):
            speaker = turn['speaker']
            content = turn['content'].strip()
            
            if not content:
                continue
                
            if speaker not in speaker_content:
                speaker_content[speaker] = []
            
            # Store content with turn index for mapping back
            speaker_content[speaker].append({
                'content': content,
                'turn_index': i
            })
        
        # Generate audio for each speaker's content in bulk
        speaker_audio_files = {}
        for speaker, content_list in speaker_content.items():
            voice = speaker_voices.get(speaker, "alex")
            
            # Combine all content for this speaker with separators
            combined_content = " ... ".join([item['content'] for item in content_list])
            
            # Generate single audio file for this speaker
            speaker_audio_file = generate_audio_segment_bulk(
                combined_content, speaker, voice, audio_output_dir
            )
            
            if speaker_audio_file and speaker_audio_file.exists():
                speaker_audio_files[speaker] = speaker_audio_file
                
                # Map the single audio file to each turn for this speaker
                for item in content_list:
                    turn_to_speaker_segment[item['turn_index']] = speaker_audio_file
        
        # For now, we'll create individual segments for concatenation
        # This is a simplified approach - for true optimization, we'd split the bulk audio
        audio_segments = []
        for i, turn in enumerate(conversation_turns):
            if i in turn_to_speaker_segment:
                # Generate individual segment for proper concatenation
                speaker = turn['speaker']
                content = turn['content'].strip()
                voice = speaker_voices.get(speaker, "alex")
                
                if content:
                    segment_file = generate_audio_segment(
                        content, speaker, voice, i, audio_output_dir
                    )
                    if segment_file and segment_file.exists():
                        audio_segments.append(segment_file)
        
        # Generate final audio file
        if audio_segments:
            audio_filename = f"panel_podcast_optimized_{uuid.uuid4().hex[:8]}.mp3"
            final_audio_path = audio_output_dir / audio_filename
            
            success = concatenate_audio_segments(audio_segments, final_audio_path, audio_output_dir)
            
            # Clean up temporary files
            for segment in audio_segments:
                try:
                    segment.unlink()
                except:
                    pass
            
            # Clean up speaker bulk files
            for speaker_file in speaker_audio_files.values():
                try:
                    speaker_file.unlink()
                except:
                    pass
            
            if success and final_audio_path.exists():
                return final_audio_path
        
        logger.error("No audio segments generated in optimized approach")
        return None
        
    except Exception as e:
        logger.error(f"Optimized audio generation failed: {e}")
        return None


def concatenate_audio_segments(
    segments: List[Path], 
    output_file: Path, 
    audio_output_dir: Path
) -> bool:
    """
    Concatenate multiple audio segments into a single file.
    
    Args:
        segments: List of audio segment file paths
        output_file: Final output file path
        audio_output_dir: Directory for temporary files
        
    Returns:
        True if successful, False otherwise
    """
    if not segments:
        return False
    
    try:
        # Create a temporary file list for ffmpeg
        concat_list_file = audio_output_dir / f"concat_list_{uuid.uuid4().hex[:8]}.txt"
        
        with open(concat_list_file, 'w') as f:
            for segment in segments:
                f.write(f"file '{segment.absolute()}'\n")
        
        try:
            # Try ffmpeg concatenation first
            subprocess.run([
                "ffmpeg", "-f", "concat", "-safe", "0", 
                "-i", str(concat_list_file),
                "-c", "copy", str(output_file)
            ], check=True, capture_output=True, timeout=300)
            
            # Clean up concat list file
            concat_list_file.unlink()
            return True
            
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            # Fallback: copy first file if only one segment
            if len(segments) == 1:
                import shutil
                shutil.copy2(segments[0], output_file)
                return True
            else:
                logger.warning("ffmpeg not available and multiple segments - using simple concatenation")
                return _simple_audio_concatenation(segments, output_file)
        
        finally:
            # Clean up concat list file if it exists
            if concat_list_file.exists():
                try:
                    concat_list_file.unlink()
                except:
                    pass
                    
    except Exception as e:
        logger.error(f"Error concatenating audio segments: {e}")
        return False


def _simple_audio_concatenation(segments: List[Path], output_file: Path) -> bool:
    """
    Simple fallback concatenation by combining binary data.
    
    Note: This is a basic approach and may not work well with all audio formats.
    """
    try:
        with open(output_file, 'wb') as outfile:
            for segment in segments:
                with open(segment, 'rb') as infile:
                    outfile.write(infile.read())
        return True
    except Exception as e:
        logger.error(f"Simple concatenation failed: {e}")
        return False


def minimax_text_to_speech(text: str, output_file: Path, voice: str = "alex") -> bool:
    """
    Convert text to speech using Minimax API.
    
    Args:
        text: Text to convert
        output_file: Output audio file path
        voice: Voice identifier (maps to Minimax voice IDs)
        
    Returns:
        True if successful, False otherwise
    """
    # Get Minimax API credentials from settings
    api_key = getattr(settings, 'MINIMAX_API_KEY', None)
    group_id = getattr(settings, 'MINIMAX_GROUP_ID', None)
    if not api_key or not group_id:
        raise ValueError("Minimax API key or group ID is not set")
    
    # Map local voice names to Minimax voice IDs with robust error handling
    logger.debug(f"minimax_text_to_speech called with voice parameter: '{voice}' (type: {type(voice)})")
    
    # Ensure voice is a string and handle any unexpected values
    if not isinstance(voice, str):
        logger.warning(f"Voice parameter is not a string: {voice} (type: {type(voice)}). Converting to string.")
        voice = str(voice)
    
    # Handle empty or whitespace-only voice
    if not voice or not voice.strip():
        logger.warning(f"Voice parameter is empty or whitespace. Using 'alex' as fallback.")
        voice = "alex"
    
    # Handle 'default' specifically (in case it's still passed from somewhere)
    if voice == "default":
        logger.warning(f"Voice 'default' is not supported. Using 'alex' as fallback.")
        voice = "alex"
    
    # Check if voice exists in mapping
    if voice not in VOICE_MAPPING:
        logger.warning(f"Voice '{voice}' not found in VOICE_MAPPING. Available voices: {list(VOICE_MAPPING.keys())}. Using 'alex' as fallback.")
        voice = "alex"
    
    minimax_voice = VOICE_MAPPING[voice]
    logger.debug(f"Mapped voice '{voice}' to Minimax voice: '{minimax_voice}'")
    
    # Prepare API request
    api_url = f"https://api.minimaxi.chat/v1/t2a_v2?GroupId={group_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "speech-02-hd",
        "text": text,
        "stream": False,
        "output_format": "hex",
        "voice_setting": {
            "voice_id": minimax_voice,
            "speed": 1,
            "vol": 1,
            "pitch": 0,
        },
        "audio_setting": {
            "sample_rate": 16000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1,
        },
    }
    
    logger.info(f"Generating audio with Minimax TTS: voice={minimax_voice}, text_length={len(text)}")
        
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        response_data = response.json()
        
        if response_data.get("base_resp", {}).get("status_code") == 0:
            # Get the audio data (hex string)
            audio_hex = response_data.get("data", {}).get("audio")

            if audio_hex:
                # Convert hex string to binary audio data
                audio_binary = bytes.fromhex(audio_hex)
                
                # Ensure output directory exists
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                
                with open(output_file, "wb") as f:
                    f.write(audio_binary)
                
                # Verify file was created and has content
                if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    logger.info(f"Successfully generated audio segment: {output_file}")
                    return True
                else:
                    logger.error(f"Audio file was created but is empty or invalid: {output_file}")
                    return False
            else:
                logger.error(f"No audio data (hex string) received from Minimax.")
                logger.error(f"Full response data: {response_data}")
                return False
        else:
            status_msg = response_data.get("base_resp", {}).get("status_msg", "Unknown API error")
            error_code = response_data.get("base_resp", {}).get("status_code", "N/A")
            logger.error(f"Minimax API error: {status_msg} (Code: {error_code})")
            logger.error(f"Full response data: {response_data}")
            return False

    except requests.exceptions.Timeout:
        logger.error(f"Timeout error occurred while generating audio")
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred while generating audio: {http_err}")
        try:
            logger.error(f"Response content: {response.text}")
        except:
            logger.error("Could not decode response content")
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error occurred while generating audio")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request error occurred while generating audio: {req_err}")
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON response.")
        try:
            logger.error(f"Response content: {response.text if 'response' in locals() else 'No response object'}")
        except:
            logger.error("Could not access response content")
    except Exception as e:
        logger.error(f"An unexpected error occurred generating audio: {str(e)}")
    
    return False

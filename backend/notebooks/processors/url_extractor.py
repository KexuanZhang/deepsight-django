"""
URL feature extraction and content service adapted from FastAPI DeepSight for Django.
"""

import asyncio
import logging
import os
import tempfile
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse, urlunparse
from datetime import datetime, timedelta, timezone
import re
from uuid import uuid4

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile, InMemoryUploadedFile
from django.core.exceptions import ValidationError
import io

from ..utils.storage import get_storage_adapter
from ..utils.helpers import ContentIndexingService, config as settings, clean_title
from .upload_processor import UploadProcessor

logger = logging.getLogger(__name__)


class URLExtractor:
    """URL feature extraction and content service for Django."""
    
    def __init__(self):
        self.service_name = "url_extractor"
        self.logger = logging.getLogger(f"{__name__}.url_extractor")
        
        # Initialize storage services
        self.storage_adapter = get_storage_adapter()
        self.content_indexing = ContentIndexingService()
        
        # Track ongoing processing tasks
        self.processing_tasks: Dict[str, Any] = {}
        self.url_id_mapping: Dict[str, str] = {}  # Maps upload_url_id to url_id
        
        # Initialize upload processor for transcription functionality
        self.upload_processor = UploadProcessor()
        
        # Crawl4ai lazy loading
        self._crawl4ai_loaded = False
        self._crawl4ai = None
        
        self.logger.info("URL extractor service initialized")
    
    def log_operation(self, operation: str, details: str = "", level: str = "info"):
        """Log service operations with consistent formatting."""
        message = f"[{self.service_name}] {operation}"
        if details:
            message += f": {details}"
        
        getattr(self.logger, level)(message)
    
    def _validate_url(self, url: str) -> bool:
        """Validate if the URL is well-formed"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    async def _load_crawl4ai(self):
        """Lazy load crawl4ai with proper configuration."""
        if self._crawl4ai_loaded:
            return
            
        try:
            from crawl4ai import AsyncWebCrawler
            self._crawl4ai = AsyncWebCrawler
            self._crawl4ai_loaded = True
            # crawl4ai loaded successfully
        except ImportError as e:
            self.log_operation("crawl4ai_import_error", f"crawl4ai not available: {e}", "warning")
            self._crawl4ai_loaded = False
    
    async def _check_media_availability(self, url: str) -> Dict[str, Any]:
        """Check if URL has downloadable media using yt-dlp"""
        try:
            import yt_dlp
            
            # Options for probing the URL without downloading
            probe_opts = {
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'cookiesfrombrowser': ('chrome', None, None, None),  # Use Chrome cookies by default
            }
            
            # Extract information to see what's available
            with yt_dlp.YoutubeDL(probe_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                except Exception as e:
                    # If extraction fails due to authentication, try without cookies first
                    if "Sign in to confirm" in str(e) or "bot" in str(e).lower() or "authentication" in str(e).lower():
                        self.log_operation("youtube_auth_with_cookies_failed", f"YouTube auth failed with Chrome cookies for URL: {url}", "warning")
                        
                        # Try without cookies as fallback
                        fallback_opts = probe_opts.copy()
                        fallback_opts.pop('cookiesfrombrowser', None)
                        
                        try:
                            with yt_dlp.YoutubeDL(fallback_opts) as fallback_ydl:
                                info = fallback_ydl.extract_info(url, download=False)
                                self.log_operation("youtube_fallback_success", f"Successfully accessed without cookies: {url}")
                        except Exception as fallback_e:
                            self.log_operation("youtube_auth_required", f"YouTube requires authentication for URL: {url}", "warning")
                            return {
                                "has_media": False, 
                                "error": "YouTube authentication required. Please ensure you're logged into Chrome or the content is publicly accessible.",
                                "auth_required": True
                            }
                    else:
                        raise e
            
            if not info:
                return {"has_media": False, "error": "Could not retrieve media information"}
            
            # Determine if video and audio streams exist
            formats = info.get('formats', [])
            has_video = any(f.get('vcodec') and f['vcodec'] != 'none' for f in formats)
            has_audio = any(f.get('acodec') and f['acodec'] != 'none' for f in formats)
            
            media_info = {
                "has_media": has_video or has_audio,
                "has_video": has_video,
                "has_audio": has_audio,
                "title": info.get('title', 'media_download'),
                "duration": info.get('duration'),
                "uploader": info.get('uploader'),
                "description": info.get('description', ''),
                "view_count": info.get('view_count'),
                "upload_date": info.get('upload_date')
            }
            
            return media_info
            
        except ImportError:
            return {"has_media": False, "error": "yt-dlp not available"}
        except Exception as e:
            self.log_operation("media_check_error", f"Error checking media availability for {url}: {e}", "error")
            return {"has_media": False, "error": str(e)}
    
    async def _extract_with_crawl4ai(self, url: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Extract content using crawl4ai."""
        await self._load_crawl4ai()
        
        if not self._crawl4ai_loaded:
            raise Exception("crawl4ai not available - please ensure crawl4ai is properly installed")
        
        try:
            async with self._crawl4ai(verbose=False) as crawler:
                result = await crawler.arun(
                    url=url,
                    wait_for=options.get("wait_for_js", 2),
                    bypass_cache=True,
                    word_count_threshold=10,
                    remove_overlay_elements=True,
                    screenshot=False,
                    process_iframes=options.get("extract_iframes", False),
                    exclude_tags=['nav', 'header', 'footer', 'aside'],
                    exclude_external_links=True,
                    only_text=False,
                )
                
                if not result.success:
                    error_msg = f"Crawl4ai failed with status: {getattr(result, 'status_code', 'unknown')}"
                    if hasattr(result, 'error_message') and result.error_message:
                        error_msg += f" - Error: {result.error_message}"
                    self.log_operation("crawl4ai_failed", error_msg, "error")
                    raise Exception(error_msg)
                
                features = {
                    "title": result.metadata.get("title", "") if result.metadata else "",
                    "description": result.metadata.get("description", "") if result.metadata else "",
                    "content": result.markdown or result.cleaned_html or "",
                    "links": result.links.get("internal", []) if result.links else [],
                    "images": result.media.get("images", []) if result.media else [],
                    "metadata": result.metadata or {},
                    "url": url,
                    "extraction_method": "crawl4ai"
                }
                
                return features
                
        except Exception as e:
            self.log_operation("crawl4ai_extract_error", f"Error extracting with crawl4ai from {url}: {e}", "error")
            raise
    
    async def _download_and_transcribe_media(self, url: str, media_info: Dict[str, Any]) -> Dict[str, Any]:
        """Download media from URL and transcribe it using upload processor pipeline"""
        temp_files = []
        temp_dir = None
        original_file_path = None
        try:
            import yt_dlp
            
            base_title = media_info.get('title', 'media_download')
            base_filename = clean_title(base_title)
            
            # Limit to reasonable length for filename
            max_base_length = 100  # 100 characters for base name
            if len(base_filename) > max_base_length:
                base_filename = base_filename[:max_base_length].rstrip('_')
            
            # Create temporary directory for downloads
            temp_dir = tempfile.mkdtemp(prefix="deepsight_media_")
            
            content_parts = []
            transcript_filename = f"{base_filename}.md"
            
            # Process video if available
            if media_info.get('has_video'):
                video_path = await self._download_video(url, temp_dir, base_filename)
                if video_path:
                    temp_files.append(video_path)
                    original_file_path = video_path  # Store for later copying

                    # Detect actual video format from downloaded file
                    video_filename = os.path.basename(video_path)
                    video_ext = os.path.splitext(video_filename)[1].lower()
                    
                    # Create file metadata for upload processor
                    file_metadata = {
                        'filename': f"{base_filename}_video{video_ext}",
                        'file_extension': video_ext,
                        'content_type': self._get_mime_type_from_extension(video_ext),
                        'file_size': os.path.getsize(video_path)
                    }

                    processing_result = await self.upload_processor._process_video_immediate(video_path, file_metadata)

                    if processing_result.get('content'):
                        content_parts.append(processing_result['content'])
            
            # Process audio if available (and not already processed from video)
            elif media_info.get('has_audio'):
                audio_path = await self._download_audio(url, temp_dir, base_filename)
                if audio_path:
                    temp_files.append(audio_path)
                    original_file_path = audio_path  # Store for later copying
                    
                    audio_filename = os.path.basename(audio_path)
                    audio_ext = os.path.splitext(audio_filename)[1].lower()
                    
                    file_metadata = {
                        'filename': f"{base_filename}_audio{audio_ext}",
                        'file_extension': audio_ext,
                        'content_type': self._get_mime_type_from_extension(audio_ext),
                        'file_size': os.path.getsize(audio_path)
                    }
                    
                    processing_result = await self.upload_processor._process_audio_immediate(audio_path, file_metadata)
                    
                    if processing_result.get('content'):
                        content_parts.append(processing_result['content'])
            
            # Combine all content parts
            combined_content = "\n\n".join(content_parts) if content_parts else ""
            
            if not combined_content:
                raise Exception("No content could be extracted from the media")
            
            return {
                "content": combined_content,
                "transcript_filename": transcript_filename,
                "media_info": media_info,
                "processing_type": "media",
                "original_file_path": original_file_path,
                "success": True
            }
            
        except Exception as e:
            self.log_operation("media_download_error", f"Error downloading/transcribing media: {e}", "error")
            raise
        finally:
            # Do NOT clean up temporary files here - they will be cleaned up after storage
            # The original_file_path needs to persist until after _store_processed_content
            pass
    
    def _get_mime_type_from_extension(self, extension: str) -> str:
        """Get MIME type from file extension."""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(f"file{extension}")
        return mime_type or "application/octet-stream"
    
    async def _download_video(self, url: str, temp_dir: str, base_filename: str) -> Optional[str]:
        """Download video from URL using yt-dlp."""
        try:
            import yt_dlp
            
            output_path = os.path.join(temp_dir, f"{base_filename}_video.%(ext)s")
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'outtmpl': output_path,
                'format': 'bestvideo+bestaudio/best',
                'nocheckcertificate': True,
                'cookiesfrombrowser': ('chrome', None, None, None),  # Use Chrome cookies by default
            }
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as e:
                # If download fails with cookies, try without cookies
                if "Sign in" in str(e) or "authentication" in str(e).lower() or "bot" in str(e).lower():
                    self.log_operation("video_download_cookies_failed", f"Video download with Chrome cookies failed, trying without cookies: {url}", "warning")
                    fallback_opts = ydl_opts.copy()
                    fallback_opts.pop('cookiesfrombrowser', None)
                    
                    with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                        ydl.download([url])
                else:
                    raise e
                
            # Find the downloaded file
            for file_path in Path(temp_dir).iterdir():
                if file_path.is_file() and base_filename in file_path.name:
                    self.log_operation("video_download", f"Downloaded video: {file_path}")
                    return str(file_path)
                    
            return None
            
        except Exception as e:
            self.log_operation("video_download_error", f"Error downloading video: {e}", "error")
            return None
    
    async def _download_audio(self, url: str, temp_dir: str, base_filename: str) -> Optional[str]:
        """Download audio from URL using yt-dlp."""
        try:
            import yt_dlp
            
            output_path = os.path.join(temp_dir, f"{base_filename}_audio.%(ext)s")
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'outtmpl': output_path,
                'format': 'bestaudio/best',
                'nocheckcertificate': True,
                'cookiesfrombrowser': ('chrome', None, None, None),  # Use Chrome cookies by default
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as e:
                # If download fails with cookies, try without cookies
                if "Sign in" in str(e) or "authentication" in str(e).lower() or "bot" in str(e).lower():
                    self.log_operation("audio_download_cookies_failed", f"Audio download with Chrome cookies failed, trying without cookies: {url}", "warning")
                    fallback_opts = ydl_opts.copy()
                    fallback_opts.pop('cookiesfrombrowser', None)
                    
                    with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                        ydl.download([url])
                else:
                    raise e
                
            # Find the downloaded file
            for file_path in Path(temp_dir).iterdir():
                if file_path.is_file() and base_filename in file_path.name:
                    self.log_operation("audio_download", f"Downloaded audio: {file_path}")
                    return str(file_path)
                    
            return None
            
        except Exception as e:
            self.log_operation("audio_download_error", f"Error downloading audio: {e}", "error")
            return None
    
    def _clean_markdown_content(self, content: str, features: Dict[str, Any]) -> str:
        """Clean markdown content by removing invalid image references that cause 404 errors."""
        if not content:
            return content
            
        import re
        
        # Remove image references that look like "_page_X_Figure_Y.jpeg" pattern
        # These are typically generated by crawl4ai but don't have actual files
        content = re.sub(r'!\[.*?\]\([^)]*_page_\d+_Figure_\d+\.[^)]+\)', '', content)
        
        # Remove broken image references to non-existent local files
        content = re.sub(r'!\[.*?\]\([^)]*\.(jpg|jpeg|png|gif|svg|webp)(?:\?[^)]*)?\)', 
                        lambda m: '' if not m.group(0).startswith('![](http') else m.group(0), 
                        content, flags=re.IGNORECASE)
        
        # Clean up multiple consecutive newlines left by removed images
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        return content.strip()
    
    async def process_url(self, url: str, extraction_options: Optional[Dict[str, Any]] = None, upload_url_id: Optional[str] = None, user_id: int = None, notebook_id: int = None) -> Dict[str, Any]:
        """Process URL content using crawl4ai only."""
        try:
            if not self._validate_url(url):
                raise ValueError(f"Invalid URL: {url}")
            
            # Default extraction options for basic URL processing
            options = {
                "extract_links": True,
                "extract_images": True,
                "extract_metadata": True,
                "wait_for_js": 2,
                "timeout": 30
            }
            if extraction_options:
                options.update(extraction_options)
            
            # Extract content using crawl4ai
            features = await self._extract_with_crawl4ai(url, options)
            
            # Clean markdown content
            cleaned_content = self._clean_markdown_content(features.get("content", ""), features)
            
            # Store processed content
            file_id = await self._store_processed_content(
                url=url,
                content=cleaned_content,
                features=features,
                upload_url_id=upload_url_id,
                processing_type="url_content",
                user_id=user_id,
                notebook_id=notebook_id
            )
            
            return {
                "file_id": file_id,
                "url": url,
                "status": "completed",
                "content_preview": cleaned_content[:500],
                "title": features.get("title", ""),
                "extraction_method": "crawl4ai"
            }
            
        except Exception as e:
            self.log_operation("process_url_error", f"Error processing URL {url}: {e}", "error")
            raise
    
    async def process_url_update_existing(self, url: str, kb_item_id: str, extraction_options: Optional[Dict[str, Any]] = None, upload_url_id: Optional[str] = None, user_id: int = None, notebook_id: int = None) -> Dict[str, Any]:
        """Process URL content and update an existing KnowledgeBaseItem."""
        try:
            if not self._validate_url(url):
                raise ValueError(f"Invalid URL: {url}")
            
            # Default extraction options for basic URL processing
            options = {
                "extract_links": True,
                "extract_images": True,
                "extract_metadata": True,
                "wait_for_js": 2,
                "timeout": 30
            }
            if extraction_options:
                options.update(extraction_options)
            
            # Extract content using crawl4ai
            features = await self._extract_with_crawl4ai(url, options)
            
            # Clean markdown content
            cleaned_content = self._clean_markdown_content(features.get("content", ""), features)
            
            # Update existing KnowledgeBaseItem
            await self._update_existing_kb_item(
                kb_item_id=kb_item_id,
                url=url,
                content=cleaned_content,
                features=features,
                processing_type="url_content",
                user_id=user_id
            )
            
            return {
                "file_id": kb_item_id,
                "url": url,
                "status": "completed",
                "content_preview": cleaned_content[:500],
                "title": features.get("title", ""),
                "extraction_method": "crawl4ai"
            }
            
        except Exception as e:
            self.log_operation("process_url_update_error", f"Error updating KB item {kb_item_id} with URL {url}: {e}", "error")
            raise
    
    async def process_url_with_media_update_existing(self, url: str, kb_item_id: str, extraction_options: Optional[Dict[str, Any]] = None, upload_url_id: Optional[str] = None, user_id: int = None, notebook_id: int = None) -> Dict[str, Any]:
        """Process URL content with media support and update an existing KnowledgeBaseItem."""
        try:
            if not self._validate_url(url):
                raise ValueError(f"Invalid URL: {url}")
            
            # Check for media availability
            media_info = await self._check_media_availability(url)
            
            content = ""
            processing_type = "url_content"
            original_file_path = None
            features = {}  # Initialize features to avoid UnboundLocalError
            
            if media_info.get("has_media"):
                # Download and transcribe media
                media_result = await self._download_and_transcribe_media(url, media_info)
                content = media_result.get("content", "")
                original_file_path = media_result.get("original_file_path")  # Extract the original file path
                processing_type = "media"
                # For media content, create basic features dict
                features = {
                    "title": media_info.get("title", url),
                    "url": url,
                    "extraction_method": "media_transcription"
                }
            else:
                # Fall back to regular web scraping
                options = {
                    "extract_links": True,
                    "extract_images": True,
                    "extract_metadata": True,
                    "wait_for_js": 2,
                    "timeout": 30
                }
                if extraction_options:
                    options.update(extraction_options)
                
                features = await self._extract_with_crawl4ai(url, options)
                content = features.get("content", "")
            
            # Clean markdown content
            cleaned_content = self._clean_markdown_content(content, features)
            
            # Update existing KnowledgeBaseItem
            try:
                await self._update_existing_kb_item(
                    kb_item_id=kb_item_id,
                    url=url,
                    content=cleaned_content,
                    features=features,
                    processing_type=processing_type,
                    user_id=user_id,
                    original_file_path=original_file_path  # Pass the original file path for MinIO storage
                )
            finally:
                # Clean up temporary files after storage
                if original_file_path and os.path.exists(original_file_path):
                    try:
                        # Clean up the temporary directory containing the downloaded file
                        temp_dir = os.path.dirname(original_file_path)
                        if temp_dir and os.path.exists(temp_dir) and "deepsight_media_" in temp_dir:
                            import shutil
                            shutil.rmtree(temp_dir)
                            self.log_operation("temp_cleanup", f"Cleaned up temporary directory: {temp_dir}")
                    except Exception as cleanup_err:
                        self.log_operation("cleanup_error", f"Failed to cleanup temp files: {cleanup_err}", "warning")
            
            return {
                "file_id": kb_item_id,
                "url": url,
                "status": "completed",
                "content_preview": cleaned_content[:500],
                "title": features.get("title", ""),
                "has_media": media_info.get("has_media", False),
                "processing_type": processing_type
            }
            
        except Exception as e:
            self.log_operation("process_url_media_update_error", f"Error updating KB item {kb_item_id} with media URL {url}: {e}", "error")
            raise
    
    async def process_url_with_media(self, url: str, extraction_options: Optional[Dict[str, Any]] = None, upload_url_id: Optional[str] = None, user_id: int = None, notebook_id: int = None) -> Dict[str, Any]:
        """Process URL content with media support."""
        try:
            if not self._validate_url(url):
                raise ValueError(f"Invalid URL: {url}")
            
            # Check for media availability
            media_info = await self._check_media_availability(url)
            
            content = ""
            processing_type = "url_content"
            transcript_filename = None
            original_file_path = None
            features = {}  # Initialize features to avoid UnboundLocalError
            
            if media_info.get("has_media"):
                # Download and transcribe media
                media_result = await self._download_and_transcribe_media(url, media_info)
                content = media_result.get("content", "")
                transcript_filename = media_result.get("transcript_filename")
                original_file_path = media_result.get("original_file_path")  # Get the downloaded file path
                processing_type = "media"
                # For media content, create basic features dict
                features = {
                    "title": media_info.get("title", url),
                    "url": url,
                    "extraction_method": "media_transcription"
                }
            else:
                # Fall back to regular web scraping
                options = {
                    "extract_links": True,
                    "extract_images": True,
                    "extract_metadata": True,
                    "wait_for_js": 2,
                    "timeout": 30
                }
                if extraction_options:
                    options.update(extraction_options)
                
                features = await self._extract_with_crawl4ai(url, options)
                content = features.get("content", "")
            
            # Clean markdown content
            cleaned_content = self._clean_markdown_content(content, features)
            
            # Store processed content
            file_id = await self._store_processed_content(
                url=url,
                content=cleaned_content,
                features={"title": media_info.get("title", url), "url": url},
                upload_url_id=upload_url_id,
                processing_type=processing_type,
                transcript_filename=transcript_filename,
                original_file_path=original_file_path,  # Pass the video file path
                user_id=user_id,
                notebook_id=notebook_id
            )
            
            # Clean up temporary files after storage
            if original_file_path and os.path.exists(original_file_path):
                try:
                    # Clean up the temporary directory containing the downloaded file
                    temp_dir = os.path.dirname(original_file_path)
                    if temp_dir and os.path.exists(temp_dir) and "deepsight_media_" in temp_dir:
                        import shutil
                        shutil.rmtree(temp_dir)
                        self.log_operation("temp_cleanup", f"Cleaned up temporary directory: {temp_dir}")
                except Exception as cleanup_err:
                    self.log_operation("cleanup_error", f"Failed to cleanup temp files: {cleanup_err}", "warning")
            
            return {
                "file_id": file_id,
                "url": url,
                "status": "completed",
                "content_preview": cleaned_content[:500] if cleaned_content else "",
                "title": media_info.get("title", url),
                "has_media": media_info.get("has_media", False),
                "processing_type": processing_type
            }
            
        except Exception as e:
            self.log_operation("process_url_with_media_error", f"Error processing URL with media {url}: {e}", "error")
            raise
    
    async def process_url_media_only(self, url: str, upload_url_id: Optional[str] = None, user_id: int = None, notebook_id: int = None) -> Dict[str, Any]:
        """Process URL content for media only - NO crawl4ai fallback."""
        try:
            if not self._validate_url(url):
                raise ValueError(f"Invalid URL: {url}")
            
            # Check for media availability
            media_info = await self._check_media_availability(url)
            
            # Only proceed if media is available
            if not media_info.get("has_media"):
                if media_info.get("auth_required"):
                    raise Exception(f"YouTube authentication required for URL: {url}")
                else:
                    raise Exception(f"No downloadable media found at URL: {url}")
            
            # Download and transcribe media
            media_result = await self._download_and_transcribe_media(url, media_info)
            
            if not media_result.get("success"):
                raise Exception(f"Media processing failed: {media_result.get('error', 'Unknown error')}")
            
            content = media_result.get("content", "")
            transcript_filename = media_result.get("transcript_filename")
            original_file_path = media_result.get("original_file_path")
            
            if not content:
                raise Exception("No content could be extracted from the media")
            
            try:
                # Clean markdown content
                cleaned_content = self._clean_markdown_content(content, media_info)
                
                # Store processed content with original file
                file_id = await self._store_processed_content(
                    url=url,
                    content=cleaned_content,
                    features={"title": media_info.get("title", url), "url": url},
                    upload_url_id=upload_url_id,
                    processing_type="media",
                    transcript_filename=transcript_filename,
                    original_file_path=original_file_path,
                    user_id=user_id,
                    notebook_id=notebook_id
                )
            finally:
                # Clean up temporary files after storage
                if original_file_path and os.path.exists(original_file_path):
                    try:
                        temp_dir = os.path.dirname(original_file_path)
                        if temp_dir and "deepsight_media_" in temp_dir:
                            import shutil
                            shutil.rmtree(temp_dir)
                            self.log_operation("temp_cleanup", f"Cleaned up temporary directory: {temp_dir}")
                    except Exception as cleanup_err:
                        self.log_operation("cleanup_error", f"Failed to cleanup temp files: {cleanup_err}", "warning")
            
            return {
                "file_id": file_id,
                "url": url,
                "status": "completed",
                "content_preview": cleaned_content[:500] if cleaned_content else "",
                "title": media_info.get("title", url),
                "has_media": True,
                "processing_type": "media",
                "transcript_filename": transcript_filename
            }
            
        except Exception as e:
            self.log_operation("process_url_media_only_error", f"Error processing URL media only {url}: {e}", "error")
            raise
    
    async def process_url_document_update_existing(self, url: str, kb_item_id: str, upload_url_id: Optional[str] = None, user_id: int = None, notebook_id: int = None) -> Dict[str, Any]:
        """Process URL as document download and update existing KnowledgeBaseItem."""
        temp_file_path = None
        try:
            if not self._validate_url(url):
                raise ValueError(f"Invalid URL: {url}")
            
            self.log_operation("document_download_start", f"Starting document download from {url}")
            
            # Download file to temporary location
            temp_file_path = await self._download_document_to_temp(url)
            
            # Validate file format
            file_info = await self._validate_document_format(temp_file_path)
            
            if not file_info["is_valid"]:
                raise ValueError(f"Invalid document format. Expected PDF or PPTX, got: {file_info['detected_type']}")
            
            # Process the document and update existing KB item
            await self._process_and_update_document_file(temp_file_path, file_info, url, kb_item_id, user_id, notebook_id)
            
            return {
                "file_id": kb_item_id,
                "url": url, 
                "status": "completed",
                "title": file_info.get("filename", url),
                "processing_type": "document",
                "file_extension": file_info["extension"],
                "file_size": file_info["size"]
            }
            
        except Exception as e:
            self.log_operation("process_url_document_update_error", f"Error updating KB item {kb_item_id} with document URL {url}: {e}", "error")
            raise
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    self.log_operation("temp_cleanup", f"Cleaned up temporary file: {temp_file_path}")
                except Exception as cleanup_error:
                    self.log_operation("temp_cleanup_error", f"Error cleaning up {temp_file_path}: {cleanup_error}", "warning")
    
    async def process_url_document_only(self, url: str, upload_url_id: Optional[str] = None, user_id: int = None, notebook_id: int = None) -> Dict[str, Any]:
        """Process URL as document download - validates format and only saves PDF/PPTX files."""
        temp_file_path = None
        try:
            if not self._validate_url(url):
                raise ValueError(f"Invalid URL: {url}")
            
            self.log_operation("document_download_start", f"Starting document download from {url}")
            
            # Download file to temporary location
            temp_file_path = await self._download_document_to_temp(url)
            
            # Validate file format
            file_info = await self._validate_document_format(temp_file_path)
            
            if not file_info["is_valid"]:
                raise ValueError(f"Invalid document format. Expected PDF or PPTX, got: {file_info['detected_type']}")
            
            # Process the document using upload processor
            processed_result = await self._process_document_file(temp_file_path, file_info, url, upload_url_id, user_id, notebook_id)
            
            # processed_result should have the structure from upload processor
            return {
                "file_id": processed_result.get("file_id"),
                "url": url, 
                "status": processed_result.get("status", "completed"),
                "content_preview": processed_result.get("content_preview", ""),
                "title": file_info.get("filename", url),
                "processing_type": "document",
                "file_extension": file_info["extension"],
                "file_size": file_info["size"]
            }
            
        except Exception as e:
            self.log_operation("process_url_document_error", f"Error processing document URL {url}: {e}", "error")
            raise
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    self.log_operation("temp_cleanup", f"Cleaned up temporary file: {temp_file_path}")
                except Exception as cleanup_error:
                    self.log_operation("temp_cleanup_error", f"Error cleaning up {temp_file_path}: {cleanup_error}", "warning")
    
    async def _download_document_to_temp(self, url: str) -> str:
        """Download document from URL to temporary file."""
        import aiohttp
        import aiofiles
        
        try:
            temp_dir = tempfile.mkdtemp()
            # Generate filename from URL or use generic name
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path) or "document"
            if not filename:
                filename = "document.tmp"
                self.log_operation("debug_filename_fallback", f"Empty filename, using fallback: {filename}")
            
            temp_file_path = os.path.join(temp_dir, filename)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to download document: HTTP {response.status}")
                    
                    # Check content type if available
                    content_type = response.headers.get('content-type', '').lower()
                    self.log_operation("download_info", f"Content-Type: {content_type}, URL: {url}")
                    
                    async with aiofiles.open(temp_file_path, 'wb') as temp_file:
                        async for chunk in response.content.iter_chunked(8192):
                            await temp_file.write(chunk)
            
            # Fix file extension based on detected content type or magic detection
            corrected_path = await self._fix_file_extension(temp_file_path, content_type)
            corrected_filename = os.path.basename(corrected_path)
            
            self.log_operation("document_downloaded", f"Downloaded {os.path.getsize(corrected_path)} bytes to {corrected_path}")
            return corrected_path
            
        except Exception as e:
            self.log_operation("download_error", f"Error downloading document from {url}: {e}", "error")
            raise
    
    async def _fix_file_extension(self, file_path: str, content_type: str) -> str:
        """Fix file extension based on content type or magic detection."""
        import magic
        import shutil
        
        try:
            # Detect actual file type using magic
            mime_type = magic.from_file(file_path, mime=True)
            
            # Determine correct extension
            correct_extension = None
            if mime_type == 'application/pdf' or 'application/pdf' in content_type:
                correct_extension = '.pdf'
            elif mime_type in ['application/vnd.openxmlformats-officedocument.presentationml.presentation'] or 'powerpoint' in content_type.lower():
                correct_extension = '.pptx'
            elif mime_type == 'application/vnd.ms-powerpoint':
                correct_extension = '.ppt'
            
            # If we need to fix the extension
            if correct_extension:
                current_path = Path(file_path)
                current_extension = current_path.suffix.lower()
                
                # Only rename if extension is missing or incorrect
                if not current_extension or current_extension != correct_extension:
                    # For document files, preserve the original filename and add correct extension
                    original_name = current_path.name
                    
                    # Only remove extension if it's a known file extension, not just any suffix
                    known_extensions = {'.pdf', '.ppt', '.pptx', '.doc', '.docx', '.txt', '.md', '.html', '.htm', '.zip', '.tar', '.gz'}
                    if current_extension and current_extension in known_extensions:
                        # Remove the known extension and add the correct one
                        original_name = original_name[:-len(current_extension)]
                    
                    # Use clean_title to sanitize the filename and add correct extension
                    clean_base_name = clean_title(original_name)
                    new_filename = clean_base_name + correct_extension
                    new_path = current_path.parent / new_filename
                    
                    shutil.move(str(current_path), str(new_path))
                    self.log_operation("extension_fixed", f"Fixed extension from {current_extension} to {correct_extension}")
                    return str(new_path)
            
            return file_path
            
        except Exception as e:
            self.log_operation("extension_fix_error", f"Error fixing extension: {e}", "warning")
            return file_path
    
    async def _validate_document_format(self, file_path: str) -> Dict[str, Any]:
        """Validate that the downloaded file is a PDF or PPTX."""
        import magic
        
        try:
            # Get file info
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)
            
            
            # Detect file type using python-magic
            mime_type = magic.from_file(file_path, mime=True)
            file_type = magic.from_file(file_path)
            
            self.log_operation("file_validation", f"File: {filename}, MIME: {mime_type}, Type: {file_type}")
            
            # Check if it's a valid document format
            is_pdf = mime_type == 'application/pdf' or 'PDF' in file_type
            is_pptx = (mime_type in ['application/vnd.openxmlformats-officedocument.presentationml.presentation'] or 
                      'PowerPoint' in file_type or 'Microsoft Office' in file_type)
            
            is_valid = is_pdf or is_pptx
            
            if is_pdf:
                extension = '.pdf'
                detected_type = 'PDF'
            elif is_pptx:
                extension = '.pptx'
                detected_type = 'PowerPoint'
            else:
                extension = '.unknown'
                detected_type = f'Unknown ({mime_type})'
            
            return {
                "is_valid": is_valid,
                "extension": extension,
                "detected_type": detected_type,
                "mime_type": mime_type,
                "size": file_size,
                "filename": filename
            }
            
        except Exception as e:
            self.log_operation("validation_error", f"Error validating file format: {e}", "error")
            raise
    
    async def _process_document_file(self, file_path: str, file_info: Dict, url: str, upload_url_id: Optional[str], user_id: int, notebook_id: int) -> Dict[str, Any]:
        """Process the validated document file using upload processor."""
        try:
            # Create a Django UploadedFile object from the temporary file
            with open(file_path, 'rb') as temp_file:
                file_content = temp_file.read()
            
            # Create an InMemoryUploadedFile that acts like an uploaded file
            django_file = InMemoryUploadedFile(
                file=io.BytesIO(file_content),
                field_name='file',
                name=file_info["filename"],
                content_type=file_info["mime_type"],
                size=file_info["size"],
                charset=None
            )
            
            # Add source_url to the file metadata for duplicate detection
            # We'll need to modify the upload processor to handle this metadata
            if hasattr(django_file, 'source_url'):
                django_file.source_url = url
            else:
                # Store it as an attribute that can be accessed later
                django_file._source_url = url
            
            # Use upload processor to handle the file
            result = await self.upload_processor.process_upload(
                file=django_file,
                upload_file_id=upload_url_id,
                user_pk=user_id,
                notebook_id=notebook_id
            )
            
            # Log the result structure for debugging
            self.log_operation("upload_result", f"Upload processor returned: {result}")
            
            return result
            
        except Exception as e:
            self.log_operation("document_processing_error", f"Error processing document file: {e}", "error")
            raise
    
    async def _process_and_update_document_file(self, file_path: str, file_info: Dict, url: str, kb_item_id: str, user_id: int, notebook_id: int = None) -> None:
        """Process the validated document file and update existing KnowledgeBaseItem."""
        try:
            # Create a Django UploadedFile object from the temporary file
            with open(file_path, 'rb') as temp_file:
                file_content = temp_file.read()
            
            # Create an InMemoryUploadedFile that acts like an uploaded file
            django_file = InMemoryUploadedFile(
                file=io.BytesIO(file_content),
                field_name='file',
                name=file_info["filename"],
                content_type=file_info["mime_type"],
                size=len(file_content),
                charset=None,
            )
            
            # Add source_url to the file metadata for duplicate detection
            django_file._source_url = url
            
            # Process the file using upload processor to update existing KB item
            result = await self.upload_processor.process_upload(
                django_file, 
                upload_file_id=uuid4().hex,
                user_pk=user_id,
                notebook_id=notebook_id,
                kb_item_id=kb_item_id  # Update existing item
            )
            
            # The upload processor will have updated the KB item content
            self.log_operation("document_processed", f"Successfully processed and updated document from URL: {url}")
            
        except Exception as e:
            self.log_operation("document_update_error", f"Error processing and updating document file: {e}", "error")
            raise
    
    async def _store_processed_content(self, url: str, content: str, features: Dict[str, Any], upload_url_id: Optional[str], processing_type: str, transcript_filename: Optional[str] = None, original_file_path: Optional[str] = None, user_id: int = None, notebook_id: int = None) -> str:
        """Store processed URL content."""
        try:
            # Determine appropriate filename based on content type
            if original_file_path and processing_type == "media":
                # For media files, use the original video filename
                original_basename = os.path.basename(original_file_path)
                url_metadata = {
                    "source_url": url,
                    "original_filename": original_basename,
                    "file_extension": os.path.splitext(original_basename)[1],
                    "content_type": self._get_mime_type_from_extension(os.path.splitext(original_basename)[1]),
                    "file_size": os.path.getsize(original_file_path) if os.path.exists(original_file_path) else len(content.encode('utf-8')),
                    "upload_timestamp": datetime.now().isoformat(),
                    "parsing_status": "completed",
                    "processing_metadata": {
                        "extraction_type": "url_extractor",
                        "extraction_success": True,
                        "extraction_method": "yt-dlp",
                        "content_length": len(content),
                        "processing_type": processing_type
                    },
                    "upload_url_id": upload_url_id,
                    "transcript_filename": transcript_filename
                }
            else:
                # For non-media content, use markdown filename
                url_metadata = {
                    "source_url": url,
                    "original_filename": f"{features.get('title', 'webpage')}.md",
                    "file_extension": ".md",
                    "content_type": "text/markdown",
                    "file_size": len(content.encode('utf-8')),
                    "upload_timestamp": datetime.now().isoformat(),
                    "parsing_status": "completed",
                    "processing_metadata": {
                        "extraction_type": "url_extractor",
                        "extraction_success": True,
                        "extraction_method": features.get("extraction_method", "crawl4ai"),
                        "content_length": len(content),
                        "processing_type": processing_type
                    },
                    "upload_url_id": upload_url_id,
                    "transcript_filename": transcript_filename
                }
            
            # Use sync_to_async to call the synchronous storage method
            # Use thread_sensitive=False to run in thread pool where sync ORM calls are allowed
            from asgiref.sync import sync_to_async
            store_file_sync = sync_to_async(self.storage_adapter.store_processed_file, thread_sensitive=False)
            
            # Store the processed content with original file if available
            processing_result_data = {
                'processing_type': processing_type,
                'features_available': ['media_transcription' if processing_type == 'media' else 'url_content'],
                'processing_time': 'immediate'
            }
            
            # For media processing, use transcript filename instead of default extracted_content.md
            if processing_type == "media" and transcript_filename:
                processing_result_data['content_filename'] = transcript_filename
            
            file_id = await store_file_sync(
                content=content,
                metadata=url_metadata,
                processing_result=processing_result_data,
                user_id=user_id,
                notebook_id=notebook_id,
                original_file_path=original_file_path,  # Pass the original file to be stored
                source_identifier=url  # Pass URL for source hash calculation
            )
            
            # Store mapping if upload_url_id is provided
            if upload_url_id:
                self.url_id_mapping[upload_url_id] = file_id
            
            self.log_operation("store_content", f"Stored URL content with file_id: {file_id}")
            return file_id
            
        except Exception as e:
            self.log_operation("store_content_error", f"Error storing URL content: {e}", "error")
            raise
    
    async def _update_existing_kb_item(self, kb_item_id: str, url: str, content: str, features: Dict[str, Any], processing_type: str, user_id: int, original_file_path: Optional[str] = None) -> None:
        """Update an existing KnowledgeBaseItem with processed content using proper minio storage."""
        try:
            # Import models inside method to avoid circular imports
            from ..models import KnowledgeBaseItem
            from asgiref.sync import sync_to_async
            
            # Get the existing KB item to get the notebook ID
            get_kb_item_sync = sync_to_async(KnowledgeBaseItem.objects.get, thread_sensitive=False)
            kb_item = await get_kb_item_sync(id=kb_item_id)
            
            # Get the notebook ID directly from KnowledgeBaseItem (now notebook-specific)
            notebook_id = kb_item.notebook_id
            
            # Determine appropriate filename and metadata based on content type
            if original_file_path and processing_type == "media":
                # For media files, use the original video filename and metadata
                original_basename = os.path.basename(original_file_path)
                file_metadata = {
                    "source_url": url,
                    "original_filename": original_basename,
                    "file_extension": os.path.splitext(original_basename)[1],
                    "content_type": self._get_mime_type_from_extension(os.path.splitext(original_basename)[1]),
                    "file_size": os.path.getsize(original_file_path) if os.path.exists(original_file_path) else len(content.encode('utf-8')),
                    "parsing_status": "completed",
                    "processing_metadata": {
                        "extraction_type": "url_extractor",
                        "extraction_success": True,
                        "extraction_method": "yt-dlp",
                        "content_length": len(content),
                        "processing_type": processing_type
                    }
                }
                
                # For media processing, use transcript filename instead of default extracted_content.md
                processing_result = {
                    "content": content,
                    "title": features.get("title", "media"),
                    "content_filename": f"{features.get('title', 'media')}.md",
                    "features_available": ["media_transcription"],
                    "metadata": features
                }
            else:
                # For non-media content, use markdown filename
                file_metadata = {
                    "original_filename": f"{features.get('title', 'webpage')}.md",
                    "file_extension": ".md",
                    "content_type": "text/markdown",
                    "file_size": len(content.encode('utf-8')),
                    "parsing_status": "completed",
                    "source_url": url,
                    "processing_metadata": {
                        "extraction_type": "url_extractor",
                        "extraction_success": True,
                        "extraction_method": features.get("extraction_method", "crawl4ai"),
                        "content_length": len(content),
                        "processing_type": processing_type
                    }
                }
                
                # Prepare processing result for storage
                processing_result = {
                    "content": content,
                    "title": features.get("title", "webpage"),
                    "content_filename": f"{features.get('title', 'webpage')}.md",
                    "features_available": ["text_content"],
                    "metadata": features
                }
            
            # Use the storage adapter to properly store content in minio and update database
            if not self.storage_adapter:
                raise Exception("Storage adapter not available")
            
            # Call store_processed_file with the existing kb_item_id to update it
            store_file_sync = sync_to_async(self.storage_adapter.store_processed_file, thread_sensitive=False)
            await store_file_sync(
                content=content,
                metadata=file_metadata,
                processing_result=processing_result,
                user_id=user_id,
                notebook_id=notebook_id,
                original_file_path=original_file_path,  # Pass the original file path for MinIO storage
                source_identifier=url,  # Use URL as source identifier for duplicate detection
                kb_item_id=kb_item_id   # Update existing KB item
            )
            
            self.log_operation("update_kb_item", f"Updated existing KB item {kb_item_id} with URL content using minio storage")
            
        except Exception as e:
            self.log_operation("update_kb_item_error", f"Error updating existing KB item {kb_item_id}: {e}", "error")
            raise
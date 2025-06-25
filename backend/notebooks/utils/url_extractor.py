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
from datetime import datetime, timedelta
import re

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile

from .file_storage import FileStorageService
from .content_index import ContentIndexingService
from .upload_processor import UploadProcessor
from .config import config as settings

logger = logging.getLogger(__name__)


class URLExtractor:
    """URL feature extraction and content service for Django."""
    
    def __init__(self):
        self.service_name = "url_extractor"
        self.logger = logging.getLogger(f"{__name__}.url_extractor")
        
        # Initialize storage services
        self.file_storage = FileStorageService()
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
            self.log_operation("crawl4ai_loaded", "Successfully loaded crawl4ai")
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
            }
            
            # Extract information to see what's available
            with yt_dlp.YoutubeDL(probe_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                except Exception as e:
                    # If extraction fails due to authentication, return appropriate error
                    if "Sign in to confirm" in str(e) or "bot" in str(e).lower():
                        self.log_operation("youtube_auth_required", f"YouTube requires authentication for URL: {url}", "warning")
                        return {
                            "has_media": False, 
                            "error": "YouTube authentication required",
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
            raise Exception("crawl4ai not available")
        
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
                    raise Exception(f"Crawl4ai failed: {result.status_code}")
                
                features = {
                    "title": result.metadata.get("title", ""),
                    "description": result.metadata.get("description", ""),
                    "content": result.markdown or result.cleaned_html or "",
                    "links": result.links.get("internal", []) if result.links else [],
                    "images": result.media.get("images", []) if result.media else [],
                    "metadata": result.metadata or {},
                    "url": url,
                    "extraction_method": "crawl4ai"
                }
                
                return features
                
        except Exception as e:
            self.log_operation("crawl4ai_extract_error", f"Error extracting with crawl4ai: {e}", "error")
            raise
    
    async def _download_and_transcribe_media(self, url: str, media_info: Dict[str, Any]) -> Dict[str, Any]:
        """Download media from URL and transcribe it using upload processor pipeline"""
        temp_files = []
        try:
            import yt_dlp
            
            base_title = media_info.get('title', 'media_download')
            base_filename = self._clean_title(base_title)
            
            # Create temporary directory for downloads
            temp_dir = tempfile.mkdtemp(prefix="deepsight_media_")
            
            content_parts = []
            transcript_filename = f"{base_filename}_transcript.md"
            
            # Process video if available
            if media_info.get('has_video'):
                video_path = await self._download_video(url, temp_dir, base_filename)
                if video_path:
                    temp_files.append(video_path)

                    # Detect actual video format from downloaded file
                    video_filename = os.path.basename(video_path)
                    video_ext = os.path.splitext(video_filename)[1].lower()
                    
                    # Create file metadata for upload processor
                    file_metadata = {
                        'filename': f"{base_filename}_video{video_ext}",
                        'file_extension': video_ext,
                        'file_size': os.path.getsize(video_path)
                    }

                    processing_result = self.upload_processor._process_video_immediate(video_path, file_metadata)

                    if processing_result.get('content'):
                        content_parts.append(processing_result['content'])
            
            # Process audio if available (and not already processed from video)
            elif media_info.get('has_audio'):
                audio_path = await self._download_audio(url, temp_dir, base_filename)
                if audio_path:
                    temp_files.append(audio_path)
                    
                    audio_filename = os.path.basename(audio_path)
                    audio_ext = os.path.splitext(audio_filename)[1].lower()
                    
                    file_metadata = {
                        'filename': f"{base_filename}_audio{audio_ext}",
                        'file_extension': audio_ext,
                        'file_size': os.path.getsize(audio_path)
                    }
                    
                    processing_result = self.upload_processor._process_audio_immediate(audio_path, file_metadata)
                    
                    if processing_result.get('content'):
                        content_parts.append(processing_result['content'])
            
            # Combine all content parts
            combined_content = "\n\n".join(content_parts) if content_parts else ""
            
            return {
                "content": combined_content,
                "transcript_filename": transcript_filename,
                "media_info": media_info,
                "processing_type": "media"
            }
            
        except Exception as e:
            self.log_operation("media_download_error", f"Error downloading/transcribing media: {e}", "error")
            raise
        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
    
    async def _download_video(self, url: str, temp_dir: str, base_filename: str) -> Optional[str]:
        """Download video from URL using yt-dlp."""
        try:
            import yt_dlp
            
            output_path = os.path.join(temp_dir, f"{base_filename}_video.%(ext)s")
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'outtmpl': output_path,
                'format': 'best[height<=720]/best',  # Limit to 720p for processing
                'nocheckcertificate': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
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
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
            # Find the downloaded file
            for file_path in Path(temp_dir).iterdir():
                if file_path.is_file() and base_filename in file_path.name:
                    self.log_operation("audio_download", f"Downloaded audio: {file_path}")
                    return str(file_path)
                    
            return None
            
        except Exception as e:
            self.log_operation("audio_download_error", f"Error downloading audio: {e}", "error")
            return None
    
    def _clean_title(self, title: str) -> str:
        """Clean title for filename usage."""
        # Remove invalid filename characters
        cleaned = re.sub(r'[<>:"/\\|?*]', '', title)
        # Replace spaces with underscores
        cleaned = re.sub(r'\s+', '_', cleaned)
        # Limit length
        return cleaned[:100]
    
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
            
            # Store processed content
            file_id = await self._store_processed_content(
                url=url,
                content=features.get("content", ""),
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
                "content_preview": features.get("content", "")[:500],
                "title": features.get("title", ""),
                "extraction_method": "crawl4ai"
            }
            
        except Exception as e:
            self.log_operation("process_url_error", f"Error processing URL {url}: {e}", "error")
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
            
            if media_info.get("has_media"):
                # Download and transcribe media
                media_result = await self._download_and_transcribe_media(url, media_info)
                content = media_result.get("content", "")
                transcript_filename = media_result.get("transcript_filename")
                processing_type = "media"
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
            
            # Store processed content
            file_id = await self._store_processed_content(
                url=url,
                content=content,
                features={"title": media_info.get("title", url), "url": url},
                upload_url_id=upload_url_id,
                processing_type=processing_type,
                transcript_filename=transcript_filename,
                user_id=user_id,
                notebook_id=notebook_id
            )
            
            return {
                "file_id": file_id,
                "url": url,
                "status": "completed",
                "content_preview": content[:500] if content else "",
                "title": media_info.get("title", url),
                "has_media": media_info.get("has_media", False),
                "processing_type": processing_type
            }
            
        except Exception as e:
            self.log_operation("process_url_with_media_error", f"Error processing URL with media {url}: {e}", "error")
            raise
    
    async def _store_processed_content(self, url: str, content: str, features: Dict[str, Any], upload_url_id: Optional[str], processing_type: str, transcript_filename: Optional[str] = None, user_id: int = None, notebook_id: int = None) -> str:
        """Store processed URL content."""
        try:
            # Create URL metadata
            url_metadata = {
                "source_url": url,
                "original_filename": f"{features.get('title', 'webpage')}.md",
                "file_extension": ".md",
                "content_type": "text/markdown",
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
            from asgiref.sync import sync_to_async
            store_file_sync = sync_to_async(self.file_storage.store_processed_file)
            
            # Store the processed content
            file_id = await store_file_sync(
                content=content,
                metadata=url_metadata,
                processing_result={
                    'processing_type': processing_type,
                    'features_available': ['url_content'],
                    'processing_time': 'immediate'
                },
                user_id=user_id,
                notebook_id=notebook_id
            )
            
            # Store mapping if upload_url_id is provided
            if upload_url_id:
                self.url_id_mapping[upload_url_id] = file_id
            
            self.log_operation("store_content", f"Stored URL content with file_id: {file_id}")
            return file_id
            
        except Exception as e:
            self.log_operation("store_content_error", f"Error storing URL content: {e}", "error")
            raise 
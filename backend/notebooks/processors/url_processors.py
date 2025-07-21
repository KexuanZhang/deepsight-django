"""
URL Processors - Handle URL domain specific processing logic
"""
import os
import re
import asyncio
import logging
import tempfile
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class URLProcessor:
    """Handle URL domain specific processing"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.url_processor")
        
        # Domain-specific processors
        self.domain_processors = {
            'youtube.com': self.process_youtube_url,
            'youtu.be': self.process_youtube_url,
            'arxiv.org': self.process_arxiv_url,
            'github.com': self.process_github_url,
            'default': self.process_general_webpage
        }

    def get_domain_processor(self, url: str):
        """Get the appropriate processor for a URL domain."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove 'www.' prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Find specific processor or use default
        return self.domain_processors.get(domain, self.domain_processors['default'])

    async def process_url_by_domain(self, url: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process URL using domain-specific processor."""
        processor = self.get_domain_processor(url)
        return await processor(url, options or {})

    async def process_youtube_url(self, url: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Process YouTube URLs with enhanced metadata and transcript extraction."""
        try:
            self.logger.info(f"Processing YouTube URL: {url}")
            
            # Extract video ID from URL
            video_id = self._extract_youtube_video_id(url)
            if not video_id:
                raise ValueError("Could not extract YouTube video ID from URL")

            # Try to get video info and transcript using yt-dlp
            try:
                import yt_dlp
                
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'skip_download': True,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    # Extract video metadata
                    metadata = {
                        'title': info.get('title', ''),
                        'description': info.get('description', ''),
                        'duration': info.get('duration', 0),
                        'view_count': info.get('view_count', 0),
                        'like_count': info.get('like_count', 0),
                        'uploader': info.get('uploader', ''),
                        'upload_date': info.get('upload_date', ''),
                        'video_id': video_id,
                        'url': url,
                        'processing_method': 'youtube_yt_dlp'
                    }
                    
                    # Try to extract transcript/subtitles
                    transcript = ""
                    if 'subtitles' in info and info['subtitles']:
                        # Use manual subtitles if available
                        for lang in ['en', 'en-US', 'en-GB']:
                            if lang in info['subtitles']:
                                transcript = await self._extract_subtitle_text(info['subtitles'][lang])
                                break
                    
                    if not transcript and 'automatic_captions' in info and info['automatic_captions']:
                        # Fall back to automatic captions
                        for lang in ['en', 'en-US', 'en-GB']:
                            if lang in info['automatic_captions']:
                                transcript = await self._extract_subtitle_text(info['automatic_captions'][lang])
                                break
                    
                    # Create content combining metadata and transcript
                    content = f"# {metadata['title']}\n\n"
                    if metadata['description']:
                        content += f"**Description:** {metadata['description']}\n\n"
                    content += f"**Uploader:** {metadata['uploader']}\n"
                    content += f"**Duration:** {metadata['duration']} seconds\n"
                    content += f"**Views:** {metadata['view_count']}\n\n"
                    
                    if transcript:
                        content += "## Transcript\n\n" + transcript
                    else:
                        content += "## Transcript\n\nNo transcript available for this video."
                    
                    return {
                        'content': content,
                        'metadata': metadata,
                        'features_available': ['video_metadata', 'transcript_extraction', 'youtube_api'],
                        'processing_time': 'immediate',
                        'has_media': True
                    }
                    
            except ImportError:
                # Fallback if yt-dlp is not available
                return await self.process_general_webpage(url, options)
                
        except Exception as e:
            self.logger.error(f"YouTube processing failed: {e}")
            # Fallback to general webpage processing
            return await self.process_general_webpage(url, options)

    async def process_arxiv_url(self, url: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Process arXiv URLs with enhanced paper metadata."""
        try:
            self.logger.info(f"Processing arXiv URL: {url}")
            
            # Extract arXiv ID
            arxiv_id = self._extract_arxiv_id(url)
            if not arxiv_id:
                raise ValueError("Could not extract arXiv ID from URL")

            # Try to get arXiv metadata
            try:
                import feedparser
                
                # Fetch paper metadata from arXiv API
                api_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
                feed = feedparser.parse(api_url)
                
                if feed.entries:
                    entry = feed.entries[0]
                    
                    # Extract metadata
                    metadata = {
                        'title': entry.get('title', ''),
                        'summary': entry.get('summary', ''),
                        'authors': [author.name for author in entry.get('authors', [])],
                        'published': entry.get('published', ''),
                        'updated': entry.get('updated', ''),
                        'arxiv_id': arxiv_id,
                        'categories': [tag.term for tag in entry.get('tags', [])],
                        'url': url,
                        'processing_method': 'arxiv_api'
                    }
                    
                    # Create formatted content
                    content = f"# {metadata['title']}\n\n"
                    content += f"**Authors:** {', '.join(metadata['authors'])}\n"
                    content += f"**arXiv ID:** {arxiv_id}\n"
                    content += f"**Categories:** {', '.join(metadata['categories'])}\n"
                    content += f"**Published:** {metadata['published']}\n\n"
                    content += f"## Abstract\n\n{metadata['summary']}"
                    
                    return {
                        'content': content,
                        'metadata': metadata,
                        'features_available': ['paper_metadata', 'arxiv_api', 'author_extraction'],
                        'processing_time': 'immediate'
                    }
                
            except ImportError:
                self.logger.warning("feedparser not available for arXiv processing")
            
            # Fallback to general webpage processing
            return await self.process_general_webpage(url, options)
            
        except Exception as e:
            self.logger.error(f"arXiv processing failed: {e}")
            return await self.process_general_webpage(url, options)

    async def process_github_url(self, url: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Process GitHub URLs with repository information."""
        try:
            self.logger.info(f"Processing GitHub URL: {url}")
            
            # Extract repository info from URL
            repo_info = self._extract_github_repo_info(url)
            if not repo_info:
                return await self.process_general_webpage(url, options)

            # Try to get repository information via GitHub API
            try:
                import requests
                
                owner, repo = repo_info['owner'], repo_info['repo']
                api_url = f"https://api.github.com/repos/{owner}/{repo}"
                
                response = requests.get(api_url, timeout=10)
                if response.status_code == 200:
                    repo_data = response.json()
                    
                    # Extract metadata
                    metadata = {
                        'name': repo_data.get('name', ''),
                        'full_name': repo_data.get('full_name', ''),
                        'description': repo_data.get('description', ''),
                        'owner': repo_data.get('owner', {}).get('login', ''),
                        'language': repo_data.get('language', ''),
                        'stars': repo_data.get('stargazers_count', 0),
                        'forks': repo_data.get('forks_count', 0),
                        'created_at': repo_data.get('created_at', ''),
                        'updated_at': repo_data.get('updated_at', ''),
                        'url': url,
                        'clone_url': repo_data.get('clone_url', ''),
                        'homepage': repo_data.get('homepage', ''),
                        'processing_method': 'github_api'
                    }
                    
                    # Create formatted content
                    content = f"# {metadata['full_name']}\n\n"
                    if metadata['description']:
                        content += f"**Description:** {metadata['description']}\n\n"
                    content += f"**Owner:** {metadata['owner']}\n"
                    content += f"**Language:** {metadata['language']}\n"
                    content += f"**Stars:** {metadata['stars']}\n"
                    content += f"**Forks:** {metadata['forks']}\n"
                    content += f"**Created:** {metadata['created_at']}\n"
                    content += f"**Updated:** {metadata['updated_at']}\n"
                    if metadata['homepage']:
                        content += f"**Homepage:** {metadata['homepage']}\n"
                    content += f"**Clone URL:** {metadata['clone_url']}\n"
                    
                    return {
                        'content': content,
                        'metadata': metadata,
                        'features_available': ['repository_metadata', 'github_api', 'code_stats'],
                        'processing_time': 'immediate'
                    }
                
            except ImportError:
                self.logger.warning("requests not available for GitHub processing")
            except Exception as api_error:
                self.logger.warning(f"GitHub API request failed: {api_error}")
            
            # Fallback to general webpage processing
            return await self.process_general_webpage(url, options)
            
        except Exception as e:
            self.logger.error(f"GitHub processing failed: {e}")
            return await self.process_general_webpage(url, options)

    async def process_general_webpage(self, url: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Process general webpages using crawl4ai."""
        try:
            self.logger.info(f"Processing general webpage: {url}")
            
            # Use crawl4ai for general webpage extraction
            try:
                from crawl4ai import AsyncWebCrawler
                
                async with AsyncWebCrawler() as crawler:
                    result = await crawler.arun(
                        url=url,
                        word_count_threshold=options.get('word_count_threshold', 10),
                        extraction_strategy=options.get('extraction_strategy'),
                        chunking_strategy=options.get('chunking_strategy'),
                        css_selector=options.get('css_selector'),
                        timeout=options.get('timeout', 30),
                        delay_before_return_html=options.get('wait_for_js', 2)
                    )
                    
                    if result.success:
                        metadata = {
                            'title': result.metadata.get('title', '') if result.metadata else '',
                            'description': result.metadata.get('description', '') if result.metadata else '',
                            'url': url,
                            'word_count': len(result.markdown.split()) if result.markdown else 0,
                            'processing_method': 'crawl4ai',
                            'success': True
                        }
                        
                        # Clean the markdown content
                        content = self._clean_markdown_content(result.markdown or "", metadata)
                        
                        return {
                            'content': content,
                            'metadata': metadata,
                            'features_available': ['web_extraction', 'markdown_conversion', 'content_cleaning'],
                            'processing_time': 'immediate'
                        }
                    else:
                        raise Exception(f"crawl4ai extraction failed: {result.error_message}")
                        
            except ImportError:
                self.logger.warning("crawl4ai not available")
                raise Exception("Web crawling library not available")
                
        except Exception as e:
            self.logger.error(f"General webpage processing failed: {e}")
            raise

    def _extract_youtube_video_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from various URL formats."""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:watch\?v=)([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _extract_arxiv_id(self, url: str) -> Optional[str]:
        """Extract arXiv ID from URL."""
        patterns = [
            r'arxiv\.org\/abs\/([0-9]{4}\.[0-9]{4,5})',
            r'arxiv\.org\/pdf\/([0-9]{4}\.[0-9]{4,5})\.pdf',
            r'arxiv\.org\/abs\/([a-z-]+\/[0-9]{7})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _extract_github_repo_info(self, url: str) -> Optional[Dict[str, str]]:
        """Extract GitHub repository owner and name from URL."""
        pattern = r'github\.com\/([^\/]+)\/([^\/]+)'
        match = re.search(pattern, url)
        
        if match:
            return {
                'owner': match.group(1),
                'repo': match.group(2).rstrip('.git')
            }
        return None

    async def _extract_subtitle_text(self, subtitle_list: list) -> str:
        """Extract text from YouTube subtitle data."""
        try:
            # Download subtitle file (usually VTT format)
            import requests
            
            # Find the best subtitle format (prefer VTT)
            subtitle_url = None
            for sub in subtitle_list:
                if sub.get('ext') == 'vtt':
                    subtitle_url = sub.get('url')
                    break
            
            if not subtitle_url and subtitle_list:
                # Fall back to first available subtitle
                subtitle_url = subtitle_list[0].get('url')
            
            if subtitle_url:
                response = requests.get(subtitle_url, timeout=10)
                response.raise_for_status()
                
                # Parse VTT content
                vtt_content = response.text
                transcript = self._parse_vtt_content(vtt_content)
                return transcript
                
        except Exception as e:
            self.logger.warning(f"Failed to extract subtitle text: {e}")
        
        return ""

    def _parse_vtt_content(self, vtt_content: str) -> str:
        """Parse VTT subtitle content to extract text."""
        try:
            lines = vtt_content.split('\n')
            transcript_lines = []
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Skip metadata and timing lines
                if '-->' in line or line.startswith('WEBVTT') or line.startswith('NOTE') or not line:
                    i += 1
                    continue
                
                # Check if this is a timestamp line
                if re.match(r'^\d+$', line):
                    i += 1
                    continue
                
                # This should be subtitle text
                if line and not line.startswith('<'):
                    # Clean HTML tags and formatting
                    clean_line = re.sub(r'<[^>]+>', '', line)
                    clean_line = re.sub(r'&[a-zA-Z]+;', '', clean_line)
                    if clean_line.strip():
                        transcript_lines.append(clean_line.strip())
                
                i += 1
            
            return ' '.join(transcript_lines)
            
        except Exception as e:
            self.logger.warning(f"Failed to parse VTT content: {e}")
            return ""

    def _clean_markdown_content(self, content: str, metadata: Dict[str, Any]) -> str:
        """Clean and format markdown content."""
        if not content:
            return ""
        
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        # Remove empty links
        content = re.sub(r'\[([^\]]*)\]\(\s*\)', r'\1', content)
        
        # Clean up image references that may be broken
        content = re.sub(r'!\[([^\]]*)\]\([^)]*\)', r'*[Image: \1]*', content)
        
        # Remove excessive bullet points
        content = re.sub(r'(\n\s*[-*+]\s*){3,}', '\n\n', content)
        
        return content.strip() 
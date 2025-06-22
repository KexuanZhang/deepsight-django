"""
Content indexing and search service for processed files.
"""

import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC

from .base_service import BaseService

class ContentIndexingService(BaseService):
    """Service for indexing and searching processed content."""
    
    def __init__(self):
        super().__init__("content_indexing")
        
        # Simple in-memory search index (can be enhanced with Elasticsearch later)
        self.search_index = {}
        self.file_index = {}
        
        # Load existing index
        self._load_search_index()
    
    def index_content(
        self, 
        file_id: str, 
        content: str, 
        metadata: Dict[str, Any],
        processing_stage: str = "immediate"
    ):
        """Index processed content for search."""
        try:
            # Create searchable content by cleaning and preprocessing
            searchable_content = self._preprocess_content(content)
            
            # Extract keywords and phrases
            keywords = self._extract_keywords(searchable_content)
            
            index_data = {
                "file_id": file_id,
                "content": content,
                "searchable_content": searchable_content,
                "keywords": keywords,
                "metadata": metadata,
                "processing_stage": processing_stage,
                "indexed_at": datetime.now(UTC).isoformat(),
                "content_length": len(content),
                "content_type": metadata.get("file_extension", "unknown"),
                "filename": metadata.get("original_filename", "unknown")
            }
            
            # Store in search index
            self.search_index[file_id] = index_data
            
            # Update file index for quick metadata lookups
            self.file_index[file_id] = {
                "filename": metadata.get("original_filename", "unknown"),
                "content_type": metadata.get("file_extension", "unknown"),
                "indexed_at": index_data["indexed_at"],
                "content_length": len(content),
                "processing_stage": processing_stage
            }
            
            # Persist index
            self._save_search_index()
            
            self.log_operation("index_content", f"file_id={file_id}, stage={processing_stage}, keywords={len(keywords)}")
            
        except Exception as e:
            self.log_operation("index_content_error", str(e), "error")
    
    async def search_content(
        self, 
        query: str, 
        file_types: Optional[List[str]] = None,
        limit: int = 10,
        min_score: float = 0.1
    ) -> List[Dict[str, Any]]:
        """Search indexed content."""
        try:
            if not query.strip():
                return []
            
            query_terms = self._preprocess_content(query).split()
            results = []
            
            for file_id, index_data in self.search_index.items():
                # Filter by file types if specified
                if file_types and index_data["content_type"] not in file_types:
                    continue
                
                # Calculate relevance score
                score = self._calculate_relevance_score(query_terms, index_data)
                
                if score >= min_score:
                    results.append({
                        "file_id": file_id,
                        "filename": index_data["filename"],
                        "content_type": index_data["content_type"],
                        "score": score,
                        "snippet": self._extract_snippet(query, index_data["content"]),
                        "metadata": index_data["metadata"],
                        "indexed_at": index_data["indexed_at"]
                    })
            
            # Sort by relevance score (descending)
            results.sort(key=lambda x: x["score"], reverse=True)
            
            # Apply limit
            results = results[:limit]
            
            self.log_operation("search_content", f"query='{query}', results={len(results)}")
            return results
            
        except Exception as e:
            self.log_operation("search_content_error", str(e), "error")
            return []
    
    async def get_content_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """Get content suggestions based on partial query."""
        try:
            suggestions = set()
            partial_lower = partial_query.lower().strip()
            
            if len(partial_lower) < 2:
                return []
            
            for file_id, index_data in self.search_index.items():
                keywords = index_data.get("keywords", [])
                
                for keyword in keywords:
                    if keyword.lower().startswith(partial_lower):
                        suggestions.add(keyword)
                
                # Also check content for phrase suggestions
                content_lower = index_data["searchable_content"].lower()
                if partial_lower in content_lower:
                    # Find words that start with the partial query
                    words = re.findall(r'\b' + re.escape(partial_lower) + r'\w*', content_lower)
                    suggestions.update(words[:5])  # Limit per file
            
            # Convert to sorted list and apply limit
            suggestion_list = sorted(list(suggestions))[:limit]
            
            self.log_operation("get_suggestions", f"query='{partial_query}', suggestions={len(suggestion_list)}")
            return suggestion_list
            
        except Exception as e:
            self.log_operation("get_suggestions_error", str(e), "error")
            return []
    
    async def remove_from_index(self, file_id: str):
        """Remove file from search index."""
        try:
            if file_id in self.search_index:
                del self.search_index[file_id]
            
            if file_id in self.file_index:
                del self.file_index[file_id]
            
            self._save_search_index()
            
            self.log_operation("remove_from_index", f"file_id={file_id}")
            
        except Exception as e:
            self.log_operation("remove_from_index_error", str(e), "error")
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get search index statistics."""
        try:
            total_files = len(self.search_index)
            total_content_length = sum(data["content_length"] for data in self.search_index.values())
            
            file_types = {}
            processing_stages = {}
            
            for data in self.search_index.values():
                content_type = data["content_type"]
                file_types[content_type] = file_types.get(content_type, 0) + 1
                
                stage = data["processing_stage"]
                processing_stages[stage] = processing_stages.get(stage, 0) + 1
            
            return {
                "total_files": total_files,
                "total_content_length": total_content_length,
                "file_types": file_types,
                "processing_stages": processing_stages,
                "index_size_mb": len(str(self.search_index)) / (1024 * 1024)
            }
            
        except Exception as e:
            self.log_operation("get_index_stats_error", str(e), "error")
            return {}
    
    def _preprocess_content(self, content: str) -> str:
        """Preprocess content for search indexing."""
        # Convert to lowercase
        content = content.lower()
        
        # Remove special characters but keep spaces and basic punctuation
        content = re.sub(r'[^\w\s\-\.]', ' ', content)
        
        # Normalize whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content."""
        # Simple keyword extraction (can be enhanced with NLP libraries)
        words = content.split()
        
        # Filter out very short words and common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him',
            'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their'
        }
        
        keywords = []
        for word in words:
            if len(word) > 2 and word not in stop_words:
                keywords.append(word)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for keyword in keywords:
            if keyword not in seen:
                seen.add(keyword)
                unique_keywords.append(keyword)
        
        # Return top keywords (limit to avoid huge lists)
        return unique_keywords[:100]
    
    def _calculate_relevance_score(self, query_terms: List[str], index_data: Dict[str, Any]) -> float:
        """Calculate relevance score for search query."""
        if not query_terms:
            return 0.0
        
        content = index_data["searchable_content"]
        keywords = index_data.get("keywords", [])
        filename = index_data["filename"].lower()
        
        score = 0.0
        total_terms = len(query_terms)
        
        for term in query_terms:
            term_score = 0.0
            
            # Exact matches in content (higher weight)
            exact_matches = content.count(term)
            term_score += exact_matches * 0.1
            
            # Keyword matches (medium weight)
            if term in keywords:
                term_score += 0.5
            
            # Filename matches (high weight)
            if term in filename:
                term_score += 1.0
            
            # Partial keyword matches (lower weight)
            for keyword in keywords:
                if term in keyword:
                    term_score += 0.2
                    break
            
            score += term_score
        
        # Normalize by number of query terms
        normalized_score = score / total_terms if total_terms > 0 else 0.0
        
        # Apply content length factor (shorter content with matches gets higher score)
        length_factor = 1.0 / (1.0 + index_data["content_length"] / 10000.0)
        
        return min(normalized_score * length_factor, 1.0)
    
    def _extract_snippet(self, query: str, content: str, snippet_length: int = 200) -> str:
        """Extract relevant snippet from content for search results."""
        query_lower = query.lower()
        content_lower = content.lower()
        
        # Find the first occurrence of any query term
        best_pos = -1
        for term in query_lower.split():
            pos = content_lower.find(term)
            if pos != -1 and (best_pos == -1 or pos < best_pos):
                best_pos = pos
        
        if best_pos == -1:
            # No query terms found, return beginning of content
            snippet = content[:snippet_length]
        else:
            # Extract snippet around the found term
            start = max(0, best_pos - snippet_length // 2)
            end = min(len(content), start + snippet_length)
            snippet = content[start:end]
            
            # Clean up snippet boundaries
            if start > 0:
                # Find the first complete word
                space_pos = snippet.find(' ')
                if space_pos != -1:
                    snippet = snippet[space_pos + 1:]
                snippet = "..." + snippet
            
            if end < len(content):
                # Find the last complete word
                space_pos = snippet.rfind(' ')
                if space_pos != -1:
                    snippet = snippet[:space_pos]
                snippet = snippet + "..."
        
        return snippet.strip()
    
    def _load_search_index(self):
        """Load search index from disk."""
        try:
            index_file = self.data_dir / "search_index.json"
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.search_index = data.get("search_index", {})
                    self.file_index = data.get("file_index", {})
                
                self.log_operation("load_index", f"loaded {len(self.search_index)} files")
        except Exception as e:
            self.log_operation("load_index_error", str(e), "error")
            self.search_index = {}
            self.file_index = {}
    
    def _save_search_index(self):
        """Save search index to disk."""
        try:
            index_file = self.data_dir / "search_index.json"
            data = {
                "search_index": self.search_index,
                "file_index": self.file_index,
                "last_updated": datetime.now(UTC).isoformat()
            }
            
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.log_operation("save_index_error", str(e), "error")


# Global singleton instance to prevent repeated initialization
content_indexing_service = ContentIndexingService() 
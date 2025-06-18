import logging
import threading
from typing import List, Dict, Set, Tuple, Optional
import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi
import torch
from ...interface import Information
from ...utils import ArticleTextProcessing
import torch.nn.functional as F
import dspy

from .storm_dataclass import StormInformationTable

def get_device():
    """Detect the best available device: 'cuda', 'mps', or 'cpu'. """
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        return "mps"
    return "cpu"

class ContextualizeSnippet(dspy.Signature):
    """
    Generate a brief contextual summary that explains where a specific snippet fits in the
    larger document and what surrounding context is necessary to understand it properly.
    """
    title = dspy.InputField(
        desc="Title of the document from which the snippet was extracted"
    )
    full_document = dspy.InputField(
        desc="The full document text or a representative portion of it"
    )
    snippet = dspy.InputField(
        desc="The specific snippet extracted from the document that needs contextualization"
    )
    context = dspy.OutputField(
        desc="A brief contextual summary (50-100 words) that explains where the snippet fits in the document and its surrounding context"
    )

class EnhancedStormInformationTable(StormInformationTable):
    """
    Enhanced version of StormInformationTable that implements the advanced RAG pipeline:
    1. Contextual chunk generation (adding explanatory text to each chunk)
    2. Dual-indexing: Vector embeddings and BM25 retrieval (on both original and contextualized content)
    3. Two-stage rank fusion:
       - First fuse BM25 results (original + contextualized)
       - Then fuse with vector search results
    4. Reranking with a cross-encoder
    """

    RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L6-v2"

    def __init__(self, conversations=None, url_to_info=None, reranker_threshold=0.5):
        """
        Initialize the enhanced information table.

        Args:
            conversations: Optional list of conversations to initialize from
            url_to_info: Optional dictionary mapping URLs to Information objects
            reranker_threshold: Minimum score threshold for reranker results (0 to 1)
        """
        if conversations:
            super().__init__(conversations)
        else:
            super().__init__([])
            if url_to_info:
                self.url_to_info = url_to_info

        # Initialize enhanced-specific attributes
        self.url_to_contextualized_info = {}
        
        # Additional storage for contextualized snippets
        self.collected_contextualized_snippets = []
        
        # Separate BM25 indices for original and contextualized content
        self.bm25_index_original = None
        self.bm25_index_contextualized = None
        self.bm25_tokenized_original = []
        self.bm25_tokenized_contextualized = []

        # Store reranker threshold
        self.reranker_threshold = reranker_threshold

        # Initialize reranker
        self.reranker = CrossEncoder(
            self.RERANKER_MODEL_NAME,
            device=self._device,
            activation_fn=torch.nn.Sigmoid(),
            trust_remote_code=True
        )

        # Debug info
        self.debug_info = {}

    def generate_contextualized_snippets(self, lm):
        """
        Generate context for each snippet and create contextualized versions.

        Args:
            lm: Language model to use for context generation
        """
        logging.info("Generating contextualized snippets...")
        self.url_to_contextualized_info = {}

        # Process each URL and its information
        for url, info in self.url_to_info.items():
            contextualized_info = self._generate_context_for_info(info, lm)
            self.url_to_contextualized_info[url] = contextualized_info

        logging.info(f"Generated contextualized snippets for {len(self.url_to_contextualized_info)} URLs")

    def _generate_context_for_info(self, info: Information, lm) -> Information:
        """
        Generate contextual information for a single Information object.

        Args:
            info: The original Information object
            lm: Language model for context generation

        Returns:
            Information object with contextualized snippets
        """
        # Create a new Information object to hold contextualized snippets
        contextualized_info = Information(
            url=info.url,
            description=info.description,
            snippets=[],  # Will be filled with contextualized snippets
            title=info.title,
            meta=info.meta.copy() if info.meta else {}
        )

        # Extract the full document text if available, or combine snippets
        full_document = info.meta.get("text", None)
        if not full_document:
            full_document = " ".join(info.snippets)

        # Generate context for each snippet
        for snippet in info.snippets:
            contextualized_snippet = self._generate_context_for_snippet(
                snippet=snippet,
                full_document=full_document,
                title=info.title,
                lm=lm
            )
            contextualized_info.snippets.append(contextualized_snippet)

        return contextualized_info

    def _generate_context_for_snippet(self, snippet: str, full_document: str, title: str, lm) -> str:
        """
        Generate contextual information for a single snippet using DSPy.
        Uses dspy.Predict within a dspy.settings.context for robustness.

        Args:
            snippet: The original snippet
            full_document: The full document text
            title: Document title
            lm: Language model instance conforming to dspy.dsp.LM interface

        Returns:
            Contextualized snippet (original snippet with context prepended, or a fallback)
        """
        try:
            # Use dspy.settings.context to configure the LM for the Predict call
            # Use the lock to ensure thread-safe prediction if LM client is not thread-safe
            with self._predict_lock:
                with dspy.settings.context(lm=lm):
                    contextualize_predictor = dspy.Predict(ContextualizeSnippet)
                    # Call the predictor - This is the standard DSPy way
                    response = contextualize_predictor(
                        title=title,
                        full_document=full_document,
                        snippet=snippet
                    )
                    context = response.context.strip()

            # Ensure context is not too long
            if len(context.split()) > 120:  # A bit of buffer over 100
                context = " ".join(context.split()[:100]) + "..."

            # Create contextualized snippet
            contextualized_snippet = f"Context: {context}\n\nSnippet: {snippet}"
            return contextualized_snippet

        except Exception as e:
            # Log the specific error and the LM type being used
            # Use str(e) to get the actual error message, avoiding attribute errors
            logging.error(f"Error generating context using {type(lm).__name__} for title '{title}': {str(e)}")
            # Fall back to original snippet with a standard prefix
            return f"Context: This is a snippet from a document titled '{title}'.\n\nSnippet: {snippet}"

    def prepare_table_for_retrieval(self):
        """
        Enhanced preparation that includes both vector encoding and dual BM25 indexing.
        """
        # First do the basic vector preparation from parent class
        super().prepare_table_for_retrieval()

        # Reset BM25 collections
        self.bm25_tokenized_original = []
        self.bm25_tokenized_contextualized = []
        
        # Ensure we have both original and contextualized snippets
        if not self.collected_snippets:
            logging.warning("No original snippets available for BM25 indexing")
            return

        # Map URLs to their contextualized snippets for easy lookup
        url_to_contextualized = {}
        for url, info in self.url_to_contextualized_info.items():
            if info.snippets:
                url_to_contextualized[url] = info.snippets[0]  # Take first snippet if multiple exist

        # Tokenize original snippets for BM25 and collect corresponding contextualized versions
        for idx, snippet in enumerate(self.collected_snippets):
            # Original content
            tokens_original = snippet.lower().split()
            self.bm25_tokenized_original.append(tokens_original)
            
            # Contextualized content
            url = self.collected_urls[idx]
            if url in url_to_contextualized:
                contextualized_snippet = url_to_contextualized[url]
                tokens_contextualized = contextualized_snippet.lower().split()
                self.bm25_tokenized_contextualized.append(tokens_contextualized)
            else:
                # If no contextualized version exists, use original to maintain index alignment
                self.bm25_tokenized_contextualized.append(tokens_original)
                logging.warning(f"No contextualized snippet found for URL {url}, using original content")

        # Build BM25 indices if we have valid snippets
        if self.bm25_tokenized_original and any(tokens for tokens in self.bm25_tokenized_original):
            try:
                self.bm25_index_original = BM25Okapi(self.bm25_tokenized_original)
                logging.info(f"Original content BM25 index built successfully with {len(self.bm25_tokenized_original)} documents")
            except Exception as e:
                logging.warning(f"Error creating original BM25 index: {e}. BM25 search will be disabled.")
                self.bm25_index_original = None

        if self.bm25_tokenized_contextualized and any(tokens for tokens in self.bm25_tokenized_contextualized):
            try:
                self.bm25_index_contextualized = BM25Okapi(self.bm25_tokenized_contextualized)
                logging.info(f"Contextualized content BM25 index built successfully with {len(self.bm25_tokenized_contextualized)} documents")
            except Exception as e:
                logging.warning(f"Error creating contextualized BM25 index: {e}. BM25 search will be disabled.")
                self.bm25_index_contextualized = None

    def retrieve_information(
        self,
        queries: List[str],
        initial_retrieval_k: int = 150,  # Default to retrieving top 150 chunks initially
        final_context_k: int = 20,  # Default to returning top 20 chunks after reranking
        bm25_weight: float = 0.5,
        vector_weight: float = 0.5,
        query_logger = None
    ) -> List[Information]:
        """
        Retrieve information using the enhanced retrieval pipeline:
        1. Initial retrieval: Get top-N chunks using hybrid search (vector + BM25)
        2. Rerank: Get top-K chunks using cross-encoder reranking

        Args:
            queries: List of search queries
            initial_retrieval_k: Number of chunks to retrieve in initial phase (default 150)
            final_context_k: Number of chunks to return after reranking (default 20)
            bm25_weight: Weight for BM25 scores in fusion (0.0 to 1.0)
            vector_weight: Weight for vector scores in fusion (0.0 to 1.0)
            query_logger: Optional QueryLogger to log retrieval process

        Returns:
            List of Information objects containing the top-K most relevant chunks
        """
        if not isinstance(queries, list):
            queries = [queries]

        all_results = []

        # Process each query separately
        for query in queries:
            # --- Logging Setup ---
            current_query_log_data = {
                "queries": [query],
                "retrieval_steps": {}
            }

            # Step 1: Initial retrieval using both vector and BM25
            vector_hits, vector_scores = self._vector_search(query, k=initial_retrieval_k)
            bm25_hits, bm25_scores = self._bm25_search(query, k=initial_retrieval_k)

            # Log initial retrieval results
            try:
                current_query_log_data["retrieval_steps"]["initial_vector"] = [
                    {"title": info.title, "url": info.url} for info in vector_hits
                ]
                current_query_log_data["retrieval_steps"]["initial_bm25"] = [
                    {"title": info.title, "url": info.url} for info in bm25_hits
                ]
            except Exception as e:
                logging.warning(f"Failed to format initial retrieval log data: {e}")

            # Step 2: Combine results using rank fusion
            fused_results = self._rank_fusion(
                query=query,
                vector_hits=vector_hits,
                vector_scores=vector_scores,
                bm25_hits=bm25_hits,
                bm25_scores=bm25_scores,
                vector_weight=vector_weight,
                bm25_weight=bm25_weight,
                k=initial_retrieval_k
            )

            # Log fusion results
            try:
                fusion_log_data = []
                for info, score in fused_results:
                    fusion_log_data.append({
                        "title": info.title,
                        "url": info.url,
                        "score": float(score)
                    })
                current_query_log_data["retrieval_steps"]["fusion"] = fusion_log_data
            except Exception as e:
                logging.warning(f"Failed to format fusion log data: {e}")

            query_results = []
            # Step 3: Rerank using cross-encoder
            if len(fused_results) > 0:
                reranked_results = self._cross_encoder_rerank(query, fused_results)

                # Log reranked results
                try:
                    rerank_log_data = []
                    for info, score in reranked_results[:final_context_k]:
                         rerank_log_data.append({
                            "title": info.title,
                            "url": info.url,
                            "score": float(score)
                         })
                    current_query_log_data["retrieval_steps"]["rerank"] = rerank_log_data
                except Exception as e:
                    logging.warning(f"Failed to format rerank log data: {e}")

                # Add final top-k results to query_results
                for info, _ in reranked_results[:final_context_k]:
                    query_results.append(info)

            # Write log entry
            if query_logger:
                try:
                    query_logger.log(current_query_log_data)
                except Exception as e:
                    logging.error(f"Failed to log query data for query '{query}': {e}")

            # Add results from this query to the overall results
            all_results.extend(query_results)

        # Deduplicate results based on URL
        seen_urls = set()
        final_results = []
        for info in all_results:
            if info.url not in seen_urls:
                seen_urls.add(info.url)
                final_results.append(info)

        return final_results

    def from_standard_table(self, standard_table):
        """
        Convert a standard StormInformationTable to an enhanced one.
        """
        self.url_to_info = standard_table.url_to_info.copy()
        return self

    def search(self, query, k=3, return_scores=False, vector_weight=0.5, bm25_weight=0.5):
        """
        Search for the most relevant snippets for a query.

        Args:
            query: The search query
            k: Number of results to return
            return_scores: Whether to return relevance scores along with snippets
            vector_weight: Weight for vector search results
            bm25_weight: Weight for BM25 search results

        Returns:
            List of snippets or (snippet, score) tuples if return_scores=True
        """
        if not self.collected_contextualized_snippets:
            logging.warning("No snippets available for search")
            return [] if not return_scores else []

        # Get results using both methods
        vector_hits, vector_scores = self._vector_search(query, k=k)
        bm25_hits, bm25_scores = self._bm25_search(query, k=k)

        # Combine results
        fused_results = self._rank_fusion(
            query=query,
            vector_hits=vector_hits,
            vector_scores=vector_scores,
            bm25_hits=bm25_hits,
            bm25_scores=bm25_scores,
            vector_weight=vector_weight,
            bm25_weight=bm25_weight,
            k=k
        )

        if return_scores:
            return fused_results
        else:
            return [item[0] for item in fused_results]

    def _vector_search(self, query, k=10):
        """
        Perform vector-based semantic search using the parent class's encoder.
        """
        if not self.collected_snippets:
            return [], []

        self._initialize_encoder()
        
        # Encode query
        encoded_query = self.encoder.encode(query, convert_to_tensor=True)
        encoded_query = encoded_query.to(self.encoded_snippets.device)

        # Calculate similarities
        vector_similarities = F.cosine_similarity(
            encoded_query.unsqueeze(0),
            self.encoded_snippets
        )

        # Get top-k results
        actual_k = min(k, len(vector_similarities))
        if actual_k <= 0:
            return [], []

        top_results = torch.topk(vector_similarities, k=actual_k)
        top_scores = top_results.values.cpu().tolist()
        top_indices = top_results.indices.cpu().tolist()

        # Convert to Information objects
        hits = []
        for idx in top_indices:
            url = self.collected_urls[idx]
            original_snippet = self.collected_snippets[idx]

            if url in self.url_to_info:
                original_info = self.url_to_info[url]
                info = Information(
                    url=url,
                    description=original_info.description,
                    snippets=[original_snippet],
                    title=original_info.title,
                    meta=original_info.meta.copy() if original_info.meta else {}
                )
                hits.append(info)

        return hits, top_scores

    def _bm25_search(self, query, k=10):
        """
        Perform BM25-based lexical search on both original and contextualized content.

        Args:
            query: The search query
            k: Number of results to return

        Returns:
            Tuple of (hits, scores) where hits is a list of Information objects
            and scores is a list of relevance scores
        """
        if not self.collected_snippets:
            logging.warning("No snippets available for BM25 search")
            return [], []

        if self.bm25_index_original is None or self.bm25_index_contextualized is None:
            logging.warning("BM25 indices not prepared. Call prepare_table_for_retrieval first.")
            return [], []

        # Tokenize the query for BM25
        tokenized_query = query.lower().split()

        # Get BM25 scores for both original and contextualized content
        original_scores = self.bm25_index_original.get_scores(tokenized_query)
        contextualized_scores = self.bm25_index_contextualized.get_scores(tokenized_query)

        # Normalize scores to [0, 1] range for each set
        max_original = max(original_scores) if len(original_scores) > 0 and max(original_scores) > 0 else 1.0
        max_contextualized = max(contextualized_scores) if len(contextualized_scores) > 0 and max(contextualized_scores) > 0 else 1.0
        
        original_scores_norm = [float(score / max_original) for score in original_scores]
        contextualized_scores_norm = [float(score / max_contextualized) for score in contextualized_scores]

        # Combine scores using weighted average
        combined_scores = []
        for orig_score, ctx_score in zip(original_scores_norm, contextualized_scores_norm):
            # Give slightly more weight to contextualized scores (0.6 vs 0.4)
            combined_score = (0.4 * orig_score + 0.6 * ctx_score)
            combined_scores.append(combined_score)

        # Get top-k indices based on combined scores
        top_indices = np.argsort(combined_scores)[-k:][::-1]
        
        # Convert to Information objects
        hits = []
        scores = []
        for idx in top_indices:
            url = self.collected_urls[idx]
            if url in self.url_to_info:
                original_info = self.url_to_info[url]
                info = Information(
                    url=url,
                    description=original_info.description,
                    snippets=[self.collected_snippets[idx]],
                    title=original_info.title,
                    meta=original_info.meta.copy() if original_info.meta else {}
                )
                hits.append(info)
                scores.append(float(combined_scores[idx]))

        return hits, scores

    def _rank_fusion(self, query, vector_hits, vector_scores, bm25_hits, bm25_scores,
                    vector_weight=0.5, bm25_weight=0.5, k=10):
        """
        Combine results from different retrieval methods using weighted score fusion.

        Args:
            query: The original query
            vector_hits: List of Information objects from vector search
            vector_scores: List of scores from vector search
            bm25_hits: List of Information objects from BM25 search
            bm25_scores: List of scores from BM25 search
            vector_weight: Weight for vector search scores
            bm25_weight: Weight for BM25 search scores
            k: Number of results to return

        Returns:
            List of (Information, score) tuples sorted by score
        """
        # Create URL-to-score mappings
        vector_url_to_score = {hit.url: score for hit, score in zip(vector_hits, vector_scores)}
        bm25_url_to_score = {hit.url: score for hit, score in zip(bm25_hits, bm25_scores)}

        # Create URL-to-hit mappings
        url_to_hit = {}
        for hit in vector_hits:
            url_to_hit[hit.url] = hit
        for hit in bm25_hits:
            if hit.url not in url_to_hit: # Prioritize hit from vector search if overlap
                 url_to_hit[hit.url] = hit

        # Combine all unique URLs
        all_urls = set(list(vector_url_to_score.keys()) + list(bm25_url_to_score.keys()))

        # Calculate combined scores
        combined_scores = []
        for url in all_urls:
            vector_score = vector_url_to_score.get(url, 0.0)
            bm25_score = bm25_url_to_score.get(url, 0.0)

            # Weighted fusion score
            fusion_score = (vector_weight * vector_score) + (bm25_weight * bm25_score)
            if url in url_to_hit: # Ensure we have a hit object for the URL
                combined_scores.append((url_to_hit[url], fusion_score))

        # Sort by score and return top-k
        combined_scores.sort(key=lambda x: x[1], reverse=True)
        return combined_scores[:k]

    def _cross_encoder_rerank(self, query, candidates, k=None):
        """
        Rerank candidate results using a cross-encoder model.

        Args:
            query: The search query
            candidates: List of (Information, score) tuples to rerank
            k: Number of results to return (if None, return all reranked)

        Returns:
            List of (Information, score) tuples sorted by reranker score
        """
        if not candidates:
            return []

        # Prepare input pairs for the reranker
        rerank_pairs = []
        valid_candidates_info = [] # Store the Information objects corresponding to rerank_pairs
        for info, _ in candidates:
            # Use the first snippet (or an empty string if no snippets)
            snippet = info.snippets[0] if info.snippets and isinstance(info.snippets, list) else ""
            if snippet: # Only process if snippet is not empty
                rerank_pairs.append((query, snippet))
                valid_candidates_info.append(info) # Keep track of the info object

        if not rerank_pairs:
             logging.warning("No valid candidates with non-empty snippets for reranking.")
             # Return original candidates sorted by fusion score
             candidates.sort(key=lambda x: x[1], reverse=True)
             return candidates[:k] if k is not None else candidates


        # Get reranker scores
        with self._predict_lock:
            rerank_scores = self.reranker.predict(rerank_pairs, show_progress_bar=False) # Disable progress bar

        # Combine with original information objects that were valid
        reranked_results = [(info, float(score)) for info, score in zip(valid_candidates_info, rerank_scores)]

        # Filter out results with scores lower than reranker_threshold
        reranked_results = [(info, score) for info, score in reranked_results if score >= self.reranker_threshold]

        # Sort by reranker score
        reranked_results.sort(key=lambda x: x[1], reverse=True)

        # Return top-k if specified
        if k is not None:
            return reranked_results[:k]
        return reranked_results
# STORM Enhanced RAG Pipeline

This document describes the Enhanced RAG Pipeline in STORM, which is now the default RAG system used throughout the application.

## Overview

The Enhanced RAG Pipeline improves retrieval quality through several advanced techniques:

1. **Contextual Chunk Generation**: Adding explanatory context to each chunk to help the retrieval system understand its relevance
2. **Dual-Index Retrieval**: Using both vector embeddings and BM25 retrieval for better coverage
3. **Rank Fusion**: Combining retrieval results from multiple methods
4. **Cross-Encoder Reranking**: Using a cross-encoder model to precisely rerank results

## Recent Updates

The codebase has been updated with the following improvements:

1. **Reranker Model Standardization**: Now consistently using the "jinaai/jina-reranker-v2-base-multilingual" model across all devices (CPU, CUDA, MPS)
2. **Parameter Consistency**: Retrieved and reranked results count now properly respect the CLI parameters passed through run_storm_wiki_*.py scripts
3. **Improved Query Logger**: Redesigned JSON structure that clearly links each query with all of its retrieval steps

## Architecture

The enhanced RAG pipeline follows these steps:

1. **Query Processing**: Receives a query or list of queries
2. **Retrieval**: 
   - Vector-based semantic search using SentenceTransformer encodings
   - BM25 lexical search for keyword matching
3. **Rank Fusion**: Combining results from both retrieval methods with weighted scores
4. **Reranking**: Using a cross-encoder model to precisely rerank the fused results
5. **Result Selection**: Returning the top-k most relevant results

## Query Logging

The enhanced QueryLogger now captures detailed information at each step of the retrieval process with an improved hierarchical structure:

```json
{
    "query_id": "query_1",
    "timestamp": "2023-07-01T12:34:56.789012",
    "queries": ["search query text"],
    "retrieval_steps": {
        "initial_vector": [{"title": "Document 1", "url": "https://example.com/doc1"},...],
        "initial_bm25": [{"title": "Document 2", "url": "https://example.com/doc2"},...],
        "fusion": [{"title": "Document 1", "url": "https://example.com/doc1", "score": 0.95},...],
        "rerank": [{"title": "Document 3", "url": "https://example.com/doc3", "score": 0.98},...],
        "final": [{"title": "Document 3", "url": "https://example.com/doc3"},...]
    }
}
```

Each query is logged as a complete unit in JSONL format, making it easy to analyze the retrieval pipeline's performance for specific queries. The logs are stored in the `rag_retrieve_log.jsonl` file in the output directory.

## Best Practices for Integration

When adding new modules or features that need to retrieve information:

1. Always use the `EnhancedStormInformationTable` class for retrieval
2. Pass the `query_logger` parameter to the `retrieve_information` method to enable logging
3. If using a standard `StormInformationTable`, convert it to an enhanced table using `EnhancedStormInformationTable().from_standard_table(standard_table)`
4. Use CLI-passed parameters for retrieval configuration instead of hardcoded values

## Implementation Details

The enhanced RAG pipeline is implemented in the following files:

- `knowledge_storm/storm_wiki/modules/enhanced_rag.py`: Core implementation
- `knowledge_storm/storm_wiki/modules/article_generation.py`: Integration with article generation
- `knowledge_storm/utils.py`: QueryLogger implementation

## Configuration Options

The EnhancedStormInformationTable class supports several parameters for tuning the retrieval process:

- `search_top_k`: Number of final results to return (default: 10)
- `bm25_weight`: Weight for BM25 results in fusion (default: 0.5)
- `vector_weight`: Weight for vector results in fusion (default: 0.5)
- `rerank_top_k`: Number of top results to consider for reranking (default: 20) 
- `fusion_top_k`: Number of initial candidates to collect before reranking (default: 50)

These parameters can be configured via command-line arguments in the run_storm_wiki_*.py scripts.

## Dependencies

The enhanced RAG pipeline requires additional dependencies:

- `rank_bm25`: For BM25 indexing and retrieval
- `sentence-transformers`: For both vector embeddings and the cross-encoder reranker

These are automatically added to the requirements.txt file.

## Performance Considerations

- The enhanced RAG pipeline requires more computational resources than the standard pipeline
- Context generation with an LLM adds API costs but significantly improves retrieval quality
- For lower-resource environments, the standard pipeline can still be used by omitting the `--use-enhanced-rag` flag 

## Query Rewriting

STORM now includes a QueryRewrite module that enhances RAG performance by automatically rewriting search queries before retrieval. This module helps to:

1. Expand queries with relevant terminology and context
2. Reframe queries to improve information retrieval
3. Ensure consistent query structure for the retrieval system

The QueryRewrite module uses the article's language model to transform each query in the section_query list while maintaining the same format and structure.

### Example

Here's how query rewriting works in practice:

```python
# Original queries
section_query = ["Machine Learning", "Neural Networks", "Supervised Learning"]

# After rewriting
rewritten_queries = ["Machine Learning algorithms and techniques", 
                    "Neural Networks architecture and applications", 
                    "Supervised Learning methods and evaluation metrics"]
```

### How It Works

1. The QueryRewrite module is initialized in the StormArticleGenerationModule constructor
2. During the generate_section method, original queries are logged then passed to the rewrite module
3. Rewritten queries are logged and used for information retrieval
4. The number and structure of queries is preserved to maintain compatibility

You can observe the original and rewritten queries in the logs to evaluate the effectiveness of query rewriting. 
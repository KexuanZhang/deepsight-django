"""
Content type detection module for podcast generation.

This module handles automatic detection of content types to optimize
podcast generation strategies.
"""

import logging
from typing import Dict, List
from ..interfaces.content_detector_interface import ContentDetectorInterface

logger = logging.getLogger(__name__)


class ContentTypeDetector(ContentDetectorInterface):
    """Detects content type to optimize podcast generation strategy"""

    def __init__(self):
        self.detection_patterns = {
            "academic_paper": [
                "abstract",
                "introduction",
                "methodology",
                "results",
                "conclusion",
                "references",
                "doi:",
                "arxiv",
                "journal",
                "conference",
                "peer review",
                "hypothesis",
                "experimental",
                "statistical analysis",
            ],
            "financial_report": [
                "revenue",
                "profit",
                "earnings",
                "financial",
                "quarterly",
                "annual report",
                "balance sheet",
                "cash flow",
                "ebitda",
                "shareholder",
                "fiscal year",
                "投资",
                "财报",
                "季度",
                "年报",
                "营收",
                "利润",
                "股东",
            ],
            "news_report": [
                "breaking news",
                "reporter",
                "according to",
                "sources said",
                "latest update",
                "新闻",
                "报道",
                "记者",
                "消息",
                "最新",
                "突发",
                "据悉",
            ],
            "press_conference": [
                "press conference",
                "announcement",
                "ceo said",
                "executive",
                "q&a",
                "发布会",
                "新闻发布",
                "记者会",
                "首席执行官",
                "总裁",
                "问答",
            ],
            "lecture_recording": [
                "professor",
                "lecture",
                "university",
                "students",
                "lesson",
                "course",
                "教授",
                "讲座",
                "大学",
                "课程",
                "学生",
                "授课",
                "讲课",
            ],
            "product_launch": [
                "product launch",
                "new product",
                "features",
                "specifications",
                "price",
                "产品发布",
                "新品",
                "功能",
                "特性",
                "价格",
                "上市",
            ],
            "technical_documentation": [
                "api",
                "documentation",
                "technical spec",
                "implementation",
                "architecture",
                "技术文档",
                "接口",
                "架构",
                "实现",
                "规范",
            ],
            "review_article": [
                "review",
                "survey",
                "comprehensive",
                "state of the art",
                "overview",
                "综述",
                "回顾",
                "概述",
                "现状",
                "总结",
            ],
        }

    def detect_content_type(self, content: str, file_metadata: Dict) -> str:
        """Detect the type of content to adjust podcast generation strategy"""
        content_lower = content.lower()

        # Check file metadata for hints
        title = file_metadata.get("title", "").lower()
        filename = file_metadata.get("filename", "").lower()

        # Score each content type
        type_scores = {}
        for content_type, keywords in self.detection_patterns.items():
            score = 0
            for keyword in keywords:
                score += content_lower.count(keyword)
                score += title.count(keyword) * 2  # Title keywords are weighted more
                score += filename.count(keyword) * 1.5
            type_scores[content_type] = score

        # Return the type with highest score, default to academic_paper
        detected_type = max(type_scores, key=type_scores.get)
        if type_scores[detected_type] == 0:
            detected_type = "academic_paper"  # Default fallback

        logger.info(f"Detected content type: {detected_type} (scores: {type_scores})")
        return detected_type

    def add_content_type(self, content_type: str, keywords: List[str]):
        """Add a new content type with its detection keywords"""
        self.detection_patterns[content_type] = keywords
        logger.info(f"Added new content type: {content_type}")

    def get_supported_types(self) -> List[str]:
        """Get list of supported content types"""
        return list(self.detection_patterns.keys())


# Global singleton instance
content_detector = ContentTypeDetector()

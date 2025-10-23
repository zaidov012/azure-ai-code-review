"""Parser for LLM responses into ReviewComment objects."""

import json
import re
from typing import List, Optional
import logging

from ..azure_devops.models import ReviewComment
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class ResponseParser:
    """Parser for converting LLM responses to ReviewComment objects."""
    
    @staticmethod
    def extract_json(text: str) -> Optional[str]:
        """
        Extract JSON content from markdown code blocks or raw text.
        
        Args:
            text: Text potentially containing JSON
        
        Returns:
            Extracted JSON string or None
        """
        # Try to find JSON in markdown code block
        json_block_pattern = r'```(?:json)?\s*(\[.*?\])\s*```'
        matches = re.findall(json_block_pattern, text, re.DOTALL)
        
        if matches:
            return matches[0]
        
        # Try to find raw JSON array
        array_pattern = r'\[\s*\{.*?\}\s*\]'
        matches = re.findall(array_pattern, text, re.DOTALL)
        
        if matches:
            # Return the longest match (most likely the complete array)
            return max(matches, key=len)
        
        # Check if the entire text is JSON
        text = text.strip()
        if text.startswith('[') and text.endswith(']'):
            return text
        
        return None
    
    @staticmethod
    def parse_review_response(
        response_text: str,
        file_path: str
    ) -> List[ReviewComment]:
        """
        Parse LLM response into ReviewComment objects.
        
        Args:
            response_text: Raw LLM response text
            file_path: Path to the reviewed file
        
        Returns:
            List of ReviewComment objects
        """
        comments = []
        
        # Extract JSON from response
        json_str = ResponseParser.extract_json(response_text)
        
        if not json_str:
            logger.warning(f"No JSON found in response for {file_path}")
            logger.debug(f"Response text: {response_text[:500]}")
            return comments
        
        try:
            # Parse JSON
            data = json.loads(json_str)
            
            if not isinstance(data, list):
                logger.warning(f"Expected JSON array, got {type(data)}")
                return comments
            
            # Convert each item to ReviewComment
            for item in data:
                if not isinstance(item, dict):
                    logger.warning(f"Expected dict in array, got {type(item)}")
                    continue
                
                try:
                    comment = ResponseParser.parse_comment_dict(item, file_path)
                    if comment:
                        comments.append(comment)
                except Exception as e:
                    logger.warning(f"Error parsing comment: {e}")
                    continue
            
            logger.info(f"Parsed {len(comments)} review comments from response")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.debug(f"JSON string: {json_str}")
        
        return comments
    
    @staticmethod
    def parse_comment_dict(data: dict, file_path: str) -> Optional[ReviewComment]:
        """
        Parse a single comment dictionary into ReviewComment.
        
        Args:
            data: Dictionary with comment data
            file_path: Path to the file
        
        Returns:
            ReviewComment object or None if invalid
        """
        # Required fields
        line_number = data.get("line_number") or data.get("line")
        content = data.get("content") or data.get("description") or data.get("message")
        
        if line_number is None or not content:
            logger.warning(f"Missing required fields in comment: {data}")
            return None
        
        # Convert line_number to int
        try:
            line_number = int(line_number)
        except (ValueError, TypeError):
            logger.warning(f"Invalid line_number: {line_number}")
            return None
        
        # Optional fields with defaults
        severity = data.get("severity", "suggestion").lower()
        category = data.get("category", "code_quality").lower()
        
        # Validate severity
        valid_severities = {"critical", "major", "minor", "suggestion"}
        if severity not in valid_severities:
            logger.warning(f"Unknown severity '{severity}', defaulting to 'suggestion'")
            severity = "suggestion"
        
        # Validate category
        valid_categories = {
            "security", "performance", "code_quality",
            "best_practices", "bugs", "documentation", "general"
        }
        if category not in valid_categories:
            logger.warning(f"Unknown category '{category}', defaulting to 'code_quality'")
            category = "code_quality"
        
        return ReviewComment(
            file_path=file_path,
            line_number=line_number,
            content=content,
            severity=severity,
            category=category
        )
    
    @staticmethod
    def parse_summary_response(response_text: str) -> str:
        """
        Parse summary response, extracting clean text.
        
        Args:
            response_text: Raw LLM response
        
        Returns:
            Cleaned summary text
        """
        # Remove markdown code blocks if present
        summary = re.sub(r'```.*?```', '', response_text, flags=re.DOTALL)
        
        # Clean up extra whitespace
        summary = re.sub(r'\n{3,}', '\n\n', summary)
        summary = summary.strip()
        
        return summary
    
    @staticmethod
    def validate_comments(comments: List[ReviewComment]) -> List[ReviewComment]:
        """
        Validate and filter comments.
        
        Args:
            comments: List of review comments
        
        Returns:
            List of valid comments
        """
        valid_comments = []
        
        for comment in comments:
            # Check line number is positive
            if comment.line_number <= 0:
                logger.warning(f"Invalid line number {comment.line_number}, skipping")
                continue
            
            # Check content is not empty
            if not comment.content or not comment.content.strip():
                logger.warning("Empty comment content, skipping")
                continue
            
            # Check content is not too long (Azure DevOps limit is ~4000 chars)
            if len(comment.content) > 3500:
                logger.warning(f"Comment too long ({len(comment.content)} chars), truncating")
                comment.content = comment.content[:3500] + "\n\n[Content truncated...]"
            
            valid_comments.append(comment)
        
        if len(valid_comments) < len(comments):
            logger.info(
                f"Filtered {len(comments) - len(valid_comments)} invalid comments. "
                f"{len(valid_comments)} valid comments remaining."
            )
        
        return valid_comments

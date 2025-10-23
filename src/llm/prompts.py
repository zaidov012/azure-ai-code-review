"""Prompt templates for code review."""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    """Template for generating prompts."""
    name: str
    system_message: str
    user_template: str
    description: str = ""


class CodeReviewPrompts:
    """Collection of prompts for code review tasks."""
    
    # System message for code review
    SYSTEM_MESSAGE = """You are an expert code reviewer with deep knowledge of software engineering best practices, security, performance optimization, and code quality.

Your task is to review code changes and provide constructive, actionable feedback. Focus on:
- Security vulnerabilities
- Performance issues
- Code quality and maintainability
- Best practices violations
- Potential bugs
- Documentation

Be constructive and helpful. Provide specific suggestions for improvement."""
    
    # File review template
    FILE_REVIEW_TEMPLATE = """Review the following code changes from a pull request.

**Pull Request Context:**
Title: {pr_title}
Description: {pr_description}

**File:** {file_path}
**Language:** {language}
**Change Type:** {change_type}

**Code Content:**
```{language}
{file_content}
```

{diff_section}

**Review Scope:** {review_scope}

Please review this code and identify issues. For each issue found, provide:
1. **Line Number**: The specific line number where the issue occurs
2. **Severity**: One of: critical, major, minor, suggestion
3. **Category**: One of: security, performance, code_quality, best_practices, bugs, documentation
4. **Description**: Clear explanation of the issue and how to fix it

Format your response as a JSON array of review comments:
```json
[
  {{
    "line_number": 42,
    "severity": "major",
    "category": "security",
    "content": "Potential SQL injection vulnerability. Use parameterized queries instead."
  }},
  {{
    "line_number": 15,
    "severity": "minor",
    "category": "code_quality",
    "content": "Consider extracting this logic into a separate function for better readability."
  }}
]
```

If no issues are found, return an empty array: []

Focus on providing actionable, specific feedback that helps improve the code."""
    
    # Summary review template
    SUMMARY_TEMPLATE = """Based on the following review results, create a concise summary.

**Pull Request:** {pr_title}

**Review Results:**
- Total files reviewed: {total_files}
- Issues found: {total_issues}
  - Critical: {critical_count}
  - Major: {major_count}
  - Minor: {minor_count}
  - Suggestions: {suggestion_count}

**Categories:**
{category_breakdown}

Please create a brief summary (3-5 sentences) highlighting:
1. Overall code quality assessment
2. Most important issues to address
3. Any positive aspects worth mentioning
4. General recommendations

Keep it constructive and helpful."""
    
    # Quick review template (for large files)
    QUICK_REVIEW_TEMPLATE = """Perform a quick security and critical bug scan of this code.

**File:** {file_path}
**Language:** {language}

**Code:**
```{language}
{file_content}
```

Focus ONLY on:
- Critical security vulnerabilities (SQL injection, XSS, authentication issues, etc.)
- Critical bugs that could cause crashes or data loss
- Critical performance issues

Return only critical and major issues in JSON format:
```json
[
  {{
    "line_number": 42,
    "severity": "critical",
    "category": "security",
    "content": "Description and fix"
  }}
]
```

If no critical issues found, return: []"""
    
    @classmethod
    def build_file_review_prompt(
        cls,
        file_path: str,
        file_content: str,
        language: str,
        change_type: str = "edit",
        pr_title: str = "",
        pr_description: str = "",
        diff_content: Optional[str] = None,
        review_scope: Optional[List[str]] = None
    ) -> str:
        """
        Build a file review prompt.
        
        Args:
            file_path: Path to the file
            file_content: Content of the file
            language: Programming language
            change_type: Type of change (add, edit, delete)
            pr_title: Pull request title
            pr_description: Pull request description
            diff_content: Diff content (optional)
            review_scope: List of review aspects to focus on
        
        Returns:
            Formatted prompt string
        """
        # Format diff section if available
        diff_section = ""
        if diff_content:
            diff_section = f"""
**Diff:**
```diff
{diff_content}
```
"""
        
        # Format review scope
        scope_str = ", ".join(review_scope) if review_scope else "all aspects"
        
        return cls.FILE_REVIEW_TEMPLATE.format(
            pr_title=pr_title or "N/A",
            pr_description=pr_description or "N/A",
            file_path=file_path,
            language=language or "unknown",
            change_type=change_type,
            file_content=file_content,
            diff_section=diff_section,
            review_scope=scope_str
        )
    
    @classmethod
    def build_quick_review_prompt(
        cls,
        file_path: str,
        file_content: str,
        language: str
    ) -> str:
        """
        Build a quick review prompt for critical issues only.
        
        Args:
            file_path: Path to the file
            file_content: Content of the file
            language: Programming language
        
        Returns:
            Formatted prompt string
        """
        return cls.QUICK_REVIEW_TEMPLATE.format(
            file_path=file_path,
            file_content=file_content,
            language=language or "unknown"
        )
    
    @classmethod
    def build_summary_prompt(
        cls,
        pr_title: str,
        review_stats: Dict[str, Any]
    ) -> str:
        """
        Build a summary prompt.
        
        Args:
            pr_title: Pull request title
            review_stats: Dictionary with review statistics
        
        Returns:
            Formatted prompt string
        """
        # Build category breakdown
        categories = review_stats.get("by_category", {})
        category_breakdown = "\n".join(
            f"  - {cat}: {count}" for cat, count in categories.items()
        )
        
        return cls.SUMMARY_TEMPLATE.format(
            pr_title=pr_title,
            total_files=review_stats.get("total_files", 0),
            total_issues=review_stats.get("total_issues", 0),
            critical_count=review_stats.get("by_severity", {}).get("critical", 0),
            major_count=review_stats.get("by_severity", {}).get("major", 0),
            minor_count=review_stats.get("by_severity", {}).get("minor", 0),
            suggestion_count=review_stats.get("by_severity", {}).get("suggestion", 0),
            category_breakdown=category_breakdown or "  - None"
        )
    
    @classmethod
    def get_system_message(cls, review_mode: str = "default") -> str:
        """
        Get system message based on review mode.
        
        Args:
            review_mode: Review mode (default, quick, thorough)
        
        Returns:
            System message string
        """
        if review_mode == "quick":
            return cls.SYSTEM_MESSAGE + "\n\nFocus on critical security and bug issues only."
        elif review_mode == "thorough":
            return cls.SYSTEM_MESSAGE + "\n\nProvide detailed, comprehensive feedback on all aspects."
        else:
            return cls.SYSTEM_MESSAGE


def detect_language(file_path: str) -> str:
    """
    Detect programming language from file extension.
    
    Args:
        file_path: Path to the file
    
    Returns:
        Language name
    """
    extension_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".java": "java",
        ".cs": "csharp",
        ".go": "go",
        ".rb": "ruby",
        ".php": "php",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
        ".rs": "rust",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".sql": "sql",
        ".sh": "bash",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".json": "json",
        ".xml": "xml",
        ".html": "html",
        ".css": "css",
        ".md": "markdown",
    }
    
    for ext, lang in extension_map.items():
        if file_path.endswith(ext):
            return lang
    
    return "unknown"

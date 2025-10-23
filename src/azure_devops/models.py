"""Data models for Azure DevOps API responses."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class CommentThreadStatus(Enum):
    """Status of a comment thread."""
    ACTIVE = "active"
    FIXED = "fixed"
    WONT_FIX = "wontFix"
    CLOSED = "closed"
    BY_DESIGN = "byDesign"
    PENDING = "pending"
    UNKNOWN = "unknown"


class PullRequestStatus(Enum):
    """Status of a pull request."""
    ACTIVE = "active"
    ABANDONED = "abandoned"
    COMPLETED = "completed"
    NOT_SET = "notSet"


class FileDiffOperation(Enum):
    """Type of file operation in diff."""
    ADD = "add"
    DELETE = "delete"
    EDIT = "edit"
    RENAME = "rename"
    ENCODING = "encoding"


@dataclass
class User:
    """Azure DevOps user."""
    id: str
    display_name: str
    unique_name: str
    email: Optional[str] = None
    image_url: Optional[str] = None
    
    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "User":
        """Create User from API response."""
        return cls(
            id=data.get("id", ""),
            display_name=data.get("displayName", ""),
            unique_name=data.get("uniqueName", ""),
            email=data.get("emailAddress"),
            image_url=data.get("imageUrl"),
        )


@dataclass
class GitRepository:
    """Git repository information."""
    id: str
    name: str
    url: str
    project_id: str
    default_branch: Optional[str] = None
    
    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "GitRepository":
        """Create GitRepository from API response."""
        project = data.get("project", {})
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            url=data.get("url", ""),
            project_id=project.get("id", ""),
            default_branch=data.get("defaultBranch"),
        )


@dataclass
class FileDiff:
    """Represents a file change in a pull request."""
    path: str
    change_type: FileDiffOperation
    original_path: Optional[str] = None
    diff_content: Optional[str] = None
    additions: int = 0
    deletions: int = 0
    
    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "FileDiff":
        """Create FileDiff from API response."""
        item = data.get("item", {})
        change_type_str = data.get("changeType", "edit")
        
        # Map Azure DevOps change types to our enum
        change_type_map = {
            "add": FileDiffOperation.ADD,
            "edit": FileDiffOperation.EDIT,
            "delete": FileDiffOperation.DELETE,
            "rename": FileDiffOperation.RENAME,
            "encoding": FileDiffOperation.ENCODING,
        }
        
        # Handle combined change types (e.g., "edit, rename")
        if "," in change_type_str:
            change_type_str = change_type_str.split(",")[0].strip()
        
        change_type = change_type_map.get(
            change_type_str.lower(), 
            FileDiffOperation.EDIT
        )
        
        return cls(
            path=item.get("path", ""),
            change_type=change_type,
            original_path=data.get("sourceServerItem"),
        )
    
    @property
    def is_binary(self) -> bool:
        """Check if file is likely binary based on extension."""
        binary_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico',
            '.pdf', '.zip', '.tar', '.gz', '.exe', '.dll',
            '.so', '.dylib', '.class', '.jar', '.war',
        }
        return any(self.path.lower().endswith(ext) for ext in binary_extensions)
    
    @property
    def total_changes(self) -> int:
        """Total number of changes (additions + deletions)."""
        return self.additions + self.deletions


@dataclass
class CommentThread:
    """Represents a comment thread on a PR."""
    id: int
    status: CommentThreadStatus
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    comments: List["Comment"] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "CommentThread":
        """Create CommentThread from API response."""
        thread_context = data.get("threadContext", {})
        
        # Extract file path and line number
        file_path = None
        line_number = None
        
        if thread_context:
            file_path = thread_context.get("filePath")
            right_file_start = thread_context.get("rightFileStart")
            if right_file_start:
                line_number = right_file_start.get("line")
        
        status_str = data.get("status", "unknown")
        status = CommentThreadStatus.UNKNOWN
        try:
            status = CommentThreadStatus(status_str.lower())
        except ValueError:
            pass
        
        # Parse comments
        comments = []
        for comment_data in data.get("comments", []):
            comments.append(Comment.from_api(comment_data))
        
        return cls(
            id=data.get("id", 0),
            status=status,
            file_path=file_path,
            line_number=line_number,
            comments=comments,
            properties=data.get("properties", {}),
        )


@dataclass
class Comment:
    """Represents a single comment in a thread."""
    id: int
    content: str
    author: User
    published_date: Optional[datetime] = None
    last_updated_date: Optional[datetime] = None
    comment_type: str = "text"
    
    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "Comment":
        """Create Comment from API response."""
        author_data = data.get("author", {})
        author = User.from_api(author_data)
        
        # Parse dates
        published_date = None
        last_updated_date = None
        
        if data.get("publishedDate"):
            try:
                published_date = datetime.fromisoformat(
                    data["publishedDate"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass
        
        if data.get("lastUpdatedDate"):
            try:
                last_updated_date = datetime.fromisoformat(
                    data["lastUpdatedDate"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass
        
        return cls(
            id=data.get("id", 0),
            content=data.get("content", ""),
            author=author,
            published_date=published_date,
            last_updated_date=last_updated_date,
            comment_type=data.get("commentType", "text"),
        )


@dataclass
class PullRequest:
    """Represents a pull request."""
    pull_request_id: int
    title: str
    description: str
    source_branch: str
    target_branch: str
    status: PullRequestStatus
    created_by: User
    repository: GitRepository
    creation_date: Optional[datetime] = None
    closed_date: Optional[datetime] = None
    url: Optional[str] = None
    reviewers: List[User] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    
    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "PullRequest":
        """Create PullRequest from API response."""
        created_by = User.from_api(data.get("createdBy", {}))
        repository = GitRepository.from_api(data.get("repository", {}))
        
        # Parse status
        status_str = data.get("status", "notSet")
        status = PullRequestStatus.NOT_SET
        try:
            status = PullRequestStatus(status_str.lower())
        except ValueError:
            pass
        
        # Parse reviewers
        reviewers = []
        for reviewer_data in data.get("reviewers", []):
            reviewers.append(User.from_api(reviewer_data))
        
        # Parse dates
        creation_date = None
        closed_date = None
        
        if data.get("creationDate"):
            try:
                creation_date = datetime.fromisoformat(
                    data["creationDate"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass
        
        if data.get("closedDate"):
            try:
                closed_date = datetime.fromisoformat(
                    data["closedDate"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass
        
        # Extract labels
        labels = []
        label_data = data.get("labels", [])
        if isinstance(label_data, list):
            labels = [label.get("name", "") for label in label_data if isinstance(label, dict)]
        
        return cls(
            pull_request_id=data.get("pullRequestId", 0),
            title=data.get("title", ""),
            description=data.get("description", ""),
            source_branch=data.get("sourceRefName", ""),
            target_branch=data.get("targetRefName", ""),
            status=status,
            created_by=created_by,
            repository=repository,
            creation_date=creation_date,
            closed_date=closed_date,
            url=data.get("url"),
            reviewers=reviewers,
            labels=labels,
        )
    
    @property
    def is_active(self) -> bool:
        """Check if PR is still active."""
        return self.status == PullRequestStatus.ACTIVE
    
    @property
    def is_completed(self) -> bool:
        """Check if PR is completed/merged."""
        return self.status == PullRequestStatus.COMPLETED


@dataclass
class ReviewComment:
    """Structured review comment to be posted to PR."""
    file_path: str
    line_number: int
    content: str
    severity: str = "suggestion"  # critical, major, minor, suggestion
    category: str = "general"  # code_quality, security, performance, best_practices, bugs
    
    def to_thread_context(self) -> Dict[str, Any]:
        """Convert to Azure DevOps thread context format."""
        return {
            "filePath": self.file_path,
            "rightFileStart": {
                "line": self.line_number,
                "offset": 1
            },
            "rightFileEnd": {
                "line": self.line_number,
                "offset": 1
            }
        }
    
    def format_content(self, style: str = "constructive") -> str:
        """Format comment content based on style."""
        severity_emoji = {
            "critical": "🔴",
            "major": "🟡",
            "minor": "🔵",
            "suggestion": "💡",
        }
        
        category_label = {
            "security": "Security",
            "performance": "Performance",
            "code_quality": "Code Quality",
            "best_practices": "Best Practice",
            "bugs": "Bug",
            "general": "Review",
        }
        
        emoji = severity_emoji.get(self.severity.lower(), "💬")
        label = category_label.get(self.category.lower(), "Review")
        
        if style == "concise":
            return f"{emoji} **{label}**: {self.content}"
        elif style == "detailed":
            return (
                f"{emoji} **{label}** ({self.severity.title()})\n\n"
                f"{self.content}\n\n"
                f"---\n"
                f"*AI-generated review comment*"
            )
        else:  # constructive
            return (
                f"{emoji} **{label}**\n\n"
                f"{self.content}\n\n"
                f"*Severity: {self.severity.title()}*"
            )

# Repository Management Packages

Two complementary packages for repository operations:

## Provider Package
A unified interface for repository cloning with support for Nexus.

## Versioner Package  
A unified interface for full git operations with support for GitHub and Bitbucket.

## Features

### Provider Package
- **Clone Interface**: Simple interface with only `clone` method
- **Nexus Support**: Clone operations using git commands
- **Modern Python**: Uses Python 3.11+ features with proper typing and async/await

### Versioner Package
- **Full Git Interface**: Complete interface with `clone`, `add`, `pull`, `commit`, `push`
- **GitHub Support**: Full git operations using pygit2 with token authentication
- **Bitbucket Support**: Full git operations using pygit2 with username/password authentication
- **Modern Python**: Uses Python 3.11+ features with proper typing and async/await

## Installation

```bash
uv add pygit2
```

## Usage

### Provider Package (Clone Only)

```python
from provider import create_provider

# Create Nexus Provider using factory function
nexus = create_provider("nexus", base_url="https://nexus.example.com")
await nexus.clone("https://nexus.example.com/repo.git", "/tmp/repo")
```

### Versioner Package (Full Git Operations)

```python
from versioner import create_versioner

# GitHub Versioner (full git operations)
github = create_versioner("github", token="your_github_token")
await github.clone("https://github.com/user/repo.git", "/tmp/repo")
await github.add("/tmp/repo", ["file.txt"])
await github.pull("/tmp/repo", "main")
await github.commit("/tmp/repo", "Add new file")
await github.push("/tmp/repo", "main")

# Bitbucket Versioner (full git operations)
bitbucket = create_versioner("bitbucket", username="username", app_password="app_password")
await bitbucket.clone("https://bitbucket.org/user/repo.git", "/tmp/repo")
await bitbucket.add("/tmp/repo", ["file.txt"])
await bitbucket.pull("/tmp/repo", "main")
await bitbucket.commit("/tmp/repo", "Add new file")
await bitbucket.push("/tmp/repo", "main")
```

### Provider Interface

All providers implement the following interface:

```python
class ProviderBase(ABC):
    @abstractmethod
    async def clone(self, repository_url: str, target_path: str | Path) -> None:
        """Clone a repository to the specified path."""
        pass
```

### Versioner Interface

All versioners implement the following interface:

```python
class VersionerBase(ABC):
    @abstractmethod
    async def clone(self, repository_url: str, target_path: str | Path) -> None:
        """Clone a repository to the specified path."""
        pass
    
    @abstractmethod
    async def add(self, repository_path: str | Path, files: list[str] | None = None) -> None:
        """Add files to the staging area."""
        pass
    
    @abstractmethod
    async def pull(self, repository_path: str | Path, branch: str = "main") -> None:
        """Pull latest changes from the remote repository."""
        pass
    
    @abstractmethod
    async def commit(self, repository_path: str | Path, message: str) -> None:
        """Commit staged changes."""
        pass
    
    @abstractmethod
    async def push(self, repository_path: str | Path, branch: str = "main") -> None:
        """Push commits to the remote repository."""
        pass
```

## Architecture

### Provider Package

#### ProviderBase
Abstract base class defining the common interface for all providers (clone only).

#### NexusProvider
- **Operations**: Clone only
- **Implementation**: Uses git commands via subprocess
- **Authentication**: None (public repositories)

### Versioner Package

#### VersionerBase
Abstract base class defining the common interface for all versioners (full git operations).

#### GitMixin
Mixin class providing shared pygit2 functionality for GitHub and Bitbucket versioners.

#### GithubVersioner
- **Operations**: Full git operations (clone, add, pull, commit, push)
- **Implementation**: Uses pygit2
- **Authentication**: GitHub personal access token

#### BitbucketVersioner
- **Operations**: Full git operations (clone, add, pull, commit, push)
- **Implementation**: Uses pygit2
- **Authentication**: Username and app password

## Error Handling

### Provider Package
All providers raise `ProviderError` for operation failures:

```python
from provider import ProviderError

try:
    await provider.clone("invalid_url", "/tmp/repo")
except ProviderError as e:
    print(f"Operation failed: {e}")
```

### Versioner Package
All versioners raise `VersionerError` for operation failures:

```python
from versioner import VersionerError

try:
    await versioner.clone("invalid_url", "/tmp/repo")
except VersionerError as e:
    print(f"Operation failed: {e}")
```

## Dependencies

- `pygit2`: Git operations for GitHub and Bitbucket versioners
- `asyncio`: Asynchronous operations
- `pathlib`: Path handling

## Testing

Run the test script to verify all packages work correctly:

```bash
uv run test_new_structure.py
```

## Code Quality

Both packages follow strict Python standards:
- Google format docstrings
- Modern typing (Python 3.11+)
- Ruff linting and formatting
- Absolute imports only
- Comprehensive error handling

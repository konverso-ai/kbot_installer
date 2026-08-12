# Factory Package

A utility package for dynamic class and method instantiation using string names and `importlib`.

## Features

- **Dynamic Class Loading**: Get classes by name from any package
- **Dynamic Object Creation**: Create instances of classes by name
- **Naming Convention Support**: Use simplified names with automatic module/class resolution
- **Type Safety**: Full type hints and proper error handling
- **Flexible**: Works with any package structure

## Functions

The package exports only the main factory functions. Utility functions are available internally but not exported from the package.

#### `factory_class(name: str, package: str) -> type[T]`

Get a class by name from a package using generic naming convention.

```python
from utils.factory import factory_class

# Get the NexusProvider class
NexusProviderClass = factory_class("nexus", "provider")
print(NexusProviderClass)  # <class 'provider.nexus_provider.NexusProvider'>

# Get the GithubVersioner class
GithubVersionerClass = factory_class("github", "versioner")
print(GithubVersionerClass)  # <class 'versioner.github_versioner.GithubVersioner'>
```

### `factory_object(name: str, package: str, **kwargs: Any) -> T`

Create an instance of a class by name from a package using generic naming convention.

```python
from utils.factory import factory_object

# Create a NexusProvider instance
nexus = factory_object("nexus", "provider", base_url="https://nexus.example.com")
print(nexus)  # NexusProvider(https://nexus.example.com)

# Create a GithubVersioner instance
github = factory_object("github", "versioner", token="test_token")
print(github)  # GitHubVersioner(https://github.com)
```

#### `factory_function(module_name: str, attribute_name: str) -> T`

Get an attribute (class, function, or any object) from an explicit module path, with
no naming convention required between `module_name` and `attribute_name`. This is a
thin wrapper around `importlib.import_module(module_name)` + `getattr(module, attribute_name)`,
for cases where `factory_class`'s `{name}_{package}` / `{Name}{Package}` convention
does not apply.

```python
from utils.factory import factory_function

# Explicit module path + attribute name, no convention involved
NexusProvider = factory_function("provider.nexus_provider", "NexusProvider")
print(NexusProvider)  # <class 'provider.nexus_provider.NexusProvider'>

build_url = factory_function("provider.utils", "build_url")
print(build_url)  # <function build_url at 0x...>
```

### `factory_method(name: str, package: str, **kwargs: Any) -> Any`

Create an instance using generic naming convention. This function is a convenience
alias kept for backward compatibility: it behaves exactly like `factory_object` and
simply delegates to it (which itself builds the module/class names and delegates to
`factory_function`).

```python
from utils.factory import factory_method

# For provider package: "nexus" -> "nexus_provider" module -> "NexusProvider" class
nexus = factory_method("nexus", "provider", base_url="https://nexus.example.com")

# For versioner package: "github" -> "github_versioner" module -> "GithubVersioner" class
github = factory_method("github", "versioner", token="test_token")

# For versioner package: "bitbucket" -> "bitbucket_versioner" module -> "BitbucketVersioner" class
bitbucket = factory_method("bitbucket", "versioner", username="user", app_password="pass")
```

## Naming Conventions

The `factory_method` function uses a generic naming convention that works with any package:

### Generic Convention
- **Module name**: `"{method_name}_{package}"`
- **Class name**: `"{method_name.capitalize()}{package.capitalize()}"`

### Examples
- Input: `("nexus", "provider")` → Module: `"nexus_provider"` → Class: `"NexusProvider"`
- Input: `("github", "versioner")` → Module: `"github_versioner"` → Class: `"GithubVersioner"`
- Input: `("bitbucket", "versioner")` → Module: `"bitbucket_versioner"` → Class: `"BitbucketVersioner"`
- Input: `("test", "package")` → Module: `"test_package"` → Class: `"TestPackage"`

## Usage Examples

### Basic Usage

```python
from utils.factory import factory_class, factory_object, factory_method

# Get a class
NexusProviderClass = factory_class("nexus", "provider")

# Create an instance directly
nexus = factory_object("nexus", "provider", base_url="https://nexus.example.com")

# Create an instance using naming convention
nexus = factory_method("nexus", "provider", base_url="https://nexus.example.com")
```

### Utility Functions

Utility functions are available internally but not exported from the package. If you need them, import directly from the utils module:

```python
from utils.factory.utils import build_class_name, build_module_name, snake_to_pascal

# Use utility functions directly
class_name = build_class_name("nexus", "provider")  # "NexusProvider"
module_name = build_module_name("nexus", "provider")  # "nexus_provider"
pascal_case = snake_to_pascal("nexus_provider")  # "NexusProvider"
```

### With Versioner Package

```python
from utils.factory import factory_method

# Create GitHub versioner
github = factory_method("github", "versioner", token="your_github_token")

# Create Bitbucket versioner
bitbucket = factory_method("bitbucket", "versioner", username="user", app_password="pass")
```

### Error Handling

```python
from utils.factory import factory_method

try:
    nexus = factory_method("nexus", "provider", base_url="https://nexus.example.com")
except ImportError as e:
    print(f"Package or module not found: {e}")
except AttributeError as e:
    print(f"Class not found: {e}")
except TypeError as e:
    print(f"Invalid arguments: {e}")
```

## Implementation Details

- Uses `importlib.import_module()` for dynamic module loading
- Uses `getattr()` for dynamic attribute access
- Supports both absolute and relative imports
- Full type hints for better IDE support
- Comprehensive error handling

## Dependencies

- `importlib`: For dynamic module loading
- `typing`: For type hints

## Testing

Run the test scripts to verify functionality:

```bash
# Test with provider package
uv run test_factory.py

# Test with versioner package
uv run test_factory_versioner.py

# Complete test
uv run test_factory_complete.py
```

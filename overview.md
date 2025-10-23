# AI Code Review Extension for Azure DevOps# AI Code Review for Azure DevOps



Automatically review pull requests using AI-powered code analysis with support for multiple LLM providers.Automatically review pull requests using AI-powered code analysis. This extension integrates advanced language models (LLMs) into your Azure Pipelines to provide intelligent, constructive code review feedback.



## Features## 🌟 Features



🤖 **Multi-Provider AI Support**- **🤖 Multiple AI Providers**: Choose from OpenAI (GPT-3.5/GPT-4), Azure OpenAI, Anthropic Claude, or local Ollama models

- OpenAI (GPT-4, GPT-3.5)- **🔒 On-Premise Support**: Use local LLMs with Ollama for complete data privacy

- Azure OpenAI- **🎯 Customizable Reviews**: Focus on security, performance, code quality, best practices, or bugs

- Anthropic Claude- **💬 Automatic Comments**: Posts review comments directly to your pull requests

- Ollama (local LLMs)- **📊 Smart Filtering**: Only reviews relevant file types and respects exclude patterns

- **🚀 Quick Mode**: Fast security-focused scans for time-sensitive reviews

🔍 **Comprehensive Code Analysis**- **⚙️ Flexible Configuration**: Configure via YAML files or pipeline variables

- Security vulnerabilities

- Code quality and maintainability## 📦 Installation

- Performance issues

- Best practices1. Install the extension from the [Azure DevOps Marketplace](https://marketplace.visualstudio.com/)

- Potential bugs2. Configure your LLM provider credentials as secret variables

3. Add the AI Code Review task to your pipeline

💬 **Smart PR Comments**

- Inline comments on specific lines## 🚀 Quick Start

- Constructive feedback with examples

- Summary reports### Basic Usage

- Configurable review depth

```yaml

⚙️ **Highly Configurable**trigger: none

- File type filteringpr:

- Directory exclusions  branches:

- Custom review scopes    include:

- Flexible comment styles      - main



## Quick Startpool:

  vmImage: 'ubuntu-latest'

1. **Install the extension** in your Azure DevOps organization

2. **Configure your LLM provider** (add API key as a pipeline variable)steps:

3. **Add the task** to your PR pipeline:  - checkout: self

    persistCredentials: true

```yaml  

- task: AICodeReview@1  - task: UsePythonVersion@0

  inputs:    inputs:

    llmProvider: 'openai'      versionSpec: '3.10'

    llmModel: 'gpt-4-turbo'  

    llmApiKey: $(OPENAI_API_KEY)  - task: AICodeReview@1

    postComments: true    displayName: 'AI Code Review'

  condition: eq(variables['Build.Reason'], 'PullRequest')    inputs:

  env:      llmProvider: 'openai'

    SYSTEM_ACCESSTOKEN: $(System.AccessToken)      llmModel: 'gpt-4'

```      llmApiKey: '$(OPENAI_API_KEY)'

      postComments: true

4. **Create a Pull Request** and watch the AI review your code automatically!      postSummary: true

    env:

## Configuration      SYSTEM_ACCESSTOKEN: $(System.AccessToken)

```

### Basic Configuration

### Using Configuration File

```yaml

- task: AICodeReview@1Create `config/config.yaml`:

  displayName: 'AI Code Review'

  inputs:```yaml

    llmProvider: 'openai'          # Required: openai, azure_openai, anthropic, ollamallm:

    llmModel: 'gpt-4-turbo'        # Required: Model name  provider: "azure_openai"

    llmApiKey: $(OPENAI_API_KEY)   # Required: API key from pipeline variables  model: "gpt-4"

    postComments: true             # Post comments to PR  api_key: "${LLM_API_KEY}"

```  api_base: "https://your-org.openai.azure.com"

  api_version: "2024-02-15-preview"

### Advanced Configuration

azure_devops:

```yaml  organization_url: "${AZDO_ORG_URL}"

- task: AICodeReview@1  project: "${AZDO_PROJECT}"

  inputs:  repository: "${AZDO_REPOSITORY}"

    llmProvider: 'azure_openai'

    llmModel: 'gpt-4'review:

    llmApiKey: $(AZURE_OPENAI_KEY)  review_scope:

    llmApiBase: 'https://your-resource.openai.azure.com'    - security

        - performance

    reviewScope: |    - code_quality

      security  file_extensions:

      code_quality    - .py

      performance    - .ts

        - .js

    fileExtensions: |  exclude_patterns:

      .py    - "**/test_*.py"

      .js    - "**/node_modules/**"

      .ts```

    

    excludePatterns: |Pipeline:

      */dist/*

      */node_modules/*```yaml

```- task: AICodeReview@1

  inputs:

## Requirements    configPath: 'config/config.yaml'

  env:

- Azure DevOps organization (cloud or server)    SYSTEM_ACCESSTOKEN: $(System.AccessToken)

- API key for one of the supported LLM providers:    LLM_API_KEY: $(OPENAI_API_KEY)

  - **OpenAI**: Get from [platform.openai.com](https://platform.openai.com)```

  - **Azure OpenAI**: Deploy in Azure Portal

  - **Anthropic**: Get from [console.anthropic.com](https://console.anthropic.com)## 🎛️ Configuration Options

  - **Ollama**: Install locally from [ollama.ai](https://ollama.ai)

- Build service permissions to post comments### LLM Provider Settings



## Setup Instructions| Input | Description | Default |

|-------|-------------|---------|

### 1. Store API Key Securely| `llmProvider` | LLM provider (openai, azure_openai, anthropic, ollama) | `openai` |

| `llmModel` | Model name (e.g., gpt-4, claude-3-opus) | `gpt-4` |

Store your API key as a secret pipeline variable:| `llmApiKey` | API key for the provider | - |

| `llmApiBase` | Base URL (for Azure OpenAI/Ollama) | - |

1. Go to Pipelines → Edit your pipeline| `llmApiVersion` | API version (for Azure OpenAI) | - |

2. Click **Variables**

3. Add variable (e.g., `OPENAI_API_KEY`)### Review Settings

4. Check **Keep this value secret**

| Input | Description | Default |

### 2. Enable Build Service Permissions|-------|-------------|---------|

| `reviewScope` | Aspects to review (security, performance, etc.) | All aspects |

1. Project Settings → Repositories → Security| `fileExtensions` | File types to review | Common code files |

2. Find **[Project] Build Service**| `excludePatterns` | Glob patterns to exclude | Test files, build artifacts |

3. Grant **Contribute** permission| `quickMode` | Fast security-only scan | `false` |

| `maxIssuesPerFile` | Maximum issues per file (0 = unlimited) | `10` |

### 3. Add to Pipeline

### Posting Settings

Add the task to your `azure-pipelines.yml`:

| Input | Description | Default |

```yaml|-------|-------------|---------|

trigger: none| `postComments` | Post review comments to PR | `true` |

| `postSummary` | Post summary comment | `true` |

pr:| `commentStyle` | Comment style (constructive, direct, detailed) | `constructive` |

  branches:

    include: ['*']## 📝 Supported LLM Providers



pool:### OpenAI

  vmImage: 'ubuntu-latest'

```yaml

steps:- task: AICodeReview@1

  - task: AICodeReview@1  inputs:

    displayName: 'AI Code Review'    llmProvider: 'openai'

    inputs:    llmModel: 'gpt-4'

      llmProvider: 'openai'    llmApiKey: '$(OPENAI_API_KEY)'

      llmModel: 'gpt-4-turbo'```

      llmApiKey: $(OPENAI_API_KEY)

      postComments: true### Azure OpenAI

    condition: eq(variables['Build.Reason'], 'PullRequest')

    env:```yaml

      SYSTEM_ACCESSTOKEN: $(System.AccessToken)- task: AICodeReview@1

```  inputs:

    llmProvider: 'azure_openai'

## Support    llmModel: 'gpt-4'

    llmApiKey: '$(AZURE_OPENAI_API_KEY)'

- **Documentation**: See README.md and ExtensionSetup.md in the repository    llmApiBase: 'https://your-org.openai.azure.com'

- **Issues**: Report issues on GitHub    llmApiVersion: '2024-02-15-preview'

- **Support**: Contact your organization administrator```



## Privacy & Security### Anthropic Claude



- API keys are never logged or exposed```yaml

- Code is sent to your chosen LLM provider for analysis- task: AICodeReview@1

- Comments are posted using your build service account  inputs:

- No data is stored by the extension    llmProvider: 'anthropic'

    llmModel: 'claude-3-opus-20240229'

## License    llmApiKey: '$(ANTHROPIC_API_KEY)'

```

MIT License - See LICENSE file for details

### Ollama (Local/On-Premise)

```yaml
- task: AICodeReview@1
  inputs:
    llmProvider: 'ollama'
    llmModel: 'codellama'
    llmApiBase: 'http://localhost:11434'
```

## 🔐 Security Best Practices

1. **Store API Keys Securely**: Always use Azure Pipeline secret variables
2. **Use Variable Groups**: Organize secrets in variable groups
3. **Enable System.AccessToken**: Required for posting comments
4. **On-Premise Option**: Use Ollama for complete data privacy

### Setting up Secrets

1. Go to your Azure DevOps project
2. Navigate to Pipelines → Library → Variable Groups
3. Create a new group named `AI-Review-Secrets`
4. Add secret variables:
   - `LLM_API_KEY`
   - `LLM_API_BASE` (if needed)
5. Reference the group in your pipeline:

```yaml
variables:
  - group: 'AI-Review-Secrets'
```

## 📊 Output Variables

The task sets the following output variables:

- `AI_REVIEW_ISSUE_COUNT`: Total number of issues found
- `AI_REVIEW_CRITICAL_COUNT`: Number of critical/error issues
- `AI_REVIEW_SUMMARY`: Text summary of the review

Use them in subsequent steps:

```yaml
- script: |
    echo "Issues found: $(AI_REVIEW_ISSUE_COUNT)"
    echo "Critical: $(AI_REVIEW_CRITICAL_COUNT)"
  displayName: 'Display Results'
```

## 🎯 Review Scope Options

| Scope | Description |
|-------|-------------|
| `security` | Security vulnerabilities, injection flaws, auth issues |
| `performance` | Performance bottlenecks, inefficient algorithms |
| `code_quality` | Code smells, complexity, maintainability |
| `best_practices` | Language idioms, design patterns |
| `bugs` | Logic errors, edge cases, potential crashes |
| `style` | Formatting, naming conventions |
| `documentation` | Missing docs, unclear comments |

## 🔧 Advanced Configuration

### Fail Build on Critical Issues

```yaml
- task: AICodeReview@1
  inputs:
    llmProvider: 'openai'
    llmModel: 'gpt-4'
    llmApiKey: '$(OPENAI_API_KEY)'
  env:
    SYSTEM_ACCESSTOKEN: $(System.AccessToken)
    FAIL_ON_CRITICAL_ISSUES: 'true'
```

### Custom File Patterns

```yaml
- task: AICodeReview@1
  inputs:
    fileExtensions: |
      .py
      .ts
      .tsx
      .rs
      .go
    excludePatterns: |
      **/test_*.py
      **/*.test.ts
      **/vendor/**
      **/node_modules/**
      **/__pycache__/**
```

### Dry Run Mode

```yaml
- task: AICodeReview@1
  inputs:
    postComments: false
    postSummary: false
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         Azure Pipeline Task             │
│  (TypeScript runner + Python script)    │
└──────────────┬──────────────────────────┘
               │
               ├─► Azure DevOps API (Fetch PR)
               │
               ├─► LLM Provider
               │   ├─ OpenAI API
               │   ├─ Azure OpenAI
               │   ├─ Anthropic API
               │   └─ Ollama (Local)
               │
               └─► Azure DevOps API (Post Comments)
```

## 📖 Documentation

- [Full Documentation](https://github.com/simbrella/azure-ai-code-review/wiki)
- [Configuration Guide](https://github.com/simbrella/azure-ai-code-review/wiki/Configuration)
- [Troubleshooting](https://github.com/simbrella/azure-ai-code-review/wiki/Troubleshooting)

## 🤝 Support

- [Report Issues](https://github.com/simbrella/azure-ai-code-review/issues)
- [Request Features](https://github.com/simbrella/azure-ai-code-review/issues/new)
- [Contribute](https://github.com/simbrella/azure-ai-code-review/blob/main/CONTRIBUTING.md)

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details

## 🙏 Credits

Built with:
- [OpenAI](https://openai.com/)
- [Azure OpenAI Service](https://azure.microsoft.com/en-us/products/ai-services/openai-service)
- [Anthropic Claude](https://www.anthropic.com/)
- [Ollama](https://ollama.ai/)
- [Azure Pipelines Task SDK](https://github.com/microsoft/azure-pipelines-task-lib)

---

Made with ❤️ by [Simbrella](https://simbrella.com)

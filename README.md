# Azure DevOps AI PR Review Extension

An intelligent Azure DevOps extension that leverages AI (OpenAI, Azure OpenAI, Anthropic, Ollama) to automatically review pull requests and provide insightful comments on code quality, security, performance, and best practices.

## 🎯 Key Features

- **Multiple LLM Providers**: OpenAI GPT-4, Azure OpenAI, Anthropic Claude, Ollama (local)
- **Automated Reviews**: Analyzes code changes and posts structured comments to PRs
- **Security Focused**: Detects vulnerabilities, bugs, and anti-patterns
- **Highly Configurable**: Customize review scope, file filters, and comment styles
- **Enterprise Ready**: Supports on-premise Azure DevOps and air-gapped environments
- **Easy Integration**: Simple pipeline task - just add to your YAML

## 📋 Prerequisites

- Azure DevOps organization (cloud or on-premise)
- API key for your LLM provider (OpenAI, Azure OpenAI, Anthropic, or Ollama)
- **Authentication** (choose one):
  - **Option A**: Build Service with `Contribute to pull requests` permission - See **[PERMISSION_SETUP.md](PERMISSION_SETUP.md)**
  - **Option B**: Personal Access Token with `Code (Read/Write)` scope - See **[USING_PAT_TOKEN.md](USING_PAT_TOKEN.md)**

## 🚀 Quick Start

See **[ExtensionSetup.md](ExtensionSetup.md)** for complete installation and configuration instructions.

### Basic Pipeline Example

```yaml
trigger: none

pr:
  branches:
    include: ['*']

pool:
  vmImage: 'ubuntu-latest'

steps:
  - task: AICodeReview@1
    displayName: 'AI Code Review'
    inputs:
      llmProvider: 'openai'
      llmModel: 'gpt-4-turbo'
      llmApiKey: $(OPENAI_API_KEY)
      reviewScope: |
        security
        code_quality
        performance
      postComments: true
    condition: eq(variables['Build.Reason'], 'PullRequest')
    env:
      SYSTEM_ACCESSTOKEN: $(System.AccessToken)
```

## ⚙️ Configuration Options

### LLM Providers

| Provider | Models | Best For |
|----------|--------|----------|
| **OpenAI** | GPT-4 Turbo, GPT-4, GPT-3.5 | High quality, cloud-based |
| **Azure OpenAI** | Your deployed models | Enterprise compliance |
| **Anthropic** | Claude 3 Opus/Sonnet/Haiku | Alternative provider |
| **Ollama** | Llama 2, Mistral, CodeLlama | Local/air-gapped setups |

### Task Input Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `llmProvider` | LLM provider (openai, azure_openai, anthropic, ollama) | - |
| `llmModel` | Model name (e.g., gpt-4-turbo) | - |
| `llmApiKey` | API key for the provider | - |
| `reviewScope` | What to review (security, code_quality, performance, etc.) | All |
| `fileExtensions` | File types to review (.py, .js, .ts, etc.) | All |
| `excludePatterns` | Patterns to exclude (*/dist/*, *.min.js) | None |
| `postComments` | Whether to post comments to PR | true |
| `commentStyle` | Comment style (constructive, concise, detailed) | constructive |

### Review Scope Options

- `security` - Security vulnerabilities and risks
- `code_quality` - Code style and maintainability
- `performance` - Performance issues and optimizations
- `best_practices` - Language-specific best practices
- `bugs` - Potential bugs and logic errors
- `documentation` - Missing or incorrect docs
- `testing` - Test coverage and quality
- `architecture` - Design patterns and structure

## 📖 Configuration Examples

### Example 1: Security-Focused Review

```yaml
- task: AICodeReview@1
  inputs:
    llmProvider: 'openai'
    llmModel: 'gpt-4'
    llmApiKey: $(OPENAI_API_KEY)
    reviewScope: |
      security
      bugs
    postComments: true
    commentStyle: 'detailed'
```

### Example 2: Full Review with Azure OpenAI

```yaml
- task: AICodeReview@1
  inputs:
    llmProvider: 'azure_openai'
    llmModel: 'gpt-4'
    llmApiKey: $(AZURE_OPENAI_KEY)
    llmApiBase: 'https://your-resource.openai.azure.com'
    llmApiVersion: '2023-05-15'
    reviewScope: |
      security
      code_quality
      performance
      best_practices
    fileExtensions: |
      .py
      .js
      .ts
    excludePatterns: |
      */dist/*
      */build/*
      *.min.js
    postComments: true
    commentStyle: 'constructive'
```

### Example 3: Local Ollama Setup

```yaml
- task: AICodeReview@1
  inputs:
    llmProvider: 'ollama'
    llmModel: 'codellama'
    llmApiBase: 'http://localhost:11434'
    reviewScope: |
      code_quality
      bugs
    postComments: true
```

### Example 4: Using Configuration File

Create `config.yaml` in your repo:
```yaml
llm:
  provider: openai
  model: gpt-4-turbo
  api_key: ${OPENAI_API_KEY}

review:
  review_scope:
    - security
    - code_quality
    - performance
  file_extensions:
    - .py
    - .js
    - .ts
  exclude_patterns:
    - '*/dist/*'
    - '*.min.js'
```

Pipeline:
```yaml
- task: AICodeReview@1
  inputs:
    configPath: 'config.yaml'
    postComments: true
```

## 🔒 Security Best Practices

1. **Store API keys as secret variables** in Azure Pipelines
2. **Use `$(System.AccessToken)`** for Azure DevOps authentication
3. **Never commit** API keys or PAT tokens to source control
4. **Use minimum permissions** for PAT tokens (Code Read/Write + PR Threads Read/Write)
5. **Enable SSL verification** for production environments

## 🐛 Troubleshooting

### Issue: Comments not posted to PR

**Solutions:**
- Ensure `SYSTEM_ACCESSTOKEN` environment variable is set: `env: SYSTEM_ACCESSTOKEN: $(System.AccessToken)`
- Verify Build Service has **Contribute** permission on the repository
- Check `postComments: true` is set in task inputs

### Issue: Authentication errors

**Solutions:**
- Verify PAT token is valid and not expired
- Check PAT has required scopes: Code (Read/Write) and Pull Request Threads (Read/Write)
- **For Build Service**: See **[PERMISSION_SETUP.md](PERMISSION_SETUP.md)** for granting permissions
  - Go to Project Settings → Repositories → Security → Grant "Contribute to pull requests" to Build Service
- Ensure `System.AccessToken` is passed in pipeline YAML: `env: SYSTEM_ACCESSTOKEN: $(System.AccessToken)`

### Issue: API rate limits or timeouts

**Solutions:**
- Reduce `max_files_per_review` (default: 50)
- Add file filtering with `fileExtensions` and `excludePatterns`
- Use a higher-tier API plan with your provider

### Issue: Task not running on PR

**Solutions:**
- Ensure PR trigger is configured: `pr: branches: include: ['*']`
- Add condition: `condition: eq(variables['Build.Reason'], 'PullRequest')`
- Check pipeline is not manually triggered (should be PR trigger)

## 📊 Project Structure

```
azure-extension/
├── src/                     # Python source code
│   ├── config/             # Configuration management
│   ├── azure_devops/       # Azure DevOps API integration
│   ├── llm/                # LLM provider implementations
│   └── utils/              # Utilities and logging
├── task/                   # Azure Pipelines task
│   ├── src/index.ts        # TypeScript task runner
│   └── task.json           # Task manifest
├── scripts/                # Utility scripts
│   └── review_pr.py        # Main review orchestration
├── tests/                  # Test suite (107+ tests)
├── config.example.yaml     # Example configuration
├── requirements.txt        # Python dependencies
└── vss-extension.json      # Extension manifest
```

## 🧪 Testing

```bash
# Run all tests
python scripts/run_tests.py --all --coverage

# Run only unit tests
python scripts/run_tests.py --python

# Run integration tests
python scripts/run_tests.py --markers integration

# Validate configuration
python validate_setup.py
```

## 📝 License

[Add your license]

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a pull request.

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Review [ExtensionSetup.md](ExtensionSetup.md) for setup help
- Check troubleshooting section above

---

**Status**: Production Ready ✅  
**Version**: 1.0.0

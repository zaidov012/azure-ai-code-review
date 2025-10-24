# Azure DevOps AI Code Review

An intelligent Azure DevOps extension that leverages AI to automatically review pull requests and provide insightful feedback on code quality, security, performance, and best practices.

## ✨ Features

- **🤖 Multiple AI Providers**: OpenAI GPT-4, Azure OpenAI, Anthropic Claude, Ollama (local)
- **🔒 Security First**: Detects vulnerabilities, security risks, and anti-patterns
- **⚡ Easy Integration**: Simple pipeline task configuration
- **🎯 Smart Filtering**: Configurable file types and exclusion patterns
- **🏢 Enterprise Ready**: Supports on-premise Azure DevOps and air-gapped environments
- **💬 Automated Comments**: Posts structured review comments directly to PRs

## � Quick Start

1. **Install the extension** from Azure DevOps Marketplace
2. **Configure authentication** (Build Service or PAT token)
3. **Add API key** as a secret pipeline variable
4. **Add the task** to your PR pipeline:

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
      postComments: true
    condition: eq(variables['Build.Reason'], 'PullRequest')
    env:
      SYSTEM_ACCESSTOKEN: $(System.AccessToken)
```

> 📖 **Full setup instructions**: See [Setup.md](Setup.md)

## 📋 Prerequisites

- Azure DevOps organization (cloud or on-premise)
- API key for your chosen LLM provider
- Build Service permissions or Personal Access Token

## ⚙️ Supported LLM Providers

| Provider | Models | Use Case |
|----------|--------|----------|
| **OpenAI** | GPT-4 Turbo, GPT-4, GPT-3.5 | High-quality cloud-based reviews |
| **Azure OpenAI** | Your deployed models | Enterprise compliance & data residency |
| **Anthropic** | Claude 3 Opus/Sonnet/Haiku | Alternative cloud provider |
| **Ollama** | Llama 2, Mistral, CodeLlama | Local/air-gapped environments |

## 🎯 Configuration Options

### Basic Task Inputs

| Input | Description | Default |
|-------|-------------|---------|
| `llmProvider` | AI provider (openai, azure_openai, anthropic, ollama) | `openai` |
| `llmModel` | Model name (e.g., gpt-4-turbo) | `gpt-4` |
| `llmApiKey` | API key for the provider | Required |
| `reviewScope` | What to review (security, code_quality, etc.) | All aspects |
| `postComments` | Post review comments to PR | `true` |

### Review Scopes

Configure what the AI should focus on:

- `security` - Security vulnerabilities and risks
- `code_quality` - Code style and maintainability
- `performance` - Performance issues and optimizations
- `best_practices` - Language-specific best practices
- `bugs` - Potential bugs and logic errors
- `documentation` - Missing or unclear documentation
- `testing` - Test coverage and quality
- `architecture` - Design patterns and structure

### Example Configurations

**Security-Focused Review:**
```yaml
- task: AICodeReview@1
  inputs:
    llmProvider: 'openai'
    llmModel: 'gpt-4'
    llmApiKey: $(OPENAI_API_KEY)
    reviewScope: |
      security
      bugs
    commentStyle: 'detailed'
```

**Full Review with File Filtering:**
```yaml
- task: AICodeReview@1
  inputs:
    llmProvider: 'azure_openai'
    llmModel: 'gpt-4'
    llmApiKey: $(AZURE_OPENAI_KEY)
    llmApiBase: 'https://your-resource.openai.azure.com'
    reviewScope: |
      security
      code_quality
      performance
    fileExtensions: |
      .py
      .js
      .ts
    excludePatterns: |
      */dist/*
      */node_modules/*
```

**Local Ollama Setup:**
```yaml
- task: AICodeReview@1
  inputs:
    llmProvider: 'ollama'
    llmModel: 'codellama'
    llmApiBase: 'http://localhost:11434'
    reviewScope: |
      code_quality
      bugs
```

## 📂 Project Structure

```
azure-extension/
├── src/                    # Python source code
│   ├── azure_devops/       # Azure DevOps API client
│   ├── llm/                # LLM provider implementations
│   ├── config/             # Configuration management
│   └── utils/              # Utilities and logging
├── task/                   # Azure Pipelines task
│   ├── src/                # TypeScript task implementation
│   ├── src_python/         # Bundled Python code
│   └── task.json           # Task manifest
├── tests/                  # Test suite
├── examples/               # Usage examples
├── pipelines/              # Example pipeline templates
└── scripts/                # Build and utility scripts
```

## 🧪 Testing & Validation

Run the validation script to test your setup:

```bash
python validate_setup.py
```

Run the test suite:

```bash
# All tests with coverage
python scripts/run_tests.py --all --coverage

# Unit tests only
python scripts/run_tests.py --python
```

## 🔒 Security Best Practices

- ✅ Store API keys as **secret pipeline variables**
- ✅ Use `$(System.AccessToken)` for Azure DevOps authentication
- ✅ Never commit API keys or PAT tokens to source control
- ✅ Use minimum required permissions for tokens
- ✅ Enable SSL verification in production
- ✅ Consider Ollama for complete data privacy (air-gapped)

## 🐛 Troubleshooting

### Common Issues

**Comments not posted to PR:**
- Ensure `SYSTEM_ACCESSTOKEN: $(System.AccessToken)` is set
- Verify Build Service has "Contribute to pull requests" permission
- Check `postComments: true` in task inputs

**Authentication errors:**
- For Build Service: Grant permissions in Project Settings → Repositories → Security
- For PAT token: Verify token has Code (Read/Write) scope and hasn't expired
- Wait 5 minutes after granting permissions for propagation

**Task not running:**
- Ensure PR trigger is configured in pipeline
- Add condition: `condition: eq(variables['Build.Reason'], 'PullRequest')`
- Verify extension is installed in your organization

**API rate limits:**
- Reduce `maxFilesPerReview` (default: 50)
- Add file filtering with `fileExtensions` and `excludePatterns`
- Consider upgrading your API plan

> 📖 **Detailed troubleshooting**: See [Setup.md](Setup.md#troubleshooting)

## 📖 Documentation

- **[Setup.md](Setup.md)** - Complete installation and configuration guide
- **[config.example.yaml](config.example.yaml)** - Example configuration file
- **[examples/](examples/)** - Code examples and usage patterns
- **[pipelines/](pipelines/)** - Example pipeline templates

## � Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python scripts/run_tests.py --all`
5. Submit a pull request

## � License

MIT License - See [LICENSE](LICENSE) file for details.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/zaidov012/azure-ai-code-review/issues)
- **Documentation**: [Setup Guide](Setup.md)
- **Repository**: [github.com/zaidov012/azure-ai-code-review](https://github.com/zaidov012/azure-ai-code-review)

---

**Made with ❤️ for better code reviews**

**Version**: 2.0.0 | **Status**: Production Ready ✅


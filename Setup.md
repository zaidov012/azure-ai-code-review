# Setup Guide

Complete guide to installing, configuring, and using the Azure DevOps AI Code Review Extension.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Authentication Setup](#authentication-setup)
  - [Option 1: Using Build Service (Recommended)](#option-1-using-build-service-recommended)
  - [Option 2: Using Personal Access Token](#option-2-using-personal-access-token)
- [Configuration](#configuration)
- [Pipeline Integration](#pipeline-integration)
- [Testing Your Setup](#testing-your-setup)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, ensure you have:

### 1. Azure DevOps Access
- Azure DevOps organization (cloud: `dev.azure.com` or on-premise)
- Admin or Contributor permissions on your project
- Access to create/edit pipelines

### 2. LLM Provider Account

Choose one of the following providers:

- **OpenAI**: Sign up at [platform.openai.com](https://platform.openai.com) and create an API key
- **Azure OpenAI**: Deploy a model in Azure Portal and get endpoint + key
- **Anthropic**: Sign up at [console.anthropic.com](https://console.anthropic.com) and create an API key
- **Ollama**: Install locally from [ollama.ai](https://ollama.ai) for on-premise/air-gapped environments

---

## Installation

### Method 1: Marketplace Installation (Recommended)

1. Go to [Azure DevOps Marketplace](https://marketplace.visualstudio.com/)
2. Search for "AI Code Review"
3. Click **Get it free**
4. Select your Azure DevOps organization
5. Click **Install**

### Method 2: Manual VSIX Installation

If you're installing from a VSIX package:

1. Download the `.vsix` file from the release
2. Go to your Azure DevOps Organization Settings
3. Navigate to **Extensions** → **Browse Marketplace** → **Manage Extensions**
4. Click **Upload extension**
5. Select the `.vsix` file and upload
6. Install the extension to your organization

### Method 3: Build from Source

```powershell
# Clone the repository
git clone https://github.com/zaidov012/azure-ai-code-review.git
cd azure-ai-code-review

# Install dependencies
cd task
npm install
npm run build

# Package the extension
cd ..
npm install -g tfx-cli
tfx extension create --manifest-globs vss-extension.json
```

---

## Authentication Setup

The extension needs permission to read pull requests and post comments. Choose one of the following authentication methods:

### Option 1: Using Build Service (Recommended)

This method uses the built-in Build Service account and requires no PAT token management.

#### Step 1: Grant Permissions

1. Go to your Azure DevOps project
2. Click **Project Settings** (bottom left)
3. Navigate to **Repositories** under **Repos**
4. Select your repository
5. Click the **Security** tab
6. Click **Add** and search for one of these identities:
   - `[Your Project Name] Build Service ([Collection Name])`
   - `Project Collection Build Service ([Collection Name])`
7. Set the following permissions to **Allow**:
   - ✅ **Contribute to pull requests**
   - ✅ **Read**
   - ✅ **Create tag** (optional)
8. Click **Save changes**

#### Step 2: Use System.AccessToken in Pipeline

In your pipeline YAML, pass the `System.AccessToken`:

```yaml
- task: AICodeReview@1
  displayName: 'AI Code Review'
  inputs:
    llmProvider: 'openai'
    llmModel: 'gpt-4'
    llmApiKey: $(OPENAI_API_KEY)
    postComments: true
  env:
    SYSTEM_ACCESSTOKEN: $(System.AccessToken)
```

**Verification**: After granting permissions, comments will appear from the Build Service account.

---

### Option 2: Using Personal Access Token

Use a PAT token when you need comments to appear from a specific user account, or when you cannot modify Build Service permissions.

#### Step 1: Create a Personal Access Token

1. Go to Azure DevOps → **User Settings** (top right) → **Personal Access Tokens**
2. Click **+ New Token**
3. Configure the token:
   - **Name**: `AI Code Review`
   - **Organization**: Select your organization
   - **Expiration**: Set based on your security policy (30-90 days recommended)
   - **Scopes**: Custom defined
     - ✅ **Code**: Read & Write
     - ✅ **Pull Request Threads**: Read & Write
4. Click **Create**
5. **Important**: Copy the token immediately and save it securely

#### Step 2: Store PAT Token as Pipeline Variable

1. Navigate to your pipeline
2. Click **Edit** → **Variables** (top right)
3. Click **+ New variable**
4. Configure:
   - **Name**: `AZDO_PAT_TOKEN`
   - **Value**: Paste your PAT token
   - ✅ **Keep this value secret** (click lock icon)
5. Click **OK** and **Save**

#### Step 3: Use PAT Token in Pipeline

```yaml
- task: AICodeReview@1
  displayName: 'AI Code Review'
  inputs:
    llmProvider: 'openai'
    llmModel: 'gpt-4'
    llmApiKey: $(OPENAI_API_KEY)
    postComments: true
  env:
    AZDO_PERSONAL_ACCESS_TOKEN: $(AZDO_PAT_TOKEN)
```

**Note**: If both `AZDO_PERSONAL_ACCESS_TOKEN` and `SYSTEM_ACCESSTOKEN` are provided, the PAT token takes priority.

---

## Configuration

### Step 1: Store LLM API Key Securely

**Method A: Pipeline Variable (Quick Setup)**

1. Go to **Pipelines** → Your Pipeline → **Edit**
2. Click **Variables**
3. Add variable:
   - **Name**: `OPENAI_API_KEY` (or `AZURE_OPENAI_KEY`, `ANTHROPIC_API_KEY`, etc.)
   - **Value**: Your API key
   - ✅ **Keep this value secret**
4. Click **OK** and **Save**

**Method B: Variable Group (Shared Across Pipelines)**

1. Go to **Pipelines** → **Library**
2. Click **+ Variable group**
3. **Name**: `AI-Review-Secrets`
4. Add variables:
   - `OPENAI_API_KEY` = your-api-key (click lock icon)
   - `AZURE_OPENAI_KEY` = your-azure-key (if using Azure OpenAI)
5. Click **Save**
6. In your pipeline, reference the group:

```yaml
variables:
  - group: 'AI-Review-Secrets'
```

**Method C: Azure Key Vault (Enterprise)**

```yaml
variables:
  - group: 'KeyVault-Linked-Group'

steps:
  - task: AzureKeyVault@2
    inputs:
      azureSubscription: 'Your-Service-Connection'
      KeyVaultName: 'your-keyvault-name'
      SecretsFilter: 'OPENAI-API-KEY'
```

### Step 2: Configuration File (Optional)

For advanced configurations, create a `config.yaml` file in your repository root:

```yaml
llm:
  provider: "openai"              # openai, azure_openai, anthropic, ollama
  model: "gpt-4-turbo"
  api_key: "${OPENAI_API_KEY}"    # Uses environment variable
  temperature: 0.3
  max_tokens: 2000

azure_devops:
  organization_url: "${AZDO_ORG_URL}"
  project: "${AZDO_PROJECT}"
  repository: "${AZDO_REPOSITORY}"
  verify_ssl: true

review:
  review_scope:
    - security
    - code_quality
    - performance
    - best_practices
  
  file_extensions:
    - .py
    - .js
    - .ts
    - .java
    - .cs
  
  exclude_patterns:
    - "*/dist/*"
    - "*/build/*"
    - "*/node_modules/*"
    - "*.min.js"
  
  comment_style: constructive      # constructive, concise, detailed
  max_files_per_review: 50

log_level: INFO
```

Reference it in your pipeline:

```yaml
- task: AICodeReview@1
  inputs:
    configPath: 'config.yaml'
    postComments: true
  env:
    SYSTEM_ACCESSTOKEN: $(System.AccessToken)
    OPENAI_API_KEY: $(OPENAI_API_KEY)
```

---

## Pipeline Integration

### Basic Configuration

```yaml
trigger: none

pr:
  branches:
    include:
      - main
      - develop
      - feature/*

pool:
  vmImage: 'ubuntu-latest'

steps:
  - checkout: self
    persistCredentials: true

  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.10'
    displayName: 'Setup Python'

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
      commentStyle: 'constructive'
    condition: eq(variables['Build.Reason'], 'PullRequest')
    env:
      SYSTEM_ACCESSTOKEN: $(System.AccessToken)
```

### Advanced Configuration

```yaml
- task: AICodeReview@1
  displayName: 'AI Code Review - Detailed'
  inputs:
    # LLM Configuration
    llmProvider: 'azure_openai'
    llmModel: 'gpt-4'
    llmApiKey: $(AZURE_OPENAI_KEY)
    llmApiBase: 'https://your-resource.openai.azure.com'
    llmApiVersion: '2024-02-15-preview'
    llmTimeout: 350
    
    # Review Scope
    reviewScope: |
      security
      code_quality
      performance
      best_practices
      bugs
    
    # File Filtering
    fileExtensions: |
      .py
      .js
      .ts
      .tsx
      .java
      .cs
    
    excludePatterns: |
      */dist/*
      */build/*
      */node_modules/*
      *.min.js
      */migrations/*
    
    # Comment Settings
    postComments: true
    postSummary: true
    commentStyle: 'constructive'
    maxIssuesPerFile: 10
    
    # Runtime
    pythonVersion: '3.10'
    logLevel: 'INFO'
  
  condition: eq(variables['Build.Reason'], 'PullRequest')
  env:
    SYSTEM_ACCESSTOKEN: $(System.AccessToken)
```

### Provider-Specific Examples

**OpenAI:**
```yaml
- task: AICodeReview@1
  inputs:
    llmProvider: 'openai'
    llmModel: 'gpt-4-turbo'
    llmApiKey: $(OPENAI_API_KEY)
```

**Azure OpenAI:**
```yaml
- task: AICodeReview@1
  inputs:
    llmProvider: 'azure_openai'
    llmModel: 'gpt-4'
    llmApiKey: $(AZURE_OPENAI_KEY)
    llmApiBase: 'https://your-resource.openai.azure.com'
    llmApiVersion: '2024-02-15-preview'
```

**Anthropic Claude:**
```yaml
- task: AICodeReview@1
  inputs:
    llmProvider: 'anthropic'
    llmModel: 'claude-3-opus-20240229'
    llmApiKey: $(ANTHROPIC_API_KEY)
```

**Ollama (Local/On-Premise):**
```yaml
- task: AICodeReview@1
  inputs:
    llmProvider: 'ollama'
    llmModel: 'codellama'
    llmApiBase: 'http://localhost:11434'
```

---

## Testing Your Setup

### Step 1: Validate Configuration

Run the validation script to ensure everything is configured correctly:

```bash
# Set environment variables
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4-turbo
export LLM_API_KEY=your-key
export AZDO_ORG_URL=https://dev.azure.com/yourorg
export AZDO_PROJECT=YourProject
export AZDO_REPOSITORY=YourRepo
export AZDO_PERSONAL_ACCESS_TOKEN=your-pat

# Run validation
python validate_setup.py
```

Expected output:
```
✅ Configuration file loaded successfully
✅ LLM provider connectivity test passed
✅ Azure DevOps authentication successful
✅ Repository access verified
✅ All checks passed
```

### Step 2: Test with a Sample Pull Request

1. **Create a test branch:**
   ```bash
   git checkout -b test-ai-review
   ```

2. **Make a simple code change:**
   ```python
   # test_file.py
   def calculate_total(items):
       total = 0
       for item in items:
           total = total + item
       return total
   ```

3. **Commit and push:**
   ```bash
   git add test_file.py
   git commit -m "Test AI review functionality"
   git push origin test-ai-review
   ```

4. **Create a Pull Request** in Azure DevOps

5. **Verify the pipeline runs** and check for AI comments on your PR

6. **Expected result**: The AI should suggest improvements like using `sum(items)` instead of a manual loop

---

## Troubleshooting

### Issue: "This task must run in a pull request build"

**Cause**: Pipeline is not triggered by a PR or missing PR trigger configuration.

**Solution:**
```yaml
# Add at top of pipeline
pr:
  branches:
    include: ['*']

# Add condition to task
condition: eq(variables['Build.Reason'], 'PullRequest')
```

---

### Issue: "401 Unauthorized" or "403 Forbidden"

**Cause**: Missing or invalid authentication token.

**Solutions:**

1. **If using Build Service:**
   - Verify Build Service has "Contribute to pull requests" permission
   - Check `SYSTEM_ACCESSTOKEN` is set in the pipeline:
     ```yaml
     env:
       SYSTEM_ACCESSTOKEN: $(System.AccessToken)
     ```

2. **If using PAT token:**
   - Verify token hasn't expired
   - Check token has required scopes: Code (Read & Write), Pull Request Threads (Read & Write)
   - Ensure variable is marked as secret and properly referenced:
     ```yaml
     env:
       AZDO_PERSONAL_ACCESS_TOKEN: $(AZDO_PAT_TOKEN)
     ```

3. **Check permissions propagation:**
   - Wait 5 minutes after granting permissions for changes to take effect
   - Try running the pipeline again

---

### Issue: No comments appear on PR

**Checklist:**
- [ ] `postComments: true` is set in task inputs
- [ ] Authentication is properly configured (Build Service permissions or PAT token)
- [ ] Pipeline completed successfully without errors
- [ ] PR is not already completed or abandoned
- [ ] Check pipeline logs for "Posted X comments" or "Successfully created comment thread" messages

**Debug Steps:**
1. Enable debug logging:
   ```yaml
   variables:
     - name: System.Debug
       value: true
   ```
2. Check logs for authentication messages
3. Verify the task detected PR context correctly

---

### Issue: LLM API errors (rate limit, timeout)

**Cause**: Too many requests, large files, or API rate limits.

**Solutions:**

1. **Reduce scope:**
   ```yaml
   inputs:
     maxFilesPerReview: 20        # Reduce from default 50
     maxIssuesPerFile: 5          # Limit issues per file
   ```

2. **Filter files:**
   ```yaml
   inputs:
     fileExtensions: |
       .py
       .js
     excludePatterns: |
       */dist/*
       */node_modules/*
       */test/*
   ```

3. **Adjust timeout:**
   ```yaml
   inputs:
     llmTimeout: 600              # Increase timeout to 10 minutes
   ```

---

### Issue: "Python not found" error

**Solution**: Add Python setup step before the AI Review task:

```yaml
- task: UsePythonVersion@0
  inputs:
    versionSpec: '3.10'
  displayName: 'Setup Python'
```

---

### Issue: SSL certificate errors (on-premise Azure DevOps)

**Cause**: Self-signed certificates in on-premise installations.

**Solution**: Add to your `config.yaml`:
```yaml
azure_devops:
  verify_ssl: false  # Only for trusted internal networks
```

Or use environment variable:
```yaml
env:
  AZDO_VERIFY_SSL: 'false'
```

---

### Issue: Comments appear from wrong account

**Explanation**: 
- If using `SYSTEM_ACCESSTOKEN`: Comments appear from Build Service
- If using `AZDO_PERSONAL_ACCESS_TOKEN`: Comments appear from the PAT owner

**To change**: Switch between authentication methods as described in the [Authentication Setup](#authentication-setup) section.

---

### Issue: Extension task not found

**Cause**: Extension not installed in your organization or project.

**Solutions:**
1. Verify extension is installed in your Azure DevOps organization
2. Check extension is shared with your project
3. Ensure you're using the correct task name: `AICodeReview@1`

---

## Best Practices

### Security
- ✅ Always store API keys as secret pipeline variables
- ✅ Use variable groups for shared secrets across pipelines
- ✅ Set reasonable PAT token expiration dates (30-90 days)
- ✅ Use minimal token scopes (only what's needed)
- ✅ Rotate tokens regularly
- ❌ Never commit API keys or tokens to source control

### Performance
- ✅ Use file filtering to review only relevant files
- ✅ Exclude test files, build artifacts, and dependencies
- ✅ Set reasonable `maxFilesPerReview` limits
- ✅ Use quick mode for faster security scans
- ✅ Consider costs of API usage with your provider

### Team Adoption
- ✅ Start with `postComments: false` to review output first
- ✅ Gradually enable more review scopes as team adapts
- ✅ Customize `commentStyle` to match team preferences
- ✅ Gather team feedback and adjust settings
- ✅ Document your team's configuration in the repository

---

## Support

For additional help:
- **Documentation**: See [README.md](README.md) for feature overview
- **Issues**: Report bugs at [GitHub Issues](https://github.com/zaidov012/azure-ai-code-review/issues)
- **Discussions**: Join conversations in GitHub Discussions
- **Enterprise Support**: Contact your Azure DevOps administrator

---

**Happy Reviewing! 🚀**

# Extension Setup Guide

Complete guide to installing and configuring the Azure DevOps AI PR Review Extension.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation Methods](#installation-methods)
3. [Configuration](#configuration)
4. [Pipeline Integration](#pipeline-integration)
5. [Testing the Setup](#testing-the-setup)
6. [Common Issues](#common-issues)

---

## Prerequisites

Before starting, ensure you have:

### 1. Azure DevOps Access
- Azure DevOps organization (cloud: `dev.azure.com` or on-premise)
- Admin or Contributor permissions on your project
- Access to create/edit pipelines

### 2. LLM Provider Account
Choose one:
- **OpenAI**: Sign up at [platform.openai.com](https://platform.openai.com) and create an API key
- **Azure OpenAI**: Deploy a model in Azure Portal and get endpoint + key
- **Anthropic**: Sign up at [console.anthropic.com](https://console.anthropic.com) and create an API key
- **Ollama**: Install locally from [ollama.ai](https://ollama.ai)

### 3. Azure DevOps Personal Access Token (PAT)

Create a PAT with these permissions:

1. Go to Azure DevOps → User Settings (top right) → Personal Access Tokens
2. Click "New Token"
3. Configure:
   - **Name**: AI Code Review
   - **Organization**: Select your organization
   - **Expiration**: 90 days (or custom)
   - **Scopes**: Custom defined
     - ✅ **Code**: Read & Write
     - ✅ **Pull Request Threads**: Read & Write
4. Click "Create" and **copy the token** (save it securely - you won't see it again)

---

## Installation Methods

Choose the method that best fits your needs:

### Method 1: Direct Pipeline Integration (Quickest)

Use the extension directly in your pipeline without marketplace installation.

**Step 1:** Add the repository to your project
```bash
# Clone or add as submodule
git clone <repository-url> .azure-extension
```

**Step 2:** Add to your `azure-pipelines.yml`
```yaml
trigger: none

pr:
  branches:
    include: ['*']

pool:
  vmImage: 'ubuntu-latest'

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.10'
    displayName: 'Setup Python'
  
  - script: |
      pip install -r .azure-extension/requirements.txt
    displayName: 'Install Dependencies'
  
  - script: |
      python .azure-extension/scripts/review_pr.py \
        --pr-id $(System.PullRequest.PullRequestId)
    displayName: 'AI Code Review'
    env:
      LLM_PROVIDER: 'openai'
      LLM_MODEL: 'gpt-4-turbo'
      LLM_API_KEY: $(OPENAI_API_KEY)
      AZDO_ORG_URL: $(System.TeamFoundationCollectionUri)
      AZDO_PROJECT: $(System.TeamProject)
      AZDO_REPOSITORY: $(Build.Repository.Name)
      AZDO_PERSONAL_ACCESS_TOKEN: $(System.AccessToken)
    condition: eq(variables['Build.Reason'], 'PullRequest')
```

### Method 2: Extension Marketplace Installation (Recommended for Enterprise)

Install as an Azure DevOps extension (requires packaging).

**Step 1: Build the Extension**

```powershell
# Install Node.js and TFX CLI
npm install -g tfx-cli

# Navigate to extension directory
cd azure-extension

# Build TypeScript task
cd task
npm install
npm run build
cd ..

# Package extension
tfx extension create --manifest-globs vss-extension.json
```

This creates a `.vsix` file.

**Step 2: Upload to Marketplace**

**Option A: Private Extension (Recommended)**
1. Go to [Visual Studio Marketplace Publisher Portal](https://marketplace.visualstudio.com/manage)
2. Sign in with your Azure DevOps account
3. Click **New Extension** → **Azure DevOps**
4. Upload the `.vsix` file
5. Set **Visibility**: Private
6. Click **Share** → Select your organization

**Option B: Internal Sharing (No Marketplace)**
1. Go to your Azure DevOps Organization Settings
2. Navigate to **Extensions** → **Manage Extensions**
3. Click **Upload extension**
4. Select the `.vsix` file
5. Extension installs directly to your organization

**Step 3: Install in Organization**
1. Go to your Azure DevOps organization
2. Click **Organization Settings** → **Extensions**
3. Find "AI Code Review" extension
4. Click **Install**
5. Select the projects where you want to use it

---

## Configuration

### Step 1: Store API Key Securely

**Option A: Pipeline Variables (Recommended)**
1. Go to Pipelines → Your Pipeline → Edit
2. Click **Variables** button
3. Add variable:
   - **Name**: `OPENAI_API_KEY` (or `AZURE_OPENAI_KEY`, etc.)
   - **Value**: Your API key
   - **Keep this value secret**: ✅ Checked
4. Click **OK** and **Save**

**Option B: Variable Group**
1. Go to Pipelines → Library
2. Click **+ Variable group**
3. **Name**: `AI-Review-Secrets`
4. Add variables:
   - `OPENAI_API_KEY` = your-key (lock icon to make secret)
5. Save
6. In pipeline, reference:
   ```yaml
   variables:
     - group: 'AI-Review-Secrets'
   ```

**Option C: Azure Key Vault (Enterprise)**
1. Store secret in Azure Key Vault
2. Link Key Vault to Azure DevOps:
   ```yaml
   variables:
     - group: 'KeyVault-Secrets'  # Linked to Key Vault
   
   steps:
     - task: AzureKeyVault@2
       inputs:
         azureSubscription: 'Your-Subscription'
         KeyVaultName: 'your-keyvault'
         SecretsFilter: 'OPENAI-API-KEY'
   ```

### Step 2: Enable Build Service Permissions

The task needs permission to post comments to PRs.

1. Go to **Project Settings** (bottom left)
2. Navigate to **Repositories**
3. Select your repository
4. Go to **Security** tab
5. Find **[Your Project Name] Build Service ([Your Org Name])**
6. Set these permissions:
   - **Contribute**: Allow ✅
   - **Read**: Allow ✅
   - **Create Tag**: Allow ✅
7. Save changes

### Step 3: Create Configuration File (Optional)

For more complex setups, create `config.yaml` in your repo:

```yaml
llm:
  provider: openai              # or: azure_openai, anthropic, ollama
  model: gpt-4-turbo
  api_key: ${OPENAI_API_KEY}    # Uses environment variable
  temperature: 0.3
  max_tokens: 2000

review:
  review_scope:
    - security                   # Security vulnerabilities
    - code_quality              # Code style and maintainability
    - performance               # Performance issues
    - best_practices            # Language best practices
    - bugs                      # Potential bugs
  
  file_extensions:
    - .py
    - .js
    - .ts
    - .java
    - .go
  
  exclude_patterns:
    - '*/dist/*'
    - '*/build/*'
    - '*/node_modules/*'
    - '*.min.js'
    - '*.min.css'
  
  comment_style: constructive    # or: concise, detailed
  max_files_per_review: 50

log_level: INFO
```

**Important**: Never commit API keys to Git! Use environment variables:
```yaml
api_key: ${OPENAI_API_KEY}      # Will read from environment
```

---

## Pipeline Integration

### Basic Configuration

Add to your `azure-pipelines.yml`:

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
  # Your existing build/test steps...
  
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
  displayName: 'AI Code Review'
  inputs:
    # LLM Configuration
    llmProvider: 'azure_openai'
    llmModel: 'gpt-4'
    llmApiKey: $(AZURE_OPENAI_KEY)
    llmApiBase: 'https://your-resource.openai.azure.com'
    llmApiVersion: '2023-05-15'
    
    # Review Configuration
    reviewScope: |
      security
      code_quality
      performance
      best_practices
    
    fileExtensions: |
      .py
      .js
      .ts
      .jsx
      .tsx
    
    excludePatterns: |
      */dist/*
      */build/*
      *.min.js
      */migrations/*
    
    # Posting Options
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

### Using Configuration File

```yaml
- task: AICodeReview@1
  displayName: 'AI Code Review'
  inputs:
    configPath: 'config.yaml'
    postComments: true
  condition: eq(variables['Build.Reason'], 'PullRequest')
  env:
    SYSTEM_ACCESSTOKEN: $(System.AccessToken)
```

---

## Testing the Setup

### Step 1: Validate Configuration

Run the validation script:

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

### Step 2: Test with Sample PR

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

5. **Check the pipeline:**
   - Pipeline should trigger automatically
   - Look for "AI Code Review" step
   - Check logs for execution details

6. **Verify comments appear:**
   - Go to your PR
   - Look for AI-generated comments
   - Comments should suggest improvements (e.g., "Consider using sum() instead of manual loop")

### Step 3: Review Pipeline Logs

Check the pipeline output:

```
🤖 AI Code Review Task Starting...
✓ Running in PR context: PR #123
✓ Python found: /usr/bin/python3.10
✓ Dependencies installed
✓ Environment configured

🔍 Starting AI code review...
  📄 Reviewing: test_file.py
  💬 Generated 2 comments
  
✓ Posted 2 comments to PR
✅ AI Code Review Task Completed Successfully

📊 Review Summary:
   Total Files: 1
   Issues Found: 2
   Critical: 0
   Major: 0
   Minor: 2
```

---

## Common Issues

### Issue 1: "This task must run in a pull request build"

**Cause**: Pipeline not triggered by PR or missing PR trigger

**Solution**:
```yaml
# Add PR trigger at top of pipeline
pr:
  branches:
    include: ['*']

# Add condition to task
condition: eq(variables['Build.Reason'], 'PullRequest')
```

### Issue 2: "401 Unauthorized" when posting comments

**Cause**: Missing or invalid System.AccessToken

**Solution**:
```yaml
# Add to task environment
env:
  SYSTEM_ACCESSTOKEN: $(System.AccessToken)
```

Also verify Build Service permissions (see Configuration Step 2).

### Issue 3: "403 Forbidden" on repository access

**Cause**: Build Service lacks permissions

**Solution**:
1. Project Settings → Repositories → Your Repo
2. Security tab
3. Find "[Project] Build Service"
4. Grant **Contribute** and **Read** permissions

### Issue 4: LLM API errors (rate limit, timeout)

**Cause**: Too many requests or large files

**Solution**:
```yaml
# Add these inputs to reduce load
inputs:
  maxFilesPerReview: 20         # Default: 50
  fileExtensions: |             # Only review specific types
    .py
    .js
  excludePatterns: |            # Exclude large directories
    */dist/*
    */node_modules/*
```

### Issue 5: No comments appear on PR

**Checklist**:
- [ ] `postComments: true` is set
- [ ] `SYSTEM_ACCESSTOKEN` environment variable is set
- [ ] Build Service has **Contribute** permission
- [ ] Pipeline completed successfully (no errors)
- [ ] PR is not already completed/abandoned
- [ ] Check pipeline logs for "Posted X comments" message

### Issue 6: "Python not found" error

**Solution**:
```yaml
# Add Python setup step before AI Review task
- task: UsePythonVersion@0
  inputs:
    versionSpec: '3.10'
  displayName: 'Setup Python'
```

### Issue 7: SSL certificate errors (on-premise)

**Cause**: Self-signed certificates in on-premise Azure DevOps

**Solution in config.yaml**:
```yaml
azure_devops:
  verify_ssl: false  # Only for trusted internal networks
```

Or use environment variable:
```bash
export AZDO_VERIFY_SSL=false
```

---

## Next Steps

Once setup is complete:

1. **Test on multiple PRs** to verify consistent behavior
2. **Customize review scope** based on your team's needs
3. **Monitor API usage and costs**
4. **Gather team feedback** and adjust settings
5. **Consider** setting up monitoring/alerts for failed reviews

## Support

If you encounter issues:
- Check logs in pipeline output
- Review this troubleshooting section
- Open an issue on GitHub
- Contact your Azure DevOps administrator

---

**Happy Reviewing! 🚀**

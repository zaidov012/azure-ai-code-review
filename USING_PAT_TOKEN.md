# Using Personal Access Token (PAT) for Authentication

This guide shows how to configure the AI Code Review task to use a Personal Access Token instead of the Build Service account.

## Why Use a PAT Token?

Using a PAT token allows comments to be posted under your user account (or a service account) instead of the generic "Project Collection Build Service" account. This provides:

- ✅ **Better attribution** - Comments appear from a recognizable user
- ✅ **No permission setup required** - Bypasses Build Service permission requirements
- ✅ **More control** - Use specific service accounts with controlled access

## Quick Setup

### Step 1: Create a Personal Access Token

1. Go to your Azure DevOps user settings:
   ```
   https://azdo.simbrella.pro/DefaultCollection/_usersSettings/tokens
   ```

2. Click **New Token**

3. Configure the token:
   - **Name**: `AI Code Review Bot` (or any name you prefer)
   - **Organization**: Select your organization
   - **Expiration**: Set based on your security policy (e.g., 90 days, 1 year)
   - **Scopes**: Select **Custom defined**
     - ✅ **Code**: Read & Write

4. Click **Create**

5. **Important**: Copy the token immediately and save it securely (you won't be able to see it again!)

### Step 2: Add PAT Token to Pipeline Variables

1. Navigate to your pipeline:
   ```
   Project > Pipelines > [Your Pipeline] > Edit
   ```

2. Click **Variables** (top right)

3. Click **New variable**

4. Configure the variable:
   - **Name**: `AZDO_PAT_TOKEN` (or `AZDO_PERSONAL_ACCESS_TOKEN`)
   - **Value**: Paste your PAT token
   - ✅ **Keep this value secret** (click the lock icon)
   - **Scope**: This release (or Pipeline if available)

5. Click **OK** and **Save**

### Step 3: Update Your Pipeline YAML

Update your pipeline YAML to use the PAT token. Here's your corrected configuration:

```yaml
trigger: none  # Don't run on push

pool:
  name: 'AzDoLinux'

stages:
  - stage: AIReview
    displayName: 'AI Code Review'
    jobs:
      - job: ReviewJob
        displayName: 'Review Pull Request with AI'
        steps:
          - checkout: self
            fetchDepth: 0
            persistCredentials: true

          - task: UsePythonVersion@0
            inputs:
              versionSpec: '3.8'
            displayName: 'Setup Python'
          
          - task: AICodeReview@1
            displayName: 'AI Code Review'
            inputs:
              # LLM Configuration
              llmProvider: 'openai'
              llmModel: 'gpt-5-mini'
              llmApiKey: $(OPENAI_API_KEY)
              llmTimeout: 399
              
              # Review Configuration
              reviewScope: |
                security
                code_quality
                performance
                best_practices
              
              fileExtensions: |
                .cs
                .json
              
              excludePatterns: |
                */dist/*
                */build/*
              
              # Posting Options
              postComments: true
              postSummary: true
              commentStyle: 'constructive'
              maxIssuesPerFile: 15
              
              # Runtime
              logLevel: 'INFO'
            env:
              # Use PAT token for authentication (comments will appear from your user)
              AZDO_PERSONAL_ACCESS_TOKEN: $(AZDO_PAT_TOKEN)
              
              # Note: Remove or comment out SYSTEM_ACCESSTOKEN if you don't want to use Build Service
              # SYSTEM_ACCESSTOKEN: $(System.AccessToken)
         
          - script: |
              echo "AI Review completed"
              echo "Issues found: $(AI_REVIEW_ISSUE_COUNT)"
              echo "Critical issues: $(AI_REVIEW_CRITICAL_COUNT)"
            displayName: 'Display review summary'
            condition: always()
```

### Step 4: Rebuild and Deploy the Extension (If Using Packaged Extension)

If you're using the extension from the marketplace or a VSIX package, you need to rebuild it:

```powershell
# Navigate to extension directory
cd "c:\Users\azaidov\Documents\Simbrella\azure-extension"

# Build the task
cd task
npm run build

# Go back to root and package the extension
cd ..
tfx extension create --manifest-globs vss-extension.json
```

Then republish the extension to your Azure DevOps organization.

### Step 5: Test the Configuration

1. **Trigger a PR build** to test the new configuration

2. **Check the logs** for this message:
   ```
   Using provided PAT token for authentication
   ```

3. **Verify comments** are posted with your user account instead of "Project Collection Build Service"

## Troubleshooting

### Comments Still Appear from Build Service

**Cause**: The extension is still using `System.AccessToken`

**Solution**: 
1. Ensure you removed or commented out `SYSTEM_ACCESSTOKEN: $(System.AccessToken)` from your YAML
2. Verify the PAT token variable is set correctly in pipeline variables
3. Make sure you rebuilt the task (`npm run build` in the `task` directory)
4. If using packaged extension, ensure you republished the updated VSIX

### 403 Forbidden Error with PAT Token

**Cause**: PAT token lacks required permissions

**Solution**:
1. Check token has **Code (Read & Write)** scope
2. Verify token hasn't expired
3. Ensure the user who created the token has access to the repository

### PAT Token Not Being Used

**Causes**:
- Variable name mismatch
- Token not marked as secret
- Task not rebuilt after code changes

**Solution**:
1. Verify variable name is exactly `AZDO_PAT_TOKEN` or `AZDO_PERSONAL_ACCESS_TOKEN`
2. Check that variable is available in the pipeline scope
3. Enable debug logging: Add variable `System.Debug = true`
4. Look for this log line: `Using provided PAT token for authentication`

### Variable Not Available in Pipeline

**Solution**:
1. Ensure variable is saved in pipeline variables
2. Variable should be at pipeline level, not stage/job level
3. For classic pipelines, add to variable groups

## Security Best Practices

### PAT Token Security

- ✅ **Always mark tokens as secret** in pipeline variables
- ✅ **Set reasonable expiration dates** (30-90 days recommended)
- ✅ **Use minimal scopes** (only Code: Read & Write)
- ✅ **Rotate tokens regularly**
- ✅ **Use service accounts** for production pipelines
- ❌ **Never commit tokens** to source control
- ❌ **Don't share tokens** across multiple pipelines

### Service Account Recommendation

For production use, create a dedicated service account:

1. Create a new Azure DevOps user: `svc-ai-code-review@yourdomain.com`
2. Grant minimal repository access
3. Generate PAT token from this account
4. Use this token in all pipelines

This provides:
- Clear attribution
- Easier auditing
- Simplified permission management
- Better security boundaries

## How It Works

The task now uses this authentication priority:

1. **First**: Check if `AZDO_PERSONAL_ACCESS_TOKEN` environment variable is set
2. **Then**: If not set, fall back to `System.AccessToken` (Build Service)

This means:
- If you provide a PAT token via `env.AZDO_PERSONAL_ACCESS_TOKEN`, it will be used
- If you don't provide a PAT token, Build Service authentication is used automatically
- PAT token always takes priority over Build Service

## Verification

To verify which authentication method is being used, check the pipeline logs with debug enabled:

```yaml
variables:
  - name: System.Debug
    value: true
```

Look for one of these messages:
- `Using provided PAT token for authentication` ✅ Using your PAT
- `Using System.AccessToken for authentication` ℹ️ Using Build Service

## Need Help?

- Check [PERMISSION_SETUP.md](PERMISSION_SETUP.md) for Build Service permission setup
- Review [ExtensionSetup.md](ExtensionSetup.md) for general extension setup
- Open an issue if you encounter problems

---

**Last Updated**: October 24, 2025

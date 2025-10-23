# Azure DevOps Build Service Permissions Setup

## Problem
The error `TF401027: You need the Git 'PullRequestContribute' permission` occurs when the Build service account lacks permissions to create comments on pull requests.

**Error Message:**
```
"You need the Git 'PullRequestContribute' permission to perform this action. 
Details: identity 'Build\\1c88ba22-a6c8-4f44-bbca-451ac072d954', scope 'repository'."
```

## Solution: Grant Build Service Permissions

### Option 1: Grant Permissions at Repository Level (Recommended)

1. **Navigate to Repository Settings:**
   - Go to your Azure DevOps project: `https://azdo.simbrella.pro/DefaultCollection/SalaryNow/_git/salarynow-core`
   - Click on **Project Settings** (bottom left)
   - Under **Repos**, select **Repositories**
   - Select your repository (`salarynow-core`)

2. **Find Build Service Identity:**
   - Click on the **Security** tab
   - Click **Add** button
   - Search for one of these identities:
     - `SalaryNow Build Service (DefaultCollection)` (Project-level)
     - `Project Collection Build Service (DefaultCollection)` (Collection-level)

3. **Grant Required Permissions:**
   - Find the Build Service identity in the list
   - Set the following permissions to **Allow**:
     - ✅ **Contribute to pull requests** - Required for creating comments
     - ✅ **Create tag** (if needed for tagging)
     - ✅ **Read** - Should already be enabled

4. **Save Changes**

### Option 2: Grant Permissions at Project Level

1. **Navigate to Project Settings:**
   - Go to your project: `https://azdo.simbrella.pro/DefaultCollection/SalaryNow`
   - Click **Project Settings** (bottom left)

2. **Access Repositories Security:**
   - Under **Repos**, click **Repositories**
   - Click on the **Security** tab at the top

3. **Find and Configure Build Service:**
   - Search for: `SalaryNow Build Service (DefaultCollection)`
   - Grant **Contribute to pull requests** permission
   - Set to **Allow**

4. **Save Changes**

### Option 3: Use Personal Access Token (Alternative)

If you cannot modify Build Service permissions, use a PAT token instead:

1. **Create a Personal Access Token:**
   - Go to: `https://azdo.simbrella.pro/DefaultCollection/_usersSettings/tokens`
   - Click **New Token**
   - Set these scopes:
     - ✅ **Code (Read & Write)** - Required for PR comments
   - Save the token securely

2. **Configure Pipeline Variable:**
   - In your pipeline, add a secret variable:
     - Variable name: `AZDO_PAT_TOKEN` (or any name you prefer)
     - Value: Your PAT token
     - ✅ Keep this value secret

3. **Update Pipeline YAML:**
   ```yaml
   - task: AICodeReview@1
     inputs:
       # ... other inputs ...
     env:
       # Comment out or remove the System.AccessToken line
       # SYSTEM_ACCESSTOKEN: $(System.AccessToken)
       
       # Use your PAT token instead
       AZDO_PERSONAL_ACCESS_TOKEN: $(AZDO_PAT_TOKEN)
   ```

**Note:** The task now prioritizes `AZDO_PERSONAL_ACCESS_TOKEN` over `System.AccessToken`. If both are provided, the PAT token will be used.

## Verification

### Test Permissions

After granting permissions, run this verification:

1. **Check Build Service Identity:**
   ```bash
   # In Azure DevOps, go to:
   Project Settings > Repositories > [Your Repo] > Security
   # Verify "Contribute to pull requests" is set to "Allow" for Build Service
   ```

2. **Test in Pipeline:**
   - Trigger a new PR build
   - Check if comments are posted successfully
   - Look for this success message in logs:
     ```
     INFO src.azure_devops.comment_client: Successfully created comment thread #123
     ```

## Troubleshooting

### Still Getting 403 Errors?

1. **Check if you granted permissions to the correct identity:**
   - Project-level: `[ProjectName] Build Service ([CollectionName])`
   - Collection-level: `Project Collection Build Service ([CollectionName])`
   - Try granting to both if unsure

2. **Verify System.AccessToken is enabled:**
   - In pipeline YAML, ensure job has access:
   ```yaml
   jobs:
     - job: ReviewJob
       steps:
         - checkout: self
           persistCredentials: true  # Important!
   ```

3. **Check for Branch Policies:**
   - Branch policies might restrict who can comment
   - Go to: Repos > Branches > [Branch] > Branch policies
   - Ensure policies don't block Build Service

4. **Wait for Permission Propagation:**
   - Sometimes permissions take a few minutes to propagate
   - Try running the pipeline again after 5 minutes

## Security Considerations

### Build Service Permissions
- ✅ Safe to grant "Contribute to pull requests" to Build Service
- ✅ Limits access to repository scope only
- ✅ Cannot approve PRs or merge code
- ❌ Do NOT grant "Force push" or "Remove others' locks"

### PAT Token Best Practices
- ✅ Use minimal scopes (Code: Read & Write only)
- ✅ Set expiration dates (max 1 year)
- ✅ Store as secret pipeline variables
- ✅ Rotate tokens regularly
- ❌ Never commit tokens to source control

## Common Scenarios

### Scenario 1: Multiple Projects
If the extension is used across multiple projects:
- Grant permissions at **Collection level**
- Use: `Project Collection Build Service (DefaultCollection)`

### Scenario 2: Multiple Repositories
If one project has multiple repositories:
- Grant permissions at **Project level**, OR
- Grant individually per repository for finer control

### Scenario 3: Private vs Public Repos
- Private repos: Follow standard permission setup
- Public repos: May need additional security review

## Additional Resources

- [Azure DevOps Security Best Practices](https://learn.microsoft.com/en-us/azure/devops/organizations/security/security-best-practices)
- [Build Service Account Permissions](https://learn.microsoft.com/en-us/azure/devops/pipelines/process/access-tokens)
- [Personal Access Tokens](https://learn.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate)

## Quick Reference Commands

### Check Current Permissions (REST API)
```bash
# Replace with your values
ORG_URL="https://azdo.simbrella.pro/DefaultCollection"
PROJECT="SalaryNow"
REPO="salarynow-core"
PAT="your-pat-token"

# Get repository security namespaces
curl -u ":$PAT" "$ORG_URL/$PROJECT/_apis/git/repositories/$REPO/security?api-version=7.0"
```

### Pipeline Variable to Use
```yaml
variables:
  - name: System.Debug
    value: true  # Enable for troubleshooting
```

## Support

If you continue experiencing issues after following this guide:

1. Check Azure DevOps service health
2. Review pipeline logs with DEBUG level logging
3. Contact your Azure DevOps administrator
4. Open an issue in the extension repository

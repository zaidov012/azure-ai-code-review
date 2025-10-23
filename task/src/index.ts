/**
 * Azure Pipelines Task: AI Code Review
 * 
 * This task orchestrates AI-powered code review for pull requests.
 * It executes the Python review script with configured parameters.
 */

import * as tl from 'azure-pipelines-task-lib/task';
import * as path from 'path';
import * as fs from 'fs';

interface TaskInputs {
    configPath?: string;
    llmProvider?: string;
    llmModel?: string;
    llmApiKey?: string;
    llmApiBase?: string;
    llmApiVersion?: string;
    llmTimeout?: string;
    reviewScope: string[];
    fileExtensions: string[];
    excludePatterns: string[];
    quickMode: boolean;
    postComments: boolean;
    postSummary: boolean;
    commentStyle: string;
    maxIssuesPerFile: number;
    pythonVersion: string;
    logLevel: string;
}

/**
 * Get and validate task inputs
 */
function getInputs(): TaskInputs {
    const configPath = tl.getInput('configPath', false);
    
    // LLM Configuration
    const llmProvider = tl.getInput('llmProvider', false);
    const llmModel = tl.getInput('llmModel', false);
    const llmApiKey = tl.getInput('llmApiKey', false);
    const llmApiBase = tl.getInput('llmApiBase', false);
    const llmApiVersion = tl.getInput('llmApiVersion', false);
    const llmTimeout = tl.getInput('llmTimeout', false);
    
    // Review Configuration
    const reviewScopeInput = tl.getInput('reviewScope', false) || '';
    const reviewScope = reviewScopeInput.split('\n').filter(s => s.trim());
    
    const fileExtensionsInput = tl.getInput('fileExtensions', false) || '';
    const fileExtensions = fileExtensionsInput.split('\n').filter(s => s.trim());
    
    const excludePatternsInput = tl.getInput('excludePatterns', false) || '';
    const excludePatterns = excludePatternsInput.split('\n').filter(s => s.trim());
    
    const quickMode = tl.getBoolInput('quickMode', false);
    const postComments = tl.getBoolInput('postComments', false);
    const postSummary = tl.getBoolInput('postSummary', false);
    const commentStyle = tl.getInput('commentStyle', false) || 'constructive';
    const maxIssuesPerFile = parseInt(tl.getInput('maxIssuesPerFile', false) || '10');
    
    // Runtime Configuration
    const pythonVersion = tl.getInput('pythonVersion', false) || '3.8';
    const logLevel = tl.getInput('logLevel', false) || 'INFO';
    
    return {
        configPath,
        llmProvider,
        llmModel,
        llmApiKey,
        llmApiBase,
        llmApiVersion,
        llmTimeout,
        reviewScope,
        fileExtensions,
        excludePatterns,
        quickMode,
        postComments,
        postSummary,
        commentStyle,
        maxIssuesPerFile,
        pythonVersion,
        logLevel
    };
}

/**
 * Check if running in a pull request context
 */
function validatePRContext(): { prId: number } {
    const prId = tl.getVariable('System.PullRequest.PullRequestId');
    
    if (!prId) {
        throw new Error('This task must run in a pull request build. System.PullRequest.PullRequestId is not set.');
    }

    
    return {
        prId: parseInt(prId)
    };
}

/**
 * Find Python executable
 */
async function findPython(preferredVersion: string): Promise<string> {
    // Try version-specific python first
    const pythonVersioned = `python${preferredVersion}`;
    const pythonVersionedPath = tl.which(pythonVersioned, false);
    if (pythonVersionedPath) {
        tl.debug(`Found ${pythonVersioned} at ${pythonVersionedPath}`);
        return pythonVersionedPath;
    }
    
    // Try generic python3
    const python3Path = tl.which('python3', false);
    if (python3Path) {
        tl.debug(`Found python3 at ${python3Path}`);
        return python3Path;
    }
    
    // Try python
    const pythonPath = tl.which('python', false);
    if (pythonPath) {
        tl.debug(`Found python at ${pythonPath}`);
        return pythonPath;
    }
    
    throw new Error(`Python ${preferredVersion} not found. Please install Python ${preferredVersion} or later.`);
}

/**
 * Install Python dependencies
 */
async function installDependencies(python: string): Promise<void> {
    tl.debug('Installing Python dependencies...');
    
    // Look for requirements.txt in task directory (packaged with VSIX)
    const requirementsPath = path.join(__dirname, '..', 'requirements.txt');
    
    if (!fs.existsSync(requirementsPath)) {
        tl.warning(`requirements.txt not found at ${requirementsPath}. Skipping dependency installation.`);
        return;
    }
    
    const pip = tl.tool(python);
    pip.arg(['-m', 'pip', 'install', '--upgrade', 'pip']);
    await pip.exec();
    
    const pipInstall = tl.tool(python);
    pipInstall.arg(['-m', 'pip', 'install', '-r', requirementsPath]);
    await pipInstall.exec();
    
    tl.debug('Dependencies installed successfully.');
}

/**
 * Set environment variables from task inputs
 */
function setEnvironmentVariables(inputs: TaskInputs): void {
    // Azure DevOps variables
    const orgUrl = tl.getVariable('System.TeamFoundationCollectionUri');
    const project = tl.getVariable('System.TeamProject');
    const repository = tl.getVariable('Build.Repository.Name');
    const accessToken = tl.getVariable('System.AccessToken');
    
    if (orgUrl) process.env.AZDO_ORG_URL = orgUrl;
    if (project) process.env.AZDO_PROJECT = project;
    if (repository) process.env.AZDO_REPOSITORY = repository;
    
    // Only use System.AccessToken if AZDO_PERSONAL_ACCESS_TOKEN is not already set
    // This allows users to provide their own PAT token which takes priority
    if (!process.env.AZDO_PERSONAL_ACCESS_TOKEN && accessToken) {
        process.env.AZDO_PERSONAL_ACCESS_TOKEN = accessToken;
        tl.debug('Using System.AccessToken for authentication');
    } else if (process.env.AZDO_PERSONAL_ACCESS_TOKEN) {
        tl.debug('Using provided PAT token for authentication');
    }
    
    // LLM Configuration
    if (inputs.llmProvider) process.env.LLM_PROVIDER = inputs.llmProvider;
    if (inputs.llmModel) process.env.LLM_MODEL = inputs.llmModel;
    if (inputs.llmApiKey) process.env.LLM_API_KEY = inputs.llmApiKey;
    if (inputs.llmApiBase) process.env.LLM_API_BASE = inputs.llmApiBase;
    if (inputs.llmApiVersion) process.env.LLM_API_VERSION = inputs.llmApiVersion;
    if (inputs.llmTimeout) process.env.LLM_TIMEOUT = inputs.llmTimeout;
    
    // Review Configuration
    if (inputs.reviewScope.length > 0) {
        process.env.REVIEW_SCOPE = inputs.reviewScope.join(',');
    }
    if (inputs.fileExtensions.length > 0) {
        process.env.FILE_EXTENSIONS = inputs.fileExtensions.join(',');
    }
    if (inputs.excludePatterns.length > 0) {
        process.env.EXCLUDE_PATTERNS = inputs.excludePatterns.join(',');
    }
    
    process.env.QUICK_MODE = inputs.quickMode.toString();
    process.env.POST_COMMENTS = inputs.postComments.toString();
    process.env.POST_SUMMARY = inputs.postSummary.toString();
    process.env.COMMENT_STYLE = inputs.commentStyle;
    process.env.MAX_ISSUES_PER_FILE = inputs.maxIssuesPerFile.toString();
    process.env.LOG_LEVEL = inputs.logLevel;
    
    tl.debug('Environment variables set.');
}

/**
 * Execute Python review script
 */
async function executeReview(python: string, inputs: TaskInputs, prContext: { prId: number }): Promise<void> {
    tl.debug('Executing AI code review...');
    
    // Look for script in task directory (packaged with VSIX)
    const scriptPath = path.join(__dirname, '..', 'scripts', 'review_pr.py');
    
    if (!fs.existsSync(scriptPath)) {
        throw new Error(`Review script not found at ${scriptPath}`);
    }
    
    // Set PYTHONPATH to include the src_python directory
    const srcPythonPath = path.join(__dirname, '..', 'src_python');
    const currentPythonPath = process.env.PYTHONPATH || '';
    process.env.PYTHONPATH = currentPythonPath ? `${srcPythonPath}:${currentPythonPath}` : srcPythonPath;
    
    const pythonTool = tl.tool(python);
    pythonTool.arg(scriptPath);
    pythonTool.arg(['--pr-id', prContext.prId.toString()]);
    
    if (inputs.configPath) {
        pythonTool.arg(['--config', inputs.configPath]);
    }
    
    const exitCode = await pythonTool.exec();
    
    if (exitCode !== 0) {
        throw new Error(`AI code review failed with exit code ${exitCode}`);
    }
    
    tl.debug('AI code review completed successfully.');
}

/**
 * Parse review results and set output variables
 */
function setOutputVariables(): void {
    // These would be set by the Python script
    const summary = process.env.AI_REVIEW_SUMMARY;
    const issueCount = process.env.AI_REVIEW_ISSUE_COUNT;
    const criticalCount = process.env.AI_REVIEW_CRITICAL_COUNT;
    
    if (summary) {
        tl.setVariable('AI_REVIEW_SUMMARY', summary);
        console.log(`\n📊 Review Summary:\n${summary}\n`);
    }
    
    if (issueCount) {
        tl.setVariable('AI_REVIEW_ISSUE_COUNT', issueCount);
        console.log(`📋 Total Issues: ${issueCount}`);
    }
    
    if (criticalCount) {
        tl.setVariable('AI_REVIEW_CRITICAL_COUNT', criticalCount);
        console.log(`🔴 Critical Issues: ${criticalCount}`);
        
        // Optionally fail build if critical issues found
        const failOnCritical = tl.getVariable('FAIL_ON_CRITICAL_ISSUES');
        if (failOnCritical === 'true' && parseInt(criticalCount) > 0) {
            tl.setResult(tl.TaskResult.Failed, `Found ${criticalCount} critical issues.`);
            return;
        }
    }
}

/**
 * Main execution function
 */
async function run(): Promise<void> {
    try {
        console.log('🤖 AI Code Review Task Starting...\n');
        
        // Get inputs
        const inputs = getInputs();
        tl.debug('Task inputs loaded.');
        
        // Validate PR context
        const prContext = validatePRContext();
        console.log(`✓ Running in PR context: PR #${prContext.prId}`);
        
        // Find Python
        const python = await findPython(inputs.pythonVersion);
        console.log(`✓ Python found: ${python}`);
        
        // Install dependencies
        await installDependencies(python);
        console.log('✓ Dependencies installed');
        
        // Set environment variables
        setEnvironmentVariables(inputs);
        console.log('✓ Environment configured');
        
        // Execute review
        console.log('\n🔍 Starting AI code review...\n');
        await executeReview(python, inputs, prContext);
        console.log('\n✓ AI code review completed');
        
        // Set output variables
        setOutputVariables();
        
        console.log('\n✅ AI Code Review Task Completed Successfully\n');
        tl.setResult(tl.TaskResult.Succeeded, 'AI code review completed.');
        
    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        console.error(`\n❌ Task failed: ${errorMessage}\n`);
        tl.setResult(tl.TaskResult.Failed, errorMessage);
    }
}

// Execute
run();

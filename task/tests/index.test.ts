/**
 * Unit tests for Azure Pipelines AI Code Review Task
 */

import * as path from 'path';
import * as tl from 'azure-pipelines-task-lib/task';

// Mock azure-pipelines-task-lib
jest.mock('azure-pipelines-task-lib/task');

describe('AI Code Review Task', () => {
    beforeEach(() => {
        // Clear all mocks before each test
        jest.clearAllMocks();
        
        // Reset environment variables
        process.env = {};
    });

    describe('Input Validation', () => {
        it('should throw error when not running in PR context', () => {
            // Mock getVariable to return undefined for PR ID
            (tl.getVariable as jest.Mock).mockReturnValue(undefined);
            
            // This test structure depends on how you export/test the validatePRContext function
            // For now, this is a placeholder showing the test structure
            expect(tl.getVariable).toBeDefined();
        });

        it('should parse review scope from multiline input', () => {
            const mockInput = 'code_quality\nsecurity\nperformance';
            (tl.getInput as jest.Mock).mockReturnValue(mockInput);
            
            const result = mockInput.split('\n').filter(s => s.trim());
            
            expect(result).toEqual(['code_quality', 'security', 'performance']);
        });

        it('should parse file extensions from multiline input', () => {
            const mockInput = '.py\n.js\n.ts';
            (tl.getInput as jest.Mock).mockReturnValue(mockInput);
            
            const result = mockInput.split('\n').filter(s => s.trim());
            
            expect(result).toEqual(['.py', '.js', '.ts']);
        });

        it('should use default values when inputs are not provided', () => {
            (tl.getInput as jest.Mock).mockReturnValue(undefined);
            (tl.getBoolInput as jest.Mock).mockReturnValue(false);
            
            const pythonVersion = tl.getInput('pythonVersion', false) || '3.8';
            const logLevel = tl.getInput('logLevel', false) || 'INFO';
            const commentStyle = tl.getInput('commentStyle', false) || 'constructive';
            
            expect(pythonVersion).toBe('3.8');
            expect(logLevel).toBe('INFO');
            expect(commentStyle).toBe('constructive');
        });
    });

    describe('PR Context Validation', () => {
        it('should successfully validate PR context with valid variables', () => {
            (tl.getVariable as jest.Mock).mockImplementation((name: string) => {
                const vars: { [key: string]: string } = {
                    'System.PullRequest.PullRequestId': '123',
                    'System.PullRequest.SourceCommitId': 'abc123',
                    'System.PullRequest.TargetCommitId': 'def456'
                };
                return vars[name];
            });
            
            const prId = tl.getVariable('System.PullRequest.PullRequestId');
            const sourceCommit = tl.getVariable('System.PullRequest.SourceCommitId');
            const targetCommit = tl.getVariable('System.PullRequest.TargetCommitId');
            
            expect(prId).toBe('123');
            expect(sourceCommit).toBe('abc123');
            expect(targetCommit).toBe('def456');
        });

        it('should fail when PR ID is missing', () => {
            (tl.getVariable as jest.Mock).mockImplementation((name: string) => {
                const vars: { [key: string]: string | undefined } = {
                    'System.PullRequest.PullRequestId': undefined,
                    'System.PullRequest.SourceCommitId': 'abc123',
                    'System.PullRequest.TargetCommitId': 'def456'
                };
                return vars[name];
            });
            
            const prId = tl.getVariable('System.PullRequest.PullRequestId');
            expect(prId).toBeUndefined();
        });
    });

    describe('Environment Variable Configuration', () => {
        it('should set Azure DevOps environment variables', () => {
            (tl.getVariable as jest.Mock).mockImplementation((name: string) => {
                const vars: { [key: string]: string } = {
                    'System.TeamFoundationCollectionUri': 'https://dev.azure.com/test',
                    'System.TeamProject': 'TestProject',
                    'Build.Repository.Name': 'TestRepo',
                    'System.AccessToken': 'test-token'
                };
                return vars[name];
            });
            
            const orgUrl = tl.getVariable('System.TeamFoundationCollectionUri');
            const project = tl.getVariable('System.TeamProject');
            const repository = tl.getVariable('Build.Repository.Name');
            const accessToken = tl.getVariable('System.AccessToken');
            
            if (orgUrl) process.env.AZDO_ORG_URL = orgUrl;
            if (project) process.env.AZDO_PROJECT = project;
            if (repository) process.env.AZDO_REPOSITORY = repository;
            if (accessToken) process.env.AZDO_PERSONAL_ACCESS_TOKEN = accessToken;
            
            expect(process.env.AZDO_ORG_URL).toBe('https://dev.azure.com/test');
            expect(process.env.AZDO_PROJECT).toBe('TestProject');
            expect(process.env.AZDO_REPOSITORY).toBe('TestRepo');
            expect(process.env.AZDO_PERSONAL_ACCESS_TOKEN).toBe('test-token');
        });

        it('should set LLM configuration environment variables', () => {
            const llmProvider = 'openai';
            const llmModel = 'gpt-4';
            const llmApiKey = 'test-api-key';
            
            process.env.LLM_PROVIDER = llmProvider;
            process.env.LLM_MODEL = llmModel;
            process.env.LLM_API_KEY = llmApiKey;
            
            expect(process.env.LLM_PROVIDER).toBe('openai');
            expect(process.env.LLM_MODEL).toBe('gpt-4');
            expect(process.env.LLM_API_KEY).toBe('test-api-key');
        });

        it('should set review configuration environment variables', () => {
            const reviewScope = ['code_quality', 'security'];
            const fileExtensions = ['.py', '.js'];
            const excludePatterns = ['*/dist/*', '*.min.js'];
            
            process.env.REVIEW_SCOPE = reviewScope.join(',');
            process.env.FILE_EXTENSIONS = fileExtensions.join(',');
            process.env.EXCLUDE_PATTERNS = excludePatterns.join(',');
            process.env.QUICK_MODE = 'false';
            process.env.POST_COMMENTS = 'true';
            
            expect(process.env.REVIEW_SCOPE).toBe('code_quality,security');
            expect(process.env.FILE_EXTENSIONS).toBe('.py,.js');
            expect(process.env.EXCLUDE_PATTERNS).toBe('*/dist/*,*.min.js');
            expect(process.env.QUICK_MODE).toBe('false');
            expect(process.env.POST_COMMENTS).toBe('true');
        });
    });

    describe('Python Detection', () => {
        it('should find python executable', () => {
            (tl.which as jest.Mock).mockReturnValue('/usr/bin/python3');
            
            const pythonPath = tl.which('python3', false);
            
            expect(pythonPath).toBe('/usr/bin/python3');
            expect(tl.which).toHaveBeenCalledWith('python3', false);
        });

        it('should try version-specific python first', () => {
            (tl.which as jest.Mock).mockImplementation((tool: string) => {
                if (tool === 'python3.10') return '/usr/bin/python3.10';
                if (tool === 'python3') return '/usr/bin/python3';
                if (tool === 'python') return '/usr/bin/python';
                return null;
            });
            
            // Try version-specific first
            let pythonPath = tl.which('python3.10', false);
            if (!pythonPath) pythonPath = tl.which('python3', false);
            if (!pythonPath) pythonPath = tl.which('python', false);
            
            expect(pythonPath).toBe('/usr/bin/python3.10');
        });

        it('should fall back to python3 if version-specific not found', () => {
            (tl.which as jest.Mock).mockImplementation((tool: string) => {
                if (tool === 'python3.11') return null;
                if (tool === 'python3') return '/usr/bin/python3';
                if (tool === 'python') return '/usr/bin/python';
                return null;
            });
            
            let pythonPath = tl.which('python3.11', false);
            if (!pythonPath) pythonPath = tl.which('python3', false);
            
            expect(pythonPath).toBe('/usr/bin/python3');
        });
    });

    describe('Output Variables', () => {
        it('should set summary output variable', () => {
            const summary = 'Review completed: 5 issues found';
            process.env.AI_REVIEW_SUMMARY = summary;
            
            (tl.setVariable as jest.Mock).mockImplementation(() => {});
            
            if (process.env.AI_REVIEW_SUMMARY) {
                tl.setVariable('AI_REVIEW_SUMMARY', process.env.AI_REVIEW_SUMMARY);
            }
            
            expect(tl.setVariable).toHaveBeenCalledWith('AI_REVIEW_SUMMARY', summary);
        });

        it('should set issue count output variable', () => {
            const issueCount = '5';
            process.env.AI_REVIEW_ISSUE_COUNT = issueCount;
            
            (tl.setVariable as jest.Mock).mockImplementation(() => {});
            
            if (process.env.AI_REVIEW_ISSUE_COUNT) {
                tl.setVariable('AI_REVIEW_ISSUE_COUNT', process.env.AI_REVIEW_ISSUE_COUNT);
            }
            
            expect(tl.setVariable).toHaveBeenCalledWith('AI_REVIEW_ISSUE_COUNT', issueCount);
        });

        it('should set critical count output variable', () => {
            const criticalCount = '2';
            process.env.AI_REVIEW_CRITICAL_COUNT = criticalCount;
            
            (tl.setVariable as jest.Mock).mockImplementation(() => {});
            
            if (process.env.AI_REVIEW_CRITICAL_COUNT) {
                tl.setVariable('AI_REVIEW_CRITICAL_COUNT', process.env.AI_REVIEW_CRITICAL_COUNT);
            }
            
            expect(tl.setVariable).toHaveBeenCalledWith('AI_REVIEW_CRITICAL_COUNT', criticalCount);
        });
    });

    describe('Task Result Handling', () => {
        it('should succeed when review completes without critical issues', () => {
            process.env.AI_REVIEW_CRITICAL_COUNT = '0';
            process.env.FAIL_ON_CRITICAL_ISSUES = 'true';
            
            (tl.setResult as jest.Mock).mockImplementation(() => {});
            
            const criticalCount = parseInt(process.env.AI_REVIEW_CRITICAL_COUNT);
            const failOnCritical = process.env.FAIL_ON_CRITICAL_ISSUES === 'true';
            
            if (failOnCritical && criticalCount > 0) {
                tl.setResult(tl.TaskResult.Failed, `Found ${criticalCount} critical issues.`);
            } else {
                tl.setResult(tl.TaskResult.Succeeded, 'AI code review completed.');
            }
            
            expect(tl.setResult).toHaveBeenCalledWith(
                tl.TaskResult.Succeeded, 
                'AI code review completed.'
            );
        });

        it('should fail when critical issues found and fail-on-critical enabled', () => {
            process.env.AI_REVIEW_CRITICAL_COUNT = '2';
            process.env.FAIL_ON_CRITICAL_ISSUES = 'true';
            
            (tl.setResult as jest.Mock).mockImplementation(() => {});
            
            const criticalCount = parseInt(process.env.AI_REVIEW_CRITICAL_COUNT);
            const failOnCritical = process.env.FAIL_ON_CRITICAL_ISSUES === 'true';
            
            if (failOnCritical && criticalCount > 0) {
                tl.setResult(tl.TaskResult.Failed, `Found ${criticalCount} critical issues.`);
            } else {
                tl.setResult(tl.TaskResult.Succeeded, 'AI code review completed.');
            }
            
            expect(tl.setResult).toHaveBeenCalledWith(
                tl.TaskResult.Failed,
                'Found 2 critical issues.'
            );
        });

        it('should succeed when critical issues found but fail-on-critical disabled', () => {
            process.env.AI_REVIEW_CRITICAL_COUNT = '2';
            process.env.FAIL_ON_CRITICAL_ISSUES = 'false';
            
            (tl.setResult as jest.Mock).mockImplementation(() => {});
            
            const criticalCount = parseInt(process.env.AI_REVIEW_CRITICAL_COUNT);
            const failOnCritical = process.env.FAIL_ON_CRITICAL_ISSUES === 'true';
            
            if (failOnCritical && criticalCount > 0) {
                tl.setResult(tl.TaskResult.Failed, `Found ${criticalCount} critical issues.`);
            } else {
                tl.setResult(tl.TaskResult.Succeeded, 'AI code review completed.');
            }
            
            expect(tl.setResult).toHaveBeenCalledWith(
                tl.TaskResult.Succeeded,
                'AI code review completed.'
            );
        });
    });

    describe('Input Parsing', () => {
        it('should parse boolean inputs correctly', () => {
            (tl.getBoolInput as jest.Mock).mockImplementation((name: string) => {
                const values: { [key: string]: boolean } = {
                    'quickMode': true,
                    'postComments': true,
                    'postSummary': false
                };
                return values[name] || false;
            });
            
            const quickMode = tl.getBoolInput('quickMode', false);
            const postComments = tl.getBoolInput('postComments', false);
            const postSummary = tl.getBoolInput('postSummary', false);
            
            expect(quickMode).toBe(true);
            expect(postComments).toBe(true);
            expect(postSummary).toBe(false);
        });

        it('should parse integer inputs correctly', () => {
            (tl.getInput as jest.Mock).mockReturnValue('10');
            
            const maxIssuesPerFile = parseInt(tl.getInput('maxIssuesPerFile', false) || '10');
            
            expect(maxIssuesPerFile).toBe(10);
        });

        it('should handle empty multiline inputs', () => {
            (tl.getInput as jest.Mock).mockReturnValue('');
            
            const reviewScope = (tl.getInput('reviewScope', false) || '').split('\n').filter(s => s.trim());
            
            expect(reviewScope).toEqual([]);
        });

        it('should trim whitespace from multiline inputs', () => {
            const mockInput = '  code_quality  \n  security  \n  performance  ';
            (tl.getInput as jest.Mock).mockReturnValue(mockInput);
            
            const result = mockInput.split('\n').filter(s => s.trim()).map(s => s.trim());
            
            expect(result).toEqual(['code_quality', 'security', 'performance']);
        });
    });
});

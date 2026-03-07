# Plugin Examples

Collection of example plugins demonstrating various features and use cases.

## Table of Contents

- [Agent Plugin Examples](#agent-plugin-examples)
  - [Custom Code Reviewer Agent](#custom-code-reviewer-agent)
  - [Security Scanner Agent](#security-scanner-agent)
  - [Documentation Generator Agent](#documentation-generator-agent)
- [Task Source Plugin Examples](#task-source-plugin-examples)
  - [File-Based Task Source](#file-based-task-source)
  - [GitHub Issues Task Source](#github-issues-task-source)
  - [Jira Task Source](#jira-task-source)
- [Integration Plugin Examples](#integration-plugin-examples)
  - [Slack Notification Integration](#slack-notification-integration)
  - [GitHub Webhook Integration](#github-webhook-integration)
  - [Jenkins CI/CD Integration](#jenkins-cicd-integration)

---

## Agent Plugin Examples

### Custom Code Reviewer Agent

A specialized agent for code review with custom prompts and behavior.

**File:** `custom-code-reviewer/plugin.py`

```python
"""
Custom Code Reviewer Agent Plugin.

This plugin provides a specialized code reviewer agent with custom
behavior for analyzing code quality, security, and performance.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from devflow.plugins.agent_plugin import AgentPlugin
from devflow.plugins.base import PluginMetadata


logger = logging.getLogger(__name__)


class CodeReviewerAgent:
    """Code reviewer agent implementation."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.agent_id = None
        self.review_rules = config.get('review_rules', [])

    def execute(self, task: str, code: str = None) -> Dict[str, Any]:
        """Execute a code review task."""
        review_result = {
            'timestamp': datetime.now().isoformat(),
            'task': task,
            'issues': [],
            'suggestions': [],
            'score': 0
        }

        # Analyze code if provided
        if code:
            review_result['issues'] = self._find_issues(code)
            review_result['suggestions'] = self._generate_suggestions(code)
            review_result['score'] = self._calculate_score(code)

        return review_result

    def _find_issues(self, code: str) -> list:
        """Find code issues."""
        issues = []
        # Simplified issue detection
        if 'TODO' in code:
            issues.append({
                'type': 'warning',
                'message': 'Code contains TODO comments'
            })
        if 'print(' in code:
            issues.append({
                'type': 'style',
                'message': 'Consider using logging instead of print'
            })
        return issues

    def _generate_suggestions(self, code: str) -> list:
        """Generate improvement suggestions."""
        return [
            'Consider adding type hints',
            'Add docstrings to functions',
            'Implement error handling'
        ]

    def _calculate_score(self, code: str) -> int:
        """Calculate code quality score."""
        score = 100
        if 'TODO' in code:
            score -= 10
        if 'print(' in code:
            score -= 5
        return max(0, score)


class CustomCodeReviewerPlugin(AgentPlugin):
    """Custom code reviewer agent plugin."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="custom-code-reviewer",
            version="1.0.0",
            description="Specialized code reviewer agent with custom analysis",
            author="DevFlow Team",
            plugin_type="agent",
            dependencies=[],
            devflow_version="0.1.0"
        )

    def get_agent_type(self) -> str:
        return "code-reviewer"

    def get_agent_class(self):
        return CodeReviewerAgent

    def get_agent_config(self) -> Dict[str, Any]:
        return {
            "model": "claude-3-5-sonnet-20241022",
            "max_tasks": 5,
            "timeout": 1800,
            "skills": [
                "code-review",
                "security-analysis",
                "performance-analysis",
                "style-check"
            ],
            "system_prompt": """You are an expert code reviewer with deep knowledge of:
- Software architecture and design patterns
- Security best practices and vulnerability detection
- Performance optimization techniques
- Code maintainability and readability

When reviewing code:
1. Identify potential bugs and edge cases
2. Suggest improvements for performance and readability
3. Check for security vulnerabilities
4. Verify adherence to coding standards
5. Provide clear, actionable feedback

Be constructive and educational in your feedback.""",
            "temperature": 0.3,
            "max_tokens": 4000,
            "review_rules": [
                "check_security",
                "check_performance",
                "check_style",
                "check_documentation"
            ]
        }

    def on_agent_created(self, agent_id: str, agent_type: str) -> None:
        if agent_type == self.get_agent_type():
            logger.info(f"Code reviewer agent created: {agent_id}")

    def on_agent_completed(self, agent_id: str, result: Any) -> None:
        if isinstance(result, dict) and 'score' in result:
            score = result['score']
            logger.info(f"Code review completed with score: {score}/100")
```

**Usage:**

```python
from devflow.plugins.plugin_manager import PluginManager

manager = PluginManager()
result = manager.load_plugin_from_path("./custom-code-reviewer")

if result.success:
    manager.start_plugin(result.plugin_name)

    # Get the agent
    plugin = manager.get_plugin(result.plugin_name)
    agent_config = plugin.get_agent_config()

    print(f"Agent Type: {plugin.get_agent_type()}")
    print(f"Skills: {agent_config['skills']}")
```

---

### Security Scanner Agent

An agent specialized in security vulnerability scanning.

**File:** `security-scanner/plugin.py`

```python
"""
Security Scanner Agent Plugin.

Provides automated security scanning capabilities for code and dependencies.
"""

import logging
import re
from typing import Dict, Any, List
from datetime import datetime

from devflow.plugins.agent_plugin import AgentPlugin
from devflow.plugins.base import PluginMetadata


logger = logging.getLogger(__name__)


class SecurityScannerAgent:
    """Security scanner agent implementation."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.vulnerability_db = config.get('vulnerability_db', [])

    def scan(self, target: str) -> Dict[str, Any]:
        """Scan target for security vulnerabilities."""
        return {
            'timestamp': datetime.now().isoformat(),
            'target': target,
            'vulnerabilities': self._scan_vulnerabilities(target),
            'risk_score': self._calculate_risk_score(target)
        }

    def _scan_vulnerabilities(self, code: str) -> List[Dict[str, Any]]:
        """Scan code for known vulnerability patterns."""
        vulnerabilities = []

        # Check for hardcoded secrets
        secret_patterns = [
            (r'password\s*=\s*["\'].+["\']', 'hardcoded_password'),
            (r'api_key\s*=\s*["\'].+["\']', 'hardcoded_api_key'),
            (r'token\s*=\s*["\'].+["\']', 'hardcoded_token'),
        ]

        for pattern, vuln_type in secret_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                vulnerabilities.append({
                    'type': vuln_type,
                    'severity': 'HIGH',
                    'description': f'Potential {vuln_type} detected'
                })

        # Check for SQL injection risks
        if re.search(r'execute\(.+\+.+|query\(.+\+.', code):
            vulnerabilities.append({
                'type': 'sql_injection',
                'severity': 'CRITICAL',
                'description': 'Potential SQL injection vulnerability'
            })

        return vulnerabilities

    def _calculate_risk_score(self, code: str) -> int:
        """Calculate security risk score."""
        vulnerabilities = self._scan_vulnerabilities(code)
        score = 0
        for vuln in vulnerabilities:
            if vuln['severity'] == 'CRITICAL':
                score += 10
            elif vuln['severity'] == 'HIGH':
                score += 7
            elif vuln['severity'] == 'MEDIUM':
                score += 5
            elif vuln['severity'] == 'LOW':
                score += 2
        return min(100, score)


class SecurityScannerPlugin(AgentPlugin):
    """Security scanner agent plugin."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="security-scanner",
            version="1.0.0",
            description="Automated security vulnerability scanner",
            author="DevFlow Team",
            plugin_type="agent",
            dependencies=[],
            devflow_version="0.1.0"
        )

    def get_agent_type(self) -> str:
        return "security-scanner"

    def get_agent_class(self):
        return SecurityScannerAgent

    def get_agent_config(self) -> Dict[str, Any]:
        return {
            "model": "claude-3-5-sonnet-20241022",
            "max_tasks": 3,
            "timeout": 3600,
            "skills": [
                "security-scan",
                "vulnerability-detection",
                "secret-detection",
                "dependency-analysis"
            ],
            "system_prompt": """You are a security expert specializing in:
- Application security vulnerabilities
- OWASP Top 10 vulnerabilities
- Secret and credential detection
- Dependency vulnerability analysis

When scanning code:
1. Identify security vulnerabilities
2. Assess risk severity (CRITICAL, HIGH, MEDIUM, LOW)
3. Provide remediation recommendations
4. Suggest security best practices

Report findings clearly with severity levels and actionable fixes.""",
            "vulnerability_db": [
                # Known vulnerability patterns
            ]
        }
```

---

### Documentation Generator Agent

An agent that automatically generates documentation from code.

**File:** `documentation-generator/plugin.py`

```python
"""
Documentation Generator Agent Plugin.

Automatically generates documentation from code and project structure.
"""

import logging
import ast
from typing import Dict, Any, List
from datetime import datetime

from devflow.plugins.agent_plugin import AgentPlugin
from devflow.plugins.base import PluginMetadata


logger = logging.getLogger(__name__)


class DocumentationGeneratorAgent:
    """Documentation generator agent implementation."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.output_format = config.get('output_format', 'markdown')

    def generate_docs(self, code: str, filename: str = None) -> Dict[str, Any]:
        """Generate documentation from code."""
        return {
            'timestamp': datetime.now().isoformat(),
            'filename': filename,
            'documentation': self._parse_and_generate(code),
            'format': self.output_format
        }

    def _parse_and_generate(self, code: str) -> str:
        """Parse code and generate documentation."""
        try:
            tree = ast.parse(code)
            docs = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    docs.append(self._document_function(node))
                elif isinstance(node, ast.ClassDef):
                    docs.append(self._document_class(node))

            return '\n\n'.join(docs)
        except Exception as e:
            logger.error(f"Error generating docs: {e}")
            return f"Error generating documentation: {e}"

    def _document_function(self, node: ast.FunctionDef) -> str:
        """Generate documentation for a function."""
        doc = f"### Function: `{node.name}`\n\n"
        doc += f"**Line:** {node.lineno}\n\n"

        # Get docstring
        if node.body and isinstance(node.body[0], ast.Expr):
            docstring = ast.get_docstring(node)
            if docstring:
                doc += f"{docstring}\n\n"

        # Get parameters
        args = [arg.arg for arg in node.args.args]
        if args:
            doc += "**Parameters:**\n"
            for arg in args:
                doc += f"- `{arg}`\n"

        return doc

    def _document_class(self, node: ast.ClassDef) -> str:
        """Generate documentation for a class."""
        doc = f"## Class: `{node.name}`\n\n"
        doc += f"**Line:** {node.lineno}\n\n"

        # Get docstring
        docstring = ast.get_docstring(node)
        if docstring:
            doc += f"{docstring}\n\n"

        # List methods
        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        if methods:
            doc += "**Methods:**\n"
            for method in methods:
                doc += f"- `{method.name}()`\n"

        return doc


class DocumentationGeneratorPlugin(AgentPlugin):
    """Documentation generator agent plugin."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="documentation-generator",
            version="1.0.0",
            description="Automatic documentation generator from code",
            author="DevFlow Team",
            plugin_type="agent",
            dependencies=[],
            devflow_version="0.1.0"
        )

    def get_agent_type(self) -> str:
        return "documentation-generator"

    def get_agent_class(self):
        return DocumentationGeneratorAgent

    def get_agent_config(self) -> Dict[str, Any]:
        return {
            "model": "claude-3-5-sonnet-20241022",
            "max_tasks": 10,
            "timeout": 1800,
            "skills": [
                "documentation-generation",
                "code-parsing",
                "markdown-generation"
            ],
            "system_prompt": """You are a documentation specialist with expertise in:
- Technical writing
- Code documentation best practices
- Markdown and structured documentation
- API documentation standards

When generating documentation:
1. Analyze code structure and functionality
2. Extract key information from docstrings
3. Create clear, organized documentation
4. Include usage examples where helpful
5. Follow documentation best practices

Generate comprehensive, easy-to-understand documentation.""",
            "output_format": "markdown"
        }
```

---

## Task Source Plugin Examples

### File-Based Task Source

Fetch tasks from JSON files in a directory.

**File:** `file-task-source/plugin.py`

```python
"""
File-Based Task Source Plugin.

Fetches tasks from JSON files in a specified directory.
"""

import logging
import json
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

from devflow.plugins.task_source_plugin import TaskSourcePlugin
from devflow.plugins.base import PluginMetadata


logger = logging.getLogger(__name__)


class FileTaskSourcePlugin(TaskSourcePlugin):
    """Task source that reads tasks from JSON files."""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.task_dir = Path(self.config.get('task_dir', './tasks'))
        self.file_pattern = self.config.get('file_pattern', '*.json')
        self._processed_tasks = set()

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="file-task-source",
            version="1.0.0",
            description="Fetch tasks from JSON files in a directory",
            author="DevFlow Team",
            plugin_type="task_source",
            dependencies=[],
            devflow_version="0.1.0"
        )

    def get_source_name(self) -> str:
        return "file-tasks"

    def get_polling_interval(self) -> int:
        return self.config.get('polling_interval', 60)

    def fetch_tasks(self) -> List[Dict[str, Any]]:
        tasks = []

        if not self.task_dir.exists():
            logger.warning(f"Task directory does not exist: {self.task_dir}")
            return tasks

        for task_file in self.task_dir.glob(self.file_pattern):
            try:
                with open(task_file, 'r') as f:
                    task_data = json.load(f)
                    task_data['_source_file'] = str(task_file)
                    tasks.append(task_data)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in {task_file}: {e}")

        logger.info(f"Fetched {len(tasks)} tasks from {self.task_dir}")
        return tasks

    def validate_task(self, task: Dict[str, Any]) -> bool:
        required_fields = ['id', 'title', 'type']
        if not all(field in task for field in required_fields):
            return False

        # Check for duplicates
        if task['id'] in self._processed_tasks:
            return False

        return True

    def transform_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        self._processed_tasks.add(task['id'])

        return {
            'id': task['id'],
            'title': task.get('title'),
            'description': task.get('description', ''),
            'type': task.get('type', 'general'),
            'priority': task.get('priority', 5),
            'agent_type': task.get('agent_type', 'general'),
            'dependencies': task.get('dependencies', []),
            'timeout': task.get('timeout', 3600),
            'input_data': {
                'source': self.get_source_name(),
                'source_file': task.get('_source_file')
            }
        }
```

**Example task file:** `tasks/example_task.json`

```json
{
  "id": "task-001",
  "title": "Implement user authentication",
  "description": "Add OAuth2 authentication to the application",
  "type": "development",
  "priority": 1,
  "agent_type": "general",
  "dependencies": [],
  "timeout": 7200
}
```

---

### GitHub Issues Task Source

Fetch tasks from GitHub Issues.

**File:** `github-issues-task-source/plugin.py`

```python
"""
GitHub Issues Task Source Plugin.

Fetches tasks from a GitHub repository's issues.
"""

import logging
import requests
from typing import Dict, Any, List
from datetime import datetime

from devflow.plugins.task_source_plugin import TaskSourcePlugin
from devflow.plugins.base import PluginMetadata


logger = logging.getLogger(__name__)


class GitHubIssuesTaskSource(TaskSourcePlugin):
    """Task source that fetches from GitHub Issues."""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.repo_owner = self.config.get('repo_owner')
        self.repo_name = self.config.get('repo_name')
        self.api_token = self.config.get('api_token')
        self.labels = self.config.get('labels', [])
        self.state = self.config.get('state', 'open')
        self.base_url = "https://api.github.com"

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="github-issues-task-source",
            version="1.0.0",
            description="Fetch tasks from GitHub Issues",
            author="DevFlow Team",
            plugin_type="task_source",
            dependencies=[],
            devflow_version="0.1.0"
        )

    def get_source_name(self) -> str:
        return "github-issues"

    def get_polling_interval(self) -> int:
        return self.config.get('polling_interval', 300)  # 5 minutes

    def fetch_tasks(self) -> List[Dict[str, Any]]:
        if not self.repo_owner or not self.repo_name:
            logger.error("GitHub repository not configured")
            return []

        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/issues"
        headers = {
            'Accept': 'application/vnd.github.v3+json'
        }

        if self.api_token:
            headers['Authorization'] = f'token {self.api_token}'

        params = {
            'state': self.state,
            'labels': ','.join(self.labels) if self.labels else None,
            'sort': 'created',
            'direction': 'desc'
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            issues = response.json()
            logger.info(f"Fetched {len(issues)} issues from GitHub")
            return [self._issue_to_task(issue) for issue in issues]

        except requests.RequestException as e:
            logger.error(f"Error fetching GitHub issues: {e}")
            return []

    def _issue_to_task(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'id': f"github-{issue['number']}",
            'title': issue['title'],
            'description': issue.get('body', ''),
            'type': self._determine_task_type(issue),
            'priority': self._determine_priority(issue),
            'agent_type': 'general',
            'dependencies': [],
            'input_data': {
                'source': self.get_source_name(),
                'github_url': issue['html_url'],
                'github_number': issue['number'],
                'github_labels': [label['name'] for label in issue.get('labels', [])],
                'github_created_at': issue['created_at'],
                'github_updated_at': issue['updated_at']
            }
        }

    def _determine_task_type(self, issue: Dict[str, Any]) -> str:
        labels = [label['name'].lower() for label in issue.get('labels', [])]

        if 'bug' in labels:
            return 'maintenance'
        elif 'enhancement' in labels or 'feature' in labels:
            return 'development'
        elif 'documentation' in labels:
            return 'documentation'
        else:
            return 'general'

    def _determine_priority(self, issue: Dict[str, Any]) -> int:
        labels = [label['name'].lower() for label in issue.get('labels', [])]

        if 'critical' in labels or 'urgent' in labels:
            return 1
        elif 'high' in labels:
            return 2
        elif 'low' in labels:
            return 8
        else:
            return 5

    def validate_task(self, task: Dict[str, Any]) -> bool:
        return all(key in task for key in ['id', 'title', 'type'])

    def transform_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        # Tasks are already in the correct format
        return task
```

---

### Jira Task Source

Fetch tasks from Jira.

**File:** `jira-task-source/plugin.py`

```python
"""
Jira Task Source Plugin.

Fetches tasks from Jira using REST API.
"""

import logging
import requests
from typing import Dict, Any, List
from datetime import datetime

from devflow.plugins.task_source_plugin import TaskSourcePlugin
from devflow.plugins.base import PluginMetadata


logger = logging.getLogger(__name__)


class JiraTaskSource(TaskSourcePlugin):
    """Task source that fetches from Jira."""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.base_url = self.config.get('base_url')
        self.username = self.config.get('username')
        self.api_token = self.config.get('api_token')
        self.jql_query = self.config.get('jql', 'project = MYPROJECT')
        self.fields = self.config.get('fields', ['summary', 'description', 'status', 'priority'])

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="jira-task-source",
            version="1.0.0",
            description="Fetch tasks from Jira",
            author="DevFlow Team",
            plugin_type="task_source",
            dependencies=[],
            devflow_version="0.1.0"
        )

    def get_source_name(self) -> str:
        return "jira"

    def get_polling_interval(self) -> int:
        return self.config.get('polling_interval', 300)

    def fetch_tasks(self) -> List[Dict[str, Any]]:
        if not self.base_url:
            logger.error("Jira base URL not configured")
            return []

        url = f"{self.base_url}/rest/api/2/search"
        auth = (self.username, self.api_token)
        headers = {'Content-Type': 'application/json'}

        params = {
            'jql': self.jql_query,
            'fields': ','.join(self.fields),
            'maxResults': 50
        }

        try:
            response = requests.get(url, auth=auth, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            issues = data.get('issues', [])

            logger.info(f"Fetched {len(issues)} issues from Jira")
            return [self._issue_to_task(issue) for issue in issues]

        except requests.RequestException as e:
            logger.error(f"Error fetching Jira issues: {e}")
            return []

    def _issue_to_task(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        fields = issue.get('fields', {})

        return {
            'id': issue['key'],
            'title': fields.get('summary', ''),
            'description': fields.get('description', ''),
            'type': self._map_issue_type(fields.get('issuetype', {})),
            'priority': self._map_priority(fields.get('priority', {})),
            'agent_type': 'general',
            'dependencies': [],
            'input_data': {
                'source': self.get_source_name(),
                'jira_url': f"{self.base_url}/browse/{issue['key']}",
                'jira_status': fields.get('status', {}).get('name', ''),
                'jira_priority': fields.get('priority', {}).get('name', ''),
                'jira_issue_type': fields.get('issuetype', {}).get('name', '')
            }
        }

    def _map_issue_type(self, issue_type: Dict[str, Any]) -> str:
        type_name = issue_type.get('name', '').lower()

        if 'bug' in type_name:
            return 'maintenance'
        elif 'story' in type_name or 'task' in type_name:
            return 'development'
        else:
            return 'general'

    def _map_priority(self, priority: Dict[str, Any]) -> int:
        priority_name = priority.get('name', '').lower()

        if 'highest' in priority_name or 'critical' in priority_name:
            return 1
        elif 'high' in priority_name:
            return 2
        elif 'medium' in priority_name:
            return 5
        elif 'low' in priority_name:
            return 8
        else:
            return 5

    def validate_task(self, task: Dict[str, Any]) -> bool:
        return all(key in task for key in ['id', 'title', 'type'])

    def transform_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        return task
```

---

## Integration Plugin Examples

### Slack Notification Integration

Send notifications to Slack channels.

**File:** `slack-integration/plugin.py`

```python
"""
Slack Notification Integration Plugin.

Sends notifications to Slack channels via webhook or API.
"""

import logging
import requests
from typing import Dict, Any, List
from datetime import datetime

from devflow.plugins.integration_plugin import IntegrationPlugin
from devflow.plugins.base import PluginMetadata


logger = logging.getLogger(__name__)


class SlackIntegration(IntegrationPlugin):
    """Slack notification integration."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="slack-integration",
            version="1.0.0",
            description="Send notifications to Slack",
            author="DevFlow Team",
            plugin_type="integration",
            dependencies=[],
            devflow_version="0.1.0"
        )

    def get_integration_name(self) -> str:
        return "slack"

    def get_integration_type(self) -> str:
        return "notification"

    def get_required_config_fields(self) -> List[str]:
        return ['webhook_url']

    def get_optional_config_fields(self) -> List[str]:
        return ['channel', 'username', 'icon_emoji']

    def connect(self) -> bool:
        if not self.validate_config():
            logger.error("Invalid Slack configuration")
            return False

        # Test webhook
        return self.test_connection()

    def test_connection(self) -> bool:
        try:
            result = self.send_notification("DevFlow Slack connection test", "info")
            return result
        except Exception as e:
            logger.error(f"Slack connection test failed: {e}")
            return False

    def send_notification(self, message: str, level: str = "info") -> bool:
        webhook_url = self.config.get('webhook_url')

        if not webhook_url:
            logger.error("Slack webhook URL not configured")
            return False

        # Format message based on level
        emoji = {
            'info': ':information_source:',
            'warning': ':warning:',
            'error': ':x:',
            'success': ':white_check_mark:'
        }.get(level, ':information_source:')

        payload = {
            'text': f"{emoji} {message}",
            'username': self.config.get('username', 'DevFlow'),
            'icon_emoji': self.config.get('icon_emoji', ':robot_face:'),
            'channel': self.config.get('channel')
        }

        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Slack notification sent: {message[:50]}...")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        # Handle incoming Slack events (if using Slack Events API)
        event_type = payload.get('type')

        if event_type == 'url_verification':
            challenge = payload.get('challenge')
            return {'success': True, 'challenge': challenge}

        return {'success': False, 'message': 'Event type not handled'}

    def get_supported_webhook_events(self) -> List[str]:
        return ['url_verification', 'message', 'app_mention']
```

---

### GitHub Webhook Integration

Handle webhooks from GitHub.

**File:** `github-webhook-integration/plugin.py`

```python
"""
GitHub Webhook Integration Plugin.

Handles webhooks from GitHub for various events.
"""

import logging
import hmac
import hashlib
from typing import Dict, Any, List

from devflow.plugins.integration_plugin import IntegrationPlugin
from devflow.plugins.base import PluginMetadata


logger = logging.getLogger(__name__)


class GitHubWebhookIntegration(IntegrationPlugin):
    """GitHub webhook integration."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="github-webhook-integration",
            version="1.0.0",
            description="Handle webhooks from GitHub",
            author="DevFlow Team",
            plugin_type="integration",
            dependencies=[],
            devflow_version="0.1.0"
        )

    def get_integration_name(self) -> str:
        return "github-webhook"

    def get_integration_type(self) -> str:
        return "vcs"

    def get_required_config_fields(self) -> List[str]:
        return ['webhook_secret']

    def connect(self) -> bool:
        return self.validate_config()

    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        # Verify webhook signature
        if not self._verify_signature(payload, headers):
            return {'success': False, 'message': 'Invalid signature'}

        # Get event type
        event_type = headers.get('X-GitHub-Event', '')

        try:
            if event_type == 'push':
                self._handle_push(payload)
            elif event_type == 'pull_request':
                self._handle_pull_request(payload)
            elif event_type == 'issues':
                self._handle_issues(payload)

            return {'success': True, 'message': f'{event_type} event processed'}

        except Exception as e:
            logger.error(f"Error handling GitHub webhook: {e}")
            return {'success': False, 'message': str(e)}

    def _verify_signature(self, payload: Dict[str, Any], headers: Dict[str, str]) -> bool:
        signature = headers.get('X-Hub-Signature-256')
        if not signature:
            return False

        secret = self.config.get('webhook_secret').encode()
        expected_signature = 'sha256=' + hmac.new(secret, str(payload).encode(), hashlib.sha256).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    def _handle_push(self, payload: Dict[str, Any]) -> None:
        ref = payload.get('ref', '')
        repository = payload.get('repository', {}).get('name', '')
        pusher = payload.get('pusher', {}).get('name', '')

        logger.info(f"Push to {repository} on {ref} by {pusher}")
        # Handle push event...

    def _handle_pull_request(self, payload: Dict[str, Any]) -> None:
        action = payload.get('action', '')
        pr = payload.get('pull_request', {})
        title = pr.get('title', '')
        number = pr.get('number', '')

        logger.info(f"Pull request #{number} {action}: {title}")
        # Handle pull request event...

    def _handle_issues(self, payload: Dict[str, Any]) -> None:
        action = payload.get('action', '')
        issue = payload.get('issue', {})
        title = issue.get('title', '')
        number = issue.get('number', '')

        logger.info(f"Issue #{number} {action}: {title}")
        # Handle issues event...

    def get_supported_webhook_events(self) -> List[str]:
        return ['push', 'pull_request', 'issues', 'issue_comment', 'status']

    def send_notification(self, message: str, level: str = "info") -> bool:
        # Create a GitHub issue or comment with the notification
        logger.info(f"GitHub notification: {message}")
        return True
```

---

### Jenkins CI/CD Integration

Integrate with Jenkins for CI/CD operations.

**File:** `jenkins-integration/plugin.py`

```python
"""
Jenkins CI/CD Integration Plugin.

Integrates with Jenkins for CI/CD operations.
"""

import logging
import requests
from typing import Dict, Any, List
from datetime import datetime

from devflow.plugins.integration_plugin import IntegrationPlugin
from devflow.plugins.base import PluginMetadata


logger = logging.getLogger(__name__)


class JenkinsIntegration(IntegrationPlugin):
    """Jenkins CI/CD integration."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="jenkins-integration",
            version="1.0.0",
            description="Integrate with Jenkins for CI/CD",
            author="DevFlow Team",
            plugin_type="integration",
            dependencies=[],
            devflow_version="0.1.0"
        )

    def get_integration_name(self) -> str:
        return "jenkins"

    def get_integration_type(self) -> str:
        return "cicd"

    def get_required_config_fields(self) -> List[str]:
        return ['base_url', 'username', 'api_token']

    def connect(self) -> bool:
        if not self.validate_config():
            return False

        return self.test_connection()

    def test_connection(self) -> bool:
        try:
            response = self._api_call('/api/json', method='GET')
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Jenkins connection test failed: {e}")
            return False

    def _api_call(self, path: str, method: str = 'GET', data: Dict[str, Any] = None):
        base_url = self.config.get('base_url').rstrip('/')
        username = self.config.get('username')
        api_token = self.config.get('api_token')

        url = f"{base_url}{path}"
        auth = (username, api_token)
        headers = {'Content-Type': 'application/json'}

        if method == 'GET':
            return requests.get(url, auth=auth, headers=headers, timeout=30)
        elif method == 'POST':
            return requests.post(url, auth=auth, json=data, headers=headers, timeout=30)

    def trigger_build(self, job_name: str, parameters: Dict[str, Any] = None) -> bool:
        try:
            path = f"/job/{job_name}/build"
            if parameters:
                path += "WithParameters"

            response = self._api_call(path, method='POST', data=parameters)
            response.raise_for_status()

            logger.info(f"Triggered Jenkins build: {job_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to trigger build: {e}")
            return False

    def get_build_status(self, job_name: str, build_number: int) -> Dict[str, Any]:
        try:
            path = f"/job/{job_name}/{build_number}/api/json"
            response = self._api_call(path, method='GET')
            response.raise_for_status()

            data = response.json()
            return {
                'building': data.get('building', False),
                'result': data.get('result'),
                'timestamp': data.get('timestamp'),
                'duration': data.get('duration')
            }

        except Exception as e:
            logger.error(f"Failed to get build status: {e}")
            return {}

    def handle_webhook(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        # Handle Jenkins webhook notifications
        job_name = payload.get('name', '')
        build = payload.get('build', {})

        logger.info(f"Jenkins webhook: Job {job_name}, build {build.get('number')}")

        # Process build completion
        if build.get('status') == 'COMPLETED':
            result = build.get('result', 'UNKNOWN')
            logger.info(f"Build completed with result: {result}")

        return {'success': True, 'message': 'Webhook processed'}

    def get_supported_webhook_events(self) -> List[str]:
        return ['job_completed', 'job_started', 'job_failed']

    def get_health_check(self) -> Dict[str, Any]:
        try:
            response = self._api_call('/api/json', method='GET')
            is_healthy = response.status_code == 200

            return {
                'status': 'healthy' if is_healthy else 'unhealthy',
                'message': 'Jenkins is connected' if is_healthy else 'Jenkins is unreachable',
                'details': {
                    'integration_name': self.get_integration_name(),
                    'integration_type': self.get_integration_type(),
                    'base_url': self.config.get('base_url')
                }
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Jenkins health check failed: {e}',
                'details': {}
            }
```

**Usage:**

```python
from devflow.plugins.plugin_manager import PluginManager

manager = PluginManager()
result = manager.load_plugin_from_path("./jenkins-integration")

if result.success:
    plugin = manager.get_plugin(result.plugin_name)
    plugin.connect()

    # Trigger a build
    plugin.trigger_build('my-project', {
        'BRANCH': 'main',
        'ENVIRONMENT': 'production'
    })

    # Check build status
    status = plugin.get_build_status('my-project', 123)
    print(f"Build status: {status}")
```

---

## Running Examples

Each example can be run independently:

```bash
# Load an example plugin
from devflow.plugins.plugin_manager import PluginManager

manager = PluginManager()

# Load the plugin
result = manager.load_plugin_from_path("./examples/custom-code-reviewer")

if result.success:
    # Start the plugin
    manager.start_plugin(result.plugin_name)

    # Use the plugin
    plugin = manager.get_plugin(result.plugin_name)
    # ... plugin-specific usage

    # Stop when done
    manager.stop_plugin(result.plugin_name)
```

For more detailed examples, check the `examples/` directory in the DevFlow repository.

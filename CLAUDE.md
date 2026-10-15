CLAUDE.md — Windows MCP Server Development Instructions

1. Project Identity

This repository contains a Python-based Model Context Protocol (MCP) server designed to provide locally hosted AI systems with secure, structured access to remote Windows endpoints.

The MCP server enables AI agents to perform system diagnostics, troubleshooting, monitoring, and authorized administrative operations through standardized MCP tools.

Important: Claude Code is being used as a software development assistant to build and maintain this project. Claude Code is not the intended runtime client of this MCP server.

The completed platform must remain independent of Anthropic, Claude Code, and any particular AI model or provider.

The intended consumers are locally hosted AI applications and agents that support the MCP protocol.

2. Required Project Context

Before proposing major architectural changes or implementing significant features, review the following documentation when available:

* docs/VISION.md — Overall project purpose and long-term objectives.
* docs/ARCHITECTURE.md — System components, communication paths, and infrastructure.
* docs/SECURITY.md — Security requirements, authorization boundaries, and execution policies.
* docs/TOOL-CATALOG.md — Existing and planned MCP tools.
* docs/ROADMAP.md — Development milestones and priorities.
* docs/diagrams/ — Architecture and workflow diagrams.

Treat these documents as the intended design, but verify their accuracy against the existing implementation.

If documentation conflicts with functioning code, identify the discrepancy before changing behavior.

Do not assume that documented future capabilities are already implemented.

3. Technology and Architecture

Current Technology

* Primary language: Python
* Protocol: Model Context Protocol (MCP)
* Target operating systems: Windows
* Remote administration: PowerShell and PowerShell Remoting / WinRM
* Configuration: Environment variables and .env files
* AI integration: MCP-compatible locally hosted AI clients

Additional libraries and frameworks should be selected based on compatibility, security, maintainability, and actual project requirements.

Architectural Principles

The application should be organized into independent, reusable components.

Maintain a clear separation between:

1. MCP protocol handling and tool registration.
2. Tool-specific business logic.
3. Remote Windows execution.
4. Target validation and authorization.
5. Configuration management.
6. Authentication and credential handling.
7. Logging, auditing, and error handling.

Avoid placing all functionality in server.py.

The MCP server should remain lightweight, with individual tools implemented as modular components wherever practical.

4. Development Responsibilities

When working in this repository, act as an experienced Python software engineer with expertise in:

* MCP server development
* Windows administration
* PowerShell automation
* Remote systems management
* Network security
* Secure application architecture
* Infrastructure automation

Your responsibility is to help develop a reliable, secure, extensible MCP server suitable for increasingly sophisticated AI-driven Windows administration.

Prioritize maintainability, reliability, and security over unnecessary complexity.

5. Code Development Standards

General Requirements

* Inspect existing code before introducing new implementations.
* Reuse established components and utilities.
* Avoid duplicating existing functionality.
* Follow consistent naming conventions.
* Use Python type hints where practical.
* Prefer clear, readable implementations over unnecessary abstractions.
* Keep functions focused on specific responsibilities.
* Use structured error handling.
* Avoid introducing unnecessary dependencies.
* Preserve backward compatibility when practical.

Modular Tool Development

Each MCP tool should have:

* A descriptive and unambiguous name.
* A clearly defined purpose.
* Explicit, typed input parameters.
* Input validation.
* Consistent structured output.
* Meaningful error reporting.
* Defined authorization requirements.
* Appropriate logging.
* Automated tests where practical.

Tools should return information in a format that AI agents can interpret reliably.

Do not rely on free-form text responses when structured data would be more appropriate.

Tool Parameterization

Remote administrative tools must accept target computer information through explicit parameters.

Do not hardcode target hostnames or IP addresses into tool implementations.

Shared validation and remote connection logic should be reused across tools.

6. Security Requirements

Security is a core architectural requirement and must be enforced by the MCP server independently of the AI client.

Target Authorization

* Maintain an explicit allowlist of authorized endpoints.
* Load configurable allowlist values from environment-based configuration.
* Reject unauthorized target requests.
* Validate hostname formats and resolved addresses.
* Prevent unauthorized network access through hostname or DNS manipulation.
* Do not silently substitute a different target if validation fails.
* Apply network-level restrictions where practical.

Remote Execution

* Prefer predefined administrative operations over unrestricted command execution.
* Never introduce arbitrary remote PowerShell execution without explicit approval.
* Separate read-only tools from tools that modify system state.
* Apply least-privilege principles.
* Require appropriate authorization for high-impact operations.
* Implement execution timeouts.
* Avoid unsafe shell interpolation and command construction.
* Never automatically execute destructive operations during testing.

Credentials and Secrets

* Never hardcode passwords, API keys, or authentication secrets.
* Never commit populated .env files.
* Provide safe configuration examples through .env.example.
* Avoid logging credentials or sensitive authentication data.
* Use secure authentication mechanisms appropriate for the environment.

Auditing

Administrative actions should produce meaningful audit records containing, where available:

* Tool name
* Requested target
* Validated target
* Operation performed
* Execution timestamp
* Success or failure
* Relevant error details
* Request or correlation identifier

Avoid recording unnecessary sensitive information.

7. Network Environment

The initial development environment consists of a workstation with two network interfaces:

Production Network Interface

Connected to the existing production environment.

Isolated Laboratory Interface

Connected to a separate test network containing Windows endpoints used for development and validation.

During initial development, remote administration tools must be tested only against explicitly authorized laboratory endpoints.

The existence of a production network connection must not be interpreted as permission to access production systems.

Do not introduce automatic network discovery, broad subnet scanning, or unrestricted host targeting without explicit authorization.

The architecture should support future deployment into other authorized environments without requiring major code changes.

8. Error Handling and Reliability

Remote administration is inherently subject to connectivity failures, authentication problems, endpoint unavailability, and operating system differences.

Tools should gracefully handle:

* Unreachable endpoints
* DNS resolution failures
* Authentication failures
* Insufficient permissions
* WinRM connection failures
* PowerShell execution errors
* Timeouts
* Unexpected or malformed responses
* Unsupported operating system capabilities

Errors should be returned in a structured, actionable format.

Do not report an operation as successful unless its outcome has been verified to the extent practical.

Avoid silently swallowing exceptions.

9. Testing Requirements

Whenever adding or modifying functionality:

1. Identify the expected behavior.
2. Add or update relevant tests.
3. Test input validation.
4. Test unauthorized target rejection.
5. Test expected error conditions.
6. Verify that existing tools continue functioning.
7. Validate MCP tool registration and schemas.
8. Test remote operations against approved laboratory endpoints when available.

Never execute destructive integration tests without explicit permission.

Mock remote execution where appropriate for automated unit tests.

Do not claim that a test passed unless it was actually executed successfully.

10. Development Workflow

Before Making Changes

For significant changes:

1. Review the relevant source files.
2. Review applicable project documentation.
3. Understand the existing implementation.
4. Identify the components that will be affected.
5. Explain the proposed approach.
6. Identify meaningful security or compatibility implications.

For small, straightforward changes, proceed directly when the requirements are clear.

During Implementation

* Make focused changes.
* Preserve existing functionality.
* Follow established project patterns.
* Avoid unrelated refactoring.
* Do not introduce unnecessary architectural complexity.
* Keep security controls centralized and consistent.
* Prefer reusable components over duplicated implementations.

After Implementation

1. Run applicable tests.
2. Review potential regressions.
3. Check for security issues.
4. Summarize changes made.
5. Identify any unresolved limitations.
6. Update relevant documentation when behavior or architecture changes.

11. Project Documentation Maintenance

Keep documentation synchronized with the implementation.

When introducing a new MCP tool, update docs/TOOL-CATALOG.md.

When modifying system architecture, update docs/ARCHITECTURE.md and relevant diagrams.

When introducing security-related changes, update docs/SECURITY.md.

When completing roadmap milestones, update docs/ROADMAP.md.

Do not describe incomplete functionality as implemented.

12. Long-Term Development Direction

The MCP server is intended to evolve beyond basic remote command execution into a comprehensive Windows infrastructure management interface.

Potential future capabilities include:

* Advanced Windows diagnostics
* Event log analysis
* Service and process management
* Network troubleshooting
* Active Directory integration
* Windows update management
* Software inventory and deployment
* Automated troubleshooting workflows
* Multi-endpoint administration
* Controlled remediation
* Approval-based administrative operations
* Infrastructure monitoring integrations

Design new components with reasonable extensibility in mind, but do not implement speculative features unless requested.

13. AI Client Independence

The MCP server must remain compatible with the standardized MCP ecosystem.

Do not introduce dependencies on:

* Claude Code
* Anthropic-specific APIs
* A particular locally hosted model
* A particular AI application
* Provider-specific tool-calling formats

Provider-specific integration should remain outside the core MCP server unless explicitly required.

The MCP server should expose well-defined tools and enforce its own execution policies.

The AI client is responsible for reasoning about which tools to request.

The MCP server is responsible for validating and safely executing authorized requests.

14. Collaboration Expectations

When discussing implementation decisions:

* Be technically precise.
* Explain important architectural tradeoffs.
* Challenge designs that introduce security or reliability problems.
* Recommend better approaches when justified.
* Avoid unnecessary rewrites of working functionality.
* Distinguish between confirmed facts and assumptions.
* Ask for clarification when a decision would significantly affect architecture or security.

Do not make major architectural changes without explaining the rationale.

15. Guiding Principle

Build a secure, modular, reliable, and AI-independent Windows management interface that allows locally hosted AI systems to interact with authorized infrastructure through standardized MCP tools.

Every major design decision should support that objective.
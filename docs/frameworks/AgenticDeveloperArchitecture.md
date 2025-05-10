# Agentic Developer Architecture (Revised)

> This document describes the design and architecture of the Agentic Developer: an autonomous, ontology‑backed, control‑theoretic system for iterative software development, with a specific focus on the Interpreter as the bidirectional bridge between agent and project reality.

## Table of Contents
1. [Introduction](#introduction)
2. [End-to-End Architecture Overview](#end-to-end-architecture-overview)
3. [Core Components](#core-components)
   - Interpreter Sessions & Control Surface
   - Planner Sub-Agents
   - Code Generation Agent
   - Executor & Sandbox
   - Verifier & Feedback Loop
   - Meta-Learner
4. [Interpreter as Computational Bridge](#interpreter-as-computational-bridge)
   - Project-Centered Execution Context
   - Multi-Modal Integration Hub
   - Concurrent Computational Spaces
   - Programmable Automation Surface
5. [Tool Interface via Python DSL](#tool-interface-via-python-dsl)
6. [Ontological Knowledge Domains](#ontological-knowledge-domains)
7. [Memory Tiers and Stores](#memory-tiers-and-stores)
8. [Runtime Isolation & Risk Controls](#runtime-isolation--risk-controls)
9. [Control-Loop Formalism & Tuning](#control-loop-formalism--tuning)

---

## Introduction
The Agentic Developer is an autonomous software-engineering system designed to translate high-level requirements into production-ready code through iterative, closed-loop feedback. At its foundation is the Interpreter - a bidirectional computational bridge that connects agent intelligence to project reality.

The system rests on four pillars:
1. **Control-Theoretic Architecture**  
   Treating software development as a dynamic system with measurable gains, latencies, and feedback loops, ensuring stability and convergence toward the target requirements.

2. **Interpreter-Mediated Interactions**  
   All agent components interact with the project through a central Interpreter layer that acts as both control surface and observatory window, providing a persistent execution context.

3. **Ontology-Backed Knowledge**  
   The agent maintains structured ontologies for its intrinsic state, domain world knowledge, and available skillsets, enabling precise reasoning and context-aware planning.

4. **Layered Risk Isolation**  
   To safeguard the codebase and infrastructure, all actions execute within hardened sandboxes with appropriate isolation boundaries, balancing autonomy with robust safety controls.

## End-to-End Architecture Overview

The architecture revolves around a continuous feedback loop where the Interpreter serves as the central hub connecting agent components with the project:

```
┌──────────────────────┐
│   Project Reality    │
│  (Files, Resources)  │
└────────┬─────────────┘
         │
         │
┌────────▼─────────────┐
│                      │
│     INTERPRETER      │◄───────────┐
│                      │            │
└────────┬─────────────┘            │
         │                          │
         │                          │
┌────────▼─────────────┐    ┌───────┴──────────┐
│    Agent Components  │    │ Meta-Learner     │
│                      │    │ (Feedback Loop)  │
│  ┌─────────────────┐ │    └──────────────────┘
│  │     Planner     │ │
│  └────────┬────────┘ │
│           │          │
│  ┌────────▼────────┐ │
│  │  Code Generator │ │
│  └────────┬────────┘ │
│           │          │
│  ┌────────▼────────┐ │
│  │     Verifier    │ │
│  └─────────────────┘ │
└──────────────────────┘
```

1. **Goal Intake & Error Computation**  
   Requirements (set-points) are compared against current system behavior to compute an error signal \(E(s)\).

2. **Interpreter Session Initialization**  
   The Interpreter establishes a project-centered execution context with appropriate tools and access patterns.

3. **Planning & Task Graph Generation**  
   Planner sub-agents decompose \(E(s)\) into a directed task graph, scheduling subtasks based on dependencies and risk assessments.

4. **Code Generation & Tool Invocation**  
   The Code Generation Agent selects tools from the Interpreter's registry, synthesizes code diffs, and stages patches for execution.

5. **Execution in Integrated Environment**  
   Each patch is applied through the Interpreter, which provides a consistent interface to the project regardless of the specific tool or operation.

6. **Verification & Feedback Filtering**  
   Verifier modules execute tests, static analyses, and performance checks through the Interpreter, filtering raw outputs into a normalized feedback signal \(Y_f(s)\).

7. **Loop Closure & Meta-Learning**  
   The filtered feedback updates the error \(E(s)=R(s)-Y_f(s)\), and the Meta-Learner adjusts system gains and policies before the next iteration.

This end-to-end loop maps onto a closed-loop transfer function, ensuring stability, convergence, and adaptive refinement through quantitative feedback at each stage.

## Core Components

### Interpreter Sessions & Control Surface

The Interpreter is the foundation of the architecture, serving as a bidirectional bridge between agent components and project reality:

- **Session Management**: Creates and maintains persistent computational contexts with state continuity across interactions
- **Tool Integration**: Exposes development tools as programmable Python interfaces
- **Execution Environment**: Provides a dynamic, interactive computational space for code execution and evaluation
- **Concurrent Contexts**: Supports multiple parallel activities with isolated state but shared infrastructure
- **Project Centricity**: Ensures all operations are centered around the development project

The Interpreter implements several key mechanisms:

- **Kernel Management**: Controls the lifecycle of Python processes that execute code
- **State Persistence**: Maintains computational state between interactions
- **Tool Registry**: Catalogs available development tools and their interfaces
- **Resource Control**: Manages access to system resources and enforces limits
- **Error Handling**: Provides robust recovery from execution failures

### Planner Sub-Agents

The Planner layer decomposes requirement errors into a structured task graph via specialized sub-agents:
- **Task-Decomposer Agent**: Breaks high-level requirements into discrete, manageable subtasks, generating dependencies and heuristics for ordering.
- **Dependency-Resolver Agent**: Analyzes the codebase's AST and dependency graphs to ensure each subtask's prerequisites are satisfied, updating the task graph with resource and order constraints.
- **Risk-Assessor Agent**: Estimates uncertainty, potential side-effects, and complexity for each task, assigning weights that influence scheduling and parallelism.

All Planner components operate through the Interpreter, which provides both:
- A standardized interface to project resources (files, structures, dependencies)
- A computational environment for executing analysis algorithms

### Code Generation Agent

The Code Generation Agent translates task graph nodes into concrete code diffs by:
1. Selecting appropriate tools from the Interpreter's Tool Registry
2. Issuing tool invocations through the Interpreter's session
3. Generating, formatting, and linting code patches, then staging them for execution

Rather than directly accessing project files or external systems, the Code Generation Agent works entirely through the Interpreter's sessions, which:
- Ensure consistency in resource access patterns
- Provide isolated environments for different generative tasks
- Maintain a persistent context for iterative refinement

### Executor & Sandbox

The Executor runs generated artifacts in isolation:
- Launches operations through the Interpreter's tool interfaces
- Captures logs, runtime traces, and performance metrics
- Reports execution latency and environment health back to the Verifier

The Interpreter provides a consistent abstraction layer between the Executor and the underlying infrastructure, handling the details of process management, sandboxing, and resource allocation.

### Verifier & Feedback Loop

The Verifier filters raw execution outputs into feedback signals:
- **Functional Tests**: Unit, integration, and property-based tests producing pass/fail vectors.
- **Static Analysis**: Linters, type-checkers, and security scanners yielding error counts and severity scores.
- **Metrics Aggregation**: Code coverage, performance baselines, and resource usage feeding into a normalized feedback `Y_f(s)`.

This feedback is compared against the requirement set-point to compute the next error `E(s)`.

Like all other components, the Verifier interacts with the project through the Interpreter, running verification tools as programmable Python interfaces rather than command-line operations.

### Meta-Learner

The Meta-Learner monitors key performance indicators and adjusts agent "gain knobs":
- **Planning Granularity**: Modifies how finely tasks are decomposed.
- **Codegen Temperature**: Tunes LLM sampling parameters for creativity vs. consistency.
- **Verifier Thresholds**: Calibrates test strictness and allowable flakiness.

The Meta-Learner obtains performance metrics through the Interpreter and uses it to tune agent behavior for subsequent iterations.

## Interpreter as Computational Bridge

The Interpreter transcends its role as a mere execution environment to become the fundamental computational fabric of the system:

### Project-Centered Execution Context

- All computation occurs in service to project manipulation and understanding
- Session state reflects and impacts the project's state
- Filesystem access patterns align with project structure
- Working directories and environment variables are project-aware

### Multi-Modal Integration Hub

- Development tools are exposed as Python interfaces rather than command-line operations
- Complex workflows are composed from simpler operations
- Tool interfaces provide consistent input/output patterns regardless of underlying implementation
- New capabilities can be integrated through the same extension mechanisms

### Concurrent Computational Spaces

- Multiple independent but related activities occur simultaneously
- Different tasks maintain their own state but share a common substrate
- Focus can shift between contexts while all contexts remain active
- Each context may serve different purposes (monitoring, editing, building, testing)

### Programmable Automation Surface

- Interpreter sessions expose a consistent Python API for all operations
- Tools are defined using a declarative Python DSL
- Complex development operations are abstracted into composable functions
- Extension happens through Python's native module and class mechanisms

## Tool Interface via Python DSL

The Agentic Developer uses Python as its Domain-Specific Language (DSL) to define, discover, and negotiate tool capabilities through a unified interface.

### Tool Definition

- **Decorator-Based Metadata**: Tools are Python functions annotated with an `@tool` decorator capturing:
  - `name`: canonical identifier (e.g., `"git_commit"`)
  - `version`: semantic version string (e.g., `"1.2.0"`)
  - `requires`: list of required context or credentials (e.g., `["git_repo", "CI_token"]`)
  - Optional parameters: `deprecated_since`, `timeout_ms`, `provides`
- **Example**:
  ```python
  from agent_tools import tool

  @tool(name="git_commit", version="1.2.0", requires=["git_repo", "CI_token"])
  def git_commit(message: str) -> str:
      """
      Commit staged changes with `message`. Returns the new commit hash.
      """
      assert len(message) < 1000, "Commit message too long"
      output = sh(f"git commit -m {quote(message)}")
      return parse_hash(output)
  ```

### Tool Registry and Discovery

The Interpreter's Tool Registry serves as the central catalog of available tools:

- It scans the `tools/` directory for decorated functions and methods
- It builds a capability graph showing tool dependencies and relationships
- It enables discovery and filtering by name, purpose, or required resources
- It manages compatibility between tools and interpreter sessions

Tools are exposed through the Interpreter session interface:

```python
# Using the tool registry through a session
session = interpreter.get_session("main")
git_tool = session.get_tool("git")
commit_hash = git_tool.commit("Fixed bug in parser")
```

## Ontological Knowledge Domains

The Ontological Knowledge Domains define the structured knowledge that the Agentic Developer uses to reason, plan, and act. They are divided into three interrelated layers:

### Intrinsic Knowledge
Models the agent's internal state and capabilities:
- **Agent Profile**: Versioned policies, prompt templates, LLM model configurations.
- **Active Goals & Constraints**: Current requirement set-points, SLAs, security guardrails.
- **Working Context**: In-flight task graph, recent iteration history, transient variables.

**Storage**: Fast in-memory cache (e.g., Redis) with TTL to hold ephemeral context per planning cycle.

### World Knowledge
Represents the external environment and domain semantics:
- **Code Graphs**: AST indexes, dependency and call graphs of the codebase.
- **Runtime Profiles**: Benchmarks, performance baselines, failure modes.
- **Domain Ontologies**: Business logic rules, data schemas, coding standards.

**Storage**: Persistent vector database (e.g., Pinecone) for embeddings + symbolic index (e.g., SQLite) for structured queries.

### Skillset Knowledge
Catalogs the agent's available tools and their interfaces:
- **Tool Registry**: Python functions annotated with metadata (`@tool`), defining name, version, parameters, preconditions.
- **Capability Graph**: Meta-model of tool composability and prerequisites.

**Storage**: Version-controlled module repository (tools/) and in-memory registry loaded at runtime.

## Memory Tiers and Stores

The Agentic Developer uses a dual-tier memory architecture to balance performance and persistence:

### Working Context Store
- **Purpose**: Holds ephemeral state needed within a single planning-execution-verification cycle.
- **Contents**: Current task graph, intermediate results, recent tool outputs, transient variables.
- **Implementation**: In-memory cache (e.g., Redis) with fine-grained TTL (e.g., 1–2 hours) to automatically evict stale context.
- **Access Pattern**: Read/write by all sub-agents during a planning iteration; non-durable across process restarts.

### Persistent Knowledge Base
- **Purpose**: Stores long-term domain knowledge, historical metrics, and learned policies.
- **Contents**: Vector embeddings of code snippets and docs, symbolic indexes for AST/query lookups, iteration logs, meta-learner snapshots.
- **Implementation**: 
  - Vector Database (e.g., Pinecone, FAISS) for similarity search on embeddings.
  - Symbolic Index (e.g., SQLite, Elasticsearch) for structured queries and provenance tracking.
- **Access Pattern**: Queried by Planner and Verifier for context retrieval; appended by Executor and Meta-Learner for new observations.

The Interpreter aligns with this memory architecture by:
- Providing access to working context through session state
- Interfacing with persistent storage through tool interfaces
- Managing the lifecycle of both memory tiers

## Runtime Isolation & Risk Controls

To ensure the Agentic Developer operates safely, all runtime actions are confined and monitored through layered isolation and robust risk controls. We categorize controls into two areas: Risk Avoidance and Risk Management.

### Risk Avoidance
- **Least-Privilege Sandboxes**  
  - Ephemeral micro-VMs (e.g., Firecracker) or containers with minimal Linux capabilities (seccomp, AppArmor, SELinux).  
  - Read-only mounts for source code; write access limited to isolated work directories.  
  - No direct network egress unless explicitly whitelisted per tool.

- **Credential Vaulting & Scoping**  
  - Short-lived, scoped credentials issued at runtime via a secrets broker (e.g., HashiCorp Vault, AWS STS).  
  - Tokens restricted to ephemeral branches or test environments; automatically revoked after execution.

- **Static Output Vetting**  
  - AST-based lint checks on generated diffs to block disallowed patterns (e.g., modifications to protected directories, removal of CI config).  
  - Blacklist and whitelist enforcement for shell commands and API calls.

The Interpreter enforces these controls by:
- Managing resource allocation and access through session contexts
- Providing controlled interfaces to external systems
- Validating operations before execution

### Risk Management
- **Ephemeral Branching & CI Gating**  
  - Agent commits land on ephemeral, auto-generated branches (e.g., `agent/run-<timestamp>`).  
  - Continuous integration runs full test suite and policy checks; merges into `main` only on green status.

- **Automated Rollback**  
  - On post-merge CI failures or anomaly detection, a rollback pipeline triggers `git revert` on the offending commits.  
  - Maintains an immutable audit log of agent actions (commits, tool invocations, sandbox snapshots).

- **Runtime Monitoring & Kill-Switch**  
  - Sidecar watchdog process tracks sandbox metrics (file I/O rates, CPU usage, network activity).  
  - Automatic termination of sandboxes on policy violations or exceeded thresholds; snapshots retained for forensic analysis.

- **Canary Deployments**  
  - Deployments target a non-production environment first; health checks and smoke tests validate stability before promoting to production.

The Interpreter supports these risk management practices through:
- Tool interfaces for version control and CI operations
- Session tracking and resource monitoring
- Execution logging and audit trails

## Control-Loop Formalism & Tuning

The Agentic Developer's convergence behavior is modeled using classical control theory, with the Interpreter serving as the interface between the controller (agent components) and the plant (project).

### Transfer Functions
Let:
- \( G_P(s) \) = Planner transfer function
- \( G_C(s) \) = Code Generation transfer function
- \( G_E(s) \) = Executor transfer function
- \( G_R(s) \) = Runtime (Plant) transfer function
- \( G_V(s) \) = Verifier (Sensor) transfer function
- \( G_I(s) \) = Interpreter transfer function (new)

**Closed-Loop Transfer Function**:
\[
T(s) = \frac{Y(s)}{R(s)} = \frac{G_P(s)\,G_C(s)\,G_I(s)\,G_E(s)\,G_R(s)}{1 + G_P(s)\,G_C(s)\,G_I(s)\,G_E(s)\,G_R(s)\,G_V(s)}.
\]

The addition of \( G_I(s) \) represents the Interpreter's role in the control loop, introducing its own dynamics that affect the overall system behavior.

**Interpreter-Specific Parameters**:
- Execution latency for code operations
- Tool integration overhead
- Concurrent session management efficiency
- State persistence reliability

By tuning these parameters, the system can optimize for:
- Stability (avoiding oscillations in code changes)
- Responsiveness (quick adaptation to requirement changes)
- Accuracy (fidelity to original requirements)

### Validation Metrics
- **Mean-Time-to-Green (MTTG)**: Average time to restore a green pipeline after requirement change.
- **Overshoot Frequency**: Rate of repeated failures after initial success.
- **Stability Margin**: Minimum gain reduction before oscillatory behavior emerges.
- **Robustness**: Response consistency across varied requirement complexity and disturbance profiles.

The Interpreter provides the mechanisms to measure these metrics through:
- Execution time tracking
- Output capture and analysis
- Tool integration for monitoring and reporting
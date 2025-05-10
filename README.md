# Agentic Development

[TOC]

## About

Agentic Development is the application of automation to software development itself.

## The Development Process

The process being automated follows:

1. Articulate the problem or hypothesis
2. Research the problem space 
3. Architect & design a solution
4. Plan out the work
5. Write the code
6. Test the solution
7. Release the solution

This process fits into the larger "Problem Solving" framework we are naturally predisposed to as humans.

## Agents, Knowledge, and Work

Autonomous systems, whether computer or human, with the ability to take action towards some semantic goal are defined as `agents`. Agents, within the scope of this project, apply `work` to the system by writing valid software instructions that some interpreter then executes.

> For example, an agent seeking to modify the source of a file could A) submit a command to open a patch, B) then write it's modifications to the now open patch & C) finally close the patch. The Interpreter would, in the background, A) open a temporary file attaching it to the stdin stream, B) wait for the file to close, re-attaching the previous stdin & C) applying the patch to the project.

`Knowledge` then is, pragmatically, an agent's ability to take relevant information & apply it toward's producing higher quality results.

> For example, an agent that knows hashmaps provide an O(1) lookup time & iterative list searches have a O(n) lookup time, would use a hashmap to maintain an extremely large set of values it needs to track.

## Automation

Automating the end to end process requires:

- Identifing individual procedures.
- Creating, for each procedure, a pipeline that given structured input produces structured output.
- Define a target end state, determine the current state & calculate the difference between (the error); iterate until a threshold is met.

More formally the Automation is based on a closed loop transfer function from systems control theory. In depth information can be found in [the formal framework](./docs/AgenticDeveloperArchitecture.md).

## Testing

The project includes comprehensive test suites to validate functionality:

- **CLI Tests**: Tests for the command-line interface
  ```bash
  python -m tests.run_cli_tests
  ```

- **Event-Driven Architecture Tests**: Tests for the persistent kernel architecture
  ```bash
  python -m tests.run_event_driven_tests
  ```

Test suite options:
- `--verbose` or `-v`: Enable verbose output
- `--unit-only`: Run only unit tests
- `--integration-only`: Run only integration tests

For example:
```bash
# Run only unit tests for the event-driven architecture
python -m tests.run_event_driven_tests --unit-only
```

## Contributor's Guide

We keep the layout of the source code simple following these three rules:

1. A single file implements a single feature/semantic/responsibility
2. Refactor out core functionality & external utilities
3. A single control surface can be exposed in multiple ways (CLI, HTTP, etc...)

When writing code, follow these directive, guidelines, and patterns:

- K.I.S.S: Favor plain, repetitive and/or explicit code over metaprogramming, templating and/or dynamic code. Use syntactic sugar where it creates clarity. Make code readable.
- Be declarative: the code should describe outcomes; liberally use assertions to frame your expectation of external state & program behaviors; Be wary of implicit behaviors; use principles of Domain-driven Design.
- Use Types & Interfaces: Constrain the system you are working with by modeling it's scope & functionality through Types & Interfaces.
- Encode Knowledge: Make the code self documenting; otherwise include comments & document inline with the code. Add documentation to elucidate contextual motives for certain code.
- Fail Fast: Don't try to accommodate minority edge cases, just throw errors early & often. Raise specific exception types with descriptive & contextual error messages.
- Be pragmatic: Favor specialization over generalization; repeat yourself if it's quicker; don't get caught up managing the hierarchical relationships in your code.
- Use dataclasses over regular python classes, except in cases where a regular class is simpler.
- Assume & design for immutability; explicitly indicate mutable types & variables.
- "Any" (or lack of) Type hints are a code smell; constrain the behavior of code.
- Use Protocols (ie. Structural Typing) when exposing external/public interfaces; unless the type is universal.
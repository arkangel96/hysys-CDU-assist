# Deliverable 6 -- Cursor Workspace Specification (CWS)

## Purpose

Define the recommended project organization for development in Cursor.

## Folder Structure

``` text
project/
├── docs/
│   ├── deliverables/
│   ├── engineering/
│   └── prompts/
├── knowledge/
├── memory/
├── connectors/
├── hysys/
├── tests/
├── scripts/
└── logs/
```

## Recommended Documents

-   Engineering Reasoning Specification
-   Engineering Knowledge Base
-   Interaction Specification
-   Learning Specification
-   Rules & Constraints
-   API documentation
-   Decision trees
-   Test cases

## Development Workflow

1.  Update engineering specification.
2.  Update knowledge base.
3.  Implement connector.
4.  Test.
5.  Validate against HYSYS.
6.  Record lessons.

## Prompting Principles

-   Ask for evidence.
-   Explain engineering reasoning.
-   Preserve reproducibility.
-   Cite assumptions.

## Versioning

-   Semantic versioning
-   Change log
-   Baseline snapshots

``` yaml
workflow:
  - specify
  - implement
  - test
  - validate
  - document
```

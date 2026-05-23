# Azure DevOps Agile Work Item Type Definition

Use the current vault note `00 - Inbox/Azure DevOps Agile Work Item Types.md` as the preferred source when available. This reference is a compact fallback for agents using the skill outside the vault.

## Type selection

- **Epic**: large initiative, product area, or major scenario that is too broad for sprint planning.
- **Feature**: capability or user experience that groups related user stories.
- **User Story**: backlog item that delivers user, customer, operator, or stakeholder value.
- **Task**: concrete implementation, documentation, testing, or investigation work required to complete a story.
- **Bug**: product/code defect or behaviour that does not meet expectations.
- **Issue**: delivery blocker, risk, dependency, or non-code impediment.

## Default hierarchy

```text
Epic
└── Feature
    └── User Story
        ├── Task
        ├── Task
        └── Test Case
```

Bugs may be managed as requirements, tasks, or outside the backlog depending on the team setting. Issues should not be used for defects.

## Naming rules

- Prefer clear outcome titles over vague activity buckets.
- Avoid `[CAF] -` in the title when the CAF tag is present.
- Feature titles should read like capabilities, for example `Spoke - App Service`.
- User Story titles should describe a deliverable outcome, for example `Implement Azure DevOps Agents in Shared Services`.
- Task titles should describe a concrete step, for example `Create End-to-End Deployment Guide Template`.
- Bug titles should start with `Fix` only when the defect is confirmed.
- Issue titles should describe the blocker or risk to resolve.

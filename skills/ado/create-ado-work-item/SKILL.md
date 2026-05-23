---
name: create-ado-work-item
description: Create Azure DevOps Boards work items for the Azure Capability Landing Zones CAF backlog from reusable Agile templates. Use when Liam asks to create ADO/Azure DevOps work items, create CAF backlog items, apply or reference work item templates, choose Azure Boards Agile work item types, or turn `00 - Inbox/Azure DevOps Agile Work Item Types.md` guidance into Feature, User Story, Task, Bug, or Issue records.
---

# Create Azure DevOps Work Item

## Purpose

Create Azure DevOps Boards work items consistently using the CAF Agile work item type definition in `00 - Inbox/Azure DevOps Agile Work Item Types.md` and reusable templates in `assets/ado-work-item-templates.json`.

## Required context

Before choosing a work item type, read the current vault note when it exists:

```powershell
Get-Content -LiteralPath "00 - Inbox/Azure DevOps Agile Work Item Types.md" -Raw
```

If the vault note is not available, use `references/agile-work-item-definition.md` as the fallback.

## Helper script

Use the helper for deterministic creation:

```powershell
python "<skill-dir>\scripts\create_ado_work_item.py" list-templates
python "<skill-dir>\scripts\create_ado_work_item.py" show-template work-item-template-creation
python "<skill-dir>\scripts\create_ado_work_item.py" create --template user-story --title "Implement Example Capability" --parent-id 12345
```

The script uses the local Azure DevOps CLI authentication/PAT via `az boards`. It does not store credentials.

Default target:

- Organization: `https://dev.azure.com/version1ukdcs`
- Project: `Azure Capability Landing Zones`
- Area/iteration: `Azure Capability Landing Zones`

Use `--dry-run` before live creation when the request is ambiguous or the item would affect a live backlog unexpectedly.

## Template keys

The bundled templates are:

- `work-item-template-creation`: User Story for creating Azure Boards work item templates.
- `feature`: Feature/capability template.
- `user-story`: value-delivering backlog item template.
- `task`: concrete implementation/documentation/testing task template.
- `bug`: defect template.
- `issue`: blocker/risk/impediment template.

To add or adjust future templates, edit `assets/ado-work-item-templates.json`. Keep template names stable so Liam can reference them by key in future prompts.

## Type selection rules

Use the Agile definition note as source of truth. In short:

- Use **Feature** for a capability or user experience that groups related stories.
- Use **User Story** for deliverable user, customer, operator, or stakeholder value.
- Use **Task** for a concrete implementation, documentation, testing, or investigation step.
- Use **Bug** for defective product/code behaviour.
- Use **Issue** for delivery blockers, risks, dependencies, or non-code impediments.

Do not use Issue for a confirmed defect. Do not use Task for a parent item that needs child user stories.

## Creation workflow

1. Read the current definition note or fallback reference.
2. Select the closest template key, or list templates if unsure.
3. Draft a clear title using the naming rules:
   - avoid `[CAF] -` when the CAF tag is present;
   - use capability names for Features;
   - use outcome names for User Stories;
   - use concrete action names for Tasks;
   - use defect or blocker wording for Bugs/Issues.
4. Run the helper with `--dry-run` if the target type, parent, title, or template is uncertain.
5. Create the item with the helper.
6. If a parent is known, pass `--parent-id`; the helper creates the relation after item creation.
7. Return the ID, type, title, parent, tags, and web edit URL.

## Common examples

Create the same kind of item as the initial template-creation story:

```powershell
python "<skill-dir>\scripts\create_ado_work_item.py" create `
  --template work-item-template-creation `
  --parent-id 10052
```

Create a specific CAF task:

```powershell
python "<skill-dir>\scripts\create_ado_work_item.py" create `
  --template task `
  --title "Create End-to-End Deployment Guide Template" `
  --parent-id 10052 `
  --tag Technical
```

Preview without writing to Azure DevOps:

```powershell
python "<skill-dir>\scripts\create_ado_work_item.py" create `
  --template user-story `
  --title "Add AKS Spoke Support" `
  --dry-run
```

## Safety

- Do not modify, close, delete, or retype existing work items unless Liam explicitly asks.
- Do not create many work items in a loop without showing the proposed list first.
- Prefer creating one work item at a time when requirements are vague.
- If Azure DevOps CLI authentication fails, report the command and error; do not ask for or print PAT values.

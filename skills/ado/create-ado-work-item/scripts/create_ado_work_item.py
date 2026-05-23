#!/usr/bin/env python3
"""Create Azure DevOps work items from reusable CAF Agile templates.

The script intentionally shells out to `az boards` so it reuses the user's
existing Azure DevOps CLI authentication/PAT configuration.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_TEMPLATE_FILE = SKILL_DIR / "assets" / "ado-work-item-templates.json"
DEFAULT_DEFINITION_RELATIVE = Path("00 - Inbox") / "Azure DevOps Agile Work Item Types.md"


def az_executable() -> str:
    az = shutil.which("az") or shutil.which("az.cmd")
    if az:
        return az
    common_windows = Path("C:/Program Files/Microsoft SDKs/Azure/CLI2/wbin/az.cmd")
    if common_windows.exists():
        return str(common_windows)
    raise SystemExit("Azure CLI executable not found. Ensure `az` is installed and available on PATH.")


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise SystemExit(f"Template file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in template file {path}: {exc}")


def load_definition(path: Path | None) -> str | None:
    if path is None:
        candidate = Path.cwd() / DEFAULT_DEFINITION_RELATIVE
    else:
        candidate = path
    if candidate.exists():
        return candidate.read_text(encoding="utf-8-sig")
    return None


def html_sections(sections: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for section in sections:
        heading = html.escape(str(section.get("heading", "Section")))
        parts.append(f"<p><b>{heading}</b></p>")
        body = section.get("body")
        if body:
            parts.append(f"<p>{html.escape(str(body))}</p>")
        bullets = section.get("bullets") or []
        if bullets:
            parts.append("<ul>")
            for bullet in bullets:
                parts.append(f"<li>{html.escape(str(bullet))}</li>")
            parts.append("</ul>")
    return "".join(parts)


def html_list(items: list[str]) -> str:
    if not items:
        return ""
    return "<ul>" + "".join(f"<li>{html.escape(str(item))}</li>" for item in items) + "</ul>"


def merge_tags(defaults: list[str], template_tags: list[str], extra_tags: list[str]) -> str:
    seen: set[str] = set()
    merged: list[str] = []
    for tag in [*defaults, *template_tags, *extra_tags]:
        clean = tag.strip()
        if clean and clean.lower() not in seen:
            merged.append(clean)
            seen.add(clean.lower())
    return "; ".join(merged)


def run_az(args: list[str], dry_run: bool) -> Any:
    if dry_run:
        return {"dryRunCommand": args}
    completed = subprocess.run(args, check=False, text=True, capture_output=True)
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr)
        raise SystemExit(completed.returncode)
    if not completed.stdout.strip():
        return None
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return completed.stdout


def build_fields(template: dict[str, Any], tags: str, args: argparse.Namespace) -> list[str]:
    fields: list[str] = []
    if tags:
        fields.append(f"System.Tags={tags}")
    priority = args.priority if args.priority is not None else template.get("priority")
    if priority is not None:
        fields.append(f"Microsoft.VSTS.Common.Priority={priority}")
    activity = args.activity or template.get("activity")
    if activity:
        fields.append(f"Microsoft.VSTS.Common.Activity={activity}")
    acceptance = args.acceptance_criteria or html_list(template.get("acceptance_criteria") or [])
    if acceptance:
        fields.append(f"Microsoft.VSTS.Common.AcceptanceCriteria={acceptance}")
    return fields


def create_work_item(args: argparse.Namespace) -> dict[str, Any]:
    data = load_json(args.template_file)
    defaults = data.get("defaults", {})
    templates = data.get("templates", {})
    if args.template not in templates:
        valid = ", ".join(sorted(templates))
        raise SystemExit(f"Unknown template '{args.template}'. Valid templates: {valid}")

    template = templates[args.template]
    definition = load_definition(args.definition)
    description = args.description or html_sections(template.get("description_sections") or [])
    if definition and args.include_definition_note:
        description += "<p><b>Definition source</b></p>"
        description += f"<p>{html.escape(str(args.definition or DEFAULT_DEFINITION_RELATIVE))}</p>"

    organization = args.organization or defaults.get("organization")
    project = args.project or defaults.get("project")
    area = args.area if args.area is not None else defaults.get("area")
    iteration = args.iteration if args.iteration is not None else defaults.get("iteration")
    if not organization or not project:
        raise SystemExit("organization and project are required, either in defaults or arguments")

    title = args.title or template.get("title")
    work_item_type = args.type or template.get("type")
    tags = merge_tags(defaults.get("tags") or [], template.get("tags") or [], args.tag or [])

    command = [
        az_executable(), "boards", "work-item", "create",
        "--organization", organization,
        "--project", project,
        "--type", work_item_type,
        "--title", title,
        "--description", description,
        "--output", "json",
    ]
    if area:
        command.extend(["--area", area])
    if iteration:
        command.extend(["--iteration", iteration])
    if args.assigned_to:
        command.extend(["--assigned-to", args.assigned_to])

    result = run_az(command, args.dry_run)
    if args.dry_run:
        update_command = [az_executable(), "boards", "work-item", "update", "--id", "<new-id>", "--organization", organization, "--output", "json"]
        fields = build_fields(template, tags, args)
        if fields:
            update_command.extend(["--fields", *fields])
        relation_command = None
        if args.parent_id:
            relation_command = [az_executable(), "boards", "work-item", "relation", "add", "--organization", organization, "--id", "<new-id>", "--relation-type", "parent", "--target-id", str(args.parent_id)]
        return {"create": result, "update": update_command, "relation": relation_command}

    new_id = result["id"]
    fields = build_fields(template, tags, args)
    if fields:
        run_az([az_executable(), "boards", "work-item", "update", "--id", str(new_id), "--organization", organization, "--fields", *fields, "--output", "json"], False)
    if args.parent_id:
        run_az([az_executable(), "boards", "work-item", "relation", "add", "--organization", organization, "--id", str(new_id), "--relation-type", "parent", "--target-id", str(args.parent_id), "--output", "json"], False)
    return run_az([az_executable(), "boards", "work-item", "show", "--id", str(new_id), "--organization", organization, "--output", "json"], False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Azure DevOps work items from reusable templates.")
    parser.add_argument("--template-file", type=Path, default=DEFAULT_TEMPLATE_FILE)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-templates", help="List available template keys")
    list_parser.add_argument("--json", action="store_true", help="Emit full template JSON")

    show_parser = subparsers.add_parser("show-template", help="Show one template")
    show_parser.add_argument("template")

    create_parser = subparsers.add_parser("create", help="Create a work item")
    create_parser.add_argument("--template", required=True, help="Template key, e.g. user-story or work-item-template-creation")
    create_parser.add_argument("--title")
    create_parser.add_argument("--type")
    create_parser.add_argument("--organization")
    create_parser.add_argument("--project")
    create_parser.add_argument("--area")
    create_parser.add_argument("--iteration")
    create_parser.add_argument("--assigned-to")
    create_parser.add_argument("--parent-id", type=int)
    create_parser.add_argument("--tag", action="append", default=[])
    create_parser.add_argument("--priority", type=int)
    create_parser.add_argument("--activity")
    create_parser.add_argument("--description", help="HTML description override")
    create_parser.add_argument("--acceptance-criteria", help="HTML acceptance criteria override")
    create_parser.add_argument("--definition", type=Path, help="Path to Azure DevOps Agile work item definition note")
    create_parser.add_argument("--include-definition-note", action="store_true")
    create_parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    data = load_json(args.template_file)

    if args.command == "list-templates":
        if args.json:
            print(json.dumps(data.get("templates", {}), indent=2))
        else:
            for key, value in sorted(data.get("templates", {}).items()):
                print(f"{key}\t{value.get('type')}\t{value.get('title')}")
        return 0

    if args.command == "show-template":
        template = data.get("templates", {}).get(args.template)
        if template is None:
            raise SystemExit(f"Unknown template: {args.template}")
        print(json.dumps(template, indent=2))
        return 0

    if args.command == "create":
        result = create_work_item(args)
        print(json.dumps(result, indent=2))
        return 0

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

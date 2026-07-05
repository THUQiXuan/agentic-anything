"""Render a structured page manifest as agent-readable Markdown.

The Markdown view is the primary non-visual representation: a compact,
linear document with headings, content, links (with resolved page ids),
forms, and images — everything an agent needs without parsing HTML.
"""

from __future__ import annotations

from typing import Any


def page_to_markdown(manifest: dict[str, Any]) -> str:
    lines: list[str] = []
    title = manifest.get("title") or manifest.get("page_id", "")
    lines.append(f"# {title}".rstrip())
    lines.append("")
    meta = [
        f"- page_id: `{manifest.get('page_id', '')}`",
        f"- url: {manifest.get('source_url', '')}",
    ]
    if manifest.get("page_type"):
        meta.append(f"- type: {manifest['page_type']}")
    if manifest.get("meta_description"):
        meta.append(f"- description: {manifest['meta_description']}")
    if manifest.get("snapshot_path"):
        meta.append(f"- screenshot: {manifest['snapshot_path']}")
    lines.extend(meta)
    lines.append("")

    blocks = manifest.get("content", [])
    if blocks:
        lines.append("## Content")
        lines.append("")
        for item in blocks:
            kind = item.get("kind", "")
            text = item.get("text", "")
            if not text:
                continue
            if kind == "heading":
                level = min(6, max(2, int(item.get("level", 2)) + 1))
                lines.append(f"{'#' * level} {text}")
            elif kind == "li":
                lines.append(f"- {text}")
            elif kind == "pre":
                lines.append("```")
                lines.append(text)
                lines.append("```")
            else:
                lines.append(text)
            lines.append("")

    links = manifest.get("links", [])
    if links:
        lines.append("## Links")
        lines.append("")
        for link in links:
            label = link.get("text") or link.get("url", "")
            target = link.get("target_page_id")
            suffix = f" → `{target}`" if target else ""
            nav = " (nav)" if link.get("is_nav") else ""
            lines.append(f"- [{label}]({link.get('url', '')}){suffix}{nav}")
        lines.append("")

    forms = manifest.get("forms", [])
    if forms:
        lines.append("## Forms")
        lines.append("")
        for form in forms:
            lines.append(
                f"### `{form.get('form_id')}` — {form.get('method', 'GET')} {form.get('action_url', '')}"
            )
            lines.append("")
            for field in form.get("fields", []):
                bits = [f"`{field.get('name', '')}`", field.get("input_type", "text")]
                if field.get("label"):
                    bits.append(f'label: "{field["label"]}"')
                if field.get("required"):
                    bits.append("required")
                if field.get("options"):
                    bits.append("options: " + ", ".join(field["options"][:12]))
                lines.append("- " + " · ".join(bits))
            if form.get("submit_labels"):
                lines.append("- submit: " + ", ".join(form["submit_labels"]))
            lines.append("")

    images = manifest.get("images", [])
    if images:
        lines.append("## Images")
        lines.append("")
        for image in images[:30]:
            alt = image.get("alt") or "(no alt)"
            lines.append(f"- {alt}: {image.get('url', '')}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"

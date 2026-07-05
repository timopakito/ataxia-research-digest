import html
import json
import os

import anthropic

DEFAULT_MODEL = "claude-sonnet-5"

DIGEST_TOOL = {
    "name": "build_digest",
    "description": "Structure the weekly digest content for the association's newsletter.",
    "input_schema": {
        "type": "object",
        "properties": {
            "intro": {
                "type": "string",
                "description": (
                    "Short intro paragraph in French (2-3 sentences), warm tone, "
                    "for patients/families of the association."
                ),
            },
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "heading": {
                            "type": "string",
                            "description": "French section heading, e.g. 'Nouveaux essais cliniques'.",
                        },
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "url": {"type": "string"},
                                    "summary": {
                                        "type": "string",
                                        "description": (
                                            "2-4 sentences in plain, non-technical French explaining "
                                            "what this is and why it may matter to patients/families."
                                        ),
                                    },
                                },
                                "required": ["title", "url", "summary"],
                            },
                        },
                    },
                    "required": ["heading", "items"],
                },
            },
        },
        "required": ["intro", "sections"],
    },
}

SYSTEM_PROMPT = """Tu rédiges une lettre d'information hebdomadaire en français pour une \
association qui accompagne des personnes atteintes d'ataxies cérébelleuses (ataxie de \
Friedreich, ataxies spinocérébelleuses, etc.) et leurs familles.

On te fournit une liste d'éléments bruts (essais cliniques, publications scientifiques, \
actualités) trouvés cette semaine, chacun avec un titre, une URL et éventuellement un \
résumé technique. Ta tâche : organiser ces éléments en sections claires et rédiger, pour \
chaque élément, un résumé court et accessible à un public non médical (pas de jargon \
non expliqué), en expliquant en quoi cela peut concerner les patients ou leurs proches.

Règles strictes :
- N'utilise que les informations et URLs fournies. N'invente aucune URL, aucun essai, \
aucune publication.
- Reprends l'URL exactement telle que fournie pour chaque élément.
- Reste factuel et prudent (ne promets rien sur l'efficacité d'un traitement en cours d'essai).
- Tu dois appeler l'outil build_digest avec le contenu structuré."""


def _format_items_for_prompt(items_by_source):
    labels = {
        "pubmed": "Publications scientifiques (PubMed)",
        "clinicaltrials": "Essais cliniques (ClinicalTrials.gov)",
        "news": "Actualités",
    }
    blocks = []
    for source, items in items_by_source.items():
        if not items:
            continue
        blocks.append(f"## {labels.get(source, source)}")
        for item in items:
            blocks.append(
                json.dumps(
                    {
                        "title": item["title"],
                        "url": item["url"],
                        "date": item["date"],
                        "snippet": item["snippet"],
                    },
                    ensure_ascii=False,
                )
            )
    return "\n".join(blocks)


def build_digest(items_by_source):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)

    user_content = (
        "Voici les nouveaux éléments trouvés cette semaine :\n\n"
        + _format_items_for_prompt(items_by_source)
    )

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[DIGEST_TOOL],
        tool_choice={"type": "tool", "name": "build_digest"},
        messages=[{"role": "user", "content": user_content}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "build_digest":
            return block.input

    raise RuntimeError("Claude did not return a build_digest tool call")


def render_html(digest):
    parts = [f"<p>{html.escape(digest['intro'])}</p>"]
    for section in digest["sections"]:
        if not section["items"]:
            continue
        parts.append(f"<h2>{html.escape(section['heading'])}</h2>")
        parts.append("<ul>")
        for item in section["items"]:
            url = item["url"]
            if not (url.startswith("http://") or url.startswith("https://")):
                continue
            title = html.escape(item["title"])
            summary = html.escape(item["summary"])
            safe_url = html.escape(url, quote=True)
            parts.append(
                f'<li><a href="{safe_url}">{title}</a><p>{summary}</p></li>'
            )
        parts.append("</ul>")
    return "\n".join(parts)

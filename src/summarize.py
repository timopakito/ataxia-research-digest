import json
import os

import anthropic

DEFAULT_MODEL = "claude-sonnet-5-5"

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
association qui accompagne des personnes atteintes d'ataxies cérébelleuses (toutes les ataxies \
SAUF l'ataxie de Friedreich) et leurs familles.

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


def _incomplete(stop_reason, detail):
    return RuntimeError(
        f"Reponse Claude incomplete ou malformee (stop_reason={stop_reason!r}) : "
        f"{detail}. Essaie d'augmenter max_tokens ou de reduire le nombre d'elements."
    )


def _validate_digest(digest, stop_reason):
    """Sanity-check the tool_use input against the shape render_pdf expects.

    The JSON schema passed to Claude is a generation hint, not an enforced
    contract: a truncated response (stop_reason == "max_tokens") or a model
    slip-up can still come back with the wrong shape, e.g. a 'sections' entry
    that's a bare string instead of {"heading": ..., "items": [...]}. Catch
    that here with a clear error instead of letting render_pdf crash deep
    inside a loop.
    """
    if not isinstance(digest, dict) or "sections" not in digest:
        raise _incomplete(stop_reason, "pas de 'sections' dans le digest")

    if not isinstance(digest["sections"], list):
        raise _incomplete(
            stop_reason,
            f"'sections' devrait etre une liste, recu {type(digest['sections']).__name__}",
        )

    for i, section in enumerate(digest["sections"]):
        if not isinstance(section, dict) or "heading" not in section or "items" not in section:
            raise _incomplete(
                stop_reason,
                f"sections[{i}] devrait etre un objet {{heading, items}}, recu {section!r}",
            )
        if not isinstance(section["items"], list):
            raise _incomplete(
                stop_reason,
                f"sections[{i}]['items'] devrait etre une liste, recu {type(section['items']).__name__}",
            )
        for j, item in enumerate(section["items"]):
            if not isinstance(item, dict) or not {"title", "url", "summary"} <= item.keys():
                raise _incomplete(
                    stop_reason,
                    f"sections[{i}]['items'][{j}] devrait etre un objet "
                    f"{{title, url, summary}}, recu {item!r}",
                )


def build_digest(items_by_source):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL

    user_content = (
        "Voici les nouveaux éléments trouvés cette semaine :\n\n"
        + _format_items_for_prompt(items_by_source)
    )

    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        tools=[DIGEST_TOOL],
        tool_choice={"type": "tool", "name": "build_digest"},
        messages=[{"role": "user", "content": user_content}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "build_digest":
            digest = block.input
            _validate_digest(digest, response.stop_reason)
            return digest

    raise RuntimeError(
        f"Claude did not return a build_digest tool call (stop_reason={response.stop_reason!r})"
    )

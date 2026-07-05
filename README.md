# Veille ataxies cérébelleuses

Pipeline hebdomadaire qui surveille PubMed, ClinicalTrials.gov et l'actualité (Google
News) pour les ataxies cérébelleuses (ataxie de Friedreich, ataxies spinocérébelleuses),
résume les nouveautés en français avec Claude, et envoie un email hebdomadaire à
l'association.

## Fonctionnement

1. `src/collectors/` récupère les nouveaux essais cliniques, publications et actualités
   des 7 derniers jours.
2. `src/state.py` compare avec `data/seen_ids.json` pour ne garder que les éléments
   jamais signalés auparavant.
3. `src/summarize.py` envoie ces nouveaux éléments à l'API Claude, qui structure et
   rédige un résumé en français accessible à un public non médical.
4. `src/emailer.py` envoie le résumé par email via [Resend](https://resend.com).
5. `data/seen_ids.json` est mis à jour et commité par le workflow GitHub Actions pour
   ne pas re-signaler les mêmes éléments la semaine suivante.

S'il n'y a aucun nouvel élément dans la semaine, aucun email n'est envoyé.

## Configuration

Copier `.env.example` vers `.env` et renseigner :

- `ANTHROPIC_API_KEY` — clé API Claude (https://console.anthropic.com)
- `RESEND_API_KEY` — clé API Resend (https://resend.com). **Le domaine d'envoi doit
  être vérifié dans Resend** avant d'utiliser une adresse `EMAIL_FROM` sur ce domaine ;
  pour tester rapidement sans domaine, Resend fournit un expéditeur de test.
- `EMAIL_FROM` — adresse d'expédition
- `EMAIL_TO` — un ou plusieurs destinataires séparés par des virgules
- `NCBI_API_KEY` — optionnel, augmente la limite de requêtes PubMed

Les termes de recherche (portée des maladies suivies) se modifient dans
`config/sources.yaml` sans toucher au code.

## Lancer en local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.main
```

## Déploiement (GitHub Actions)

Le workflow `.github/workflows/weekly_digest.yml` tourne chaque lundi 07:00 UTC
(modifiable) et peut aussi être lancé manuellement depuis l'onglet Actions
(`workflow_dispatch`).

Ajouter les mêmes variables que `.env` comme secrets du dépôt GitHub :
`Settings → Secrets and variables → Actions` :
`ANTHROPIC_API_KEY`, `RESEND_API_KEY`, `EMAIL_FROM`, `EMAIL_TO`, `NCBI_API_KEY` (optionnel).

Le workflow committe automatiquement `data/seen_ids.json` après chaque exécution.

# Architecture

Le dépôt est un mono-repo : `backend/` (ce document), `frontend/` (à venir), `analytics/`, orchestrés par le
`docker-compose.yaml` de la racine.

Le backend suit une **architecture modulaire (monolithe modulaire) dont chaque module est hexagonal** (ports et
adaptateurs). Une seule image Docker, lancée sous trois formes : `api`, `worker` et `beat`.

## Pourquoi ce choix

| Besoin du projet | Conséquence |
|---|---|
| Une petite équipe, un seul déploiement | Pas de microservices : l'ancien découpage (un conteneur par réseau social) multipliait le déploiement sans bénéfice. |
| La valeur est dans la logique (dédoublonnage, sentiment, seuils d'alerte) | Cette logique vit dans `domain` et `application`, sans dépendre de FastAPI, SQLAlchemy ou d'un fournisseur de scraping. |
| Sources et modèles d'analyse qui vont changer (API officielles, modèle de sentiment fine-tuné) | Ils sont derrière des ports (`Collector`, `SentimentAnalyzer`) : on remplace un adaptateur sans toucher au reste. |
| Possibilité d'extraire un module en service plus tard | Les modules ne se parlent que par leur `public.py`. |

Une hexagonale « pure » appliquée partout aurait été disproportionnée pour du CRUD. Elle est appliquée à chaque module,
mais les modules simples (`identity`, `watches`) restent minces.

## Carte du code

```
backend/yimba/
├── shared/            noyau partagé sans dépendance : erreurs, horloge, pagination, SourceKind
├── infrastructure/    outillage technique des adaptateurs sortants (SQLAlchemy, types)
├── modules/
│   ├── analysis/      langue, sentiment, émotion d'un texte
│   ├── watches/       les veilles : mots-clés, sources, fréquence, seuils
│   ├── mentions/      publications normalisées, enrichies, dédoublonnées ; requêtes et statistiques
│   ├── collection/    planification et exécution de la collecte, un collecteur par source
│   ├── alerts/        alerte quand la part de négatif dépasse le seuil d'une veille
│   └── identity/      authentification et permissions, déléguées au service auth existant
│       (chaque module : domain/ application/ adapters/ public.py)
├── entrypoints/       adaptateurs entrants : api (FastAPI), worker (Celery), cli (Typer)
├── bootstrap.py       racine de composition : seul endroit qui relie ports et adaptateurs
└── config.py          configuration par variables d'environnement
```

### Dans un module

```
adapters/     implémentent les ports (SQL, HTTP, YouTube, RSS...) ──┐
application/  cas d'usage + ports (interfaces)                      ├─ les dépendances vont vers le bas
domain/       entités, objets-valeur, règles métier                 ┘
public.py     la seule surface importable par les autres modules
```

### Entre modules

```
alerts, collection
      │
mentions, watches
      │
analysis, identity
```

Un module ne dépend que des modules situés plus bas, et seulement via leur `public.py`. Quand `collection` doit parler
à `mentions` ou `watches`, un adaptateur traduit entre les deux vocabulaires (`MentionsItemSink`, `DirectoryWatchCatalog`) :
`collection` ne connaît ni les tables ni les entités des autres modules.

### Ce qui est vérifié automatiquement

- `lint-imports` (contrats dans `backend/pyproject.toml`) : sens des couches, indépendance des modules frères, domaine sans
  framework ni base de données, application sans SQLAlchemy/FastAPI/httpx.
- `backend/tests/test_architecture.py` : un module n'importe un autre module que par son `public.py`.

## Chaîne de collecte

```
beat (chaque minute) ──► yimba.plan ──► pour chaque (veille, source) dû ──► yimba.collect
                                                                               │
   Collector.collect ─► RawArchive ─► ItemSink ─► IngestMentions ─► TextAnalyzer ─► MentionRepository
   (YouTube, Bluesky,   (raw_items)   (collection)  normalise, dédoublonne, anonymise    │
    Meta, RSS, GDELT)                                                                    └─► EvaluateAlerts ─► Notifier

beat (chaque jour) ──► yimba.purge_raw ──► supprime les raw_items non revus depuis RAW_RETENTION_DAYS
```

- Une collecte est enregistrée (`collection_runs`) avec son statut et son erreur éventuelle ; un échec d'une source
  n'arrête jamais le worker.
- Une exécution « en cours » depuis plus de 30 minutes est considérée comme morte et peut être relancée.
- Aucune requête HTTP utilisateur ne déclenche de collecte : l'API ne lit que la base.
- Les auteurs sont stockés sous forme de hash salé (`AUTHOR_HASH_SALT`), jamais en clair, dans les mentions. Les
  réponses brutes (`raw_items`) les contiennent en clair : c'est pourquoi elles sont purgées.

## Analytique et modèles

```
tables de l'application ──► dbt (analytics/dbt) ──► schéma analytics (marts, sans texte ni auteur) ──► Superset
                                   │                                │
                              tests dbt                     Pandera (analytics/quality)

mentions ──► yimba annotation export ──► Label Studio ──► export JSON ──► yimba annotation evaluate ──► MLflow
```

- L'image `analytics` (dbt-core, Pandera) est séparée de l'application : ses dépendances ne touchent pas l'API.
- Superset se connecte avec le rôle `superset_reader`, qui ne lit que le schéma `analytics`.
- L'évaluation est un cas d'usage du module `analysis` (`EvaluateAnalyzer`) ; Label Studio et MLflow sont des
  adaptateurs (`label_studio.py`, `mlflow_tracker.py`) derrière le port `ExperimentTracker`.
- `build_text_analyzer` garde un analyseur par configuration et par processus : un modèle transformers n'est chargé
  qu'une fois.

## Exploitation

- **Flower** (`yimba flower`, service `flower`) : workers, file d'attente, tâches. Lié à `127.0.0.1`, protégé par
  `FLOWER_BASIC_AUTH`, refuse de démarrer sans en production.
- **GlitchTip** (profil `observability`) : reçoit les exceptions et les logs ERROR de l'API et du worker par le SDK
  Sentry (`SENTRY_DSN`), sans données personnelles (`send_default_pii=False`).

## Ajouter une source

1. Écrire un `Collector` qui appelle l'API **officielle** de la source (pas de scraping, pas de revendeur de données
   comme Apify ou Mention).
   Un mot-clé en échec ne doit pas faire perdre les autres : voir `collect_partially`.
2. L'enregistrer dans `backend/yimba/modules/collection/adapters/factory.py`.
3. Ajouter la valeur à `SourceKind` (`backend/yimba/shared/source.py`).

Aucun autre module ne change.

## Changer de modèle de sentiment

Implémenter `SentimentAnalyzer` (voir `adapters/transformers_sentiment.py`) et le choisir avec `ANALYSIS_ENGINE`.
L'analyse par lexique fournie par défaut est une **base de départ non validée** : elle sert à faire tourner le produit de
bout en bout, pas à éclairer une décision. Avant usage réel, constituer un échantillon annoté (français, nouchi) et
mesurer chaque moteur dessus.

## Base de données

PostgreSQL. Migrations Alembic dans `backend/migrations/` (`make migrate`). Les tests tournent sur SQLite par défaut et sur
PostgreSQL avec `TEST_DATABASE_URL`.

# Backend (yimba-api)

API HTTP (FastAPI), workers de collecte et d'analyse (Celery) et planificateur (beat), dans une seule image. Architecture
modulaire, chaque module hexagonal : voir [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).

Les commandes ci-dessous se lancent depuis `backend/` ; la pile complète se démarre depuis la racine (`make run`).

## Fonctionnement

### Vue d'ensemble

L'API ne fait que lire et écrire en base : aucune requête HTTP ne déclenche de collecte. La collecte et l'analyse
tournent dans les workers, planifiés par beat à travers Redis.

```mermaid
flowchart LR
    client(["Frontend / client HTTP"]) -->|"Bearer jeton"| api["API<br/>FastAPI"]
    api -->|"jeton et permissions"| auth[("Service<br/>d'authentification")]
    api -->|"veilles, mentions,<br/>statistiques, alertes"| db[("PostgreSQL")]

    beat["Beat<br/>Celery"] -->|"chaque minute : yimba.plan<br/>chaque jour : yimba.purge_raw"| redis[("Redis<br/>file « yimba »")]
    redis --> worker["Workers<br/>Celery"]
    worker -->|"recherche par mot-clé"| sources[["API officielles<br/>News RSS · GDELT · YouTube<br/>Bluesky · Facebook · Instagram"]]
    worker -->|"collectes, réponses brutes,<br/>mentions, alertes"| db
    worker -.->|"alerte"| notifier["Notifier<br/>(journaux)"]

    worker -.->|"tâches"| flower["Flower"]
    api -.->|"erreurs"| glitchtip["GlitchTip"]
    worker -.->|"erreurs"| glitchtip
    db -->|"dbt"| marts[("schéma analytics")]
    marts --> superset["Superset"]
```

### Workflow de collecte

Toutes les minutes, beat demande la planification ; chaque couple (veille, source) dont la fréquence est écoulée part
dans la file, et un worker le collecte. Un échec est enregistré dans `collection_runs` sans arrêter le worker.

```mermaid
sequenceDiagram
    autonumber
    participant B as Beat
    participant Q as Redis
    participant W as Worker
    participant DB as PostgreSQL
    participant S as API de la source

    B->>Q: yimba.plan (toutes les 60 s)
    Q->>W: yimba.plan
    W->>DB: veilles actives et dernière collecte de chaque (veille, source)
    W->>Q: yimba.collect(veille, source) pour chaque couple dû
    Q->>W: yimba.collect
    W->>DB: collection_runs : « running »
    loop chaque mot-clé de la veille
        W->>S: recherche
        S-->>W: publications
    end
    W->>DB: raw_items : réponses brutes (une ligne par publication)
    W->>W: ingestion (voir ci-dessous)
    W->>DB: mentions : les nouvelles seulement
    W->>DB: collection_runs : « succeeded » ou « failed »
    opt de nouvelles mentions ont été enregistrées
        W->>DB: part de mentions négatives sur 24 h
        opt seuil atteint et pas d'alerte depuis 6 h
            W->>DB: watch_alerts : nouvelle alerte
            W->>W: Notifier
        end
    end
```

- **Due** : jamais collectée, ou fréquence de la veille écoulée depuis la dernière collecte ; une collecte restée
  « running » plus de 30 minutes est considérée comme morte et relancée.
- **Échecs** : un mot-clé en échec n'annule pas les autres ; la collecte n'échoue que si tous échouent.
- **Purge** : chaque jour, `yimba.purge_raw` supprime les `raw_items` non revus depuis `RAW_RETENTION_DAYS` jours.

### Ingestion d'une publication

```mermaid
flowchart LR
    item["Publication collectée"] --> valid{"Texte et identifiant<br/>présents ?"}
    valid -- non --> skipped["Ignorée"]
    valid -- oui --> seen{"Déjà vue pour cette veille ?<br/>même identifiant ou même texte"}
    seen -- oui --> duplicate["Doublon"]
    seen -- non --> analysis["Analyse : langue, sentiment, émotion<br/>(lexique ou transformers)"]
    analysis --> anonymise["Auteur remplacé par un hash salé"]
    anonymise --> stored[("mentions")]
```

### Traitement d'une requête

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API
    participant Auth as Service d'authentification
    participant DB as PostgreSQL

    C->>A: GET /watches/{id}/mentions (Authorization: Bearer)
    A->>Auth: valider le jeton
    Auth-->>A: utilisateur, sinon 401
    A->>Auth: permission « mention:can-read »
    Auth-->>A: accordée, sinon 403
    A->>DB: la veille appartient-elle à l'utilisateur ?
    alt non (ou veille inconnue)
        A-->>C: 404
    else oui
        A->>DB: mentions filtrées et paginées
        A-->>C: 200 JSON
    end
```

Le service d'authentification injoignable donne une 502.

## Sources

Uniquement des API officielles : ni scraping, ni revendeur de données. Une source sans identifiants est ignorée.

| Source | API | Identifiants (`.env`) | Ce qui est collecté | Limites |
|---|---|---|---|---|
| `news` | Google News RSS + flux RSS ajoutés | aucun (`NEWS_EXTRA_FEEDS`) | articles | — |
| `gdelt` | GDELT DOC 2.0 (presse mondiale) | aucun (`GDELT_ENABLED`) | titres d'articles des dernières 24 h | une requête toutes les 5 s par adresse IP (nouvel essai automatique) |
| `youtube` | YouTube Data API v3 | `YOUTUBE_API_KEY` | vidéos et commentaires des premières vidéos | 10 000 unités/jour, ~106 par mot-clé : fréquence 6 h ou 24 h |
| `bluesky` | AT Protocol | `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD` | publications | — |
| `facebook` | Graph API (Pages) | `META_ACCESS_TOKEN`, `FACEBOOK_PAGE_IDS` | publications des Pages suivies qui citent un mot-clé, et leurs commentaires | pas de recherche sur tout Facebook ; Pages non gérées : fonctionnalité « Page Public Content Access » |
| `instagram` | Graph API (hashtags) | `META_ACCESS_TOKEN`, `INSTAGRAM_ACCOUNT_ID` | publications des dernières 24 h par hashtag | compte professionnel, 30 hashtags distincts par 7 jours, ni commentaires ni auteur |

Les réponses brutes des API sont gardées dans `raw_items` (une ligne par publication, mise à jour à chaque passage) pour
pouvoir corriger une conversion après coup ; elles contiennent des données personnelles en clair et sont supprimées après
`RAW_RETENTION_DAYS` jours sans être revues.

## API

| Méthode | Chemin | Rôle |
|---|---|---|
| POST, GET | `/watches` | créer une veille, lister les siennes |
| GET, PATCH, DELETE | `/watches/{id}` | consulter, modifier, supprimer |
| GET | `/watches/{id}/mentions` | mentions (filtres : source, langue, sentiment, émotion, dates, texte) |
| GET | `/watches/{id}/stats` | totaux et séries (`group_by=day\|source\|language`) |
| GET | `/watches/{id}/alerts` | alertes levées |
| POST | `/watches/{id}/alerts/{alert_id}/acknowledge` | marquer une alerte comme traitée |
| GET | `/@ping` | sonde de vie |

Chaque route exige `Authorization: Bearer <token>` et une permission (voir `appdesc.yml`). Une veille n'est visible que
par son propriétaire.

## Développement

En local, sans Docker (la configuration est lue dans le `.env` de la racine, puis dans `backend/.env` s'il existe) :

```sh
make install                         # poetry install
poetry run yimba db-upgrade          # DATABASE_URL pointe par défaut sur un fichier SQLite
poetry run yimba api --reload
poetry run yimba worker              # nécessite Redis
poetry run yimba beat
poetry run yimba flower              # http://localhost:5555
poetry run yimba collect <watch_id> news   # collecter une source tout de suite, sans file d'attente
```

Vérifications :

```sh
make check          # black, isort, flake8, règles d'architecture, tests
TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/yimba_test make tests   # tests sur PostgreSQL
```

## Image Docker (`backend/Dockerfile`)

Une image, trois rôles (`api` par défaut, `worker`, `beat`), construite en deux étapes : Poetry installe les
dépendances verrouillées (`poetry.lock`) dans un environnement isolé, l'image finale ne garde que cet environnement et
le code, déjà compilés en bytecode, et tourne en utilisateur non privilégié. Le contexte de construction ne contient que
le nécessaire (`.dockerignore` en liste blanche : ni `.env`, ni tests, ni `.git`).

Un seul workflow, [`.github/workflows/backend.yaml`](../.github/workflows/backend.yaml), déclenché quand `backend/`,
`analytics/` ou `docker-compose.yaml` changent :

| Job | Pull request | Push sur `main`, `preprod`, `develop` |
|---|---|---|
| `check` : lint, architecture, tests SQLite et PostgreSQL, migrations, dbt et Pandera | oui | oui |
| `image` : construction de l'image et test de démarrage | oui | oui |
| `publish` : image de base et variante `-ml` poussées sur GHCR (`latest` / `preprod` / `dev`, plus une étiquette par commit) | non | si `check` et `image` réussissent |


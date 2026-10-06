# yimba-api

Yimba est une plateforme de **veille d'opinion et d'émotions en ligne** : elle collecte des publications (réseaux sociaux,
presse), les analyse (langue, sentiment, émotion) et alerte quand l'opinion se dégrade, pour éclairer la décision.

L'architecture est décrite dans [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Démarrage

Prérequis : Python 3.12, [Poetry](https://python-poetry.org), Docker.

```sh
cp .env.example .env         # puis renseigner les valeurs
make run                     # api + worker + beat + postgres + redis, migrations incluses via le service migrate
```

L'API écoute sur `http://localhost:8800` (documentation sur `/docs`).

En local, sans Docker :

```sh
make install
poetry run yimba db-upgrade          # DATABASE_URL pointe par défaut sur un fichier SQLite
poetry run yimba api --reload
poetry run yimba worker              # nécessite Redis
poetry run yimba beat
poetry run yimba collect <watch_id> news   # collecter une source tout de suite, sans file d'attente
```

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

## Qualité

```sh
make check          # black, isort, flake8, règles d'architecture, tests
TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/yimba_test make tests   # tests sur PostgreSQL
```

## Ce qui reste à faire avant la production

- Valider le contrat avec le service d'authentification (`AuthServiceAccessControl`, voir sa docstring).
- Valider les `mappers` Apify sur des réponses réelles des acteurs configurés.
- Remplacer l'analyse par lexique par un modèle multilingue évalué sur un corpus français et nouchi annoté.
- Rapports PDF et nuage de mots (anciens gabarits conservés dans `legacy/`).
- Conformité données personnelles (ARTCI) : durée de conservation, droit d'effacement.

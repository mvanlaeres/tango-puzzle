# Tango Puzzle

Un jeu de puzzle inspiré du Tango de LinkedIn, jouable dans le navigateur et propulsé par une API FastAPI.

## Principe du jeu

La grille (4x4 ou 6x6) doit être remplie avec deux symboles — **S** (Soleil) et **L** (Lune) — en respectant ces règles :

- Chaque ligne et chaque colonne contient autant de S que de L.
- Pas plus de 2 symboles identiques consécutifs (horizontalement ou verticalement).
- Les indices entre deux cellules adjacentes indiquent si elles doivent être **égales** (=) ou **opposées** (x).

## Structure du projet

```
tango/
├── backend/
│   ├── main.py              # Application FastAPI
│   ├── puzzle/
│   │   ├── generator.py     # Génération de puzzles (backtracking)
│   │   └── validator.py     # Validation des grilles
│   ├── tests/
│   │   ├── test_generator.py
│   │   └── test_validator.py
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   └── index.html           # Interface web
└── .gitignore
```

## Lancer le projet

### Prérequis

- Python 3.12+

### Installation

```bash
cd backend
pip install -r requirements.txt
```

### Démarrer le serveur

```bash
cd backend
uvicorn main:app --reload
```

L'interface est accessible sur [http://localhost:8000](http://localhost:8000).

## API

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/puzzle` | Génère un nouveau puzzle |
| `POST` | `/validate` | Valide une grille (partielle ou complète) |
| `GET` | `/health` | Statut du serveur |

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

# MCP Référentiels

Monorepo contenant les serveurs MCP pour les référentiels numériques responsables.

## MCPs disponibles

| MCP                   | Description                                                         | Port local |
| --------------------- | ------------------------------------------------------------------- | ---------- |
| [greenit](./greenit/) | Référentiel GreenIT — bonnes pratiques éco-conception web           | 8000       |
| [rgaa](./rgaa/)       | RGAA — Référentiel Général d'Accessibilité pour les Administrations | 8001       |
| [rgesn](./rgesn/)     | RGESN — Référentiel Général d'Écoconception de Services Numériques  | 8002       |

## Package partagé

Le dossier [`core/`](./core/) contient le package `mcp-ref-core` partagé entre tous les MCPs :

- `auth.py` — gestion des tokens d'authentification
- `routes.py` — routes HTTP communes (homepage, guide, admin API)
- `_helpers.py` — fonctions de validation

## Développement

```bash
# Installer le core en mode éditable
pip install -e core/

# Tester un MCP spécifique
cd greenit/files && pytest ../tests/ -v

# Builder une image Docker (depuis la racine)
docker build -f greenit/Dockerfile -t greenit-mcp .
```

# MCP Numérique Responsable

Serveurs [MCP (Model Context Protocol)](https://modelcontextprotocol.io) donnant à Claude un accès direct aux référentiels du numérique responsable français.

## Les MCPs disponibles

### greenit — Éco-conception web

Accès au [référentiel GreenIT](https://www.greenit.fr/) (115 bonnes pratiques) pour concevoir des services numériques à faible impact environnemental.

Claude peut :

- Lister et filtrer les bonnes pratiques par phase du cycle de vie, ressource économisée, niveau de priorité
- Obtenir le détail complet d'une fiche (description, exemples, validations)
- Chercher des pratiques par mot-clé ou thème
- Comparer plusieurs fiches
- Calculer un EcoIndex pour une page web
- Identifier les pratiques prioritaires selon un contexte projet

### rgaa — Accessibilité numérique

Accès au [RGAA 4.2.1](https://www.numerique.gouv.fr/publications/rgaa-accessibilite/) (106 critères d'accessibilité) pour auditer et améliorer l'accessibilité des services publics numériques.

Claude peut :

- Consulter les 106 critères RGAA par thème ou niveau WCAG
- Chercher dans les critères et le glossaire
- Analyser statiquement une page web (~57% des critères automatisables)
- Générer une checklist d'audit personnalisée
- Calculer un taux de conformité à partir des résultats d'audit
- Choisir le type d'audit adapté (complet, rapide, complémentaire)

### rgesn — Écoconception de services numériques

Accès au [RGESN](https://ecoresponsable.numerique.gouv.fr/publications/referentiel-general-ecoconception/) — en cours d'implémentation.

## Utilisation

Les MCPs fonctionnent en deux modes selon votre situation.

### Mode stdio — usage local (sans token)

Idéal pour un usage personnel sur votre poste. Claude lance le conteneur Docker directement, aucun serveur à déployer.

**Prérequis :** Docker installé et démarré.

```bash
# Construire les images (depuis la racine du dépôt)
docker build -f greenit/Dockerfile -t greenit-mcp .
docker build -f rgaa/Dockerfile -t rgaa-mcp .
```

**Configuration Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`) :

```json
{
  "mcpServers": {
    "greenit": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "greenit-mcp"]
    },
    "rgaa": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "rgaa-mcp"]
    }
  }
}
```

**Configuration Claude Code (CLI)** :

```bash
claude mcp add greenit -- docker run --rm -i greenit-mcp
claude mcp add rgaa -- docker run --rm -i rgaa-mcp
```

### Mode HTTP — serveur partagé (avec token)

Idéal pour une équipe ou un déploiement sur serveur. Le MCP tourne en permanence et est accessible via une URL.

Demandez un token d'accès à votre administrateur, puis configurez Claude avec l'URL et le token fournis.

**Claude Desktop** :

```json
{
  "mcpServers": {
    "greenit": {
      "type": "http",
      "url": "https://mcp.example.com/greenit",
      "headers": {
        "Authorization": "Bearer <votre-token>"
      }
    },
    "rgaa": {
      "type": "http",
      "url": "https://mcp.example.com/rgaa",
      "headers": {
        "Authorization": "Bearer <votre-token>"
      }
    }
  }
}
```

**Claude Code (CLI)** :

```bash
claude mcp add greenit --transport http --url https://mcp.example.com/greenit \
  --header "Authorization: Bearer <votre-token>"
claude mcp add rgaa --transport http --url https://mcp.example.com/rgaa \
  --header "Authorization: Bearer <votre-token>"
```

## Déploiement

Pour déployer les MCPs sur un serveur, générer des tokens et configurer l'environnement, consultez le [guide de déploiement](docs/DEPLOIEMENT.md).

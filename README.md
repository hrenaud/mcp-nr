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

Accès au [RGESN 2024](https://ecoresponsable.numerique.gouv.fr/publications/referentiel-general-ecoconception/) (78 critères d'écoconception) pour évaluer et améliorer l'impact environnemental des services numériques.

Claude peut :

- Lister et filtrer les 78 critères par thème, priorité ou difficulté
- Obtenir le détail complet d'un critère (objectif, mise en œuvre, moyen de contrôle)
- Chercher par mot-clé dans les critères
- Identifier les 30 critères prioritaires à traiter en premier
- Générer une checklist d'audit filtrée
- Calculer un taux de conformité pondéré par priorité

## Connexion à Claude

Demandez l'URL et un token d'accès à votre administrateur, puis ajoutez les MCPs à Claude.

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`) :

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
    },
    "rgesn": {
      "type": "http",
      "url": "https://mcp.example.com/rgesn",
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
claude mcp add rgesn --transport http --url https://mcp.example.com/rgesn \
  --header "Authorization: Bearer <votre-token>"
```

Redémarrez Claude Desktop ou relancez `claude` pour que les MCPs soient actifs.

## Pour aller plus loin

- **Déployer les MCPs sur un serveur** (Docker, tokens, reverse proxy) → [docs/DEPLOIEMENT.md](docs/DEPLOIEMENT.md)
- **Lancer les MCPs en local** sans serveur (usage avancé, Docker requis) → [docs/DEPLOIEMENT.md](docs/DEPLOIEMENT.md), section _Mode stdio_
- **Outils GreenIT avec exemples de prompts** → [greenit/docs/GUIDE_DEVELOPPEMENT.md](greenit/docs/GUIDE_DEVELOPPEMENT.md)
- **Outils RGAA avec exemples de prompts** → [rgaa/docs/GUIDE_DEVELOPPEMENT.md](rgaa/docs/GUIDE_DEVELOPPEMENT.md)
- **Outils RGESN avec exemples de prompts** → [OUTILS.md](OUTILS.md), section _RGESN MCP_
- **Structure et outils par MCP** (dev/archi) → [greenit/README.md](greenit/README.md), [rgaa/README.md](rgaa/README.md), [rgesn/README.md](rgesn/README.md)

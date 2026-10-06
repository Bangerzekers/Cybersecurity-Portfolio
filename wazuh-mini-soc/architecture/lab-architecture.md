# Architecture du lab

```
                 ┌───────────────────────────┐
                 │   Serveur Wazuh (Debian)  │
                 │   Mini-PC — Manager +     │
                 │   Indexer + Dashboard     │
                 └─────────────┬─────────────┘
                               │
                 Réseau local domestique
                   192.168.1.0/24
                               │
        ┌──────────────────────┴──────────────────────┐
        │                                              │
┌───────┴────────┐                            ┌────────┴────────┐
│ Agent Windows   │                            │  Agent Windows  │
│ WIN-LAB-01      │                            │  WIN-LAB-02     │
│ (Windows 11)    │                            │  (Windows 11)   │
└─────────────────┘                            └─────────────────┘
```

## Composants

| Composant | Rôle | Détail |
|---|---|---|
| Serveur Wazuh | Manager, indexer, dashboard | Mini-PC reconverti, Debian, installation "all-in-one" |
| WIN-LAB-01 / WIN-LAB-02 | Endpoints surveillés | Windows 11, Wazuh Agent, Script Block Logging activé |
| Réseau | Transport agents ↔ manager | Réseau domestique standard, pas de VLAN dédié |

## Logging activé côté Windows

- **PowerShell Script Block Logging** (stratégie locale / GPO) : journalise le contenu exécuté des scripts PowerShell, y compris les commandes obfusquées une fois désobfusquées à l'exécution — Event ID **4104**
- Les logs sont collectés par le Wazuh Agent et transmis au manager pour être évalués contre les règles de détection (dont la règle custom `100100`)

## Pourquoi ce choix de logging

Le Script Block Logging est une des sources les plus riches pour la détection d'activité PowerShell malveillante (living-off-the-land), car il capture le contenu réel exécuté plutôt que la seule ligne de commande initiale, qui peut être trompeuse ou encodée en base64.

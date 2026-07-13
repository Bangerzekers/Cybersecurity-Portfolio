# Sauvegarde automatisée de configurations réseau — Ansible / HPE Aruba

> Projet réel, issu de mon activité d'administration réseau. Les adresses IP, noms de sites et détails d'infrastructure ci-dessous sont anonymisés/génériques.

## 1. Contexte

Gestion d'un parc de switches HPE Aruba dans un environnement multi-sites incluant des zones cliniques et administratives, sans solution de sauvegarde automatisée des configurations. En cas de panne matérielle ou d'erreur de configuration, la restauration dépendait d'interventions manuelles — risque opérationnel et perte de traçabilité des changements.

## 2. Objectif

Mettre en place une sauvegarde automatisée, planifiée et versionnée des configurations pour l'ensemble du parc, en tenant compte de l'hétérogénéité des modèles :

- Switches Aruba OS-Switch/ProCurve (séries 2530, 2920), plus anciens, gérés en SSH classique
- Switches Aruba CX, plus récents, avec leur propre syntaxe et API

## 3. Environnement

- Ansible (contrôleur sur un poste/serveur Linux dédié)
- Connexion SSH vers un sous-réseau de management dédié (VLAN isolé)
- Ansible Vault pour la gestion des identifiants
- Cron pour la planification des sauvegardes
- Dépôt de configs versionné (git ou stockage horodaté)

## 4. Architecture du projet

```
ansible-aruba-backups/
├── inventory/
│   └── switches.ini          # Inventaire organisé par site / groupe logique
├── playbooks/
│   ├── backup_procurve.yml   # Playbook pour les modèles OS-Switch/ProCurve
│   ├── backup_cx.yml         # Playbook pour les modèles Aruba CX
│   └── backup_master.yml     # Playbook orchestrateur (inclut les deux ci-dessus)
├── group_vars/
│   └── vault.yml              # Identifiants chiffrés (Ansible Vault)
└── README.md
```

## 5. Inventaire (extrait, anonymisé)

```ini
[site_a_procurve]
sw-a-01 ansible_host=10.0.3.11
sw-a-02 ansible_host=10.0.3.12

[site_b_procurve]
sw-b-01 ansible_host=10.0.3.21

[site_a_cx]
sw-a-cx-01 ansible_host=10.0.3.31

[procurve:children]
site_a_procurve
site_b_procurve

[cx:children]
site_a_cx
```

## 6. Principe des playbooks

**Modèles OS-Switch/ProCurve** — connexion SSH, exécution de `show running-config`, récupération et sauvegarde du output horodaté localement.

**Modèles Aruba CX** — utilisation du module réseau adapté (ou appel API CX si disponible), export de la configuration au format natif.

**Playbook orchestrateur** — exécute les deux playbooks selon les groupes d'inventaire concernés, centralise les logs d'exécution, et notifie en cas d'échec de connexion à un équipement.

## 7. Sécurité des identifiants

Les identifiants SSH ne sont jamais en clair dans les fichiers du projet : ils sont stockés dans `group_vars/vault.yml`, chiffré avec `ansible-vault`. Le mot de passe du vault est fourni au moment de l'exécution (ou via un fichier de mot de passe protégé, hors du dépôt).

```bash
ansible-vault encrypt group_vars/vault.yml
ansible-playbook playbooks/backup_master.yml --ask-vault-pass
```

## 8. Planification

Exécution automatique via cron, avec rotation des sauvegardes (conservation d'un historique glissant plutôt qu'un accumulation infinie) et alerte en cas d'échec.

```
0 2 * * * ansible-playbook /opt/ansible-aruba-backups/playbooks/backup_master.yml --vault-password-file /etc/ansible/.vault_pass >> /var/log/aruba-backup.log 2>&1
```

## 9. Bénéfices apportés

- Restauration rapide en cas de panne ou de mauvaise manipulation
- Historique des configurations exploitable pour audit/traçabilité
- Réduction du risque opérationnel dans un environnement sensible (santé)
- Base réutilisable pour étendre l'automatisation à d'autres tâches (durcissement, conformité, inventaire)

## 10. Limites actuelles et pistes d'amélioration

- Pas encore de vérification automatique d'intégrité post-restauration
- Le versionnement pourrait être migré vers un dépôt git dédié avec diff automatique entre sauvegardes
- Ajout possible d'une détection de drift de configuration (écart entre config attendue et config réelle)

## Compétences démontrées

Administration réseau, Ansible, SSH, gestion de secrets (Vault), segmentation VLAN, automatisation d'infrastructure, hygiène de sécurité opérationnelle, documentation technique.

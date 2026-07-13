# Portfolio Cybersécurité — Paul Jacquet

Professionnel IT orienté **cybersécurité opérationnelle**, avec une expérience concrète en administration réseau (infrastructure HPE Aruba en environnement de santé), support N2, environnements Microsoft (365, Exchange Online, SharePoint, Power Automate) et fondamentaux réseau (TCP/IP, VLAN, segmentation, pare-feu).

Ce portfolio présente deux types de contenu, clairement distingués :

- **Projets réels**, issus de mon activité professionnelle (anonymisés) ;
- **Notes de méthodologie**, où je détaille comment j'aborderais un scénario de sécurité donné (investigation SOC, audit IAM, gestion des vulnérabilités) — utile pour montrer ma logique et mes connaissances techniques, même sans lab dédié réalisé pour l'occasion.

> Je suis actuellement en transition vers un poste 100% cybersécurité et je complète activement ce portfolio avec des labs pratiques. Les projets ci-dessous seront enrichis au fur et à mesure.

## Projets réels

### 1. Sauvegarde automatisée de configurations réseau — Ansible / HPE Aruba

Automatisation via Ansible du backup de configuration pour un parc de switches HPE Aruba (OS-Switch/ProCurve 2530, 2920, et CX) sur un réseau de management dédié (VLAN), avec inventaire structuré par site, playbooks différenciés selon les modèles, gestion des secrets via Ansible Vault et planification via cron.

[Consulter le projet](ansible-aruba-backups/README.md)

**Compétences démontrées :** administration réseau, Ansible, SSH, gestion de secrets (Vault), segmentation VLAN, automatisation, documentation d'infrastructure, hygiène de sécurité opérationnelle (accès, sauvegarde, traçabilité des changements de config).

## Notes de méthodologie

Ces documents ne décrivent pas un incident réel, mais ma démarche technique face à un scénario donné : requêtes, outils, raisonnement, priorisation. L'objectif est de montrer comment je pense et travaille, en toute transparence sur le fait qu'il s'agit d'un exercice et non d'un vécu.

### 2. Méthodologie d'investigation SOC avec Microsoft Sentinel

Démarche d'investigation face à un scénario de connexions suspectes : collecte de logs, requêtes KQL, triage, qualification, recommandations.

[Consulter](soc-sentinel/README.md) — **Compétences :** Microsoft Sentinel, KQL, Windows Event Logs, triage, chronologie d'incident.

### 3. Méthodologie d'audit de sécurité Microsoft Entra ID

Démarche d'audit d'un tenant : comptes à privilèges, MFA, accès conditionnels, comptes inactifs, principe du moindre privilège.

[Consulter](entra-id-security-audit/README.md) — **Compétences :** IAM, Entra ID, MFA, Conditional Access, RBAC, PowerShell/Graph.

### 4. Méthodologie de gestion des vulnérabilités

Démarche de scan, qualification, priorisation et remédiation sur un système type.

[Consulter](vulnerability-management/README.md) — **Compétences :** CVSS, Nmap, scanners de vulnérabilités, priorisation, reporting.

## Compétences techniques

- **Sécurité :** analyse d'événements, investigation, IAM, durcissement, gestion des vulnérabilités, segmentation réseau
- **Réseau :** TCP/IP, DNS, DHCP, VLAN, routage, pare-feu, SSH, équipements HPE Aruba
- **Automatisation :** Ansible, gestion de secrets (Vault), scripting
- **Microsoft :** Microsoft 365, Exchange Online, Entra ID, SharePoint, Power Automate, PowerShell
- **Systèmes :** Windows, Active Directory, postes de travail, support N2
- **Documentation :** procédures, rapports techniques, recommandations

## Objectif professionnel

Intégrer une équipe de cybersécurité, SOC, IAM ou sécurité réseau en Suisse, en m'appuyant sur mon expérience IT et réseau existante tout en développant mes compétences en sécurité opérationnelle.

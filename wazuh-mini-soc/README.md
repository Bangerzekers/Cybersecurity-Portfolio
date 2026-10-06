# Wazuh Mini-SOC — Lab de détection PowerShell

Lab personnel de déploiement Wazuh (SIEM/XDR open-source) pour superviser des endpoints Windows et détecter l'exécution de scripts PowerShell suspects via le Script Block Logging, avec écriture et validation d'une règle de détection custom mappée MITRE ATT&CK.

## Contexte

Objectif : me familiariser de bout en bout avec le déploiement d'un SIEM — installation du serveur, onboarding d'agents, activation du logging pertinent côté Windows, écriture d'une règle de détection, et vérification que la chaîne fonctionne réellement (du log brut à l'alerte visible dans le dashboard).

## Architecture

- **Serveur Wazuh** : mini-PC reconverti en serveur dédié, Debian, installation Wazuh "all-in-one" (manager + indexer + dashboard) en dernière version stable
- **Agents** : 2 postes Windows 11, Wazuh Agent installé, PowerShell Script Block Logging activé
- **Réseau** : réseau local domestique standard (192.168.1.0/24), pas de segmentation dédiée pour ce lab

Détail dans [`architecture/lab-architecture.md`](./architecture/lab-architecture.md).

## Détection mise en place

- Activation du Script Block Logging PowerShell côté Windows (Event ID **4104**)
- Règle de détection custom Wazuh **ID 100100** (niveau 8), groupe `windows,powershell,mini_soc` — voir [`config/local_rules.xml`](./config/local_rules.xml)
- Mapping **MITRE ATT&CK : T1059.001** (Command and Scripting Interpreter: PowerShell), tactique **Execution**

## Test de la règle

Déclenchement contrôlé depuis un agent Windows :

```powershell
$MINISOC_TEST = "MINISOC_TEST_lab_detection"
Write-Output $MINISOC_TEST
```

Le contenu du script block (capturé via l'Event ID 4104) matche le pattern de la règle `100100`, ce qui génère une alerte de niveau 8 dans le dashboard Wazuh, correctement associée à la technique MITRE T1059.001.

## Compétences démontrées

Déploiement Wazuh (manager + agents), configuration du logging Windows (Script Block Logging / Event ID 4104), écriture de règles de détection au format XML, mapping MITRE ATT&CK, validation end-to-end d'une détection (du déclenchement à l'alerte).

## Pistes d'évolution

- Ajout d'un agent Linux
- Détections complémentaires (FIM, Syscollector, SCA)
- Intégration Sysmon pour un télémétrie process plus fine
- Threat hunting via `wazuh-logtest` sur des logs historiques

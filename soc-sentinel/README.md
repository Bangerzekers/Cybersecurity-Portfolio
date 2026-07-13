# Investigation SOC avec Microsoft Sentinel

## 1. Résumé

Ce projet simule une investigation SOC sur plusieurs tentatives de connexion échouées suivies d’une connexion réussie depuis une source inhabituelle.

L’objectif est de montrer une démarche complète :

1. collecte des événements ;
2. création d’une détection ;
3. triage de l’alerte ;
4. investigation ;
5. qualification ;
6. recommandations.

## 2. Environnement

- Microsoft Sentinel ou Log Analytics Workspace
- Machine Windows 10/11 de laboratoire
- Windows Event Logs
- Microsoft Defender, si disponible
- Requêtes KQL

## 3. Scénario

Un compte utilisateur fait l’objet de nombreuses tentatives de connexion échouées. Une authentification réussie est ensuite observée depuis une adresse IP inhabituelle.

Hypothèses étudiées :

- erreur utilisateur ;
- mot de passe oublié ;
- attaque par force brute ;
- password spraying ;
- compromission de compte.

## 4. Événements utiles

| Event ID | Description |
|---|---|
| 4624 | Connexion réussie |
| 4625 | Échec de connexion |
| 4672 | Privilèges spéciaux attribués |
| 4688 | Création d’un processus |

## 5. Requêtes KQL

### Échecs de connexion

```kusto
SecurityEvent
| where EventID == 4625
| summarize FailedAttempts=count() by Account, IpAddress, bin(TimeGenerated, 10m)
| where FailedAttempts >= 5
| order by FailedAttempts desc
```

### Succès après plusieurs échecs

```kusto
let FailedLogons =
    SecurityEvent
    | where EventID == 4625
    | summarize FailedAttempts=count() by Account, IpAddress, bin(TimeGenerated, 15m)
    | where FailedAttempts >= 5;
let SuccessfulLogons =
    SecurityEvent
    | where EventID == 4624
    | project SuccessTime=TimeGenerated, Account, IpAddress, Computer;
FailedLogons
| join kind=inner SuccessfulLogons on Account, IpAddress
| where SuccessTime between (TimeGenerated .. TimeGenerated + 15m)
| project Account, IpAddress, FailedAttempts, SuccessTime, Computer
```

### Activité PowerShell

```kusto
SecurityEvent
| where EventID == 4688
| where NewProcessName endswith @"\powershell.exe"
    or NewProcessName endswith @"\pwsh.exe"
| project TimeGenerated, Account, Computer, NewProcessName, CommandLine
| order by TimeGenerated desc
```

## 6. Méthode d’investigation

- Identifier le compte concerné.
- Vérifier le nombre et la fréquence des échecs.
- Examiner l’adresse IP source.
- Rechercher une connexion réussie après les échecs.
- Vérifier les processus lancés après la connexion.
- Contrôler les changements de privilèges.
- Rechercher des événements similaires sur d’autres comptes.
- Déterminer s’il s’agit d’un incident réel ou d’un faux positif.

## 7. Chronologie

| Heure | Événement | Interprétation |
|---|---|---|
| À compléter | Plusieurs événements 4625 | Tentatives répétées |
| À compléter | Événement 4624 | Connexion réussie |
| À compléter | Processus inhabituel | Activité à qualifier |
| À compléter | Mesure de confinement | Compte sécurisé |

## 8. Conclusion

**Classification :** à compléter  
**Sévérité :** à compléter  
**Compte compromis :** oui / non / indéterminé  
**Impact :** à compléter

## 9. Recommandations

- Réinitialiser le mot de passe du compte si la compromission est confirmée.
- Révoquer les sessions actives.
- Activer ou renforcer l’authentification multifacteur.
- Vérifier les règles d’accès conditionnel.
- Bloquer temporairement la source si cela est justifié.
- Rechercher la même adresse IP dans les autres journaux.
- Mettre en place une détection des succès après plusieurs échecs.
- Documenter les faux positifs connus.

## 10. Preuves à ajouter

Placer ici des captures anonymisées :

- vue de l’incident Sentinel ;
- résultat des requêtes KQL ;
- chronologie ;
- entités liées ;
- règle analytique ;
- résultat après remédiation.

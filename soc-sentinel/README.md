# Méthodologie d'investigation SOC avec Microsoft Sentinel

> **Note de méthodologie :** ce document ne relate pas un incident réel. Il décrit la démarche technique que je suivrais face au scénario ci-dessous, pour illustrer mon raisonnement et mes connaissances en investigation SOC.

## 1. Scénario de référence

Un compte utilisateur fait l'objet de nombreuses tentatives de connexion échouées, suivies d'une authentification réussie depuis une adresse IP inhabituelle.

Hypothèses à écarter ou confirmer, dans l'ordre :
1. Erreur utilisateur / mot de passe oublié
2. Attaque par force brute ciblée
3. Password spraying (plusieurs comptes, peu de tentatives chacun)
4. Compromission effective du compte

## 2. Environnement type

- Microsoft Sentinel ou Log Analytics Workspace
- Windows Event Logs (postes + contrôleurs de domaine)
- Microsoft Defender, si disponible

## 3. Événements Windows pertinents

| Event ID | Description |
|---|---|
| 4624 | Connexion réussie |
| 4625 | Échec de connexion |
| 4672 | Privilèges spéciaux attribués |
| 4688 | Création d'un processus |

## 4. Démarche de triage

1. **Quantifier** : combien d'échecs, sur quelle fenêtre de temps, depuis combien d'IP/sources différentes.
2. **Corréler** : la connexion réussie provient-elle d'une IP jamais vue pour ce compte ? Géolocalisation cohérente avec l'utilisateur ?
3. **Contextualiser** : le compte a-t-il des privilèges élevés ? Y a-t-il eu une action sensible après la connexion (4672, 4688, accès à des ressources critiques) ?
4. **Qualifier** : faux positif, incident mineur, ou compromission avérée nécessitant escalade.

## 5. Exemple de requête KQL (échecs de connexion groupés)

```kusto
SecurityEvent
| where EventID == 4625
| summarize FailedAttempts=count() by Account, IpAddress, bin(TimeGenerated, 10m)
| where FailedAttempts >= 5
| order by FailedAttempts desc
```

Cette requête permet d'identifier rapidement les comptes et IP concentrant un nombre anormal d'échecs sur une fenêtre glissante de 10 minutes — un indicateur classique de brute force ou de password spraying.

## 6. Recommandations types en cas de confirmation

- Réinitialisation immédiate du mot de passe du compte concerné
- Révocation des sessions actives
- Vérification MFA (activation si absente)
- Blocage de l'IP source au niveau du pare-feu/Conditional Access
- Revue des accès et actions effectuées pendant la fenêtre de compromission suspectée

## Compétences illustrées

Microsoft Sentinel, KQL, lecture de logs Windows, raisonnement de triage SOC, priorisation d'incident.

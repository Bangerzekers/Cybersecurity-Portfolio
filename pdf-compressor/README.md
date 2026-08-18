[README.md](https://github.com/user-attachments/files/31178883/README.md)

# 📄 Compresseur de PDF — 100% local

Petit outil avec interface graphique pour compresser des fichiers PDF (recompression des images embarquées) **sans jamais envoyer le document sur un site tiers**.

## 🎯 Contexte / Pourquoi ce projet

La plupart des outils de compression de PDF trouvés en ligne obligent à uploader son document sur un serveur externe. Dans un contexte professionnel (documents administratifs, données sensibles, environnement hospitalier), ce n'est pas toujours souhaitable :

- **Confidentialité** : le fichier ne quitte jamais la machine, aucune donnée n'est transmise à un tiers
- **Pas de dépendance réseau** : fonctionne hors ligne
- **Pas de limite de taille/nombre de fichiers**, pas de compte à créer, pas de publicité
- **Contrôle total** sur le niveau de compression appliqué

Ce script répond à un besoin concret : compresser des PDF volumineux (scans, documents avec images) rapidement, localement, et de façon reproductible.

## ⚙️ Fonctionnalités

- Interface graphique simple (Tkinter)
- Glisser-déposer du fichier PDF dans la fenêtre (ou sélection via l'explorateur)
- 3 niveaux de compression au choix : **Léger / Moyen / Fort**
- Recompression des images internes en JPEG (qualité + redimensionnement) via **Pillow**
- Nettoyage et optimisation de la structure du PDF via **PyMuPDF**
- Barre de progression et rapport final (taille avant/après, % de réduction)

## 🧱 Stack technique

| Composant | Rôle |
|---|---|
| [PyMuPDF](https://pymupdf.readthedocs.io/) | Lecture/écriture du PDF, extraction et remplacement des images |
| [Pillow](https://pillow.readthedocs.io/) | Recompression JPEG et redimensionnement des images |
| [Tkinter](https://docs.python.org/3/library/tkinter.html) | Interface graphique |
| [tkinterdnd2](https://pypi.org/project/tkinterdnd2/) *(optionnel)* | Support du glisser-déposer natif |

## 📥 Installation

```bash
git clone https://github.com/Bangerzekers/Cybersecurity-Portfolio.git
cd Cybersecurity-Portfolio/pdf-compressor   # adapter selon l'arborescence

pip install pymupdf pillow
pip install tkinterdnd2   # optionnel, active le glisser-déposer
```

## ▶️ Utilisation

```bash
python compresseur_pdf.py
```

1. Glissez votre PDF dans la fenêtre (ou cliquez pour le sélectionner)
2. Choisissez un niveau de compression
3. Cliquez sur **Compresser le PDF**
4. Le fichier compressé est généré à côté de l'original, suffixé `_compresse.pdf`

## 🎚️ Niveaux de compression

| Niveau | Qualité JPEG | Résolution max | Cas d'usage |
|---|---|---|---|
| Léger | 90 | 2480×3508 px | Qualité quasi identique, gain modéré |
| Moyen | 82 | 1800×2400 px | Bon compromis qualité/poids (par défaut) |
| Fort | 60 | 1200×1600 px | Compression maximale, pour l'archivage ou l'envoi par mail |

## 🔒 Confidentialité

Aucune connexion réseau n'est requise pour la compression elle-même : tout le traitement se fait localement, sur la machine de l'utilisateur.

## 📌 Pistes d'amélioration

- Compression par lot (plusieurs PDF à la suite)
- Choix du dossier de sortie
- Version en ligne de commande (`--input`, `--level`) pour l'intégration dans des scripts d'automatisation

---

*Projet développé dans le cadre de ma pratique personnelle d'administration système / cybersécurité, pour disposer d'un outil de compression fiable et respectueux des données traitées.*

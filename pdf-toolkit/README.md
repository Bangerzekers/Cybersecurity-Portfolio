# 🧰 PDF Toolkit — boîte à outils PDF locale (édition, organisation, OCR, intégrité)

Application de bureau (Python + PySide6 + PyMuPDF) qui regroupe une quinzaine d'opérations PDF courantes — de l'édition directe au clic à la vérification d'intégrité entre deux versions d'un document — **sans jamais faire transiter le fichier par un service tiers**.

## 🎯 Contexte / Pourquoi ce projet

Après [`pdf-compressor`](../pdf-compressor/) et [`pdf-protector`](../pdf-protector/), deux scripts ciblés sur une seule opération, ce projet répond à un besoin plus large : disposer d'un équivalent local et hors-ligne des suites en ligne type iLovePDF ou PDF24, pour un usage administratif quotidien (environnement hospitalier notamment) sans dépendre d'un upload vers un serveur externe.

C'est le plus complet des trois projets PDF du portfolio : il couvre l'organisation de documents, l'édition visuelle directe, et deux fonctions pensées spécifiquement pour un usage sécurité — la comparaison de PDF (vérifier qu'un document n'a pas été altéré) et le caviardage réellement destructif (le texte masqué est supprimé du fichier, pas seulement recouvert).

## ⚙️ Fonctionnalités

**Édition & organisation**
- Éditeur visuel : clic sur un texte pour le remplacer sur place, ajout de texte/image en cliquant où voulu, surlignage/soulignement/barré par glisser, dessin à main levée, remplissage de champs de formulaire (texte, case à cocher, liste déroulante), annuler/rétablir
- Organisation des pages par miniatures : réordonner par glisser-déposer, pivoter, supprimer, insérer des pages d'un autre PDF ou des pages blanches
- Fusion de plusieurs PDF, découpage/extraction par plage ou par nombre de pages, rognage (crop) interactif par glisser sur l'aperçu

**Sécurité & intégrité**
- Caviardage définitif (texte réellement supprimé du fichier, pas un rectangle noir superposé), avec détection automatique de motifs sensibles (e-mail, IBAN, téléphone)
- Protection/déprotection par mot de passe (AES-256), gestion des droits d'impression/copie/modification
- **Comparaison de deux PDF** : vérification d'identité stricte par hachage, puis diff textuel et visuel page par page (différences surlignées en rouge) si le fichier a été modifié
- **Réparation** d'un PDF corrompu ou qui refuse de s'ouvrir, avec reconstruction des pages récupérables
- Nettoyage des métadonnées (auteur, XMP, JavaScript, pièces jointes embarquées) pour ne pas exposer l'origine d'un document

**Conversion**
- Filigrane, numérotation de pages, insertion de texte/image/signature, édition des métadonnées
- Images ↔ PDF (conservation de la transparence, correction d'orientation EXIF), extraction de texte, OCR (rendre un PDF scanné cherchable)

## 🧱 Stack technique

| Composant | Rôle |
|---|---|
| [PyMuPDF](https://pymupdf.readthedocs.io/) | Moteur PDF : lecture, écriture, rendu, caviardage réel (`redact_annot`), formulaires |
| [PySide6](https://doc.qt.io/qtforpython/) | Interface graphique (Qt), y compris le canevas interactif de l'éditeur visuel |
| [Pillow](https://pillow.readthedocs.io/) | Traitement d'images (conversion, orientation EXIF, diff visuel pixel à pixel) |
| [ocrmypdf](https://ocrmypdf.readthedocs.io/) + [Tesseract](https://github.com/tesseract-ocr/tesseract) | OCR — ajout d'une couche de texte invisible sur un PDF scanné |
| [fonttools](https://fonttools.readthedocs.io/) | Sous-ensemble de polices lors de la compression |

## 🖊️ L'éditeur visuel — détail technique

Le point le plus intéressant du projet : modifier un texte existant dans un PDF n'est pas une opération native du format (contrairement à un `.docx`, un PDF ne stocke pas de paragraphes réagençables). L'éditeur applique donc, à chaque clic :

1. Détection de la zone cliquée via la structure de la page (`get_text("dict")`), avec reconnaissance de la police d'origine la plus proche (gras/italique/chasse fixe) par ses flags
2. Suppression réelle du contenu existant par annotation de caviardage (`add_redact_annot` + `apply_redactions`) — le texte ou l'image sous la zone est effacé du fichier, pas recouvert
3. Réinsertion du nouveau contenu à l'identique (position, couleur de fond détectée automatiquement par échantillonnage des pixels voisins)

Un historique annuler/rétablir (jusqu'à 25 étapes) est maintenu par snapshots en mémoire du document.

## 🔍 Comparer deux PDF — détail technique

Pensé comme un outil de vérification d'intégrité documentaire :
1. Comparaison par hachage SHA-256 des fichiers bruts (sortie immédiate si identiques bit à bit)
2. Sinon, page par page : diff du texte extrait (`difflib`) + diff visuel par soustraction de pixels entre les deux rendus (`PIL.ImageChops.difference`), avec surbrillance rouge des zones modifiées
3. Signalement des pages ajoutées/supprimées et des changements de dimensions

## 🔒 Confidentialité

Aucune connexion réseau n'est utilisée pour le traitement des PDF eux-mêmes : tout se fait localement. Seule l'installation initiale des dépendances Python (et de Tesseract pour l'OCR) nécessite une connexion.

## 📥 Installation

```bash
git clone https://github.com/Bangerzekers/Cybersecurity-Portfolio.git
cd Cybersecurity-Portfolio/pdf-toolkit

pip install -r requirements.txt
```

Sous Windows, `lancer.bat` automatise la création de l'environnement virtuel et l'installation (et répare l'environnement automatiquement s'il est incomplet ou cassé). Sous Linux/macOS : `./lancer.sh`.

L'OCR nécessite en plus Tesseract installé séparément sur le poste (voir la section OCR de l'application, qui indique clairement s'il est détecté).

## ▶️ Utilisation

```bash
python app.py
```

L'interface présente les outils regroupés par catégorie dans une barre latérale (Éditer, Organiser, Optimiser, Modifier, Sécurité, Convertir, Avancé). Chaque opération traite le fichier choisi et enregistre le résultat séparément — le document d'origine n'est jamais modifié sauf demande explicite.

## ⚠️ Limites

- Pas de réagencement automatique de paragraphe : l'édition de texte remplace un bloc par un autre à la même position, sans reflow (limite inhérente au format PDF, pas à l'implémentation)
- Le caviardage automatique par motifs (e-mail, IBAN, téléphone) doit toujours être vérifié visuellement avant diffusion du document
- L'OCR dépend de la qualité du scan d'origine et nécessite Tesseract installé séparément
- La comparaison visuelle ignore les pages dont les dimensions diffèrent entre les deux fichiers

## 📌 Pistes d'amélioration

- Traitement par lot (plusieurs fichiers à la suite) pour les opérations d'organisation
- Export PDF/A pour l'archivage long terme
- Conversion PDF ↔ Word/Excel/PowerPoint
- Packaging `.exe` signé pour faciliter le déploiement en environnement d'entreprise (contournement des politiques d'accès contrôlé aux dossiers)

---

*Projet développé pour couvrir, en un seul outil local, l'essentiel des besoins de manipulation de PDF rencontrés en environnement professionnel — avec une attention particulière portée à ce qu'implique réellement « supprimer » ou « comparer » un document du point de vue de son intégrité.*

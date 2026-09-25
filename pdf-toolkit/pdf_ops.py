"""
pdf_ops.py — toutes les opérations PDF, 100 % en local (aucun accès réseau).

Ce module ne dépend PAS de l'interface graphique : il peut être importé
dans n'importe quel script Python.

Dépendances : pymupdf (>= 1.24.3), pillow
"""
from __future__ import annotations

import difflib
import hashlib
import io
import math
import os
import re
import secrets
import shutil
import subprocess
from pathlib import Path

import pymupdf

MM = 72 / 25.4  # 1 mm en points PDF

SAVE_OPTS = dict(garbage=3, deflate=True)


class PdfError(Exception):
    """Erreur lisible par l'utilisateur."""


class PasswordRequired(PdfError):
    """Le fichier est protégé et le mot de passe est manquant / incorrect."""


# --------------------------------------------------------------------------- #
#  Utilitaires
# --------------------------------------------------------------------------- #
def open_pdf(path: str, password: str = "") -> pymupdf.Document:
    """Ouvre un PDF (et le déverrouille si besoin)."""
    try:
        doc = pymupdf.open(path)
    except Exception as e:  # fichier corrompu, introuvable, etc.
        raise PdfError(f"Impossible d'ouvrir « {Path(path).name} » : {e}") from e
    if doc.needs_pass:
        if not password or not doc.authenticate(password):
            doc.close()
            raise PasswordRequired(path)
    if not doc.is_pdf:
        doc.close()
        raise PdfError(f"« {Path(path).name} » n'est pas un fichier PDF.")
    return doc


def needs_password(path: str):
    """True si chiffré, False sinon, None si le fichier est illisible (inutile de demander un mot de passe)."""
    try:
        d = pymupdf.open(path)
        r = bool(d.needs_pass)
        d.close()
        return r
    except Exception:
        return None


def quick_info(path: str) -> dict:
    """Infos rapides (sans mot de passe) : nombre de pages, chiffré ou non."""
    doc = pymupdf.open(path)
    try:
        return {
            "encrypted": bool(doc.needs_pass),
            "pages": 0 if doc.needs_pass else doc.page_count,
            "size": os.path.getsize(path),
        }
    finally:
        doc.close()


def _save_doc(doc: pymupdf.Document, out: str, **opts) -> None:
    """Enregistre puis ferme `doc`. Gère l'écrasement du fichier d'origine."""
    out = os.path.abspath(str(out))
    same = bool(doc.name) and os.path.abspath(doc.name) == out
    target = out + ".tmp" if same else out
    doc.save(target, **opts)
    doc.close()
    if same:
        os.replace(target, out)


def parse_ranges(spec: str, n: int) -> list[list[int]]:
    """
    "1-3, 5, 7-" -> [[0,1,2],[4],[6..n-1]]  (indices base 0).
    Une plage décroissante ("5-3") inverse l'ordre des pages.
    """
    groups: list[list[int]] = []
    for part in re.split(r"[;,]", spec or ""):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d*)\s*-\s*(\d*)", part)
        if m:
            a = int(m.group(1)) if m.group(1) else 1
            b = int(m.group(2)) if m.group(2) else n
        elif part.isdigit():
            a = b = int(part)
        else:
            raise ValueError(f"Plage invalide : « {part} »")
        if not (1 <= a <= n and 1 <= b <= n):
            raise ValueError(f"Plage hors limites : « {part} » (le document a {n} pages)")
        groups.append(list(range(a - 1, b)) if a <= b else list(range(a - 1, b - 2, -1)))
    if not groups:
        raise ValueError("Aucune page indiquée (exemple : 1-3, 5, 8-).")
    return groups


def pages_from_spec(spec: str, n: int) -> list[int]:
    """Vide => toutes les pages. Sinon pages uniques triées."""
    if not (spec or "").strip():
        return list(range(n))
    return sorted({p for g in parse_ranges(spec, n) for p in g})


def _flat(groups):
    return [p for g in groups for p in g]


def _unique_path(path: str) -> str:
    p = Path(path)
    k = 2
    while p.exists():
        p = Path(path).with_name(f"{Path(path).stem}_{k}{Path(path).suffix}")
        k += 1
    return str(p)


def _normalize(page: pymupdf.Page) -> None:
    """Supprime la rotation de la page (apparence identique) pour simplifier les superpositions."""
    if page.rotation:
        page.remove_rotation()


def _anchor(rect, pos: str, w: float, h: float, margin: float):
    """Coin haut-gauche d'un bloc w×h placé selon 'haut|milieu|bas-gauche|centre|droite'."""
    v, hp = pos.split("-")
    x = {"gauche": rect.x0 + margin,
         "centre": (rect.x0 + rect.x1 - w) / 2,
         "droite": rect.x1 - margin - w}[hp]
    y = {"haut": rect.y0 + margin,
         "milieu": (rect.y0 + rect.y1 - h) / 2,
         "bas": rect.y1 - margin - h}[v]
    return x, y


# --------------------------------------------------------------------------- #
#  Aperçus
# --------------------------------------------------------------------------- #
def render_thumbnails(path: str, pw: str = "", max_dim: int = 150):
    """[(largeur, hauteur, stride, octets_RGB), ...] — sans dépendance à Qt."""
    doc = open_pdf(path, pw)
    out = []
    try:
        for page in doc:
            r = page.rect
            z = max_dim / max(r.width, r.height)
            pix = page.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=False)
            out.append((pix.width, pix.height, pix.stride, bytes(pix.samples)))
    finally:
        doc.close()
    return out


def render_page(path: str, pw: str, index: int, dpi: int = 110):
    doc = open_pdf(path, pw)
    try:
        pix = doc[index].get_pixmap(dpi=dpi, alpha=False)
        return pix.width, pix.height, pix.stride, bytes(pix.samples)
    finally:
        doc.close()


# --------------------------------------------------------------------------- #
#  Fusion / organisation / découpe
# --------------------------------------------------------------------------- #
def merge(files: list[tuple[str, str]], out: str, bookmarks: bool = True) -> int:
    """files = [(chemin, mot_de_passe), ...]. Retourne le nombre total de pages."""
    if not files:
        raise ValueError("Ajoute au moins un fichier.")
    dst = pymupdf.open()
    toc = []
    for path, pw in files:
        src = open_pdf(path, pw)
        try:
            start = len(dst)
            if src.page_count:
                dst.insert_pdf(src)
                toc.append([1, Path(path).stem, start + 1])
        finally:
            src.close()
    if bookmarks and toc:
        dst.set_toc(toc)
    total = len(dst)
    dst.save(out, **SAVE_OPTS)
    dst.close()
    return total


def build_from_pages(sources: list[tuple[str, str]], items: list[tuple[int, int, int]], out: str) -> int:
    """
    Construit un PDF à partir d'une liste de pages.
    sources : [(chemin, mot_de_passe)]
    items   : [(index_source, index_page, rotation_ajoutée)] ; index_source = -1 -> page blanche A4
    """
    if not items:
        raise ValueError("Le document résultant serait vide.")
    docs: dict[int, pymupdf.Document] = {}
    dst = pymupdf.open()
    try:
        for si, pi, rot in items:
            if si < 0:
                dst.new_page(width=595, height=842)
                continue
            if si not in docs:
                docs[si] = open_pdf(*sources[si])
            src = docs[si]
            dst.insert_pdf(src, from_page=pi, to_page=pi)
            dst[-1].set_rotation((src[pi].rotation + rot) % 360)
    finally:
        for d in docs.values():
            d.close()
    n = len(dst)
    dst.save(out, **SAVE_OPTS)
    dst.close()
    return n


def extract_pages(path: str, pw: str, spec: str, out: str) -> int:
    src = open_pdf(path, pw)
    try:
        pages = _flat(parse_ranges(spec, src.page_count))
        dst = pymupdf.open()
        for p in pages:
            dst.insert_pdf(src, from_page=p, to_page=p)
    finally:
        src.close()
    dst.save(out, **SAVE_OPTS)
    dst.close()
    return len(pages)


def _split_groups(src, groups, out_dir, stem) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    created = []
    for g in groups:
        label = f"p{g[0] + 1}" if len(g) == 1 else f"p{g[0] + 1}-{g[-1] + 1}"
        target = _unique_path(os.path.join(out_dir, f"{stem}_{label}.pdf"))
        dst = pymupdf.open()
        for p in g:
            dst.insert_pdf(src, from_page=p, to_page=p)
        dst.save(target, **SAVE_OPTS)
        dst.close()
        created.append(target)
    return created


def split_by_ranges(path: str, pw: str, spec: str, out_dir: str) -> list[str]:
    src = open_pdf(path, pw)
    try:
        groups = parse_ranges(spec, src.page_count)
        return _split_groups(src, groups, out_dir, Path(path).stem)
    finally:
        src.close()


def split_every(path: str, pw: str, n: int, out_dir: str) -> list[str]:
    if n < 1:
        raise ValueError("N doit être ≥ 1.")
    src = open_pdf(path, pw)
    try:
        total = src.page_count
        groups = [list(range(i, min(i + n, total))) for i in range(0, total, n)]
        return _split_groups(src, groups, out_dir, Path(path).stem)
    finally:
        src.close()


# --------------------------------------------------------------------------- #
#  Compression
# --------------------------------------------------------------------------- #
def compress(path: str, pw: str, out: str, level: str = "moyen") -> tuple[int, int]:
    """level : 'leger' (sans perte) | 'moyen' | 'fort'. Retourne (taille_avant, taille_après)."""
    before = os.path.getsize(path)
    doc = open_pdf(path, pw)
    presets = {
        "moyen": dict(dpi_threshold=170, dpi_target=130, quality=72),
        "fort": dict(dpi_threshold=110, dpi_target=90, quality=50),
    }
    if level in presets:
        if hasattr(doc, "rewrite_images"):
            try:
                doc.rewrite_images(**presets[level])
            except Exception:
                pass
        try:  # nécessite le paquet 'fonttools' ; ignoré sinon
            doc.subset_fonts()
        except Exception:
            pass
    opts = dict(garbage=4, deflate=True, deflate_images=True, deflate_fonts=True, clean=True)
    try:
        _save_doc(doc, out, use_objstms=1, **opts)
    except TypeError:  # anciennes versions de PyMuPDF
        _save_doc(doc, out, **opts)
    return before, os.path.getsize(out)


# --------------------------------------------------------------------------- #
#  Superpositions : filigrane, numérotation, tampon
# --------------------------------------------------------------------------- #
def add_watermark(path, pw, out, text, size=70, opacity=0.25, angle=45,
                  color=(0.5, 0.5, 0.5), pages_spec="") -> int:
    if not text.strip():
        raise ValueError("Saisis le texte du filigrane.")
    doc = open_pdf(path, pw)
    idx = set(pages_from_spec(pages_spec, doc.page_count))
    for i, page in enumerate(doc):
        if i not in idx:
            continue
        _normalize(page)
        rect = page.rect
        fs = float(size)
        w = pymupdf.get_text_length(text, fontname="helv", fontsize=fs)
        max_w = (math.hypot(rect.width, rect.height) if angle else rect.width) * 0.85
        if w > max_w:  # le texte est trop long : on réduit la police
            fs *= max_w / w
            w = max_w
        c = pymupdf.Point(rect.width / 2, rect.height / 2)
        pt = pymupdf.Point(c.x - w / 2, c.y + fs * 0.3)
        page.insert_text(pt, text, fontsize=fs, fontname="helv", color=color,
                         fill_opacity=opacity, morph=(c, pymupdf.Matrix(angle)), overlay=True)
    _save_doc(doc, out, **SAVE_OPTS)
    return len(idx)


def add_page_numbers(path, pw, out, position="bas-centre", fmt="Page {n} / {N}",
                     start=1, size=10, margin=28, skip_first=False) -> int:
    try:
        fmt.format(n=1, N=1)
    except (KeyError, IndexError, ValueError):
        raise ValueError("Format invalide. Utilise {n} (numéro) et {N} (total). Ex : Page {n} / {N}")
    doc = open_pdf(path, pw)
    total = doc.page_count
    done = 0
    for i, page in enumerate(doc):
        if skip_first and i == 0:
            continue
        _normalize(page)
        label = fmt.format(n=start + i, N=total + start - 1)
        w = pymupdf.get_text_length(label, fontname="helv", fontsize=size)
        x, y = _anchor(page.rect, position, w, size * 1.2, margin)
        page.insert_text((x, y + size), label, fontsize=size, fontname="helv", color=(0, 0, 0))
        done += 1
    _save_doc(doc, out, **SAVE_OPTS)
    return done


def _image_bytes(path: str):
    """Retourne (octets, largeur_px, hauteur_px, dpi). Corrige l'orientation EXIF (photos de téléphone)."""
    from PIL import Image, ImageOps

    try:
        with Image.open(path) as im:
            src_fmt = im.format
            dpi = im.info.get("dpi", (150, 150))[0] or 150
            raw = Path(path).read_bytes()
            orient = im.getexif().get(274, 1)
            if src_fmt == "JPEG" and im.mode in ("RGB", "L") and orient in (1, None):
                return raw, im.width, im.height, dpi if 30 < dpi < 2400 else 150
            im = ImageOps.exif_transpose(im)
            has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
            buf = io.BytesIO()
            if src_fmt == "JPEG" and not has_alpha:
                im.convert("RGB").save(buf, "JPEG", quality=92)
            else:
                im.convert("RGBA" if has_alpha else "RGB").save(buf, "PNG")
            return buf.getvalue(), im.width, im.height, dpi if 30 < dpi < 2400 else 150
    except Exception as e:
        raise PdfError(f"Image illisible « {Path(path).name} » : {e}") from e


def add_stamp(path, pw, out, pages_spec="", text="", image_path="", position="bas-droite",
              size=24, margin=24, opacity=1.0, color=(0, 0, 0)) -> int:
    """Ajoute un texte (size = pt) ou une image (size = % de la largeur de page) sur les pages choisies."""
    if not text.strip() and not image_path:
        raise ValueError("Saisis un texte ou choisis une image.")
    img = _image_bytes(image_path) if image_path else None
    doc = open_pdf(path, pw)
    idx = set(pages_from_spec(pages_spec, doc.page_count))
    for i, page in enumerate(doc):
        if i not in idx:
            continue
        _normalize(page)
        r = page.rect
        if img:
            data, iw, ih, _ = img
            w = r.width * size / 100.0
            h = w * ih / iw
            x, y = _anchor(r, position, w, h, margin)
            page.insert_image(pymupdf.Rect(x, y, x + w, y + h), stream=data, overlay=True)
        else:
            lines = text.split("\n")
            lw = max(pymupdf.get_text_length(l, fontname="helv", fontsize=size) for l in lines)
            lh = size * 1.25 * len(lines)
            x, y = _anchor(r, position, lw, lh, margin)
            for k, line in enumerate(lines):
                page.insert_text((x, y + size + k * size * 1.25), line, fontsize=size,
                                 fontname="helv", color=color, fill_opacity=opacity, overlay=True)
    _save_doc(doc, out, **SAVE_OPTS)
    return len(idx)


# --------------------------------------------------------------------------- #
#  Sécurité
# --------------------------------------------------------------------------- #
def protect(path, pw, out, user_pw, owner_pw="", allow_print=True, allow_copy=False, allow_edit=False):
    """Chiffrement AES-256. Le mot de passe propriétaire (aléatoire si vide) verrouille les droits."""
    if not user_pw:
        raise ValueError("Le mot de passe d'ouverture est obligatoire.")
    doc = open_pdf(path, pw)
    perm = pymupdf.PDF_PERM_ACCESSIBILITY
    if allow_print:
        perm |= pymupdf.PDF_PERM_PRINT | pymupdf.PDF_PERM_PRINT_HQ
    if allow_copy:
        perm |= pymupdf.PDF_PERM_COPY
    if allow_edit:
        perm |= (pymupdf.PDF_PERM_MODIFY | pymupdf.PDF_PERM_ANNOTATE
                 | pymupdf.PDF_PERM_FORM | pymupdf.PDF_PERM_ASSEMBLE)
    owner = owner_pw or secrets.token_urlsafe(18)  # si owner == user, les restrictions seraient sans effet
    _save_doc(doc, out, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=user_pw,
              owner_pw=owner, permissions=perm, **SAVE_OPTS)


def unlock(path, pw, out):
    """Enregistre une copie sans mot de passe (le mot de passe doit être connu)."""
    doc = open_pdf(path, pw)
    _save_doc(doc, out, encryption=pymupdf.PDF_ENCRYPT_NONE, **SAVE_OPTS)


PRESETS = {
    "email": r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+",
    "iban": r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,4})?\b",
    "telephone": r"\+\d{1,3}(?:[ .\-]?\d{1,4}){3,5}|\b0\d(?:[ .\-]?\d{2}){4}\b|\b0\d{2}[ .]?\d{3}[ .]?\d{2}[ .]?\d{2}\b",
}


def redact(path, pw, out, terms: list[str], presets=()) -> tuple[int, list[str]]:
    """
    Caviardage DÉFINITIF (le texte sous le rectangle noir est supprimé du fichier).
    Retourne (nb_zones, termes_non_trouvés).
    """
    terms = [t.strip() for t in terms if t.strip()]
    if not terms and not presets:
        raise ValueError("Indique au moins un terme ou coche un motif automatique.")
    regexes = [re.compile(PRESETS[k]) for k in presets]
    doc = open_pdf(path, pw)
    total = 0
    hits = {t: 0 for t in terms}
    for page in doc:
        needles = set(terms)
        if regexes:
            text = page.get_text("text")
            for rx in regexes:
                needles.update(m.group(0).strip() for m in rx.finditer(text))
        found = 0
        for needle in needles:
            for r in page.search_for(needle):
                page.add_redact_annot(r, fill=(0, 0, 0))
                found += 1
                if needle in hits:
                    hits[needle] += 1
        if found:
            page.apply_redactions()
        total += found
    _save_doc(doc, out, garbage=4, deflate=True)
    return total, [t for t, c in hits.items() if c == 0]


# --------------------------------------------------------------------------- #
#  Métadonnées
# --------------------------------------------------------------------------- #
META_KEYS = ("title", "author", "subject", "keywords")


def read_metadata(path: str, pw: str = "") -> dict:
    doc = open_pdf(path, pw)
    try:
        md = doc.metadata or {}
        return {k: md.get(k) or "" for k in META_KEYS}
    finally:
        doc.close()


def write_metadata(path, pw, out, meta: dict):
    doc = open_pdf(path, pw)
    md = dict(doc.metadata or {})
    keep = {k: md.get(k) or "" for k in
            ("title", "author", "subject", "keywords", "creator", "producer", "creationDate", "modDate")}
    keep.update({k: meta.get(k, "") for k in META_KEYS})
    doc.set_metadata(keep)
    _save_doc(doc, out, **SAVE_OPTS)


def clean_metadata(path, pw, out):
    """Supprime métadonnées, XMP, JavaScript, miniatures et pièces jointes."""
    doc = open_pdf(path, pw)
    try:
        doc.scrub(attached_files=True, clean_pages=True, embedded_files=True, hidden_text=False,
                  javascript=True, metadata=True, redactions=False, remove_links=False,
                  reset_fields=False, reset_responses=False, thumbnails=True, xml_metadata=True)
    except Exception:
        pass
    doc.set_metadata({})
    try:
        doc.del_xml_metadata()
    except Exception:
        pass
    _save_doc(doc, out, garbage=4, deflate=True)


# --------------------------------------------------------------------------- #
#  Conversions
# --------------------------------------------------------------------------- #
def images_to_pdf(images: list[str], out: str, page_mode: str = "a4", margin: int = 18) -> int:
    """page_mode : 'a4' (image ajustée sur une page A4) ou 'original' (page = taille de l'image)."""
    if not images:
        raise ValueError("Ajoute au moins une image.")
    dst = pymupdf.open()
    for p in images:
        data, w, h, dpi = _image_bytes(p)
        if page_mode == "a4":
            pw_, ph_ = (595, 842) if h >= w else (842, 595)
            page = dst.new_page(width=pw_, height=ph_)
            rect = pymupdf.Rect(margin, margin, pw_ - margin, ph_ - margin)
        else:
            page = dst.new_page(width=max(72, w * 72 / dpi), height=max(72, h * 72 / dpi))
            rect = page.rect
        page.insert_image(rect, stream=data, keep_proportion=True)
    n = len(dst)
    dst.save(out, **SAVE_OPTS)
    dst.close()
    return n


def pdf_to_images(path, pw, out_dir, fmt="png", dpi=150, pages_spec="") -> list[str]:
    doc = open_pdf(path, pw)
    os.makedirs(out_dir, exist_ok=True)
    stem = Path(path).stem
    ext = "jpg" if fmt.lower() in ("jpg", "jpeg") else "png"
    created = []
    try:
        for i in pages_from_spec(pages_spec, doc.page_count):
            pix = doc[i].get_pixmap(dpi=dpi, alpha=False)
            target = _unique_path(os.path.join(out_dir, f"{stem}_p{i + 1:03d}.{ext}"))
            if ext == "jpg":
                pix.save(target, jpg_quality=90)
            else:
                pix.save(target)
            created.append(target)
    finally:
        doc.close()
    return created


def extract_text(path, pw, out_txt) -> int:
    doc = open_pdf(path, pw)
    chunks = []
    try:
        for i, page in enumerate(doc, 1):
            chunks.append(f"\n===== Page {i} =====\n{page.get_text('text')}")
    finally:
        doc.close()
    text = "".join(chunks)
    Path(out_txt).write_text(text, encoding="utf-8")
    return len(re.sub(r"===== Page \d+ =====|\s", "", text))


# --------------------------------------------------------------------------- #
#  Édition visuelle (éditeur : cliquer sur le PDF pour le modifier)
# --------------------------------------------------------------------------- #
FAMILIES = {
    "Helvetica (sans empattement)": ("helv", "hebo", "heit", "hebi"),
    "Times (avec empattement)": ("tiro", "tibo", "tiit", "tibi"),
    "Courier (chasse fixe)": ("cour", "cobo", "coit", "cobi"),
}
_FAM_KEYS = list(FAMILIES)


def font_code(family: str, bold: bool = False, italic: bool = False) -> str:
    reg, b, i, bi = FAMILIES[family]
    return bi if bold and italic else b if bold else i if italic else reg


def guess_font(font_name: str, flags: int):
    """Police d'un span PDF -> (famille de base, gras, italique) la plus proche parmi les polices standard."""
    n = (font_name or "").lower()
    bold = bool(flags & 16) or any(k in n for k in ("bold", "black", "heavy", "semibold"))
    ital = bool(flags & 2) or any(k in n for k in ("italic", "oblique"))
    mono = bool(flags & 8) or any(k in n for k in ("courier", "mono", "consol"))
    serif = (bool(flags & 4) or any(k in n for k in ("times", "georgia", "garamond", "cambria", "serif", "book"))) \
        and "sans" not in n
    return (_FAM_KEYS[2] if mono else _FAM_KEYS[1] if serif else _FAM_KEYS[0]), bold, ital


def sample_bg(page: pymupdf.Page, rect) -> tuple:
    """Couleur de fond autour d'une zone (pixel le plus fréquent sur son pourtour)."""
    r = pymupdf.Rect(rect) + (-2, -2, 2, 2)
    r &= page.rect
    if r.is_empty or r.is_infinite:
        return (1, 1, 1)
    pix = page.get_pixmap(clip=r, alpha=False)
    w, h = pix.width, pix.height
    cnt: dict = {}
    for x in range(w):
        for y in (0, h - 1):
            c = pix.pixel(x, y)
            cnt[c] = cnt.get(c, 0) + 1
    for y in range(h):
        for x in (0, w - 1):
            c = pix.pixel(x, y)
            cnt[c] = cnt.get(c, 0) + 1
    rgb = max(cnt, key=cnt.get)
    return tuple(v / 255 for v in rgb[:3])


def _redact(page, rect, fill, images=None):
    images = getattr(pymupdf, "PDF_REDACT_IMAGE_NONE", 0) if images is None else images
    page.add_redact_annot(pymupdf.Rect(rect), fill=fill, cross_out=False)
    try:
        page.apply_redactions(images=images, graphics=getattr(pymupdf, "PDF_REDACT_LINE_ART_NONE", 0))
    except TypeError:
        page.apply_redactions(images=images)


def place_text(page, rect, text, fontname, size, color=(0, 0, 0), align=0) -> float:
    """Écrit `text` dans `rect` ; réduit un peu la police, élargit puis agrandit vers le bas si ça ne rentre pas."""
    rect = pymupdf.Rect(rect)
    wide = pymupdf.Rect(rect.x0, rect.y0, max(rect.x1, page.rect.x1 - 30), rect.y1)
    cands = [(rect, size * k) for k in (1, 0.95, 0.9, 0.85)]
    cands += [(wide, size), (wide, size * 0.9)]
    r = pymupdf.Rect(wide)
    for _ in range(40):
        r = pymupdf.Rect(r.x0, r.y0, r.x1, r.y1 + size * 1.4)
        if r.y1 > page.rect.y1 - 5:
            break
        cands.append((r, size))
    for rc_, fs in cands:
        if page.insert_textbox(rc_, text, fontsize=fs, fontname=fontname, color=color, align=align) >= 0:
            return fs
    raise ValueError("Le texte ne rentre pas dans la page.")


def replace_text(page, rect, text, family, bold, italic, size, color, align=0, fill=None):
    """Remplace le texte d'une zone : efface l'ancien (vraiment), réécrit le nouveau au même endroit."""
    rect = pymupdf.Rect(rect)
    bg = fill if fill is not None else sample_bg(page, rect)
    dh = rect.height * 0.08
    _redact(page, pymupdf.Rect(rect.x0 + 0.5, rect.y0 + dh, rect.x1 - 0.5, rect.y1 - dh), bg)
    if text.strip():
        place_text(page, rect, text, font_code(family, bold, italic), size, color, align)


def erase_rect(page, rect, fill=None):
    """Gomme une zone (texte, images et dessins dessous supprimés) et la remplit avec la couleur de fond."""
    rect = pymupdf.Rect(rect)
    bg = fill if fill is not None else sample_bg(page, rect)
    _redact(page, rect, bg, images=getattr(pymupdf, "PDF_REDACT_IMAGE_PIXELS", 2))


def delete_image_at(page, rect):
    _redact(page, rect, False, images=getattr(pymupdf, "PDF_REDACT_IMAGE_REMOVE", 1))


def add_textbox(page, x, y, text, family, bold, italic, size, color, align=0):
    x1 = page.rect.x1 - 30
    x = min(x, x1 - 100)
    rect = pymupdf.Rect(max(5, x), y, x1, y + size * 1.4 * (text.count("\n") + 1))
    place_text(page, rect, text, font_code(family, bold, italic), size, color, align)


def add_image_at(page, x, y, image_path, width_pct=25):
    data, iw, ih, _ = _image_bytes(image_path)
    w = page.rect.width * width_pct / 100
    h = w * ih / iw
    x = max(0, min(x, page.rect.x1 - w))
    y = max(0, min(y, page.rect.y1 - h))
    page.insert_image(pymupdf.Rect(x, y, x + w, y + h), stream=data, overlay=True)


def markup_rect(page, rect, kind="highlight", color=(1, 1, 0)) -> int:
    """Surligne / souligne / barre les mots dont le centre est dans `rect`. Retourne le nb de mots."""
    rect = pymupdf.Rect(rect)
    words = [pymupdf.Rect(w[:4]) for w in page.get_text("words")
             if rect.contains(pymupdf.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2))]
    if not words:
        return 0
    fn = {"highlight": page.add_highlight_annot, "underline": page.add_underline_annot,
          "strikeout": page.add_strikeout_annot}[kind]
    annot = fn(words)
    annot.set_colors(stroke=color)
    annot.update()
    return len(words)


def add_ink(page, points, color=(0, 0, 0.8), width=2.0):
    annot = page.add_ink_annot([[(p[0], p[1]) for p in points]])
    annot.set_border(width=width)
    annot.set_colors(stroke=color)
    annot.update()


def add_shape_rect(page, rect, color=(0, 0, 0), width=1.5, fill=False):
    page.draw_rect(pymupdf.Rect(rect), color=color, fill=color if fill else None, width=width, overlay=True)


def widget_at(page, pt):
    for w in page.widgets() or []:
        if w.rect.contains(pymupdf.Point(pt)):
            return w
    return None


def annot_at(page, pt):
    for a in page.annots() or []:
        if pymupdf.Rect(a.rect).contains(pymupdf.Point(pt)):
            return a
    return None


# --------------------------------------------------------------------------- #
#  Structure d'une page : blocs de texte / images / champs, pour l'éditeur
# --------------------------------------------------------------------------- #
def page_structure(page: pymupdf.Page) -> dict:
    """Décrit une page pour l'éditeur : lignes de texte (regroupées par bloc visuel),
    images et champs de formulaire, chacun avec son rectangle en points PDF."""
    lines = []
    for b in page.get_text("dict").get("blocks", []):
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            spans = l["spans"]
            if not spans or not "".join(s["text"] for s in spans).strip():
                continue
            s0 = spans[0]
            fam, bold, ital = guess_font(s0["font"], s0["flags"])
            lines.append({
                "rect": list(l["bbox"]),
                "text": "".join(s["text"] for s in spans),
                "size": round(s0["size"], 1),
                "color": tuple(((s0.get("color", 0) >> shift) & 255) / 255 for shift in (16, 8, 0)),
                "family": fam, "bold": bold, "italic": ital,
            })
    images = [{"rect": list(b["bbox"])} for b in page.get_text("dict").get("blocks", []) if b["type"] == 1]
    fields = []
    for w in page.widgets() or []:
        fields.append({"rect": list(w.rect), "name": w.field_name, "type": int(w.field_type),
                       "type_name": w.field_type_string, "value": w.field_value,
                       "choices": list(w.choice_values or [])})
    return {"width": page.rect.width, "height": page.rect.height, "lines": lines,
            "images": images, "fields": fields}


def set_field_value(page, field_name: str, value):
    for w in page.widgets() or []:
        if w.field_name == field_name:
            w.field_value = value
            w.update()
            return True
    return False


# --------------------------------------------------------------------------- #
#  Rogner les pages (crop)
# --------------------------------------------------------------------------- #
def crop_pages(path, pw, out, left_mm, top_mm, right_mm, bottom_mm, pages_spec="") -> int:
    doc = open_pdf(path, pw)
    idx = set(pages_from_spec(pages_spec, doc.page_count))
    n = 0
    for i, page in enumerate(doc):
        if i not in idx:
            continue
        r = page.rect
        newrect = pymupdf.Rect(r.x0 + left_mm * MM, r.y0 + top_mm * MM,
                               r.x1 - right_mm * MM, r.y1 - bottom_mm * MM)
        if newrect.width < 10 or newrect.height < 10:
            raise ValueError("Le rognage laisse une page trop petite (ou vide) : réduis les marges.")
        page.set_cropbox(newrect)
        n += 1
    _save_doc(doc, out, **SAVE_OPTS)
    return n


def crop_preview_box(path, pw, page_index, left_mm, top_mm, right_mm, bottom_mm):
    """Rectangle de rognage (en points, origine haut-gauche) pour l'aperçu, sans rien modifier."""
    doc = open_pdf(path, pw)
    try:
        r = doc[page_index].rect
    finally:
        doc.close()
    return [left_mm * MM, top_mm * MM, r.width - right_mm * MM, r.height - bottom_mm * MM], r.width, r.height


# --------------------------------------------------------------------------- #
#  Réparer un PDF corrompu
# --------------------------------------------------------------------------- #
def repair(path, pw, out) -> tuple[int, int]:
    """Tente de rouvrir et reconstruire un PDF endommagé. Retourne (pages récupérées, pages totales)."""
    try:
        doc = pymupdf.open(path)
    except Exception as e:
        raise PdfError(f"Le fichier est trop endommagé pour être ouvert : {e}") from e
    if doc.needs_pass:
        if not pw or not doc.authenticate(pw):
            doc.close()
            raise PasswordRequired(path)
    total = doc.page_count
    try:
        doc.save(out, garbage=4, clean=True, deflate=True)
        doc.close()
        return total, total
    except Exception:
        pass
    # repli : on reconstruit un document neuf en ne gardant que les pages récupérables
    dst = pymupdf.open()
    ok = 0
    for i in range(total):
        try:
            dst.insert_pdf(doc, from_page=i, to_page=i)
            ok += 1
        except Exception:
            continue
    doc.close()
    if ok == 0:
        dst.close()
        raise PdfError("Aucune page n'a pu être récupérée dans ce fichier.")
    dst.save(out, garbage=4, deflate=True)
    dst.close()
    return ok, total


# --------------------------------------------------------------------------- #
#  Comparer deux PDF
# --------------------------------------------------------------------------- #
def compare_pdfs(path_a, pw_a, path_b, pw_b, out_dir, dpi=130) -> dict:
    if hashlib.sha256(Path(path_a).read_bytes()).digest() == hashlib.sha256(Path(path_b).read_bytes()).digest():
        return {"identical": True, "pages_a": None, "pages_b": None, "diff_pages": [], "images": [], "report": None}

    from PIL import Image, ImageChops

    da, db = open_pdf(path_a, pw_a), open_pdf(path_b, pw_b)
    na, nb = da.page_count, db.page_count
    os.makedirs(out_dir, exist_ok=True)
    diff_pages, images, report = [], [], []
    try:
        for i in range(max(na, nb)):
            if i >= na:
                report.append(f"--- Page {i + 1} : présente uniquement dans le second fichier ---")
                diff_pages.append(i + 1)
                continue
            if i >= nb:
                report.append(f"--- Page {i + 1} : présente uniquement dans le premier fichier ---")
                diff_pages.append(i + 1)
                continue
            pa, pb = da[i], db[i]
            ta, tb = pa.get_text("text"), pb.get_text("text")
            page_diff = False
            if ta != tb:
                d = list(difflib.unified_diff(ta.splitlines(), tb.splitlines(), lineterm="",
                                              fromfile=f"A — page {i + 1}", tofile=f"B — page {i + 1}"))
                if d:
                    report.append("\n".join(d))
                    page_diff = True
            pixa = pa.get_pixmap(dpi=dpi, alpha=False)
            pixb = pb.get_pixmap(dpi=dpi, alpha=False)
            if (pixa.width, pixa.height) == (pixb.width, pixb.height):
                ia = Image.frombytes("RGB", (pixa.width, pixa.height), pixa.samples)
                ib = Image.frombytes("RGB", (pixb.width, pixb.height), pixb.samples)
                if ImageChops.difference(ia, ib).getbbox():
                    mask = ImageChops.difference(ia, ib).convert("L").point(lambda v: 255 if v > 18 else 0)
                    red = Image.new("RGB", ib.size, (230, 0, 0))
                    highlighted = Image.composite(red, ib, mask)
                    out_img = Image.blend(ib, highlighted, 0.55)
                    p = _unique_path(os.path.join(out_dir, f"diff_p{i + 1:03d}.png"))
                    out_img.save(p)
                    images.append(p)
                    page_diff = True
            else:
                report.append(f"--- Page {i + 1} : dimensions différentes, comparaison visuelle ignorée ---")
                page_diff = True
            if page_diff:
                diff_pages.append(i + 1)
    finally:
        da.close()
        db.close()
    report_path = os.path.join(out_dir, "rapport_comparaison.txt")
    Path(report_path).write_text("\n\n".join(report) or "Aucune différence de texte détectée.", encoding="utf-8")
    return {"identical": False, "pages_a": na, "pages_b": nb, "diff_pages": diff_pages,
            "images": images, "report": report_path}


# --------------------------------------------------------------------------- #
#  OCR (rendre un PDF scanné cherchable) — nécessite Tesseract OCR installé
# --------------------------------------------------------------------------- #
def ocr_available() -> bool:
    return shutil.which("tesseract") is not None


def ocr_languages() -> list[str]:
    if not ocr_available():
        return []
    try:
        out = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, timeout=6).stdout
        langs = {l.strip() for l in out.splitlines()[1:] if l.strip()}
        return sorted(langs - {"osd", "equ"})  # pas de vraies langues (détection d'orientation / équations)
    except Exception:
        return []


def ocr_pdf(path, pw, out, languages="fra+eng", force=False, deskew=True, rotate=True) -> None:
    if not ocr_available():
        raise PdfError("Tesseract OCR n'est pas installé (ou introuvable dans le PATH) sur ce poste. "
                       "Installe-le — voir le README — puis réessaie.")
    import ocrmypdf
    from ocrmypdf.exceptions import (EncryptedPdfError, MissingDependencyError, PriorOcrFoundError,
                                     TaggedPDFError)

    src, tmp = path, None
    if pw:
        tmp = out + ".src_dechiffre.pdf"
        unlock(path, pw, tmp)
        src = tmp
    try:
        ocrmypdf.ocr(src, out, language=languages, force_ocr=force, skip_text=not force,
                    deskew=deskew, rotate_pages=rotate, optimize=1, progress_bar=False)
    except MissingDependencyError as e:
        raise PdfError(f"Un composant nécessaire à l'OCR est introuvable : {e}") from e
    except EncryptedPdfError as e:
        raise PdfError("Ce PDF est protégé : indique le mot de passe pour lancer l'OCR.") from e
    except PriorOcrFoundError as e:
        raise PdfError("Ce PDF contient déjà du texte. Coche « Forcer l'OCR » pour le refaire quand même.") from e
    except TaggedPDFError as e:
        raise PdfError(f"OCR impossible sur ce PDF structuré : {e}") from e
    except Exception as e:
        raise PdfError(f"L'OCR a échoué : {e}") from e
    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)

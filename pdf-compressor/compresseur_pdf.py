"""
Compresseur de PDF - Interface graphique
==========================================

Fonctionnalités :
- Glisser-déposer un PDF dans la fenêtre (ou bouton "Parcourir")
- 3 niveaux de compression (Léger / Moyen / Fort)
- Compression basée sur pymupdf + Pillow (recompression JPEG des images)
- Popup de résultat avec taille avant/après et % de réduction

Installation des dépendances :
    pip install pymupdf pillow

Pour activer le glisser-déposer (optionnel mais recommandé) :
    pip install tkinterdnd2

Sans tkinterdnd2, l'appli fonctionne quand même via le bouton "Parcourir".

Lancement :
    python compresseur_pdf.py
"""

import io
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import pymupdf
from PIL import Image

# --------------------------------------------------------------------------
# Support optionnel du glisser-déposer (tkinterdnd2)
# --------------------------------------------------------------------------
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False


# --------------------------------------------------------------------------
# Profils de compression
# --------------------------------------------------------------------------
# quality      : qualité JPEG (0-100)
# max_w/max_h  : dimensions max des images (px) - redimensionnement si dépassé
PROFILES = {
    "leger": {
        "label": "Léger",
        "description": "Qualité quasi identique, gain modéré",
        "quality": 90,
        "max_w": 2480,
        "max_h": 3508,
    },
    "moyen": {
        "label": "Moyen",
        "description": "Bon compromis qualité / poids (recommandé)",
        "quality": 82,
        "max_w": 1800,
        "max_h": 2400,
    },
    "fort": {
        "label": "Fort",
        "description": "Compression maximale, qualité visible réduite",
        "quality": 60,
        "max_w": 1200,
        "max_h": 1600,
    },
}


# --------------------------------------------------------------------------
# Logique de compression
# --------------------------------------------------------------------------
def compress_image(image_bytes, quality, max_w, max_h):
    img = Image.open(io.BytesIO(image_bytes))

    # Transparence / formats incompatibles JPEG -> fond blanc
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGBA")
        background = Image.new("RGB", img.size, "white")
        background.paste(img, mask=img.getchannel("A"))
        img = background
    else:
        img = img.convert("RGB")

    # Redimensionnement uniquement si nécessaire
    img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)

    output = io.BytesIO()
    img.save(
        output,
        format="JPEG",
        quality=quality,
        optimize=True,
        progressive=True,
    )
    return output.getvalue()


def compress_pdf(input_path, output_path, profile_key, progress_callback=None):
    profile = PROFILES[profile_key]
    quality = profile["quality"]
    max_w = profile["max_w"]
    max_h = profile["max_h"]

    doc = pymupdf.open(input_path)
    processed_xrefs = set()

    total_pages = len(doc)
    for page_number in range(total_pages):
        page = doc[page_number]

        for image in page.get_images(full=True):
            xref = image[0]

            # Une même image peut être utilisée plusieurs fois
            if xref in processed_xrefs:
                continue
            processed_xrefs.add(xref)

            try:
                extracted = doc.extract_image(xref)
                original_bytes = extracted["image"]

                compressed_bytes = compress_image(
                    original_bytes, quality, max_w, max_h
                )

                # On ne remplace que si le résultat est réellement plus petit
                if len(compressed_bytes) < len(original_bytes):
                    page.replace_image(xref, stream=compressed_bytes)

            except Exception as e:
                print(f"Image {xref} ignorée : {e}")

        if progress_callback:
            progress_callback(page_number + 1, total_pages)

    doc.save(
        output_path,
        garbage=4,
        deflate=True,
        clean=True,
    )
    doc.close()


# --------------------------------------------------------------------------
# Interface graphique
# --------------------------------------------------------------------------
BASE_CLASS = TkinterDnD.Tk if DND_AVAILABLE else tk.Tk


class CompresseurApp(BASE_CLASS):
    def __init__(self):
        super().__init__()

        self.title("Compresseur de PDF")
        self.geometry("520x480")
        self.resizable(False, False)
        self.configure(bg="#f4f5f7")

        self.selected_file = None
        self.selected_profile = tk.StringVar(value="moyen")

        self._build_ui()

    # ---------------------------------------------------------------
    def _build_ui(self):
        title = tk.Label(
            self,
            text="Compresseur de PDF",
            font=("Segoe UI", 16, "bold"),
            bg="#f4f5f7",
        )
        title.pack(pady=(20, 5))

        subtitle_text = (
            "Glissez-déposez un PDF ci-dessous, ou cliquez pour le choisir"
            if DND_AVAILABLE
            else "Cliquez ci-dessous pour choisir un PDF\n"
            "(pip install tkinterdnd2 pour activer le glisser-déposer)"
        )
        subtitle = tk.Label(
            self, text=subtitle_text, font=("Segoe UI", 9), bg="#f4f5f7", fg="#666"
        )
        subtitle.pack(pady=(0, 10))

        # Zone de dépôt / bouton parcourir
        self.drop_zone = tk.Label(
            self,
            text="📄\n\nAucun fichier sélectionné",
            font=("Segoe UI", 10),
            bg="#ffffff",
            fg="#888",
            relief="ridge",
            bd=1,
            width=50,
            height=6,
            cursor="hand2",
        )
        self.drop_zone.pack(pady=5, padx=20)
        self.drop_zone.bind("<Button-1>", lambda e: self._browse_file())

        if DND_AVAILABLE:
            self.drop_zone.drop_target_register(DND_FILES)
            self.drop_zone.dnd_bind("<<Drop>>", self._on_drop)

        # Niveaux de compression
        levels_frame = tk.LabelFrame(
            self, text="Niveau de compression", bg="#f4f5f7", font=("Segoe UI", 10, "bold")
        )
        levels_frame.pack(pady=15, padx=20, fill="x")

        for key in ("leger", "moyen", "fort"):
            profile = PROFILES[key]
            rb = tk.Radiobutton(
                levels_frame,
                text=f"{profile['label']} — {profile['description']}",
                variable=self.selected_profile,
                value=key,
                bg="#f4f5f7",
                font=("Segoe UI", 9),
                anchor="w",
                justify="left",
            )
            rb.pack(fill="x", padx=10, pady=4)

        # Bouton compresser
        self.compress_btn = tk.Button(
            self,
            text="Compresser le PDF",
            font=("Segoe UI", 11, "bold"),
            bg="#2d6cdf",
            fg="white",
            activebackground="#1f57bf",
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=8,
            command=self._start_compression,
            state="disabled",
        )
        self.compress_btn.pack(pady=15)

        # Barre de progression
        self.progress = ttk.Progressbar(self, orient="horizontal", length=460, mode="determinate")
        self.progress.pack(pady=(0, 10))

        self.status_label = tk.Label(self, text="", bg="#f4f5f7", font=("Segoe UI", 9), fg="#444")
        self.status_label.pack()

    # ---------------------------------------------------------------
    def _on_drop(self, event):
        # event.data peut contenir des accolades si le chemin a des espaces
        raw_path = event.data.strip("{}")
        self._set_file(raw_path)

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Choisir un fichier PDF",
            filetypes=[("Fichiers PDF", "*.pdf")],
        )
        if path:
            self._set_file(path)

    def _set_file(self, path):
        if not path.lower().endswith(".pdf"):
            messagebox.showerror("Fichier invalide", "Merci de sélectionner un fichier .pdf")
            return
        if not os.path.isfile(path):
            messagebox.showerror("Fichier introuvable", f"Impossible de trouver :\n{path}")
            return

        self.selected_file = path
        size_mo = os.path.getsize(path) / 1024 / 1024
        filename = os.path.basename(path)
        self.drop_zone.config(
            text=f"✅ {filename}\n({size_mo:.2f} Mo)",
            fg="#222",
        )
        self.compress_btn.config(state="normal")
        self.status_label.config(text="")

    # ---------------------------------------------------------------
    def _start_compression(self):
        if not self.selected_file:
            return

        self.compress_btn.config(state="disabled")
        self.progress["value"] = 0
        self.status_label.config(text="Compression en cours...")

        thread = threading.Thread(target=self._run_compression, daemon=True)
        thread.start()

    def _run_compression(self):
        input_path = self.selected_file
        profile_key = self.selected_profile.get()
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_compresse{ext}"

        def progress_callback(current, total):
            percent = int((current / total) * 100) if total else 0
            self.after(0, lambda: self._update_progress(percent, current, total))

        try:
            compress_pdf(input_path, output_path, profile_key, progress_callback)
        except Exception as e:
            self.after(0, lambda: self._on_error(str(e)))
            return

        original_size = os.path.getsize(input_path) / 1024 / 1024
        compressed_size = os.path.getsize(output_path) / 1024 / 1024
        reduction = (1 - compressed_size / original_size) * 100 if original_size else 0

        self.after(
            0,
            lambda: self._on_success(output_path, original_size, compressed_size, reduction),
        )

    def _update_progress(self, percent, current, total):
        self.progress["value"] = percent
        self.status_label.config(text=f"Page {current}/{total}...")

    def _on_success(self, output_path, original_size, compressed_size, reduction):
        self.progress["value"] = 100
        self.status_label.config(text="Terminé !")
        self.compress_btn.config(state="normal")

        messagebox.showinfo(
            "Compression terminée",
            f"Fichier créé :\n{output_path}\n\n"
            f"Taille originale   : {original_size:.2f} Mo\n"
            f"Taille compressée  : {compressed_size:.2f} Mo\n"
            f"Réduction          : {reduction:.1f} %",
        )

    def _on_error(self, message):
        self.status_label.config(text="Erreur")
        self.compress_btn.config(state="normal")
        messagebox.showerror("Erreur pendant la compression", message)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    app = CompresseurApp()
    app.mainloop()
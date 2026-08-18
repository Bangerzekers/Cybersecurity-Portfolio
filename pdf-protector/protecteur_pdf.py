import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import pikepdf
except ImportError:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "Dépendance manquante",
        "Le module 'pikepdf' n'est pas installé.\n\n"
        "Ouvre PowerShell et exécute :\n\n"
        "py -m pip install pikepdf"
    )
    sys.exit(1)


class PDFProtectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Protection PDF par mot de passe")
        self.root.geometry("760x545")
        self.root.minsize(700, 520)
        self.root.resizable(True, True)

        try:
            self.root.tk.call("tk", "scaling", 1.2)
        except Exception:
            pass

        style = ttk.Style()
        try:
            style.theme_use("vista")
        except Exception:
            pass

        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("Primary.TButton", font=("Segoe UI", 11, "bold"), padding=(14, 10))
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))

        self.pdf_path = tk.StringVar()
        self.password = tk.StringVar()
        self.password_confirm = tk.StringVar()
        self.show_password = tk.BooleanVar(value=False)

        outer = ttk.Frame(root, padding=24)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text="Protection PDF par mot de passe",
            style="Title.TLabel"
        ).pack(anchor="center", pady=(0, 20))

        file_frame = ttk.LabelFrame(outer, text="Fichier PDF", padding=14)
        file_frame.pack(fill="x", pady=(0, 16))
        file_frame.columnconfigure(0, weight=1)

        ttk.Entry(
            file_frame,
            textvariable=self.pdf_path,
            state="readonly"
        ).grid(row=0, column=0, sticky="ew", padx=(0, 10), pady=2)

        ttk.Button(
            file_frame,
            text="Parcourir...",
            command=self.select_pdf
        ).grid(row=0, column=1, sticky="e", pady=2)

        pwd_frame = ttk.LabelFrame(outer, text="Mot de passe", padding=14)
        pwd_frame.pack(fill="x", pady=(0, 16))
        pwd_frame.columnconfigure(1, weight=1)

        ttk.Label(pwd_frame, text="Mot de passe :").grid(
            row=0, column=0, sticky="w", pady=7
        )

        self.pwd_entry = ttk.Entry(
            pwd_frame,
            textvariable=self.password,
            show="•"
        )
        self.pwd_entry.grid(
            row=0, column=1, sticky="ew", padx=(14, 0), pady=7
        )

        ttk.Label(pwd_frame, text="Confirmation :").grid(
            row=1, column=0, sticky="w", pady=7
        )

        self.pwd_confirm_entry = ttk.Entry(
            pwd_frame,
            textvariable=self.password_confirm,
            show="•"
        )
        self.pwd_confirm_entry.grid(
            row=1, column=1, sticky="ew", padx=(14, 0), pady=7
        )

        ttk.Checkbutton(
            pwd_frame,
            text="Afficher le mot de passe",
            variable=self.show_password,
            command=self.toggle_password
        ).grid(
            row=2, column=1, sticky="w", padx=(14, 0), pady=(8, 2)
        )

        info_frame = ttk.LabelFrame(outer, text="Informations", padding=14)
        info_frame.pack(fill="x", pady=(0, 18))

        ttk.Label(
            info_frame,
            text=(
                "• Le fichier original n'est jamais supprimé ni modifié.\n"
                "• Un nouveau fichier « _protege.pdf » est créé dans le même dossier.\n"
                "• Le mot de passe n'est pas enregistré par le programme."
            ),
            justify="left"
        ).pack(anchor="w")

        self.protect_button = ttk.Button(
            outer,
            text="PROTÉGER LE PDF",
            command=self.protect_pdf,
            style="Primary.TButton"
        )
        self.protect_button.pack(fill="x", ipady=4, pady=(4, 0))

        # Aucun texte/status sous le bouton : aspect plus propre,
        # et aucune ligne susceptible d'être coupée en bas de fenêtre.

        self.root.bind("<Return>", lambda event: self.protect_pdf())

    def select_pdf(self):
        path = filedialog.askopenfilename(
            title="Sélectionner un PDF",
            filetypes=[("Fichiers PDF", "*.pdf")]
        )
        if path:
            self.pdf_path.set(path)
            self.pwd_entry.focus_set()

    def toggle_password(self):
        show_char = "" if self.show_password.get() else "•"
        self.pwd_entry.configure(show=show_char)
        self.pwd_confirm_entry.configure(show=show_char)

    def build_output_path(self, input_path):
        base, ext = os.path.splitext(input_path)
        candidate = f"{base}_protege{ext}"
        counter = 2

        while os.path.exists(candidate):
            candidate = f"{base}_protege_{counter}{ext}"
            counter += 1

        return candidate

    def protect_pdf(self):
        input_path = self.pdf_path.get().strip()
        pwd = self.password.get()
        pwd_confirm = self.password_confirm.get()

        if not input_path:
            messagebox.showwarning("PDF manquant", "Sélectionne d'abord un fichier PDF.")
            return

        if not os.path.isfile(input_path):
            messagebox.showerror("Erreur", "Le fichier PDF sélectionné n'existe plus.")
            return

        if not pwd:
            messagebox.showwarning("Mot de passe manquant", "Saisis un mot de passe.")
            return

        if pwd != pwd_confirm:
            messagebox.showwarning(
                "Confirmation incorrecte",
                "Les deux mots de passe ne correspondent pas."
            )
            return

        if len(pwd) < 8:
            if not messagebox.askyesno(
                "Mot de passe court",
                "Le mot de passe contient moins de 8 caractères.\n\n"
                "Il est recommandé d'utiliser un mot de passe plus long.\n\n"
                "Continuer quand même ?"
            ):
                return

        output_path = self.build_output_path(input_path)

        try:
            self.protect_button.configure(state="disabled")
            self.root.update_idletasks()

            with pikepdf.Pdf.open(input_path) as pdf:
                pdf.save(
                    output_path,
                    encryption=pikepdf.Encryption(
                        user=pwd,
                        owner=pwd,
                        R=6,
                        allow=pikepdf.Permissions(
                            accessibility=True,
                            extract=True,
                            modify_annotation=True,
                            modify_assembly=True,
                            modify_form=True,
                            modify_other=True,
                            print_lowres=True,
                            print_highres=True
                        )
                    )
                )

            self.password.set("")
            self.password_confirm.set("")

            messagebox.showinfo(
                "PDF protégé",
                "Le PDF a été protégé avec succès.\n\n"
                f"Fichier créé :\n{output_path}\n\n"
                "Le fichier original a été conservé."
            )

        except pikepdf.PasswordError:
            messagebox.showerror(
                "PDF déjà protégé",
                "Le PDF source est déjà protégé par un mot de passe."
            )
        except Exception as exc:
            messagebox.showerror(
                "Erreur",
                f"Impossible de protéger le PDF.\n\nDétail :\n{exc}"
            )
        finally:
            self.protect_button.configure(state="normal")


if __name__ == "__main__":
    root = tk.Tk()
    app = PDFProtectorApp(root)
    root.mainloop()

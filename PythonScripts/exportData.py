import pandas as pd
import csv
import io
import os
import argparse  # Νέα βιβλιοθήκη για command line arguments
from google import genai

# ==========================================
# ΡΥΘΜΙΣΕΙΣ (ΣΤΑΘΕΡΕΣ)
# ==========================================
MODEL = "gemini-3-flash-preview"
#MODEL = "gemini-pro-latest"
API_KEY_FILE = "api_key.key"
TEMPLATE_CSV = "template.csv"

def process_thesis_data(writer_name):
    """
    Επεξεργάζεται τη διατριβή για έναν συγκεκριμένο συγγραφέα.
    """
    # Δυναμικός ορισμός αρχείων βάσει του ονόματος που δόθηκε
    pdf_file_path = f"{writer_name}.pdf"
    #output_csv = f"{writer_name}-{MODEL}.csv"
    output_csv = f"{writer_name}.csv"

    print(f"=== Εξαγωγή δεδομένων από PDF με {MODEL} ===")
    print(f"Συγγραφέας: {writer_name}\n")

    # 1. Διάβασμα API key
    if not os.path.exists(API_KEY_FILE):
        print(f"ΣΦΑΛΜΑ: Δεν βρέθηκε το '{API_KEY_FILE}'.")
        return

    with open(API_KEY_FILE, "r", encoding="utf-8") as f:
        api_key = f.read().strip()

    if not api_key:
        print(f"ΣΦΑΛΜΑ: Το '{API_KEY_FILE}' είναι κενό.")
        return

    client = genai.Client(api_key=api_key)

    # 2. Έλεγχοι αρχείων PDF και Template
    for path in [pdf_file_path, TEMPLATE_CSV]:
        if not os.path.exists(path):
            print(f"ΣΦΑΛΜΑ: Δεν βρέθηκε το αρχείο: {path}")
            return

    # 3. Φόρτωση PDF
    with open(pdf_file_path, "rb") as f:
        pdf_bytes = f.read()
    print(f"PDF φορτώθηκε ({len(pdf_bytes)/(1024*1024):.2f} MB)")

    # 4. Φόρτωση template
    df_template = pd.read_csv(TEMPLATE_CSV)
    df_template['Number'] = pd.to_numeric(df_template['Number'], errors='coerce')
    print(f"Template: {len(df_template)} πεδία\n")

    prompt_fields = "\n".join(f"{row['Number']}: {row['Description']}" for _, row in df_template.iterrows())

    prompt = f"""
Είσαι ειδικός στην καταγραφή μεταδεδομένων διδακτορικών διατριβών ελληνικών πανεπιστημίων.
Πάρε το PDF που επισυνάπτεται, ανάλυσέ το προσεκτικά ολόκληρο, εξήγαγε τις πληροφορίες για ΚΑΘΕ πεδίο και συμπλήρωσε **αποκλειστικά** τη στήλη "Data" για κάθε μία από τις {len(df_template)} γραμμές του template που ακολουθεί.

{prompt_fields}

Κανόνες (πολύ σημαντικό):
ΕΠΙΣΤΡΕΨΕ ΜΟΝΟ ΈΝΑ CSV ΜΕ 2 ΣΤΗΛΕΣ: Number,Data
- ΞΕΚΙΝΑ ΑΠΑΡΑΙΤΗΤΑ ΑΠΟ Number 1 (ακόμα και αν είναι N/A)
- Πρώτη γραμμή: Number,Data
- Μην γράψεις ΚΑΜΙΑ λέξη, σχόλιο, markdown, εξήγηση, ```csv ή οτιδήποτε άλλο εκτός από το CSV
- Αν δεν υπάρχει η πληροφορία → βάλε "N/A"
- Χρησιμοποίησε ακριβώς την επίσημη διατύπωση του κειμένου (με κεφαλαία όπου υπάρχουν)
- Ονόματα συγγραφέα/επιβλέποντα/εξεταστών → όπως ακριβώς εμφανίζονται
- Ημερομηνίες → YYYY-MM-DD όταν είναι δυνατόν
- Γλώσσα απάντησης: στην γλώσσα που περιέχεται η πληροφορία μέσα στο PDF, χωρίς μετάφραση
- ΚΑΘΕ τιμή με κόμμα ή ελληνικούς χαρακτήρες → σε "εισαγωγικά"
"""

    # 5. Κλήση μοντέλου
    print(f"Κλήση {MODEL}...")
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[
                {"parts": [
                    {"inline_data": {"mime_type": "application/pdf", "data": pdf_bytes}},
                    {"text": prompt}
                ]}
            ]
        )
        response_text = response.text.strip()
        print("Απάντηση λήφθηκε.\n")
    except Exception as e:
        print(f"Σφάλμα Gemini: {e}")
        return

    # Καθαρισμός markdown
    clean_text = response_text
    if "```" in clean_text:
        parts = clean_text.split("```")
        clean_text = parts[1].strip() if len(parts) > 1 else clean_text
        if clean_text.lower().startswith("csv"):
            clean_text = clean_text[3:].strip()

    # 6. Parsing και Merge
    try:
        extracted_df = pd.read_csv(
            io.StringIO(clean_text),
            quoting=csv.QUOTE_ALL,
            dtype=str,
            engine='python'
        ).replace('', 'N/A')

        extracted_df['Number'] = pd.to_numeric(extracted_df['Number'], errors='coerce')

        final_df = pd.merge(
            df_template[['Number', 'Field']],
            extracted_df[['Number', 'Data']],
            on='Number',
            how='left'
        )

        final_df['Data'] = final_df['Data'].fillna('N/A')
        final_df = final_df[['Field', 'Data']]
        
        final_df.to_csv(output_csv, index=False, encoding="utf-8-sig")

        print(f"ΕΠΙΤΥΧΙΑ! Το αρχείο δημιουργήθηκε: {output_csv}")

    except Exception as e:
        print(f"Πρόβλημα parsing: {e}")

if __name__ == "__main__":
    # Ρύθμιση του parser για τη γραμμή εντολών
    parser = argparse.ArgumentParser(description="Εξαγωγή δεδομένων από PDF διατριβής.")
    parser.add_argument("writer", type=str, help="Το όνομα του συγγραφέα (π.χ. apostolidou)")
    
    args = parser.parse_args()

    # Εκτέλεση της συνάρτησης με το όνομα που έδωσε ο χρήστης
    process_thesis_data(args.writer)

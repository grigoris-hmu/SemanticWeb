import sys
import pandas as pd
import re

def main():
    if len(sys.argv) < 2:
        print("Usage: python converter.py number_my_file")
        return
    
    filename_base = sys.argv[1].split(".")[0]

    # Εξαγωγή του αριθμού από την αρχή του ονόματος [π.χ. 8_test -> 8]
    match = re.match(r'^(\d+)', filename_base)
    if not match:
        print("Error: Το όνομα του αρχείου πρέπει να ξεκινάει με αριθμό.")
        return
    file_number = match.group(1)
    
    csv_file = f"{filename_base}.csv"
    ttl_file = f"{filename_base}.ttl"
    
    try:
        # Ανάγνωση δεδομένων από το template.csv δομή
        df = pd.read_csv(csv_file, header=None)
        data_dict = {}
        for _, row in df.iterrows():
            if pd.isna(row[0]) or pd.isna(row[1]): continue
            key = str(row[0]).strip()
            val = str(row[1]).strip()
            # Εξαίρεση κενών και N/A τιμών
            if val.lower() not in ["n/a", "", "nan", "none"]:
                data_dict[key] = val
    except FileNotFoundError:
        print(f"Error: Το αρχείο {csv_file} δεν βρέθηκε.")
        return

    # Αντιστοίχιση βάσει final.ttl
    if "altTitle" in data_dict:
        data_dict["alternativeHeadline"] = data_dict.pop("altTitle")

    prefixes_old = """@prefix : <http://www.semanticweb.org/team1/ontologies/semantic-web-project#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@base <http://www.semanticweb.org/team1/ontologies/semantic-web-project> .

<http://www.semanticweb.org/team1/ontologies/semantic-web-project> rdf:type owl:Ontology .

"""

    prefixes_x = """
###  http://www.semanticweb.org/team1/ontologies/semantic-web-project#SampleID_1

"""
    prefixes = f"\n###  http://www.semanticweb.org/team1/ontologies/semantic-web-project#SampleID_{file_number}\n"
    # Ομαδοποίηση ιδιοτήτων βάσει template.ttl
    mapping = {
        "Sample": ["analysisTools", "basicUnit", "collectionMethod", "geographicalUnit", "methodOfAnalysis", 
                   "methodOfRecording", "recordingTools", "sampleCollectionReference", "sampleDescription", 
                   "sampleSize", "sampleTimeReference", "spatialCoverage", "statesOfReference"],
        "Survey": ["sampleProd", "spaceAnalysis", "strategy", "studyAssumptions", "studyQuestions", "target", 
                   "timeAnalysis", "workAssumptions"],
        "Writer": ["fathersName", "firstName", "gender", "surName"],
        "Thesis": ["abstract", "alternativeHeadline", "dateOfSupport", "department", "institution", "keyWords", 
                   "language", "libraryLink", "nameOfSupervisor", "numberOfPages", "program", "title", "typeOfDissertation"]
    }

    output_ttl = [prefixes]

    # IDs με βάση τον αριθμό του αρχείου
    ids = {
        "Sample": f":SampleID_{file_number}",
        "Survey": f":SurveyID_{file_number}",
        "Writer": f":WriterID_{file_number}",
        "Thesis": f":ThesisID_{file_number}"
    }

    # Λειτουργία για τη δημιουργία blocks με τη νέα μορφοποίηση γραμμής
    def create_block(subject, rdf_type, props, extra_props=None):
        # Εφαρμογή νέας γραμμής μετά το κόμμα για το rdf:type
        block = [f"{subject} rdf:type owl:NamedIndividual ,\n                   {rdf_type} ;"]
        if extra_props:
            for ep_key, ep_val in extra_props.items():
                block.append(f"          {ep_key} {ep_val} ;")
        for p in props:
            if p in data_dict:
                val = data_dict[p]
                if p == "dateOfSupport":
                    block.append(f'          :{p} "{val}"^^xsd:date ;')
                else:
                    block.append(f'          :{p} "{val}" ;')
        return "\n".join(block).rstrip(" ;") + " .\n"

    # Δημιουργία των ενοτήτων (Blocks)
    output_ttl.append(create_block(ids["Sample"], ":Sample", mapping["Sample"]))
    output_ttl.append(create_block(ids["Survey"], ":Survey", mapping["Survey"], {":hasSample": ids["Sample"]}))
    output_ttl.append(create_block(ids["Writer"], ":Writer", mapping["Writer"]))
    
    t_type = ":" + data_dict.get("typeOfDissertation", "MasterThesis").replace(" ", "")
    output_ttl.append(create_block(ids["Thesis"], t_type, mapping["Thesis"], 
                                   {":hasSurvey": ids["Survey"], ":hasWriter": ids["Writer"]}))

    with open(ttl_file, 'w', encoding='utf-8') as f:
        f.writelines(output_ttl)
    
    print(f"Επιτυχής δημιουργία: {ttl_file}")

if __name__ == "__main__":
    main()
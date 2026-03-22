# queries.py

PREFIXES = """
PREFIX : <http://www.semanticweb.org/team1/ontologies/semantic-web-project/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

# Helper: normalization in SPARQL (lowercase + remove accents + ς->σ)
# NOTE: kept inline for Virtuoso compatibility (no custom function)
def _norm_expr(var_name: str) -> str:
    # var_name is something like ?vRaw
    return f'''REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE({var_name},
     "ά","α"), "έ","ε"), "ή","η"), "ί","ι"), "ό","ο"), "ύ","υ"), "ώ","ω"),
    "ϊ","ι"), "ϋ","υ"), "ΐ","ι"), "ΰ","υ"), "ς","σ")'''

SPARQL_TEMPLATES = {
    # ------------------------------------------------------------
    # Core lists
    # ------------------------------------------------------------
    "all_dissertations": """
        SELECT ?ThesisID ?Title ?SurName ?FirstName ?DateOfSupport
        WHERE {
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :hasWriter ?Writer .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .
        }
        ORDER BY DESC(?DateOfSupport)
    """,

    "recent": """
        SELECT ?ThesisID ?Title ?SurName ?FirstName ?DateOfSupport
        WHERE {
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :hasWriter ?Writer .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .
        }
        ORDER BY DESC(?DateOfSupport)
        LIMIT 10
    """,

    # ------------------------------------------------------------
    # Keyword search scopes (used by search_in)
    # ------------------------------------------------------------
    "search_keyword": """
        SELECT DISTINCT ?ThesisID ?Title ?KeyWords ?SurName ?FirstName ?DateOfSupport
        WHERE {{
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :keyWords ?KeyWords ;
                   :hasWriter ?Writer .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .

          BIND(LCASE(STR(?KeyWords)) AS ?vRaw)
          BIND({_norm_expr("?vRaw")} AS ?vClean)

          FILTER(CONTAINS(?vClean, "{keyword}"))
        }}
        ORDER BY DESC(?DateOfSupport)
    """,

    "search_title": """
        SELECT DISTINCT ?ThesisID ?Title ?SurName ?FirstName ?DateOfSupport
        WHERE {{
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :hasWriter ?Writer .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .

          BIND(LCASE(STR(?Title)) AS ?vRaw)
          BIND({_norm_expr("?vRaw")} AS ?vClean)

          FILTER(CONTAINS(?vClean, "{keyword}"))
        }}
        ORDER BY DESC(?DateOfSupport)
    """,

    "search_abstract": """
        SELECT DISTINCT ?ThesisID ?Title ?Abstract ?SurName ?FirstName ?DateOfSupport
        WHERE {{
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :abstract ?Abstract ;
                   :hasWriter ?Writer .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .

          BIND(LCASE(STR(?Abstract)) AS ?vRaw)
          BIND({_norm_expr("?vRaw")} AS ?vClean)

          FILTER(CONTAINS(?vClean, "{keyword}"))
        }}
        ORDER BY DESC(?DateOfSupport)
    """,

    "search_title_keywords": """
        SELECT DISTINCT ?ThesisID ?Title ?KeyWords ?SurName ?FirstName ?DateOfSupport
        WHERE {{
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :keyWords ?KeyWords ;
                   :hasWriter ?Writer .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .

          BIND(LCASE(CONCAT(STR(?Title), " ", STR(?KeyWords))) AS ?vRaw)
          BIND({_norm_expr("?vRaw")} AS ?vClean)

          FILTER(CONTAINS(?vClean, "{keyword}"))
        }}
        ORDER BY DESC(?DateOfSupport)
    """,

    "search_all": """
        SELECT DISTINCT ?ThesisID ?Title ?KeyWords ?Abstract ?SurName ?FirstName ?DateOfSupport
        WHERE {{
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :keyWords ?KeyWords ;
                   :hasWriter ?Writer .
          OPTIONAL {{ ?ThesisID :abstract ?Abstract . }}
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .

          BIND(LCASE(CONCAT(STR(?Title), " ", STR(?KeyWords), " ", STR(?Abstract))) AS ?vRaw)
          BIND({_norm_expr("?vRaw")} AS ?vClean)

          FILTER(CONTAINS(?vClean, "{keyword}"))
        }}
        ORDER BY DESC(?DateOfSupport)
    """,

    # ------------------------------------------------------------
    # Author / Supervisor searches
    # ------------------------------------------------------------
    "search_author_name": """
        SELECT DISTINCT ?ThesisID ?LastName ?FirstName ?Title ?DateOfSupport ?Link
        WHERE {{
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :hasWriter ?w .
          ?w :firstName ?FirstName ;
             :surName ?LastName .
          OPTIONAL {{ ?ThesisID :libraryLink ?Link }}

          BIND(CONCAT(STR(?FirstName), " ", STR(?LastName)) AS ?fullName)
          BIND(CONCAT(STR(?LastName), " ", STR(?FirstName)) AS ?reverseName)

          BIND(LCASE(?fullName) AS ?fnLower)
          BIND(LCASE(?reverseName) AS ?rnLower)

          BIND({_norm_expr("?fnLower")} AS ?fnClean)
          BIND({_norm_expr("?rnLower")} AS ?rnClean)

          FILTER(CONTAINS(?fnClean, "{author}") || CONTAINS(?rnClean, "{author}"))
        }}
        ORDER BY DESC(?DateOfSupport)
    """,

    # IMPORTANT: ontology uses :nameOfSupervisor (DatatypeProperty), not :hasSupervisor
    "search_supervisor": """
        SELECT DISTINCT ?ThesisID ?Title ?SurName ?FirstName ?DateOfSupport ?SupervisorName
        WHERE {{
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :nameOfSupervisor ?SupervisorName ;
                   :hasWriter ?Writer .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .

          BIND(LCASE(STR(?SupervisorName)) AS ?vRaw)
          BIND({_norm_expr("?vRaw")} AS ?vClean)

          FILTER(CONTAINS(?vClean, "{supervisor}"))
        }}
        ORDER BY DESC(?DateOfSupport)
    """,

    # ------------------------------------------------------------
    # Gender
    # ------------------------------------------------------------
    "female_authors": """
        SELECT ?ThesisID ?Title ?SurName ?FirstName ?DateOfSupport
        WHERE {
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :hasWriter ?Writer .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName ;
                  :gender ?g .
          FILTER(regex(str(?g), "Γυναίκα", "i"))
        }
        ORDER BY DESC(?DateOfSupport)
    """,

    "male_authors": """
        SELECT ?ThesisID ?Title ?SurName ?FirstName ?DateOfSupport
        WHERE {
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :hasWriter ?Writer .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName ;
                  :gender ?g .
          FILTER(regex(str(?g), "Άνδρας", "i"))
        }
        ORDER BY DESC(?DateOfSupport)
    """,

    # ------------------------------------------------------------
    # Institution
    # ------------------------------------------------------------
    "institution_list": """
        SELECT DISTINCT ?Institution
        WHERE { ?thesis :institution ?Institution . }
        ORDER BY ?Institution
    """,

    "all_institutions": """
        SELECT ?ThesisID ?Institution ?Title ?SurName ?FirstName ?DateOfSupport
        WHERE {
        # Αναζήτηση όλων των διατριβών (συμπεριλαμβανομένων των υποκλάσεων)
        ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
        
        # Ανάκτηση των στοιχείων της διατριβής
        ?ThesisID :institution ?Institution ;
                    :title ?Title ;
                    :dateOfSupport ?DateOfSupport ;
                    :hasWriter ?Writer .
        
        # Ανάκτηση των στοιχείων του συγγραφέα
        ?Writer :surName ?SurName ;
                :firstName ?FirstName .
        }
        # Ταξινόμηση: 
        # 1. Φθίνουσα ως προς το Ίδρυμα (Institution)
        # 2. Φθίνουσα ως προς την Ημερομηνία Παρουσίασης (DateOfSupport)
        ORDER BY DESC(?Institution) DESC(?DateOfSupport)
    """,
    "by_institution": """
        SELECT DISTINCT ?ThesisID ?Institution ?Title ?SurName ?FirstName ?DateOfSupport
        WHERE {{
            # Αναζήτηση των διατριβών και των υποκλάσεων τους
            ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
            
            # Ανάκτηση βασικών στοιχείων διατριβής
            ?ThesisID :institution ?Institution ;
                    :title ?Title ;
                    :dateOfSupport ?DateOfSupport ;
                    :hasWriter ?Writer .
            
            # Ανάκτηση στοιχείων συγγραφέα
            ?Writer :surName ?SurName ;
                    :firstName ?FirstName .
            
            # Διαδικασία Καθαρισμού Ελληνικών Χαρακτήρων (Normalization)
            BIND(LCASE(STR(?Institution)) AS ?vRaw)
            BIND({_norm_expr("?vRaw")} AS ?vClean)
            
            # Φιλτράρισμα βάσει του καθαρισμένου ονόματος του ιδρύματος.
            # Αντικατάστησε το {institution} με την τιμή αναζήτησης σε πεζά και χωρίς τόνους (π.χ. "πανεπιστημιο αιγαιου")
            FILTER (CONTAINS(?vClean, "{institution}"))
        }}
        # Ταξινόμηση φθίνουσα ως προς την ημερομηνία υποστήριξης
        ORDER BY DESC(?DateOfSupport)
    """,

    # ------------------------------------------------------------
    # Year
    # ------------------------------------------------------------
    "by_year": """
        SELECT ?ThesisID ?Title ?SurName ?FirstName ?DateOfSupport
        WHERE {{
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation ;
                   :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :hasWriter ?Writer .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .
          FILTER(YEAR(?DateOfSupport) = {selected_year})
        }}
        ORDER BY DESC(?DateOfSupport)
    """,

    # ------------------------------------------------------------
    # Type of dissertation
    # ------------------------------------------------------------
    "AllThesis": """
        SELECT ?ThesisID ?Title ?SurName ?FirstName ?TypeOfDissertation ?DateOfSupport
        WHERE {
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :typeOfDissertation ?TypeOfDissertation ;
                   :hasWriter ?Writer .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .
        }
        ORDER BY DESC(?DateOfSupport)
    """,

    "MasterThesis": """
        SELECT ?ThesisID ?Title ?SurName ?FirstName ?DateOfSupport
        WHERE {
          ?ThesisID rdf:type :MasterThesis .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :hasWriter ?Writer ;
                   :typeOfDissertation "MasterThesis" .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .
        }
        ORDER BY DESC(?DateOfSupport)
    """,

    "DoctoralThesis": """
        SELECT ?ThesisID ?Title ?SurName ?FirstName ?DateOfSupport
        WHERE {
          ?ThesisID rdf:type :DoctoralDissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :hasWriter ?Writer ;
                   :typeOfDissertation "DoctoralDissertation" .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .
        }
        ORDER BY DESC(?DateOfSupport)
    """,

    "BachelorThesis": """
        SELECT ?ThesisID ?Title ?SurName ?FirstName ?DateOfSupport
        WHERE {
          ?ThesisID rdf:type :BachelorsThesis .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :hasWriter ?Writer ;
                   :typeOfDissertation "BachelorsThesis" .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .
        }
        ORDER BY DESC(?DateOfSupport)
    """,

    # ------------------------------------------------------------
    # Strategy
    # ------------------------------------------------------------
    "by_strategy_All": """
        SELECT ?ThesisID ?Title ?SurName ?FirstName ?Strategy ?DateOfSupport
        WHERE {
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :hasWriter ?Writer ;
                   :hasSurvey ?Survey .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .
          ?Survey :strategy ?Strategy .
        }
        ORDER BY DESC(?DateOfSupport)
    """,

    "by_strategy_Qualitative": """
        SELECT ?ThesisID ?Title ?SurName ?FirstName ?DateOfSupport
        WHERE {
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :hasWriter ?Writer ;
                   :hasSurvey ?Survey .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .
          ?Survey :strategy "Qualitative" .
        }
        ORDER BY DESC(?DateOfSupport)
    """,

    "by_strategy_Quantitative": """
        SELECT ?ThesisID ?Title ?SurName ?FirstName ?DateOfSupport
        WHERE {
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :hasWriter ?Writer ;
                   :hasSurvey ?Survey .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .
          ?Survey :strategy "Quantitative" .
        }
        ORDER BY DESC(?DateOfSupport)
    """,

    "by_strategy_Mixed": """
        SELECT ?ThesisID ?Title ?SurName ?FirstName ?DateOfSupport
        WHERE {
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :hasWriter ?Writer ;
                   :hasSurvey ?Survey .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .
          ?Survey :strategy "Mixed" .
        }
        ORDER BY DESC(?DateOfSupport)
    """,

    # ------------------------------------------------------------
    # timeAnalysis / spaceAnalysis
    # ------------------------------------------------------------
    "time_analysis_historical": """
        SELECT ?ThesisID ?Title ?SurName ?FirstName ?DateOfSupport
        WHERE {
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :hasWriter ?Writer ;
                   :hasSurvey ?Survey .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .
          ?Survey :timeAnalysis "Ιστορική" .
        }
        ORDER BY DESC(?DateOfSupport)
    """,

    "time_analysis_nonhistorical": """
        SELECT ?ThesisID ?Title ?SurName ?FirstName ?DateOfSupport
        WHERE {
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :hasWriter ?Writer ;
                   :hasSurvey ?Survey .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .
          ?Survey :timeAnalysis "Μη Ιστορική" .
        }
        ORDER BY DESC(?DateOfSupport)
    """,

    "space_analysis_historical": """
        SELECT ?ThesisID ?Title ?SurName ?FirstName ?DateOfSupport
        WHERE {
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :hasWriter ?Writer ;
                   :hasSurvey ?Survey .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .
          ?Survey :spaceAnalysis "Ιστορική" .
        }
        ORDER BY DESC(?DateOfSupport)
    """,

    "space_analysis_nonhistorical": """
        SELECT ?ThesisID ?Title ?SurName ?FirstName ?DateOfSupport
        WHERE {
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation .
          ?ThesisID :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :hasWriter ?Writer ;
                   :hasSurvey ?Survey .
          ?Writer :surName ?SurName ;
                  :firstName ?FirstName .
          ?Survey :spaceAnalysis "Μη Ιστορική" .
        }
        ORDER BY DESC(?DateOfSupport)
    """,

    # ------------------------------------------------------------
    # sampleSize
    # ------------------------------------------------------------
    "sample_size_min": """
        SELECT ?ThesisID ?Title ?SurName ?FirstName ?Strategy ?SampleSize ?DateOfSupport
        WHERE {{
          ?ThesisID rdf:type/rdfs:subClassOf* :Dissertation ;
                   :title ?Title ;
                   :dateOfSupport ?DateOfSupport ;
                   :hasWriter ?Writer ;
                   :hasSurvey ?Survey .
          ?Writer :firstName ?FirstName ;
                  :surName ?SurName .
          ?Survey :hasSample ?Sample .
          OPTIONAL {{ ?Survey :strategy ?Strategy . }}
          ?Sample :sampleSize ?SampleSize .
          BIND(xsd:integer(?SampleSize) AS ?sizeInt)
          FILTER(?sizeInt >= {min_size})
        }}
        ORDER BY DESC(?sizeInt) DESC(?DateOfSupport)
    """,

    # ------------------------------------------------------------
    # thesis_details (Property / Value pairs — used by JSON endpoint)
    # ------------------------------------------------------------
    "thesis_details": """
        SELECT DISTINCT ?Property ?Value
        WHERE {{
          VALUES ?thesis {{ <{thesis_id}> }}
          {{ BIND(?thesis AS ?Entity) ?thesis ?Property ?Value . }}
          UNION {{ ?thesis :hasWriter ?Entity . ?Entity ?Property ?Value . }}
          UNION {{ ?thesis :hasSurvey ?Entity . ?Entity ?Property ?Value . }}
          UNION {{ ?thesis :hasSurvey ?survey . ?survey :hasSample ?Entity . ?Entity ?Property ?Value . }}
        }}
    """,

    # ------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------
    "stats_years": """
        SELECT ?Year (COUNT(?d) AS ?Count)
        WHERE {
          ?d :dateOfSupport ?DateOfSupport .
          BIND(YEAR(?DateOfSupport) AS ?Year)
        }
        GROUP BY ?Year
        ORDER BY ?Year
    """,
    "stats_gender": """
        SELECT ?g (COUNT(?w) AS ?Count)
        WHERE { ?w :gender ?g }
        GROUP BY ?g
    """,
}

# inject normalization helper expansions
# (this keeps templates readable above)
SPARQL_TEMPLATES["search_keyword"] = SPARQL_TEMPLATES["search_keyword"].replace("{_norm_expr(\"?vRaw\")}", _norm_expr("?vRaw"))
SPARQL_TEMPLATES["search_title"] = SPARQL_TEMPLATES["search_title"].replace("{_norm_expr(\"?vRaw\")}", _norm_expr("?vRaw"))
SPARQL_TEMPLATES["search_abstract"] = SPARQL_TEMPLATES["search_abstract"].replace("{_norm_expr(\"?vRaw\")}", _norm_expr("?vRaw"))
SPARQL_TEMPLATES["search_title_keywords"] = SPARQL_TEMPLATES["search_title_keywords"].replace("{_norm_expr(\"?vRaw\")}", _norm_expr("?vRaw"))
SPARQL_TEMPLATES["search_all"] = SPARQL_TEMPLATES["search_all"].replace("{_norm_expr(\"?vRaw\")}", _norm_expr("?vRaw"))
SPARQL_TEMPLATES["search_author_name"] = SPARQL_TEMPLATES["search_author_name"].replace("{_norm_expr(\"?fnLower\")}", _norm_expr("?fnLower")).replace("{_norm_expr(\"?rnLower\")}", _norm_expr("?rnLower"))
SPARQL_TEMPLATES["search_supervisor"] = SPARQL_TEMPLATES["search_supervisor"].replace("{_norm_expr(\"?vRaw\")}", _norm_expr("?vRaw"))
SPARQL_TEMPLATES["by_institution"] = SPARQL_TEMPLATES["by_institution"].replace("{_norm_expr(\"?vRaw\")}", _norm_expr("?vRaw"))

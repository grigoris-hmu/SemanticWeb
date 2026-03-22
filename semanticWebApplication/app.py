from flask import Flask, render_template, request, jsonify
from SPARQLWrapper import SPARQLWrapper, JSON
import unicodedata
from datetime import datetime

from queries import PREFIXES, SPARQL_TEMPLATES

app = Flask(__name__)

current_year = datetime.now().year
years = list(range(current_year, 1999, -1))

VIRTUOSO_URL = "http://127.0.0.1:8890/sparql"


def strip_accents(s: str) -> str:
    """Lowercase + remove accents and normalize final sigma (ς -> σ)."""
    s = (s or "").replace("ς", "σ")
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def execute_sparql(query: str):
    sparql = SPARQLWrapper(VIRTUOSO_URL)
    sparql.setQuery(PREFIXES + query)
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
        return results["results"]["bindings"], results["head"]["vars"]
    except Exception as e:
        print(f"SPARQL Error: {e}")
        return [], []


def get_institutions():
    query = SPARQL_TEMPLATES["institution_list"]
    bindings, _ = execute_sparql(query)
    print("Institutions found:", len(bindings))
    print("Sample institutions:", [row["Institution"]["value"] for row in bindings[:5]])
    return [row["Institution"]["value"] for row in bindings if "Institution" in row]


def compact_predicate(p: str) -> str:
    """Make URI nicer for JSON keys."""
    if not p:
        return ""
    # keep after # or /
    if "#" in p:
        return p.split("#")[-1]
    return p.rstrip("/").split("/")[-1]


@app.route("/")
def index():
    return render_template("index.html", year_labels=years, institutions=get_institutions())


@app.route("/query", methods=["POST"])
def query_handler():
    query_type = request.form.get("query_type")

    '''    
    # Keyword search with scope
    if query_type == "search_keyword":
        keyword = strip_accents(request.form.get("keyword", "").lower().strip())
        search_in = request.form.get("search_in", "keywords")

        scope_map = {
            "title": "search_title",
            "keywords": "search_keyword",
            "abstract": "search_abstract",
            "title_keywords": "search_title_keywords",
            "all": "search_all",
        }
        tpl_key = scope_map.get(search_in, "search_keyword")
        sparql_query = SPARQL_TEMPLATES[tpl_key].format(keyword=keyword)
    '''

    if query_type == "search_title_keywords":
        keyword = strip_accents(request.form.get("keyword", "").lower().strip())
        sparql_query = SPARQL_TEMPLATES["search_title_keywords"].format(keyword=keyword)

    elif query_type == "search_abstract":
        keyword = strip_accents(request.form.get("keyword", "").lower().strip())
        sparql_query = SPARQL_TEMPLATES["search_abstract"].format(keyword=keyword)

    elif query_type == "search_author_name":
        author = strip_accents(request.form.get("author_name", "").lower().strip())
        sparql_query = SPARQL_TEMPLATES["search_author_name"].format(author=author)

    elif query_type == "search_supervisor":
        supervisor = strip_accents(request.form.get("supervisor_name", "").lower().strip())
        sparql_query = SPARQL_TEMPLATES["search_supervisor"].format(supervisor=supervisor)

    elif query_type == "by_institution":
        institution = strip_accents(request.form.get('institution', '').lower().strip())
        print("Selected institution (raw):", request.form.get('institution'))
        if institution == "all_institutions":
            sparql_query = SPARQL_TEMPLATES["all_institutions"]
        else:
            sparql_query = SPARQL_TEMPLATES["by_institution"].format(institution=institution)

    elif query_type == "by_year":
        year = request.form.get("selected_year")
        sparql_query = SPARQL_TEMPLATES["by_year"].format(selected_year=year)

    elif query_type == "sample_size_min":
        min_size = request.form.get("min_sample_size", "").strip()
        if not min_size.isdigit():
            return render_template("index.html", year_labels=years, institutions=get_institutions())
        sparql_query = SPARQL_TEMPLATES["sample_size_min"].format(min_size=min_size)

    # keep legacy: thesis_details as table page (optional)
    elif query_type == "thesis_details":
        thesis_id = request.form.get("thesis_id", "").strip()
        sparql_query = SPARQL_TEMPLATES["thesis_details"].format(thesis_id=thesis_id)

    elif query_type in SPARQL_TEMPLATES:
        sparql_query = SPARQL_TEMPLATES[query_type]

    else:
        return render_template("index.html", year_labels=years, institutions=get_institutions())

    print("### Query_type: ### ", query_type)
    print(sparql_query)
    results, columns = execute_sparql(sparql_query)
    return render_template("results.html", results=results, columns=columns)


@app.route("/thesis_details", methods=["GET"])
def thesis_details_api():
    thesis_id = (request.args.get("thesis_id") or "").strip()
    if not thesis_id:
        return jsonify({"error": "Missing thesis_id"}), 400

    sparql_query = SPARQL_TEMPLATES["thesis_details"].format(thesis_id=thesis_id)
    bindings, _ = execute_sparql(sparql_query)

    # thesis_details returns rows: ?Property ?Value
    out = {}
    for row in bindings:
        p = row.get("Property", {}).get("value")
        v = row.get("Value", {}).get("value")
        if not p or v is None:
            continue
        key = compact_predicate(p)

        # collect multi-values
        if key in out:
            if isinstance(out[key], list):
                out[key].append(v)
            else:
                out[key] = [out[key], v]
        else:
            out[key] = v

    return jsonify(out)


@app.route("/stats")
def stats():
    y_raw, _ = execute_sparql(SPARQL_TEMPLATES["stats_years"])
    g_raw, _ = execute_sparql(SPARQL_TEMPLATES["stats_gender"])

    final_counts = {"Άνδρες": 0, "Γυναίκες": 0}
    for row in g_raw:
        val = row["g"]["value"].lower().strip()
        count = int(row["Count"]["value"])
        if val.startswith(("m", "a", "α", "ά", "΄")):
            final_counts["Άνδρες"] += count
        else:
            final_counts["Γυναίκες"] += count

    return render_template(
        "stats.html",
        year_labels=[r["Year"]["value"] for r in y_raw],
        year_counts=[int(r["Count"]["value"]) for r in y_raw],
        gender_labels=list(final_counts.keys()),
        gender_counts=list(final_counts.values()),
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)

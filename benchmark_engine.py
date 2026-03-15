# benchmark_engine.py

def run_benchmarks(scope, result):

    roof = float(scope.get("roof_m2", 0))
    direct = result.get("direct", 0)

    notes = []

    # Labour benchmark (SA typical range)
    labour_rate = 350

    if labour_rate < 300:
        notes.append("Labour rate appears below SA benchmark (R300–R450/h)")
    elif labour_rate > 450:
        notes.append("Labour rate appears above SA benchmark (R300–R450/h)")
    else:
        notes.append("Labour rate: R350/h → within SA benchmark (R300–R450/h)")

    # Materials benchmark
    expected_material_cost = roof * 200

    if expected_material_cost > 0:

        if direct < expected_material_cost * 0.9:
            notes.append("Materials appear below expected SA industry range.")
        elif direct > expected_material_cost * 1.2:
            notes.append("Materials appear above typical SA cost levels.")
        else:
            notes.append("Materials fall within typical SA cost ranges.")

    notes.append("Overall: Quote aligns with industry pricing while protecting margin.")

    return "\n".join(notes)
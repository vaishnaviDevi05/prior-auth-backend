def get_patient_name(pat):
    """Safely extract patient name from FHIR object."""
    try:
        if pat.name and len(pat.name) > 0:
            name_obj = pat.name[0]

            given = ""
            family = ""

            if hasattr(name_obj, "given") and name_obj.given:
                given = name_obj.given[0]

            if hasattr(name_obj, "family") and name_obj.family:
                family = name_obj.family

            full = f"{given} {family}".strip()
            return full if full else "Unknown"

        return "Unknown"

    except Exception:
        return "Unknown"

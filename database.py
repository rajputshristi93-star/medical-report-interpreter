import math

from supabase_client import get_supabase


def _json_safe(x):
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    if isinstance(x, dict):
        return {k: _json_safe(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_json_safe(v) for v in x]
    return x


def save_report(user_id, filename, source, context, results, explanation, confirmed=False):
    """Saves only when the user explicitly chose to save (confirmed=True)."""
    if not confirmed:
        raise PermissionError("Saving needs explicit user confirmation (confirmed=True).")

    data = {
        "user_id": user_id,
        "filename": filename,
        "source": source,
        "context": context,
        "results": _json_safe(results),
        "explanation": explanation,
    }
    response = get_supabase().table("reports").insert(data).execute()
    return response.data


def get_user_reports(user_id):
    response = (
        get_supabase()
        .table("reports")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


def delete_report(user_id, report_id):
    response = (
        get_supabase()
        .table("reports")
        .delete()
        .eq("id", report_id)
        .eq("user_id", user_id)
        .execute()
    )
    return response.data
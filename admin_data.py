"""Data access for the admin dashboard.

Every call uses the logged-in user's own Supabase client. The database decides what is allowed:
the admin functions check is_admin() themselves, and they return counts only, never report contents.
"""
import time

import pandas as pd
import streamlit as st

from supabase_client import get_supabase

DEFAULT_PROFILE = {"role": "user", "status": "active", "full_name": ""}
DOCTOR_COLS = ["name", "specialty", "qualification", "clinic", "address", "city", "phone", "website", "social_url",
               "source_url", "listing_basis", "verified_on"]
REQUIRED = ["name", "specialty", "city", "source_url", "listing_basis", "verified_on"]
SPECIALTIES = ["General Physician", "Diabetologist", "Endocrinologist", "Nephrologist", "Gastroenterologist",
               "Hepatologist", "Cardiologist", "Hematologist", "Rheumatologist", "Dietitian"]
BASIS = ["hospital website", "clinic website", "doctor's own website", "doctor gave permission",
         "government or institution page"]


# ---------------------------------------------------------------- who is this user?
def get_profile(user, max_age=60):
    """Role and status of the logged-in user, refreshed every minute. Works before the profiles table exists."""
    cached = st.session_state.get("profile")
    if cached and cached.get("id") == user.id and time.time() - cached.get("at", 0) < max_age:
        return cached
    from profile_data import get_details  # the same single query also fills the profile page cache

    prof = dict(DEFAULT_PROFILE)
    try:
        row = get_details(user, force=True)
        prof.update({k: row[k] for k in ("role", "status", "full_name") if row.get(k) is not None})
    except Exception as e:
        print("profile lookup failed:", str(e)[:120])
    prof.update({"id": user.id, "at": time.time()})
    st.session_state["profile"] = prof
    return prof


def is_admin(user):
    p = get_profile(user)
    return p.get("role") == "admin" and p.get("status") == "active"


# ---------------------------------------------------------------- admin functions
def _rpc(name, **params):
    return get_supabase().rpc(name, params).execute().data or []


def overview():
    rows = _rpc("admin_overview")
    return rows[0] if rows else {}


def users():
    df = pd.DataFrame(_rpc("admin_user_list"))
    if not df.empty:
        df["created_at"] = pd.to_datetime(df["created_at"], utc=True).dt.tz_convert(None)
    return df


def signups(days):
    df = pd.DataFrame(_rpc("admin_signups_by_day", days=days))
    if not df.empty:
        df["day"] = pd.to_datetime(df["day"])
    return df


def reports_per_day(days):
    df = pd.DataFrame(_rpc("admin_reports_by_day", days=days))
    if not df.empty:
        df["day"] = pd.to_datetime(df["day"])
    return df


def sources():
    return pd.DataFrame(_rpc("admin_reports_by_source"))


def audit(rows=100):
    df = pd.DataFrame(_rpc("admin_audit_list", max_rows=rows))
    if not df.empty:
        df["created_at"] = pd.to_datetime(df["created_at"], utc=True).dt.tz_convert(None)
    return df


def set_status(user_id, status):
    _rpc("admin_set_status", target=user_id, new_status=status)


def set_role(user_id, role):
    _rpc("admin_set_role", target=user_id, new_role=role)


def delete_reports(user_id):
    return _rpc("admin_delete_reports", target=user_id)


def log(action, target, detail):
    _rpc("admin_log", p_action=action, p_target=target, p_detail=detail)


# ---------------------------------------------------------------- doctor directory
def doctors():
    rows = (get_supabase().table("doctors").select("*").order("created_at", desc=True).limit(2000).execute().data or [])
    df = pd.DataFrame(rows, columns=["id"] + DOCTOR_COLS)
    df["verified_on"] = pd.to_datetime(df["verified_on"], errors="coerce").dt.date
    return df


def _clean(v):
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()[:10]
    v = str(v).strip()
    return v or None


def _record(row):
    return {c: _clean(row.get(c)) for c in DOCTOR_COLS}


def _missing(rec):
    return [c for c in REQUIRED if not rec.get(c)]


def save_doctors(original, edited):
    """Applies the changes made in the editor. Returns (added, updated, deleted, problems)."""
    sb = get_supabase()
    original = original.reset_index(drop=True)
    edited = edited.reset_index(drop=True)
    old = {r["id"]: _record(r) for _, r in original.iterrows()}
    added = updated = deleted = 0
    problems = []
    seen = set()
    for i, row in edited.iterrows():
        rec, rid = _record(row), _clean(row.get("id"))
        if not any(rec.values()):
            continue  # empty row
        miss = _missing(rec)
        if miss:
            problems.append(f"Row {i + 1} ({rec.get('name') or 'no name'}): missing {', '.join(miss)}")
            continue
        try:
            if rid is None:
                sb.table("doctors").insert(rec).execute()
                added += 1
            else:
                seen.add(rid)
                if rid in old and rec != old[rid]:
                    sb.table("doctors").update(rec).eq("id", rid).execute()
                    updated += 1
        except Exception as e:
            problems.append(f"Row {i + 1} ({rec.get('name')}): {str(e)[:90]}")
    for rid in old:
        if rid not in seen and rid in set(original["id"]):
            still_there = any(_clean(x) == rid for x in edited.get("id", []))
            if not still_there:
                try:
                    sb.table("doctors").delete().eq("id", rid).execute()
                    deleted += 1
                except Exception as e:
                    problems.append(f"Could not delete {old[rid].get('name')}: {str(e)[:90]}")
    if added or updated or deleted:
        log("doctors_edited", "doctors", f"{added} added, {updated} updated, {deleted} deleted")
    return added, updated, deleted, problems


def import_doctors(df):
    """Adds doctors from an uploaded CSV. Returns (added, problems)."""
    missing_cols = [c for c in REQUIRED if c not in df.columns]
    if missing_cols:
        return 0, [f"The file is missing these columns: {', '.join(missing_cols)}"]
    recs, problems = [], []
    for i, row in df.iterrows():
        rec = _record(row)
        if rec.get("name", "") and rec["name"].upper().startswith("EXAMPLE"):
            continue
        miss = _missing(rec)
        if miss:
            problems.append(f"Row {i + 2}: missing {', '.join(miss)}")
        else:
            recs.append(rec)
    added = 0
    for i in range(0, len(recs), 50):
        try:
            get_supabase().table("doctors").insert(recs[i:i + 50]).execute()
            added += len(recs[i:i + 50])
        except Exception as e:
            problems.append(f"A batch failed: {str(e)[:100]}")
    if added:
        log("doctors_imported", "doctors", f"{added} doctors imported from CSV")
    return added, problems

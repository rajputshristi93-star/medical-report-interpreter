"""Profile details and profile photo, stored in Supabase. Photos are shrunk to a small square JPEG before upload."""
import base64
import io
import time
from concurrent.futures import ThreadPoolExecutor

import streamlit as st
from PIL import Image, ImageOps

from supabase_client import get_supabase

BUCKET = "avatars"
MAX_UPLOAD = 3 * 1024 * 1024


def get_details(user, force=False):
    """The user's profile row. Returns {'_missing': True} if the profile tables are not set up yet."""
    cached = st.session_state.get("pf_cache")
    if cached and cached.get("id") == user.id and not force:
        return cached
    row, _ok = _fetch_row(get_supabase(), user)
    st.session_state["pf_cache"] = row
    return row


def _fetch_row(client, user):
    """One query for the whole profile row. Returns (row, ok). Safe to call from a background thread."""
    try:
        rows = client.table("profiles").select("*").eq("id", user.id).limit(1).execute().data
        row, ok = (dict(rows[0]) if rows else {}), True
    except Exception as e:
        print("profile details unavailable:", str(e)[:120])
        row, ok = {"_missing": True}, False
    if row and "avatar_path" not in row and not row.get("_missing"):
        row["_missing"] = True  # profile_setup.sql has not been run yet
    row["id"] = user.id
    return row, ok


def prefetch_after_login(user):
    """Right after sign-in: loads the profile row and the profile photo AT THE SAME TIME and fills the session caches,
    so the first page opens at once instead of making 3 or 4 requests one after another.
    The photo path is always '<user id>/avatar.jpg' (see save_avatar), so it can be fetched without waiting for the row."""
    t0 = time.perf_counter()
    client = get_supabase()  # created here, in the script thread; the workers only use it
    path = f"{user.id}/avatar.jpg"

    def photo():
        try:
            return client.storage.from_(BUCKET).download(path)
        except Exception:
            return None  # no photo yet (normal) or storage not set up

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_row, f_photo = pool.submit(_fetch_row, client, user), pool.submit(photo)
        (row, ok), raw = f_row.result(), f_photo.result()
    st.session_state["pf_cache"] = row
    if ok:  # same shape that admin_data.get_profile builds, so it does not ask the database again for a minute
        prof = {"role": "user", "status": "active", "full_name": ""}
        prof.update({k: row[k] for k in ("role", "status", "full_name") if row.get(k) is not None})
        prof.update({"id": user.id, "at": time.time()})
        st.session_state["profile"] = prof
    if raw and row.get("avatar_path") == path:
        st.session_state["pf_avatar"] = {"path": path, "id": user.id, "uri": "data:image/jpeg;base64," + base64.b64encode(raw).decode()}
    print(f"[login] profile + photo loaded in {time.perf_counter() - t0:.2f}s")


def clear_cache():
    for k in ("pf_cache", "pf_avatar"):
        st.session_state.pop(k, None)


def avatar_uri(user, details):
    """A data: address for the photo (so it can sit inside the page), or None."""
    path = details.get("avatar_path")
    if not path:
        return None
    cached = st.session_state.get("pf_avatar")
    if cached and cached.get("path") == path and cached.get("id") == user.id:
        return cached["uri"]
    try:
        raw = get_supabase().storage.from_(BUCKET).download(path)
        uri = "data:image/jpeg;base64," + base64.b64encode(raw).decode()
        st.session_state["pf_avatar"] = {"path": path, "id": user.id, "uri": uri}
        return uri
    except Exception as e:
        print("avatar download failed:", str(e)[:120])
        return None


def prepare_avatar(raw):
    """Crops to a centred square, shrinks to 256 px and strips camera data. Returns JPEG bytes."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
    img = ImageOps.fit(img.convert("RGB"), (256, 256), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, "JPEG", quality=86, optimize=True)  # no EXIF is written
    return out.getvalue()


def save_avatar(user, jpeg):
    path = f"{user.id}/avatar.jpg"
    get_supabase().storage.from_(BUCKET).upload(path, jpeg, {"content-type": "image/jpeg", "upsert": "true"})
    get_supabase().rpc("set_my_avatar", {"p_path": path}).execute()
    clear_cache()


def remove_avatar(user):
    try:
        get_supabase().storage.from_(BUCKET).remove([f"{user.id}/avatar.jpg"])
    except Exception as e:
        print("avatar remove:", str(e)[:100])
    get_supabase().rpc("set_my_avatar", {"p_path": None}).execute()
    clear_cache()


def save_details(user, name, phone, city, gender, dob, about):
    get_supabase().rpc("update_my_profile", {
        "p_full_name": name or "", "p_phone": phone or "", "p_city": city or "", "p_gender": gender or "",
        "p_date_of_birth": dob.isoformat() if dob else None, "p_about": about or ""}).execute()
    clear_cache()


def initials(text):
    parts = [p for p in str(text or "").replace("@", " ").replace(".", " ").split() if p]
    return ("".join(p[0] for p in parts[:2]) or "U").upper()

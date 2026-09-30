def add_status(results):
    for r in results:
        v, lo, hi = r.get("value"), r.get("ref_low"), r.get("ref_high")
        if v is None or (lo is None and hi is None):
            r["status"] = "unknown"
        elif lo is not None and v < lo:
            r["status"] = "low"
        elif hi is not None and v > hi:
            r["status"] = "high"
        else:
            r["status"] = "normal"
    return results
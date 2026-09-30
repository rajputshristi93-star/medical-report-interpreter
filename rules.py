def add_status(results):
    for r in results:
        v, lo, hi = r.get("value"), r.get("ref_low"), r.get("ref_high")
        r["flag"] = ""

        if v is None or (lo is None and hi is None):
            r["status"] = "unknown"
            continue

        if lo is not None and v < lo:
            r["status"] = "low"
        elif hi is not None and v > hi:
            r["status"] = "high"
        else:
            r["status"] = "normal"

        # Extreme values: possible typo, lab error, or a serious finding
        if hi is not None and v > hi * 3:
            r["flag"] = "extreme"
        elif lo is not None and lo > 0 and v < lo / 3:
            r["flag"] = "extreme"
    return results
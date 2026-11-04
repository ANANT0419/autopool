#!/usr/bin/env python3
"""Runs every AutoPool ride, bulb, sign-up and Arcus action against the local Firestore emulator only."""
import base64, json, sys, time, urllib.request, urllib.error

HOST = "http://127.0.0.1:8791"
P = "demo-autopool"
ROOT = f"projects/{P}/databases/(default)/documents"
NOW = int(time.time() * 1000)
HOUR = 3600 * 1000
assert "127.0.0.1" in HOST and P.startswith("demo-")


def b64(d):
    return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")


def token(uid, provider="anonymous", email=None, verified=None):
    t = int(time.time())
    c = {"sub": uid, "user_id": uid, "aud": P, "iss": f"https://securetoken.google.com/{P}", "iat": t, "exp": t + 3600,
         "auth_time": t, "firebase": {"sign_in_provider": provider, "identities": {}}}
    if email:
        c["email"] = email
    if verified is not None:
        c["email_verified"] = verified
    return b64({"alg": "none", "typ": "JWT"}) + "." + b64(c) + "."


def call(method, path, body=None, tok=None):
    req = urllib.request.Request(HOST + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + tok} if tok else {})})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def val(v):
    if isinstance(v, bool):
        return {"booleanValue": v}
    if isinstance(v, int):
        return {"integerValue": str(v)}
    if isinstance(v, str):
        return {"stringValue": v}
    if isinstance(v, list):
        return {"arrayValue": {"values": [val(x) for x in v]}}
    if isinstance(v, dict):
        return {"mapValue": {"fields": {k: val(x) for k, x in v.items()}}}
    raise TypeError(v)


fields = lambda d: {k: val(v) for k, v in d.items()}
OWNER_ADMIN = "owner"  # the emulator treats this token as an admin that skips the rules, used for setup only


def seed(path, d):
    s, b = call("PATCH", f"/v1/{ROOT}/{path}", {"fields": fields(d)}, OWNER_ADMIN)
    assert s == 200, (path, s, b)


def commit(path, d, tok, mask=None, exists=None):
    w = {"update": {"name": f"{ROOT}/{path}", "fields": fields(d)}}
    if mask is not None:
        w["updateMask"] = {"fieldPaths": mask}
    if exists is not None:
        w["currentDocument"] = {"exists": exists}
    return call("POST", f"/v1/{ROOT}:commit", {"writes": [w]}, tok)[0]


def query(col, field, floor, tok):
    q = {"structuredQuery": {"from": [{"collectionId": col}]}}
    if field:
        q["structuredQuery"]["where"] = {"fieldFilter": {"field": {"fieldPath": field}, "op": "GREATER_THAN", "value": val(floor)}}
        q["structuredQuery"]["orderBy"] = [{"field": {"fieldPath": field}, "direction": "ASCENDING"}]
    s, b = call("POST", f"/v1/{ROOT}:runQuery", q, tok)
    n = len([x for x in json.loads(b) if "document" in x]) if s == 200 else 0
    return s, n


A, B, C = token("a"), token("b"), token("c")
ME = token("own", "google.com", "anantgarg419@gmail.com", True)
FAKE_PW = token("x", "password", "anantgarg419@gmail.com", True)
OTHER_G = token("y", "google.com", "someone@gmail.com", True)
ra = {"uid": "a", "name": "A", "phone": "9000000001", "n": 1}
rb = {"uid": "b", "name": "B", "phone": "9000000002", "n": 1}
rc = {"uid": "c", "name": "C", "phone": "9000000003", "n": 1}


def ride(riders=None, **kw):
    return {"dir": "c2m", "leaveAt": NOW + HOUR, "createdAt": NOW, "creator": "a", "cancelled": False,
            "riders": riders if riders is not None else [ra, rb], **kw}


results = []


def check(name, want_ok, status):
    ok = status == 200
    good = ok == want_ok
    results.append(good)
    print(("PASS" if good else "FAIL"), "|", "should work   " if want_ok else "should be blocked", "|", name, "| got", status)


def upd(name, want, before, changes, tok):
    """The same write the app makes: only the changed fields are sent, on an existing ride."""
    rid = "r" + str(len(results))
    seed(f"rides/{rid}", before)
    check(name, want, commit(f"rides/{rid}", changes, tok, mask=list(changes), exists=True))


print("--- things students do today ---")
check("post a ride", True, commit("rides/new1", ride([ra]), A, exists=False))
check("post with a group of 4", True, commit("rides/new2", ride([{**ra, "n": 4}]), A, exists=False))
upd("join a ride", True, ride(), {"riders": [ra, rb, rc]}, C)
upd("join as 3 people", True, ride(), {"riders": [ra, rb, {**rc, "n": 3}]}, C)
upd("join as the 5th rider", True, ride([ra, rb, rc, {**rc, "uid": "d"}]), {"riders": [ra, rb, rc, {**rc, "uid": "d"}, {**rc, "uid": "c2"}]}, token("c2"))
upd("leave a ride", True, ride(), {"riders": [ra]}, B)
upd("leave when first of three", True, ride([rb, ra, rc]), {"riders": [ra, rc]}, B)
upd("leave twice (nothing changes)", True, ride([ra]), {"riders": [ra]}, B)
upd("poster cancels", True, ride(), {"cancelled": True}, A)
upd("poster changes time, nobody joined", True, ride([ra]), {"leaveAt": NOW + 2 * HOUR}, A)
upd("I'm at the gate", True, ride(), {"riders": [ra, {**rb, "gate": True}]}, B)
upd("I've paid", True, ride(), {"riders": [ra, {**rb, "paid": True}]}, B)
upd("I paid the driver", True, ride(), {"payer": "b", "riders": [ra, {**rb, "paid": True}]}, B)
upd("I paid the driver, with UPI", True, ride(), {"payer": "b", "riders": [ra, {**rb, "paid": True, "upi": "b@okaxis"}]}, B)
upd("I paid the driver, tapped twice", True, ride([ra, {**rb, "paid": True}], payer="b"), {"payer": "b", "riders": [ra, {**rb, "paid": True}]}, B)
upd("older ride with no 'cancelled' field, join", True, {k: v for k, v in ride().items() if k != "cancelled"}, {"riders": [ra, rb, rc]}, C)

print("--- reading ---")
seed("rides/old", ride(leaveAt=NOW - 48 * HOUR))
seed("rides/now", ride(leaveAt=NOW + HOUR))
s, n = query("rides", "leaveAt", NOW - HOUR, A)
check(f"app's live ride list (last hour), got {n} rides", True, s)
s, n = query("rides", "leaveAt", NOW - 2 * HOUR - 50 * 60 * 1000, A)
check("same list from a phone whose clock is 1h50 slow", True, s)
s, n = query("rides", None, 0, A)
check("student downloads ALL rides", False, s)
s, n = query("rides", "leaveAt", 0, A)
check("student asks for rides since the beginning", False, s)
s, n = query("rides", "leaveAt", NOW - 4 * HOUR, A)
check("student asks for rides from 4 hours ago", False, s)
s, n = query("rides", None, 0, ME)
check(f"you download all rides in admin, got {n} rides", True, s)
s, n = query("rides", None, 0, FAKE_PW)
check("password login with your email downloads all rides", False, s)
check("student reads one ride by its ID (needed to join)", True, call("GET", f"/v1/{ROOT}/rides/now", None, A)[0])

seed("bulbs/a", {"uid": "a", "name": "A", "phone": "9000000001", "dir": "c2m", "until": NOW + HOUR})
seed("bulbs/old", {"uid": "old", "name": "O", "phone": "9000000009", "dir": "c2m", "until": NOW - 48 * HOUR})
s, n = query("bulbs", "until", NOW, B)
check(f"app's live bulb list, got {n}", True, s)
s, n = query("bulbs", None, 0, B)
check("student downloads ALL bulbs", False, s)
s, n = query("bulbs", "until", 0, B)
check("student asks for bulbs since the beginning", False, s)
check("turn my bulb on", True, commit("bulbs/b", {"uid": "b", "name": "B", "phone": "9000000002", "dir": "c2m", "until": NOW + HOUR}, B))
check("turn my bulb off", True, commit("bulbs/b", {"uid": "b", "until": 0}, B))
check("turn someone else's bulb off", False, commit("bulbs/a", {"uid": "a", "until": 0}, B))

print("--- misuse that should now be blocked ---")
upd("stranger cancels someone's ride", False, ride(), {"cancelled": True}, C)
upd("rider who isn't the poster cancels", False, ride(), {"cancelled": True}, B)
upd("stranger changes the time", False, ride([ra]), {"leaveAt": NOW + 2 * HOUR}, C)
upd("poster changes time after someone joined", False, ride(), {"leaveAt": NOW + 2 * HOUR}, A)
upd("remove another rider", False, ride(), {"riders": [ra]}, C)
upd("poster removes a rider", False, ride(), {"riders": [ra]}, A)
upd("empty a ride", False, ride(), {"riders": []}, C)
upd("add someone else as a rider", False, ride(), {"riders": [ra, rb, rc]}, token("z"))
upd("swap a rider for yourself", False, ride(), {"riders": [ra, rc]}, C)
upd("change another rider's phone number", False, ride(), {"riders": [ra, {**rb, "phone": "9999999999"}]}, C)
upd("mark another rider as paid", False, ride(), {"riders": [ra, {**rb, "paid": True}]}, A)
upd("raise your own seats to fill the auto", False, ride(), {"riders": [ra, {**rb, "n": 5}]}, B)
upd("join a cancelled ride", False, ride(cancelled=True), {"riders": [ra, rb, rc]}, C)
upd("6th rider joins", False, ride([ra, rb, rc, {**rc, "uid": "d"}, {**rc, "uid": "e"}]), {"riders": [ra, rb, rc, {**rc, "uid": "d"}, {**rc, "uid": "e"}, {**rc, "uid": "f"}]}, token("f"))
upd("join claiming 9 seats", False, ride(), {"riders": [ra, rb, {**rc, "n": 9}]}, C)
upd("change who posted the ride", False, ride(), {"creator": "c"}, C)
upd("mark someone else as the payer", False, ride(), {"payer": "a", "riders": [{**ra, "paid": True}, rb]}, B)
upd("replace the payer", False, ride(payer="a"), {"payer": "b", "riders": [ra, {**rb, "paid": True}]}, B)
upd("non-rider sets themselves as payer", False, ride(), {"payer": "c"}, C)
check("post a ride as someone else", False, commit("rides/bad1", ride([ra]), B, exists=False))
check("post a ride with extra riders", False, commit("rides/bad2", ride(), A, exists=False))
check("post with someone else as first rider", False, commit("rides/bad3", ride([rb]), A, exists=False))
check("signed-out visitor posts", False, commit("rides/bad4", ride([ra]), None, exists=False))
check("delete a ride", False, call("POST", f"/v1/{ROOT}:commit", {"writes": [{"delete": f"{ROOT}/rides/now"}]}, A)[0])

print("--- sign-ups and Arcus stay as they are ---")
check("save my sign-up", True, commit("users/a", {"uid": "a", "name": "A", "phone": "9000000001"}, A))
check("read my sign-up", True, call("GET", f"/v1/{ROOT}/users/a", None, A)[0])
check("read someone else's sign-up", False, call("GET", f"/v1/{ROOT}/users/a", None, B)[0])
s, n = query("users", None, 0, ME)
check(f"you list sign-ups in admin, got {n}", True, s)
s, n = query("users", None, 0, A)
check("student lists sign-ups", False, s)
seed("arcus/settings", {"live": False})
seed("arcus/menu", {"categories": [], "rev": 1})
check("student reads the Arcus switch", True, call("GET", f"/v1/{ROOT}/arcus/settings", None, A)[0])
check("student reads the menu", True, call("GET", f"/v1/{ROOT}/arcus/menu", None, A)[0])
check("signed-out visitor reads the menu", False, call("GET", f"/v1/{ROOT}/arcus/menu", None, None)[0])
check("you flip the switch", True, commit("arcus/settings", {"live": True}, ME))
check("you save the menu", True, commit("arcus/menu", {"categories": [], "rev": 2}, ME))
check("student flips the switch", False, commit("arcus/settings", {"live": True}, A))
check("student changes the menu", False, commit("arcus/menu", {"categories": [], "rev": 3}, A))
check("other Google account changes the menu", False, commit("arcus/menu", {"categories": [], "rev": 3}, OTHER_G))
check("password login with your email changes the menu", False, commit("arcus/menu", {"categories": [], "rev": 3}, FAKE_PW))

print(f"\n{sum(results)} of {len(results)} passed")
sys.exit(0 if all(results) else 1)

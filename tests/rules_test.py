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

print("--- Arcus ordering ---")
def batch(tok, *writes):
    """Sends several changes as one all-or-nothing commit, the way the app's order transaction does."""
    out = []
    for path, d, stamps, ex in writes:
        w = {"update": {"name": f"{ROOT}/{path}", "fields": fields(d)}}
        if ex is not None:
            w["currentDocument"] = {"exists": ex}
        if stamps:
            w["updateTransforms"] = [{"fieldPath": f, "setToServerValue": "REQUEST_TIME"} for f in stamps]
        out.append(w)
    return call("POST", f"/v1/{ROOT}:commit", {"writes": out}, tok)[0]


STAMPS = ["createdAt", "statusAt"]
line = {"id": "i1", "en": "SAMPLE item 1", "hi": "", "price": 10, "qty": 2, "veg": True}


def order(uid="a", **kw):
    return {"uid": uid, "code": "A7K2", "name": "A", "phone": "9000000001", "mode": "pickup", "items": [line], "count": 2,
            "total": 20, "note": "", "shift": "day", "status": "placed", **kw}


def counts(placed, last, confirmed=0, ready=0):
    return {"placed": placed, "confirmed": confirmed, "ready": ready, "lastOrder": last}


def place(oid, tok, uid, open_after, placed_after, **kw):
    return batch(tok, (f"arcusOrders/{oid}", order(uid, **kw), STAMPS, False),
                 (f"arcusMine/{uid}", {"open": open_after, "lastOrder": oid}, None, None),
                 ("arcus/counts", counts(placed_after, oid), None, None))


def cancel(oid, tok, uid, open_after, placed_after, reason="Changed my mind"):
    w = {"update": {"name": f"{ROOT}/arcusOrders/{oid}", "fields": fields({"status": "cancelled", "cancelReason": reason, "cancelledBy": "student"})},
         "updateMask": {"fieldPaths": ["status", "cancelReason", "cancelledBy"]},
         "updateTransforms": [{"fieldPath": "statusAt", "setToServerValue": "REQUEST_TIME"}],
         "currentDocument": {"exists": True}}
    rest = [{"update": {"name": f"{ROOT}/arcusMine/{uid}", "fields": fields({"open": open_after, "lastOrder": oid})}},
            {"update": {"name": f"{ROOT}/arcus/counts", "fields": fields(counts(placed_after, oid))}}]
    return call("POST", f"/v1/{ROOT}:commit", {"writes": [w, *rest]}, tok)[0]


def fresh(uid, opened, placed):
    """Clean starting point: Arcus on, this student has these open orders, counts as given."""
    seed("arcus/settings", {"live": True})
    seed("arcus/counts", counts(placed, "seed"))
    seed(f"arcusMine/{uid}", {"open": opened, "lastOrder": "seed"})
    for x in opened:
        seed(f"arcusOrders/{x}", order(uid))


call("DELETE", f"/v1/{ROOT}/arcus/counts", None, OWNER_ADMIN)
seed("arcus/settings", {"live": True})
check("very first order, counts and my list don't exist yet", True, place("o1", A, "a", ["o1"], 1))
check("read my own order", True, call("GET", f"/v1/{ROOT}/arcusOrders/o1", None, A)[0])
check("check an order that doesn't exist yet", True, call("GET", f"/v1/{ROOT}/arcusOrders/nothing", None, A)[0] in (200, 404) and 200 or 403)
check("read the overall counts", True, call("GET", f"/v1/{ROOT}/arcus/counts", None, B)[0])
check("read my open orders list", True, call("GET", f"/v1/{ROOT}/arcusMine/a", None, A)[0])
fresh("a", ["p1", "p2"], 2)
check("third open order", True, place("p3", A, "a", ["p1", "p2", "p3"], 3))
fresh("a", ["c1"], 1)
check("cancel my order while Placed", True, cancel("c1", A, "a", [], 0))
s = call("GET", f"/v1/{ROOT}/arcusOrders/c1", None, A)
check("the cancelled order is still readable, so the student sees it", True, s[0])

print("--- Arcus ordering misuse ---")
fresh("a", ["p1", "p2", "p3"], 3)
check("4th open order", False, place("p4", A, "a", ["p1", "p2", "p3", "p4"], 4))
check("empty my list to get round the limit", False, commit("arcusMine/a", {"open": [], "lastOrder": "p1"}, A))
check("shrink my list while placing, to get round the limit", False, place("p4", A, "a", ["p4"], 4))
fresh("a", [], 0)
check("order sent without updating the counts", False, batch(A, ("arcusOrders/n1", order(), STAMPS, False), ("arcusMine/a", {"open": ["n1"], "lastOrder": "n1"}, None, None)))
check("order sent without updating my list", False, batch(A, ("arcusOrders/n1", order(), STAMPS, False), ("arcus/counts", counts(1, "n1"), None, None)))
check("order alone", False, batch(A, ("arcusOrders/n1", order(), STAMPS, False)))
check("counts raised by 5 with one order", False, place("n1", A, "a", ["n1"], 5))
check("counts raised with no order", False, commit("arcus/counts", counts(9, "n1"), A))
check("counts lowered with no cancel", False, commit("arcus/counts", counts(0, "n1"), A))
check("student changes the confirmed count", False, batch(A, ("arcusOrders/n1", order(), STAMPS, False), ("arcusMine/a", {"open": ["n1"], "lastOrder": "n1"}, None, None), ("arcus/counts", counts(1, "n1", confirmed=4), None, None)))
check("order as someone else", False, place("n1", B, "a", ["n1"], 1))
check("order that starts as Ready", False, place("n1", A, "a", ["n1"], 1, status="ready"))
check("order with a very long note", False, place("n1", A, "a", ["n1"], 1, note="x" * 141))
check("order with no items", False, place("n1", A, "a", ["n1"], 1, items=[]))
check("order with too many lines", False, place("n1", A, "a", ["n1"], 1, items=[line] * 31))
check("order with a negative total", False, place("n1", A, "a", ["n1"], 1, total=-5))
check("order with an extra field", False, place("n1", A, "a", ["n1"], 1, paid=True))
check("order for delivery (pickup only at launch)", False, place("n1", A, "a", ["n1"], 1, mode="delivery"))
check("signed-out visitor orders", False, place("n1", None, "a", ["n1"], 1))
seed("arcus/settings", {"live": False})
check("order while Arcus is switched off", False, place("n1", A, "a", ["n1"], 1))
fresh("a", ["c2"], 1)
seed("arcusOrders/c2", order(status="confirmed"))
check("cancel after it was confirmed", False, cancel("c2", A, "a", [], 0))
fresh("a", ["c3"], 1)
check("cancel someone else's order", False, cancel("c3", B, "b", [], 0))
check("cancel with no reason", False, cancel("c3", A, "a", [], 0, reason=""))
check("cancel without updating the counts", False, commit("arcusOrders/c3", {"status": "cancelled", "cancelReason": "x", "cancelledBy": "student"}, A, mask=["status", "cancelReason", "cancelledBy"]))
check("mark my own order Ready", False, commit("arcusOrders/c3", {"status": "ready"}, A, mask=["status"]))
check("lower my own total", False, commit("arcusOrders/c3", {"total": 1}, A, mask=["total"]))
check("read someone else's order", False, call("GET", f"/v1/{ROOT}/arcusOrders/c3", None, B)[0])
s, n = query("arcusOrders", None, 0, A)
check("student lists orders", False, s)
check("read someone else's open orders", False, call("GET", f"/v1/{ROOT}/arcusMine/a", None, B)[0])
check("delete an order", False, call("POST", f"/v1/{ROOT}:commit", {"writes": [{"delete": f"{ROOT}/arcusOrders/c3"}]}, A)[0])

print("--- Arcus shop details and Mishu's controls ---")
shop = {"dayStart": "09:30", "nightStart": "20:30", "closeAt": "04:00", "lastOrder": "03:45", "dayPhone": "9000000011", "nightPhone": ""}
check("you save opening hours and phones", True, commit("arcus/shop", shop, ME))
check("student reads opening hours", True, call("GET", f"/v1/{ROOT}/arcus/shop", None, A)[0])
check("signed-out visitor reads handler phones", False, call("GET", f"/v1/{ROOT}/arcus/shop", None, None)[0])
check("student changes opening hours", False, commit("arcus/shop", shop, A))
check("other Google account changes phones", False, commit("arcus/shop", shop, OTHER_G))
check("a badly written phone number", False, commit("arcus/shop", {**shop, "dayPhone": "call me"}, ME))
check("you move an order to Confirmed", True, commit("arcusOrders/c3", {"status": "confirmed"}, ME, mask=["status"]))
check("you read any order", True, call("GET", f"/v1/{ROOT}/arcusOrders/c3", None, ME)[0])
s, n = query("arcusOrders", None, 0, ME)
check(f"you list orders, got {n}", True, s)
check("you correct the counts", True, commit("arcus/counts", counts(0, "fix"), ME))
check("password login with your email moves an order", False, commit("arcusOrders/c3", {"status": "ready"}, FAKE_PW, mask=["status"]))

print("--- Arcus handlers ---")
DAY = token("hd", "password", "arcus-day@autopool-93a9d.firebaseapp.com")
NIGHT = token("hn", "password", "arcus-night@autopool-93a9d.firebaseapp.com")
STRANGER_PW = token("hx", "password", "someone@autopool-93a9d.firebaseapp.com")
GOOGLE_SAME = token("hg", "google.com", "arcus-day@autopool-93a9d.firebaseapp.com", True)


def step(oid, tok, uid, status, counts_after, open_after=None, reason=None):
    """The handler's transaction: the order, the counts and, when it finishes, the student's open list."""
    f = {"status": status}
    if reason is not None:
        f.update({"cancelReason": reason, "cancelledBy": "handler"})
    writes = [{"update": {"name": f"{ROOT}/arcusOrders/{oid}", "fields": fields(f)}, "updateMask": {"fieldPaths": list(f)},
               "updateTransforms": [{"fieldPath": "statusAt", "setToServerValue": "REQUEST_TIME"}], "currentDocument": {"exists": True}},
              {"update": {"name": f"{ROOT}/arcus/counts", "fields": fields(counts_after)}}]
    if open_after is not None:
        writes.append({"update": {"name": f"{ROOT}/arcusMine/{uid}", "fields": fields({"open": open_after, "lastOrder": oid})}})
    return call("POST", f"/v1/{ROOT}:commit", {"writes": writes}, tok)[0]


def at(status, oid="h1"):
    fresh("a", [oid], 1)
    seed(f"arcusOrders/{oid}", order(status=status))
    return oid


check("handler confirms", True, step(at("placed"), DAY, "a", "confirmed", counts(0, "h1", confirmed=1)))
check("other handler marks ready", True, step(at("confirmed"), NIGHT, "a", "ready", counts(0, "h1", ready=1)))
check("handler marks done", True, step(at("ready"), DAY, "a", "done", counts(0, "h1"), []))
check("handler cancels with a reason", True, step(at("confirmed"), DAY, "a", "cancelled", counts(0, "h1"), [], "Item ran out"))
check("handler reads any order", True, call("GET", f"/v1/{ROOT}/arcusOrders/h1", None, DAY)[0])
check("handler reads a student's open list", True, call("GET", f"/v1/{ROOT}/arcusMine/a", None, DAY)[0])
open_q = {"structuredQuery": {"from": [{"collectionId": "arcusOrders"}], "where": {"fieldFilter": {"field": {"fieldPath": "status"}, "op": "IN", "value": val(["placed", "confirmed", "ready"])}}}}
check("handler's live list of open orders", True, call("POST", f"/v1/{ROOT}:runQuery", open_q, DAY)[0])
check("student asks for the open orders list", False, call("POST", f"/v1/{ROOT}:runQuery", open_q, A)[0])
s, n = query("arcusOrders", None, 0, DAY)
check("handler downloads the full order history", False, s)
check("handler marks items out of stock", True, commit("arcus/stock", {"out": ["i1", "i2"]}, DAY))
check("student reads what is out of stock", True, call("GET", f"/v1/{ROOT}/arcus/stock", None, A)[0])

print("--- Arcus handler misuse ---")
check("skip from Placed to Done", False, step(at("placed"), DAY, "a", "done", counts(0, "h1"), []))
check("go backwards from Ready to Confirmed", False, step(at("ready"), DAY, "a", "confirmed", counts(0, "h1", confirmed=1)))
check("reopen a finished order", False, step(at("done"), DAY, "a", "ready", counts(0, "h1", ready=1)))
check("cancel with no reason", False, step(at("placed"), DAY, "a", "cancelled", counts(0, "h1"), []))
check("done without clearing the student's list", False, step(at("ready"), DAY, "a", "done", counts(0, "h1")))
at("placed")
check("confirm without updating the counts", False, commit("arcusOrders/h1", {"status": "confirmed"}, DAY, mask=["status"]))
check("handler changes an order's total", False, commit("arcusOrders/h1", {"total": 1}, DAY, mask=["total"]))
check("handler deletes an order", False, call("POST", f"/v1/{ROOT}:commit", {"writes": [{"delete": f"{ROOT}/arcusOrders/h1"}]}, DAY)[0])
check("handler changes the menu", False, commit("arcus/menu", {"categories": [], "rev": 9}, DAY))
check("handler flips the Arcus switch", False, commit("arcus/settings", {"live": False}, DAY))
check("handler changes hours or phones", False, commit("arcus/shop", shop, DAY))
check("handler lists sign-ups", False, query("users", None, 0, DAY)[0])
check("stranger with a password login moves an order", False, step(at("placed"), STRANGER_PW, "a", "confirmed", counts(0, "h1", confirmed=1)))
check("Google login with a handler's address moves an order", False, step(at("placed"), GOOGLE_SAME, "a", "confirmed", counts(0, "h1", confirmed=1)))
check("student moves their own order to Confirmed", False, step(at("placed"), A, "a", "confirmed", counts(0, "h1", confirmed=1)))
check("student marks items out of stock", False, commit("arcus/stock", {"out": ["i1"]}, A))
check("stranger with a password login changes stock", False, commit("arcus/stock", {"out": []}, STRANGER_PW))
check("bad alert channel name", False, commit("arcus/shop", {**shop, "dayTopic": "has spaces/slash"}, ME))
check("you save alert channel names", True, commit("arcus/shop", {**shop, "dayTopic": "arcus-day-abc", "nightTopic": "arcus-night-def"}, ME))

print(f"\n{sum(results)} of {len(results)} passed")
sys.exit(0 if all(results) else 1)

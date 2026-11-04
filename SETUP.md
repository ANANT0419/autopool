# AutoPool: go-live setup (about 15 minutes, all free)

The app is one file: `index.html`. Open it now and it runs in **demo mode** (rides stay on your phone only).
To make it **live for the whole hostel**, do the 3 steps below.

---

## Step 1: Firebase (the shared online database), ~7 min
1. Go to **console.firebase.google.com**, sign in with Google, and choose **Create project** (name: `autopool`). Turn Google Analytics off. Stay on the free **Spark** plan; no card is needed.
2. **Build → Authentication → Get started → Sign-in method → Anonymous → Enable.**
   (This gives each phone an invisible ID so people can't edit each other's rides.)
3. **Build → Firestore Database → Create database** → location `asia-south1 (Mumbai)` → **Start in production mode**.
4. Open the **Rules** tab, replace everything with the rules below (the same text is in `firestore.rules`), then click **Publish**:
```
rules_version = '2';
service cloud.firestore {
  match /databases/{db}/documents {

    function signedIn() {
      return request.auth != null;
    }
    // Mishu's Google account only. The sign-in method is checked too, so an email + password
    // login (handlers, from Stage 4) can never pass as this account.
    function isOwner() {
      return signedIn()
        && request.auth.token.get('email', '') == 'anantgarg419@gmail.com'
        && request.auth.token.get('email_verified', false) == true
        && request.auth.token.firebase.sign_in_provider == 'google.com';
    }

    // Lists of rides and bulbs only reach back this far, so nobody can download the full history.
    // 3 hours leaves room for a phone whose clock is a little wrong (the app asks for the last hour).
    function recentCutoff() {
      return request.time.toMillis() - 3 * 60 * 60 * 1000;
    }

    // ---- Ride changes: each one below matches one action in the app ----
    function changedOnly(keys) {
      return request.resource.data.diff(resource.data).affectedKeys().hasOnly(keys);
    }
    function isPoster() {
      return resource.data.creator == request.auth.uid;
    }
    function nothingChanged() {
      return request.resource.data.diff(resource.data).affectedKeys().size() == 0;
    }
    function validSeats(rider) {
      return rider.n is int && rider.n >= 1 && rider.n <= 5;
    }
    // Join: your own entry is added at the end, and everyone else stays as they were.
    function isJoin(before, after) {
      return changedOnly(['riders'])
        && resource.data.get('cancelled', false) == false
        && after.size() == before.size() + 1
        && after[0:before.size()] == before
        && after[before.size()].uid == request.auth.uid
        && validSeats(after[before.size()]);
    }
    // Leave: only your own entry is removed.
    function isLeave(before, after) {
      return changedOnly(['riders'])
        && after.size() == before.size() - 1
        && before.hasAll(after)
        && before.removeAll(after).size() == 1
        && before.removeAll(after)[0].uid == request.auth.uid;
    }
    // "At the gate", "I've paid": only your own entry changes, and not your seat count.
    function changesOnlyMyEntry(before, after) {
      return after.size() == before.size()
        && before.removeAll(after).size() == 1
        && after.removeAll(before).size() == 1
        && before.removeAll(after)[0].uid == request.auth.uid
        && after.removeAll(before)[0].uid == request.auth.uid
        && after.removeAll(before)[0].n == before.removeAll(after)[0].n;
    }
    function isSetPayer(before, after) {
      return changedOnly(['payer', 'riders'])
        && request.resource.data.payer == request.auth.uid
        && resource.data.get('payer', request.auth.uid) == request.auth.uid
        && changesOnlyMyEntry(before, after);
    }
    function isCancel() {
      return isPoster() && changedOnly(['cancelled']) && request.resource.data.cancelled == true;
    }
    function isSetTime(before) {
      return isPoster() && changedOnly(['leaveAt'])
        && request.resource.data.leaveAt is number
        && before.size() <= 1;
    }

    // ---- Rides. Maximum 5 riders. Riders can only add, remove or change themselves. ----
    match /rides/{id} {
      allow get: if signedIn();
      allow list: if isOwner() || (signedIn() && resource.data.leaveAt > recentCutoff());
      allow create: if signedIn()
        && request.resource.data.creator == request.auth.uid
        && request.resource.data.leaveAt is number
        && request.resource.data.riders.size() == 1
        && request.resource.data.riders[0].uid == request.auth.uid
        && validSeats(request.resource.data.riders[0]);
      allow update: if signedIn()
        && request.resource.data.creator == resource.data.creator
        && request.resource.data.riders.size() <= 5
        && (nothingChanged()
          || isJoin(resource.data.riders, request.resource.data.riders)
          || isLeave(resource.data.riders, request.resource.data.riders)
          || (changedOnly(['riders']) && changesOnlyMyEntry(resource.data.riders, request.resource.data.riders))
          || isSetPayer(resource.data.riders, request.resource.data.riders)
          || isCancel()
          || isSetTime(resource.data.riders));
      allow delete: if false;
    }

    // ---- 💡 Flexible bulb: each person can only switch their own, and only recent ones can be listed. ----
    match /bulbs/{uid} {
      allow get: if signedIn() && uid == request.auth.uid;
      allow list: if signedIn() && resource.data.until > recentCutoff();
      allow write: if signedIn() && uid == request.auth.uid
        && request.resource.data.uid == request.auth.uid;
    }

    // ---- Sign-ups: each phone reads and saves its own record. Only admin.html reads everyone's. ----
    match /users/{uid} {
      allow read: if (signedIn() && uid == request.auth.uid) || isOwner();
      allow write: if signedIn() && uid == request.auth.uid
        && request.resource.data.uid == request.auth.uid;
    }

    // ---- Arcus (new in Stage 2): any app user can read. Only Mishu can change. ----
    match /arcus/settings {
      allow read: if signedIn();
      allow write: if isOwner() && request.resource.data.live is bool;
    }
    match /arcus/menu {
      allow read: if signedIn();
      allow write: if isOwner()
        && request.resource.data.categories is list
        && request.resource.data.rev is int;
    }

    // ---- Arcus ordering (new in Stage 3) ----
    // Stage 4 adds the handlers' logins here. Until then only Mishu can move an order along.
    function isStaff() {
      return isOwner();
    }
    function orderPath(id) {
      return /databases/$(db)/documents/arcusOrders/$(id);
    }
    function isNewOrder(path) {
      return !exists(path) && getAfter(path).data.uid == request.auth.uid;
    }
    function isStudentCancel(path) {
      return exists(path)
        && get(path).data.uid == request.auth.uid
        && get(path).data.status == 'placed'
        && getAfter(path).data.status == 'cancelled';
    }
    // The order, the counts and "my open orders" must all change together, so they can't drift apart.
    function movesAllTogether(id) {
      return getAfter(/databases/$(db)/documents/arcus/counts).data.lastOrder == id
        && getAfter(/databases/$(db)/documents/arcusMine/$(request.auth.uid)).data.lastOrder == id;
    }
    function validNewOrder(id) {
      let d = request.resource.data;
      return d.keys().hasOnly(['uid', 'code', 'name', 'phone', 'mode', 'items', 'count', 'total', 'note', 'shift', 'status', 'createdAt', 'statusAt'])
        && d.keys().hasAll(['uid', 'code', 'name', 'phone', 'mode', 'items', 'count', 'total', 'note', 'shift', 'status', 'createdAt', 'statusAt'])
        && d.uid == request.auth.uid
        && d.status == 'placed'
        && d.mode == 'pickup'
        && d.shift in ['day', 'night']
        && d.code is string && d.code.size() == 4
        && d.name is string && d.name.size() > 0 && d.name.size() <= 60
        && d.phone is string && d.phone.size() > 0 && d.phone.size() <= 15
        && d.note is string && d.note.size() <= 140
        && d.items is list && d.items.size() > 0 && d.items.size() <= 30
        && d.count is int && d.count > 0 && d.count <= 200
        && d.total is int && d.total >= 0
        && d.createdAt == request.time
        && d.statusAt == request.time
        && get(/databases/$(db)/documents/arcus/settings).data.live == true
        && movesAllTogether(id);
    }
    // A student can cancel only their own order, only while it is still "Placed", and must give a reason.
    function validStudentCancel(id) {
      let d = request.resource.data;
      return signedIn()
        && resource.data.uid == request.auth.uid
        && resource.data.status == 'placed'
        && d.diff(resource.data).affectedKeys().hasOnly(['status', 'statusAt', 'cancelReason', 'cancelledBy'])
        && d.status == 'cancelled'
        && d.statusAt == request.time
        && d.cancelledBy == 'student'
        && d.cancelReason is string && d.cancelReason.size() > 0 && d.cancelReason.size() <= 80
        && movesAllTogether(id);
    }

    // Orders: students can see only their own, and can never list them. Nobody can delete one.
    // Asking for an order that doesn't exist yet is allowed: placing an order checks it wasn't already sent.
    match /arcusOrders/{id} {
      allow get: if signedIn() && (resource == null || resource.data.uid == request.auth.uid || isStaff());
      allow list: if isStaff();
      allow create: if signedIn() && validNewOrder(id);
      allow update: if isStaff() || validStudentCancel(id);
      allow delete: if false;
    }

    // One small record per student listing their open orders. This is what limits them to 3.
    match /arcusMine/{uid} {
      allow read: if signedIn() && (uid == request.auth.uid || isStaff());
      allow create, update: if isStaff() || (signedIn() && uid == request.auth.uid && validMineStep());
      allow delete: if false;
    }
    function validMineStep() {
      let d = request.resource.data;
      let before = resource == null ? [] : resource.data.open;
      let path = orderPath(d.lastOrder);
      return d.keys().hasOnly(['open', 'lastOrder'])
        && d.lastOrder is string
        && d.open is list && d.open.size() <= 3
        && ((isNewOrder(path)
              && d.open.size() == before.size() + 1
              && d.open.hasAll(before)
              && d.open.hasAny([d.lastOrder]))
          || (isStudentCancel(path)
              && d.open.size() == before.size() - 1
              && before.hasAll(d.open)
              && before.hasAny([d.lastOrder])
              && !d.open.hasAny([d.lastOrder])));
    }

    // The overall numbers students see: how many orders, never whose or what. No cart numbers.
    match /arcus/counts {
      allow read: if signedIn();
      allow create, update: if isStaff() || (signedIn() && validCountStep());
      allow delete: if false;
    }
    function validCountStep() {
      let d = request.resource.data;
      let placed = resource == null ? 0 : resource.data.placed;
      let confirmed = resource == null ? 0 : resource.data.confirmed;
      let ready = resource == null ? 0 : resource.data.ready;
      let path = orderPath(d.lastOrder);
      return d.keys().hasOnly(['placed', 'confirmed', 'ready', 'lastOrder'])
        && d.keys().hasAll(['placed', 'confirmed', 'ready', 'lastOrder'])
        && d.lastOrder is string
        && d.confirmed == confirmed
        && d.ready == ready
        && ((isNewOrder(path) && d.placed == placed + 1)
          || (isStudentCancel(path) && d.placed == placed - 1));
    }

    // Opening hours and handler phone numbers. Read only while the Arcus tab is open. Only Mishu can change them.
    match /arcus/shop {
      allow read: if signedIn();
      allow write: if isOwner()
        && request.resource.data.dayStart.matches('^[0-2][0-9]:[0-5][0-9]$')
        && request.resource.data.nightStart.matches('^[0-2][0-9]:[0-5][0-9]$')
        && request.resource.data.closeAt.matches('^[0-2][0-9]:[0-5][0-9]$')
        && request.resource.data.lastOrder.matches('^[0-2][0-9]:[0-5][0-9]$')
        && request.resource.data.dayPhone.matches('^([0-9]{10})?$')
        && request.resource.data.nightPhone.matches('^([0-9]{10})?$');
    }
  }
}
```
5. Click **Project settings (gear icon) → Your apps → `</>` Web**. Register the app with the name `autopool`. Skip hosting.
   Copy the `firebaseConfig = { ... }` block it shows.
6. Open `index.html` in any text editor and find `firebase: null,` near the top. Replace it with the config you copied:
```js
firebase: { apiKey: "...", authDomain: "...", projectId: "...", storageBucket: "...", messagingSenderId: "...", appId: "..." },
```
   (It's safe for this key to be public. The rules above are what protect the data.)

## Step 2: Phone alerts when the app is closed (ntfy), ~2 min
1. Pick a hard-to-guess topic name, e.g. `cdl-autopool-x7k2`, and put it in `index.html`:
   `ntfyTopic: "cdl-autopool-x7k2",`
2. Everyone who wants alerts installs **ntfy** (App Store / Play Store), taps **+**, and subscribes to that topic.
   The 🔔 button in the app shows these same instructions.

## Step 3: Put it online (free link), ~3 min
**Easiest:** go to **app.netlify.com/drop** and drag the `autopool` folder onto the page. You get a link like `https://xyz.netlify.app`. Sign up (free) so the link doesn't expire, and rename the site to something like `cdl-autopool`.
**To update later:** edit `index.html`, then drag the folder onto the same site's **Deploys** page.

Upload the **whole folder**: `index.html`, `manifest.json`, `sw.js`, and the 3 `icon-*.png` files (`icon.svg` is optional). The install feature needs all of them.

Share the link in the hostel WhatsApp group. People then install it like an app:
- **Android (Chrome):** a yellow **Install AutoPool** bar appears → tap **Install**. Or use the ⋮ menu → **Install app**.
- **iPhone:** the link **must be opened in Safari** (not inside WhatsApp's or Instagram's built-in browser; tap ⋯ → Open in Safari). Tap **Install** on the yellow bar for steps, or go straight to **Share ⬆️ → Add to Home Screen**.

After that it has its own icon, opens full-screen with no browser bar, and still opens with no internet (live rides need internet).
**After you update `index.html`:** people get the new version the next time they open the app with internet.

---

## Free-tier headroom
Firestore's free tier allows 50,000 reads and 20,000 writes a day. A busy hostel day with ~200 rides and ~300 users stays well under that. Old rides are hidden after leave time + 3 min and never deleted (storage use is tiny).

## Known limits (v1)
- No OTP: anyone can type any number. That's fine in a closed hostel group; add OTP later only if misuse happens (SMS costs money).
- In-app pop-ups on **iPhone** work only if the app was added to the Home Screen (iOS 16.4+). ntfy works everywhere.
- Shuttle times are hard-coded from the official sheet (search `SHUTTLE` in `index.html` to edit them).
- Uses the phone's clock. A phone with wrong time shows wrong countdowns.

## If something breaks
Tap 👤 → 🐞 **Issue log** → **Open** → **Copy** → send it to whoever maintains the app.

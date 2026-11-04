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

# AutoPool: go-live setup (about 15 minutes, all free)

The app is one file: `index.html`. Open it now and it runs in **demo mode** (rides stay on your phone only).
To make it **live for the whole hostel**, do the 3 steps below.

---

## Step 1: Firebase (the shared online database), ~7 min
1. Go to **console.firebase.google.com**, sign in with Google, and choose **Create project** (name: `autopool`). Turn Google Analytics off. Stay on the free **Spark** plan; no card is needed.
2. **Build → Authentication → Get started → Sign-in method → Anonymous → Enable.**
   (This gives each phone an invisible ID so people can't edit each other's rides.)
3. **Build → Firestore Database → Create database** → location `asia-south1 (Mumbai)` → **Start in production mode**.
4. Open the **Rules** tab, replace everything with the rules below, then click **Publish**:
```
rules_version = '2';
service cloud.firestore {
  match /databases/{db}/documents {
    match /rides/{id} {
      allow read: if request.auth != null;
      allow create: if request.auth != null
        && request.resource.data.creator == request.auth.uid
        && request.resource.data.riders.size() <= 4;
      allow update: if request.auth != null
        && request.resource.data.creator == resource.data.creator
        && request.resource.data.riders.size() <= 4;
      allow delete: if false;
    }
    match /bulbs/{uid} {            // 💡 "I'm flexible" — each person can only switch their own bulb
      allow read: if request.auth != null;
      allow write: if request.auth != null && uid == request.auth.uid
        && request.resource.data.uid == request.auth.uid;
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
Tap 🐞 (issue log) → **Copy** → send it to whoever maintains the app.

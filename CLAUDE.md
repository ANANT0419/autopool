# AutoPool (AUTO-BUDDY): handover notes for Claude

## What this is
AutoPool is a small web app for students at IMT Ghaziabad. It lets them share autos between the **CDL hostel** and the **IMT main campus** when they miss the shuttle. Someone posts "leaving in X min" and others join the same auto.
- It's live on **GitHub Pages** (repo `ANANT0419/autopool`) and hostel students already use it, so **don't break what's working**.
- Owner: Mishu (Anant Garg), anantgarg419@gmail.com. A collaborator also has access to the repo.

## How to work with Mishu
- Explain things **without jargon**, define every new term, and keep replies short.
- **New ideas:** brainstorm with him topic by topic first, with research, before writing any code.
- **Builds:** once an idea is agreed, make sensible assumptions and start. List the assumptions at the end.
- Ask before starting any big build he didn't ask for.
- Use **free tools only**: Firebase free (Spark) plan, GitHub Pages, ntfy. Nothing that needs a card.
- `main` is protected. Work on a branch and open a pull request. Mishu merges it.

## Files
- `index.html`: the whole app (HTML, CSS and JS in one file). The settings block near the top is `window.AUTOPOOL_CONFIG`.
- `arcus.html`: the handler screen for Arcus orders (installs as its own app via `arcus.webmanifest`). See `ARCUS_PLAN.md`.
- `admin.html`: stats page (sign-ups, rides posted or cancelled, money saved, CSV downloads). Only `anantgarg419@gmail.com` can see it.
- `sw.js` + `manifest.json` + `icon-*`: let the site install like an app and open offline.
  - **Bump the cache version `V` in `sw.js` (currently "autopool-v7") whenever you change files**, or phones keep showing the old app.
- `ARCUS_PLAN.md`: the brief for Arcus, the campus canteen ordering feature, and its stages. Read it before any Arcus work.
- `firestore.rules`: the full security rules, to paste into the Firebase console. Keep it the same as the block in `SETUP.md`.
- `SETUP.md`: the original go-live guide. Note that its Netlify hosting step is out of date: the app now runs on GitHub Pages.

## Product decisions (keep these)
- **Fares** are for the whole auto: ₹80 for 1–3 people, ₹100 for 4, ₹120 for 5. Maximum 5 people.
  - The fares are set in two places: `AUTOPOOL_CONFIG.fares` in `index.html` and `FARES` in `admin.html`. Keep them the same.
- **Both directions:** CDL→Campus and Campus→CDL.
- **Login:** name + phone number, so riders can call each other to hold the auto. Firebase anonymous sign-in sits underneath.
- **WhatsApp sharing** is offered *after* posting a ride. It never happens automatically.
- **Mascot "Chhotu"** (a kid in a yellow cap, drawn as SVG) follows the user, in the spirit of "Inku" from Mishu's tattoo-studio site.
- **💡 "Flexible" bulb toggle:** for people who are open to going with no fixed time. They gather first, then agree on a time.
- **Alerts:**
  - In-app alerts.
  - Closed-app alerts via the **ntfy** app. Topic: `imt-cdl-autopool-66cea7`, plus a per-user channel.
- **Works on Android and iPhone.** On iPhone, it must be installed from Safari.
- **Languages:** English and Hindi toggle. There's also a large-text mode.
- **🐞 Issue log:** a row in the 👤 You & settings sheet, with a red dot on 👤 when there are new errors. Every feature should log errors there, even when things work, so Mishu can report them. Each phone only sees its own log.

## Backend
- Firebase project `autopool-93a9d` (Firestore + anonymous Auth). The web config in `index.html` is safe to be public. The Firestore security rules are what protect the data.
- **Live rules:** the same as `firestore.rules` once published. The 5-rider limit is in them.
- **Arcus records:** `arcus/settings` (`live` = the off switch; 1 read per app open) and `arcus/menu` (the whole menu as one record; read only while the Arcus tab is open). Later stages added `arcus/shop`, `arcus/counts`, `arcus/stock`, `arcusOrders/{id}` and `arcusMine/{uid}`: see `ARCUS_PLAN.md`.
- `admin.html` signs in under its own Firebase app name ("admin"), so the Google login and the app's anonymous login on one phone don't replace each other.
  - Any new feature that adds data needs matching rule changes. Write out the new rules for Mishu to paste into the console, because Claude can't edit the console.

## How to test and release safely
- **App changes:** test on a copy outside the repo with `firebase: null`, `ntfyTopic: ""` and `FIREBASE = null` in `admin.html`. Nothing reaches real students, and Arcus can be switched on in the copy's own admin page.
- **Rule changes:** run them against Google's Firestore emulator on this computer, then `python3 tests/rules_test.py`. Download `cloud-firestore-emulator-v1.19.8.jar` to a temporary folder, not the repo (ask Mishu first), and start it with `--host 127.0.0.1 --port 8791 --project_id demo-autopool --rules firestore.rules`. Add a check for every new rule. Firebase's Rules playground can't test lists or a whole join.
- **Publishing rules:** Claude can load rules into the console editor once Mishu has signed in, but Mishu clicks Publish. Keep `firestore.rules` and the block in `SETUP.md` the same.
- **Arcus off switch:** Mishu flips it himself. Claude's safety checks block that action.
- **The admin page doesn't update itself:** reload `admin.html` before trusting the switch it shows.

## Status (Nov 2026)
Live and in use. Arcus Stage 4 (handler screen, switched off for students until Mishu flips it) is built. See `ARCUS_PLAN.md` for the next stages.

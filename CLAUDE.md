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
- `admin.html`: stats page (sign-ups, rides posted or cancelled, money saved, CSV downloads). Only `anantgarg419@gmail.com` can see it.
- `sw.js` + `manifest.json` + `icon-*`: let the site install like an app and open offline.
  - **Bump the cache version `V` in `sw.js` (currently "autopool-v4") whenever you change files**, or phones keep showing the old app.
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
- **🐞 Issue log button:** every feature should log errors there, even when things work, so Mishu can report them.

## Backend
- Firebase project `autopool-93a9d` (Firestore + anonymous Auth). The web config in `index.html` is safe to be public. The Firestore security rules are what protect the data.
- **Check the live rules:** `SETUP.md` now says `riders.size() <= 5` (it used to say 4). The app allows 5 people.
  - Check the live rules in the Firebase console. If they still say 4, a 5th person can't join. Update them to 5.
- **Arcus records:** `arcus/settings` (`live` = the off switch; 1 read per app open) and `arcus/menu` (the whole menu as one record; read only while the Arcus tab is open).
- `admin.html` signs in under its own Firebase app name ("admin"), so the Google login and the app's anonymous login on one phone don't replace each other.
  - Any new feature that adds data needs matching rule changes. Write out the new rules for Mishu to paste into the console, because Claude can't edit the console.

## Status (Nov 2026)
Live and in use. Arcus Stage 2 (browsable menu, switched off for students) is built. See `ARCUS_PLAN.md` for the next stages.

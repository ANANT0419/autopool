# Arcus: campus canteen ordering feature (the brief)

Saved at the start of Stage 2 so later stages can use it. This is Mishu's brief, as written.

## Decisions already made (don't reopen them)
- Handler login: email + password, one Firebase login per handler, using made-up addresses. Security rules allow only those exact logins.
- Shifts: day 9:30 AM-8:30 PM, night 8:30 PM-4:00 AM. Last orders 3:45 AM (changeable setting). The handler on shift owns every open order. Orders still open at handover pass on with a "from day shift" or "from night shift" tag, plus a banner on the handler screen. "Call Arcus" dials whoever is on shift now. Each shift has its own ntfy channel.
- Pickup only at launch, built so delivery can be added later. Students pay at Arcus, with no online payment.
- No photos at launch. Text menu with veg/non-veg marks.
- Menu: categories in an order I set; each item has an English name, optional Hindi name, price, veg/non-veg mark and in-stock switch. Out-of-stock items stay visible, greyed out. Store the whole menu as ONE Firestore record, to protect the free plan's limit of about 50,000 reads a day.
- Handler phone numbers and shift times are edited in admin.html and stored in Firestore, NOT in AUTOPOOL_CONFIG, because the repo is public.
- ntfy order alerts carry only basics, like "New order #A7K2, 3 items". No names or phone numbers.
- Limit how many open orders one person can have.
- Students can't see other people's orders. They can see overall numbers only, like how many orders are placed or waiting, with no names, items or phone numbers. (Added after Stage 2. Keep these counts in one small record to protect the daily reads. Mishu decided in Stage 3 to drop "in cart": carts live on each phone, so students see only real orders, as waiting, being made and ready.)
- Design: match Stage 1 exactly. Glass, one blue accent, yellow only on Chhotu, dark mode, spring motion, Inter on Android, solid bars on slow phones. Respect reduce-motion. No heavy libraries.
- Don't invent menu items or prices. Use items labelled "SAMPLE" until I send real ones.

## Stages (one pull request each; I merge)
1. Design refresh: done.
2. Menu: this stage.
3. Ordering: cart with + / - steppers and live rolling total, optional note, "Order placed" moment with order number, "Call Arcus", status Placed > Confirmed > Ready > Done or Cancelled with a reason, opening hours. Students can cancel only while "Placed".
4. Handler screen: arcus.html, installable, with login, live orders, big status buttons, call button, today's count, sound and vibration, ntfy alerts sent from the student's phone, one-tap out of stock. Arcus goes live when I flip the switch.
5. Admin stats: orders per day, by shift, top items, cancellations.

## Built in Stage 3
- Records: `arcusOrders/{id}` (one per order), `arcusMine/{uid}` (a student's open order IDs; this enforces the limit of 3), `arcus/counts` (the overall numbers), `arcus/shop` (hours and handler phones, edited in admin.html).
- A student's order, `arcusMine` and `arcus/counts` must change in the same transaction. The rules refuse anything else.
- Prices come from the menu when the order is placed, but the rules can't compare them with the menu. A student could fake a total, so the handler should charge from the menu.
- Opening hours are checked on the student's phone only, using its clock.

## Must do in Stage 4
- Add the handlers' logins to `isStaff()` in `firestore.rules`.
- Every status change must also update `arcus/counts`. Done and Cancelled must also remove the order from the student's `arcusMine`, or that student stays stuck at the limit.
- Remove nothing else: the "Test:" buttons on order cards only appear in demo mode.

## Stage 2 scope
- Rides and Arcus tabs with clear navigation between them.
- Browsable Arcus menu, with no ordering yet.
- Menu editing in admin.html, for my Google account only: add, edit and delete items, set prices and categories, switch stock on and off. Restyle admin.html to match the app.
- An off switch that keeps Arcus hidden from students until Stage 4. I turn it on from admin.html.
- Hindi text for everything new, and errors logged to the issue log.
- Write out the complete Firestore rules for me to paste, keeping the 5-rider limit and everything that works today.

## Safety
- Students use this app daily. Nothing that works today may break.
- Never test against live data. Test on a copy with firebase: null and ntfyTopic: "", so nothing reaches real students.
- Work on a branch and open a pull request. Bump the sw.js cache version and APP_VERSION.
- Test on a phone-sized screen in both languages and dark mode before the pull request.
- Afterwards, list your assumptions, the rules I must paste, and what to test on real phones.

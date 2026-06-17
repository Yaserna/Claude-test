# CLAUDE.md — Project Memory & Handoff

> This file is the complete memory of the project so any future Claude Code
> session can continue without losing context. It records the working agreement
> with the user, the environment constraints, the architecture, every feature
> built, and the outstanding items. Read it fully before doing anything.

---

## 0) Working agreement with the user (NON-NEGOTIABLE — follow exactly)

The user set these rules at the very start. Honor them in every reply:

1. **Treat the user as completely non-technical** (no knowledge of networking,
   coding, command line, or any digital/technical topic). Explain everything in
   the simplest possible terms, as if for the first time. (User framed it as
   "IQ below 20, not a software engineer" — meaning: zero assumptions, maximum
   simplicity. In practice the user is more capable than that, e.g. installed
   ADB themselves, but keep explanations simple anyway.)
2. **One step at a time.** Whenever the user must run code or a command, give
   **exactly one** step, then **wait** for their confirmation/result before the
   next step. Never dump multiple manual steps at once.
3. **Everything the user must copy** (code, commands, links, anything) goes in a
   **copyable code block**.
4. **The user's shorthand replies:**
   - `.` (a dot) = "everything ran with no error, all good."
   - `3` (the number three) = "the command produced no output and the terminal
     just moved to the next line — ambiguous, needs investigation."
   - A full pasted output = "I don't know if it worked; you (Claude) analyze it."
5. **For every command, state the platform:** Windows or Linux.
6. **Roles:** The user is "the hands"; **Claude is the boss/engineer.** The user
   is only the interface between Claude and the outside world / the user's phone
   and PC. Claude makes the engineering decisions and drives.
7. **Challenge the user.** If an idea is flawed, wrong, or impossible, say so
   plainly and honestly (no flattery). Tell them when something can't be done.
8. **Reply in Persian (Farsi).** The user communicates in Persian.

Style that worked well: short, warm Persian messages; mark the user's actionable
step with a 🟢; end with a single clear question; use honest "🔴 challenge"
notes when needed.

---

## 1) The project

A **personal Android SMS app** that clones Xiaomi **"Mi Message"** (system
package `com.android.mms`, shown in Persian as **«پیام‌رسانی»**) and adds private
/ decoy customizations. **Personal use only — never published** (so cloning
Mi's look, name, and icon is fine for the user's own device).

Target device: the user's **Xiaomi phone (MIUI / HyperOS, Android, dual-SIM,
Persian, RTL)**. The app becomes the **default SMS app**.

### The 4 core custom ("private/decoy") features — the whole point of the app
1. **Hidden contacts:** messages from user-selected numbers are **completely
   hidden** — stored only in a private local DB, **never** written to the system
   SMS store, and excluded from the main conversation list.
2. **Decoy notification:** when a hidden contact messages, the notification shows
   a **fake sender name + fake text**. Tapping it opens a **chosen innocent
   ("decoy target") conversation**, NOT the hidden section. The decoy
   notification is intentionally **plain (no action buttons)**. (As of Session 3,
   each hidden number can have its **own** decoy; a global decoy is the default.)
3. **Secret entrance to the real hidden section:** **long-press the + (FAB)**
   on the home screen (~2s as of Session 2) → PIN screen → hidden section.
   (Management of hidden contacts happens ONLY inside the hidden section; there
   is deliberately **no trace** of the hidden feature on the main screen.)
4. **Decoy "private folder":** **pull the conversation list down** → the whole
   list slides down revealing a **lock icon + "release to open private folder"**
   behind it (mirrors Mi Message's real gesture) → release → opens a **decoy,
   intentionally empty** screen titled **«پیام‌های خصوصی»**. This is bait for
   anyone who knows Mi's gesture; the real hidden data is elsewhere (feature 3).

---

## 2) Environment & build/delivery pipeline (CRITICAL — read carefully)

- Claude runs in an **isolated, ephemeral Linux container**. It has **Java 21**
  and **Gradle**, but **no Android SDK**, and the network policy **BLOCKS
  `dl.google.com` and `maven.google.com`** (403). Allowed: `github.com`,
  `repo1.maven.org` (Maven Central), `services.gradle.org`, `plugins.gradle.org`.
  → **Android cannot be built inside the container.** Do not try.
- **Builds run on GitHub Actions** via `.github/workflows/build.yml`: sets up
  JDK 17 (temurin), runs `./gradlew assembleDebug`, uploads the APK artifact,
  and publishes it to a Release tagged **`latest`** (via
  `softprops/action-gh-release`). `permissions: contents: write`.
- **Repo:** `Yaserna/Claude-test` (ORIGINAL; see §9 — renamed to
  `Yaserna/Yaser-D.z`). **Work branch (sessions 1–2):**
  `claude/sleepy-carson-jtkc15`. **Work branch (session 3 onward):** `Mi-Message`.
  The workflow triggers on push to `claude/**`, `Mi-Message`, and `main`.
- **The user installs the APK from the public Release URL** (open on the phone).
  ORIGINAL (sessions 1–2):
  ```
  https://github.com/Yaserna/Claude-test/releases/download/latest/app-debug.apk
  ```
  CURRENT (session 3 onward — see §9):
  ```
  https://github.com/Yaserna/Yaser-D.z/releases/download/latest/app-debug.apk
  ```
- **Fixed signing keystore** committed at `app/keystore.jks`
  (storePassword/keyPassword = `android`, alias = `shared`), wired into BOTH the
  debug and release `signingConfig`. This makes every CI build sign **identically**
  so the user gets **in-place updates (no uninstall)**. NOTE: build #1 used CI's
  ephemeral debug key, so the user had to uninstall once before build #2; every
  build since updates in place.
- **Per-change loop (what to do every time):**
  1. Edit code. 2. `git add -A` and commit (author name "Claude", email
  `novulefok93@gmail.com`; do NOT put the model id anywhere). 3. Push to the work
  branch (retry w/ backoff on network errors). 4. Wait ~150–165s. 5. Check the
  run via `mcp__github__actions_list` (method `list_workflow_runs`, owner
  `Yaserna`, repo `Yaser-D.z`, resource_id `build.yml`, filter branch). 6. If
  `success`, tell the user (Persian, 🟢) to update from the Release link and what
  to test. 7. User tests and reports.
- **Cannot compile locally** → write code carefully, rely on CI to catch compile
  errors, and iterate from logs. Builds have been green; keep it that way.
- GitHub MCP tools (`mcp__github__*`) flap (connect/disconnect); re-load via
  ToolSearch `select:mcp__github__actions_list` when needed. Plain `git` over
  the allowed `github.com` works for push. **Note (§9):** this environment's git
  proxy **refuses branch deletion** (`push --delete` / `push :branch` hang up),
  and the GitHub MCP has no delete-branch tool → branch deletion must be done by
  the user on the GitHub web UI.

### User device / PC facts
- **PC:** Windows 11. ADB (platform-tools) extracted to `C:\platform-tools`.
- **Phone:** Xiaomi, dual-SIM, Persian, **screen density 2.75** (1080 px wide;
  derived from Mi's FAB = 155px = 56dp). ADB device serial **`d62fc44f`**. A
  stale wireless-ADB entry `192.168.43.14:45733 (offline)` caused
  "more than one device/emulator" → fixed with `adb -s d62fc44f ...` then
  `adb disconnect`.
- **UI replication method (clean-room):** the user captured Mi Message's exact
  view hierarchies with `adb -s d62fc44f shell uiautomator dump` +
  `adb pull /sdcard/window_dump.xml` for: home, settings, "more settings",
  selection mode, and the chat screen. These dumps (and screenshots) were used
  for pixel-accurate replication. **We deliberately did NOT decompile the
  proprietary Mi Message APK** — the user pushed for it twice; Claude declined
  on principle (copyright / clean-room) and explained the clean-room method
  (observable UI only) is both proper and sufficient. uiautomator dumps are
  observable runtime output, so they are fine.

---

## 3) Tech stack & conventions

- **Kotlin.** AGP **8.5.2**, Gradle wrapper **8.7**, Kotlin **1.9.24**,
  compileSdk/targetSdk **34**, minSdk **24**, JDK 17 on CI. **viewBinding**
  enabled. **Material3** theme.
- `applicationId` / `namespace` = **`com.privatemsg.app`**.
- Dependencies: core-ktx 1.13.1, appcompat 1.7.0, material 1.12.0,
  constraintlayout 2.1.4, recyclerview 1.3.2, swiperefreshlayout 1.1.0
  (the last is now UNUSED — pull-to-reveal was reimplemented manually; can be
  removed later), androidx.biometric 1.1.0 (Session 2).
- **Forced Persian + RTL app-wide:** `ui/BaseActivity` overrides
  `attachBaseContext` to apply `Locale("fa")` via `createConfigurationContext`
  (sets locale + layout direction). **Every activity extends `BaseActivity`**
  (not AppCompatActivity). This is why the app is RTL regardless of phone
  language. `BaseActivity` also hosts the shared `showNumberMenu()` and
  `showListMenu()`.
- **All user-facing strings live in `res/values/strings.xml` (Persian).**
- **Theme/colors** (`values/themes.xml` = `Theme.Material3.Dark.NoActionBar`,
  `values/colors.xml`): bg `#000000`, surface `#1C1C1E`, pill `#2C2C2E`,
  **accent `#F7A623` (orange)**, textPrimary white, textSecondary `#9E9E9E`,
  avatarGray `#3A3A3C`. Sent bubble green `#1FA055`; received bubble = pill grey.
  Delivered tick / links blue `#1A73E8`.
- Dialogs/menus use **`MaterialAlertDialogBuilder`** (rounded corners).
- All popup/context menus go through **`showListMenu`** (centered, fixed width).

### Permissions (AndroidManifest)
SEND_SMS, RECEIVE_SMS, READ_SMS, RECEIVE_MMS, READ_CONTACTS, READ_PHONE_STATE,
POST_NOTIFICATIONS, ACCESS_FINE_LOCATION, USE_BIOMETRIC. Default-SMS-app
components: SmsReceiver (SMS_DELIVER), MmsReceiver (WAP_PUSH, stub),
HeadlessSmsSendService (RESPOND_VIA_MESSAGE, stub), MainActivity (MAIN/LAUNCHER +
SEND/SENDTO sms/… + ACTION_SEND text/plain share). `<application android:name=".App">`.

---

## 4) Architecture / file map (package `com.privatemsg.app`)

### data/
- **Models.kt** — `Conversation(threadId, address, snippet, date, unread=false)`,
  `Message(id, threadId, address, body, date, type, subId=-1, status=-1)`.
  `type`: 1=inbox, 2=sent, 5=failed. `status`: 0=delivered (Telephony).
- **SmsRepository.kt** — `getConversations()` (one row per thread, excludes
  hidden numbers, computes `unread`), `getMessages(threadId)`,
  `storeSentMessage(address, body, subId): Uri?`, `deleteMessage(id)`,
  `deleteThread(threadId)`, `markThreadRead(threadId)`, `migrateToHidden`,
  `restoreFromHidden`, `purgeHiddenFromProvider(hiddenDb)` (defense-in-depth).
- **HiddenDbHelper.kt** — SQLite `hidden.db`, now **v4** (see §9):
  `hidden_sms(id, address, body, date, type, sub_id, status, read)`.
  `insert(...)` (incoming type=1 → read=0, else read=1; returns row id),
  `updateStatus(id, status)`, `markRead(address)`, `hasUnread(address)`,
  `getConversations()`, `getMessages(address)`, `deleteById`, `deleteByAddress`.
- **SecureStore.kt** — SharedPreferences `secure_prefs`:
  - PIN as **salted SHA-256** (`setPin/checkPin/hasPin`).
  - **Global decoy:** `decoyName`, `decoyText`, `decoyTarget`.
  - **Per-number decoy (§9):** `decoyNameFor/decoyTextFor/decoyTargetFor(address)`
    (fall back to the global values), `setDecoyFor(address,name,text,target)`,
    `hasCustomDecoy(address)`, `clearDecoyFor(address)` (called from
    `removeHiddenNumber`). Stored under `decoy_*_<normalized>` keys.
  - Hidden numbers (StringSet of original address; match via `normalize()`):
    `addHiddenNumber/removeHiddenNumber/isHidden/getHiddenNumbers`.
  - `normalize(address)`: real phone numbers (digits/separators, ≥7 digits) →
    **last 10 digits**; operator/alphanumeric sender IDs → **lowercased text**.
  - Pinned threads, `deliveryReportEnabled`, `fontScale`, `uiScale`,
    `fingerprintEnabled`, per-conversation SIM (`getThreadSim/setThreadSim`).
- **ContactsHelper.kt** — `displayFor/nameFor` via PhoneLookup; shared
  thread-safe `ConcurrentHashMap` cache (static).
- **SimHelper.kt** — `sims(): List<Sim(subId, slot)>`; `defaultSubId()`.
- **FavoritesDbHelper.kt** — SQLite `favorites.db`; `add/getAll/delete`.

### ui/ (all extend BaseActivity)
- **BaseActivity.kt** — forces fa/RTL; applies font/ui scale; auto-locks the
  hidden section on background (`leavesToMainOnBackground`); `showNumberMenu`,
  `showListMenu`.
- **MainActivity.kt** — home; background load; live `ContentObserver`; search
  index; selection mode; FAB tap = compose, **FAB ~2s long-press = PinActivity**;
  pull-to-reveal → DecoyPrivateActivity; handles compose + share intents.
- **ConversationActivity.kt** — normal chat (provider-backed); bubbles, ticks,
  in-bubble SIM tag, attach menu, per-thread SIM, message multi-select,
  live `ContentObserver`.
- **HiddenConversationActivity.kt** — hidden chat (hidden.db-backed); same UI,
  attach hidden; FLAG_SECURE. **(§9)** marks read on resume, cancels its decoy
  notification on resume, and reloads **live** via the `ACTION_HIDDEN_REFRESH`
  broadcast (also marks read + cancels decoy when a message arrives while
  resumed; tracks `resumedNow` via onResume/onPause).
- **ConversationAdapter.kt** — conversation rows (avatar, unread dot/bold,
  selection checkbox).
- **MessageAdapter.kt** — message bubbles; `Linkifier`; full-row long-press;
  message multi-select; failed→sender-side w/ red ✕.
- **Linkifier.kt** — clickable URLs + number runs (≥4 digits; skip `: / -`).
- **ContactSuggestAdapter.kt** — recipient autocomplete.
- **HiddenActivity.kt** — the real hidden section. Lists every registered hidden
  number (with latest message or "no messages yet"); shows the **unread dot**
  (§9). Toolbar menu: Add hidden number / Decoy notification (global) /
  Fingerprint / Change PIN. **(§9)** long-press a row → menu: **«اعلان اختصاصی»**
  (opens DecoySettings for that number) / **«نمایش دوباره»** (unhide).
  Runs `purgeHiddenFromProvider` on open. FLAG_SECURE.
- **PinActivity.kt** — lock-screen PIN keypad (rounded keys, standard size,
  auto-enter); optional fingerprint unlock. FLAG_SECURE.
- **DecoySettingsActivity.kt** — edit decoy fake name/text + pick target.
  **(§9)** dual-mode: launched **without** `address` → edits the **global**
  decoy; launched **with** an `address` extra → edits that **one number's**
  decoy and titles the screen `decoy_title_for`.
- **ConversationPickerActivity.kt**, **FavoritesActivity.kt**,
  **SettingsActivity.kt** (Delivery report toggle, Display sizes, About credit),
  **DecoyPrivateActivity.kt** (empty «پیام‌های خصوصی»).
- **Digits.kt** — `String.toLatinDigits()`.

### sms/
- **SmsReceiver.kt** — `SMS_DELIVER`. If sender `isHidden` → store in hidden DB +
  `Notifier.showDecoy(context, secure, address)` + **(§9)** broadcast
  `ACTION_HIDDEN_REFRESH` (so an open hidden chat updates live), then return
  (never touches provider). Else → insert to provider + `Notifier.showIncoming`.
- **Notifier.kt** — `showIncoming` uses **MessagingStyle** + Reply/Mark-read/
  Delete actions. `showDecoy(context, secure, address)` **(§9)**: per-number
  fake name/text/target (fallback to global), **distinct notif id**
  `("decoy_"+normalize(address)).hashCode()`, plain (no actions). `cancelDecoy(
  context, address)` **(§9)** cancels that number's decoy.
- **NotificationActionReceiver.kt** — REPLY (RemoteInput) / MARK_READ / DELETE.
- **SmsStatusReceiver.kt** — SENT/DELIVERED for provider messages; hidden
  delivery (`ACTION_HIDDEN_DELIVERED` → `updateStatus`, broadcasts
  `ACTION_HIDDEN_REFRESH`).
- **MmsReceiver.kt**, **HeadlessSmsSendService.kt** — stubs.

### root
- **App.kt** — Application; foreground tracker (`App.inForeground`).

---

## 5) Chronological log of user requests & how each was resolved

(So nothing is lost. Each item = a user ask → what was built.)

1. **Working rules** established (see §0).
2. Decided the project: Android SMS app cloning Mi Message, personal use.
3. Defined the 4 core features.
4. **Milestone 1** — minimal default-SMS app verified on the Xiaomi (install ✓,
   default ✓, read ✓, send ✓, receive ✓, notify ✓).
5. **Hidden system** — private DB, hide numbers, global decoy, PIN, contact names.
6. Refinements: remove "Hide" from the main list; pick decoy target from a chat.
7. **Register a hidden number directly.**
8. **Appearance** — dark RTL theme; home + chat; long-press menus; rounded menus.
9. Declined decompiled Mi code; accepted ADB `uiautomator dump` (clean-room).
10. **Multi-select mode.**
11. Force RTL + SIM selection.
12. Compose-from-contacts; contact picker; real-notification tap; layout dir.
13. Inline contact search; clickable links/numbers; faster search.
14. Slow cold start fix; FAB 3s; Change PIN; MIUI autostart guidance.
15. Settings + sent/delivered ticks + SIM tag + notification actions.
16. SIM memory; time + colored ticks; unread; live list; orange icon.
17. SIM tag below bubble; sent ticks black; unread bold; time stays black.
18. MessagingStyle inline reply.
19. Input bar redesign; + attach menu (contact/location); PIN keypad; MMS deferred.
20. SIM badge left/smaller; stricter number links; bigger bottom keypad.
21. Full-width keypad.
22. Decoy private folder via graphical pull-reveal.
23. Wrote CLAUDE.md + CONVERSATION_LOG.md (original handoff).
24–31. **Session 2** — see §8.
32–35. **Session 3** — see §9.

---

## 6) Outstanding / deferred / to verify

- **MMS image & general attachments** — NOT built (complex/fragile). The + menu
  has only **Send contact** and **Send location** (both sent as text SMS).
- **Delivery (second tick)** — normal AND hidden — depends on the carrier
  returning a delivery report; out of our control.
- **Pull-to-reveal polish** — may want fade-in / threshold tuning.
- **Main-list update latency** — ContentObserver re-queries all SMS; small delay.
- Some **old messages have no `sub_id`** → no SIM tag on them (expected).
- `swiperefreshlayout` dependency is unused (safe to drop later).

---

## 7) How to continue (quick start for the next session)

1. You are on branch **`Mi-Message`** of **`Yaserna/Yaser-D.z`** (see §9).
2. Make changes → commit (author "Claude") → push to `Mi-Message` → CI builds →
   the user updates from the Release link in §2. You **cannot** build locally.
3. Keep the working agreement (§0): Persian, one step at a time, copyable blocks,
   say Windows/Linux, challenge bad ideas, you are the engineer.
4. The whole UI is Persian + RTL (BaseActivity). Strings → `values/strings.xml`.
5. The real hidden section = long-press + (~2s) → PIN. The decoy private folder =
   pull list down. Don't ever surface the real hidden feature on the main UI.

---

## 8) Session 2 — continued work (APPEND-ONLY; everything in §0–§7 is unchanged)

> This section records everything built in the second working session. Where a
> value here differs from above (e.g. FAB long-press is now 2s), THIS section is
> the newer truth. (Session 3 in §9 is newer still.)

### 8.0 Session/branch note
- Opened on an empty branch; all real code was on `claude/sleepy-carson-jtkc15`.
  User chose to continue on that branch. Keystore, CI workflow, `latest` Release
  URL unchanged — in-place updates still work.

### 8.1 New dependency / permission / manifest
- **Dependency:** `androidx.biometric:biometric:1.1.0`. **Permission:**
  `USE_BIOMETRIC`. **Application class:** `.App`. **Share:** ACTION_SEND
  text/plain intent-filter on MainActivity.

### 8.2 New files
- **`App.kt`** (foreground tracker), **`ui/Digits.kt`** (`toLatinDigits`),
  `res/drawable/key_button.xml` + `key_button_ok.xml` (rounded PIN keys),
  `res/drawable/sim_card_shape.xml` (in-bubble SIM chip).

### 8.3 SecureStore additions
- `fontScale`, `uiScale`, `fingerprintEnabled`.

### 8.4 BaseActivity additions
- Display size (font/ui scale via attachBaseContext + recreate); auto-lock of the
  hidden section on background (`leavesToMainOnBackground`); `showListMenu` (center
  gravity, fixed 86% width).

### 8.5 Message UI / adapter
- Full-row long-press; failed/queued sends stay sender-side (red ✕); SIM tag
  moved inside the bubble (blue chip, white English slot); all numbers Latin;
  message multi-select (choose/select-all/copy/delete) in normal + hidden chats.

### 8.6 Sending / delivery
- Multipart SMS everywhere; hidden delivery reports (hidden.db v3 `status`,
  delivery PendingIntent + refresh broadcast).

### 8.7 Tap-the-title → manage the number
- Saved → contact card; unsaved → `ACTION_VIEW tel:` (dialer number page).

### 8.8 Hidden section: no trace anywhere else
- `purgeHiddenFromProvider` runs when HiddenActivity opens (defense-in-depth).

### 8.9 Fingerprint unlock
- Toggle in HiddenActivity menu; `BiometricPrompt` in PinActivity; PIN auto-enter.

### 8.10 Settings screen
- Display section (text size + whole-UI/DPI, steps 0.85/1/1.15/1.3); About credit
  «کد نویسی شده توسط Yaser D.z».

### 8.11 Misc
- FAB long-press to enter hidden is now **2s**; `AppDialogTheme` symmetric insets.

### 8.12 Session 2 build history (branch `claude/sleepy-carson-jtkc15`, all green)
1. `fa2f773` — PIN keypad reshaped + auto-unlock + tap title → contact.
2. `5601c4f` — unsaved number → dialer page; SIM tag inside bubble (blue).
3. `9ca28d5` — text-size + whole-UI (DPI) settings; bubble time Latin.
4. `046127b` — full-row long-press; share-text; hidden per-SIM memory +
   auto-lock on background; Latin digits.
5. `a4779d7` — center dialogs in RTL; author credit.
6. `1833c7e` — fixed-width centered menu; message multi-select; fingerprint
   unlock; purge hidden traces.
7. `18c8e06` — FAB 2s; multipart SMS; failed→sender-side; hidden delivery
   reports; smaller PIN keypad.

### 8.13 Outstanding / to-verify (Session 2)
- Delivery tick depends on carrier; large UI scale may crowd some screens;
  MMS/image still not built.

---

## 9) Session 3 — continued work (APPEND-ONLY; everything in §0–§8 is unchanged)

> Third working session (Claude Code on the web). Where a value here differs from
> above, THIS section is the newest truth.

### 9.0 Repo & branch changes (IMPORTANT)
- The repository was **renamed `Yaserna/Claude-test` → `Yaserna/Yaser-D.z`** (now
  **private**) and the app source was restored on a fresh random branch
  (`claude/hopeful-shannon-np00jt`). All **77 source files** were intact.
- The user wanted **clean, recognizable branch names**, so the work was
  consolidated onto a clean branch named **`Mi-Message`** (it already existed at
  the restore point). Procedure used: `git checkout Mi-Message` →
  `git merge --ff-only <random>` → edit workflow → push.
- **Build workflow now also triggers on `Mi-Message`** (added to the `push:
  branches` list alongside `claude/**` and `main`). Auto-build works on it.
- **New install URL** (same `latest` Release, new repo name):
  ```
  https://github.com/Yaserna/Yaser-D.z/releases/download/latest/app-debug.apk
  ```
- **Branch deletion limitation:** the random `claude/...` branch was deleted
  **locally**, but the environment's git proxy **refuses remote branch deletion**
  (`push --delete` / `push :branch` → "remote end hung up"), and the GitHub MCP
  has no delete-branch tool. → The user deletes such branches manually from the
  GitHub branches web page. (Other stray empty branches existed too: `Miner`,
  `Wallet-Script`, `main` — all at the same empty commit.)

### 9.1 Feature: unread state in the hidden section
- **`hidden.db` → v4**: added a `read` column (`onUpgrade` adds it with default 1
  so existing messages count as read). `insert()` sets `read = 0` for incoming
  (type=1), `1` otherwise. New helpers: `markRead(address)`, `hasUnread(address)`
  (true if any incoming message with read=0).
- **HiddenConversationActivity**: `onResume` calls `markRead(address)` (opening a
  hidden chat clears its unread state).
- **HiddenActivity.refresh()**: each row's `Conversation.unread =
  hiddenDb.hasUnread(address)` → the existing orange dot + bold name now appear
  for unread hidden conversations.

### 9.2 Feature: per-hidden-number decoy notification
- **SecureStore**: per-number keys `decoy_name_<norm>`, `decoy_text_<norm>`,
  `decoy_target_<norm>`. `decoyNameFor/decoyTextFor/decoyTargetFor(address)` read
  the per-number value or fall back to the global decoy. `setDecoyFor(address,
  name, text, target)`, `hasCustomDecoy(address)`, `clearDecoyFor(address)`
  (called from `removeHiddenNumber` so unhiding cleans up).
- **Notifier.showDecoy(context, secure, address)**: looks up per-number
  name/text/target; uses a **distinct notification id**
  `("decoy_"+normalize(address)).hashCode()` (so different hidden numbers don't
  overwrite each other's decoy); request code uses the same id. Removed the old
  single `DECOY_ID` constant.
- **SmsReceiver**: passes the sender `address` to `showDecoy`.
- **DecoySettingsActivity**: dual-mode. No `address` extra → edits the **global**
  decoy (opened from the hidden toolbar "Decoy notification"). With an `address`
  extra → edits **that number's** decoy and sets the toolbar title via
  `decoy_title_for`. Fields prefill with the effective values (per-number or
  global fallback).
- **HiddenActivity**: long-press a hidden row now opens a menu via `showListMenu`
  → **«اعلان اختصاصی»** (custom decoy → opens DecoySettings with that address) /
  **«نمایش دوباره»** (unhide). New strings `custom_decoy`, `decoy_title_for`.

### 9.3 Bug fix: hidden chat didn't update live
- **SmsReceiver** now broadcasts `Intent(SmsStatusReceiver.ACTION_HIDDEN_REFRESH)
  .setPackage(packageName)` after inserting a hidden message.
- **HiddenConversationActivity.refreshReceiver** (already registered
  RECEIVER_NOT_EXPORTED for that action) reloads the thread, so a new incoming
  hidden message appears **live** without leaving/re-entering. While the chat is
  resumed it also `markRead` + `cancelDecoy`. Added a `resumedNow` flag set in
  `onResume`/cleared in `onPause`.

### 9.4 Bug fix: decoy notification lingered after opening the hidden chat
- **Notifier.cancelDecoy(context, address)** added (cancels the per-number decoy
  notif id). Called from **HiddenConversationActivity.onResume** (opening the
  chat removes its decoy) and from the refresh receiver when a message arrives
  while the chat is open.

### 9.5 Session 3 build history (branch `Mi-Message`, all green)
1. `09316e7` — unread state in hidden section (hidden.db v4 `read`) +
   per-hidden-number decoy notifications.
2. `acaad74` — add `Mi-Message` to the build-workflow triggers (auto-build there).
3. `3843e97` — hidden chat live update (refresh broadcast) + auto-cancel the
   decoy notification when its hidden chat opens.
4. Session-3 memory update (this §9 + CONVERSATION_LOG.md Session 3).

### 9.6 Outstanding / to-verify (Session 3)
- User confirmed §9.1–9.4 working ("اوکه شد").
- The random `claude/hopeful-shannon-np00jt` remote branch may still exist until
  the user deletes it on GitHub (see §9.0).
- Everything from §6 / §8.13 still applies (MMS not built; delivery tick depends
  on carrier; etc.).

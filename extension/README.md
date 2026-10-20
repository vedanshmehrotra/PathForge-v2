# PathForge Chrome companion

A compact Manifest V3 side panel for the existing PathForge backend. Version **0.4.1** reads your current LeetCode solution automatically; the website remains the place for full progress and account details.

## Install or update

1. In Google Chrome, open `chrome://extensions` and enable **Developer mode**.
2. Choose **Load unpacked** and select `D:\PathForge - v2\extension`.
3. If already installed, click **Reload** on the PathForge card, then close and reopen the old panel.
4. Pin PathForge from Chrome's Extensions menu and click its mint P icon.
5. On first use, choose **Open PathForge**, sign in in the same Chrome window/profile, then **Connect account**. Setup disappears after connection.
6. Open a LeetCode problem containing your **Python / Python3** solution. Open PathForge to read and analyze it automatically.

No copying or pasting is needed. The small recheck icon reads an edited solution. Edits hide stale results; PathForge does not submit an analysis on every keystroke. If the active page is not a problem, the compact problem picker can open a LeetCode URL or title slug.

## What you see

- The current problem and its difficulty.
- A LeetCode verdict **only when its submitted code matches the captured code**. Otherwise, correctness is shown as unchecked. Pattern detection never establishes correctness.
- Recognized patterns and the listed pattern evidence for one relevant approach. Proposed expectations remain labeled, and unused alternatives are not displayed as missing requirements.
- Up to three clickable practice bubbles with title, difficulty, and a backend-provided pattern or catalog topic. Hovering reveals the existing recommendation reason.
- A small footer link to the PathForge website for progress and additional details.

A matching failed LeetCode submission uses the existing pattern-focused recommendation mode. Other cases use the existing calendar-practice policy, with its related follow-up displayed first. This is client orchestration of the existing API; the extension contains no recommendation algorithm. Catalog topics are labeled as topics when the API does not supply a target pattern.

Animations are subtle and respect the browser's reduced-motion preference. The connected view uses flat sections and compact recommendation bubbles.

## Code capture and correctness

The extension reads the **complete Monaco model**, including offscreen lines. It first uses Monaco's editor API, then an editor ref held by its React component when the global API is unavailable. It never treats the visible `.view-lines` DOM as a complete solution.

For a specifically opened `/submissions/<id>/` URL, the LeetCode submission API can supply its submitted code when the editor cannot be read. On a normal problem page, an old submission is never silently substituted for an unreadable current editor.

Submission details are read through same-origin LeetCode requests. The extension checks problem slug, Python language, and source equality before displaying a verdict. It does not run or submit code on LeetCode, copy LeetCode cookies/tokens, or send them to PathForge. Private or unavailable submissions leave correctness unchecked.

[LeetSync's submission handler](https://github.com/LeetSync/LeetSync/blob/main/src/handlers/LeetCodeHandler.ts) and [submission requests](https://github.com/LeetSync/LeetSync/blob/main/src/api/submissions/getSubmission.ts) informed the submission integration. PathForge additionally needs the current editor contents because an unsubmitted draft can differ from the latest accepted submission.

LeetCode's page internals can change. If neither a complete editor nor an explicitly opened submission is available, the panel asks you to open the editor and recheck. It does not analyze partial visible code.

## Account, automatic requests, and storage

Opening the connected panel can prepare a problem and save an analysis to the existing PathForge account. First-time preparation can use the existing external problem/LLM provider. Existing ground truth is reused by the backend. An unavailable comparison requires an explicit **Inspect code without problem comparison** choice before code-only analysis is sent.

The one-time connection preference is saved locally. Access tokens and compact result caches use `chrome.storage.session`; refresh tokens and raw editor drafts are not stored by the extension. After a Chrome restart, PathForge can silently reconnect from an open, signed-in website tab when the connection preference is enabled. If no valid website session is available, reconnecting is necessary. Account controls are behind the small settings icon.

Confirmed results for recent identical code/problem/account fingerprints are reused on recheck/reopen. If a previous analysis request had an uncertain outcome, the extension asks you to inspect your website record before deliberately retrying. Network errors and timeouts never trigger automatic write retries.

## Practice and levels (0.4.1)

Drafts and Run/Test never affect Elo. Accepted and rejected submissions are
checked automatically while the source tab is active, including after starting
with an empty editor. A rejected or unconfirmed submission cannot use the daily
scoring allowance; an accepted correction can qualify later that day. Accepted
code with an unrecognized approach keeps its LeetCode verdict without a skill
penalty. Typing hides stale results without analyzing every keystroke.

Recent practice includes every detected pattern, even when a comparison cannot
award XP. Learning Progress shows your pattern levels, derived from existing Elo.
The sidebar briefly animates a newly confirmed XP change and then hides it.
Reopening a cached result never replays the reward.

Draft scans cannot score. A completed, code-matched LeetCode submission is
recorded once on the server, and the same problem can affect scoring at most
once per UTC day. Rechecking or restarting the browser cannot repeatedly score
that submission. Existing evidence/authority requirements still apply.

Deploy the matching backend and website before installing this version.
An older backend pauses automatic practice updates until it supports the new
recording safeguards. See [practice recording](../docs/architecture/PRACTICE_RECORDING.md).

## Browser support

Chrome **116+** is the supported target. This Chrome manifest is not a Zen/Firefox package. Other browser variants have not been verified.

## Packaging, development, and checks

The extension has no runtime dependencies and needs no build step. Its directory contains only its own assets and documentation. Website/backend files and test tooling are outside the package.

```powershell
.\scripts\package_extension.ps1
```

This creates `dist/pathforge-extension-chrome.zip`; extract it before using **Load unpacked**.

For a local app, change `API_BASE` and `WEBSITE_BASE` in `panel.js` to the existing local API/website origins (`http://localhost:8000` and `http://localhost:3000`). Those origins already have manifest host permissions. Reload the extension after changes.

With an existing Playwright CLI/Chromium installation, run the isolated browser checks:

```powershell
.\scripts\verify_extension.ps1
```

Pass `-BrowserExecutable` if the CLI needs your installed Playwright Chromium path. Test dependencies are for development only and are never packaged. See [VERIFICATION.md](VERIFICATION.md) for current evidence and live-site limits.

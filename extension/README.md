# PathForge Chrome companion

## Companion 0.5 release candidate

Current-problem recommendations, plain-language pattern explanations, a focused connection page and brief server-confirmed XP bars are implemented in this checkout. The website remains a separate interface on the same backend. See [release notes and verification](../docs/releases/companion-0.5.0.md).

Deploy the matching API and website before distributing 0.5.0. The extension's sign-in action opens `/companion/connect`; sign in there, return to the sidebar, then choose **Connect account**. The public Firefox version changes only after Mozilla approval. Runtime dependencies and permissions are unchanged.

---

A compact Manifest V3 side panel for the existing PathForge backend. Version **0.5.0** reads your current LeetCode solution automatically; the website remains the place for full progress and account details.

## Install or update

1. In Google Chrome, open `chrome://extensions` and enable **Developer mode**.
2. Choose **Load unpacked** and select `D:\PathForge - v2\extension`.
3. If already installed, click **Reload** on the PathForge card, then close and reopen the old panel.
4. Pin PathForge from Chrome's Extensions menu and click its PF icon.
5. On first use, choose **Sign in on PathForge**, sign in in the same Chrome window/profile, then **Connect account**. Setup disappears after connection.
6. Open a LeetCode problem containing your **Python / Python3** solution. Open PathForge to read and analyze it automatically.

No copying or pasting is needed. The small recheck icon reads an edited solution. Edits hide stale results; PathForge does not submit an analysis on every keystroke. If the active page is not a problem, the compact problem picker can open a LeetCode URL or title slug.

## What you see

- The current problem and its difficulty.
- A LeetCode verdict **only when its submitted code matches the captured code**. Otherwise, correctness is shown as unchecked. Pattern detection never establishes correctness.
- Recognized patterns and the listed pattern evidence for one relevant approach. Proposed expectations remain labeled, and unused alternatives are not displayed as missing requirements.
- Up to three clickable practice bubbles with title, difficulty, and a backend-provided pattern or catalog topic. Hovering reveals the existing recommendation reason.
- A small footer link to the PathForge website for progress and additional details.

Recommendations use the current problem as context through the existing calendar-practice service. Related follow-ups appear first; after a failed submission, unrelated exploration is withheld. This is client orchestration of the existing API; the extension contains no recommendation algorithm. Catalog topics are labeled as topics when the API does not supply a target pattern.

Animations are subtle and respect the browser's reduced-motion preference. The connected view uses flat sections and compact recommendation bubbles.

## Code capture and correctness

The extension reads the **complete Monaco model**, including offscreen lines. It first uses Monaco's editor API, then an editor ref held by its React component when the global API is unavailable. It never treats the visible `.view-lines` DOM as a complete solution.

LeetCode submission details are used only to verify whether a completed submission matches the editor's problem, language and complete code. Submission details never replace an inaccessible editor.

Submission details are read through same-origin LeetCode requests. The extension checks problem slug, Python language, and source equality before displaying a verdict. It does not run or submit code on LeetCode, copy LeetCode cookies/tokens, or send them to PathForge. Private or unavailable submissions leave correctness unchecked.

[LeetSync's submission handler](https://github.com/LeetSync/LeetSync/blob/main/src/handlers/LeetCodeHandler.ts) and [submission requests](https://github.com/LeetSync/LeetSync/blob/main/src/api/submissions/getSubmission.ts) informed the submission integration. PathForge additionally needs the current editor contents because an unsubmitted draft can differ from the latest accepted submission.

Only the visible, editable Code editor supplies source. Read-only submission previews, hidden editors, partial visible lines and unbound editor models are never analyzed. Browsing an old submission pauses the panel until you return to the editable Code tab. A submission URL remains supported when the actual editable editor is visible, including after a new Submit.

## Account, automatic requests, and storage

Opening the connected panel can prepare a problem and save an analysis to the existing PathForge account. First-time preparation can use the existing external problem/LLM provider. Existing ground truth is reused by the backend. An unavailable comparison requires an explicit **Inspect code without problem comparison** choice before code-only analysis is sent.

The connection and dismissed pattern-hint preferences are saved locally. Access tokens and compact result caches use `chrome.storage.session`; refresh tokens and raw editor drafts are not stored by the extension. After a Chrome restart, PathForge can silently reconnect from an open, signed-in website tab when the connection preference is enabled. If no valid website session is available, reconnecting is necessary. Account controls are behind the small settings icon.

Confirmed results for recent identical code/problem/account fingerprints are reused on recheck/reopen. If a previous analysis request had an uncertain outcome, the extension asks you to inspect your website record before deliberately retrying. Network errors and timeouts never trigger automatic write retries.

## Practice and levels (0.5.0)

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
recording safeguards. If only recommendations are incompatible, analysis remains
available and the panel explains that suggestions need a service update. See [practice recording](../docs/architecture/PRACTICE_RECORDING.md).

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

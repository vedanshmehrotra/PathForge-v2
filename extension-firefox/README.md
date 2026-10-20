# PathForge for Firefox / Zen

Separate Firefox Manifest V3 client for the existing PathForge APIs. The Chrome version stays in `extension/`; this folder is its Firefox sibling. There are no runtime dependencies, remote scripts, bundled website files, or backend/recommendation implementations.

## Try it before publishing

Use desktop Firefox 142+ or a Zen version based on Firefox 142+. Zen-specific sidebar presentation still requires a manual check.

1. Open `about:debugging` in Firefox or Zen.
2. Select **This Firefox** > **Load Temporary Add-on**.
3. Select `D:\PathForge - v2\extension-firefox\manifest.json`.
4. Allow access to the listed PathForge and LeetCode sites. If access was revoked, restore it in the extension's permissions settings.
5. Pin PathForge to the toolbar and click its icon to toggle the sidebar. It is also available in the browser's sidebar selector.
6. Choose **Open PathForge**, sign in in the same browser window/profile, then **Connect account**.
7. Open a LeetCode problem with your Python/Python3 solution and open PathForge. It reads the complete editor model and analyzes it through the existing backend.

Temporary installations disappear when the browser restarts. Use **Reload** in `about:debugging` after changing these files.

The recheck icon reads edited code. Correctness is unchecked unless a LeetCode submission matches the problem, language and exact captured solution. Pattern detection alone does not establish correctness. Up to three recommendation bubbles use the existing backend; full progress stays on the PathForge website.

## Practice and levels (0.4.1)

Drafts and Run/Test never affect Elo. Accepted and rejected submissions are
checked automatically while the source tab is active, including after starting
with an empty editor. A rejected or unconfirmed submission cannot use the daily
scoring allowance; an accepted correction can qualify later that day. Accepted
code with an unrecognized approach keeps its LeetCode verdict without a skill
penalty. Typing hides stale results without analyzing every keystroke.

Learning Progress includes every detected pattern in saved practice, even when
the comparison cannot award XP. Levels display existing Elo; a newly confirmed
rating change briefly fills a compact sidebar bar. Cached results never repeat
the reward. Draft scans cannot score, each completed code-matched LeetCode
submission is recorded once, and a problem can affect scoring at most once per
UTC day. Existing authority rules still apply.

Deploy the matching API and website before installing version 0.4.1. An older
API pauses automatic analysis until it supports the recording safeguards.
See [practice recording](../docs/architecture/PRACTICE_RECORDING.md) for details.

## Make the upload ZIP

From the repository root:

```powershell
.\scripts\package_extension_firefox.ps1
```

Upload **`D:\PathForge - v2\dist\pathforge-extension-firefox.zip`** to the Mozilla Add-on Developer Hub. The manifest is at the ZIP root. Do not upload the Chrome ZIP or the entire repository.

Choose **On this site** for a public listing or **On your own** for private distribution. Review Mozilla's validation results and complete its listing, privacy and data disclosure fields. The packaged `PRIVACY.md` describes extension data handling; a public privacy policy must also accurately describe the existing backend/provider handling. This ZIP is unsigned. Normal installation requires the signed `.xpi` from Mozilla or the published listing. Do not disable signature checks in your everyday browser.

Keep the manifest's Gecko ID stable after the first submission. No compilation is needed: these files are the readable source, and the packaging script only archives them.

## Architecture and maintenance

Reuses `/auth/session`, `/prepare-problem`, `/analyze` and `/recommend` on the same backend as Chrome and the website. The only browser adapters are the Firefox manifest, `background.js` toolbar handler, and native `browser.*` calls in `panel.js`. Firefox supports `MAIN` script injection for the same complete Monaco/React editor reader. LeetCode cookies and tokens are never extracted or forwarded to PathForge.

Session access tokens and compact result caches use `browser.storage.session`, not persistent local storage. Only the connection preference is stored locally. No refresh tokens or raw editor drafts are stored. Opening the connected sidebar can prepare a problem and save analysis to your account. An uncertain analysis write is never automatically repeated.

The panel and editor reader were copied from Chrome to give this folder independent installable assets as requested. Future shared UI/reader changes need to be applied to both extension folders. This duplicates only the small extension client; it does not duplicate website or backend code.

See `VERIFICATION.md` for checks actually performed and remaining limits.

For the native browser checks, package first, then run `node scripts/verify_extension_firefox.js` with development-only Selenium WebDriver and Firefox available. The runner accepts a Selenium module path and browser executable when they are outside normal discovery. It creates a fresh profile, uses controlled fixtures, and closes the browser afterward; it does not use your signed-in profile.

References: [Firefox temporary installation](https://extensionworkshop.com/documentation/develop/temporary-installation-in-firefox/), [submitting an add-on](https://extensionworkshop.com/documentation/publish/submitting-an-add-on/), [Firefox data consent](https://extensionworkshop.com/documentation/develop/firefox-builtin-data-consent/).

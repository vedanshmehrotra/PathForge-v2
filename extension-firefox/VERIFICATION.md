# Firefox extension verification

**0.5 update, 25 October 2026:** 20 isolated Firefox browser checks passed with controlled service/editor responses. Includes editable-editor-only capture, pausing on read-only historical submissions and resuming with current editor code. Chrome additionally checks XP transitions, smooth collapse, no duplicate reward, first-use guidance and incompatible recommendation APIs. See [current release verification](../docs/releases/companion-0.5.0.md). The report below is historical evidence; submission-preview fallback is removed in 0.5.0.

The packaged 0.5.0 add-on passed 20 checks in a fresh Firefox profile: native sidebar opening, permissions, account scanning, session storage, full editable-editor capture, pausing on read-only historical submissions, resuming with current editor code, verdict matching, related/filtered suggestions, cached analysis, compact layout and disconnect cleanup. Website, editor and API responses were controlled fixtures; this was not production OAuth or real LeetCode. See [the release verification](../docs/releases/companion-0.5.0.md). Earlier results below remain historical.

---

## Historical verification — 20 October 2026

## Current version 0.4.1

The practice-recording, level-feedback and submission-reader changes match the
Chrome client, with native `browser.*` adapters preserved. JavaScript syntax,
reader/style parity and package contents were checked. The new shared flow was
exercised in Chromium with controlled fixtures. Native Firefox/Zen execution was
not repeated for this version; Firefox and Selenium are unavailable in the
current environment. The older native results below are historical evidence.

## Historical version 0.3.0

Version **0.3.0**, desktop Firefox **142+** manifest. No original Chrome extension files, website/backend sources, deployment configuration or recommendation/scoring algorithms were changed. Original Chrome file SHA-256 hashes were compared before and after this work and are identical.

## Executed checks

- Mozilla `web-ext lint`: **zero errors, zero warnings, zero notices**.
- JavaScript syntax checks for `panel.js`, `leetcode.js`, `background.js` and the test runner.
- Upload ZIP contents: manifest at archive root, only extension-specific assets/documentation; no website, backend, test tooling or runtime dependencies.
- **17 native Firefox WebDriver checks passed** on Firefox 157.0 in a fresh profile with the actual packaged ZIP installed temporarily.

The browser checks cover installation, site permissions, setup initialization, native sidebar open/close from user gestures, website-session discovery, verified-account connection, complete offscreen Monaco source capture through Firefox MAIN-world scripting, matching Accepted and Wrong Answer verdicts, rejection of a stale Accepted source, concise patterns, three clickable recommendations and related follow-up ordering, the existing pattern-focused recommendation mode after failure, session-only tokens, confirmed-result cache reuse, horizontal overflow at the tested window size, and disconnect cleanup. The connected screenshot was visually inspected.

LeetCode and website pages, GraphQL submission replies and PathForge responses were **controlled fixtures**. The test intercepts those origins before navigation; no production analysis, paid preparation, account login or data write is performed. Native Firefox tabs, host access, script injection, storage and sidebar APIs are used. The panel workflow runs in an extension tab while the native sidebar API is checked separately; a physical click on the browser toolbar icon is not automated.

Run after packaging, with development-only `selenium-webdriver` and Firefox/geckodriver available:

```powershell
.\scripts\package_extension_firefox.ps1
node .\scripts\verify_extension_firefox.js
```

The runner also accepts the Selenium module path and Firefox executable as arguments. Reports/screenshots go to `.playwright-cli/extension-firefox-review/`. Selenium may download geckodriver to its test-tool cache. None of these dependencies are packaged. Extension-page automation access is enabled only inside the disposable test process/profile; normal browser settings are untouched.

## Remaining checks

- Real signed-in LeetCode editor/GraphQL compatibility and a production-authenticated PathForge analysis remain unverified in this review. Existing code is Python/Python3-only.
- Zen uses the Firefox manifest, but its native sidebar presentation still needs a manual check. An isolated WebDriver launch of the installed Zen 1.22.1b exited before a session could be established; no Zen workflow pass is claimed.
- This ZIP is unsigned. Mozilla's live upload validation, signing/review, public listing, and signed-install prompts are separate from local lint and temporary-install checks.
- Review the application's backend/provider privacy and retention policy before publication. `PRIVACY.md` describes the extension's data handling and is not a substitute for the backend policy.

Earlier Playwright attempts installed the extension but could not automate its `moz-extension:` page. Standard Firefox WebDriver with Mozilla's documented test-only system-access setting completed the checks above. No extension workaround or permission weakening was introduced for those failed harness attempts.

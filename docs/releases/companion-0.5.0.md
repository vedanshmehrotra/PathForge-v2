# PathForge Companion 0.5.0

Release notes, packaging and verification for 0.5.0. Website/API deployment and Mozilla publication are separate: the public listing remains on its separately approved version until the new Firefox package is submitted and approved. Search Console changes and user outreach are outside this release.

## What changed

- The current LeetCode problem anchors sidebar recommendations. Related suggestions share a catalog topic and stay at the current difficulty or below. After a failed submission, unrelated exploration is withheld. General suggestions are labelled as exploration.
- Tappable patterns explain the supported structures in plain language, with a first-use hint. XP rules are available before submitting. Larger explanatory text stays readable in a narrow panel. Unsupported accepted approaches clearly describe an analysis limit; an optional example never replaces the LeetCode verdict.
- A fresh, eligible score update animates a small XP bar, shows the amount and level, and fades out while its space collapses smoothly. The final XP amount remains readable. Cached or replayed results never repeat the reward.
- Saved practice explains why XP is unchanged: draft, failed submission, daily allowance, missing comparison, or insufficiently reviewed evidence.
- A focused website connection page preserves the normal Google sign-in flow and returns extension users to connection instructions.
- Learning Progress surfaces recent practice; the existing chart and advanced metrics remain available.
- A public `/companion` page includes installation, a sample-data tour, requirements, privacy/support links and factual FAQs. Canonical/social metadata, a generated social image, robots and a public-page sitemap are included.
- Only the visible, editable Code editor supplies code. Browsing an old read-only submission pauses analysis without fetching its solution. Hidden editors and unbound models are excluded; a real editable editor remains supported on submission URLs after Submit.
- An incompatible recommendation API keeps the analysis visible and explains that the service needs an update, without offering a futile retry. Temporary connection errors still offer retry.
- Both clients use the existing website PF mark. No runtime dependencies or new permissions were added.

The detector, matcher, rating calculation, scoring/authority gates, database schema and existing website recommendation modes are unchanged. No ground-truth records were created, relabelled or promoted to award XP.

## Release order

1. Deploy the backend and website changes together. The backend adds optional `mode: companion` to `/recommend`; existing modes remain compatible. Confirm `/openapi.json` lists `companion` among the `/recommend` request modes before distributing either extension ZIP. Check `/companion`, `/companion/connect`, `/robots.txt`, `/sitemap.xml` and the social image on the actual deployment.
2. Use a test account to verify the deployed connection and completed-submission flow. A recognized approach can still be unscored; do not promise XP for an unreviewed problem.
3. Package with `scripts/package_extension_firefox.ps1` and `scripts/package_extension.ps1`.
4. Upload `dist/pathforge-extension-firefox.zip` to Mozilla as version **0.5.0**. It is unsigned until Mozilla signs it. Chrome users extract `dist/pathforge-extension-chrome.zip` and load its directory through `chrome://extensions`.
5. Update the listing text and images to match the approved version. Keep Experimental status accurate; do not remove it merely for visibility.

Do not publish the new extension before its backend and connection page are deployed. An older backend rejects the new recommendation mode; analysis remains independent but suggestions will show a retry state.

## Mozilla release notes

Understand your Python approach with short explanations for detected patterns. Practice suggestions now use your current LeetCode problem, distinguish related topics from general exploration, and avoid unrelated difficulty jumps after a wrong answer.

Eligible pattern XP updates have a brief animated progress bar and level feedback. Clearer messages explain saved practice without XP, including drafts, failed submissions and repeated checks. Failed submissions do not cost XP; correcting and submitting again can still qualify that day.

Account connection is simpler, with a focused sign-in page and a clearer return to LeetCode. The sidebar keeps detailed progress on the PathForge website.

## Notes to reviewer

This is a lightweight Firefox MV3 sidebar client of the existing PathForge backend. Executable source is plain readable JavaScript, HTML and CSS. There is no bundling, minification, code generation or remotely loaded executable code in the extension. The PowerShell packaging script only archives explicitly listed extension files. The separately hosted Next.js website is not part of the ZIP.

Use desktop Firefox 142+. Open PathForge from the sidebar, complete Google sign-in in the same browser, return and choose Connect account. Open a LeetCode Python/Python3 solution in the visible, editable Code tab. Browsing historical read-only submission previews pauses capture. Only a completed LeetCode submission matching its slug, language and full code supplies a correctness verdict. The extension does not submit code to LeetCode.

Connected analysis sends the current solution and problem identifier to PathForge and uses a session-only PathForge access token. No refresh token or LeetCode authentication material is forwarded. Required permissions and data-collection categories are unchanged. The current problem slug and submission state also provide recommendation context; they do not grant skill authority.

The store images show the actual extension with labelled illustrative sample data. They are not testimonials, user statistics or claims of measured learning gains. Supply a dedicated reviewer test account through Mozilla's private reviewer channel if requested; never put its credentials in this repository.

## Listing material

**Name:** PathForge Companion — LeetCode Python Practice

**Summary:** Understand patterns in your LeetCode Python code, save your practice, and find related problems from a compact Firefox sidebar.

**Description:**

PathForge Companion helps you understand the patterns in your own LeetCode Python solutions and choose a useful next practice problem, without copying code out of the editor.

- Automatically identifies the current problem and reads its complete Python/Python3 solution.
- Explains supported patterns in plain language.
- Displays a correctness verdict only when a completed LeetCode submission matches your code.
- Suggests related practice from the PathForge catalog, with general exploration clearly labelled.
- Saves practice to your existing PathForge account.
- Briefly animates eligible pattern XP and level changes, and explains when practice is saved without XP.

Requires desktop Firefox 142+, internet access, a PathForge account and Python/Python3. Install, sign in on PathForge in the same browser, then connect the sidebar.

When connected, opening the sidebar, changing problems or rechecking can send your code and problem to PathForge for analysis and progress tracking. Drafts and Run/Test do not change XP. Failed submissions do not cost XP. XP requires an eligible, verified comparison and can change at most once per problem per UTC day. Pattern observations and levels do not certify correctness or mastery.

An independent companion, not affiliated with LeetCode.

**Homepage and support website after deployment:** https://path-forge-v2.vercel.app/companion

**Support email:** mehrotravedansh2006@gmail.com

**Category:** Web Development. Keep unrelated tags unselected.

**Screenshot files and captions:**

1. `pathforge-frontend/public/companion/patterns.png` — Understand patterns in your own Python code. Actual interface with illustrative sample data.
2. `pathforge-frontend/public/companion/level-up.png` — A fresh, eligible XP update fills the pattern bar and shows the new level. Illustrative sample data.
3. `pathforge-frontend/public/companion/retry.png` — A failed submission keeps XP unchanged and offers related practice when available. Illustrative sample data.

## Verification

Executed on 24–25 October 2026 (local time):

- 135 backend tests passed for calendar/context recommendations, authenticated ownership, practice tracking, scoring safeguards and comparison policy. Database and external network access were blocked; loopback was allowed for the in-process HTTP test client.
- 159 frontend tests passed, including server HTML, connection copy, private-route protection and allowlisted OAuth return routing. TypeScript passed.
- 86 checks passed with the actual Chrome MV3 extension loaded in an isolated Chromium profile. Editor/submission, account and API responses were controlled fixtures. Includes XP transitions and smooth collapse with a lasting receipt, cached/server replay suppression, related/empty recommendation states, incompatible recommendation API guidance, first-use hints, stale code and widths 280–440px. Read-only/hidden editors, unbound models and historical submissions cannot provide code; a focused preview beside an editable editor cannot replace the solution.
- 20 checks passed with the actual packaged add-on in a fresh Firefox profile, including native sidebar opening, session storage, full editor capture, verdict matching, context recommendations, pausing on historical read-only previews and resuming from current editor code on submission URLs. Service/editor responses were controlled fixtures.
- 16 local Next.js browser/HTTP checks passed for public server HTML, install links, tour, connection flow, private-route gate, mobile layout, robots, sitemap, social image and signed-in progress interaction. Signed-in views used controlled account/API fixtures.

The production build was checked with Next.js's supported Webpack compiler. The local Turbopack preview failed in its Windows worker process before compiling application CSS; project build/deployment configuration was not changed.

This does not establish production OAuth, real LeetCode compatibility for this new release, production recommendation catalog coverage, or learning improvement. The preceding live 0.4.1 walkthrough is separate evidence. Deploy and verify with the test account before calling 0.5.0 live-tested.

## First learner pilot

Recruit 10–15 Python learners who already attempt Easy problems; watch the first five without explaining the interface. Record where they stall and ask them to explain one detected pattern and the reason for their next problem.

Count separately: installs, first completed code-matched submission analyzed, distinct submissions, second-day return and seven-day return. Exclude developer/test accounts and repeated scans. A recommendation click is not a completed attempt; XP growth is not measured learning. For possible learning benefit, observe an unseen related problem and report the sample size and assistance used.

No new tracking or solution telemetry was added. Use consented manual pilot records initially. Any later analytics needs deliberate event definitions and an accurate privacy disclosure.

Search Console verification, sitemap submission, AMO edits and outreach require the corresponding account actions after deployment. No ranking, inclusion or adoption is guaranteed.

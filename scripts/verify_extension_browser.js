// Real MV3 extension/browser APIs; controlled LeetCode editor, submission, and PathForge API fixtures.
async page => {
  const context = page.context();
  const worker = context.serviceWorkers().find(item => item.url().endsWith('/service-worker.js'));
  if (!worker) throw new Error('Extension did not load.');
  const origin = worker.url().replace('/service-worker.js', '');
  const site = 'https://path-forge-v2.vercel.app';
  const apiBase = 'https://pathforge-v2.onrender.com';
  const code = '\nclass Solution:\n    def twoSum(self, nums, target):\n        seen = {}\n' + Array.from({ length: 100 }, (_, i) => `        # offscreen line ${i}`).join('\n') + '\n        return [0, 1]\n';
  const passed = [], calls = [], graphql = [], errors = [];
  const mode = { auth: 200, prepare: 200, analyze: 200, recommend: 200, status: 10, submittedCode: code, submittedSlug: null, gate: null, unsafe: false, unsafeTitle: true, noRelated: false, emptySuggestions: false, submissionId: '701', scored: false, replayed: false, scoreReason: 'expectations_not_authorizing', policyVersion: 2, patternDetected: true, editorCode: null, previewOnly: false };
  const assert = (value, text) => { if (!value) throw new Error(text); passed.push(text); };
  const wait = async (predicate, text = 'Expected state did not appear') => {
    for (let i = 0; i < 600; i++) { if (await predicate()) return; await new Promise(resolve => setTimeout(resolve, 30)); }
    throw new Error(text);
  };
  const json = (route, status, data) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(data) }).catch(() => {});
  const groups = [
    { id: 'hash', name: 'Hash lookup', patterns: ['hash_map_lookup'], review_state: 'UNREVIEWED', pattern_evidence_state: 'ALL_OBSERVED', observed_patterns: ['hash_map_lookup'], unobserved_patterns: [], family_relation: 'ONE_OF' },
    { id: 'pointers', name: 'Two pointers', patterns: ['two_pointers_same'], review_state: 'REVIEWED', pattern_evidence_state: 'NONE_OBSERVED', observed_patterns: [], unobserved_patterns: ['two_pointers_same'], family_relation: 'ONE_OF' },
  ];
  const apiHandler = async route => {
    const request = route.request(), path = new URL(request.url()).pathname, body = request.postDataJSON();
    calls.push({ path, body, authorization: request.headers().authorization });
    if (mode.gate?.path === path) { const gate = mode.gate; gate.entered = true; await gate.promise; }
    if (path === '/auth/session') return json(route, mode.auth, mode.auth === 200 ? { authenticated: true, practice_policy_version: mode.policyVersion, user_id: 41, email: 'extension-test@example.invalid' } : { detail: 'Session expired' });
    if (path === '/prepare-problem') return json(route, mode.prepare, mode.prepare === 200 ? { leetcode_id: 1, title: 'Two Sum', difficulty: 'Easy' } : { detail: { code: 'COMPARISON_UNSUPPORTED', message: 'Comparison unavailable.' } });
    const event = body?.practice_event || {};
    const scored = mode.scored && event.submission_status === 'accepted';
    const reason = !event.submission_id ? 'awaiting_submission' : event.submission_status === 'failed' ? 'submission_not_accepted' : mode.scoreReason;
    if (path === '/analyze') return json(route, mode.analyze, mode.analyze === 200 ? {
      ast: { detected_patterns: mode.patternDetected ? [{ pattern_id: 'hash_map_lookup', confidence: .95 }, { pattern_id: 'array_traversal', confidence: .9 }] : [] },
      problem_info: body.problem ? { title: 'Two Sum', difficulty: 'Easy', solution_groups: groups } : null,
      match_result: { match_result: 'FULL_MATCH' }, persisted: { submission_id: 321, skill_updates_skipped: !scored, replayed: mode.replayed, score_reason: scored ? 'scored' : reason },
      elo_updates: scored ? [{ pattern_id: 'hash_map_lookup', elo_before: 1192, elo_after: 1208, delta: 16,
        level_before: { level: 4, experience: 792, into_level: 192, points_per_level: 200, progress_percent: 96 },
        level_after: { level: 5, experience: 808, into_level: 8, points_per_level: 200, progress_percent: 4 } }] : [],
    } : { detail: 'Server response interrupted.' });
    if (path === '/recommend') return json(route, mode.recommend, mode.recommend === 200 ? { recommendations: mode.emptySuggestions ? [] : [
      { problem_id: '980', title: 'Unique Paths III', difficulty: 'Hard', practice_kind: 'follow_up', reason_evidence: { anchor_url: 'https://leetcode.com/problems/two-sum/', shared_topics: ['Hash Table'] }, problem_url: 'https://leetcode.com/problems/unique-paths-iii/' },
      { problem_id: '217', title: 'Contains Duplicate', difficulty: 'Easy', pattern: body.mode === 'legacy' ? 'hash_map_lookup' : '', topics: ['Hash Table'], practice_kind: 'explore', problem_url: mode.unsafe ? 'javascript:alert(1)' : 'https://leetcode.com/problems/contains-duplicate/' },
      { problem_id: '242', title: mode.unsafeTitle ? '<script>Valid Anagram</script>' : 'Valid Anagram', difficulty: 'Easy', topics: ['String', 'Hash Table'], practice_kind: mode.noRelated ? 'explore' : 'follow_up', reason_evidence: mode.noRelated ? null : { anchor_url: 'https://leetcode.com/problems/two-sum/', shared_topics: ['Hash Table'] }, problem_url: 'https://leetcode.com/problems/valid-anagram/' },
      { problem_id: '20', title: 'Valid Parentheses', difficulty: 'Easy', pattern: 'stack', practice_kind: 'starter', problem_url: 'https://leetcode.com/problems/valid-parentheses/' },
      { problem_id: '1', title: 'Two Sum', difficulty: 'Easy', pattern: 'hash_map_lookup', problem_url: 'https://leetcode.com/problems/two-sum/' },
    ] } : mode.recommend === 422 ? { detail: [{ type: 'literal_error', loc: ['body', 'mode'], msg: 'Input should be legacy or practice' }] } : { detail: 'Suggestions unavailable.' });
    throw new Error(`Unexpected PathForge endpoint: ${path}`);
  };
  const leetcodeHandler = async route => {
    const request = route.request();
    if (new URL(request.url()).pathname === '/graphql/') {
      const body = request.postDataJSON(); graphql.push({ body, authorization: request.headers().authorization });
      if (body.query.includes('submissionDetails')) return json(route, 200, { data: { submissionDetails: {
        code: mode.submittedCode, statusCode: mode.status, lang: { name: 'Python3' }, question: { titleSlug: mode.submittedSlug || 'two-sum', title: 'Two Sum' },
      } } });
      return json(route, 200, { data: { questionSubmissionList: { submissions: [{ id: mode.submissionId }] } } });
    }
    const html = `<!doctype html><style>.monaco-editor{width:700px;height:500px}.view-lines{height:50px;overflow:hidden}</style><a href="/problems/two-sum/">1. Two Sum</a><div class="monaco-editor"><textarea class="inputarea" ${mode.previewOnly ? 'readonly' : ''}></textarea><div class="view-lines">ONLY VISIBLE LINES, NOT THE SOURCE</div></div><script>
      window.fixtureCode=${JSON.stringify(mode.editorCode || code)}; window.fixtureLanguage='python'; window.fixtureReadOnly=${mode.previewOnly};
      window.fixtureModel={getValue:()=>window.fixtureCode,getLanguageId:()=>window.fixtureLanguage,isDisposed:()=>false};
      window.fixtureEditor={getValue:()=>window.fixtureCode,getModel:()=>window.fixtureModel,getDomNode:()=>document.querySelector('.monaco-editor'),getRawOptions:()=>({readOnly:window.fixtureReadOnly}),hasTextFocus:()=>true};
      window.monaco={editor:{getEditors:()=>[window.fixtureEditor],getModels:()=>[window.fixtureModel]}};
    </script>`;
    return route.fulfill({ contentType: 'text/html', body: html });
  };
  const websiteHandler = route => route.fulfill({ contentType: 'text/html', body: '<!doctype html><title>PathForge sign-in fixture</title><p>Sign in</p>' });
  await context.route(`${apiBase}/**`, apiHandler);
  await context.route('https://leetcode.com/**', leetcodeHandler);
  await context.route(`${site}/**`, websiteHandler);
  await worker.evaluate(async () => { await chrome.storage.session.clear(); await chrome.storage.local.remove(['pathforgeSetup', 'pathforgeSession', 'pathforgePatternHintSeen']); });
  await page.goto('about:blank');
  let panel = await context.newPage();
  const source = await context.newPage();
  await source.goto('https://leetcode.com/problems/two-sum/description/?envType=daily-question');
  await source.bringToFront();
  await panel.goto(`${origin}/panel.html`);
  panel.on('pageerror', error => errors.push(error.message));
  const count = path => calls.filter(item => item.path === path).length;
  const last = path => calls.filter(item => item.path === path).at(-1);
  const done = () => wait(async () => await panel.locator('#analysis-result').isVisible() && !(await panel.locator('#recheck').isDisabled()));
  const recheck = async () => { await panel.locator('#recheck').click(); await done(); };
  const gate = path => { let release; const promise = new Promise(resolve => { release = resolve; }); mode.gate = { path, promise, release, entered: false }; return mode.gate; };
  let website;
  try {
    await panel.locator('#setup').waitFor();
    assert((await panel.locator('#setup').textContent()).includes('Not every accepted solution qualifies'), 'First-use setup explains XP eligibility before the first attempt');
    assert((await worker.evaluate(() => chrome.sidePanel.getPanelBehavior())).openPanelOnActionClick, 'Toolbar opens the registered side panel');
    assert(await panel.locator('textarea').count() === 0, 'The extension contains no manual code editor');
    await panel.locator('#connect-account').click();
    await wait(async () => (await panel.locator('#message').textContent()).includes('Open the PathForge website'));
    assert(true, 'First-use setup explains when the website is not open');
    await panel.locator('#open-app').click();
    await wait(() => context.pages().some(item => item.url().startsWith(site)));
    website = context.pages().find(item => item.url().startsWith(site));
    await website.evaluate(() => localStorage.removeItem('sb-browser-test-auth-token'));
    await panel.locator('#connect-account').click();
    await wait(async () => (await panel.locator('#message').textContent()).includes('No signed-in website session'));
    assert(true, 'Signed-out website sessions cannot connect');
    await website.evaluate(() => localStorage.setItem('sb-browser-test-auth-token', JSON.stringify({ access_token: 'browser-fixture-token', refresh_token: 'MUST_NOT_IMPORT' })));
    await panel.locator('#connect-account').click();
    await done();
    await source.bringToFront(); await done();
    assert(!(await panel.locator('#setup').isVisible()) && !(await panel.locator('#settings').isVisible()), 'Connection setup and account controls disappear after connection');
    assert(last('/analyze').body.code === code && code.includes('offscreen line 99'), 'Automatic capture submits the complete Monaco model including offscreen code');
    assert(last('/prepare-problem').body.problem.title_slug === 'two-sum' && last('/analyze').body.problem.leetcode_id === 1, 'URL subroutes resolve through the existing preparation API');
    assert(last('/analyze').body.user_id === 41 && last('/analyze').body.language === 'python', 'Automatic analysis uses verified identity and supported language');
    assert((await panel.locator('#verdict-label').textContent()) === 'Accepted on LeetCode', 'Accepted is shown only for matching submitted code');
    assert(last('/analyze').body.practice_event.submission_status === 'accepted' && (await panel.locator('#xp-detail').textContent()).includes('has not been verified for XP'), 'Accepted code explains why an unreviewed comparison cannot award XP');
    assert(await panel.locator('#pattern-hint').isVisible(), 'Pattern explanations have a discoverable first-use hint');
    assert((await panel.locator('#pattern-explanation').textContent()).includes('dictionary'), 'A detected pattern has an understandable explanation');
    await panel.getByRole('button', { name: '✓ Array traversal', exact: true }).click();
    assert((await panel.locator('#pattern-explanation').textContent()).includes('visit items'), 'Tapping a different pattern changes its plain-language explanation');
    assert(!(await panel.locator('#pattern-hint').isVisible()) && await worker.evaluate(async () => (await chrome.storage.local.get('pathforgePatternHintSeen')).pathforgePatternHintSeen), 'The pattern hint disappears after use and remembers only a UI preference');
    await panel.getByRole('button', { name: '✓ Hash lookup', exact: true }).click();
    assert((await panel.locator('#comparison').textContent()).includes('Possible approach') && !(await panel.locator('#comparison').textContent()).includes('Two pointers'), 'Main comparison qualifies unreviewed evidence and omits unused alternatives');
    await panel.locator('.xp-guide summary').click();
    assert((await panel.locator('.xp-guide p').textContent()).includes('already being in the catalog does not prevent XP'), 'Optional XP guidance distinguishes catalog availability from reward eligibility');
    await panel.locator('.xp-guide summary').click();
    assert(await panel.locator('#recommendations a').count() === 3 && (await panel.locator('#recommendations a').first().textContent()).includes('Valid Anagram'), 'At most three complete clickable bubbles show related practice first');
    assert(!(await panel.locator('#recommendations').textContent()).includes('Unique Paths III'), 'The client also rejects a harder recommendation even when topic metadata claims a relation');
    assert(await panel.locator('#recommendations script').count() === 0, 'Recommendation text is escaped instead of interpreted as HTML');
    mode.unsafeTitle = false;
    await recheck();
    await panel.locator('#analysis-result').evaluate(async element => { await Promise.all(element.getAnimations({ subtree: true }).map(animation => animation.finished)); });
    await panel.screenshot({ path: '.playwright-cli/extension-review/patterns.png', fullPage: true });
    assert(!calls.some(call => ['/elo', '/auth/profile'].includes(call.path)) && (await panel.locator('#progress-link').getAttribute('href')).endsWith('/progress'), 'Progress is a website link without loading the website dashboard into the panel');
    assert(!(await panel.locator('body').innerText()).includes('detector confidence') && !(await panel.locator('body').innerText()).includes('submission 321'), 'The main view excludes developer metrics and raw persistence details');
    const storage = await worker.evaluate(async () => ({ session: await chrome.storage.session.get(), local: await chrome.storage.local.get() }));
    assert(!JSON.stringify(storage).includes('MUST_NOT_IMPORT') && !storage.local.pathforgeSession && storage.local.pathforgeSetup === true, 'Only connection preference persists on disk; refresh tokens are never imported');
    assert(graphql.every(call => !call.authorization) && calls.every(call => call.authorization === 'Bearer browser-fixture-token'), 'LeetCode reads use same-origin sessions while only PathForge requests receive its bearer token');
    const writes = count('/analyze');
    await recheck();
    assert(count('/analyze') === writes, 'Rechecking identical code reuses confirmed analysis without duplicate writes');
    mode.emptySuggestions = true; await recheck();
    assert(await panel.locator('#recommendations a').count() === 0 && (await panel.locator('#recommendation-help').textContent()).includes('No suitable follow-up'), 'An empty accepted slate does not pretend that other topics are shown');
    mode.emptySuggestions = false;

    mode.status = 11;
    await recheck();
    assert((await panel.locator('#verdict-label').textContent()).includes('Wrong answer') && last('/recommend').body.mode === 'companion' && last('/recommend').body.context_problem_slug === 'two-sum' && last('/recommend').body.submission_status === 'failed', 'A failed submission requests related practice for the current problem');
    assert(last('/analyze').body.practice_event.submission_status === 'failed' && (await panel.locator('#saved-note').textContent()).includes('fix and submit again'), 'The extension sends a failed verdict and leaves room for a corrected submission');
    assert(await panel.locator('#recommendations a').count() === 1 && (await panel.locator('#recommendations').textContent()).includes('Same topic: Hash Table'), 'Failure suggestions omit unrelated choices and qualify catalog topics');
    await panel.locator('#analysis-result').evaluate(async element => { await Promise.all(element.getAnimations({ subtree: true }).map(animation => animation.finished)); });
    await panel.screenshot({ path: '.playwright-cli/extension-review/retry.png', fullPage: true });
    mode.noRelated = true; await recheck();
    assert(await panel.locator('#recommendations a').count() === 0 && (await panel.locator('#recommendation-help').textContent()).includes('No related question'), 'Missing relevant practice is explained without inventing a remedial recommendation');
    mode.noRelated = false;
    mode.status = 10; mode.submittedCode = code.replace('return [0, 1]', 'return [1, 2]');
    await recheck();
    assert((await panel.locator('#verdict-label').textContent()) === 'Not checked on LeetCode' && last('/recommend').body.submission_status === 'unknown', 'An old accepted submission is never attached to different editor code');
    mode.submittedCode = code; mode.submittedSlug = 'another-problem';
    await recheck();
    assert((await panel.locator('#verdict-label').textContent()) === 'Not checked on LeetCode', 'A verdict for a different problem is rejected');
    mode.submittedSlug = null;
    mode.unsafe = true;
    await recheck();
    assert(await panel.locator('#recommendations a[href^="javascript:"]').count() === 0 && !(await panel.locator('#recommendations').textContent()).includes('Contains Duplicate'), 'Unsafe recommendation URLs are excluded');
    mode.unsafe = false; mode.recommend = 503;
    await recheck();
    assert(await panel.locator('#analysis-result').isVisible() && await panel.locator('#retry-recommendations').isVisible(), 'Suggestion failure preserves the analysis and offers a compact retry');
    mode.recommend = 200;
    await panel.locator('#retry-recommendations').click(); await done();
    mode.recommend = 422;
    await recheck();
    await wait(async () => (await panel.locator('#recommendations').textContent()).includes('need a PathForge update'));
    assert(await panel.locator('#analysis-result').isVisible() && !(await panel.locator('#retry-recommendations').isVisible()), 'An older recommendation API explains incompatibility without presenting an endless retry');
    mode.recommend = 200;

    await source.evaluate(() => { window.fixtureLanguage = 'cpp'; });
    const beforeUnsupported = count('/analyze');
    await panel.locator('#recheck').click();
    await wait(async () => (await panel.locator('#activity-title').textContent()).includes('Switch to Python'));
    assert(count('/analyze') === beforeUnsupported, 'Unsupported editor languages are explained without submission');
    await source.evaluate(() => { window.fixtureLanguage = 'python'; window.fixtureCode = 'class Solution:\n    def twoSum(self, nums, target):\n        pass'; });
    await panel.locator('#recheck').click();
    await wait(async () => (await panel.locator('#activity-title').textContent()).includes('Write your solution'));
    assert(count('/analyze') === beforeUnsupported, 'An untouched empty solution is not analyzed');
    await source.evaluate(value => { window.fixtureCode = value; }, 'class Solution:\n    def twoSum(self, nums, target):\n        """Your code here"""\n        pass');
    await panel.locator('#recheck').click();
    await wait(async () => !(await panel.locator('#recheck').isDisabled()));
    assert(count('/analyze') === beforeUnsupported, 'A starter docstring is not mistaken for an implemented solution');
    const oneLine = 'class Solution:\n    def twoSum(self, nums, target): return [0, 1]\n';
    await source.evaluate(value => { window.fixtureCode = value; }, oneLine);
    mode.submittedCode = oneLine;
    await recheck();
    assert(last('/analyze').body.code === oneLine, 'A valid single-line Python method is captured instead of being classified as empty');

    const reactCode = code + '# React ref capture\n';
    await source.evaluate(value => {
      window.fixtureCode = value; window.monaco = undefined;
      document.querySelector('.monaco-editor').__reactFiber$pathforge = { memoizedState: { memoizedState: { current: window.fixtureEditor }, next: null }, memoizedProps: {}, return: null };
    }, reactCode);
    mode.submittedCode = reactCode;
    await recheck();
    assert(last('/analyze').body.code === reactCode, 'A React-held Monaco editor is read when the global Monaco API is absent');
    await source.evaluate(() => { delete document.querySelector('.monaco-editor').__reactFiber$pathforge; });
    const beforeMissing = count('/analyze');
    await panel.locator('#recheck').click();
    await wait(async () => (await panel.locator('#activity-title').textContent()).includes('Open the Code tab'));
    assert(count('/analyze') === beforeMissing, 'Visible editor lines are never used as a partial-code fallback');
    await source.evaluate(() => { window.monaco = { editor: { getModels: () => [window.fixtureModel] } }; });
    await panel.locator('#recheck').click();
    await wait(async () => !(await panel.locator('#recheck').isDisabled()));
    assert(count('/analyze') === beforeMissing, 'An unbound global model is not mistaken for the editable solution');
    mode.submittedCode = code + '# explicitly opened submission\n';
    mode.previewOnly = true;
    const beforeHistoryGraphql = graphql.length;
    await source.bringToFront();
    await source.goto('https://leetcode.com/problems/two-sum/submissions/701/');
    await panel.locator('#recheck').click();
    await wait(async () => (await panel.locator('#activity-title').textContent()).includes('Open the Code tab') && !(await panel.locator('#recheck').isDisabled()));
    assert(count('/analyze') === beforeMissing && graphql.length === beforeHistoryGraphql && !(await panel.locator('#analysis-result').isVisible()), 'Opening an old read-only submission pauses capture without fetching its code or writing practice');
    await source.evaluate(() => { window.fixtureReadOnly = false; });
    await panel.locator('#recheck').click();
    await wait(async () => !(await panel.locator('#recheck').isDisabled()));
    assert(count('/analyze') === beforeMissing, 'A read-only input cannot bypass the editor-options guard');
    await source.evaluate(() => { document.querySelector('.inputarea').readOnly = false; });
    await recheck();
    assert((await panel.locator('#verdict-label').textContent()).includes('Not checked') && await panel.evaluate(() => state.snapshot.source === 'editor'), 'A submission URL still supports the real editable Code tab and never replaces its code with the historical submission');
    mode.previewOnly = false;
    await source.goto('https://leetcode.com/problems/two-sum/description/');
    mode.submittedCode = code;
    await recheck();
    await source.evaluate(() => { window.monaco = { editor: { getEditors: () => [window.fixtureEditor], getModels: () => [window.fixtureModel] } }; });
    await recheck();
    const beforeHidden = count('/analyze'), graphqlBeforeHidden = graphql.length;
    await source.evaluate(() => { document.querySelector('.monaco-editor').style.visibility = 'hidden'; });
    await panel.evaluate(async () => { await monitorEditor(); });
    assert(!(await panel.locator('#analysis-result').isVisible()) && (await panel.locator('#watch-status').textContent()).includes('Paused') && count('/analyze') === beforeHidden && graphql.length === graphqlBeforeHidden, 'Hiding the main editor clears stale feedback and pauses without reading a retained model');
    await source.evaluate(() => { document.querySelector('.monaco-editor').style.visibility = ''; });
    await recheck();
    const editableWithPreview = code + '# editable code beside a historical preview\n';
    await source.evaluate(value => {
      window.fixtureCode = value;
      const preview = document.createElement('div'); preview.id = 'historical-preview'; preview.className = 'monaco-editor';
      preview.innerHTML = '<textarea class="inputarea" readonly></textarea>'; document.body.prepend(preview);
      const model = { getValue: () => 'HISTORICAL PREVIEW MUST NEVER BE ANALYZED', getLanguageId: () => 'python' };
      window.fixtureEditor.getDomNode = () => document.querySelector('.monaco-editor:not(#historical-preview)');
      window.monaco.editor.getEditors = () => [{ getValue: () => model.getValue(), getModel: () => model, getDomNode: () => preview, getRawOptions: () => ({ readOnly: true }), hasTextFocus: () => true }, window.fixtureEditor];
    }, editableWithPreview);
    await recheck();
    assert(last('/analyze').body.code === editableWithPreview, 'A focused read-only preview beside an editable editor cannot replace the current solution');
    await source.evaluate(() => { document.getElementById('historical-preview').remove(); window.monaco.editor.getEditors = () => [window.fixtureEditor]; });

    await source.evaluate(() => { window.fixtureCode += '# edited after result\n'; });
    await wait(async () => (await panel.locator('#activity-title').textContent()).includes('Your solution changed'));
    assert(!(await panel.locator('#analysis-result').isVisible()), 'Editing LeetCode code hides stale observations without automatically writing on every keystroke');
    const prepGate = gate('/prepare-problem');
    await panel.locator('#recheck').click(); await wait(() => prepGate.entered);
    const beforeChanged = count('/analyze');
    await source.evaluate(() => { window.fixtureCode += '# changed during preparation\n'; });
    prepGate.release(); mode.gate = null;
    await wait(async () => !(await panel.locator('#recheck').isDisabled()));
    assert(count('/analyze') === beforeChanged, 'Code changes during preparation prevent an outdated automatic write');

    mode.prepare = 409;
    await panel.locator('#recheck').click();
    await panel.locator('#inspect-anyway').waitFor();
    await wait(async () => !(await panel.locator('#recheck').isDisabled()));
    assert(count('/analyze') === beforeChanged, 'Unavailable comparison requires an explicit code-only fallback');
    await panel.locator('#inspect-anyway').click(); await done();
    assert(!last('/analyze').body.problem, 'Explicit fallback reads code automatically and omits problem comparison');
    mode.prepare = 200;

    await source.evaluate(() => { window.fixtureCode += '# uncertain write\n'; });
    mode.analyze = 500;
    await panel.locator('#recheck').click();
    await wait(async () => !(await panel.locator('#recheck').isDisabled()));
    const uncertainCount = count('/analyze');
    mode.analyze = 200;
    await panel.locator('#recheck').click();
    await panel.locator('#retry-analysis').waitFor();
    assert(count('/analyze') === uncertainCount, 'An uncertain write is not automatically repeated on reopening or rechecking');
    await panel.locator('#retry-analysis').click(); await done();
    assert(count('/analyze') === uncertainCount + 1, 'A deliberate retry can recover an uncertain write');

    await source.evaluate(() => { window.fixtureCode += '# pending logout\n'; });
    const writeGate = gate('/analyze');
    await panel.locator('#recheck').click(); await wait(() => writeGate.entered);
    await panel.locator('#settings-toggle').click(); await panel.locator('#disconnect').click();
    writeGate.release(); mode.gate = null;
    await panel.locator('#setup').waitFor();
    assert(!(await panel.locator('#workspace').isVisible()) && (await panel.locator('#detected-patterns').textContent()) === '', 'Disconnect removes private observations and blocks late responses');
    await panel.locator('#connect-account').click(); await done();
    mode.submittedCode = await source.evaluate(() => window.fixtureCode);
    await recheck();
    const beforeReopen = count('/analyze');
    await panel.close(); panel = await context.newPage(); await source.bringToFront(); await panel.goto(`${origin}/panel.html`);
    panel.on('pageerror', error => errors.push(error.message)); await done();
    assert(count('/analyze') === beforeReopen && !(await panel.locator('#setup').isVisible()), 'Reopening goes directly to cached results without connection UI or duplicate writes');
    await worker.evaluate(() => chrome.storage.session.remove('pathforgeSession'));
    await panel.reload(); await done();
    assert(count('/analyze') === beforeReopen && !(await panel.locator('#setup').isVisible()), 'Remembered connection silently reconnects from the website without repeating a confirmed analysis');

    for (const width of [280, 320, 360, 440]) {
      await panel.setViewportSize({ width, height: 760 });
      await panel.locator('#analysis-result').evaluate(async element => { await Promise.all(element.getAnimations({ subtree: true }).map(animation => animation.finished)); });
      await panel.locator('#next-practice').evaluate(async element => { await Promise.all(element.getAnimations({ subtree: true }).map(animation => animation.finished)); });
      assert(await panel.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Compact layout has no horizontal overflow at ${width}px`);
      await panel.screenshot({ path: `.playwright-cli/extension-review/compact-${width}.png`, fullPage: true });
    }
    assert(await panel.locator('main').evaluate(element => element.getBoundingClientRect().height < 800), 'Connected results and three suggestions fit within a compact vertical layout');
    mode.scored = true; mode.submissionId = '710'; groups[0].review_state = 'REVIEWED';
    await recheck();
    assert(last('/analyze').body.practice_event.submission_id === '710' && last('/analyze').body.practice_event.source === 'extension', 'A code-matched completed submission supplies a stable practice identity');
    assert(await panel.locator('#level-feedback').isVisible() && (await panel.locator('#level-feedback').textContent()).includes('+16 XP'), 'A fresh server-confirmed rating update displays earned XP');
    await wait(async () => (await panel.locator('#level-feedback').textContent()).includes('Level 5 reached'));
    assert(await panel.locator('.level-track').getAttribute('aria-valuenow') === '4', 'Level crossing ends at the actual server-provided progress');
    await wait(async () => await panel.locator('.level-fill').evaluate(element => element.style.width === '4%'));
    await panel.locator('.level-fill').evaluate(async element => { await Promise.all(element.getAnimations().map(animation => animation.finished)); });
    await panel.screenshot({ path: '.playwright-cli/extension-review/level-up.png', fullPage: true });
    const rewardHeight = await panel.locator('#level-feedback').evaluate(element => element.getBoundingClientRect().height);
    await wait(async () => await panel.locator('#level-feedback').evaluate(element => element.classList.contains('leaving') && Number(getComputedStyle(element).opacity) < .95));
    assert(true, 'Reward feedback transitions to transparent instead of snapping away');
    assert(await panel.locator('#level-feedback').evaluate((element, height) => element.getBoundingClientRect().height < height && element.getBoundingClientRect().height > 0, rewardHeight), 'Reward space collapses gradually as the bar fades');
    await wait(async () => !(await panel.locator('#level-feedback').isVisible()));
    assert(true, 'Level feedback fades away after its short animation');
    assert((await panel.locator('#xp-detail').textContent()).includes('+16 XP'), 'The readable reward receipt remains after the animated bar disappears');
    const beforeCachedXp = count('/analyze'); await recheck();
    assert(count('/analyze') === beforeCachedXp && !(await panel.locator('#level-feedback').isVisible()), 'Cached observations never replay an XP animation');
    mode.replayed = true;
    await worker.evaluate(() => chrome.storage.session.remove('pathforgeChecks'));
    await panel.reload(); await done();
    assert(!(await panel.locator('#level-feedback').isVisible()) && (await panel.locator('#saved-note').textContent()).includes('Already saved'), 'Server duplicate receipts suppress XP even after the client cache is cleared');
    mode.scored = false; mode.replayed = false; mode.scoreReason = 'problem_already_scored_today'; mode.submissionId = '711';
    await recheck();
    assert(!(await panel.locator('#level-feedback').isVisible()) && (await panel.locator('#saved-note').textContent()).includes('today’s XP counted'), 'Another submitted solution on the same scoring day explains unchanged XP');
    mode.submittedCode += '# different submitted code'; mode.scoreReason = 'awaiting_submission';
    await source.evaluate(() => { window.fixtureCode += '# draft without a matching submission\n'; });
    await recheck();
    assert(last('/analyze').body.practice_event.submission_id === null && (await panel.locator('#saved-note').textContent()).includes('not submitted'), 'An unmatched editor draft is saved as practice without promising XP');
    mode.submittedCode = await source.evaluate(() => window.fixtureCode); mode.submissionId = '712';
    await wait(() => last('/analyze').body.practice_event.submission_id === '712');
    assert(true, 'A newly completed submission is detected without editing the code or reloading the problem');

    await source.bringToFront();
    await source.evaluate(() => { window.fixtureCode = 'class Solution:\n    def twoSum(self, nums, target):\n        pass\n'; });
    await panel.locator('#recheck').click();
    await wait(async () => (await panel.locator('#activity-title').textContent()).includes('Write your solution'));
    const beforeEmpty = count('/analyze');
    await source.evaluate(() => { window.fixtureCode = 'class Solution:\n    def twoSum(self, nums, target):\n        seen = {}\n        return []\n'; });
    await wait(async () => (await panel.locator('#activity-title').textContent()).includes('Ready when you submit'));
    assert(count('/analyze') === beforeEmpty, 'A panel opened on starter code keeps watching without posting every draft edit');
    await source.evaluate(() => {
      const run = document.createElement('button'); run.textContent = 'Run test';
      run.addEventListener('click', () => { window.fixtureRuns = (window.fixtureRuns || 0) + 1; });
      document.body.append(run);
    });
    await source.getByRole('button', { name: 'Run test', exact: true }).click();
    await panel.evaluate(async () => { lastVerdictCheck = 0; await monitorEditor(); });
    assert(count('/analyze') === beforeEmpty && await source.evaluate(() => window.fixtureRuns === 1), 'Run/Test without a completed submission does not post a scoring analysis');
    mode.status = 11; mode.submissionId = '800'; mode.submittedCode = await source.evaluate(() => window.fixtureCode);
    await wait(() => last('/analyze').body.practice_event.submission_id === '800'); await done();
    assert(last('/analyze').body.practice_event.submission_status === 'failed' && !(await panel.locator('#level-feedback').isVisible()), 'A rejected submission is detected automatically after an empty-editor start without awarding XP');
    const afterRejected = count('/analyze');
    await source.evaluate(() => { window.fixtureCode += '# corrected solution revision\n'; });
    await wait(async () => (await panel.locator('#activity-title').textContent()).includes('Your solution changed'));
    await panel.evaluate(async () => { await monitorEditor(); await monitorEditor(); });
    assert(count('/analyze') === afterRejected && !(await panel.locator('#analysis-result').isVisible()), 'Editing rejected code removes stale feedback and does not analyze each keystroke');
    mode.status = 10; mode.submissionId = '801'; mode.scored = true;
    mode.submittedCode = mode.editorCode = await source.evaluate(() => window.fixtureCode);
    await wait(() => last('/analyze').body.practice_event.submission_id === '801'); await done();
    assert(last('/analyze').body.practice_event.submission_status === 'accepted' && await panel.locator('#level-feedback').isVisible(), 'The corrected accepted submission can receive a fresh server-confirmed XP update');
    const afterAccepted = count('/analyze');
    await panel.evaluate(async () => { lastVerdictCheck = 0; await monitorEditor(); });
    assert(count('/analyze') === afterAccepted, 'Monitoring the same completed submission never starts another analysis');
    await source.reload();
    await panel.evaluate(() => new Promise(resolve => setTimeout(resolve, 800))); await done();
    assert(count('/analyze') === afterAccepted && !(await panel.locator('#level-feedback').isVisible()), 'Reloading the accepted problem reuses cached feedback without repeating a reward');
    await website.bringToFront();
    const beforeInactive = graphql.length;
    await panel.evaluate(async () => { lastVerdictCheck = 0; await monitorEditor(); });
    assert(graphql.length === beforeInactive, 'The editor monitor does not poll LeetCode while its source tab is inactive');
    await source.bringToFront(); await done();
    mode.scored = false; mode.patternDetected = false; mode.scoreReason = 'comparison_incomplete'; mode.submissionId = '802';
    groups[0].pattern_evidence_state = 'NONE_OBSERVED'; groups[0].observed_patterns = []; groups[0].unobserved_patterns = ['hash_map_lookup'];
    await recheck();
    assert((await panel.locator('#verdict-label').textContent()).includes('Accepted') && !(await panel.locator('#level-feedback').isVisible()) && (await panel.locator('#saved-note').textContent()).includes('XP unchanged'), 'Accepted code with an unrecognized approach stays Accepted and makes no proficiency or XP claim');
    assert((await panel.locator('#pattern-heading').textContent()).includes('Approach not recognized') && (await panel.locator('#detected-patterns').textContent()).includes('limit of the analysis') && !(await panel.locator('#pattern-explanation').textContent()), 'Unsupported accepted code explains the analysis limit and never retains a stale pattern explanation');
    mode.patternDetected = true;
    mode.policyVersion = 1;
    const beforeOldServer = count('/analyze'); await panel.reload();
    await wait(async () => (await panel.locator('#activity-title').textContent()).includes('companion is being updated'));
    assert(count('/analyze') === beforeOldServer, 'An older backend cannot accidentally score automatic drafts from this extension version');
    mode.policyVersion = 2; await panel.reload(); await done();
    await panel.emulateMedia({ reducedMotion: 'reduce' });
    assert(await panel.locator('.result').evaluate(element => getComputedStyle(element).animationName === 'none'), 'Animations respect reduced-motion preferences');
    assert(errors.length === 0, 'No uncaught browser runtime errors occurred');
    return { passed: passed.length, checks: passed, scope: 'Actual loaded MV3 extension with complete Monaco/React editor and LeetCode submission fixtures. Authenticated PathForge API responses are controlled; live LeetCode was blocked by its access challenge.' };
  } catch (error) {
    await panel.screenshot({ path: '.playwright-cli/extension-review/failure.png', fullPage: true }).catch(() => {});
    throw new Error(`${error.message}\nPassed before failure: ${passed.join('; ')}`);
  } finally {
    if (mode.gate) mode.gate.release();
    if (website) await website.evaluate(() => localStorage.removeItem('sb-browser-test-auth-token')).catch(() => {});
    await panel.close(); await source.close(); if (website) await website.close();
    await worker.evaluate(async () => { await chrome.storage.session.clear(); await chrome.storage.local.remove('pathforgeSetup'); });
    await context.unroute(`${apiBase}/**`, apiHandler); await context.unroute('https://leetcode.com/**', leetcodeHandler); await context.unroute(`${site}/**`, websiteHandler);
  }
}

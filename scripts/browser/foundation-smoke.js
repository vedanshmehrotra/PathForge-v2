// Playwright CLI run-code function. Local fixtures only; never use on production.
// Start frontend :3111 with API :49999/Auth :49998, serve assessment output :3112.
async page => {
  const base = 'http://127.0.0.1:3111', api = 'http://127.0.0.1:49999', auth = 'http://127.0.0.1:49998';
  const fixtureBase = 'http://127.0.0.1:3112';
  const assessmentResponse = await page.request.get(fixtureBase + '/assessment.json');
  const practiceResponse = await page.request.get(fixtureBase + '/practice.json');
  if (!assessmentResponse.ok() || !practiceResponse.ok()) throw new Error('Run the offline assessment first');
  const cases = await assessmentResponse.json(), practice = await practiceResponse.json();
  const assert = (value, message) => { if (!value) throw new Error(message) };
  const checks = [], blocked = [], consoleErrors = [], pageErrors = [], failedRequests = [], submissions = [];
  let desktopStyles;
  let current = cases[0];
  const user = { id: '00000000-0000-4000-8000-000000000007', aud: 'authenticated', role: 'authenticated',
    email: 'fixture@example.invalid', app_metadata: { provider: 'fixture', providers: ['fixture'] },
    user_metadata: { full_name: 'Local fixture' }, created_at: '2026-10-18T00:00:00Z' };
  const profile = { user_id: 7, username: 'fixture', email: user.email, display_name: 'Local fixture',
    onboarding_complete: false, current_streak: 0, experience_level: '', confident_areas: '' };
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()) });
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('requestfailed', request => failedRequests.push(request.url() + ': ' + request.failure()?.errorText));
  page.on('response', response => {
    if (response.status() >= 400) failedRequests.push(response.status() + ': ' + response.url());
  });
  await page.context().route('**/*', async route => {
    const request = route.request(), url = new URL(request.url());
    const reply = body => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body),
      headers: { 'access-control-allow-origin': base, 'access-control-allow-methods': 'GET,POST,OPTIONS',
        'access-control-allow-headers': 'authorization,content-type' } });
    // Vercel injects this only when hosted; a local production server has no
    // analytics endpoint. Stub telemetry explicitly rather than reporting its
    // known local 404 as a product-flow failure or contacting a provider.
    if (url.origin === base && url.pathname === '/_vercel/insights/script.js') {
      return route.fulfill({ status: 200, contentType: 'application/javascript', body: '/* local telemetry stub */' });
    }
    if (url.origin === base) return route.continue();
    if (![api, auth].includes(url.origin)) { blocked.push(url.origin + url.pathname); return route.abort() }
    if (request.method() === 'OPTIONS') return reply({});
    if (url.origin === auth && url.pathname === '/auth/v1/user') return reply(user);
    if (url.origin === api && url.pathname === '/auth/me') return reply(profile);
    if (url.origin === api && url.pathname === '/prepare-problem') {
      const info = current.response.problem_info;
      return reply({ ...info, leetcode_id: 209, title_slug: 'local-fixture', difficulty: 'Medium', topics: [] });
    }
    if (url.origin === api && url.pathname === '/analyze') {
      assert(request.postDataJSON().code === current.code, 'Unexpected source submitted for ' + current.id);
      submissions.push(current.id);
      return reply(current.response);
    }
    if (url.origin === api && url.pathname === '/recommend') {
      const args = request.postDataJSON();
      const key = JSON.stringify([args.difficulty || null, [...(args.excluded_ids || [])].sort()]);
      assert(practice[key], 'Missing actual-service fixture for requested practice choice');
      return reply(practice[key]);
    }
    blocked.push(url.origin + url.pathname);
    return route.abort();
  });
  await page.addInitScript(({ base, user }) => {
    if (location.origin !== base) return;
    const expires = Math.floor(Date.now() / 1000) + 7200;
    const encode = value => btoa(JSON.stringify(value)).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
    const token = encode({ alg: 'HS256', typ: 'JWT' }) + '.' + encode({ sub: user.id, exp: expires }) + '.fixture';
    localStorage.setItem('sb-127-auth-token', JSON.stringify({ access_token: token, refresh_token: 'fixture-only',
      token_type: 'bearer', expires_in: 7200, expires_at: expires, user }));
  }, { base, user });
  await page.setViewportSize({ width: 1440, height: 1000 });
  for (const fixture of cases) {
    current = fixture;
    await page.goto(base + '/analysis');
    await page.getByRole('heading', { name: 'Code Analysis', exact: true }).waitFor();
    await page.evaluate(() => document.fonts.ready.then(() => true));
    if (!desktopStyles) {
      desktopStyles = await page.getByRole('heading', { name: 'Code Analysis', exact: true }).evaluate(
        element => ({ fontSize: getComputedStyle(element).fontSize, fontFamily: getComputedStyle(element).fontFamily }));
      assert(parseFloat(desktopStyles.fontSize) >= 30, 'Desktop heading styles missing: ' + JSON.stringify(desktopStyles));
    }
    await page.getByRole('textbox', { name: 'Python solution', exact: true }).fill(current.code);
    await page.locator('#problem-id').fill('209');
    assert(await page.getByRole('button', { name: 'Run Analysis', exact: true }).isDisabled(), 'Unprepared input enabled analysis');
    await page.getByRole('button', { name: 'Prepare', exact: true }).click();
    await page.locator('#preparation-status').filter({ hasText: 'Problem prepared.' }).waitFor();
    await page.getByRole('button', { name: 'Run Analysis', exact: true }).click();
    const summary = page.locator('#analysis-summary');
    await summary.getByText('No Elo or gap changes', { exact: true }).waitFor();
    const state = current.response.problem_info.solution_groups[0].pattern_evidence_state;
    const headline = state === 'ALL_OBSERVED' ? 'Listed patterns observed — proposed approach' : 'Inconclusive comparison';
    await summary.getByText(headline, { exact: true }).waitFor();
    const text = await page.locator('main').innerText();
    assert(!/your code is incorrect|skill gap increased|Pattern alignment observed/i.test(text), 'Unsupported product claim for ' + current.id);
    assert(await page.getByRole('columnheader', { name: 'Your code', exact: true }).count() === 1, 'Comparison table absent');
    if (['fixed_maximum_sum', 'bracket_matching', 'permutations'].includes(current.id)) {
      await page.screenshot({ path: 'foundation-' + current.id + '.png', fullPage: true });
    }
    await page.locator('#solution-code').fill(current.code + '\n# changed');
    assert(await summary.count() === 0, 'Stale analysis remains visible');
    checks.push(current.id);
  }
  await page.goto(base + '/recommendations');
  const first = practice['[null,[]]'].recommendations[0].title;
  await page.getByRole('heading', { name: first, exact: true }).waitFor();
  await page.getByRole('button', { name: 'Skip ' + first, exact: true }).click();
  await page.getByRole('heading', { name: first, exact: true }).waitFor({ state: 'detached' });
  await page.getByRole('button', { name: 'Reset skips', exact: true }).click();
  await page.getByRole('heading', { name: first, exact: true }).waitFor();
  await page.getByRole('button', { name: 'Medium', exact: true }).click();
  await page.getByRole('heading', { name: 'Number of Islands', exact: true }).waitFor();
  assert(await page.locator('main article').count() === 1, 'Difficulty filter returned unrelated choices');
  checks.push('actual_service_practice_skip_reset_and_difficulty');
  current = cases.find(item => item.id === 'fixed_maximum_sum');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(base + '/analysis');
  await page.getByRole('textbox', { name: 'Python solution', exact: true }).fill(current.code);
  await page.locator('#problem-id').fill('209');
  await page.getByRole('button', { name: 'Prepare', exact: true }).click();
  await page.locator('#preparation-status').filter({ hasText: 'Problem prepared.' }).waitFor();
  await page.getByRole('button', { name: 'Run Analysis', exact: true }).click();
  await page.locator('#analysis-summary').getByText('Listed patterns observed — proposed approach', { exact: true }).waitFor();
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Mobile page overflows');
  await page.screenshot({ path: 'foundation-mobile.png', fullPage: true });
  checks.push('mobile_proposed_comparison');
  assert(blocked.length === 0, 'Unexpected external or unhandled request: ' + JSON.stringify(blocked));
  assert(pageErrors.length === 0 && consoleErrors.length === 0,
    'Browser exception or console error: ' + JSON.stringify({ pageErrors, consoleErrors }));
  assert(failedRequests.length === 0, 'Failed browser requests: ' + JSON.stringify(failedRequests));
  return { checks, submissions, blocked, pageErrors, consoleErrors, failedRequests, desktopStyles,
    telemetry: 'Vercel analytics script stubbed locally',
    scope: 'Local frontend, real engine/API and recommendation-service payloads; mocked auth/transport. No live backend/database integration.' };
}

// Local actual engine/API payloads; mocked auth/transport, never live data.
async page => {
  const base = 'http://127.0.0.1:3111', api = 'http://127.0.0.1:49999', auth = 'http://127.0.0.1:49998';
  const fixture = await page.request.get('http://127.0.0.1:3112/approach-contract.json');
  if (!fixture.ok()) throw new Error('Actual engine fixtures unavailable');
  const cases = await fixture.json();
  const assert = (condition, message) => { if (!condition) throw new Error(message) };
  const checks = [], submitted = [], blocked = [], pageErrors = [], consoleErrors = [], responses = [], failedRequests = [];
  let current = cases.subsets, pendingAnalysis = null;
  const user = { id: '00000000-0000-4000-8000-000000000007', aud: 'authenticated', role: 'authenticated',
    email: 'fixture@example.invalid', app_metadata: { provider: 'fixture', providers: ['fixture'] },
    user_metadata: { full_name: 'Local fixture' }, created_at: '2026-10-18T00:00:00Z' };
  const profile = { user_id: 7, username: 'fixture', email: user.email, display_name: 'Local fixture',
    onboarding_complete: false, current_streak: 0, experience_level: '', confident_areas: '' };
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()) });
  page.on('response', response => { if (response.status() >= 400) responses.push({ status: response.status(), url: response.url() }) });
  page.on('requestfailed', request => failedRequests.push(request.url() + ': ' + request.failure()?.errorText));
  await page.context().route('**/*', async route => {
    const request = route.request(), url = new URL(request.url());
    const reply = (body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body),
      headers: { 'access-control-allow-origin': base, 'access-control-allow-methods': 'GET,POST,OPTIONS',
        'access-control-allow-headers': 'authorization,content-type' } });
    if (url.origin === base && url.pathname === '/_vercel/insights/script.js') return route.fulfill({ status: 200, contentType: 'application/javascript', body: '/* isolated telemetry */' });
    if (url.origin === base) return route.continue();
    if (![api, auth].includes(url.origin)) { blocked.push(url.origin + url.pathname); return route.abort() }
    if (request.method() === 'OPTIONS') return reply({});
    if (url.origin === auth && url.pathname === '/auth/v1/user') return reply(user);
    if (url.origin === api && url.pathname === '/auth/me') return reply(profile);
    if (url.origin === api && url.pathname === '/prepare-problem') return reply(current.prepare, current.prepare_status);
    if (url.origin === api && url.pathname === '/analyze') {
      const body = request.postDataJSON();
      assert(body.code === current.code, 'Code was changed during preparation or explicit code-only choice');
      assert(current.prepare_status === 409 ? !body.problem : body.problem?.leetcode_id === 209, 'Wrong analysis mode submitted');
      submitted.push({ problem: body.problem ?? null, code: body.code });
      if (pendingAnalysis) { const pending = pendingAnalysis; pendingAnalysis = null; return pending(route); }
      return reply(current.response);
    }
    blocked.push(url.origin + url.pathname); return route.abort();
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
  for (const [name, data] of Object.entries(cases)) {
    current = data;
    await page.goto(base + '/analysis');
    await page.getByRole('heading', { name: 'Code Analysis', exact: true }).waitFor();
    await page.locator('#solution-code').fill(current.code);
    await page.locator('#problem-id').fill('209');
    const run = page.getByRole('button', { name: 'Run Analysis', exact: true });
    assert(await run.isDisabled(), name + ': typed but unprepared input was not blocked');
    const before = submitted.length;
    await page.getByRole('button', { name: 'Prepare', exact: true }).click();
    if (current.prepare_status === 409) {
      const codeOnly = page.getByRole('button', { name: 'Inspect code only', exact: true });
      await codeOnly.waitFor();
      const descriptions = page.getByRole('region', { name: 'Approaches outside comparison coverage', exact: true });
      await descriptions.locator('summary').click();
      await descriptions.getByText(current.prepare.detail.approaches[0].name, { exact: true }).waitFor();
      assert(await descriptions.getByRole('table').count() === 0, 'Description became a comparison checklist');
      assert(await run.isDisabled(), name + ': unsupported preparation enabled problem-aware analysis');
      assert(await page.locator('#problem-id').inputValue() === '209', 'Preparation silently cleared the problem');
      assert(submitted.length === before, 'Preparation auto-submitted analysis');
      if (name === 'subsets') await page.screenshot({ path: 'unsupported-preparation.png', fullPage: true });
      await codeOnly.click();
      await page.getByText('Code-only mode. No problem comparison or skill updates. Your code is unchanged.', { exact: true }).waitFor();
      assert(await page.locator('#problem-id').inputValue() === '', 'Explicit choice failed to clear the problem');
      assert(await page.locator('#solution-code').inputValue() === current.code, 'Explicit choice changed code');
      assert(submitted.length === before, 'Explicit mode choice auto-submitted code');
    } else {
      await page.locator('#preparation-status').filter({ hasText: 'Problem prepared.' }).waitFor();
    }
    await run.click();
    await page.locator('#analysis-summary').getByText('Practice saved', { exact: true }).waitFor();
    if (current.prepare_status === 409) {
      await page.locator('#analysis-summary').getByText('Code-only inspection', { exact: true }).waitFor();
      assert(await page.getByRole('table').count() === 0, 'Code-only output contains a requirement checklist');
    } else {
      const observed = page.getByRole('table', { name: 'Pattern comparison 1', exact: true });
      await observed.getByRole('cell', { name: 'Detected', exact: true }).first().waitFor();
      if (name === 'mixed') {
        const descriptions = page.getByRole('region', { name: 'Approaches outside comparison coverage', exact: true });
        await descriptions.locator('summary').click();
        await descriptions.getByText('Enumerate pairs', { exact: true }).waitFor();
        assert(!(await observed.innerText()).includes('Enumerate pairs'), 'Unsupported alternative entered requirements');
        await page.screenshot({ path: 'mixed-approaches.png', fullPage: true });
      }
    }
    const text = await page.locator('main').innerText();
    assert(!/your code is incorrect|skill gap increased|Patterns aligned/.test(text), 'Unjustified product verdict');
    if (name === 'subsets') {
      await page.locator('#approach-details').getByText('brute force', { exact: true }).waitFor();
      await page.screenshot({ path: 'code-only-enumeration.png', fullPage: true });
    }
    assert(submitted.length === before + 1, 'Unexpected analysis request count for ' + name);
    checks.push({ name, preparationStatus: current.prepare_status, skillUpdatesSkipped: true });
  }
  // A late failure must not discard a newer preparation. The slug below is an
  // alias for the same synthetic fixture; unit tests cover different IDs too.
  current = cases.window;
  await page.goto(base + '/analysis');
  await page.locator('#solution-code').fill(current.code);
  await page.locator('#problem-id').fill('209');
  await page.getByRole('button', { name: 'Prepare', exact: true }).click();
  await page.locator('#preparation-status').filter({ hasText: 'Problem prepared.' }).waitFor();
  let releaseError, markPending;
  const pending = new Promise(resolve => { markPending = resolve });
  pendingAnalysis = async route => {
    markPending();
    await new Promise(resolve => { releaseError = resolve });
    return route.fulfill({ status: 409, contentType: 'application/json',
      body: JSON.stringify(cases.depth.prepare), headers: { 'access-control-allow-origin': base } });
  };
  await page.getByRole('button', { name: 'Run Analysis', exact: true }).click();
  await pending;
  await page.locator('#problem-id').fill('minimum-size-subarray-sum');
  await page.getByRole('button', { name: 'Prepare', exact: true }).click();
  await page.locator('#preparation-status').filter({ hasText: 'Problem prepared.' }).waitFor();
  const failedAnalysis = page.waitForResponse(response => response.url() === api + '/analyze' && response.status() === 409);
  releaseError();
  await failedAnalysis;
  await page.getByRole('button', { name: 'Run Analysis', exact: true }).waitFor();
  await page.waitForFunction(() => !document.querySelector('button.action-primary')?.disabled);
  assert((await page.locator('#preparation-status').innerText()).includes('Problem prepared.'), 'Stale failure cleared new preparation');
  assert(await page.getByRole('button', { name: 'Inspect code only', exact: true }).count() === 0, 'Stale unsupported state affected new problem');
  assert(!(await page.locator('main').innerText()).includes('Approach descriptions are saved'), 'Stale error remains visible');
  checks.push({ name: 'stale-analysis-error-preserves-new-preparation' });
  await page.setViewportSize({ width: 390, height: 844 });
  current = cases.depth;
  await page.goto(base + '/analysis');
  await page.locator('#solution-code').fill(current.code);
  await page.locator('#problem-id').fill('209');
  await page.getByRole('button', { name: 'Prepare', exact: true }).click();
  await page.getByRole('button', { name: 'Inspect code only', exact: true }).waitFor();
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Mobile horizontal overflow');
  await page.screenshot({ path: 'unsupported-mobile.png', fullPage: true });
  checks.push({ name: 'mobile-unsupported', width: 390 });
  assert(pageErrors.length === 0 && blocked.length === 0 && failedRequests.length === 0, 'Unexpected browser failure');
  assert(responses.every(r => r.status === 409 && [api + '/prepare-problem', api + '/analyze'].includes(r.url)), 'Unexpected failed HTTP response');
  return { checks, analysesSubmitted: submitted.length, pageErrors, blocked, failedRequests, intentionalHttpErrors: responses, consoleErrors,
    scope: 'Actual builder/resolver/engine/persistence/API payloads; mocked local auth/transport; no live database or LLM.' };
}

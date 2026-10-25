// Local Next.js UI/HTTP checks. No production sign-in, analysis or telemetry.
async page => {
  const origin = 'http://127.0.0.1:3014';
  const output = '.playwright-cli/companion-review';
  const checks = [], errors = [];
  let signedIn = false;
  const assert = (value, text) => { if (!value) throw new Error(text); checks.push(text); };
  page.on('pageerror', error => errors.push(error.message));
  await page.context().route('https://*.supabase.co/**', route => route.fulfill({ status: 401, contentType: 'application/json', body: '{"error":"Real provider calls blocked in local review"}' }));
  await page.context().route('https://pathforge-v2.onrender.com/**', route => {
    const headers = { 'access-control-allow-origin': origin, 'access-control-allow-headers': 'authorization,content-type', 'access-control-allow-methods': 'GET,POST,OPTIONS' };
    if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
    if (!signedIn) return route.fulfill({ status: 401, headers, contentType: 'application/json', body: '{"detail":"Signed-out test"}' });
    const path = new URL(route.request().url()).pathname;
    const today = new Date().toISOString();
    const data = path === '/auth/me' ? { user_id: 41, display_name: 'Sample learner', email: 'sample@example.invalid' }
      : path === '/auth/profile' ? { profiles: [], practice_records: [
        { topic: 'array_traversal', attempt_count: 1, last_attempt_at: today },
        { topic: 'hash_map_lookup', attempt_count: 1, last_attempt_at: today }], overall_elo: 1200 }
      : path === '/elo' ? { pattern_elo: { hash_map_lookup: 1208 }, pattern_levels: {
        hash_map_lookup: { level: 5, experience: 808, into_level: 8, points_per_level: 200, progress_percent: 4 } }, summary: {} }
      : { detail: 'Unexpected endpoint blocked in local review' };
    return route.fulfill({ status: 200, headers, contentType: 'application/json', body: JSON.stringify(data) });
  });
  const response = await page.request.get(`${origin}/companion`);
  const html = await response.text();
  assert(response.ok() && html.includes('Find the pattern') && html.includes('What information is sent?'), 'Public product facts are in server HTML without a browser session');
  assert(html.includes('rel="canonical" href="https://path-forge-v2.vercel.app/companion"') && html.includes('og:image'), 'Canonical and social metadata identify the public product page');
  assert(html.includes('application/ld+json') && !html.includes('aggregateRating'), 'Structured data describes the product without invented reviews');
  await page.goto(`${origin}/companion`);
  await page.getByRole('heading', { level: 1, name: /Find the pattern/ }).waitFor();
  assert(await page.getByRole('link', { name: 'Get it for Firefox' }).getAttribute('href') === 'https://addons.mozilla.org/en-US/firefox/addon/pathforge-companion/', 'Install action goes to the official Mozilla listing');
  await page.locator('img[src*="patterns"]').waitFor();
  await page.waitForFunction(() => [...document.images].filter(image => image.alt.includes('illustrative')).every(image => image.complete && image.naturalWidth > 0));
  await page.screenshot({ path: `${output}/desktop.png`, fullPage: true });
  await page.getByRole('button', { name: 'Progress', exact: true }).click();
  await page.locator('img[alt*="progress screen"]').waitFor();
  assert(await page.getByText('See eligible XP arrive.').isVisible(), 'Existing product tour explains the companion reward boundary');
  await page.getByText('Why can accepted code earn no XP?', { exact: true }).click();
  assert(await page.getByText(/XP requires a supported, verified approach comparison/).isVisible(), 'XP eligibility is explained before account creation');
  await page.getByRole('link', { name: 'Connect your account' }).click();
  await page.getByRole('button', { name: 'Sign in with Google' }).waitFor();
  assert(!(await page.getByText('Your analysis workbench').count()), 'Extension onboarding opens a focused connection page instead of the workbench');
  await page.screenshot({ path: `${output}/connect.png`, fullPage: true });
  await page.goto(`${origin}/progress`);
  await page.getByRole('button', { name: 'Sign in with Google' }).waitFor();
  assert(!(await page.getByRole('heading', { name: 'Learning Progress', exact: true }).count()), 'Existing private pages retain their sign-in gate');
  const robots = await page.request.get(`${origin}/robots.txt`), sitemap = await page.request.get(`${origin}/sitemap.xml`);
  assert(robots.ok() && (await robots.text()).includes('Disallow: /companion/connect'), 'Robots serves crawl rules while excluding the connection flow');
  const map = await sitemap.text();
  assert(sitemap.ok() && map.includes('/companion') && !map.includes('/progress') && !map.includes('/companion/connect'), 'Sitemap lists public pages without personal workspace routes');
  const social = await page.request.get(`${origin}/companion/opengraph-image`);
  assert(social.ok() && social.headers()['content-type'].includes('image/png'), 'Social preview is a working generated image');
  await page.setViewportSize({ width: 375, height: 900 });
  await page.goto(`${origin}/companion`);
  await page.getByRole('heading', { level: 1 }).waitFor();
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Public companion layout fits a narrow viewport');
  await page.screenshot({ path: `${output}/mobile.png`, fullPage: true });
  // A deliberately invalid test token is returned only inside this local test
  // browser. Every provider/API request is intercepted; no real login occurs.
  signedIn = true;
  await page.addInitScript(() => {
    const encode = value => btoa(JSON.stringify(value)).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
    const user = { id: '00000000-0000-4000-8000-000000000041', aud: 'authenticated', email: 'sample@example.invalid', app_metadata: {}, user_metadata: {} };
    const token = `${encode({ alg: 'HS256', typ: 'JWT' })}.${encode({ sub: user.id, exp: Math.floor(Date.now() / 1000) + 3600 })}.not-a-real-signature`;
    const sample = JSON.stringify({ access_token: token, refresh_token: 'nonfunctional-test-fixture', expires_at: Math.floor(Date.now() / 1000) + 3600, expires_in: 3600, token_type: 'bearer', user });
    const get = Storage.prototype.getItem;
    Storage.prototype.getItem = function (key) { return /^sb-.*-auth-token$/.test(key) ? sample : get.call(this, key); };
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`${origin}/companion/connect`);
  await page.getByRole('heading', { name: 'Back to LeetCode. One last step.' }).waitFor();
  assert(await page.getByText('sample@example.invalid', { exact: true }).isVisible(), 'Signed-in connection instructions show the selected sample account');
  await page.goto(`${origin}/progress`);
  await page.getByRole('heading', { name: 'Your recent practice', exact: true }).waitFor();
  await page.getByRole('region', { name: 'Your recent practice' }).getByRole('button', { name: /hash map lookup/i }).click();
  assert(await page.getByRole('heading', { name: 'hash map lookup', exact: true }).isVisible(), 'Selecting recent practice opens that pattern’s detail');
  assert(await page.getByRole('progressbar', { name: 'hash map lookup progress toward level 6' }).getAttribute('aria-valuenow') === '8', 'Learning Progress shows the server-provided level amount');
  await page.screenshot({ path: `${output}/progress.png`, fullPage: true });
  assert(errors.length === 0, `No browser runtime errors: ${errors.join(', ')}`);
  const report = { passed: checks.length, checks, scope: 'Local Next.js public/private UI and HTTP, using controlled account/API fixtures for signed-in views; real OAuth and production data were not exercised.' };
  return report;
}

// Development-only runner. Usage: node scripts/verify_extension_firefox.js [selenium module path] [firefox.exe]
const fs = require('node:fs'), path = require('node:path');
const modulePath = process.argv[2] || 'selenium-webdriver';
const { Builder, By, until } = require(modulePath);
const firefox = require(`${modulePath}/firefox`);
const root = path.resolve(__dirname, '..');
const review = path.join(root, '.playwright-cli', 'extension-firefox-review');
const uuid = '6dcbd772-7b21-42ee-81a2-b64750b05a73', addonId = 'pathforge-companion@pathforge.local';
const code = 'class Solution:\n    def twoSum(self, nums, target):\n        seen = {}\n' +
  Array.from({ length: 100 }, (_, i) => `        # offscreen line ${i}`).join('\n') + '\n        return [0, 1]\n';
const mode = { status: 10, submittedCode: code }, checks = [], networkErrors = [];
const assert = (ok, description) => { if (!ok) throw new Error(description); checks.push(description); };
(async () => {
  fs.mkdirSync(review, { recursive: true });
  // This enables extension-page automation only in the fresh test process/profile.
  process.env.MOZ_REMOTE_ALLOW_SYSTEM_ACCESS = '1';
  const options = new firefox.Options().addArguments('-headless').enableBidi()
    .setPreference('extensions.webextensions.uuids', JSON.stringify({ [addonId]: uuid }));
  if (process.argv[3]) options.setBinary(process.argv[3]);
  const driver = await new Builder().forBrowser('firefox').setFirefoxOptions(options).build();
  let socket, onMessage;
  try {
    await driver.manage().setTimeouts({ pageLoad: 12000, script: 12000 });
    // Block/fulfill all traffic to fixture origins before opening any page.
    const bidi = await driver.getBidi();
    await bidi.subscribe('network.beforeRequestSent'); socket = await bidi.socket;
    onMessage = data => {
      const event = JSON.parse(data.toString());
      if (event.method !== 'network.beforeRequestSent' || !event.params.isBlocked) return;
      const request = event.params.request, url = new URL(request.url);
      let contentType = 'text/html', body;
      if (url.hostname === 'leetcode.com' && url.pathname === '/graphql/') {
        contentType = 'application/json';
        body = JSON.stringify({ data: { questionSubmissionList: { submissions: [{ id: '701' }] }, submissionDetails: {
          code: mode.submittedCode, statusCode: mode.status, lang: { name: 'Python3' }, question: { titleSlug: 'two-sum', title: 'Two Sum' },
        } } });
      } else if (url.hostname === 'leetcode.com') {
        body = `<!doctype html><a href="/problems/two-sum/">1. Two Sum</a><div class="monaco-editor" style="width:700px;height:500px"><div class="view-lines">VISIBLE LINES ONLY</div></div><script>
          window.fixtureCode=${JSON.stringify(code)}; window.fixtureLanguage='python';
          window.fixtureModel={getValue:()=>window.fixtureCode,getLanguageId:()=>window.fixtureLanguage,isDisposed:()=>false};
          window.fixtureEditor={getValue:()=>window.fixtureCode,getModel:()=>window.fixtureModel,getDomNode:()=>document.querySelector('.monaco-editor'),hasTextFocus:()=>true};
          window.monaco={editor:{getEditors:()=>[window.fixtureEditor],getModels:()=>[window.fixtureModel]}};
        </script>`;
      } else if (url.hostname === 'path-forge-v2.vercel.app') {
        body = '<!doctype html><p>Signed-in test website</p><script>localStorage.setItem("sb-firefox-fixture-auth-token",JSON.stringify({access_token:"firefox-fixture-token"}));</script>';
      } else { contentType = 'application/json'; body = JSON.stringify({ detail: 'Unexpected production request blocked by test harness.' }); }
      bidi.send({ method: 'network.provideResponse', params: { request: request.request, statusCode: 200,
        headers: [{ name: 'Content-Type', value: { type: 'string', value: contentType } }], body: { type: 'string', value: body },
      } }).catch(error => networkErrors.push(error.message));
    };
    socket.on('message', onMessage);
    const interception = await bidi.send({ method: 'network.addIntercept', params: { phases: ['beforeRequestSent'],
      urlPatterns: ['leetcode.com', 'path-forge-v2.vercel.app', 'pathforge-v2.onrender.com'].map(hostname => ({ type: 'pattern', protocol: 'https', hostname })),
    } });
    if (interception.error) throw new Error(JSON.stringify(interception));
    assert(await driver.installAddon(path.join(root, 'dist', 'pathforge-extension-firefox.zip'), true) === addonId, 'Firefox installs the packaged ZIP as the expected temporary add-on');
    await driver.get('https://path-forge-v2.vercel.app/analysis');
    await driver.switchTo().newWindow('tab'); await driver.get('https://leetcode.com/problems/two-sum/description/');
    const source = await driver.getWindowHandle();
    await driver.switchTo().newWindow('tab'); await driver.get(`moz-extension://${uuid}/panel.html`);
    const panel = await driver.getWindowHandle();
    await driver.wait(until.elementIsVisible(await driver.findElement(By.id('setup'))), 12000);
    assert(await driver.findElement(By.id('setup')).isDisplayed(), 'Native Firefox panel initializes with first-use setup');
    const permissions = await driver.executeScript('return browser.permissions.getAll()');
    assert(permissions.origins.includes('https://leetcode.com/*') && permissions.origins.includes('https://path-forge-v2.vercel.app/*'), 'Firefox grants required website/editor host permissions');
    await driver.executeScript(() => {
      const button = document.createElement('button'); button.id = 'verify-sidebar'; button.textContent = 'Verify sidebar';
      button.onclick = () => browser.sidebarAction.toggle(); document.body.prepend(button);
    });
    await driver.findElement(By.id('verify-sidebar')).click();
    assert(await driver.executeScript('return browser.sidebarAction.isOpen({})'), 'A user gesture opens the native Firefox sidebar');
    await driver.findElement(By.id('verify-sidebar')).click();
    assert(!(await driver.executeScript('return browser.sidebarAction.isOpen({})')), 'A second gesture closes the native Firefox sidebar');
    await driver.executeScript('document.getElementById("verify-sidebar").remove()');
    // A sidebar remembers the LeetCode tab beneath it. Reproduce that saved source
    // when testing the same panel document in a WebDriver-controlled extension tab.
    const tabs = await driver.executeScript('return browser.tabs.query({url:"https://leetcode.com/*"})');
    await driver.executeScript('return browser.windows.getCurrent().then(win => browser.storage.session.set({["pathforgeSource:"+win.id]:arguments[0]}))', tabs[0].id);
    await driver.navigate().refresh();
    await driver.wait(until.elementIsVisible(await driver.findElement(By.id('setup'))), 12000);
    // Only the fetch boundary is mocked; account scanning, storage and editor injection are native.
    await driver.executeScript(() => {
      window.fixtureCalls = [];
      window.fetch = async (url, options = {}) => {
        const endpoint = new URL(url).pathname, body = options.body ? JSON.parse(options.body) : null;
        window.fixtureCalls.push({ endpoint, body, authorization: options.headers?.Authorization });
        let data;
        if (endpoint === '/auth/session') data = { authenticated: true, practice_policy_version: 2, user_id: 41, email: 'firefox-fixture@example.invalid' };
        else if (endpoint === '/prepare-problem') data = { leetcode_id: 1, title: 'Two Sum', difficulty: 'Easy' };
        else if (endpoint === '/analyze') data = { ast: { detected_patterns: [{ pattern_id: 'hash_map_lookup', confidence: .95 }] },
          problem_info: { title: 'Two Sum', difficulty: 'Easy', solution_groups: [{ name: 'Hash lookup', patterns: ['hash_map_lookup'], review_state: 'UNREVIEWED', pattern_evidence_state: 'ALL_OBSERVED', observed_patterns: ['hash_map_lookup'], unobserved_patterns: [], family_relation: 'ONE_OF' }] }, persisted: { submission_id: 321 } };
        else if (endpoint === '/recommend') data = { recommendations: [
          { title: 'Contains Duplicate', difficulty: 'Easy', pattern: 'hash_map_lookup', problem_url: 'https://leetcode.com/problems/contains-duplicate/' },
          { title: 'Valid Anagram', difficulty: 'Easy', topics: ['String'], practice_kind: 'follow_up', problem_url: 'https://leetcode.com/problems/valid-anagram/' },
          { title: 'Valid Parentheses', difficulty: 'Easy', pattern: 'stack', problem_url: 'https://leetcode.com/problems/valid-parentheses/' },
        ] };
        else throw new Error(`Unexpected endpoint: ${endpoint}`);
        return new Response(JSON.stringify(data), { status: 200, headers: { 'Content-Type': 'application/json' } });
      };
    });
    await driver.findElement(By.id('connect-account')).click();
    const done = () => driver.wait(async () => await driver.findElement(By.id('analysis-result')).isDisplayed() && await driver.findElement(By.id('recheck')).isEnabled(), 12000);
    await done();
    assert(!(await driver.findElement(By.id('setup')).isDisplayed()), 'Verified connection hides setup and automatically analyzes captured editor code');
    let calls = await driver.executeScript('return window.fixtureCalls');
    const analysis = calls.find(call => call.endpoint === '/analyze');
    assert(analysis?.body.code === code && analysis.body.user_id === 41 && analysis.authorization === 'Bearer firefox-fixture-token', 'MAIN-world capture preserves complete offscreen source and uses the verified PathForge account');
    assert((await driver.findElement(By.id('verdict-label')).getText()) === 'Accepted on LeetCode', 'Matching LeetCode source displays Accepted');
    await driver.wait(async () => (await driver.findElements(By.css('a.recommendation'))).length === 3, 12000);
    assert((await driver.findElement(By.id('detected-patterns')).getText()).includes('Hash lookup'), 'Compact results show backend pattern evidence');
    assert((await driver.findElements(By.css('a.recommendation'))).length === 3 && (await driver.findElement(By.css('a.recommendation')).getAttribute('href')).endsWith('/valid-anagram/'), 'Three clickable recommendations put the backend follow-up first');
    const storage = await driver.executeScript('return Promise.all([browser.storage.session.get(),browser.storage.local.get()])');
    assert(storage[0].pathforgeSession?.access_token === 'firefox-fixture-token' && storage[1].pathforgeSetup && !JSON.stringify(storage[1]).includes('firefox-fixture-token'), 'Access token stays in session storage; local storage holds the connection preference');
    const before = calls.filter(call => call.endpoint === '/analyze').length;
    await driver.findElement(By.id('recheck')).click(); await done();
    calls = await driver.executeScript('return window.fixtureCalls');
    assert(calls.filter(call => call.endpoint === '/analyze').length === before, 'Identical code reuses confirmed analysis without another write');
    mode.status = 11; mode.submittedCode = `${code}\n# changed solution`;
    await driver.switchTo().window(source); await driver.executeScript('window.fixtureCode = arguments[0]', mode.submittedCode);
    await driver.switchTo().window(panel); await driver.findElement(By.id('recheck')).click(); await done();
    await driver.wait(async () => (await driver.executeScript('return window.fixtureCalls')).filter(call => call.endpoint === '/recommend').at(-1)?.body.mode === 'legacy', 12000);
    assert((await driver.findElement(By.id('verdict-label')).getText()) === 'Wrong answer on LeetCode', 'Matching failed source selects existing pattern-focused recommendations');
    mode.status = 10; mode.submittedCode = code;
    await driver.findElement(By.id('recheck')).click(); await done();
    assert((await driver.findElement(By.id('verdict-label')).getText()) === 'Not checked on LeetCode', 'An old Accepted submission cannot establish correctness for edited source');
    await driver.manage().window().setRect({ width: 400, height: 900 });
    assert(await driver.executeScript('return document.documentElement.scrollWidth <= innerWidth'), 'Compact Firefox layout has no horizontal overflow');
    fs.writeFileSync(path.join(review, 'compact.png'), await driver.takeScreenshot(), 'base64');
    await driver.findElement(By.id('settings-toggle')).click(); await driver.findElement(By.id('disconnect')).click();
    await driver.wait(until.elementIsVisible(await driver.findElement(By.id('setup'))), 12000);
    const cleared = await driver.executeScript('return browser.storage.session.get()');
    assert(!cleared.pathforgeSession && !cleared.pathforgeChecks, 'Disconnect removes session credentials and result cache');
    assert(networkErrors.length === 0, 'Fixture networking completed without protocol errors');
    const report = { passed: checks.length, checks, browser: (await driver.getCapabilities()).get('browserVersion'), scope: 'Actual packaged Firefox extension and native sidebar/storage/tabs/scripting. LeetCode, website and API responses are fixtures; no production writes.' };
    fs.writeFileSync(path.join(review, 'report.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify({ passed: checks.length, report: path.join(review, 'report.json') }));
  } catch (error) {
    fs.writeFileSync(path.join(review, 'failure.png'), await driver.takeScreenshot().catch(() => ''), 'base64');
    console.error(`Passed before failure: ${checks.join('; ')}`); throw error;
  } finally {
    if (socket && onMessage) socket.off('message', onMessage);
    await driver.quit();
  }
})().catch(error => { console.error(error.stack); process.exitCode = 1; });

const API_BASE = 'https://pathforge-v2.onrender.com';
const WEBSITE_BASE = 'https://path-forge-v2.vercel.app';
const SESSION_KEY = 'pathforgeSession';
const CACHE_KEY = 'pathforgeChecks';
const SETUP_KEY = 'pathforgeSetup';
const PATTERN_HINT_KEY = 'pathforgePatternHintSeen';
const $ = id => document.getElementById(id);
const state = { session: null, verified: false, connecting: false, running: false, accountVersion: 0,
  viewVersion: 0, windowId: null, sourceTabId: null, snapshot: null, checks: {}, queued: false, changed: false, booting: true, setupOpened: false, patternHintSeen: false };
const requests = new Set();
let navigationTimer;
let levelTimers = [];
let monitoringEditor = false;
let lastVerdictCheck = 0;
let lastVerdictSource = null;

class ApiError extends Error {
  constructor(message, status = 0, detail = null) { super(message); this.status = status; this.detail = detail; }
}
function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text != null) element.textContent = String(text);
  return element;
}
function message(text = '', kind = '') {
  $('message').textContent = text;
  $('message').className = `message ${kind}`;
}
function activity(title, help = '', loading = false) {
  $('activity').classList.remove('hidden');
  $('activity').classList.toggle('loading', loading);
  $('activity-title').textContent = title;
  $('activity-help').textContent = help;
}
function renderAccount() {
  $('setup').classList.toggle('hidden', state.verified || state.booting);
  $('boot-status').classList.toggle('hidden', !state.booting || state.verified);
  $('workspace').classList.toggle('hidden', !state.verified);
  $('settings-toggle').disabled = !state.verified;
  $('account-email').textContent = state.session?.email || 'PathForge account';
  $('connect-account').disabled = state.connecting;
  $('connect-account').textContent = state.connecting ? 'Connecting…' : state.setupOpened ? 'Connect account' : "I'm already signed in";
  $('connect-account').className = `button ${state.setupOpened ? 'primary' : 'secondary'}`;
  $('open-app').className = `button ${state.setupOpened ? 'secondary' : 'primary'}`;
  $('open-app').textContent = state.setupOpened ? 'Return to sign-in page' : 'Sign in on PathForge';
  $('setup-step').textContent = state.setupOpened ? '2. Signed in? Connect your account here.' : '1. Sign in on PathForge · 2. Connect here';
  $('reconnect').disabled = state.running || state.connecting;
  $('recheck').disabled = state.running;
  $('recheck').classList.toggle('spinning', state.running);
  if (!state.verified) $('settings').classList.add('hidden');
}
function clearView() {
  for (const timer of levelTimers) clearTimeout(timer);
  levelTimers = [];
  $('level-feedback').className = 'level-feedback hidden';
  $('level-feedback').replaceChildren();
  $('level-feedback').style.height = '';
  $('pattern-hint').classList.add('hidden');
  $('watch-status').textContent = 'Checks after Submit';
  state.snapshot = null; state.changed = false;
  for (const id of ['analysis-result', 'next-practice', 'problem-picker', 'inspect-anyway', 'retry-analysis', 'read-again']) $(id).classList.add('hidden');
  for (const id of ['detected-patterns', 'comparison', 'recommendations']) $(id).replaceChildren();
  $('problem-title').textContent = 'Your solution';
  $('difficulty').textContent = '';
  $('saved-note').textContent = '';
  $('xp-detail').textContent = '';
  $('pattern-explanation').textContent = '';
  $('comparison-details').open = false;
  message();
}
function errorText(data, status) {
  if (typeof data?.detail === 'string') return data.detail;
  return data?.detail?.message || data?.detail?.error || `PathForge request failed (${status}).`;
}

async function api(path, { body, session = state.session, timeout = 30000 } = {}) {
  if (!session?.access_token) throw new ApiError('Connect your account first.');
  const controller = new AbortController();
  requests.add(controller);
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeout);
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: body ? 'POST' : 'GET',
      headers: { Authorization: `Bearer ${session.access_token}`, ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined, signal: controller.signal,
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      if (response.status === 401 && state.verified && state.session?.access_token === session.access_token) {
        await disconnect('Reconnect your account to continue.', false);
      }
      throw new ApiError(errorText(data, response.status), response.status, data?.detail);
    }
    if (!data || typeof data !== 'object') throw new ApiError('PathForge returned an unreadable response.');
    return data;
  } catch (error) {
    if (timedOut) throw new ApiError(path === '/analyze'
      ? 'The analysis response timed out. It may have been saved. Check your PathForge record before submitting again.'
      : 'PathForge took too long to respond. Please try again.');
    if (error.name === 'AbortError') throw error;
    if (error instanceof ApiError) throw error;
    throw new ApiError(path === '/analyze'
      ? 'The connection ended before confirmation. The analysis may have been saved. Check your PathForge record before submitting again.'
      : 'Could not reach PathForge. Check your connection and try again.');
  } finally { clearTimeout(timer); requests.delete(controller); }
}

async function openWebsite() {
  const tabs = await browser.tabs.query({ url: `${WEBSITE_BASE}/*`, windowId: state.windowId });
  const connection = tabs.find(tab => tab.url?.startsWith(`${WEBSITE_BASE}/companion/connect`));
  if (connection) await browser.tabs.update(connection.id, { active: true });
  else await browser.tabs.create({ url: `${WEBSITE_BASE}/companion/connect`, windowId: state.windowId });
  state.setupOpened = true; renderAccount();
  message('Sign in on the website, then choose Connect account in this panel.');
}

async function websiteTokens() {
  const tabs = await browser.tabs.query({ url: `${WEBSITE_BASE}/*`, windowId: state.windowId });
  if (!tabs.length) throw new ApiError('Open the PathForge website and sign in in this Chrome window, then connect again.');
  const tokens = [];
  tabs.sort((a, b) => Number(b.active) - Number(a.active) || (b.lastAccessed || 0) - (a.lastAccessed || 0));
  for (const tab of tabs) {
    if (tab.id == null || tab.discarded) continue;
    try {
      // Isolated execution shares the page's local storage without using its JavaScript globals.
      const [result] = await browser.scripting.executeScript({ target: { tabId: tab.id }, world: 'ISOLATED', func: () => {
        const found = [];
        for (const key of Object.keys(localStorage)) {
          if (!/^sb-.*-auth-token$/.test(key)) continue;
          try {
            let value = localStorage.getItem(key);
            if (value?.startsWith('base64-')) value = atob(value.slice(7));
            const session = JSON.parse(value || 'null');
            if (typeof session?.access_token === 'string') found.push(session.access_token);
          } catch { /* Ignore storage entries that are not valid sessions. */ }
        }
        return found;
      } });
      if (Array.isArray(result?.result)) tokens.push(...result.result);
    } catch { /* A navigating or closed tab may become unavailable. */ }
  }
  if (!tokens.length) throw new ApiError('No signed-in website session found. Finish signing in, then connect again.');
  return [...new Set(tokens)];
}

function validSession(data) {
  return data?.authenticated === true && Number.isInteger(data.user_id) && data.user_id > 0;
}


async function connectAccount(automatic = false) {
  if (state.connecting || state.running) return;
  const account = ++state.accountVersion;
  state.connecting = true; renderAccount();
  if (!automatic) message('Connecting your account…');
  try {
    let connected;
    for (const access_token of await websiteTokens()) {
      try {
        const verified = await api('/auth/session', { session: { access_token }, timeout: 60000 });
        if (!validSession(verified)) throw new ApiError('Could not verify your PathForge account.');
        connected = { access_token, user_id: verified.user_id, email: verified.email || '', practice_policy_version: verified.practice_policy_version }; break;
      } catch (error) { if (error.status !== 401) throw error; }
    }
    if (!connected) throw new ApiError('Sign in to PathForge again, then connect here.');
    if (account !== state.accountVersion) return;
    if (state.session && state.session.user_id !== connected.user_id) state.checks = {};
    state.session = connected; state.verified = true;
    await browser.storage.session.set({ [SESSION_KEY]: connected, [CACHE_KEY]: state.checks });
    await browser.storage.local.set({ [SETUP_KEY]: true });
    clearView(); renderAccount(); message();
  } catch (error) { if (account === state.accountVersion) message(automatic ? 'Open PathForge and sign in to reconnect.' : error.message, 'error'); }
  finally { if (account === state.accountVersion) { state.connecting = false; renderAccount(); } }
  if (state.verified) await captureAndAnalyze();
}
async function disconnect(reason = 'Disconnected.', manual = true) {
  ++state.accountVersion; ++state.viewVersion;
  for (const controller of requests) controller.abort();
  state.session = null; state.verified = false; state.running = false; state.connecting = false; state.queued = false;
  if (manual) state.checks = {};
  clearView();
  await browser.storage.session.remove(manual ? [SESSION_KEY, CACHE_KEY] : SESSION_KEY);
  if (manual) await browser.storage.local.set({ [SETUP_KEY]: false });
  renderAccount(); message(reason);
}
function problemSlug(url) {
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== 'https:' || !['leetcode.com', 'www.leetcode.com'].includes(parsed.hostname)) return '';
    return parsed.pathname.match(/^\/problems\/([a-z0-9]+(?:-[a-z0-9]+)*)(?:\/|$)/)?.[1] || '';
  } catch { return ''; }
}
async function sourceTab() {
  const [active] = await browser.tabs.query({ active: true, windowId: state.windowId });
  if (problemSlug(active?.url)) {
    state.sourceTabId = active.id;
    await browser.storage.session.set({ [`pathforgeSource:${state.windowId}`]: active.id });
    return active;
  }
  if (state.sourceTabId != null) {
    const previous = await browser.tabs.get(state.sourceTabId).catch(() => null);
    if (previous?.windowId === state.windowId && problemSlug(previous.url)) return previous;
  }
  return null;
}
async function capture(tab, includeSubmission = true) {
  const [result] = await browser.scripting.executeScript({ target: { tabId: tab.id }, world: 'MAIN', func: readLeetCode, args: [{ includeSubmission }] });
  return result?.result || { error: 'EDITOR_UNAVAILABLE' };
}
async function sourceMatches(tab, snapshot) {
  const latest = await capture(tab, false);
  return latest.source === 'editor' && latest.code === snapshot.code && latest.slug === snapshot.slug;
}
function captureFailure(snapshot) {
  const messages = {
    EDITOR_UNAVAILABLE: ['Open the Code tab in LeetCode', 'Keep the editable solution visible. Submission previews are not analyzed.'],
    EDITOR_NOT_EDITABLE: ['Open the Code tab in LeetCode', 'PathForge is paused while you browse submissions or read-only code. Return to the editable solution to continue.'],
    AMBIGUOUS_EDITOR: ['Choose one solution editor', 'Close the extra editor or diff view, then recheck.'],
    EMPTY_SOLUTION: ['Write your solution in LeetCode', 'Submit for an automatic check, or recheck for a preview.'],
    UNSUPPORTED_LANGUAGE: ['Switch to Python in LeetCode', 'The current PathForge analyzer supports Python and Python3.'],
    CODE_CHANGED: ['Your code changed', 'Recheck when you are ready.'],
    NOT_A_PROBLEM: ['Open a LeetCode problem', 'Its code and problem will be read automatically.'],
  };
  const [title, help] = messages[snapshot.error] || messages.EDITOR_UNAVAILABLE;
  activity(title, help);
  $('watch-status').textContent = 'Paused · editor needed';
  $('read-again').classList.toggle('hidden', !['EDITOR_UNAVAILABLE', 'EDITOR_NOT_EDITABLE', 'AMBIGUOUS_EDITOR', 'CODE_CHANGED'].includes(snapshot.error));
}
async function cacheSave(key, entry) {
  state.checks[key] = { ...entry, at: Date.now() };
  state.checks = Object.fromEntries(Object.entries(state.checks).sort((a, b) => b[1].at - a[1].at).slice(0, 12));
  await browser.storage.session.set({ [CACHE_KEY]: state.checks });
}
async function fingerprint(snapshot, codeOnly) {
  const bytes = new TextEncoder().encode(`${browser.runtime.getManifest().version}:${state.session.user_id}:${snapshot.slug}:${codeOnly}:${snapshot.submissionId || 'draft'}:${snapshot.verdict?.state || 'unknown'}:${snapshot.code}`);
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(value => value.toString(16).padStart(2, '0')).join('');
}
async function captureAndAnalyze({ retry = false, codeOnly = false } = {}) {
  clearTimeout(navigationTimer);
  if (!state.verified || !state.session) return;
  if (!(state.session.practice_policy_version >= 2)) {
    activity('The companion is being updated', 'Use the PathForge website until practice updates are ready.');
    return;
  }
  if (state.running) { state.queued = true; return; }
  const account = state.accountVersion;
  const view = ++state.viewVersion;
  const current = () => account === state.accountVersion && view === state.viewVersion && state.verified;
  const session = state.session;
  state.running = true; clearView(); renderAccount();
  activity('Reading your solution', 'From the LeetCode editor', true);
  let key, writing = false;
  try {
    const tab = await sourceTab();
    if (!current()) return;
    if (!tab) {
      activity('Open a LeetCode problem', 'Write your solution there. PathForge will read it here.');
      $('problem-picker').classList.remove('hidden'); return;
    }
    let snapshot;
    for (let attempt = 0; attempt < 6; attempt++) {
      snapshot = await capture(tab);
      if (snapshot.error !== 'EDITOR_UNAVAILABLE') break;
      await new Promise(resolve => setTimeout(resolve, 400));
      if (!current()) return;
    }
    if (!current()) return;
    $('problem-title').textContent = snapshot.title || problemSlug(tab.url).replaceAll('-', ' ');
    if (snapshot.error) { captureFailure(snapshot); return; }
    state.snapshot = { ...snapshot, tabId: tab.id };
    key = await fingerprint(snapshot, codeOnly);
    const cached = state.checks[key];
    if (cached?.status === 'done') {
      const saved = cached.data.persisted;
      renderAnalysis({ ...cached.data, persisted: saved?.score_reason === 'scored' ? { ...saved, replayed: true } : saved }, snapshot);
      await recommendations(cached.data, snapshot, current);
      return;
    }
    if (cached && !retry) {
      activity('Check your saved practice', 'A previous check may have finished. View your record before retrying.');
      $('retry-analysis').classList.remove('hidden'); return;
    }
    let problem;
    if (!codeOnly) {
      activity('Finding the approach', 'First-time problem setup can take a little longer.', true);
      let prepared;
      try { prepared = await api('/prepare-problem', { body: { problem: { title_slug: snapshot.slug } }, session, timeout: 120000 }); }
      catch (error) { if (current() && error.status !== 401) $('inspect-anyway').classList.remove('hidden'); throw error; }
      if (!current()) return;
      if (!Number.isInteger(prepared.leetcode_id) || prepared.leetcode_id <= 0) throw new ApiError('This problem could not be identified.');
      problem = { leetcode_id: prepared.leetcode_id };
      $('problem-title').textContent = prepared.title || snapshot.title;
      $('difficulty').textContent = prepared.difficulty || '';
      snapshot.title = prepared.title || snapshot.title;
    }
    const sameSource = await sourceMatches(tab, snapshot);
    if (!current()) return;
    if (!sameSource) { captureFailure({ error: 'CODE_CHANGED' }); return; }
    activity('Reading the patterns', '', true);
    await cacheSave(key, { status: 'pending' });
    if (!current()) return;
    writing = true;
    const data = await api('/analyze', { body: { user_id: session.user_id, code: snapshot.code, language: 'python',
      practice_event: { source: 'extension', submission_id: snapshot.submissionId || null,
        submission_status: snapshot.submissionId && ['accepted', 'failed'].includes(snapshot.verdict?.state) ? snapshot.verdict.state : null },
      ...(problem ? { problem } : {}) }, session, timeout: 60000 });
    if (account !== state.accountVersion) return;
    const cachedData = { ast: { detected_patterns: data.ast?.detected_patterns || [] },
      problem_info: data.problem_info ? { title: data.problem_info.title, difficulty: data.problem_info.difficulty, solution_groups: data.problem_info.solution_groups } : null,
      persisted: data.persisted || null };
    await cacheSave(key, { status: 'done', data: cachedData });
    if (!current()) return;
    const sameAfter = await sourceMatches(tab, snapshot);
    if (!current()) return;
    if (!sameAfter) { captureFailure({ error: 'CODE_CHANGED' }); return; }
    renderAnalysis(data, snapshot);
    await recommendations(data, snapshot, current);
  } catch (error) {
    if (account === state.accountVersion && writing && key && state.checks[key]?.status !== 'done') {
      if (error.status >= 400 && error.status < 500) { delete state.checks[key]; await browser.storage.session.set({ [CACHE_KEY]: state.checks }); }
      else await cacheSave(key, { status: 'uncertain' });
    }
    if (current()) { activity('Couldn’t finish this check', error.message || 'Please recheck in a moment.'); }
  } finally {
    if (account === state.accountVersion) {
      state.running = false; renderAccount();
      if (state.queued) { state.queued = false; captureAndAnalyze(); }
    }
  }
}
function label(value) {
  const names = { hash_map_lookup: 'Hash lookup', hash_map_frequency: 'Frequency counting', two_pointers_same: 'Two pointers', two_pointers_opposite: 'Two pointers', sliding_window: 'Sliding window', sliding_window_fixed: 'Fixed sliding window', sliding_window_variable: 'Variable sliding window', binary_search: 'Binary search', binary_search_standard: 'Binary search', binary_search_rotated: 'Rotated binary search', binary_search_answer: 'Binary search on answers', dfs_recursive: 'Depth-first search', dfs_iterative: 'Depth-first search', bfs: 'Breadth-first search', bfs_level_order: 'Breadth-first search', bfs_shortest_path: 'Breadth-first search', dp_1d_forward: 'Dynamic programming', dp_1d_sequence: 'Sequence dynamic programming', dp_2d_grid: 'Grid dynamic programming', dp_2d_string: 'String dynamic programming', dp_knapsack: 'Knapsack', dp_interval: 'Interval dynamic programming', dp_state_machine: 'State-based dynamic programming', heap_top_k: 'Heap selection', greedy_local: 'Greedy choice', greedy_interval: 'Greedy intervals', backtracking_permutation: 'Backtracking: arrangements', backtracking_subset: 'Backtracking: subsets' };
  return names[value] || String(value || '').replaceAll('_', ' ').replace(/\bdp\b/gi, 'dynamic programming').replace(/^./, character => character.toUpperCase());
}
function patternExplanation(id) {
  const descriptions = {
    hash_map_lookup: 'You use a dictionary to look up a value without searching the whole collection again.',
    hash_map_frequency: 'You count how often values appear, keeping a total for each value.',
    array_traversal: 'You visit items in a sequence to inspect them or build an answer.',
    sliding_window_fixed: 'You move a fixed-size window across the sequence, updating what enters and leaves.',
    sliding_window_variable: 'You grow or shrink a window to keep a section of the sequence within a condition.',
    two_pointers_same: 'Two positions move through the sequence in the same direction.',
    two_pointers_opposite: 'Two positions move toward each other to narrow the search.',
    binary_search_standard: 'You repeatedly narrow a sorted search range instead of checking every item.',
    dfs_recursive: 'You explore one branch deeply before returning to try another.',
    dfs_iterative: 'A stack remembers branches to explore, letting you go deeper before trying another branch.',
    bfs_level_order: 'You use a queue to explore nearby items before moving to the next layer.',
    bfs_shortest_path: 'A queue explores nearby positions first. On an unweighted graph, this can find the fewest steps.',
    topological_sort: 'You work through dependencies, choosing items whose prerequisites are ready.',
    union_find: 'You track which items belong to the same group and combine groups when they connect.',
    binary_search_tree: 'An ordered tree lets comparisons guide you toward the relevant branch.',
    binary_search_rotated: 'You identify an ordered part of a rotated sequence, then narrow the search.',
    binary_search_answer: 'You test a candidate answer and narrow the range of possible answers.',
    dp_1d_forward: 'You build answers from smaller answers already stored in a one-dimensional table.',
    dp_1d_sequence: 'You reuse answers for earlier parts of a sequence instead of solving them again.',
    dp_2d_grid: 'Each grid position uses answers from earlier positions to build the result.',
    dp_2d_string: 'A table remembers results for pairs of positions in strings or sequences.',
    dp_knapsack: 'You compare taking or skipping items while tracking the remaining capacity.',
    dp_interval: 'You build answers for larger intervals from answers for smaller intervals.',
    dp_state_machine: 'You track several possible states and reuse their results as each new item arrives.',
    fast_slow_pointers: 'Two positions move at different speeds to locate a midpoint or detect a cycle.',
    linked_list_reversal: 'You change the links between nodes to reverse their direction.',
    monotonic_stack: 'You keep stack values in order, removing candidates that are no longer useful.',
    monotonic_deque: 'You keep ordered candidates for a moving range, removing old or less useful entries.',
    heap_top_k: 'A priority queue keeps useful ranked candidates available without sorting everything again.',
    greedy_local: 'A greedy approach chooses a locally useful option at each step. The choice still needs to be justified.',
    greedy_interval: 'You order and compare intervals to select or combine them.',
    backtracking_permutation: 'You try arrangements one choice at a time, undoing each choice before exploring another.',
    backtracking_subset: 'You explore groups of choices, undoing each choice before trying a different branch.',
    sorting: 'You put values in order before working with them. Sorting is a step, not proof of the whole approach.',
    brute_force: 'You try candidate answers directly. This can be useful when the search space is small.',
    prefix_sum: 'You store running totals so a section can be measured from its endpoints.',
    stack: 'You keep recent items in a stack and work with the most recent one first.',
  };
  return descriptions[id] || 'PathForge spotted this structure in your code. Tap another pattern to explore it.';
}
function practiceFeedback(saved, verdict) {
  if (!saved?.submission_id) return ['', ''];
  if (saved.replayed) return ['Already saved · no extra XP', 'This check is already in your practice record. Rechecking does not earn XP again.'];
  const reasons = {
    problem_already_scored_today: ['Practice saved · today’s XP counted', 'This problem has already changed your XP today (UTC). You can keep practising without another rating change.'],
    awaiting_submission: ['Practice saved · not submitted', 'Submit on LeetCode to check correctness. Drafts and Run/Test never change XP.'],
    submission_not_accepted: ['Practice saved · fix and submit again', 'No XP lost. Correct your solution and submit again; you can still qualify today.'],
    submission_status_unavailable: ['Practice saved · verdict not confirmed', 'XP is unchanged until a completed LeetCode submission matches this code.'],
    expectations_not_authorizing: ['Practice saved · XP unchanged', 'This problem’s approach has not been verified for XP yet. Your practice is still saved.'],
    comparison_unavailable: ['Practice saved · XP unchanged', 'There is no supported approach comparison for this problem yet. Your practice still counts.'],
    comparison_incomplete: ['Practice saved · XP unchanged', verdict.state === 'accepted'
      ? 'Your solution was accepted. PathForge could not verify its approach for pattern XP. Your practice is saved.'
      : 'PathForge could not verify a supported approach for pattern XP. Your practice is saved.'],
    observational_components_not_scoring: ['Practice saved · XP unchanged', 'These code patterns are recorded as practice, but do not qualify for XP scoring.'],
    approach_unsupported_or_ambiguous: ['Practice saved · XP unchanged', 'This approach cannot be compared reliably enough for an XP update yet.'],
    comparison_inconsistent: ['Practice saved · XP unchanged', 'PathForge could not confirm a reliable comparison. Your practice is saved.'],
    authority_required: ['Practice saved · XP unchanged', 'XP needs a verified approach comparison for this problem. Your practice is saved.'],
  };
  if (reasons[saved.score_reason]) return reasons[saved.score_reason];
  if (saved.skill_updates_skipped) return ['Practice saved · XP unchanged', 'This analysis did not qualify for a rating update. Your practice is saved.'];
  return ['Practice saved', verdict.state === 'accepted' ? 'XP reflects eligible pattern comparisons, not a certificate of mastery.' : ''];
}
function patternRow(pattern, observed, unobserved) {
  const row = node('div', 'pattern-row');
  row.append(node('span', observed && !unobserved ? 'pattern-mark found' : 'pattern-mark', observed && !unobserved ? '✓' : '○'));
  row.append(node('span', '', label(pattern)));
  row.append(node('span', 'pattern-status', observed && !unobserved ? 'Found' : unobserved && !observed ? 'Not seen' : 'Unclear'));
  return row;
}
function renderAnalysis(data, snapshot) {
  $('activity').classList.add('hidden');
  $('analysis-result').classList.remove('hidden');
  $('problem-title').textContent = data.problem_info?.title || snapshot.title;
  $('difficulty').textContent = data.problem_info?.difficulty || '';
  const verdict = snapshot.verdict || { state: 'unknown', label: 'Not checked on LeetCode' };
  $('verdict').className = `verdict ${verdict.state}`;
  $('verdict-icon').textContent = verdict.state === 'accepted' ? '✓' : verdict.state === 'failed' ? '×' : '–';
  $('verdict-label').textContent = verdict.label;
  $('verdict-note').textContent = verdict.state === 'unknown' ? 'Submit this code on LeetCode to check correctness.' : 'Matches this code’s LeetCode submission.';
  const patterns = (data.ast?.detected_patterns || []).filter(pattern => pattern.detected !== false);
  $('pattern-heading').textContent = !patterns.length && verdict.state === 'accepted' ? 'Approach not recognized yet' : 'Patterns in your code';
  $('pattern-explanation').textContent = '';
  $('pattern-hint').classList.toggle('hidden', !patterns.length || state.patternHintSeen);
  $('detected-patterns').replaceChildren();
  for (const [index, pattern] of patterns.entries()) {
    const id = pattern.pattern_id || pattern.name;
    const pill = node('button', 'pattern-pill', `✓ ${label(id)}`);
    pill.type = 'button'; pill.setAttribute('aria-pressed', String(index === 0));
    pill.addEventListener('click', () => {
      for (const button of $('detected-patterns').querySelectorAll('button')) button.setAttribute('aria-pressed', String(button === pill));
      $('pattern-explanation').textContent = patternExplanation(id);
      if (!state.patternHintSeen) {
        state.patternHintSeen = true;
        $('pattern-hint').classList.add('hidden');
        browser.storage.local.set({ [PATTERN_HINT_KEY]: true }).catch(() => {});
      }
    });
    $('detected-patterns').append(pill);
    if (index === 0) $('pattern-explanation').textContent = patternExplanation(id);
  }
  if (!patterns.length) $('detected-patterns').append(node('p', 'muted', verdict.state === 'accepted'
    ? 'PathForge couldn’t identify a supported pattern in this accepted solution. This is a limit of the analysis.'
    : 'PathForge couldn’t identify a supported pattern in this code yet.'));
  const groups = Array.isArray(data.problem_info?.solution_groups) ? data.problem_info.solution_groups : [];
  const usable = group => group.review_state !== 'CONFLICT' && group.pattern_evidence_state !== 'UNAVAILABLE';
  const chosen = groups.find(group => usable(group) && group.pattern_evidence_state === 'ALL_OBSERVED') || groups.find(group => usable(group) && group.observed_patterns?.length) || groups[0];
  const comparison = $('comparison'); comparison.replaceChildren();
  $('comparison-details').classList.toggle('hidden', !chosen);
  if (chosen) {
    comparison.append(node('p', 'comparison-caption', `${!patterns.length ? 'Example approach:' : chosen.review_state === 'REVIEWED' ? 'Compared with' : 'Possible approach:'} ${chosen.name || 'Stored approach'}`));
    if (chosen.pattern_evidence_state === 'UNAVAILABLE' || chosen.review_state === 'CONFLICT') comparison.append(node('p', 'muted', 'This approach cannot be compared reliably yet.'));
    else for (const pattern of chosen.patterns || []) comparison.append(patternRow(pattern, chosen.observed_patterns?.includes(pattern), chosen.unobserved_patterns?.includes(pattern)));
    if (chosen.family_relation === 'ONE_OF') comparison.append(node('p', 'fine', 'One possible approach. Other approaches can also be valid.'));
  }
  const saved = data.persisted;
  const [note, explanation] = practiceFeedback(saved, verdict);
  $('saved-note').textContent = note;
  $('xp-detail').textContent = explanation;
  showLevelFeedback(data);
}
function showLevelFeedback(data) {
  if (data.persisted?.replayed || data.persisted?.skill_updates_skipped || state.snapshot?.verdict?.state !== 'accepted') return;
  const updates = (data.elo_updates || []).filter(update =>
    Number.isFinite(update.delta) && update.delta !== 0 &&
    Number.isInteger(update.level_before?.level) && Number.isInteger(update.level_after?.level) &&
    Number.isFinite(update.level_before.experience) && Number.isFinite(update.level_after.experience) &&
    update.level_before.experience !== update.level_after.experience &&
    Number.isFinite(update.level_before.progress_percent) && Number.isFinite(update.level_after.progress_percent) &&
    [update.level_before.progress_percent, update.level_after.progress_percent].every(value => value >= 0 && value <= 100));
  if (!updates.length) return;
  const feedback = $('level-feedback');
  feedback.className = 'level-feedback';
  feedback.append(node('p', 'reward-heading', updates.some(update => update.delta > 0) ? 'Pattern XP gained' : 'Pattern XP updated'));
  for (const update of updates) {
    const before = update.level_before, after = update.level_after;
    const row = node('div', 'level-update');
    const title = node('p', 'level-title', `${label(update.pattern_id)} · Level ${before.level}`);
    const gain = after.experience - before.experience;
    row.classList.toggle('xp-loss', gain < 0);
    title.append(node('span', gain > 0 ? 'xp-gain' : 'xp-change', `${gain > 0 ? '+' : ''}${Number(gain.toFixed(2))} XP`));
    const track = node('div', 'level-track');
    track.setAttribute('role', 'progressbar');
    track.setAttribute('aria-label', `${label(update.pattern_id)} level progress`);
    track.setAttribute('aria-valuemin', '0'); track.setAttribute('aria-valuemax', '100');
    track.setAttribute('aria-valuenow', String(after.progress_percent));
    track.setAttribute('aria-valuetext', `Level ${after.level}, ${after.into_level} of ${after.points_per_level} XP`);
    const fill = node('span', 'level-fill');
    fill.style.width = `${before.progress_percent}%`;
    const caption = node('p', 'level-caption', `${before.into_level} / ${before.points_per_level} XP toward level ${before.level + 1}`);
    track.append(fill); row.append(title, track, caption); feedback.append(row);
    levelTimers.push(setTimeout(() => { fill.style.width = `${after.level > before.level ? 100 : after.level < before.level ? 0 : after.progress_percent}%`; }, 80));
    levelTimers.push(setTimeout(() => {
      title.firstChild.textContent = `${label(update.pattern_id)} · Level ${after.level}${after.level > before.level ? ' reached' : ''}`;
      row.classList.toggle('level-reached', after.level > before.level);
      caption.textContent = `${after.into_level} / ${after.points_per_level} XP toward level ${after.level + 1}`;
      if (after.level !== before.level) {
        fill.style.transition = 'none'; fill.style.width = after.level > before.level ? '0%' : '100%';
        levelTimers.push(setTimeout(() => { fill.style.transition = ''; fill.style.width = `${after.progress_percent}%`; }, 50));
      }
    }, 1100));
  }
  feedback.style.height = `${feedback.scrollHeight}px`;
  $('xp-detail').textContent = updates.map(update => `${label(update.pattern_id)}: ${update.level_after.experience > update.level_before.experience ? '+' : ''}${Number((update.level_after.experience - update.level_before.experience).toFixed(2))} XP · Level ${update.level_after.level}`).join(' · ');
  levelTimers.push(setTimeout(() => feedback.classList.add('leaving'), 6000));
  levelTimers.push(setTimeout(() => feedback.classList.add('hidden'), 6400));
}
function safeProblemUrl(value) {
  if (typeof value !== 'string' || /[\x00-\x20\\]/.test(value)) return null;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && ['leetcode.com', 'www.leetcode.com'].includes(url.hostname) && !url.username && !url.password && !url.port && !url.search && !url.hash && /^\/problems\/[a-z0-9]+(?:-[a-z0-9]+)*\/?$/.test(url.pathname) ? url.href : null;
  } catch { return null; }
}
async function recommendations(data, snapshot, current) {
  const failed = snapshot.verdict?.state === 'failed';
  $('next-practice').classList.remove('hidden');
  $('recommendation-title').textContent = failed ? 'Keep working on this problem' : 'Next practice';
  $('recommendation-help').textContent = failed ? 'Fix your solution and submit again. Your XP is safe.' : '';
  $('recommendations').replaceChildren(node('p', 'muted', 'Finding your next step…'));
  $('retry-recommendations').classList.add('hidden');
  try {
    const body = { user_id: state.session.user_id, mode: 'companion', context_problem_slug: snapshot.slug,
      submission_status: snapshot.verdict?.state || 'unknown' };
    const result = await api('/recommend', { body });
    if (!current()) return;
    const recs = Array.isArray(result.recommendations) ? [...result.recommendations] : [];
    recs.sort((a, b) => Number(b.practice_kind === 'follow_up') - Number(a.practice_kind === 'follow_up'));
    $('recommendations').replaceChildren();
    const seen = new Set();
    let relatedCount = 0;
    const difficulties = ['Easy', 'Medium', 'Hard'];
    const maximum = Math.max(0, difficulties.indexOf(data.problem_info?.difficulty));
    for (const rec of recs) {
      const href = safeProblemUrl(rec.problem_url);
      if (!href || seen.has(href) || href.replace(/\/$/, '').endsWith(`/problems/${snapshot.slug}`)) continue;
      if (!difficulties.includes(rec.difficulty) || difficulties.indexOf(rec.difficulty) > maximum) continue;
      const shared = rec.reason_evidence?.anchor_url?.replace(/\/$/, '').endsWith(`/problems/${snapshot.slug}`) && rec.reason_evidence?.shared_topics?.length;
      const related = rec.practice_kind === 'follow_up' && shared;
      if (failed && !related) continue;
      seen.add(href);
      if (related) relatedCount++;
      const bubble = node('a', 'recommendation'); bubble.href = href; bubble.target = '_blank'; bubble.rel = 'noopener noreferrer';
      bubble.append(node('span', 'recommendation-kind', related ? 'Related practice' : 'Explore another topic'));
      bubble.append(node('span', 'recommendation-name', rec.title || 'Practice problem'));
      const topic = related ? rec.reason_evidence.shared_topics[0] : rec.topics?.[0];
      bubble.append(node('span', 'recommendation-meta', [rec.difficulty, topic ? `${related ? 'Same topic' : 'Topic'}: ${topic}` : null].filter(Boolean).join(' · ')));
      if (rec.reason) bubble.title = rec.reason;
      $('recommendations').append(bubble);
      if (seen.size === 3) break;
    }
    if (!relatedCount) $('recommendation-help').textContent = failed
      ? 'Fix and submit this solution again. No related question at this difficulty is available right now.'
      : seen.size ? 'No related question at this difficulty is available right now. These are other topics to explore.'
      : 'No suitable follow-up is available right now. Your practice is saved.';
    if (result.state === 'context_unavailable') $('recommendation-help').textContent = 'Related practice is not available for this problem in the catalog yet.';
    if (!seen.size && !failed) $('recommendations').append(node('p', 'muted', 'No more practice suggestions right now.'));
  } catch (error) {
    if (!current()) return;
    const needsUpdate = error.status === 422 && Array.isArray(error.detail) &&
      error.detail.some(issue => issue.loc?.[0] === 'body' && issue.loc?.[1] === 'mode');
    $('recommendations').replaceChildren(node('p', 'muted', needsUpdate
      ? 'Practice suggestions need a PathForge update.' : 'Suggestions couldn’t load.'));
    if (needsUpdate) $('recommendation-help').textContent = 'Your analysis is still available. Reopen the panel after the PathForge service has been updated.';
    else $('retry-recommendations').classList.remove('hidden');
  }
}
async function monitorEditor() {
  if (!state.verified || state.running || monitoringEditor || state.sourceTabId == null ||
      !(state.session?.practice_policy_version >= 2)) return;
  monitoringEditor = true;
  const snapshot = state.snapshot;
  const sourceId = state.sourceTabId;
  const account = state.accountVersion;
  let view = state.viewVersion;
  const current = () => state.verified && !state.running && account === state.accountVersion &&
    view === state.viewVersion && sourceId === state.sourceTabId;
  const invalidate = () => {
    if (!state.changed) {
      state.changed = true; view = ++state.viewVersion;
      for (const id of ['analysis-result', 'next-practice', 'level-feedback']) $(id).classList.add('hidden');
      $('saved-note').textContent = '';
    }
  };
  try {
    const tab = await browser.tabs.get(sourceId);
    if (!current() || !tab.active || tab.windowId !== state.windowId || !problemSlug(tab.url)) return;
    const latest = await capture(tab, false);
    if (!current()) return;
    if (latest.error) {
      if (snapshot) invalidate();
      captureFailure(latest);
      return;
    }
    $('watch-status').textContent = 'Checks after Submit';
    if (snapshot && latest.slug !== snapshot.slug) { await captureAndAnalyze(); return; }
    if (snapshot && latest.code !== snapshot.code) {
      invalidate();
      activity('Your solution changed', 'Submit or recheck to analyze your updated code.');
    } else if (!snapshot) {
      activity('Ready when you submit', 'Your submission will be checked automatically. Recheck for a draft preview.');
    }
    if (snapshot && state.changed && latest.code === snapshot.code) { await captureAndAnalyze(); return; }
    const source = `${sourceId}:${latest.slug}`;
    if (lastVerdictSource !== source) { lastVerdictSource = source; lastVerdictCheck = 0; }
    // Read submission status only for the active source, at most every ten
    // seconds. Typing never posts an analysis or starts problem preparation.
    if (Date.now() - lastVerdictCheck >= 10000) {
      lastVerdictCheck = Date.now();
      const submitted = await capture(tab);
      if (!current() || submitted.error) return;
      if (submitted.code === latest.code && submitted.slug === latest.slug && submitted.submissionId &&
          (!snapshot || state.changed || submitted.submissionId !== snapshot.submissionId ||
           submitted.verdict?.state !== snapshot.verdict?.state)) {
        await captureAndAnalyze();
      }
    }
  } catch { /* The source tab can be closed while the panel remains open. */ }
  finally { monitoringEditor = false; }
}
async function restoreSession(session) {
  const changedAccount = state.session != null && state.session.user_id !== session.user_id;
  const account = ++state.accountVersion;
  ++state.viewVersion;
  for (const controller of requests) controller.abort();
  state.running = false; state.queued = false; state.session = session; state.connecting = true; state.verified = false;
  if (changedAccount) state.checks = {};
  clearView(); renderAccount();
  try {
    const verified = await api('/auth/session', { session, timeout: 60000 });
    if (account !== state.accountVersion) return;
    if (validSession(verified) && verified.user_id === session.user_id) {
      state.session.practice_policy_version = verified.practice_policy_version;
      state.verified = true;
      await browser.storage.local.set({ [SETUP_KEY]: true });
    }
  } catch { /* The remembered opt-in can reconnect from the website during startup. */ }
  finally { if (account === state.accountVersion) { state.connecting = false; renderAccount(); } }
}
async function initialize() {
  if (!globalThis.browser?.runtime?.id || !browser.storage?.session) { message('Load this folder through Firefox’s Add-ons page to use PathForge.', 'error'); return; }
  state.windowId = (await browser.windows.getCurrent()).id;
  state.patternHintSeen = (await browser.storage.local.get(PATTERN_HINT_KEY))[PATTERN_HINT_KEY] === true;
  await browser.storage.local.remove(SESSION_KEY);
  await browser.storage.session.remove('pathforgeDraft');
  const saved = await browser.storage.session.get([SESSION_KEY, CACHE_KEY, `pathforgeSource:${state.windowId}`]);
  state.checks = saved[CACHE_KEY] || {}; state.sourceTabId = saved[`pathforgeSource:${state.windowId}`] ?? null;
  await sourceTab();
  $('progress-link').href = `${WEBSITE_BASE}/progress`;
  $('open-app').addEventListener('click', () => openWebsite().catch(error => message(error.message, 'error')));
  $('connect-account').addEventListener('click', () => connectAccount());
  $('reconnect').addEventListener('click', () => connectAccount());
  $('disconnect').addEventListener('click', () => disconnect());
  $('settings-toggle').addEventListener('click', () => { $('settings').classList.toggle('hidden'); $('settings-toggle').setAttribute('aria-expanded', String(!$('settings').classList.contains('hidden'))); });
  $('recheck').addEventListener('click', () => captureAndAnalyze());
  $('read-again').addEventListener('click', () => captureAndAnalyze());
  $('start-problem').addEventListener('click', () => browser.tabs.create({ url: 'https://leetcode.com/problems/two-sum/', windowId: state.windowId }));
  $('retry-analysis').addEventListener('click', () => captureAndAnalyze({ retry: true }));
  $('inspect-anyway').addEventListener('click', () => captureAndAnalyze({ codeOnly: true }));
  $('retry-recommendations').addEventListener('click', () => { if (state.snapshot) captureAndAnalyze(); });
  $('open-problem').addEventListener('click', async () => {
    const value = $('manual-problem').value.trim();
    const slug = problemSlug(value) || (/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value) ? value : '');
    if (!slug) { message('Enter a LeetCode problem URL or title slug.', 'error'); return; }
    await browser.tabs.create({ url: `https://leetcode.com/problems/${slug}/`, windowId: state.windowId });
  });
  const followTab = tab => {
    if (!state.verified || tab?.windowId !== state.windowId || !problemSlug(tab.url)) return;
    state.sourceTabId = tab.id; ++state.viewVersion;
    clearTimeout(navigationTimer);
    navigationTimer = setTimeout(() => captureAndAnalyze(), 350);
  };
  browser.tabs.onActivated.addListener(async info => { if (info.windowId === state.windowId) followTab(await browser.tabs.get(info.tabId).catch(() => null)); });
  browser.tabs.onUpdated.addListener((_id, change, tab) => { if (tab.active && (change.url || change.status === 'complete')) followTab(tab); });
  browser.storage.onChanged.addListener((changes, area) => {
    if (area !== 'session' || !changes[SESSION_KEY]) return;
    const next = changes[SESSION_KEY].newValue;
    if (!next && state.session) disconnect('Reconnect your PathForge account.', false);
    else if (next?.access_token && next.access_token !== state.session?.access_token && !state.connecting) {
      restoreSession(next).then(() => { if (state.verified) captureAndAnalyze(); });
    }
  });
  renderAccount();
  if (saved[SESSION_KEY]) await restoreSession(saved[SESSION_KEY]);
  if (state.verified) await captureAndAnalyze();
  else if ((await browser.storage.local.get(SETUP_KEY))[SETUP_KEY]) await connectAccount(true);
  state.booting = false; renderAccount();
  setInterval(monitorEditor, 1800);
}
initialize().catch(() => { state.booting = false; renderAccount(); message('Couldn’t start PathForge. Reload the extension and reopen it.', 'error'); });

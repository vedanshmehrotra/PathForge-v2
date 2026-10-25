// Serialized into LeetCode's MAIN world. No extension globals, cookies, or page tokens are returned.
async function readLeetCode(options = {}) {
  const match = location.pathname.match(/^\/problems\/([a-z0-9]+(?:-[a-z0-9]+)*)(?:\/|$)/);
  if (location.protocol !== 'https:' || !['leetcode.com', 'www.leetcode.com'].includes(location.hostname) || !match) return { error: 'NOT_A_PROBLEM' };
  const slug = match[1];
  const visible = element => {
    if (!element?.isConnected || element.closest('[aria-hidden="true"], [inert]')) return false;
    const bounds = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    return bounds.width > 0 && bounds.height > 0 && bounds.bottom > 0 && bounds.right > 0 &&
      bounds.top < innerHeight && bounds.left < innerWidth && style.visibility !== 'hidden' &&
      style.display !== 'none' && element.checkVisibility?.({ checkOpacity: true, checkVisibilityCSS: true }) !== false;
  };
  const roots = [...document.querySelectorAll('.monaco-editor')].filter(visible);
  const candidates = [];
  const addEditor = editor => {
    try {
      if (typeof editor?.getValue !== 'function' || typeof editor?.getModel !== 'function') return;
      const dom = editor.getDomNode?.();
      if (!visible(dom) || !roots.some(root => root === dom || root.contains(dom) || dom.contains(root))) return;
      const raw = editor.getRawOptions?.();
      const option = window.monaco?.editor?.EditorOption?.readOnly;
      if (raw?.readOnly === true || raw?.domReadOnly === true ||
          (option != null && editor.getOption?.(option) === true)) return;
      // Bind the complete model to a visible editor with an editable input.
      // Submission previews and unbound global models must never supply code.
      const inputs = [...dom.querySelectorAll('textarea.inputarea, [role="textbox"][contenteditable="true"]')];
      if (!inputs.some(input => !input.disabled && !input.readOnly && input.getAttribute('aria-readonly') !== 'true')) return;
      const model = editor.getModel();
      if (model) candidates.push({ model, read: () => editor.getValue(), language: model.getLanguageId?.() || '' });
    } catch { /* An editor may have been disposed during navigation. */ }
  };
  try {
    for (const editor of window.monaco?.editor?.getEditors?.() || []) addEditor(editor);
  } catch { /* Some LeetCode builds keep Monaco inside their React component. */ }

  // @monaco-editor/react stores its editor in a ref. Read that complete model,
  // rather than .view-lines, whose DOM contains only the visible viewport.
  if (!candidates.length) {
    const visited = new Set();
    for (const root of roots) {
      let element = root;
      for (let depth = 0; element && depth < 10; depth++, element = element.parentElement) {
        const key = Object.keys(element).find(name => name.startsWith('__reactFiber$'));
        let fiber = key ? element[key] : null;
        for (let level = 0; fiber && level < 30 && !visited.has(fiber); level++, fiber = fiber.return) {
          visited.add(fiber);
          const props = fiber.memoizedProps;
          addEditor(props?.editor);
          addEditor(props?.editorRef?.current);
          let hook = fiber.memoizedState;
          const hooks = new Set();
          for (let i = 0; hook && typeof hook === 'object' && i < 30 && !hooks.has(hook); i++, hook = hook.next) {
            hooks.add(hook);
            addEditor(hook.memoizedState?.current);
          }
        }
      }
    }
  }
  const unique = candidates.filter((item, index) => candidates.findIndex(other => other.model === item.model) === index);
  if (unique.length > 1) {
    const focused = unique.filter(item => item.model === window.monaco?.editor?.getEditors?.().find(editor => editor.hasTextFocus?.())?.getModel());
    if (focused.length === 1) unique.splice(0, unique.length, focused[0]);
  }
  const editor = unique.length === 1 ? unique[0] : null;
  const code = editor ? editor.read() : '';
  const language = editor?.language || '';
  const titleElement = [...document.querySelectorAll('a[href]')].find(anchor => {
    try { return new URL(anchor.href).pathname === `/problems/${slug}/` && /^\d+\./.test(anchor.textContent.trim()); } catch { return false; }
  });
  let title = titleElement?.textContent.trim().replace(/^\d+\.\s*/, '') || slug.replaceAll('-', ' ');
  if (!editor) return { error: unique.length > 1 ? 'AMBIGUOUS_EDITOR' : 'EDITOR_NOT_EDITABLE', slug, title };
  let verdict = { state: 'unknown', label: 'Not checked on LeetCode' };
  const normalize = value => String(value || '').replace(/\r\n/g, '\n').trim();
  const python = value => ['python', 'python3'].includes(String(value).toLowerCase());
  if (code && !python(language)) return { error: 'UNSUPPORTED_LANGUAGE', language, slug, title };
  const submissionId = location.pathname.match(/\/submissions\/(\d+)(?:\/|$)/)?.[1];
  let matchedSubmissionId = null;
  if (options.includeSubmission !== false && code) {
    const query = async (text, variables) => {
      const response = await fetch('/graphql/', { method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: text, variables }), signal: AbortSignal.timeout(5000) });
      if (!response.ok) return null;
      return (await response.json()).data;
    };
    try {
      let id = submissionId;
      if (!id) {
        const list = await query('query($questionSlug:String!){questionSubmissionList(questionSlug:$questionSlug,offset:0,limit:1){submissions{id}}}', { questionSlug: slug });
        id = list?.questionSubmissionList?.submissions?.[0]?.id;
      }
      if (id && /^\d+$/.test(String(id))) {
        const data = await query('query($submissionId:Int!){submissionDetails(submissionId:$submissionId){code statusCode lang{name} question{titleSlug title}}}', { submissionId: Number(id) });
        const submission = data?.submissionDetails;
        if (submission?.question?.titleSlug === slug && typeof submission.code === 'string') {
          const labels = { 10: 'Accepted on LeetCode', 11: 'Wrong answer on LeetCode', 12: 'Memory limit exceeded', 13: 'Output limit exceeded', 14: 'Time limit exceeded', 15: 'Runtime error on LeetCode', 20: 'Compile error on LeetCode' };
          if (python(submission.lang?.name) && normalize(submission.code) === normalize(code) && labels[submission.statusCode]) {
            matchedSubmissionId = String(id);
            verdict = { state: submission.statusCode === 10 ? 'accepted' : 'failed', label: labels[submission.statusCode] };
          }
          title = submission.question.title || title;
        }
      }
    } catch { /* Unavailable/private submissions leave correctness unknown. */ }
  }
  if (editor && editor.read() !== code) return { error: 'CODE_CHANGED', slug, title };
  if (!code.trim()) return { error: unique.length > 1 ? 'AMBIGUOUS_EDITOR' : 'EDITOR_UNAVAILABLE', slug, title };
  if (!python(language)) return { error: 'UNSUPPORTED_LANGUAGE', language, slug, title };
  const withoutDocstrings = code.replace(/("""|''')[\s\S]*?\1/g, '');
  const meaningful = withoutDocstrings.split('\n').map(line => line.trim()).filter(line => line && !line.startsWith('#') && !/^(?:(?:class |(?:async )?def ).*:\s*$|pass\s*$|\.\.\.\s*$)/.test(line));
  if (!meaningful.length) return { error: 'EMPTY_SOLUTION', slug, title };
  return { slug, title, code, language: 'python', source: 'editor', submissionId: matchedSubmissionId, verdict };
}

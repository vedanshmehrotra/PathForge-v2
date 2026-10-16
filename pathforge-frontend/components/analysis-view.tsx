'use client'

import { useEffect, useRef, useState } from 'react'
import { ArrowRight, Braces, Check, Cpu, Layers2, Play, Route, ScanLine, X } from 'lucide-react'
import { useAnalyzeCode, usePrepareProblem } from '@/hooks/useApi'
import { useAuth } from '@/auth/AuthProvider'
import { ExperimentalPanel } from '@/components/experimental-panel'
import { ApproachComparison, approachComparisonHeading } from '@/components/approach-comparison'
import { AnalysisEffects } from '@/components/analysis-effects'

export function AnalysisView() {
  const { profile } = useAuth()
  const [code, setCode] = useState('')
  const [problemInput, setProblemInput] = useState('')
  const lineNumbers = useRef<HTMLPreElement>(null)
  const [submittedInput, setSubmittedInput] = useState<{ code: string; problem: string; problemId: number | null } | null>(null)
  const { result: analysisResult, loading, error, errorCode, run } = useAnalyzeCode()
  const prep = usePrepareProblem()
  const needsPreparation = !!problemInput.trim() && !prep.result
  const resultIsCurrent = !submittedInput || (code === submittedInput.code &&
    problemInput.trim() === submittedInput.problem && (prep.result?.leetcode_id ?? null) === submittedInput.problemId)
  const result = resultIsCurrent ? analysisResult : null

  useEffect(() => {
    if (errorCode === 'PREPARATION_REQUIRED' || errorCode === 'GROUND_TRUTH_UNAVAILABLE') prep.clear()
  }, [errorCode, prep.clear])

  const handleRun = () => {
    if (profile && code.trim() && !needsPreparation && !prep.loading && !loading) {
      const req: Parameters<typeof run>[0] = { user_id: profile.user_id, code, language: 'python' }
      if (prep.result) req.problem = { leetcode_id: prep.result.leetcode_id }
      setSubmittedInput({ code, problem: problemInput.trim(), problemId: prep.result?.leetcode_id ?? null })
      run(req)
    }
  }
  const handleProblemInputChange = (val: string) => {
    if (val.trim() !== problemInput.trim()) prep.clear()
    setProblemInput(val)
  }
  const handlePrepare = () => {
    const val = problemInput.trim()
    if (val) prep.run(val)
  }
  const detectedPatterns = result?.ast?.detected_patterns as Array<{
    pattern_id?: string; name?: string; category?: string; confidence?: number; nodes?: number
  }> | undefined
  const matchResult = result?.match_result as (Record<string, unknown> & { reasoning_signals?: string[] }) | undefined
  const comparisonHeading = approachComparisonHeading(result?.problem_info?.solution_groups)

  return (
    <div className="workspace-page">
      <header className="flex flex-wrap items-end justify-between gap-5">
        <div className="page-intro">
          <p className="workspace-kicker flex items-center gap-2"><ScanLine className="size-4 text-mint" />Your analysis workbench</p>
          <h1 className="page-heading">Code Analysis</h1>
          <p className="page-description">Explore what your Python code expresses, and where the evidence stops.</p>
        </div>
        <span className="text-xs text-muted-foreground">Python · structural analysis</span>
      </header>

      <div aria-label="Analysis workflow" className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        <span className={`inline-flex items-center gap-2 ${prep.result ? 'text-mint' : ''}`}><span className={`size-1.5 rounded-full ${prep.result ? 'bg-mint' : 'bg-muted-foreground/40'}`} />{prep.result ? 'Problem prepared' : 'Problem optional'}</span><ArrowRight className="size-3" />
        <span className={`inline-flex items-center gap-2 ${code.trim() ? 'text-sky' : ''}`}><span className={`size-1.5 rounded-full ${code.trim() ? 'bg-sky' : 'bg-muted-foreground/40'}`} />Your code</span><ArrowRight className="size-3" />
        <span className={`inline-flex items-center gap-2 ${result ? 'text-mint' : ''}`}><span className={`size-1.5 rounded-full ${result ? 'bg-mint' : 'bg-muted-foreground/40'}`} />{loading ? 'Inspecting…' : 'Observations'}</span>
      </div>

      <section aria-labelledby="problem-label" className="border-y border-border py-4">
        <label id="problem-label" htmlFor="problem-id" className="text-sm font-medium">LeetCode problem <span className="font-normal text-muted-foreground">(optional)</span></label>
        <p id="problem-help" className="mt-1 text-xs text-muted-foreground">Prepare a problem to compare approaches. Leave this empty to inspect code patterns on their own.</p>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <input id="problem-id" aria-describedby="problem-help preparation-status" value={problemInput}
            onChange={event => handleProblemInputChange(event.target.value)}
            onKeyDown={event => { if (event.key === 'Enter') handlePrepare() }}
            placeholder="Enter a LeetCode problem ID, for example 1 or 209"
            spellCheck={false} className="min-h-11 min-w-0 flex-1 rounded-md border border-input bg-card px-3 text-sm" />
          {prep.result ? (
            <div className="flex items-center gap-2 text-sm">
              <Check className="size-4 text-success" /><span>{prep.result.title}</span>
              <button type="button" onClick={prep.clear} aria-label="Clear prepared problem" className="inline-flex size-11 items-center justify-center rounded-md hover:bg-secondary"><X className="size-4" /></button>
            </div>
          ) : (
            <button type="button" onClick={handlePrepare} disabled={!problemInput.trim() || prep.loading} className="action-secondary disabled:opacity-50">
              {prep.loading ? <Cpu className="size-4 animate-pulse" /> : <ScanLine className="size-4" />}
              {prep.loading ? 'Preparing…' : 'Prepare'}
            </button>
          )}
        </div>
        <p id="preparation-status" role="status" className="mt-2 text-sm text-muted-foreground">
          {needsPreparation && !prep.loading ? 'Prepare the entered problem before running analysis, or clear it for analysis without a problem.' : prep.result ? 'Problem prepared. You can now compare approach evidence.' : ''}
        </p>
        {prep.error && <p role="alert" className="mt-3 text-sm text-destructive">{prep.error} Review the problem ID and prepare again explicitly.</p>}
        {error && <p role="alert" className="mt-3 text-sm text-destructive">{error} Review the message before retrying.</p>}
      </section>

      {analysisResult && !resultIsCurrent && <p role="status" className="text-sm text-muted-foreground">Your inputs changed. Run analysis again to see observations for the current code and problem.</p>}

      {result && (
        <section id="analysis-summary" aria-labelledby="summary-heading" className="detail-enter flex flex-wrap items-start justify-between gap-5 border-l-2 border-l-sky pl-5">
          <div><h2 id="summary-heading" className="text-xl font-medium">Analysis result</h2>
            <p className="mt-1 text-sm font-medium">{comparisonHeading}</p>
            <p className="mt-1 text-xs text-muted-foreground">Pattern comparison, not a code-correctness verdict.</p></div>
          <AnalysisEffects result={result} />
        </section>
      )}

      <div className="grid min-w-0 items-start gap-5 lg:grid-cols-[1.2fr_1fr]">
        <section className="surface-panel overflow-hidden" aria-labelledby="code-label">
          <div className="panel-heading">
            <label id="code-label" htmlFor="solution-code" className="flex items-center gap-2 text-sm font-semibold"><Braces className="size-4 text-mint" />Python solution</label>
            <span className="font-mono text-[11px] text-muted-foreground">solution.py</span>
          </div>
          <div className="flex min-w-0 bg-background/40">
            <pre ref={lineNumbers} aria-hidden="true" className="max-h-[330px] w-11 shrink-0 overflow-hidden border-r border-border/60 py-5 pr-3 text-right font-mono text-[13px] leading-6 text-muted-foreground/50 lg:max-h-[400px]">{code.split('\n').map((_, index) => index + 1).join('\n')}</pre>
            <textarea id="solution-code" value={code} onChange={event => setCode(event.target.value)}
              onScroll={event => { if (lineNumbers.current) lineNumbers.current.scrollTop = event.currentTarget.scrollTop }}
              aria-describedby="editor-help" spellCheck={false} wrap="off" placeholder="Paste your Python solution here…"
              className="editor-input h-[330px] w-full min-w-0 resize-none overflow-auto bg-transparent px-4 py-5 font-mono text-[13px] leading-6 lg:h-[400px]" />
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-4 py-3">
            <span id="editor-help" className="text-[11px] text-muted-foreground">Code is inspected, not executed</span>
            <button type="button" onClick={handleRun}
              disabled={loading || !profile || !code.trim() || prep.loading || needsPreparation}
              className="action-primary">
              {loading ? <Cpu className="size-4 animate-pulse" /> : <Play className="size-4" />}
              {loading ? 'Analyzing…' : 'Run Analysis'}
            </button>
          </div>
        </section>
        <section id="approach-details" className="min-w-0 min-h-[420px] scroll-mt-20" aria-labelledby="comparison-heading" aria-busy={loading}>
          <div className="flex min-h-14 items-center justify-between gap-3 border-b border-border py-3"><h2 id="comparison-heading" className="section-title flex items-center gap-2"><Layers2 className="size-4 text-sky" />Approach Comparison</h2><span className="text-[11px] text-muted-foreground">{result ? 'Evidence ready' : loading ? 'Inspecting' : 'Awaiting code'}</span></div>
          <div className="py-5">
          {result ? (
            <>
              {result.problem_info?.title && <p className="mb-4 text-sm text-muted-foreground">{result.problem_info.title}</p>}
              <div className="mb-5"><h3 className="eyebrow mb-3 text-mint"><ScanLine className="size-3.5" />Detected in your code</h3><div className="flex flex-wrap gap-2">{detectedPatterns?.length ? detectedPatterns.map((pattern, index) => <span key={pattern.pattern_id ?? index} className="rounded-md border border-mint/20 bg-mint/5 px-2.5 py-1.5 text-xs text-mint">{pattern.name || pattern.pattern_id?.replace(/_/g, ' ')}</span>) : <p className="text-sm text-muted-foreground">No supported patterns observed.</p>}</div></div>
              <ApproachComparison groups={result.problem_info?.solution_groups} legacyPatterns={result.problem_info?.canonical_patterns} showSummary={false} />
            </>
          ) : loading ? (
            <div role="status" className="flex min-h-72 flex-col items-center justify-center gap-4 text-center"><ScanLine className="size-9 animate-pulse text-mint" /><p className="text-sm font-medium">Inspecting the structure of your code…</p><p className="max-w-xs text-xs text-muted-foreground">Observations will appear when analysis completes.</p></div>
          ) : (
            <div className="py-3">
              <div className="mb-6 flex items-center justify-center gap-3 py-7 text-muted-foreground" aria-hidden="true"><Braces className="size-7 text-mint" /><span className="h-px w-8 bg-border" /><ScanLine className="size-7 text-sky" /><span className="h-px w-8 bg-border" /><Route className="size-7 text-amber" /></div>
              <p className="text-base font-medium">Run analysis to see what the code expresses.</p>
              <div className="mt-5 space-y-4 text-xs text-muted-foreground"><p className="flex items-center gap-3"><span className="size-1.5 rounded-full bg-mint" />Observed patterns from your code</p><p className="flex items-center gap-3"><span className="size-1.5 rounded-full bg-sky" />Approach alignment with a prepared problem</p><p className="flex items-center gap-3"><span className="size-1.5 rounded-full bg-amber" />Clear limits when evidence is inconclusive</p></div>
              <p className="mt-6 border-t border-border pt-4 text-xs leading-relaxed text-muted-foreground">Alternative approaches are not a checklist you must satisfy.</p>
            </div>
          )}
          </div>
        </section>
      </div>

      {result && (
        <div className="space-y-5 border-t border-border pt-6">
          <details>
            <summary className="cursor-pointer text-sm font-medium">Detection evidence and recorded updates</summary>
            <p className="mt-3 text-sm text-muted-foreground">Confidence describes detector evidence, not the chance that your solution is correct.</p>
            <ul className="mt-4 divide-y divide-border text-sm">
              {detectedPatterns?.map((p, i) => (
                <li key={p.pattern_id ?? i} className="py-3">
                  <span>{p.name || p.pattern_id?.replace(/_/g, ' ')}</span>
                  {typeof p.confidence === 'number' && <span className="ml-3 text-muted-foreground">Detector confidence {Math.round(p.confidence * 100)}%</span>}
                  {typeof p.nodes === 'number' && <span className="ml-3 text-muted-foreground">{p.nodes} nodes</span>}
                </li>
              ))}
            </ul>
            {matchResult?.reasoning_signals?.length ? <ul className="mt-4 list-inside list-disc text-sm text-muted-foreground">{matchResult.reasoning_signals.map((signal, i) => <li key={i}>{signal}</li>)}</ul> : null}
            <h3 className="section-title mt-5">Recorded rating updates</h3>
            {!result.elo_updates?.length ? <p className="mt-2 text-sm text-muted-foreground">No skill updates were recorded for this analysis.</p> : result.elo_updates.map(update => (
              <p key={update.pattern_id} className="mt-2 text-sm">{update.pattern_id.replace(/_/g, ' ')}: {Math.round(update.elo_before)} → {Math.round(update.elo_after)}</p>
            ))}
          </details>
          <details>
            <summary className="cursor-pointer text-sm font-medium">Experimental evidence and developer details</summary>
            <div className="mt-4"><ExperimentalPanel shadowAnalysis={result.shadow_analysis} /></div>
          </details>
        </div>
      )}
    </div>
  )
}

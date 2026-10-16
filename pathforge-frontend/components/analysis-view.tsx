'use client'

import { useEffect, useState } from 'react'
import { Check, Cpu, Play, ScanLine, X } from 'lucide-react'
import { useAnalyzeCode, usePrepareProblem, useGapData } from '@/hooks/useApi'
import { useAuth } from '@/auth/AuthProvider'
import { ExperimentalPanel } from '@/components/experimental-panel'
import { ApproachComparison, approachComparisonHeading } from '@/components/approach-comparison'
import { mapShadowToDisplay } from '@/services/shadow-mapper'

export function AnalysisView() {
  const { profile } = useAuth()
  const [code, setCode] = useState('')
  const [problemInput, setProblemInput] = useState('')
  const [submittedInput, setSubmittedInput] = useState<{ code: string; problem: string; problemId: number | null } | null>(null)
  const { result: analysisResult, loading, error, errorCode, run } = useAnalyzeCode()
  const prep = usePrepareProblem()
  const { data: gapData } = useGapData(profile?.user_id ?? 0)
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
  const shadow = mapShadowToDisplay(result?.shadow_analysis)
  const comparisonHeading = approachComparisonHeading(result?.problem_info?.solution_groups)

  return (
    <div className="workspace-page">
      <header className="flex flex-wrap items-end justify-between gap-5">
        <div className="page-intro">
          <p className="workspace-kicker">Look at the structure</p>
          <h1 className="page-heading">Code Analysis</h1>
          <p className="page-description">Explore what your Python code expresses, and where the evidence stops.</p>
        </div>
        <button type="button" onClick={handleRun}
          disabled={loading || !profile || !code.trim() || prep.loading || needsPreparation}
          className="action-primary">
          {loading ? <Cpu className="size-4 animate-pulse" /> : <Play className="size-4" />}
          {loading ? 'Analyzing…' : 'Run Analysis'}
        </button>
      </header>

      <section aria-labelledby="problem-label" className="border-y border-border py-5">
        <label id="problem-label" htmlFor="problem-id" className="text-sm font-medium">LeetCode problem <span className="font-normal text-muted-foreground">(optional)</span></label>
        <p id="problem-help" className="mt-1 text-sm text-muted-foreground">Prepare a problem to compare approaches. Leave this empty to inspect code patterns on their own.</p>
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
        <section id="analysis-summary" aria-labelledby="summary-heading" className="border-l-2 border-primary pl-5">
          <h2 id="summary-heading" className="text-xl font-medium">What this analysis tells you</h2>
          <dl className="mt-4 space-y-3 text-sm leading-relaxed">
            <div><dt className="font-medium">Observed Code Patterns</dt><dd className="mt-1 text-muted-foreground">{detectedPatterns?.length ? detectedPatterns.map(p => p.name || p.pattern_id?.replace(/_/g, ' ')).filter(Boolean).join(', ') : 'No supported code patterns were observed. This may reflect detector coverage.'}</dd></div>
            <div><dt className="font-medium">Approach Comparison</dt><dd className="mt-1 text-muted-foreground">{comparisonHeading}. {result.problem_info ? 'Review the approach definitions and their limits below.' : 'No problem context was supplied.'}</dd></div>
            {shadow.visible && <div><dt className="font-medium">Experimental strategy evidence</dt><dd className="mt-1 text-muted-foreground">{shadow.status === 'likely_match' ? 'Observed strategy: ' + shadow.approaches.join(', ') + '.' : shadow.explanation}</dd></div>}
          </dl>
          <p className="mt-4 text-sm text-muted-foreground">These observations do not establish solution correctness, optimality, or a skill deficit.</p>
          <a href="#approach-details" className="text-link mt-3">Read the approach comparison</a>
        </section>
      )}

      <div className="grid min-w-0 gap-8 lg:grid-cols-[1.4fr_1fr]">
        <section className="min-w-0" aria-labelledby="code-label">
          <div className="mb-3 flex items-baseline justify-between gap-3">
            <label id="code-label" htmlFor="solution-code" className="section-title">Python solution</label>
            <span className="text-xs text-muted-foreground">Code is inspected, not executed</span>
          </div>
          <textarea id="solution-code" value={code} onChange={event => setCode(event.target.value)}
            spellCheck={false} placeholder="Paste your Python solution here…"
            className="min-h-[300px] w-full min-w-0 resize-y rounded-md border border-input bg-card p-4 font-mono text-sm leading-relaxed lg:min-h-[380px]" />
        </section>
        <section id="approach-details" className="min-w-0 scroll-mt-20" aria-labelledby="comparison-heading">
          <h2 id="comparison-heading" className="section-title mb-4">Approach Comparison</h2>
          {result ? (
            <>
              {result.problem_info?.title && <p className="mb-4 text-sm text-muted-foreground">{result.problem_info.title}</p>}
              <ApproachComparison groups={result.problem_info?.solution_groups} legacyPatterns={result.problem_info?.canonical_patterns} />
            </>
          ) : (
            <div className="border-t border-border pt-5">
              <p className="text-base leading-relaxed text-muted-foreground">Run analysis to see what the code expresses.</p>
              <p className="mt-3 text-sm text-muted-foreground">A prepared problem adds an approach comparison. Alternative approaches are not a checklist you must satisfy.</p>
            </div>
          )}
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
            {!!gapData?.gap_signals?.length && <p className="mt-4 text-sm text-muted-foreground">Stored history signals: {gapData.gap_signals.map(signal => signal.pattern_id.replace(/_/g, ' ')).join(', ')}. These signals are separate from the current code observations.</p>}
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

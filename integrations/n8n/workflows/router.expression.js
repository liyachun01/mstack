(() => {
  const input = $json;
  const errors = [];
  const fixed = {
    project_id: 'mcp-stack',
    repository: '/home/developer/workspace/mstack',
    execution_domain: 'ubuntu-devbox',
    index_scope: 'approved-three-file-projection',
    memory_writes: 'explicit-confirmation',
    pkm_sync: 'off'
  };
  const profiles = ['coding', 'documentation-research', 'pkm-personal'];
  const harnesses = ['codex-ide', 'deepseek-harness'];
  for (const name of Object.keys(fixed)) {
    if (input[name] !== fixed[name]) errors.push(name + ': unsupported or missing');
  }
  for (const name of ['session_id', 'task_id']) {
    if (typeof input[name] !== 'string' ||
        !/^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$/.test(input[name])) {
      errors.push(name + ': use 1-80 safe identifier characters');
    }
  }
  if (typeof input.task !== 'string' || input.task.trim().length === 0 ||
      input.task.length > 2000) errors.push('task: expected 1-2000 characters');
  if (!profiles.includes(input.task_profile)) errors.push('task_profile: unsupported or missing');
  if (!harnesses.includes(input.harness)) errors.push('harness: unsupported or missing');
  if (input.dry_run !== true) errors.push('dry_run: must be boolean true');
  for (const name of ['implementation_question', 'broader_relationships', 'durable_decisions']) {
    if (typeof input[name] !== 'boolean') errors.push(name + ': must be boolean');
  }
  const common = {
    contract_version: 1,
    dry_run: true,
    actions_executed: [],
    memory_writes: 'disabled',
    pkm_sync: 'off',
    automatic_indexing: false,
    model_calls: false,
    approval_granted: false,
    policy_is_authorization: false
  };
  if (errors.length) return {
    ...common, status: 'rejected', errors,
    context_candidates: [], deferred: [], next_actions: ['Correct input; rerun the manual preview.']
  };
  const candidates = [];
  const deferred = [];
  const sourceTask = input.task_profile === 'coding' ||
    (input.task_profile === 'documentation-research' && input.implementation_question);
  if (sourceTask) candidates.push({
    component: 'codegraph',
    route: '/mcp/codegraph',
    purpose: 'Scoped source structure, symbols and dependencies',
    scope: fixed.index_scope,
    next_step: 'context-read connection qualification',
    execution_requires_separate_approval: true
  });
  if (input.broader_relationships) {
    if (input.task_profile === 'pkm-personal') deferred.push({
      component: 'graphify', reason: 'No personal-document corpus has been approved or indexed.'
    });
    else candidates.push({
      component: 'graphify',
      route: '/mcp/graphify',
      purpose: 'Broader relationships only if the existing source corpus is relevant',
      scope: fixed.index_scope,
      relevance_check_required: true,
      next_step: 'context-read connection qualification',
      execution_requires_separate_approval: true
    });
  }
  if (input.durable_decisions || input.task_profile !== 'coding') deferred.push({
    component: 'basic-memory',
    reason: 'Connection and scoped text-search usage remain separately gated; no model is needed.'
  });
  return {
    ...common,
    status: 'preview',
    errors: [],
    project_id: input.project_id,
    session_id: input.session_id,
    task_id: input.task_id,
    task_profile: input.task_profile,
    harness: input.harness,
    scope: fixed.index_scope,
    context_candidates: candidates,
    deferred,
    limitations: [
      'Planning only; not harness or gateway access control.',
      'Both graph indexes are partial three-file source projections, not the whole repository.',
      'Index absence cannot prove source absence; verify relevance and freshness before future calls.',
      'No task text or unknown input fields are copied into this plan; upstream input may still be visible in n8n.'
    ],
    next_actions: [
      'Review profile and existing index relevance; use normal repository inspection now.',
      'Request separate qualification of a read-only context connection when useful.',
      'Do not interpret this preview, session ID or successful node execution as permission to call tools.'
    ]
  };
})()

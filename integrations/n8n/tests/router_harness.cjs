// Synthetic in-memory tests only. No n8n API, database, credential or workflow import.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

async function main() {
  const payload = JSON.parse(fs.readFileSync(0, 'utf8'));
  const installed = process.argv.includes('--installed');
  const node = payload.workflow.nodes.find(n => n.name === 'Route preview');
  const inputNode = payload.workflow.nodes.find(n => n.name === 'Task input');
  const splitNode = payload.workflow.nodes.find(n => n.name === 'Split tasks');
  const expression = node.parameters.jsonOutput;
  let Expression;
  let SetV2;
  let SplitOut;
  let engine = 'node-vm-offline';
  if (installed) {
    const base = '/usr/local/lib/node_modules/n8n';
    assert.equal(require(base + '/package.json').version, '2.41.6');
    ({ Expression } = require(base + '/node_modules/n8n-workflow'));
    ({ SetV2 } = require(base + '/node_modules/n8n-nodes-base/dist/nodes/Set/v2/SetV2.node.js'));
    ({ SplitOut } = require(base + '/node_modules/n8n-nodes-base/dist/nodes/Transform/SplitOut/SplitOut.node.js'));
    engine = process.env.N8N_EXPRESSION_ENGINE || 'vm';
    assert.ok(['legacy', 'vm'].includes(engine), 'unqualified expression engine');
    await Expression.initExpressionEngine({
      engine, poolSize: 1, maxCodeCacheSize: 128,
      bridgeTimeout: 1000, bridgeMemoryLimit: 32, lazyAcquire: false
    });
    assert.equal(Expression.getActiveImplementation(), engine);
  }
  async function evaluate(setNode, input) {
    if (!installed) {
      if (!setNode.parameters.jsonOutput.startsWith('=')) return JSON.parse(setNode.parameters.jsonOutput);
      return JSON.parse(JSON.stringify(vm.runInNewContext(payload.source, { $json: input }, { timeout: 1000 })));
    }
    const expr = new Expression('Asia/Shanghai');
    // The real installed Set node runs against a small in-memory execution context.
    // This is not an n8n saved execution or end-to-end editor qualification.
    const context = {
      getInputData: () => [{ json: input }],
      getNode: () => setNode,
      getNodeParameter: (name, index, fallback) => setNode.parameters[name] ?? fallback,
      getMode: () => 'manual',
      continueOnFail: () => false,
      evaluateExpression: value => expr.resolveSimpleParameterValue('=' + value, { $json: input }),
    };
    const result = await expr.withIsolate(() => new SetV2({}).execute.call(context));
    assert.equal(result.length, 1);
    assert.equal(result[0].length, 1);
    assert.equal(result[0][0].binary, undefined);
    return JSON.parse(JSON.stringify(result[0][0].json));
  }
  try {
    assert.equal(expression, '={{ ' + payload.source.trim() + ' }}', 'expression/source drift');
    const batch = await evaluate(inputNode, {});
    assert.deepEqual(batch, JSON.parse(inputNode.parameters.jsonOutput), 'Task input node output');
    let splitItems;
    if (installed) {
      const splitContext = {
        getInputData: () => [{ json: batch }],
        getNode: () => splitNode,
        getNodeParameter: (name, index, fallback) => splitNode.parameters[name] ?? fallback,
        addExecutionHints: () => {},
      };
      [splitItems] = await new SplitOut().execute.call(splitContext);
    } else {
      splitItems = batch.tasks.map(json => ({ json }));
    }
    assert.equal(splitItems.length, 4, 'one-click test count');
    const batchExpected = [
      { status: 'preview', candidates: ['codegraph', 'graphify'], deferred: [] },
      { status: 'preview', candidates: ['graphify'], deferred: ['basic-memory'] },
      { status: 'preview', candidates: [], deferred: ['graphify', 'basic-memory'] },
      { status: 'rejected', candidates: [], deferred: [] },
    ];
    for (let index = 0; index < splitItems.length; index++) {
      const result = await evaluate(node, splitItems[index].json);
      assert.equal(result.status, batchExpected[index].status, 'batch status ' + index);
      assert.deepEqual(result.context_candidates.map(x => x.component), batchExpected[index].candidates);
      assert.deepEqual(result.deferred.map(x => x.component), batchExpected[index].deferred);
      assert.deepEqual(result.actions_executed, []);
      assert.equal(result.approval_granted, false);
    }
    for (const test of payload.cases) {
      const result = await evaluate(node, test.input);
      assert.equal(result.status, test.status, test.name + ': status');
      assert.deepEqual(result.context_candidates.map(x => x.component), test.candidates, test.name + ': candidates');
      assert.deepEqual(result.deferred.map(x => x.component), test.deferred, test.name + ': deferred');
      assert.equal(result.approval_granted, false);
      assert.equal(result.policy_is_authorization, false);
      assert.equal(result.memory_writes, 'disabled');
      assert.equal(result.pkm_sync, 'off');
      assert.equal(result.automatic_indexing, false);
      assert.equal(result.model_calls, false);
      assert.deepEqual(result.actions_executed, []);
      assert.equal(result.task, undefined);
      assert.equal(result.password, undefined);
      assert.equal(result.access_token, undefined);
      assert.equal(result.harness_session_id, undefined);
      assert.ok(!JSON.stringify(result).includes('SYNTHETIC_PRIVATE_MARKER'));
      if (test.status === 'rejected') assert.ok(result.errors.length > 0);
      else assert.deepEqual(result.errors, []);
      if (test.input.task_profile === 'pkm-personal') {
        assert.ok(!result.context_candidates.some(x => x.component === 'codegraph'));
      }
    }
    console.log(JSON.stringify({ passed: payload.cases.length, batchPassed: splitItems.length, engine, installed,
      nodeVersion: node.typeVersion, imported: false, credentialsRead: false }));
  } finally {
    if (Expression) await Expression.disposeExpressionEngine();
  }
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });

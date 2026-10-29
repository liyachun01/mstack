// Synthetic data only. Scope checking belongs in a provider credential or adapter,
// not in a project label. This fixture demonstrates a fixed-scope adapter contract.
const counters = { a: 0, b: 0, blocked: 0 };
const sessions = new Map();
Bun.serve({port: 8000, hostname: '0.0.0.0', async fetch(req) {
  const path = new URL(req.url).pathname;
  if (path === '/stats') return Response.json(counters);
  const project = /^\/(a|b)\/mcp$/.exec(path)?.[1];
  if (!project) return new Response('', {status: 404});
  if (req.method === 'GET') return new Response('', {status:405});
  if (req.method === 'DELETE') {
    sessions.delete(req.headers.get('mcp-session-id'));
    return new Response('', {status:200});
  }
  const msg = await req.json();
  let session = req.headers.get('mcp-session-id');
  const headers = {};
  if (msg.method === 'initialize') {
    session = crypto.randomUUID(); sessions.set(session, project);
    headers['mcp-session-id'] = session;
  } else if (sessions.get(session) !== project) {
    return new Response('', {status:404});
  }
  if (!Object.hasOwn(msg, 'id')) return new Response('', {status:202});
  let result;
  switch (msg.method) {
    case 'initialize': result = {protocolVersion:'2025-11-25', capabilities:{tools:{},prompts:{},resources:{}}, serverInfo:{name:'synthetic-'+project,version:'1'}}; break;
    case 'ping': result = {}; break;
    case 'tools/list': result = {tools: ['read_channel','blocked'].map(name => ({name,description:'Synthetic fixture', inputSchema:{type:'object',properties:{channel_id:{type:'string'}},required:['channel_id'],additionalProperties:false}}))}; break;
    case 'tools/call': {
      const {name,arguments:args} = msg.params;
      if (name === 'blocked') {counters.blocked++; break;}
      if (name !== 'read_channel') return Response.json({jsonrpc:'2.0',id:msg.id,error:{code:-32601,message:'Unknown tool'}}, {headers});
      if (!args || Object.keys(args).length !== 1 || args.channel_id !== 'channel-'+project) {
        result = {isError:true,content:[{type:'text',text:'Scope denied'}]}; break;
      }
      counters[project]++;
      result = {content:[{type:'text',text:'synthetic project '+project}]}; break;
    }
    case 'prompts/list': result = {prompts:[{name:'blocked_prompt',description:'Hidden'}]}; break;
    case 'resources/list': result = {resources:[{uri:'synthetic://'+project+'/secret',name:'Hidden'}]}; break;
    case 'resources/templates/list': result = {resourceTemplates:[]}; break;
    default: return Response.json({jsonrpc:'2.0',id:msg.id,error:{code:-32601,message:'Unsupported'}}, {headers});
  }
  return Response.json({jsonrpc:'2.0',id:msg.id,result:result ?? {}}, {headers});
}});

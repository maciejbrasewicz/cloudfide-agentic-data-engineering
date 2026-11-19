import assert from "node:assert/strict";
import { test, before, after } from "node:test";
import { once } from "node:events";
import { createAppServer } from "./server.mjs";

let server, origin;
before(async()=>{
  server=createAppServer();
  server.listen(0,"127.0.0.1");
  await once(server,"listening");
  origin="http://127.0.0.1:"+server.address().port;
});
after(async()=>{if(server)await new Promise(r=>server.close(r));});

test("homepage is served with strict security headers",async()=>{
  const r=await fetch(origin+"/");
  assert.equal(r.status,200);
  assert.match(r.headers.get("content-type"),/text\/html/);
  assert.equal(r.headers.get("x-content-type-options"),"nosniff");
  assert.equal(r.headers.get("x-frame-options"),"DENY");
  assert.match(r.headers.get("content-security-policy"),/script-src 'self'/);
  assert.match(await r.text(),/Microsoft Foundry/);
});

test("recorded evidence is available and cannot be cached as live state",async()=>{
  const r=await fetch(origin+"/data/evidence.json");
  assert.equal(r.status,200);
  assert.equal(r.headers.get("cache-control"),"no-store");
  const data=await r.json();
  assert.equal(data.schemaVersion,1);
  assert.equal(data.agents.length,3);
  assert.equal(data.observability.traceStatus,"measured_tool_calls");
  const trace=await fetch(origin+"/data/agent_trace.json");
  assert.equal(trace.status,200);
  assert.equal((await trace.json()).toolCallCount,16);
});

test("client assets are served without requiring any dependency",async()=>{
  for(const path of ["/app.js","/technical.js","/delivery_status.js","/reviewer_console.js","/styles.css","/technical.css","/favicon.svg"]){
    const r=await fetch(origin+path);
    assert.equal(r.status,200);
    assert.ok((await r.text()).length>100);
  }
});

test("only read methods and published files are accessible",async()=>{
  assert.equal((await fetch(origin+"/package.json")).status,404);
  assert.equal((await fetch(origin+"/.env")).status,404);
  assert.equal((await fetch(origin+"/../../etc/passwd")).status,404);
  assert.equal((await fetch(origin+"/app.js",{method:"POST"})).status,405);
  assert.equal((await fetch(origin+"/data/evidence.json",{method:"HEAD"})).status,200);
});

test("real reviewer output is served from the verified Foundry run",async()=>{
  const r=await fetch(origin+"/data/foundry_reports.json");
  assert.equal(r.status,200);
  const reports=await r.json();
  assert.equal(reports.schemaVersion,1);
  assert.equal(reports.runId,"44331275568");
  assert.equal(reports.roles.length,3);
  assert.equal(reports.roles[2].findingCount,11);
  assert.match(reports.roles[2].originalSummary,/79 tests/);
});

test("single integrated site presents implementation and governed Foundry execution",async()=>{
  const response=await fetch(origin+"/?lang=pl");
  assert.equal(response.status,200);
  const html=await response.text();
  assert.match(html,/id="technical"/);
  assert.match(html,/id="technical-start-form"/);
  assert.match(html,/SequentialBuilder/);
  assert.match(html,/Microsoft Foundry/);
  assert.match(html,/id="delivery-evidence"/);
  assert.match(html,/id="reviewer-workspace"/);
  assert.match(html,/id="reviewer-recalculate"/);
  assert.doesNotMatch(html,/ChatGPT/i);
  assert.doesNotMatch(html,/engineering.html/);
});

test("verified real P1-P6 agent evidence is public and API launch is protected",async()=>{
  const page=await fetch(origin+"/data/autonomous_run.json");
  assert.equal(page.status,200);
  const record=await page.json();
  assert.equal(record.runId,44433630928);
  const latest=await (await fetch(origin+"/data/latest_autonomous_run.json")).json();
  assert.equal(latest.runId,44485096373);
  assert.equal(latest.sourceWorkflowConclusion,"success");
  assert.equal(latest.reference.ciCommitStatus,"success");
  assert.equal(record.stages.length,6);
  assert.equal(record.result.testPassed,18);
  const cap=await (await fetch(origin+"/api/delivery/launch/capabilities")).json();
  assert.equal(cap.liveReady,false);
  assert.equal((await fetch(origin+"/api/delivery/launch",{method:"POST"})).status,503);
  assert.equal((await fetch(origin+"/independent_oracle.mjs")).status,404);
});

test("old Engineering Lab bookmarks redirect to canonical single page",async()=>{
  for(const language of ["pl","en"]){
    const response=await fetch(origin+"/engineering.html?lang="+language,{redirect:"manual"});
    assert.equal(response.status,302);
    assert.equal(response.headers.get("location"),"/?lang="+language+"#technical");
  }
  assert.equal((await fetch(origin+"/engineering.js")).status,404);
  assert.equal((await fetch(origin+"/engineering.css")).status,404);
});

test("public portal cannot invoke arbitrary endpoints",async()=>{
  const r=await fetch(origin+"/api/live/start",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});
  assert.equal(r.status,503);
  assert.equal((await fetch(origin+"/.env")).status,404);
  assert.equal((await fetch(origin+"/live_gateway.mjs")).status,404);
});

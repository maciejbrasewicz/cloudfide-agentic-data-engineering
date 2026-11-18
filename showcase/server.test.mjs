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
  assert.match(await r.text(),/ENGINEERING INTELLIGENCE/);
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
  for(const path of ["/app.js","/styles.css","/favicon.svg"]){
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

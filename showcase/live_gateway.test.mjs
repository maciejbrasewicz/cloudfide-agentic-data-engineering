import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { once } from "node:events";
import { createAppServer } from "./server.mjs";
import { createLiveGateway } from "./live_gateway.mjs";

const FIXED_ID="d31f31a0-417e-4b78-9d74-19762212b001";
const CODE="test-reviewer-access-code-at-least-24-characters";
const BASE="https://engineering-intelligence-production-a972180f.up.railway.app";
const mockEnv={
  GITHUB_WORKFLOW_TOKEN:"test_token_which_is_at_least_32_characters",
  REVIEWER_ACCESS_CODE:CODE,
  PUBLIC_BASE_URL:BASE
};
const fakeFetch=async(url,options={})=>{
  if(url.includes("/dispatches")){
    assert.equal(options.method,"POST");
    const body=JSON.parse(options.body);
    assert.equal(body.ref,"main");
    assert.equal(body.inputs.live_request_id,FIXED_ID);
    assert(!options.body.includes(CODE));
    return new Response(null,{status:204});
  }
  if(url.includes("/workflows/agent-review.yml/runs?")){
    return Response.json({workflow_runs:[{
      id:9911,display_title:"Foundry review · "+FIXED_ID,
      head_branch:"main",event:"workflow_dispatch"
    }]});
  }
  if(url.endsWith("/actions/runs/9911")){
    return Response.json({
      id:9911,status:"in_progress",conclusion:null,created_at:"2026-11-18T16:00:00Z",
      html_url:"https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/9911"
    });
  }
  if(url.endsWith("/actions/runs/9911/jobs?per_page=100")){
    return Response.json({jobs:[{name:"review",status:"in_progress",conclusion:null,
      steps:[{name:"Three-agent Foundry analysis",status:"in_progress",conclusion:null}]}]});
  }
  throw Error("Unexpected request "+url);
};
let server,origin;
before(async()=>{
  const gateway=createLiveGateway({
    env:mockEnv,fetchImpl:fakeFetch,now:()=>1_800_000_000_000,uuid:()=>FIXED_ID
  });
  server=createAppServer({gateway});
  server.listen(0,"127.0.0.1");await once(server,"listening");
  origin="http://127.0.0.1:"+server.address().port;
});
after(async()=>{if(server)await new Promise(r=>server.close(r));});

const start=(value=CODE,headers={})=>fetch(origin+"/api/live/start",{
  method:"POST",
  headers:{"Content-Type":"application/json",...headers},
  body:JSON.stringify({accessCode:value})
});

test("live capability does not expose a GitHub credential",async()=>{
  const r=await fetch(origin+"/api/live/capabilities");
  assert.equal(r.status,200);
  assert.equal(r.headers.get("cache-control"),"no-store, private");
  const content=await r.json();
  assert.equal(content.liveReady,true);
  assert.equal(content.maxRunsPerDay,2);
  assert(!JSON.stringify(content).includes(mockEnv.GITHUB_WORKFLOW_TOKEN));
});

test("anonymous and cross-origin launch are rejected",async()=>{
  const wrong=await start("wrong-secret");
  assert.equal(wrong.status,401);
  const cross=await start(CODE,{Origin:"https://malicious.example"});
  assert.equal(cross.status,403);
});

test("a reviewer can dispatch exactly one bounded run and retrieve real GitHub steps",async()=>{
  const launch=await start();
  assert.equal(launch.status,202);
  const body=await launch.json();
  assert.equal(body.id,FIXED_ID);
  assert.equal(body.mode,"real_run");
  const update=await fetch(origin+body.pollUrl);
  assert.equal(update.status,200);
  const recorded=await update.json();
  assert.equal(recorded.status,"in_progress");
  assert.equal(recorded.githubRunUrl.endsWith("9911"),true);
  assert.equal(recorded.jobs[0].steps[0].name,"Three-agent Foundry analysis");
  assert.equal(recorded.events.length,0);
  assert.equal((await start()).status,429);
});

test("only signed GitHub Actions OIDC may publish reviewer events",async()=>{
  const response=await fetch(origin+"/api/live/events",{
    method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({
      request_id:FIXED_ID,
      event:{type:"agent.completed",at_utc:"2026-11-18T16:00:00Z",
        classification:"untrusted_model_output",
        payload:{role:"data_architect",summary:"This is untrusted model text",findings:1}}
    })
  });
  assert.equal(response.status,401);
  assert.equal((await response.json()).error,"untrusted_runner");
});

test("unpublished server files and arbitrary routes remain inaccessible",async()=>{
  assert.equal((await fetch(origin+"/live_gateway.mjs")).status,404);
  assert.equal((await fetch(origin+"/agentic/run.py")).status,404);
  assert.equal((await fetch(origin+"/api/live/internal")).status,404);
});

test("unconfigured gateway remains available only in recorded mode",async()=>{
  const app=createLiveGateway({env:{},fetchImpl:fakeFetch});
  const temp=createAppServer({gateway:app});
  temp.listen(0,"127.0.0.1");
  await once(temp,"listening");
  const root="http://127.0.0.1:"+temp.address().port;
  try{
    const cap=await (await fetch(root+"/api/live/capabilities")).json();
    assert.equal(cap.liveReady,false);
    assert.equal(cap.mode,"recorded_only");
    assert.equal((await fetch(root+"/api/live/start",{method:"POST"})).status,503);
  }finally{
    await new Promise(resolve=>temp.close(resolve));
  }
});

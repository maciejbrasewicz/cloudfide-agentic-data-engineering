import assert from "node:assert/strict";
import {test} from "node:test";
import {createDeliveryGateway} from "./delivery_gateway.mjs";

const SHA="a".repeat(40);
const run={
  id:44433630928,head_branch:"main",event:"push",status:"in_progress",
  conclusion:null,created_at:"2026-11-19T02:00:00Z",head_sha:SHA,
  display_title:"<script>alert('xss')</script>"
};
const jobs=[
  {name:"architect",status:"completed",conclusion:"success",modelOutput:"UNTRUSTED"},
  {name:"engineer",status:"completed",conclusion:"success"},
  {name:"sandbox-validate",status:"completed",conclusion:"success"},
  {name:"verifier",status:"queued",conclusion:null},
];

function fakeResponse(){
  return {
    code:null,headers:null,body:null,
    writeHead(code,headers){this.code=code;this.headers=headers;},
    end(body){this.body=body;},
  };
}
async function query(gateway,method="GET"){
  const res=fakeResponse();
  const handled=await gateway.handle({method},res,new URL("http://localhost/api/delivery/latest"));
  assert.equal(handled,true);
  return {res,data:res.body?JSON.parse(res.body):null};
}

test("Public latest status uses only real GitHub jobs and never model narratives",async()=>{
  const seen=[];
  const api=createDeliveryGateway({
    fetchImpl:async url=>{
      seen.push(url);
      if(url.includes("/workflows/"))return {ok:true,json:async()=>({workflow_runs:[run]})};
      if(url.includes("/jobs?"))return {ok:true,json:async()=>({jobs})};
      throw Error("Unexpected API URL");
    },
    now:()=>1_000_000,
  });
  const {res,data}=await query(api);
  assert.equal(res.code,200);
  assert.equal(res.headers["Cache-Control"],"no-store");
  assert.equal(data.source,"public_github_actions");
  assert.equal(data.run.id,run.id);
  assert.equal(data.run.url,"https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/44433630928");
  assert.equal(data.phases.find(x=>x.id==="architect").conclusion,"success");
  assert.equal(data.phases.find(x=>x.id==="verifier").status,"queued");
  assert.equal(data.phases.find(x=>x.id==="adversarial").status,"not_started");
  assert.doesNotMatch(JSON.stringify(data),/UNTRUSTED|alert|modelOutput/);
  assert.equal(seen.length,2);
});

test("Read-only and no network call for unsupported methods",async()=>{
  let calls=0;
  const api=createDeliveryGateway({fetchImpl:async()=>{calls++;throw Error("Should not fetch");}});
  const {res}=await query(api,"POST");
  assert.equal(res.code,405);
  assert.equal(calls,0);
});

test("HEAD returns no body and source stays public only",async()=>{
  const api=createDeliveryGateway({
    fetchImpl:async url=>({
      ok:true,
      json:async()=>url.includes("/workflows/")?{workflow_runs:[]}:{jobs:[]},
    })
  });
  const {res}=await query(api,"HEAD");
  assert.equal(res.code,200);
  assert.equal(res.body,undefined);
});

test("Refresh caches bounded public requests and marks temporary failures stale",async()=>{
  let clock=1_000_000;
  let calls=0;
  let fail=false;
  const api=createDeliveryGateway({
    now:()=>clock,
    fetchImpl:async url=>{
      calls++;
      if(fail)throw Error("GitHub network error");
      return {ok:true,json:async()=>
        url.includes("/workflows/")?{workflow_runs:[run]}:{jobs}
      };
    }
  });
  await query(api);
  await query(api);
  assert.equal(calls,2);
  clock+=61_000;
  fail=true;
  const stale=await query(api);
  assert.equal(stale.res.code,200);
  assert.equal(stale.data.stale,true);
  assert.equal(stale.data.warning,"temporary_github_api_failure");
  clock+=310_000;
  const unavailable=await query(api);
  assert.equal(unavailable.res.code,503);
  assert.equal(unavailable.data.available,false);
  assert.equal(unavailable.data.message,"github_evidence_unavailable");
});

test("No fetched jobs are synthesized into successful execution states",async()=>{
  const api=createDeliveryGateway({
    fetchImpl:async url=>({
      ok:true,json:async()=>url.includes("/workflows/")?
        {workflow_runs:[{...run,status:"completed",conclusion:"failure"}]}:
        {jobs:[]}
    }),
  });
  const {data}=await query(api);
  assert.equal(data.run.conclusion,"failure");
  assert.ok(data.phases.every(x=>x.status==="not_started"&&x.conclusion===null));
});

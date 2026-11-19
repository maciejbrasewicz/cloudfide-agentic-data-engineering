import assert from "node:assert/strict";
import test from "node:test";
import {acceptanceUuidFactory,dispatchAcceptanceOnce} from "./one_time_acceptance.mjs";

const id="40271848-13db-4b0b-a361-8d93c56853d5";
const token="github-token-not-real-but-long-enough";
const secret="reviewer-code-not-real-but-secret-and-long-enough";

test("acceptance is disabled unless the operator UUID exists",async()=>{
  const result=await dispatchAcceptanceOnce({
    env:{GITHUB_WORKFLOW_TOKEN:token,REVIEWER_ACCESS_CODE:secret},
    port:4173,
    fetchImpl:async()=>{throw Error("must not access network")},
  });
  assert.equal(result.status,"disabled");
});

test("fixed id is consumed once and normal reviewer UUIDs resume",()=>{
  const factory=acceptanceUuidFactory({CLOUDFIDE_REVIEWER_ACCEPTANCE_ID:id});
  assert.equal(factory(),id);
  const next=factory();
  assert.notEqual(next,id);
  assert.match(next,/^[a-f0-9-]{36}$/i);
});

test("existing matching run prevents a second POST or model expense",async()=>{
  const calls=[];
  const result=await dispatchAcceptanceOnce({
    env:{CLOUDFIDE_REVIEWER_ACCEPTANCE_ID:id,GITHUB_WORKFLOW_TOKEN:token,REVIEWER_ACCESS_CODE:secret},
    port:4173,fetchImpl:async(url,opts)=>{
      calls.push({url,opts});
      return {ok:true,json:async()=>({workflow_runs:[{
        id:123456,display_title:"CloudFide delivery · "+id,
      }]})};
    },
  });
  assert.equal(result.status,"already_exists");
  assert.equal(result.runId,123456);
  assert.equal(calls.length,1);
  assert.ok(!calls[0].url.includes(secret));
});

test("real protected HTTP POST is required and secrets never appear in source-bound logs",async()=>{
  const calls=[],logs=[];
  const env={CLOUDFIDE_REVIEWER_ACCEPTANCE_ID:id,GITHUB_WORKFLOW_TOKEN:token,REVIEWER_ACCESS_CODE:secret};
  const result=await dispatchAcceptanceOnce({
    env,port:4173,log:x=>logs.push(x),
    fetchImpl:async(url,options)=>{
      calls.push({url,options});
      if(calls.length===1)return {ok:true,json:async()=>({workflow_runs:[]})};
      return {status:202,json:async()=>({id,status:"dispatched",mode:"real_full_delivery"})};
    }
  });
  assert.equal(result.status,"accepted");
  assert.equal(calls.length,2);
  assert.equal(calls[1].url,"http://127.0.0.1:4173/api/delivery/launch");
  assert.equal(calls[1].options.method,"POST");
  assert.equal(JSON.parse(calls[1].options.body).accessCode,secret);
  assert.equal(calls[0].options.headers.Authorization,"Bearer "+token);
  assert.ok(!logs.join(" ").includes(secret));
  assert.ok(!logs.join(" ").includes(token));
});

test("GitHub permission or reviewer gateway rejection fails closed",async()=>{
  const env={CLOUDFIDE_REVIEWER_ACCEPTANCE_ID:id,GITHUB_WORKFLOW_TOKEN:token,REVIEWER_ACCESS_CODE:secret};
  await assert.rejects(
    dispatchAcceptanceOnce({env,port:4173,fetchImpl:async()=>({ok:false,status:403})}),
    /Could not verify existing acceptance execution/,
  );
});

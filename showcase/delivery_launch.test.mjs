import assert from "node:assert/strict";
import {test} from "node:test";
import {createFullDeliveryLauncher} from "./delivery_launch.mjs";

const ID="2ac3fd19-f652-474c-9fbb-4f8ca925d1e3";
const CODE="reviewer-private-code-with-32-chars";
const TOKEN="github-fine-grained-token-test-only";
const T=1_800_000_000_000;
const env={GITHUB_WORKFLOW_TOKEN:TOKEN,REVIEWER_ACCESS_CODE:CODE};
const request=(method,body="",origin=null)=>({
  method,headers:{host:"cloudfide.test",...(origin?{origin}:{})},
  socket:{remoteAddress:"127.0.0.1"},
  async *[Symbol.asyncIterator](){yield Buffer.from(body);}
});
const response=()=>({
  status:null,body:"",
  writeHead(status){this.status=status;},
  end(content){this.body=content||"";}
});
async function call(gateway,path,method="GET",value="",origin=null){
  const r=response();
  assert.equal(await gateway.handle(request(method,value,origin),r,new URL("https://cloudfide.test"+path)),true);
  return {status:r.status,body:JSON.parse(r.body)};
}

test("unconfigured deployment never exposes a public full agent launch",async()=>{
  const gateway=createFullDeliveryLauncher({env:{},fetchImpl:()=>{throw Error("Unexpected GitHub call");}});
  const cap=await call(gateway,"/api/delivery/launch/capabilities");
  assert.equal(cap.body.liveReady,false);
  assert.equal((await call(gateway,"/api/delivery/launch","POST",'{"accessCode":"abc"}')).status,503);
});

test("credentialed recruiter launches EXACT bounded main-branch workflow, never arbitrary command",async()=>{
  let dispatched=false,dispatchBody=null;
  const fetchImpl=async(url,options={})=>{
    if(url.includes("/dispatches")){
      dispatched=true;dispatchBody=JSON.parse(options.body);
      assert.equal(options.method,"POST");
      return new Response(null,{status:204});
    }
    if(url.includes("/runs?")){
      return Response.json({workflow_runs:dispatched?[{
        id:987654,display_title:"CloudFide delivery · "+ID,
        status:"in_progress",conclusion:null,created_at:new Date(T).toISOString()
      }]:[]});
    }
    if(url.endsWith("/runs/987654/jobs?per_page=100")){
      return Response.json({jobs:[{
        name:"architect",status:"completed",conclusion:"success",
        steps:[{name:"Check original specification",status:"completed",conclusion:"success"}]
      }]});
    }
    throw Error("Unexpected GitHub URL");
  };
  const gateway=createFullDeliveryLauncher({env,fetchImpl,now:()=>T,uuid:()=>ID});
  const capabilities=await call(gateway,"/api/delivery/launch/capabilities");
  assert.equal(capabilities.body.liveReady,true);
  assert.equal(capabilities.body.maxRunsPerDay,5);
  assert.equal(capabilities.body.maxConcurrentRuns,1);
  assert.equal(JSON.stringify(capabilities.body).includes(TOKEN),false);
  assert.equal((await call(gateway,"/api/delivery/launch","POST",'{"accessCode":"incorrect"}')).status,401);
  assert.equal((await call(gateway,"/api/delivery/launch","POST",JSON.stringify({accessCode:CODE}),"https://attacker.test")).status,403);
  const launched=await call(gateway,"/api/delivery/launch","POST",JSON.stringify({accessCode:CODE}));
  assert.equal(launched.status,202);
  assert.equal(dispatched,true);
  assert.deepEqual(dispatchBody,{
    ref:"main",inputs:{
      mode:"rebuild",max_rounds:"3",publish_draft_pr:"true",review_request_id:ID
    }
  });
  assert.equal((await call(gateway,launched.body.pollUrl)).body.jobs[0].name,"architect");
  assert.equal((await call(gateway,"/api/delivery/launch","POST",JSON.stringify({accessCode:CODE}))).status,429);
});

test("remote active or quota-exhausted workflows block new expensive runs",async()=>{
  let used=0;
  const gateway=createFullDeliveryLauncher({
    env,now:()=>T,uuid:()=>ID,
    fetchImpl:async()=>{
      used++;
      return Response.json({workflow_runs:[{
        id:66,display_title:"CloudFide delivery · previous",
        status:"in_progress",conclusion:null,created_at:new Date(T-1000).toISOString()
      }]});
    }
  });
  assert.equal((await call(gateway,"/api/delivery/launch","POST",JSON.stringify({accessCode:CODE}))).status,429);
  assert.equal(used,1);
});


test("five completed launches in a rolling day exhaust quota; four allow the fifth",async()=>{
  function history(count){
    return Array.from({length:count},(_,index)=>({
      id:1000+index,
      display_title:"CloudFide delivery · archived-"+index,
      event:"workflow_dispatch",status:"completed",conclusion:"success",
      created_at:new Date(T-(index+1)*3_600_000).toISOString()
    }));
  }
  for(const [existing,expected] of [[4,202],[5,429]]){
    let dispatchCount=0;
    const gateway=createFullDeliveryLauncher({
      env,now:()=>T,uuid:()=>ID,
      fetchImpl:async(url)=>{
        if(url.includes("/runs?"))return Response.json({workflow_runs:history(existing)});
        if(url.includes("/dispatches")){dispatchCount++;return new Response(null,{status:204});}
        throw Error("Unexpected GitHub URL");
      }
    });
    const outcome=await call(gateway,"/api/delivery/launch","POST",JSON.stringify({accessCode:CODE}));
    assert.equal(outcome.status,expected);
    assert.equal(dispatchCount,existing===4?1:0);
  }
});

test("older completed runs do not consume today's five-run allowance",async()=>{
  let dispatchCount=0;
  const gateway=createFullDeliveryLauncher({
    env,now:()=>T,uuid:()=>ID,
    fetchImpl:async(url)=>{
      if(url.includes("/runs?"))return Response.json({workflow_runs:[{
        id:123,event:"workflow_dispatch",status:"completed",conclusion:"success",
        created_at:new Date(T-26*3_600_000).toISOString()
      }]});
      if(url.includes("/dispatches")){dispatchCount++;return new Response(null,{status:204});}
      throw Error("Unexpected GitHub URL");
    }
  });
  assert.equal((await call(gateway,"/api/delivery/launch","POST",JSON.stringify({accessCode:CODE}))).status,202);
  assert.equal(dispatchCount,1);
});


test("accepted dispatch without a visible GitHub run is clearly awaiting confirmation, not silently pending",async()=>{
  const gateway=createFullDeliveryLauncher({
    env,now:()=>T,fetchImpl:async(url)=>{
      assert.match(url,/runs\?/);
      return Response.json({workflow_runs:[]});
    }
  });
  const status=await call(gateway,"/api/delivery/launch/session/"+ID);
  assert.equal(status.status,200);
  assert.equal(status.body.status,"awaiting_github_run");
  assert.equal(status.body.githubRunUrl,undefined);
  assert.equal(status.body.jobs.length,0);
  assert.equal(status.body.evidence,"github_run_not_yet_observed");
});

test("actual live GitHub jobs expose execution steps, original run link and NO credentials",async()=>{
  const gateway=createFullDeliveryLauncher({env,now:()=>T,fetchImpl:async(url)=>{
    if(url.includes("/runs?"))return Response.json({workflow_runs:[{
      id:12768,display_title:"CloudFide delivery · "+ID,
      status:"in_progress",conclusion:null,created_at:new Date(T-150000).toISOString()
    }]});
    if(url.includes("/jobs?"))return Response.json({jobs:[{
      name:"engineer",status:"in_progress",conclusion:null,
      html_url:"https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/12768/job/876",
      started_at:new Date(T-60000).toISOString(),
      steps:[{name:"Foundry Engineer writes REAL candidate source (never executes it)",
        status:"in_progress",conclusion:null,number:4}]
    }]});
    throw Error("Unexpected query "+url);
  }});
  const session=await call(gateway,"/api/delivery/launch/session/"+ID);
  assert.equal(session.body.status,"in_progress");
  assert.equal(session.body.githubRunId,12768);
  assert.equal(session.body.jobs[0].status,"in_progress");
  assert.match(session.body.jobs[0].steps[0].name,/Foundry Engineer/);
  assert.match(session.body.jobs[0].url,/\/job\/876$/);
  assert.equal(session.body.publication.status,"not_yet_available");
  assert.doesNotMatch(JSON.stringify(session.body),new RegExp(TOKEN+"|"+CODE));
});

test("successful P4 and publisher report the ACTUAL draft PR and exact-SHA CI; never require approval to create",async()=>{
  const sha="a".repeat(40);
  const gateway=createFullDeliveryLauncher({env,now:()=>T,fetchImpl:async(url)=>{
    if(url.includes("/runs?"))return Response.json({workflow_runs:[{
      id:12769,display_title:"CloudFide delivery · "+ID,
      status:"completed",conclusion:"success",created_at:new Date(T-300000).toISOString()
    }]});
    if(url.includes("/jobs?"))return Response.json({jobs:[
      {name:"Publish verified P4 candidate as human-reviewed draft PR (no Azure)",
        status:"completed",conclusion:"success",steps:[]},
      {name:"Final fail-closed P5/P4/P6 acceptance (never infer from green jobs alone)",
        status:"completed",conclusion:"success",steps:[]}
    ]});
    if(url.includes("/pulls?"))return Response.json([{
      number:48,draft:true,merged_at:null,
      head:{ref:"agentic-delivery/run-12769",sha},
      base:{ref:"main"}
    }]);
    if(url.includes("/commits/"))return Response.json({statuses:[{
      context:"agentic-delivery/isolated-candidate-ci",state:"success"
    }]});
    throw Error("Unexpected query "+url);
  }});
  const session=await call(gateway,"/api/delivery/launch/session/"+ID);
  assert.equal(session.body.publication.status,"verified_draft_awaiting_human");
  assert.equal(session.body.publication.pullRequest.number,48);
  assert.equal(session.body.publication.pullRequest.draft,true);
  assert.equal(session.body.publication.exactCi.state,"success");
});

test("draft PR with missing independent CI is visible but must not be marked verified",async()=>{
  const sha="a".repeat(40);
  const gateway=createFullDeliveryLauncher({env,now:()=>T,fetchImpl:async(url)=>{
    if(url.includes("/runs?"))return Response.json({workflow_runs:[{
      id:12770,display_title:"CloudFide delivery · "+ID,
      status:"completed",conclusion:"success",created_at:new Date(T-300000).toISOString()
    }]});
    if(url.includes("/jobs?"))return Response.json({jobs:[{
      name:"Publish verified P4 candidate as human-reviewed draft PR (no Azure)",
      status:"completed",conclusion:"success",steps:[]
    }]});
    if(url.includes("/pulls?"))return Response.json([{
      number:49,draft:true,merged_at:null,
      head:{ref:"agentic-delivery/run-12770",sha},base:{ref:"main"}
    }]);
    if(url.includes("/commits/"))return Response.json({statuses:[]});
    throw Error("Unexpected query "+url);
  }});
  const session=await call(gateway,"/api/delivery/launch/session/"+ID);
  assert.equal(session.body.publication.status,"draft_created");
  assert.equal(session.body.publication.exactCi.state,"not_reported");
});


test("any active GitHub main workflow run, including push, blocks reviewer dispatch until it completes",async()=>{
  let dispatched=0;
  const gateway=createFullDeliveryLauncher({
    env,now:()=>T,uuid:()=>ID,
    fetchImpl:async(url)=>{
      if(url.includes("/runs?"))return Response.json({workflow_runs:[{
        id:889,event:"push",status:"in_progress",conclusion:null,
        display_title:"One-time acceptance",created_at:new Date(T-60000).toISOString()
      }]});
      if(url.includes("/dispatches")){dispatched++;return new Response(null,{status:204});}
      throw Error("Unexpected GitHub URL");
    }
  });
  const result=await call(gateway,"/api/delivery/launch","POST",JSON.stringify({accessCode:CODE}));
  assert.equal(result.status,429);
  assert.equal(result.body.error,"daily_quota_or_active_execution");
  assert.equal(dispatched,0);
});

test("a historical push does not consume one of the five protected reviewer starts",async()=>{
  let dispatched=0;
  const gateway=createFullDeliveryLauncher({
    env,now:()=>T,uuid:()=>ID,
    fetchImpl:async(url)=>{
      if(url.includes("/runs?"))return Response.json({workflow_runs:[{
        id:889,event:"push",status:"completed",conclusion:"success",
        created_at:new Date(T-60000).toISOString()
      }]});
      if(url.includes("/dispatches")){dispatched++;return new Response(null,{status:204});}
      throw Error("Unexpected GitHub URL");
    }
  });
  const result=await call(gateway,"/api/delivery/launch","POST",JSON.stringify({accessCode:CODE}));
  assert.equal(result.status,202);
  assert.equal(dispatched,1);
});

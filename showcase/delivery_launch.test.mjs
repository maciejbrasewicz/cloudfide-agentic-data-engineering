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
      status:"completed",conclusion:"success",
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
        id:123,status:"completed",conclusion:"success",
        created_at:new Date(T-26*3_600_000).toISOString()
      }]});
      if(url.includes("/dispatches")){dispatchCount++;return new Response(null,{status:204});}
      throw Error("Unexpected GitHub URL");
    }
  });
  assert.equal((await call(gateway,"/api/delivery/launch","POST",JSON.stringify({accessCode:CODE}))).status,202);
  assert.equal(dispatchCount,1);
});

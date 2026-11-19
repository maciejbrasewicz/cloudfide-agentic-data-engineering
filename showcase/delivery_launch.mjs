/* Protected recruiter control for the CURRENT full 3-agent GitHub Actions workflow.
   No source writes, commands, Azure secrets, or unsigned runner events accepted here.
   GitHub Actions jobs and the verified draft PR remain the source of truth.
*/
import {randomUUID,timingSafeEqual} from "node:crypto";
const REPO="maciejbrasewicz/cloudfide-agentic-data-engineering";
const WORKFLOW="engineer-e2e.yml";
const REF="main";
const UUID=/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i;
const DAY_MS=86_400_000;
const MAX_RUNS_PER_DAY=5;
const MIN_LAUNCH_INTERVAL_MS=120_000;
const MAX_BODY=512;
const HEADERS={
  "Cache-Control":"no-store, private","Content-Type":"application/json; charset=utf-8",
  "X-Content-Type-Options":"nosniff","Referrer-Policy":"no-referrer",
  "Content-Security-Policy":"default-src 'none'; frame-ancestors 'none'"
};
function send(res,status,value){
  const body=JSON.stringify(value);
  res.writeHead(status,{...HEADERS,"Content-Length":String(Buffer.byteLength(body))});
  res.end(body);
}
function safeEqual(a,b){
  if(typeof a!=="string"||typeof b!=="string")return false;
  const x=Buffer.from(a),y=Buffer.from(b);
  return x.length===y.length&&timingSafeEqual(x,y);
}
async function bodyObject(req){
  let raw="";
  for await(const chunk of req){
    raw+=chunk.toString("utf8");
    if(Buffer.byteLength(raw)>MAX_BODY)throw Error("Large request body");
  }
  const value=JSON.parse(raw);
  if(!value||Array.isArray(value)||typeof value!=="object"||
      Object.keys(value).length!==1||typeof value.accessCode!=="string")throw Error("Invalid input");
  return value;
}
export function createFullDeliveryLauncher({env=process.env,fetchImpl=fetch,now=Date.now,uuid=randomUUID}={}){
  const token=env.GITHUB_WORKFLOW_TOKEN||"";
  const access=env.REVIEWER_ACCESS_CODE||"";
  const ready=token.length>=24&&access.length>=24;
  const recentAttempts=new Map();
  let lastDispatch=0;
  let pendingStart=false;
  const query=async(path,options={})=>{
    const response=await fetchImpl("https://api.github.com/repos/"+REPO+path,{
      ...options,signal:AbortSignal.timeout(9000),
      headers:{
        "Accept":"application/vnd.github+json",
        "Authorization":"Bearer "+token,
        "X-GitHub-Api-Version":"2022-11-28",
        "User-Agent":"CloudFide-Reviewer-Delivery",
        ...(options.headers||{})
      }
    });
    if(!response.ok)throw Error("GitHub request failed: "+response.status);
    return response.status===204?null:response.json();
  };
  // Draft PRs and exact-SHA statuses are public repository evidence. A
  // fine-grained Actions-only token can lack Pull Requests read permission.
  // Read publication evidence without using or exposing that token.
  const publicQuery=async(path)=>{
    const response=await fetchImpl("https://api.github.com/repos/"+REPO+path,{
      signal:AbortSignal.timeout(9000),
      headers:{
        "Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28",
        "User-Agent":"CloudFide-Reviewer-Public-Evidence"
      }
    });
    if(!response.ok)throw Error("Public GitHub evidence request failed: "+response.status);
    return response.json();
  };
  async function runs(){
    const result=await query("/actions/workflows/"+WORKFLOW+"/runs?branch="+REF+"&per_page=100");
    return Array.isArray(result.workflow_runs)?result.workflow_runs:[];
  }
  async function handle(req,res,url){
    if(!url.pathname.startsWith("/api/delivery/launch"))return false;
    const method=req.method||"GET";
    if(url.pathname==="/api/delivery/launch/capabilities"&&method==="GET"){
      send(res,200,{
        liveReady:ready,mode:ready?"protected_full_three_agent_delivery":"operator_setup_required",
        maxRunsPerDay:MAX_RUNS_PER_DAY,maxConcurrentRuns:1,workflow:WORKFLOW,
        execution:"real_github_actions_foundry",
        message:ready?"Reviewer code required; all runs are audited in GitHub":
          "Set GITHUB_WORKFLOW_TOKEN and REVIEWER_ACCESS_CODE on the Railway service"
      });
      return true;
    }
    if(url.pathname==="/api/delivery/launch"&&method==="POST"){
      if(!ready){send(res,503,{error:"full_delivery_not_provisioned"});return true;}
      const origin=req.headers.origin;
      if(origin){
        try{
          const source=new URL(origin);
          if(source.host!==req.headers.host||!["http:","https:"].includes(source.protocol))throw Error("Cross-origin");
        }catch{send(res,403,{error:"origin_not_allowed"});return true;}
      }
      const ip=req.socket?.remoteAddress||"unknown";
      const recent=(recentAttempts.get(ip)||[]).filter(x=>now()-x<3_600_000);
      recent.push(now());recentAttempts.set(ip,recent);
      if(recent.length>8){send(res,429,{error:"too_many_auth_attempts"});return true;}
      let input;
      try{input=await bodyObject(req);}catch{send(res,400,{error:"invalid_request"});return true;}
      if(!safeEqual(input.accessCode,access)){send(res,401,{error:"invalid_access_code"});return true;}
      if(pendingStart||now()-lastDispatch<MIN_LAUNCH_INTERVAL_MS){
        send(res,429,{error:"another_reviewer_execution_active_or_recent"});return true;
      }
      pendingStart=true;
      try{
        const history=await runs();
        // Same GitHub concurrency group includes push and manually dispatched runs.
        // A previous acceptance push can otherwise leave reviewer launches pending.
        const active=history.some(x=>x.status!=="completed");
        const daily=history.filter(x=>x.event==="workflow_dispatch"&&now()-Date.parse(x.created_at)<DAY_MS).length;
        if(active||daily>=MAX_RUNS_PER_DAY){
          send(res,429,{error:"daily_quota_or_active_execution"});return true;
        }
        const id=uuid();
        if(!UUID.test(id))throw Error("Invalid session generator");
        await query("/actions/workflows/"+WORKFLOW+"/dispatches",{
          method:"POST",headers:{"Content-Type":"application/json"},
          body:JSON.stringify({
            ref:REF,inputs:{
              mode:"rebuild",max_rounds:"3",publish_draft_pr:"true",
              review_request_id:id
            }
          })
        });
        lastDispatch=now();
        send(res,202,{id,status:"dispatched",mode:"real_full_delivery",submittedAt:new Date(now()).toISOString(),
          pollUrl:"/api/delivery/launch/session/"+id,
          workflowUrl:"https://github.com/"+REPO+"/actions/workflows/"+WORKFLOW});
      }catch{
        send(res,502,{error:"github_delivery_dispatch_failed"});
      }finally{pendingStart=false;}
      return true;
    }
    const m=/^\/api\/delivery\/launch\/session\/([0-9a-f-]{36})$/i.exec(url.pathname);
    if(m&&method==="GET"){
      if(!ready){send(res,503,{error:"full_delivery_not_provisioned"});return true;}
      if(!UUID.test(m[1])){send(res,400,{error:"invalid_request"});return true;}
      try{
        const history=await runs();
        const run=history.find(x=>x.display_title==="CloudFide delivery · "+m[1]);
        if(!run){
          // GitHub dispatch is asynchronous; 204 means accepted, not created.
          // Never fabricate job progress, but tell the reviewer what is known.
          send(res,200,{
            id:m[1],status:"awaiting_github_run",conclusion:null,
            workflowUrl:"https://github.com/"+REPO+"/actions/workflows/"+WORKFLOW,
            jobs:[],events:[],publication:{status:"not_yet_available",pullRequest:null,exactCi:null},
            evidence:"github_run_not_yet_observed"
          });
          return true;
        }
        const result=await query("/actions/runs/"+run.id+"/jobs?per_page=100");
        const jobs=(Array.isArray(result.jobs)?result.jobs:[]).map(x=>({
          name:String(x.name||"").slice(0,160),
          status:x.status,conclusion:x.conclusion,
          url:/^https:\/\/github\.com\/maciejbrasewicz\/cloudfide-agentic-data-engineering\/actions\/runs\/\d+\/job\/\d+$/.test(x.html_url||"")?x.html_url:null,
          startedAt:x.started_at||null,completedAt:x.completed_at||null,
          steps:(x.steps||[]).map(step=>({
            name:String(step.name||"").slice(0,160),
            status:step.status,conclusion:step.conclusion,number:step.number||null
          }))
        }));
        let publication={status:"not_yet_available",pullRequest:null,exactCi:null};
        if(jobs.some(j=>j.name==="Publish verified P4 candidate as human-reviewed draft PR (no Azure)"&&j.conclusion==="success")){
          try{
            const matches=await publicQuery("/pulls?state=all&head=maciejbrasewicz:agentic-delivery/run-"+run.id+"&per_page=10");
            const pr=(Array.isArray(matches)?matches:[]).find(x=>
              Number.isSafeInteger(x.number)&&x.head?.ref==="agentic-delivery/run-"+run.id&&
              x.base?.ref==="main"&&x.merged_at==null&&x.draft===true&&
              /^[0-9a-f]{40}$/.test(x.head?.sha||"")
            );
            if(pr){
              publication={
                status:"draft_created",pullRequest:{
                  number:pr.number,draft:true,headSha:pr.head.sha,
                  url:"https://github.com/"+REPO+"/pull/"+pr.number
                },exactCi:null
              };
              try{
                const checks=await publicQuery("/commits/"+pr.head.sha+"/status");
                const exact=(Array.isArray(checks.statuses)?checks.statuses:[]).find(x=>
                  x.context==="agentic-delivery/isolated-candidate-ci");
                const state=["success","pending","error","failure"].includes(exact?.state)?
                  exact.state:"not_reported";
                publication.exactCi={state,context:"agentic-delivery/isolated-candidate-ci"};
                if(state==="success"&&run.status==="completed"&&run.conclusion==="success"&&
                  jobs.some(j=>j.name.startsWith("Final fail-closed P5/P4/P6 acceptance")&&j.conclusion==="success")){
                  publication.status="verified_draft_awaiting_human";
                }
              }catch{publication.status="draft_ci_unavailable";}
            }
          }catch{publication.status="publication_check_unavailable";}
        }
        send(res,200,{
          id:m[1],mode:"real_full_delivery",status:run.status,
          conclusion:run.conclusion,githubRunId:run.id,
          githubRunUrl:"https://github.com/"+REPO+"/actions/runs/"+run.id,
          createdAt:run.created_at||null,updatedAt:run.updated_at||null,
          jobs,events:[],publication,
          evidence:"real_github_actions_jobs_no_simulation",
          note:"P4 must pass before automatic draft PR. Human approval is only required to merge the PR."
        });
      }catch{send(res,503,{error:"github_evidence_temporarily_unavailable"});}
      return true;
    }
    send(res,404,{error:"unknown_delivery_launch_route"});
    return true;
  }
  return {handle};
}

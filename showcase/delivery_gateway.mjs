/* Read-only public Github evidence for the SINGLE CloudFide engineering portal.

   Does not dispatch work, expose credentials, interpret model output as truth,
   or claim job-level success is equivalent to passing deterministic gates.
*/
const API="https://api.github.com/repos/maciejbrasewicz/cloudfide-agentic-data-engineering";
const WORKFLOW="engineer-e2e.yml";
const TTL_MS=180_000;
const MAX_STALE_MS=900_000;
const HEADER={
  "Cache-Control":"no-store",
  "Content-Type":"application/json; charset=utf-8",
  "X-Content-Type-Options":"nosniff",
  "Referrer-Policy":"no-referrer",
  "Content-Security-Policy":"default-src 'none'; frame-ancestors 'none'"
};
const PHASES=Object.freeze([
  ["architect","Data Architect","architect"],
  ["engineer","Data Engineer","engineer"],
  ["sandbox-validate","P3 Independent Sandbox","Verify P2 code inside no-network, no-secret Docker sandbox"],
  ["rework-r2","P5 Data Engineer / repair 2","Data Engineer repairs actual P3 failing tests (iteration 2)"],
  ["sandbox-rework-r2","P5 Sandbox / repair 2","Verify corrected P5 round-2 code in independent sandbox"],
  ["rework-r3","P5 Data Engineer / repair 3","Data Engineer third and final evidence-driven correction (iteration 3)"],
  ["sandbox-rework-r3","P5 Sandbox / repair 3","Verify final P5 round-3 candidate in independent sandbox"],
  ["p5-state","Deterministic Controller","Deterministic 3-round delivery state and strict evidence verification"],
  ["verifier","Verification Engineer","Independent Foundry Verification Engineer proposes real falsification test"],
  ["adversarial","P4 Independent Falsification","Execute Verifier test independently and prove mutation sensitivity"],
  ["publish-draft-pr","Draft PR / human review","Publish verified P4 candidate as human-reviewed draft PR (no Azure)"]
]);

function reply(res,status,value,head=false){
  const raw=JSON.stringify(value);
  const bytes=Buffer.byteLength(raw);
  res.writeHead(status,{...HEADER,"Content-Length":String(bytes)});
  res.end(head?undefined:raw);
}
function safeString(value,max=256){
  return typeof value==="string"?value.slice(0,max):null;
}
function cleanStatus(value){
  return ["queued","in_progress","completed","pending","waiting"].includes(value)?value:"unknown";
}
function cleanConclusion(value){
  return ["success","failure","skipped","cancelled","timed_out","action_required","neutral"].includes(value)?value:null;
}

export function createDeliveryGateway({fetchImpl=fetch,now=Date.now,token=process.env.GITHUB_WORKFLOW_TOKEN||""}={}){
  let cached=null;
  let cachedAt=0;
  let pending=null;

  async function githubJson(path){
    const response=await fetchImpl(API+path,{
      headers:{"Accept":"application/vnd.github+json","User-Agent":"cloudfide-public-delivery-evidence",...(token?{"Authorization":"Bearer "+token}:{})},
      signal:AbortSignal.timeout(7000)
    });
    if(!response.ok)throw Error("Public GitHub evidence API returned "+response.status);
    return response.json();
  }

  async function retrieve(){
    const runs=await githubJson("/actions/workflows/"+WORKFLOW+"/runs?per_page=6&branch=main");
    const run=(Array.isArray(runs.workflow_runs)?runs.workflow_runs:[]).find(x=>
      Number.isSafeInteger(x.id) && x.head_branch==="main" &&
      ["push","workflow_dispatch"].includes(x.event));
    if(!run)return {
      available:false,source:"public_github_actions",message:"no_confirmed_runs",
      observed_at:new Date(now()).toISOString(),
    };
    const jobs=await githubJson("/actions/runs/"+run.id+"/jobs?per_page=100");
    const found=new Map();
    for(const job of Array.isArray(jobs.jobs)?jobs.jobs:[]){
      if(!job||typeof job.name!=="string")continue;
      // Prefer the latest real attempt for jobs with repeated labels.
      found.set(job.name,job);
    }
    const phases=PHASES.map(([id,label,jobName])=>{
      const item=found.get(jobName);
      return {
        id,label,
        status:item?cleanStatus(item.status):"not_started",
        conclusion:item?cleanConclusion(item.conclusion):null,
      };
    });
    // Publication is verified only from the ACTUAL matching PR and exact-SHA
    // commit status, never from the agent's report or the publisher job alone.
    let publication={status:"not_yet_verified",pullRequest:null,exactCi:null};
    const publisher=phases.find(x=>x.id==="publish-draft-pr");
    if(run.status==="completed"&&run.conclusion==="success"&&publisher?.conclusion==="success"){
      try{
        const matching=await githubJson("/pulls?state=all&head=maciejbrasewicz:agentic-delivery/run-"+run.id+"&per_page=5");
        const pr=(Array.isArray(matching)?matching:[]).find(x=>
          Number.isSafeInteger(x.number)&&x.head?.ref==="agentic-delivery/run-"+run.id&&
          x.base?.ref==="main"&&x.merged_at==null);
        if(pr&&/^[a-f0-9]{40}$/.test(pr.head?.sha||"")){
          const status=await githubJson("/commits/"+pr.head.sha+"/status");
          const exact=(Array.isArray(status.statuses)?status.statuses:[]).find(x=>
            x.context==="agentic-delivery/isolated-candidate-ci");
          const ciState=["success","pending","failure","error"].includes(exact?.state)?exact.state:"not_reported";
          publication={
            status:pr.draft&&ciState==="success"?"verified_draft_awaiting_human":
              "draft_ci_not_confirmed",
            pullRequest:{number:pr.number,draft:pr.draft===true,state:safeString(pr.state,32),
              url:"https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/pull/"+pr.number,
              headSha:pr.head.sha},
            exactCi:{context:"agentic-delivery/isolated-candidate-ci",state:ciState}
          };
        }
      }catch{publication={status:"evidence_unavailable",pullRequest:null,exactCi:null};}
    }
    const commit=safeString(run.head_sha,40);
    const safeCommit=commit&&/^[a-f0-9]{40}$/.test(commit)?commit:null;
    return {
      available:true,
      source:"public_github_actions",
      observed_at:new Date(now()).toISOString(),
      stale:false,
      evidence_note:"job_status_only_check_run_artifacts_for_acceptance",
      run:{
        id:run.id,
        url:"https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/"+run.id,
        status:cleanStatus(run.status),
        conclusion:cleanConclusion(run.conclusion),
        event:run.event,
        created_at:safeString(run.created_at,40),
        commit_sha:safeCommit,
      },
      phases,
      publication,
    };
  }

  async function current(){
    const age=now()-cachedAt;
    if(cached&&age>=0&&age<TTL_MS)return cached;
    if(pending)return pending;
    pending=retrieve().then(value=>{
      cached=value;cachedAt=now();
      return value;
    }).catch(error=>{
      if(cached&&age>=0&&age<=MAX_STALE_MS){
        return {...cached,stale:true,warning:"temporary_github_api_failure"};
      }
      throw error;
    }).finally(()=>{pending=null;});
    return pending;
  }

  async function handle(req,res,url){
    if(url.pathname!=="/api/delivery/latest")return false;
    const method=req.method||"GET";
    if(!["GET","HEAD"].includes(method)){
      res.writeHead(405,{...HEADER,"Allow":"GET, HEAD"});
      res.end();return true;
    }
    try{reply(res,200,await current(),method==="HEAD");}
    catch{
      reply(res,503,{
        available:false,
        source:"public_github_actions",
        message:"github_evidence_unavailable",
        observed_at:new Date(now()).toISOString(),
      },method==="HEAD");
    }
    return true;
  }
  return {handle};
}

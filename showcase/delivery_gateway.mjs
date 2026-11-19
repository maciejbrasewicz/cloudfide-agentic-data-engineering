/* Read-only public Github evidence for the SINGLE CloudFide engineering portal.

   Does not dispatch work, expose credentials, interpret model output as truth,
   or claim job-level success is equivalent to passing deterministic gates.
*/
const API="https://api.github.com/repos/maciejbrasewicz/cloudfide-agentic-data-engineering";
const WORKFLOW="engineer-e2e.yml";
const TTL_MS=60_000;
const MAX_STALE_MS=300_000;
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
  ["sandbox-validate","P3 Independent Sandbox","sandbox-validate"],
  ["rework-r2","P5 Data Engineer / repair 2","rework-r2"],
  ["sandbox-rework-r2","P5 Sandbox / repair 2","sandbox-rework-r2"],
  ["rework-r3","P5 Data Engineer / repair 3","rework-r3"],
  ["sandbox-rework-r3","P5 Sandbox / repair 3","sandbox-rework-r3"],
  ["p5-state","Deterministic Controller","p5-state"],
  ["verifier","Verification Engineer","verifier"],
  ["adversarial","P4 Independent Falsification","adversarial"],
  ["publish-draft-pr","Draft PR / human review","publish-draft-pr"]
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

export function createDeliveryGateway({fetchImpl=fetch,now=Date.now}={}){
  let cached=null;
  let cachedAt=0;
  let pending=null;

  async function githubJson(path){
    const response=await fetchImpl(API+path,{
      headers:{"Accept":"application/vnd.github+json","User-Agent":"cloudfide-public-delivery-evidence"},
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

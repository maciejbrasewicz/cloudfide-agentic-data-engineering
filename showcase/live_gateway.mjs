/* Evidence-only live gateway: GitHub Actions dispatch + runner-verified event ingestion.
   No Azure secrets, workflow source changes, or arbitrary user commands. */
import { createPublicKey, randomUUID, timingSafeEqual, verify as verifySignature } from "node:crypto";

const REPOSITORY = "maciejbrasewicz/cloudfide-agentic-data-engineering";
const WORKFLOW_FILE = "agent-review.yml";
const REF = "main";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const TOOL_NAMES = new Set([
  "profile_source","inspect_orders","read_project_file","check_quality",
  "inspect_approved_policy","inspect_reconciliation"
]);
const ROLES = new Set(["data_architect","data_engineer","verification_engineer"]);
const ISSUER = "https://token.actions.githubusercontent.com";
const HEADER_BASE = {
  "Cache-Control":"no-store, private",
  "X-Content-Type-Options":"nosniff",
  "Referrer-Policy":"no-referrer",
  "Content-Security-Policy":"default-src 'none'; frame-ancestors 'none'"
};
const MAX_EVENTS = 120;
const DAY_MS = 86_400_000;
const HOUR_MS = 3_600_000;
const THROTTLE_MS = 30 * 60_000;
const OIDC_MAX_AGE_MS = 8 * 60_000;
const MAX_BODY = 6_000;

function reply(res,status,body){
  const text=JSON.stringify(body);
  res.writeHead(status,{"Content-Type":"application/json; charset=utf-8","Content-Length":Buffer.byteLength(text),...HEADER_BASE});
  res.end(text);
}

function eq(a,b){
  if(typeof a!=="string"||typeof b!=="string")return false;
  const left=Buffer.from(a),right=Buffer.from(b);
  return left.length===right.length && timingSafeEqual(left,right);
}

async function readJson(req){
  let text="";
  for await(const chunk of req){
    text+=chunk.toString("utf8");
    if(text.length>MAX_BODY)throw Error("Request body exceeds limit");
  }
  if(!text||req.headers["content-type"]?.split(";")[0]!=="application/json")throw Error("Expected JSON");
  return JSON.parse(text);
}

function runIsTerminal(s){return s==="completed"||s==="failed"||s==="cancelled";}

function validateEvent(obj){
  if(!obj||typeof obj!=="object"||Array.isArray(obj)||!["type","at_utc","payload","classification"].every(k=>Object.hasOwn(obj,k)))return false;
  if(Object.keys(obj).length!==4||Number.isNaN(Date.parse(obj.at_utc)))return false;
  if(!obj.payload||typeof obj.payload!=="object"||Array.isArray(obj.payload))return false;
  const spec = {
    "workflow.started":[],
    "tool.completed":["tool","duration_ms","status"],
    "agent.completed":["role","summary","findings"],
    "workflow.completed":["total_ms","tool_count"],
    "workflow.failed":["phase"]
  };
  if(!Object.hasOwn(spec,obj.type))return false;
  if(Object.keys(obj.payload).sort().join("|")!==[...spec[obj.type]].sort().join("|"))return false;
  const expected=obj.type==="agent.completed"?"untrusted_model_output":"measured_metadata";
  if(obj.classification!==expected)return false;
  const p=obj.payload;
  if(obj.type==="tool.completed"&&(!TOOL_NAMES.has(p.tool)||!["ok","error"].includes(p.status)||!Number.isFinite(p.duration_ms)||p.duration_ms<0||p.duration_ms>120000))return false;
  if(obj.type==="agent.completed"&&(!ROLES.has(p.role)||typeof p.summary!=="string"||p.summary.length<10||p.summary.length>1000||!Number.isInteger(p.findings)||p.findings<0||p.findings>12))return false;
  if(obj.type==="workflow.completed"&&(!Number.isFinite(p.total_ms)||p.total_ms<=0||!Number.isInteger(p.tool_count)||p.tool_count<0))return false;
  if(obj.type==="workflow.failed"&&!["foundry_review","schema_validation","provenance_gate"].includes(p.phase))return false;
  return true;
}

export function createLiveGateway({env=process.env,fetchImpl=fetch,now=Date.now,uuid=randomUUID}={}){
  const token=env.GITHUB_WORKFLOW_TOKEN||"";
  const accessCode=env.REVIEWER_ACCESS_CODE||"";
  const ready=token.length>=20 && accessCode.length>=20;
  const publicBase=(env.PUBLIC_BASE_URL||"https://engineering-intelligence-production-a972180f.up.railway.app").replace(/\/$/,"");
  const audience=publicBase+"/api/live/events";
  const sessions=new Map();
  const attempts=new Map();
  let lastDispatch=0;
  let dispatchDay="";
  let dispatchToday=0;
  let jwksCache=null;
  let jwksExpires=0;

  const githubHeaders={
    "Accept":"application/vnd.github+json",
    "Authorization":"Bearer "+token,
    "X-GitHub-Api-Version":"2026-03-10",
    "User-Agent":"cloudfide-engineering-lab"
  };
  async function githubRequest(path,options={}){
    const response=await fetchImpl("https://api.github.com/repos/"+REPOSITORY+path,{
      ...options,
      headers:{...githubHeaders,...(options.headers||{})},
      signal:AbortSignal.timeout(9000)
    });
    if(!response.ok)throw Error("GitHub API returned "+response.status);
    if(response.status===204)return null;
    return response.json();
  }
  async function getRun(session){
    if(!session.ghRunId){
      const listing=await githubRequest("/actions/workflows/"+WORKFLOW_FILE+"/runs?event=workflow_dispatch&branch="+REF+"&per_page=50");
      const found=(listing.workflow_runs||[]).find(x=>
        typeof x.display_title==="string"&&x.display_title.includes(session.id)&&
        x.head_branch===REF && x.event==="workflow_dispatch"
      );
      if(found)session.ghRunId=found.id;
    }
    if(!session.ghRunId)return null;
    const [run,jobs]=await Promise.all([
      githubRequest("/actions/runs/"+session.ghRunId),
      githubRequest("/actions/runs/"+session.ghRunId+"/jobs?per_page=100")
    ]);
    const cleanJobs=(jobs.jobs||[]).map(x=>({
      name:x.name,
      status:x.status,
      conclusion:x.conclusion,
      steps:(x.steps||[]).map(y=>({name:y.name,status:y.status,conclusion:y.conclusion}))
    }));
    session.run={id:run.id,status:run.status,conclusion:run.conclusion,html_url:run.html_url,created_at:run.created_at,jobs:cleanJobs};
    return session.run;
  }
  async function verifyOidc(jwt){
    if(typeof jwt!=="string"||jwt.length>15000||jwt.split(".").length!==3)throw Error("Invalid token format");
    const [a,b,c]=jwt.split(".");
    const header=JSON.parse(Buffer.from(a,"base64url").toString("utf8"));
    const claims=JSON.parse(Buffer.from(b,"base64url").toString("utf8"));
    if(header.alg!=="RS256"||typeof header.kid!=="string"||header.kid.length>128)throw Error("Invalid JWS header");
    const wall=now()/1000;
    if(claims.iss!==ISSUER||claims.aud!==audience||claims.repository!==REPOSITORY||
       claims.ref!=="refs/heads/main"||claims.event_name!=="workflow_dispatch"||
       typeof claims.workflow_ref!=="string"||
       claims.workflow_ref!==REPOSITORY+"/.github/workflows/"+WORKFLOW_FILE+"@refs/heads/main"||
       !Number.isInteger(claims.iat)||!Number.isInteger(claims.exp)||
       claims.iat>wall+60||claims.iat<wall-OIDC_MAX_AGE_MS/1000||
       claims.exp<wall-30||claims.exp>wall+700||
       !/^\d+$/.test(String(claims.run_id))){
      throw Error("OIDC identity did not match trusted workflow");
    }
    if(!jwksCache||jwksExpires<now()){
      const response=await fetchImpl(ISSUER+"/.well-known/jwks",{signal:AbortSignal.timeout(5000)});
      if(!response.ok)throw Error("Could not get trusted OIDC keys");
      jwksCache=await response.json();
      jwksExpires=now()+HOUR_MS;
    }
    const jwk=(jwksCache.keys||[]).find(key=>key.kid===header.kid&&key.kty==="RSA");
    if(!jwk)throw Error("Unrecognized OIDC signer");
    const key=createPublicKey({key:jwk,format:"jwk"});
    if(!verifySignature("RSA-SHA256",Buffer.from(a+"."+b),key,Buffer.from(c,"base64url")))throw Error("Bad OIDC signature");
    return claims;
  }

  function evict(){
    for(const [id,item] of sessions)if(now()-item.createdMs>DAY_MS)sessions.delete(id);
    for(const [key,item] of attempts)if(now()-item.start>HOUR_MS)attempts.delete(key);
  }

  async function handle(req,res,url){
    if(!url.pathname.startsWith("/api/live/"))return false;
    evict();
    const method=req.method||"GET";
    if(method==="GET"&&url.pathname==="/api/live/capabilities"){
      reply(res,200,{
        liveReady:ready,
        mode:ready?"protected_github_oidc_dispatch":"recorded_only",
        maxRunsPerDay:2,
        source:"github_actions_foundry",
        security:"human access code + dispatch quota + OIDC runner identity",
        message:ready?"A reviewer access code is required":"Live launch requires an operator-provisioned Actions token and reviewer access code"
      });
      return true;
    }
    if(method==="POST"&&url.pathname==="/api/live/start"){
      if(!ready){reply(res,503,{error:"live_not_provisioned"});return true;}
      if(req.headers.origin && req.headers.origin!==publicBase){reply(res,403,{error:"origin_not_allowed"});return true;}
      const ip=req.socket.remoteAddress||"unknown";
      let bucket=attempts.get(ip);
      if(!bucket||now()-bucket.start>HOUR_MS){bucket={start:now(),count:0};attempts.set(ip,bucket);}
      bucket.count++;
      if(bucket.count>8){reply(res,429,{error:"too_many_attempts"});return true;}
      let body;
      try{body=await readJson(req);}catch{reply(res,400,{error:"invalid_request"});return true;}
      if(Object.keys(body).join(",")!=="accessCode"||!eq(body.accessCode,accessCode)){
        reply(res,401,{error:"invalid_access_code"});return true;
      }
      const today=new Date(now()).toISOString().slice(0,10);
      if(dispatchDay!==today){dispatchDay=today;dispatchToday=0;}
      if(dispatchToday>=2||now()-lastDispatch<THROTTLE_MS||
        [...sessions.values()].some(x=>x.active)){
        reply(res,429,{error:"daily_limit_or_active_run"});return true;
      }
      const id=uuid();
      if(!UUID.test(id)){reply(res,500,{error:"invalid_id_generator"});return true;}
      const session={id,createdMs:now(),active:true,run:null,ghRunId:null,events:[]};
      // Reserve quota before calling GitHub to avoid concurrent dispatch races.
      lastDispatch=now();dispatchToday++;
      sessions.set(id,session);
      try{
        await githubRequest("/actions/workflows/"+WORKFLOW_FILE+"/dispatches",{
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({ref:REF,inputs:{live_request_id:id}})
        });
      }catch{
        sessions.delete(id);dispatchToday--;
        lastDispatch=0;
        reply(res,502,{error:"github_dispatch_failed"});return true;
      }
      reply(res,202,{id,mode:"real_run",status:"dispatched",pollUrl:"/api/live/session/"+id});
      return true;
    }
    const match=/^\/api\/live\/session\/([0-9a-f-]{36})$/i.exec(url.pathname);
    if(method==="GET"&&match){
      const session=sessions.get(match[1]);
      if(!session){reply(res,404,{error:"session_not_found_or_expired"});return true;}
      try{await getRun(session);}catch{ /* transport failures do not fabricate a run state */ }
      if(session.run&&runIsTerminal(session.run.status))session.active=false;
      reply(res,200,{
        id:session.id,
        mode:"real_run",
        status:session.run?.status||"dispatching",
        conclusion:session.run?.conclusion||null,
        githubRunUrl:session.run?.html_url||null,
        jobs:session.run?.jobs||[],
        events:session.events,
        receivedEventCount:session.events.length,
        authSource:"github_oidc_verified"
      });
      return true;
    }
    if(method==="POST"&&url.pathname==="/api/live/events"){
      let claims;
      try{
        const authorization=req.headers.authorization||"";
        if(!authorization.startsWith("Bearer "))throw Error("Missing token");
        claims=await verifyOidc(authorization.slice(7));
      }catch{reply(res,401,{error:"untrusted_runner"});return true;}
      let body;
      try{body=await readJson(req);}catch{reply(res,400,{error:"invalid_event"});return true;}
      if(!UUID.test(body.request_id||"")||!validateEvent(body.event)){
        reply(res,400,{error:"invalid_event_contract"});return true;
      }
      const session=sessions.get(body.request_id);
      if(!session||!session.active||session.events.length>=MAX_EVENTS){
        reply(res,404,{error:"session_not_active"});return true;
      }
      if(session.ghRunId&&String(session.ghRunId)!==String(claims.run_id)){
        reply(res,403,{error:"runner_mismatch"});return true;
      }
      session.ghRunId=Number(claims.run_id);
      const event={seq:session.events.length+1,...body.event};
      session.events.push(event);
      reply(res,202,{accepted:true,sequence:event.seq});
      return true;
    }
    reply(res,404,{error:"unknown_live_route"});
    return true;
  }
  return {handle};
}

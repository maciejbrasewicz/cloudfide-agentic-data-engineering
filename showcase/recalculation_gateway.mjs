/* Reviewer-triggered REAL read-only recalculation, not an agent simulation.
   Original CSV and published candidate output come from immutable Git commits.
   Every byte is SHA-256 verified before independent BigInt financial math.
*/
import {createHash} from "node:crypto";
import {independentRecalculation} from "./independent_oracle.mjs";

const REPO="maciejbrasewicz/cloudfide-agentic-data-engineering";
const BASE="393b847e5de31bdb288f02ecc3d429bb1507a2dc";
const CANDIDATE="287b9d82237e90b753991cd43f3ebd5a2e514a53";
const SOURCE_SHA="811573152aa287b14d5006ce6901ebd0ca17586149e16a5b79de5ae69684c1d4";
const OUTPUT_SHA="b3e59f4f4ec0ef3d0f172c69d3751eaf2fcbf0224266f0695ea2fb61b56fb29f";
const RAW_BASE="https://raw.githubusercontent.com/"+REPO+"/";
const OUTPUT_PATH="deliveries/run-44433630928/revenue_by_region.csv";
const CACHE_MS=120_000;
const HEADERS={
  "Cache-Control":"no-store",
  "Content-Type":"application/json; charset=utf-8",
  "X-Content-Type-Options":"nosniff",
  "Referrer-Policy":"no-referrer",
  "Content-Security-Policy":"default-src 'none'; frame-ancestors 'none'"
};
const sha=data=>createHash("sha256").update(data).digest("hex");

function reply(res,status,obj){
  const payload=JSON.stringify(obj);
  res.writeHead(status,{...HEADERS,"Content-Length":String(Buffer.byteLength(payload))});
  res.end(payload);
}
async function readBytes(fetchImpl,url,limit){
  const response=await fetchImpl(url,{signal:AbortSignal.timeout(9000),headers:{"User-Agent":"CloudFide-Independent-Reviewer-Oracle"}});
  if(!response.ok)throw Error("Immutable source fetch rejected: "+response.status);
  const length=Number(response.headers?.get?.("content-length"));
  if(Number.isFinite(length)&&length>limit)throw Error("Immutable source exceeds byte limit");
  const data=Buffer.from(await response.arrayBuffer());
  if(!data.length||data.length>limit)throw Error("Unexpected immutable source byte length");
  return data;
}

export function createRecalculationGateway({fetchImpl=fetch,now=Date.now}={}){
  let cached=null,cachedAt=0,pending=null;
  const attempts=new Map();
  async function calculate(){
    const [rawSource,rawOutput]=await Promise.all([
      readBytes(fetchImpl,RAW_BASE+BASE+"/sales.csv",200_000),
      readBytes(fetchImpl,RAW_BASE+CANDIDATE+"/"+OUTPUT_PATH,40_000)
    ]);
    const sourceHash=sha(rawSource),outputHash=sha(rawOutput);
    if(sourceHash!==SOURCE_SHA||outputHash!==OUTPUT_SHA)throw Error("Immutable published source SHA-256 mismatch");
    const actual=independentRecalculation(rawSource.toString("utf8"),rawOutput.toString("utf8"));
    return {
      ...actual,
      execution:"fresh_server_side_deterministic_recalculation",
      agentRunExecuted:false,
      sourceCommit:BASE,candidateCommit:CANDIDATE,
      sourceSha256:sourceHash,outputSha256:outputHash,
      verifiedAt:new Date(now()).toISOString(),
      referenceRunId:44433630928,
      evidenceUrl:"https://github.com/"+REPO+"/actions/runs/44478568225"
    };
  }
  async function current(){
    const age=now()-cachedAt;
    if(cached&&age>=0&&age<CACHE_MS)return {...cached,cached:true};
    if(pending)return pending;
    pending=calculate().then(x=>{cached=x;cachedAt=now();return {...x,cached:false};}).finally(()=>{pending=null;});
    return pending;
  }
  async function handle(req,res,url){
    if(url.pathname!=="/api/review/recalculate")return false;
    if(req.method!=="POST"){reply(res,405,{error:"post_required"});return true;}
    const origin=req.headers.origin;
    if(origin){
      try{
        const from=new URL(origin);
        if(from.host!==req.headers.host||!["https:","http:"].includes(from.protocol))throw Error("Cross origin");
      }catch{reply(res,403,{error:"cross_origin"});return true;}
    }
    const key=req.socket?.remoteAddress||"unknown";
    const recent=attempts.get(key)||[];
    const kept=recent.filter(t=>now()-t<60_000);
    if(kept.length>=6){reply(res,429,{error:"reviewer_rate_limit"});return true;}
    kept.push(now());attempts.set(key,kept);
    try{
      let length=0;
      for await(const chunk of req){length+=chunk.length;if(length>512)throw Error("Request too large");}
      const data=await current();
      reply(res,200,data);
    }catch{
      reply(res,503,{status:"UNAVAILABLE",error:"independent_recalculation_unavailable",
        message:"No successful computation is reported without immutable bytes and exact independent source reconciliation"});
    }
    return true;
  }
  return {handle};
}

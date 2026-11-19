/* One-time OPERATOR-CONTROLLED production acceptance of the protected live HTTP
   gateway. The UUID enables exactly one authorized acceptance execution.
   The server pulls its existing Railway-only secrets into an internal loopback
   POST. No credential or token is logged, returned or committed. This file
   will be removed immediately after an observed GitHub workflow_dispatch.
*/
import {randomUUID} from "node:crypto";

const REPO="maciejbrasewicz/cloudfide-agentic-data-engineering";
const WORKFLOW="engineer-e2e.yml";
const UUID=/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i;

export function acceptanceUuidFactory(env=process.env){
  const acceptanceId=env.CLOUDFIDE_REVIEWER_ACCEPTANCE_ID;
  let consumed=false;
  return ()=>{
    if(!consumed&&UUID.test(acceptanceId||"")){
      consumed=true;
      return acceptanceId;
    }
    return randomUUID();
  };
}

export async function dispatchAcceptanceOnce({
  env=process.env,port,fetchImpl=fetch,log=()=>{},
}={}){
  const id=env.CLOUDFIDE_REVIEWER_ACCEPTANCE_ID;
  if(!UUID.test(id||""))return {status:"disabled"};
  if(!env.GITHUB_WORKFLOW_TOKEN||!env.REVIEWER_ACCESS_CODE)
    throw Error("Reviewer gateway is not configured; no acceptance dispatch");

  // A stable UUID is bound to one exact workflow run for crash/restart recovery.
  // Never send the secret to GitHub or log it. Only the loopback auth route sees it.
  const remote=await fetchImpl(
    "https://api.github.com/repos/"+REPO+
    "/actions/workflows/"+WORKFLOW+"/runs?event=workflow_dispatch&branch=main&per_page=100",
    {headers:{
      Authorization:"Bearer "+env.GITHUB_WORKFLOW_TOKEN,
      Accept:"application/vnd.github+json",
      "X-GitHub-Api-Version":"2022-11-28",
      "User-Agent":"CloudFide-Acceptance",
    },signal:AbortSignal.timeout(15000)},
  );
  if(!remote.ok)throw Error("Could not verify existing acceptance execution");
  const existing=await remote.json();
  const prior=(existing.workflow_runs||[]).find(x=>
    x.display_title==="CloudFide delivery · "+id);
  if(prior){
    log("Acceptance already dispatched: GitHub run #"+prior.id);
    return {status:"already_exists",runId:prior.id};
  }
  const response=await fetchImpl("http://127.0.0.1:"+port+"/api/delivery/launch",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({accessCode:env.REVIEWER_ACCESS_CODE}),
    signal:AbortSignal.timeout(25000),
  });
  const body=await response.json();
  if(response.status!==202||body.id!==id||body.mode!=="real_full_delivery"){
    throw Error("Protected HTTP dispatcher rejected acceptance run: HTTP "+response.status+
      " / "+(body.error||"unexpected response"));
  }
  log("Protected real Railway HTTP POST accepted; GitHub workflow_dispatch correlation: "+id);
  return {status:"accepted",id};
}

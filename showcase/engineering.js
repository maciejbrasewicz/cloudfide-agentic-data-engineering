/* Engineering Lab: two independent evidence sources, one real launch path.
   Browser never sees a GitHub token or Azure credential. */
(() => {
"use strict";
const en={
 skip:"Skip to content",
 topDate:"Recorded execution / explicit trust boundaries",
 navResults:"Results presentation",navArchitecture:"Workflow",navInspector:"Inspector",navLive:"Run Foundry",
 navDecisions:"Decisions & code",sourceRun:"Original run ↗",
 introEyebrow:"Technical documentation / execution & provenance",
 introHeading:"How a human, ChatGPT and Microsoft Foundry engineered and verified the same solution.",
 introBody:"This is not a demonstration of four autonomous agents. The real responsibility chain was: a human set priorities and approved direction; ChatGPT designed and implemented changes; GitHub ran checks; and three specialist Microsoft Foundry reviewers audited the result. Inspect the original evidence, tool calls and boundaries.",
 seeArchitecture:"Explore the full process",seeLive:"Recruiter execution",
 processEyebrow:"RESPONSIBILITY MODEL",processTitle:"Two AI layers. One human decision-maker.",
 processLead:"ChatGPT designed the system with a human; three Foundry agents then reviewed that system. Different responsibilities, different permissions, different evidence.",
 legendHuman:"Human decisions",legendArchitect:"ChatGPT work",legendFoundry:"Foundry execution",legendTests:"Tests and gates",
 stage0Label:"HUMAN-IN-THE-LOOP / DECISION OWNER",
 stage0Title:"You: assignment requirements, scope and approvals",
 stage0Desc:"The human defined the task, challenged proposals, decided on fixes and approved the direction of work. This did not occur via an automated Foundry approval port in the historical run; approval happened in the interactive development process.",
 stage0Output:"Output",stage0OutputText:"Requirements and approved policy",
 processConnector1:"brief · plan · review",
 stage1Label:"CHATGPT / ARCHITECT & IMPLEMENTER",
 stage1Title:"Me: solution design, implementation, test suite, agents and infrastructure",
 stage1Desc:"ChatGPT developed the architecture, helped implement code, created reviewers, investigated CI results, and assisted with GitHub Actions and Azure OIDC deployment. It was an external engineering collaborator, not one of the three Foundry agents.",
 stage1Output:"Evidence",
 processConnector2:"code and contract → GitHub",
 stage2Title:"A controlled runner checks code and authenticates to Foundry",
 stage2Desc:"Windows and Ubuntu CI, artifact reconciliation and short-lived Azure OIDC federation. Azure credentials never enter the browser.",
 stage2Output:"Gates",
 processConnector3:"SequentialBuilder / gpt-5.6-sol",
 workerOne:"Audits source records, anomalies and unresolved business rules.",
 workerTwo:"Reviews implementation, contract conformance and tests.",
 workerThree:"Attempts to falsify correctness via independent arithmetic.",
 agentBoundary:"Security boundary: all three roles are read-only reviewers. They cannot overwrite source data or approve their own findings.",
 processConnector4:"Pydantic · manifest · decision proposals",
 stage4Label:"DETERMINISTIC EVIDENCE GATE",
 stage4Title:"Trust comes from data and tests, not LLM opinion",
 stage4Desc:"Pydantic/Pandera contracts, raw TOTAL checks, Decimal arithmetic, independent CSV oracle and artifact hashes support repeatability. Model decisions still require separate human approval.",
 stage4Output:"Output",
 noteOneHeading:"What is verified?",
 noteOne:"Three agents, sequential orchestration, real tool calls, Pydantic, GitHub OIDC and 79 tests in the recorded run.",
 noteTwoHeading:"What does it NOT claim?",
 noteTwo:"Historical code fixes were human-directed with ChatGPT assistance, not autonomous commits from the Foundry Engineer Agent.",
 inspectEyebrow:"RUN INSPECTOR / RECORDED",
 inspectTitle:"A real execution record, not a recreated conversation.",
 inspectLead:"GitHub Actions #44331275568. Sixteen measured tool calls and the model reports come from the authentic run. There is no simulated agent chat.",
 recordLabel:"Recorded execution · 18 Nov 2026",
 eventLabel:"Measured tool calls",agentLabel:"Completed reports",openRecorded:"Open original run ↗",
 eventList:"Function calls / relative time",reportList:"Agent reports",
 inspectorCaveat:"The historical tool events have no reliable role attribution. That run did not export complete Application Insights spans, tokens or model costs. We do not estimate missing figures.",
 liveEyebrow:"RECRUITER EXECUTION",liveTitle:"Run the real Foundry workflow.",
 liveLead:"The portal dispatches the existing GitHub Actions job. It displays real CI stages, tool events and model-written reports. OIDC proves which runner sent events; the browser has no Azure permissions.",
 liveStatus:"CONNECTION STATUS",liveChecking:"Checking configuration…",
 accessLabel:"Reviewer access code",launch:"Launch real workflow",
 liveSafety:"Maximum two runs per day, one active execution and a mandatory cool-down. Reviewers cannot change the code or auto-approve model conclusions.",
 visitActions:"View GitHub Actions ↗",
 guardOne:"Protected execution",
 guardOneDesc:"GitHub workflow_dispatch, bounded job and short-lived Azure Entra OIDC; no Azure key is ever sent to the site.",
 guardTwo:"Actual event stream",
 guardTwoDesc:"Runner OIDC tokens are verified cryptographically. Events contain metadata and clearly classified, untrusted model summaries.",
 guardThree:"Restricted exposure",
 guardThreeDesc:"No prompts, tool arguments, secrets, arbitrary code execution or automatic merges to main.",
 contractsEyebrow:"EVIDENCE AND CONTROLS",
 contractsTitle:"Contracts, decisions and code you can inspect.",
 contractsLead:"Layers remain separate: deterministic finance arithmetic, bounded agent permissions and human review of every new model decision.",
 decisionTitle:"The model proposes. A human approves.",
 decisionDesc:"DataDecision records the review role, target, evidence, risk and source-report hash. New model suggestions are written atomically as pending_human_review. LLM output cannot modify the approved data_policy.json.",
 roadmapEyebrow:"LIMITS AND NEXT STEPS",
 roadmapTitle:"What is verified — and what still needs credentials or further work?",
 roadmapLead:"No capability is marked as deployed until its actual tests or a Foundry execution support that conclusion.",
 footerText:"Human-in-the-loop · auditable agents · deterministic verification",
 footerBack:"← Return to results"
};
const originalPL={};
for(const node of document.querySelectorAll("[data-i18n]"))originalPL[node.dataset.i18n]=node.textContent;
let lang=new URLSearchParams(location.search).get("lang")==="en"?"en":"pl";
const $=(s,r=document)=>r.querySelector(s);
const $$=(s,r=document)=>[...r.querySelectorAll(s)];
const make=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=String(text);return e};
const tr=(pl,en)=>lang==="pl"?pl:en;
const nice=(v)=>new Intl.NumberFormat(lang==="pl"?"pl-PL":"en-US",{maximumFractionDigits:2}).format(v);
let evidence=null,trace=null,reports=null,activeReport="architect";
let activeSession=null,pollId=null;
function setLanguage(next){
 lang=next==="en"?"en":"pl";
 document.documentElement.lang=lang;
 for(const e of $$("[data-i18n]"))e.textContent=lang==="en"?(en[e.dataset.i18n]||originalPL[e.dataset.i18n]):originalPL[e.dataset.i18n];
 for(const b of $$("[data-lang]"))b.setAttribute("aria-pressed",String(b.dataset.lang===lang));
 const u=new URL(location.href);u.searchParams.set("lang",lang);
 history.replaceState(null,"",u.pathname+u.search+u.hash);
 const back=$(".nav a[href='./index.html']");
 if(back)back.href="./index.html?lang="+lang;
 const foot=$(".footer a[href='./index.html']");if(foot)foot.href="./index.html?lang="+lang;
 document.title=lang==="pl"?"CloudFide / Engineering Lab — rzeczywisty workflow":"CloudFide / Engineering Lab — real workflow";
 if(evidence&&trace&&reports)renderAll();
}
function verifyEvidence(){
 if(evidence.schemaVersion!==1||trace.schemaVersion!==1||reports.schemaVersion!==1)throw Error("Schema mismatch");
 if(evidence.provenance.reviewedCommit!==trace.reviewedCommit||
 evidence.provenance.reviewedCommit!==reports.reviewedCommit||
 evidence.provenance.sourceSha256!==trace.sourceSha256||
 reports.runId!==trace.githubRunId||trace.toolCallCount!==trace.events.length||
 trace.toolCallCount!==evidence.observability.toolSpanCount)throw Error("Run provenance mismatch");
 if(trace.otelTraceId!==null||trace.tokenUsage!==null||trace.estimatedCost!==null)throw Error("Unsupported telemetry claims");
}
const repo="https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering";
const files=[
 ["agentic/run.py","Foundry / sequential orchestrator","Real SequentialBuilder, three role-specific prompts and bounded tools."],
 ["agentic/tools.py","Bounded function tools","Allowlisted source inspection, file reading and fixed pytest subprocess."],
 ["agentic/models.py","Pydantic reviewer contracts","Strict structured findings and evidence-grounded decision proposals."],
 ["agentic/decision_ledger.py","DataDecision / approval boundary","Immutable linkage from each proposal to its reviewer report; human approval required."],
 ["dataframe_contracts.py","Pandera finance schema","Non-coercive validation of Decimal, columns and line revenue."],
 [".github/workflows/agent-review.yml","GitHub OIDC / workflow","Real Azure identity, cross-platform tests, evidence gate and artifacts."],
 ["pipeline.py","Deterministic ETL","Source control reconciliation, explicit normalization, Decimal line calculations."],
 ["agentic/telemetry.py","Measured tool calls","Monotonic timings without prompt or tool-argument capture."]
];
function safeURL(url){
 const u=new URL(url);
 if(u.protocol!=="https:"||u.hostname!=="github.com")throw Error("Non-GitHub evidence link");
 return u.href;
}
function drawArchitectureFiles(){
 const root=$("#technical-files");root.replaceChildren();
 for(const [path,heading,description] of files){
   const card=make("article","technical-file");
   const block=make("div","");
   block.append(make("small","",path),make("strong","",heading),make("p","",description));
   const link=make("a","","↗");
   link.href=safeURL(repo+"/blob/main/"+path);link.target="_blank";link.rel="noopener noreferrer";
   link.setAttribute("aria-label","Inspect "+path);
   card.append(block,link);root.append(card);
 }
 const items=$("#historical-decisions");items.replaceChildren();
 const keys=["D-001","D-002","D-003"];
 for(const key of keys){
   const d=evidence.decisions.find(x=>x.id===key);
   if(!d)continue;
   const card=make("div","decision-example");
   card.append(make("span","",d.id+" / "+d.status.toUpperCase()));
   const titles={
     "D-001":[ "Usuwanie identycznych linii","Remove exact duplicate lines"],
     "D-002":[ "Ostrożne odtwarzanie cen","Conservative price recovery"],
     "D-003":[ "Ujemne ilości jako zwroty","Negative quantities as returns"]
   };
   card.append(make("strong","",tr(...titles[key])),make("p","",d.risk));
   items.append(card);
 }
}
function drawRecordedTools(){
 const root=$("#recorded-tools");root.replaceChildren();
 const total=trace.wallDurationMs/1000;
 for(const e of trace.events){
  const row=make("div","measured-tool-row");
  row.append(make("code","",e.name+"()"));
  const track=make("span","time-track");
  const pin=make("span","time-pin");
  pin.style.left=Math.min(e.startSeconds/total*100,99)+"%";
  track.append(pin);
  row.append(track,make("small","",e.durationMs.toFixed(2)+" ms"));
  row.title=tr("Start +","Start +")+e.startSeconds.toFixed(3)+"s · "+e.status;
  root.append(row);
 }
}
const names={architect:"Data Architect",engineer:"Data Engineer",verifier:"Verification Engineer"};
function drawReports(){
 const tabs=$("#recorded-agent-tabs");tabs.replaceChildren();
 for(const x of reports.roles){
   const b=make("button","",names[x.id].split(" ")[0]);
   b.type="button";b.setAttribute("aria-selected",String(activeReport===x.id));
   b.addEventListener("click",()=>{activeReport=x.id;drawReports()});tabs.append(b);
 }
 const found=reports.roles.find(x=>x.id===activeReport);
 const box=$("#recorded-agent-report");box.replaceChildren();
 box.append(make("h3","",names[found.id]));
 box.append(make("p","",tr(
   "Oryginalny raport w języku angielskim. Nie zastępujemy go interpretacją strony.",
   "Original English output from the real Microsoft Foundry run."
 )));
 box.append(make("div","original-head",String(found.findingCount)+" "+tr("ustaleń / fragment oryginalnego JSON","findings / original JSON excerpt")));
 box.append(make("blockquote","",found.originalSummary));
 const sub=make("details","");sub.append(make("summary","",tr("Wybrane ustalenia i zalecenie agenta","Selected findings and original recommendation")));
 const ul=make("ul","");for(const f of found.selectedFindings)ul.append(make("li","",f));sub.append(ul);
 sub.append(make("p","",found.originalRecommendedNextAction));
 box.append(sub);
 const source=make("a","",tr("Zobacz pełny oryginalny artefakt ↗","View original run artifact ↗"));
 source.href=safeURL(reports.runUrl);source.target="_blank";source.rel="noopener noreferrer";box.append(source);
}
function drawRoadmap(){
 const items=[
 ["Pandera DataFrame schema","pandera",true],
 ["Human-gated DataDecision","decision_ledger",true],
 ["Real 16-tool telemetry (recorded)","telemetry",true],
 ["GitHub OAuth / one-click public launch","launch",false],
 ["GitHub MCP inside agent workflow","github_mcp",false],
 ["Autonomous branch-only coding agent","coding",false],
 ["Application Insights exporter connected","appinsights",false],
 ["Per-agent tokens and billable costs measured","usage",false]
 ];
 const root=$("#technical-roadmap");root.replaceChildren();
 for(const [text,id,done] of items){
   const row=make("article","roadmap-row "+(done?"":"pending"));
   row.append(make("span","",done?"✓":"○"));
   const body=make("div","");
   const namesPL={pandera:"Pandera: walidacja DataFrame",decision_ledger:"DataDecision: propozycje do akceptacji",
     telemetry:"Telemetria: 16 zmierzonych wywołań",launch:"Publiczny start po podłączeniu tokenu GitHub",
     github_mcp:"GitHub MCP w narzędziach agentów",coding:"Agent programujący na osobnej gałęzi",
     appinsights:"Aktywny eksport Application Insights",usage:"Tokeny, koszt i czas każdego agenta"};
   body.append(make("strong","",tr(namesPL[id]||text,text)));
   body.append(make("small","",done?tr("Kod wdrożony; wymaga potwierdzenia w docelowym przebiegu","Implemented in code; requires verification on live run"):tr("Nie oznaczamy jako uruchomione","Not yet proven live")));
   row.append(body);root.append(row);
 }
}
function renderAll(){drawRecordedTools();drawReports();drawArchitectureFiles();drawRoadmap();}
function liveError(key){
 const map={
  invalid_access_code:["Nieprawidłowy kod dostępu.","Invalid access code."],
  daily_limit_or_active_run:["Limit dwóch uruchomień na dzień lub aktywny przebieg.","Daily quota or an active run prevents another launch."],
  github_dispatch_failed:["GitHub odrzucił zlecenie. Sprawdź uprawnienia Actions.","GitHub rejected the dispatch. Check Actions permissions."],
  live_not_provisioned:["Brak skonfigurowanego tokenu GitHub lub kodu recenzenta.","GitHub dispatch token or recruiter code has not been provisioned."],
  too_many_attempts:["Limit prób logowania został przekroczony.","Too many access attempts."],
  session_not_found_or_expired:["Sesja wygasła lub usługa została ponownie uruchomiona.","Session expired or the service restarted."]
 };
 return tr(...(map[key]||["Nie udało się uruchomić procesu. Sprawdź GitHub Actions.","Could not start. Check GitHub Actions."]));
}
async function loadLiveCapabilities(){
 try{
   const response=await fetch("/api/live/capabilities",{cache:"no-store"});
   if(!response.ok)throw Error("Unreachable");
   const cap=await response.json();
   $("#live-state").textContent=cap.liveReady?tr("Gotowy do uruchomienia","Ready for verified execution"):tr("Tryb odtworzonego przebiegu","Recorded-run mode only");
   $("#live-message").textContent=cap.liveReady?
     tr("Wprowadź kod dostępu, aby uruchomić kontrolowany, płatny workflow w Azure.","Enter your reviewer code to start a budget-limited real Azure workflow."):
     tr("Brakuje zatwierdzonego tokenu GitHub Actions lub kodu dostępu w bezpiecznej konfiguracji Railway. Zapisy wcześniejszych uruchomień są dostępne powyżej.",
       "An operator-provisioned GitHub Actions token and/or access code is missing from Railway. The real prior run can be inspected above.");
   $("#live-dot").classList.toggle("ready",cap.liveReady);
   $("#run-foundry").disabled=!cap.liveReady;
 }catch{
   $("#live-state").textContent=tr("Bramka live jest niedostępna","Live gateway unavailable");
   $("#live-message").textContent=tr("Historyczny przebieg pozostaje dostępny.","The real recorded run remains accessible.");
 }
}
function displayEvent(e){
 const row=make("div","live-event");row.append(make("span","event-index",String(e.seq).padStart(2,"0")));
 const inner=make("div","");
 const payload=e.payload||{};
 const eventLabel=e.type+(payload.role?" · "+payload.role:"")+(payload.tool?" · "+payload.tool+"()":"");
 inner.append(make("strong","",eventLabel));
 if(e.type==="agent.completed")inner.append(make("p","",payload.summary));
 else if(e.type==="tool.completed")inner.append(make("p","",payload.duration_ms+" ms · "+payload.status));
 else inner.append(make("p","",JSON.stringify(payload)));
 inner.append(make("small","",e.classification+" · "+e.at_utc));
 row.append(inner);return row;
}
async function pollSession(){
 if(!activeSession)return;
 try{
   const response=await fetch("/api/live/session/"+activeSession,{cache:"no-store"});
   const result=await response.json();
   if(!response.ok)throw Error(result.error||"session_error");
   $("#session-title").textContent=tr("Prawdziwy run: ","Real execution: ")+activeSession.slice(0,8)+" · "+result.status+
     (result.conclusion?" / "+result.conclusion:"");
   const link=$("#session-github");
   if(result.githubRunUrl){
     const u=new URL(result.githubRunUrl);
     if(u.hostname==="github.com"&&u.protocol==="https:"){link.href=u.href;link.hidden=false;}
   }
   const steps=$("#live-steps");steps.replaceChildren();
   for(const job of result.jobs)for(const st of job.steps||[]){
     const cls=st.conclusion==="success"?"complete":st.conclusion==="failure"?"error":st.status==="in_progress"?"running":"";
     const row=make("div","live-step "+cls);
     row.append(make("span","",st.conclusion||st.status||"waiting"),make("b","",st.name));
     steps.append(row);
   }
   const events=$("#live-events");events.replaceChildren();
   for(const e of result.events)events.append(displayEvent(e));
   if(result.status==="completed"){
     clearInterval(pollId);pollId=null;
     $("#run-foundry").disabled=true;
   }
 }catch(e){
   $("#live-error").textContent=liveError(e.message);
 }
}
async function launch(){
 const accessCode=$("#reviewer-code").value;
 if(accessCode.length<20){$("#live-error").textContent=liveError("invalid_access_code");return;}
 const button=$("#run-foundry");button.disabled=true;
 $("#live-error").textContent="";
 try{
   const r=await fetch("/api/live/start",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({accessCode})});
   const result=await r.json();
   if(!r.ok)throw Error(result.error||"launch_failed");
   activeSession=result.id;
   $("#reviewer-code").value="";
   $("#live-session").hidden=false;
   await pollSession();
   pollId=setInterval(pollSession,6000);
 }catch(e){
   $("#live-error").textContent=liveError(e.message);
   button.disabled=false;
 }
}
async function init(){
 for(const b of $$("[data-lang]"))b.addEventListener("click",()=>setLanguage(b.dataset.lang));
 setLanguage(lang);
 $("#run-foundry").addEventListener("click",launch);
 try{
   const names=["./data/evidence.json","./data/agent_trace.json","./data/foundry_reports.json"];
   const responses=await Promise.all(names.map(n=>fetch(n,{cache:"no-store"})));
   if(responses.some(x=>!x.ok))throw Error("Missing evidence");
   [evidence,trace,reports]=await Promise.all(responses.map(x=>x.json()));
   verifyEvidence();renderAll();
 }catch(e){
   console.error("Evidence contract failed",e);
   $("#recorded-tools").textContent=tr("Nie udało się potwierdzić oryginalnego przebiegu.","Recorded source contract could not be verified.");
 }
 await loadLiveCapabilities();
}
init();
})();

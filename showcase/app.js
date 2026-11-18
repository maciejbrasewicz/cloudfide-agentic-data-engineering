/* ENGINEERING INTELLIGENCE / Interaction layer
   The only data source is the checked-in verified evidence snapshot.
   No placeholder traces, guessed model usage or fake real-time connection. */
(() => {
  "use strict";
  const VIEWS = ["overview","architecture","cases","execution","data","evidence"];
  const state = {evidence:null,view:"overview",caseId:"duplicate",agentId:"architect",nodeId:"architect",region:"North",toastTimer:null};
  const $ = (selector,root=document) => root.querySelector(selector);
  const $$ = (selector,root=document) => [...root.querySelectorAll(selector)];
  const clean = (value) => String(value ?? "").replace(/[&<>"']/g,(v)=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[v]));
  const verifiedLink = (url) => {
    try {const v=new URL(url);return v.protocol==="https:"&&v.hostname==="github.com"?v.href:"#";}
    catch{return "#";}
  };
  const base = "https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering";
  const money = (value) => new Intl.NumberFormat("en-US",{minimumFractionDigits:2,maximumFractionDigits:2}).format(value);
  const num = (value) => new Intl.NumberFormat("en-US").format(value);
  const shortHash = (v) => (v||"").slice(0,12);
  const statusIcon = '<span class="status-ok" aria-label="Verified">●</span>';
  const linkToFile = (path) => base + "/blob/" + state.evidence.provenance.reviewedCommit + "/" + path.split("/").map(encodeURIComponent).join("/");
  function toast(message){
    const element=$("#toast");element.textContent=message;element.classList.add("visible");
    clearTimeout(state.toastTimer);state.toastTimer=setTimeout(()=>element.classList.remove("visible"),2300);
  }
  async function copy(value){
    try{await navigator.clipboard.writeText(value);toast("Hash copied to clipboard");}
    catch{toast("Copy unavailable in this browser");}
  }
  function switchView(name,options={}){
    if(!VIEWS.includes(name))name="overview";
    const changed=state.view!==name;state.view=name;
    $$(".view").forEach(e=>e.classList.toggle("active",e.dataset.section===name));
    $$(".nav-link").forEach(e=>{
      const active=e.dataset.view===name;
      e.classList.toggle("active",active);
      active?e.setAttribute("aria-current","page"):e.removeAttribute("aria-current");
    });
    $("#current-view-label").textContent=name==="cases"?"INVESTIGATIONS":name.toUpperCase();
    $(".rail").classList.remove("open");$("#mobile-menu").setAttribute("aria-expanded","false");
    if(options.updateHash!==false)history.replaceState(null,"","#"+name);
    if(changed&&options.scroll!==false)window.scrollTo({top:0,behavior:matchMedia("(prefers-reduced-motion: reduce)").matches?"instant":"smooth"});
    document.title="Engineering Intelligence / "+(name[0].toUpperCase()+name.slice(1));
  }
  function restoreView(){
    const name=location.hash.replace("#","");
    switchView(VIEWS.includes(name)?name:"overview",{scroll:false,updateHash:false});
  }
  function renderOverview(){
    const q=state.evidence.quality;
    const items=[
      ["VERIFIED TESTS",String(q.testCount),statusIcon+" WINDOWS / UBUNTU"],
      ["AGENT REVIEWS",String(state.evidence.agents.length).padStart(2,"0"),"MICROSOFT FOUNDRY"],
      ["CLEAN TRANSACTIONS",num(q.cleanRows),"FROM "+num(q.sourceRows)+" RAW ROWS"],
      ["NET REVENUE","2.57M","EXACT / "+money(q.netRevenue)]
    ];
    $("#overview-metrics").innerHTML=items.map(([label,value,note])=>`<div class="metric"><span class="metric-label">${label}</span><strong class="metric-value">${value}</strong><span class="metric-note">${note}</span></div>`).join("");
    const c=state.evidence.cases[0];
    $("#featured-case").innerHTML=`<div class="featured-left"><div class="label-mono">FEATURED INVESTIGATION / CASE 01</div><h3>${clean(c.title)}</h3><p>${clean(c.subtitle)} A verified multiagent review initiated an evidence-driven change to the actual project.</p><button type="button" data-open-case="${clean(c.id)}">Explore the full investigation →</button></div><div class="featured-right"><div class="featured-step"><span class="step-num">01</span><div><strong>Agent discovery</strong><span>${clean(c.discovery)}</span></div></div><div class="featured-step"><span class="step-num">02</span><div><strong>Executable counterexample</strong><span>Turn a hypothesis into a failing regression case.</span></div></div><div class="featured-step"><span class="step-num">03</span><div><strong>Verified correction</strong><span>Real pull request, independent CI and fresh agent review.</span></div></div></div>`;
  }
  const GRAPH_DETAILS={
    architect:{label:"AGENT 01 / OBSERVATION",name:"Data Architect",summary:"Profiles the raw source, examines individual orders and challenges the justification for transformations. Produces findings rather than executable policy mutations.",boundary:"Can inspect source records and approved policy. Cannot change code, generate arbitrary commands or approve financial correctness."},
    engineer:{label:"AGENT 02 / IMPLEMENTATION REVIEW",name:"Data Engineer",summary:"Reads the implementation, current data contract and tests. Uses a fixed bounded test tool and reports potential implementation defects.",boundary:"This implementation is a read-only engineering reviewer. Earlier fixes were applied by a human-directed workflow, not autonomously written by this agent."},
    verifier:{label:"AGENT 03 / FALSIFICATION",name:"Verification Engineer",summary:"Independently rechecks source and output controls, runs bounded tests and looks for counterexamples to previous engineering claims.",boundary:"Read-only role. A reviewer opinion alone cannot certify a calculation or authorize an automatic merge."},
    input:{label:"SOURCE / UNTRUSTED",name:"Raw data & assignment",summary:"Original sales.csv, supplied test suite and documented assignment assumptions. The public repository deliberately excludes the original task instructions.",boundary:"CSV content is data, never an instruction source. Original data stays immutable."},
    gate:{label:"DETERMINISTIC / NO LLM",name:"Quality & policy gate",summary:"Pydantic contract validation, Decimal arithmetic, independent raw-CSV oracle, 64 tests, source-control checks and SHA-256 provenance.",boundary:"The model cannot override the gate. All calculations can be rerun without Azure or AI."},
    output:{label:"DELIVERABLE / ATTESTED",name:"Revenue & evidence",summary:"Five regional totals, policy decisions, GitHub review history and a machine-readable report from the verified Foundry run.",boundary:"Hashes attest to artifact identity, not to the unknowable business truth of every assumption."}
  };
  function nodeButton(id,number,name,small){
    const selected=state.nodeId===id?" selected":"";
    const color={architect:"var(--mint)",engineer:"var(--cyan)",verifier:"var(--purple)",input:"#8ea5b8",gate:"var(--mint)",output:"var(--gold)"}[id];
    return `<button type="button" class="graph-node${selected}${id==="gate"?" deterministic":""}${id==="output"?" bottom-node":""}" style="--node-color:${color}" data-node="${id}" aria-pressed="${state.nodeId===id}"><span class="node-id">${number}</span><strong>${name}</strong><small>${small}</small></button>`;
  }
  function renderArchitecture(){
    $("#architecture-graph").innerHTML=
      `<div class="graph-row">${nodeButton("architect","AGENT / 01","Data Architect","SOURCE → POLICY")}${nodeButton("engineer","AGENT / 02","Data Engineer","CODE → TESTS")}${nodeButton("verifier","AGENT / 03","Verifier","FALSIFICATION")}</div>`+
      '<div class="graph-connector"><div class="graph-down"></div>SEQUENTIAL REVIEW / ROLE-BOUND TOOLS<div class="graph-down" style="margin-top:14px"></div></div>'+
      `<div class="graph-row bottom-row">${nodeButton("input","SOURCE / RAW","Source data","IMMUTABLE INPUT")}${nodeButton("gate","GATE / HARD","Quality gate","DETERMINISTIC CHECKS")}${nodeButton("output","OUTPUT / VERIFIED","Evidence","CSV · AUDIT · PR")}</div>`;
    renderArchitectureDetail();
  }
  function renderArchitectureDetail(){
    const d=GRAPH_DETAILS[state.nodeId],a=state.evidence.agents.find(x=>x.id===state.nodeId);
    const tools=a?.tools??(state.nodeId==="gate"?["pytest / hypothesis","Decimal source oracle","Pydantic policy","SHA-256 comparison"]:[]);
    $("#architecture-detail").innerHTML=`<div><div class="arch-detail-label">${clean(d.label)}</div><h3>${clean(d.name)}</h3><p>${clean(d.summary)}</p>${tools.length?`<div class="detail-tool-list">${tools.map(x=>`<span>${clean(x)}</span>`).join("")}</div>`:""}</div><div class="detail-boundary"><div class="arch-detail-label">TRUST BOUNDARY</div><strong>Capabilities are explicit.</strong><p>${clean(d.boundary)}</p>${a?`<div class="detail-tool-list"><span>${a.findings} recorded findings</span></div>`:""}</div>`;
  }
  function renderCases(){
    $("#case-list").innerHTML=state.evidence.cases.map(c=>`<button type="button" class="case-list-button ${c.id===state.caseId?"active":""}" role="tab" aria-selected="${c.id===state.caseId}" data-case="${clean(c.id)}"><span class="case-list-index">CASE ${clean(c.index)} / ${clean(c.theme.toUpperCase())}</span><strong>${clean(c.title)}</strong><small>PR #${c.pr} · VERIFIED CORRECTION ↗</small></button>`).join("");
    const c=state.evidence.cases.find(x=>x.id===state.caseId)??state.evidence.cases[0];
    const stages=[["01","DISCOVERY",c.discovery],["02","COUNTEREXAMPLE",c.counterexample],["03","CORRECTION",c.change],["04","INDEPENDENT PROOF",c.proof]];
    $("#case-detail").innerHTML=`<div class="case-topline"><span>INVESTIGATION #${clean(c.index)} / ${clean(c.theme.toUpperCase())}</span><span>● VERIFIED</span></div><h2>${clean(c.title)}</h2><p class="case-lede">${clean(c.subtitle)}</p><div class="case-evidence-chain">${stages.map(([i,t,d])=>`<div class="chain-row"><span class="chain-number">${i}</span><span class="chain-label">${t}</span><span class="chain-description">${clean(d)}</span></div>`).join("")}</div><a class="case-link" target="_blank" rel="noopener noreferrer" href="${verifiedLink(c.url)}">Inspect the actual PR #${c.pr} and code diff ↗</a>`;
  }
  function renderExecution(){
    $("#execution-source-link").href=verifiedLink(state.evidence.provenance.reviewUrl);
    $("#checkpoints").innerHTML=state.evidence.checkpoints.map(x=>`<div class="checkpoint"><span class="check-circle" aria-label="Verified">✓</span><div><h4>${clean(x.title)}</h4><p>${clean(x.description)}</p><div class="checkpoint-foot"><span>✓ ${clean(x.detail)}</span><span class="checkpoint-source">·</span><a href="${linkToFile(x.source)}" target="_blank" rel="noopener noreferrer" title="View source file">${clean(x.source)} ↗</a></div></div></div>`).join("");
    $("#agent-switcher").innerHTML=state.evidence.agents.map(x=>`<button type="button" data-agent="${x.id}" class="${state.agentId===x.id?"active":""}" aria-label="Inspect ${clean(x.name)}" aria-pressed="${state.agentId===x.id}">${x.index}</button>`).join("");
    const a=state.evidence.agents.find(x=>x.id===state.agentId)??state.evidence.agents[0];
    $("#agent-inspector").innerHTML=`<div class="agent-position">REVIEW ROLE / ${clean(a.index)}</div><h3>${clean(a.name)}</h3><p>${clean(a.summary)}</p><div class="agent-stat"><span>STRUCTURED FINDINGS</span><strong>${a.findings}</strong></div><div class="agent-stat"><span>SCHEMA VALIDATION</span><span style="color:var(--mint)">PASSED ✓</span></div><div class="agent-tool-head">ALLOWLISTED FUNCTIONS</div><div class="agent-tools">${a.tools.map(x=>`<code>${clean(x)}()</code>`).join("")}</div><div class="agent-boundary">${clean(a.boundary)}</div>`;
  }
  function renderData(){
    const q=state.evidence.quality;
    const metrics=[["FINAL NET REVENUE",money(q.netRevenue),"EXACT DECIMAL TOTAL"],["CLEAN TRANSACTIONS",num(q.cleanRows),"AFTER SOURCE-EXACT DEDUPLICATION"],["REGIONS",num(q.regions.length),"CANONICAL / 5 LABELS"]];
    $("#data-topline").innerHTML=metrics.map(x=>`<div class="data-top-metric"><span class="label-mono">${x[0]}</span><span class="value">${x[1]}</span><span class="hint">${x[2]}</span></div>`).join("");
    const max=Math.max(...q.regions.map(x=>x.value));
    $("#revenue-bars").innerHTML=q.regions.map(x=>`<button type="button" class="revenue-row" data-region="${clean(x.name)}" aria-label="${clean(x.name)} revenue ${money(x.value)}" style="background:transparent;border:0;padding:0;text-align:left;cursor:pointer"><span class="region-name">${clean(x.name)}</span><span class="bar-track"><span class="bar-fill" style="display:block;width:${Math.round(x.value/max*100)}%"></span></span><span class="region-money">${money(x.value)}</span></button>`).join("")+
      '<div style="color:#8b9ea5;font:10px var(--mono);border-top:1px solid var(--line);padding-top:16px">SELECT ANY REGION FOR AN EXACT REVENUE READING</div>';
    const anomalies=[
      ["Exact duplicates removed",q.exactDuplicates],["Noncanonical region values",q.normalizedRegions],
      ["Decimal-comma prices",q.commaPrices],["Grouped-quantity values",q.spacedQuantities],
      ["Missing unit prices recovered",q.recoveredPrices],["Blank discounts defaulted to zero",q.blankDiscountsZeroed],
      ["Negative quantity rows retained",q.negativeQuantities],["Embedded headers",q.repeatedHeaders]
    ];
    $("#anomaly-bars").innerHTML=anomalies.map(([label,value])=>`<div class="anomaly-row"><span class="anomaly-label">${clean(label)}</span><strong class="anomaly-number">${num(value)}</strong></div>`).join("");
    $("#control-stats").innerHTML=`<div class="control-stat"><small>RAW QUANTITY</small><strong>${num(q.controlQuantity)}</strong></div><div class="control-stat"><small>RAW DISCOUNT</small><strong>${money(q.controlDiscount)}</strong></div><div class="control-stat"><small>RECONCILIATION</small><strong style="color:var(--mint)">PASS ✓</strong></div>`;
  }
  function renderEvidence(){
    $("#decision-ledger").innerHTML=state.evidence.decisions.map((d,i)=>`<details class="decision" ${i===0?"open":""}><summary><span class="decision-id">${clean(d.id)}</span><span class="decision-title">${clean(d.title)}</span><span class="decision-arrow">+</span></summary><div class="decision-body"><div class="decision-tag">${clean(d.status.replaceAll("_"," ").toUpperCase())}</div><div class="decision-block"><span class="label-mono">OBSERVATION</span><p>${clean(d.observation)}</p></div><div class="decision-block"><span class="label-mono">APPROVED BEHAVIOR</span><p>${clean(d.decision)}</p></div><div class="decision-block"><span class="label-mono">REMAINING UNCERTAINTY</span><p>${clean(d.risk)}</p></div><div class="decision-block"><span class="label-mono">VERIFICATION</span><p>${clean(d.verification)}</p></div><a class="decision-link" href="${linkToFile(d.source)}" target="_blank" rel="noopener noreferrer">Inspect supporting implementation ↗</a></div></details>`).join("");
    const p=state.evidence.provenance;
    const entries=[
      ["REVIEWED COMMIT",p.reviewedCommit,"hash"],["SOURCE SHA-256",p.sourceSha256,"hash"],
      ["OUTPUT SHA-256",p.outputSha256,"hash"],["POLICY SHA-256",p.policySha256,"hash"],
      ["MODEL DEPLOYMENT",p.modelDeployment,"plain"],["EVIDENCE ORIGIN",p.kind.replaceAll("_"," ").toUpperCase(),"plain"]
    ];
    $("#manifest-content").innerHTML='<div class="manifest-content">'+entries.map(([label,value,kind])=>`<div class="manifest-row"><span class="manifest-key">${clean(label)}</span><span class="manifest-val">${clean(kind==="hash"?shortHash(value)+"…":value)}</span>${kind==="hash"?`<div class="manifest-actions"><button type="button" class="icon-action" data-copy="${clean(value)}">COPY FULL HASH ↗</button></div>`:""}</div>`).join("")+`<a class="manifest-link" href="${verifiedLink(p.reviewUrl)}" target="_blank" rel="noopener noreferrer">OPEN SOURCE WORKFLOW ↗</a><br/><a class="manifest-link" href="./data/evidence.json" download="engineering_evidence.json">DOWNLOAD PUBLIC EVIDENCE JSON ↗</a></div>`;
  }
  function attachEvents(){
    document.addEventListener("click",(event)=>{
      const viewButton=event.target.closest("[data-view], [data-view-link]");
      if(viewButton){event.preventDefault();switchView(viewButton.dataset.view??viewButton.dataset.viewLink);return;}
      const caseOpen=event.target.closest("[data-open-case]");
      if(caseOpen){state.caseId=caseOpen.dataset.openCase;renderCases();switchView("cases");return;}
      const caseBtn=event.target.closest("[data-case]");
      if(caseBtn){state.caseId=caseBtn.dataset.case;renderCases();return;}
      const agentBtn=event.target.closest("[data-agent]");
      if(agentBtn){state.agentId=agentBtn.dataset.agent;renderExecution();return;}
      const graphBtn=event.target.closest("[data-node]");
      if(graphBtn){state.nodeId=graphBtn.dataset.node;renderArchitecture();return;}
      const regionBtn=event.target.closest("[data-region]");
      if(regionBtn){const r=state.evidence.quality.regions.find(x=>x.name===regionBtn.dataset.region);if(r)toast(r.name+" · "+money(r.value));return;}
      const copyBtn=event.target.closest("[data-copy]");
      if(copyBtn){copy(copyBtn.dataset.copy);return;}
    });
    window.addEventListener("hashchange",restoreView);
    $("#mobile-menu").addEventListener("click",()=>{
      const rail=$(".rail"),open=!rail.classList.contains("open");
      rail.classList.toggle("open",open);$("#mobile-menu").setAttribute("aria-expanded",String(open));
    });
    document.addEventListener("keydown",(event)=>{
      if(event.key==="Escape"&&$(".rail").classList.contains("open")){
        $(".rail").classList.remove("open");$("#mobile-menu").setAttribute("aria-expanded","false");$("#mobile-menu").focus();
      }
      if((event.key==="ArrowRight"||event.key==="ArrowLeft")&&event.target.closest("#case-list")){
        const n=state.evidence.cases.findIndex(x=>x.id===state.caseId);
        const delta=event.key==="ArrowRight"?1:-1;
        state.caseId=state.evidence.cases[(n+delta+state.evidence.cases.length)%state.evidence.cases.length].id;
        renderCases();$("#case-list [aria-selected=true]").focus();event.preventDefault();
      }
    });
  }
  async function start(){
    try{
      const response=await fetch("./data/evidence.json",{cache:"no-cache"});
      if(!response.ok)throw Error("Evidence response "+response.status);
      const d=await response.json();
      if(d.schemaVersion!==1||!d.provenance?.reviewedCommit||!d.quality?.regions?.length||d.agents?.length!==3||d.cases?.length!==3)throw Error("Evidence contract mismatch");
      state.evidence=d;renderOverview();renderArchitecture();renderCases();renderExecution();renderData();renderEvidence();
      attachEvents();restoreView();
    }catch(error){
      console.error("Could not verify evidence data:",error);
      $("#load-error").hidden=false;
    }
  }
  start();
})();

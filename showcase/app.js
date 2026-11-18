/* CloudFide / documented Foundry case study.
   No synthetic agent conversations, invented tool timings or live-data claims. */
(() => {
  "use strict";
  const en = {
    skip:"Skip to content",
    navLab:"Engineering Lab ↗",
    heroLab:"Open Engineering Lab",
    ownershipEyebrow:"HOW WE BUILT IT",
    ownershipTitle:"Who designed the agents — and who made the decisions?",
    ownershipLead:"The process was human-in-the-loop. That's the difference between a real engineering delivery and merely running three prompts.",
    ownershipHuman:"A human approved direction",
    ownershipHumanDesc:"Requirements, data policy, review of proposals and acceptance of changes.",
    ownershipChat:"ChatGPT designed and implemented",
    ownershipChatDesc:"Architecture, code, repairs, the agents, GitHub CI and Azure OIDC.",
    ownershipFoundry:"Three Foundry agents reviewed",
    ownershipFoundryDesc:"Actual SequentialBuilder, read-only tools and structured reports.",
    ownershipGate:"Deterministic tests supplied proof",
    ownershipGateDesc:"Independent oracle, artifact checks and data validation outside model judgment.",
    ownershipCaveat:"ChatGPT was an external architect collaborating with the human, not a fourth Foundry agent. Earlier code corrections were not autonomous commits from the Engineer reviewer.",
    ownershipCTA:"Explore the full architecture and launch a real review",
    topDate:"Documented implementation · 18 November 2026",
    navTask:"Assignment",navArchitecture:"Architecture",navAgents:"Agent run",navData:"Results",navProof:"Evidence",originalRun:"Original run",
    kicker:"Real implementation case study / no simulation",
    heroTitle:"A Data Engineering assignment. Three Foundry agents. Verifiable results.",
    heroLead:"We built a working Python/pandas pipeline, then audited it with three specialized reviewers using Microsoft Agent Framework. Here is the real execution, what the agents found, what we fixed and where the numbers come from.",
    heroAction:"See what the agents did",heroResult:"Explore the data output",
    resultCard:"RESULT FROM AN ACTUAL EXECUTION",revenueTag:"Net revenue / 5 regions",
    revenueExplanation:"Computed deterministically — not by AI",
    agentCount:"agent reports",toolCount:"real tool calls",testsCount:"CI tests",durationCount:"actual execution time",
    sourceEvidence:"Evidence: verified GitHub Actions run",
    taskEyebrow:"THE ASSIGNMENT",taskHeading:"What were we asked to deliver?",
    taskLead:"Two concrete recruiting tasks. This is not an imaginary demo: the agents reviewed a real implementation.",
    virtualTitle:"Virtual column function",
    virtualDesc:"add_virtual_column(df, role, new_column) computes a new column from a restricted arithmetic expression. An AST allowlist rejects invalid names and operations without evaluating arbitrary code.",
    virtualFooter:"Delivered: function, supplied tests and regression tests.",
    etlTitle:"Net revenue from a messy sales CSV",
    etlDesc:"The export contained duplicates, a repeated header, a TOTAL control row, inconsistent number formats, inconsistent region labels and missing prices. The pipeline validates controls, applies the approved policy and produces revenue_by_region.csv.",
    etlFooter:"Delivered: regional revenue CSV and a data quality report.",
    rawSource:"SOURCE DATA",rawExplain:"rows including repeated header and TOTAL",
    cleanSource:"AFTER CLEANING",cleanExplain:"actual transaction rows",
    finalSource:"RESULT",regionWord:"regions",finalExplain:"totals exact to two decimal places",
    architectureEyebrow:"ARCHITECTURE",architectureHeading:"How the system actually works.",
    architectureLead:"Two separate paths: deterministic Python computes the result; a sequential AI review evaluates its correctness. LLM output does not replace accounting arithmetic.",
    laneA:"Computation / no AI",sourceStep:"INPUT",sourceStepDesc:"Unmodified source and versioned cleaning rules.",
    processingStep:"PROCESSING",processingStepDesc:"Source controls, cleaning, deduplication and revenue.",
    resultStep:"OUTPUT",resultStepDesc:"Five regions, quality report, SHA-256 provenance.",
    laneB:"Review / Microsoft Foundry",roleArchitect:"Source profiling, anomalies and assumptions",roleEngineer:"Code and test review",roleVerifier:"Independent verification and falsification",
    reviewStep:"REVIEW OUTPUT",reviewStepDesc:"Findings, evidence and next steps; manifest validated.",
    trustBoundary:"Important trust boundary",
    trustDesc:"Agents do not calculate revenue, nor can they certify it by assertion. The present Engineer Agent has read-only review tools; it does not modify repository code or create pull requests autonomously.",
    executionEyebrow:"RECORDED EXECUTION",executionHeading:"What did the three agents actually do?",
    executionLead:"The following results came from a real Foundry workflow run. We show differences between the three roles, including what they were unable to verify.",
    runDate:"DATE",walltime:"WALL TIME",openEvidence:"Open recorded execution ↗",
    whatRan:"WHAT RAN",
    whatRanText:"GitHub Actions executed the pipeline and tests, authenticated to Azure with OIDC, then invoked SequentialBuilder with three reviewers. Each agent had a specific prompt and bounded tools. Pydantic parsed the returned reports and a manifest checked the evidence files against their hashes.",
    reportsHeading:"The real reports — three different roles",reportsSubheading:"Select a role to see its findings and allowed tools.",
    measureLabel:"RECORDED TELEMETRY",toolHeading:"Which tools did the agents actually call?",
    toolLead:"Sixteen real tool calls were measured with timings. Without per-agent span attribution we do not assign individual calls to specific reviewers.",
    expandEvents:"Expand all 16 measured calls",
    traceLimit:"This is a real tool-call record, not a full distributed trace. Model tokens, costs and individual agent durations were not captured in this run.",
    resultsEyebrow:"DATA OUTPUT",resultsHeading:"What did the ETL produce?",
    resultsLead:"Actual totals from the generated CSV and measured data-repair counts. These values come from executable code, not an LLM.",
    regionsHeading:"Net revenue by region",totalLabel:"TOTAL",cleanHeading:"Data anomalies handled",
    controlHeading:"Control totals reconciled before deduplication",
    controlDesc:"The TOTAL record matched the 1,505 original transactions before five exact duplicates were removed. An independent CSV/Decimal parser then verified the final result.",
    controlQty:"SOURCE QUANTITY",controlDiscount:"SOURCE DISCOUNT",
    improvementsEyebrow:"AUDIT OUTCOMES",improvementsHeading:"What changed as a result of review?",
    improvementsLead:"Three actual pull requests: a concrete issue, a code correction and a regression test. Each link opens the real diff and CI history.",
    testLabel:"tests passed",testProof:"Windows and Ubuntu CI. Separately, a fault-injection lab caught 4/4 seeded code defects and rejected 1/1 corrupted source. That tests the deterministic quality gates, not the LLM agents.",
    ciLink:"Open CI result ↗",faultLink:"Open fault-injection run ↗",
    statusEyebrow:"LIMITATIONS",statusHeading:"What is implemented — and what isn't?",
    statusLead:"The precise state of the system. We do not claim autonomous code authoring or observability we have not configured.",
    doneHeading:"IMPLEMENTED AND CHECKED",pendingHeading:"NOT IMPLEMENTED YET",
    evidenceEyebrow:"EVIDENCE",evidenceHeading:"Verify the implementation yourself.",
    evidenceLead:"The case study explains the work; these are the original, inspectable runs, artifacts and code.",
    eFoundry:"Actual three-agent Foundry review",eFoundryNote:"Azure OIDC · Foundry · JSON reports · 16 tool calls",
    eTests:"CI and test results",eTestsNote:"79 tests · Windows and Ubuntu · reconciliation",
    eWorkflow:"Multiagent workflow implementation",
    eResult:"Generated revenue CSV",eResultNote:"Five regions independently rechecked",
    eCode:"Complete project",eCodeNote:"Repository as an in-depth technical appendix",
    copy:"Copy",footerText:"Real engineering work, explicit assumptions, reproducible results.",top:"Back to top ↑"
  };
  const meta = {};
  for (const node of document.querySelectorAll("[data-i18n]")) meta[node.dataset.i18n]=node.textContent;
  let language = new URLSearchParams(location.search).get("lang")==="en"?"en":"pl";
  let data=null, trace=null, reviews=null;
  let activeAgent="architect";
  const $=(selector,root=document)=>root.querySelector(selector);
  const elt=(tag,klass,text)=>{
    const node=document.createElement(tag);
    if(klass)node.className=klass;
    if(text!==undefined)node.textContent=String(text);
    return node;
  };
  const pl=(text,english)=>language==="pl"?text:english;
  const formatMoney=(value)=>new Intl.NumberFormat(language==="pl"?"pl-PL":"en-US",{minimumFractionDigits:2,maximumFractionDigits:2}).format(Number(value));
  const formatCount=(value)=>new Intl.NumberFormat(language==="pl"?"pl-PL":"en-US").format(value);
  function setLanguage(next){
    language=next==="en"?"en":"pl";
    document.documentElement.lang=language;
    for(const node of document.querySelectorAll("[data-i18n]")){
      const key=node.dataset.i18n;
      node.textContent=language==="en"?(en[key]??meta[key]):meta[key];
    }
    for(const link of document.querySelectorAll('[data-route="engineering"]')){
      link.href="./engineering.html?lang="+language;
    }
    for(const node of document.querySelectorAll("[data-lang]")){
      node.setAttribute("aria-pressed",String(node.dataset.lang===language));
    }
    const url=new URL(location.href);
    url.searchParams.set("lang",language);
    history.replaceState(null,"",url.pathname+url.search+url.hash);
    document.title=language==="pl"?"CloudFide — Agenci AI w Microsoft Foundry / studium wdrożenia":"CloudFide — Real Microsoft Foundry multiagent engineering case study";
    if(data&&trace&&reviews) renderDynamic();
  }
  function safeUrl(url){
    const parsed=new URL(url);
    if(parsed.protocol!=="https:"||parsed.hostname!=="github.com")throw Error("Unexpected evidence URL");
    return parsed.href;
  }
  function validEvidence(e,t,r){
    if(e.schemaVersion!==1||r.schemaVersion!==1||t.schemaVersion!==1) return false;
    if(e.provenance.reviewedCommit!==t.reviewedCommit||e.provenance.reviewedCommit!==r.reviewedCommit) return false;
    if(e.provenance.sourceSha256!==t.sourceSha256)return false;
    if(e.observability.toolSpanCount!==t.toolCallCount||t.events?.length!==t.toolCallCount)return false;
    if(e.agents?.length!==3||r.roles?.length!==3||!e.quality?.regions)return false;
    if(e.quality.testCount<79||t.githubRunId!==r.runId||!e.provenance.reviewUrl.endsWith(r.runId))return false;
    if(t.otelTraceId!==null||t.tokenUsage!==null||t.estimatedCost!==null)return false;
    const total=Math.round(e.quality.regions.reduce((sum,line)=>sum+line.value,0)*100);
    return total===Math.round(Number(e.quality.netRevenue)*100);
  }
  const summaries={
    architect:{
      pl:"Architekt profilował źródło i wskazał różnice między faktem a założeniem biznesowym. Zidentyfikował strukturę CSV, ale nie potwierdził jeszcze zgodności implementacji i wyników.",
      en:"The architect profiled the source and distinguished observed facts from business assumptions. It identified the CSV structure but did not establish implementation or output correctness.",
      decisionPL:"Co z tego wynika: usunięcie duplikatów, interpretacja zwrotów i odtwarzanie cen wymagają potwierdzenia przez właściciela danych.",
      decisionEN:"What this means: duplicate deletion, return semantics and price recovery still require validation by the data owner."
    },
    engineer:{
      pl:"Engineer miał zadanie przejrzeć kod i testy, ale w tym konkretnym raporcie nie potwierdził ich zgodności. Zwrócił ograniczenia dostępu do dowodów. Nie przedstawiamy tego jako pełnego code review.",
      en:"The engineer was tasked with reviewing code and tests, but this report did not establish their conformance. It reported limits to the evidence available; this is not presented as a complete code review.",
      decisionPL:"Co z tego wynika: sam fakt uruchomienia trzech agentów nie dowodzi, że każdy wykonał swój etap równie dobrze. To obszar do poprawy w orkiestracji.",
      decisionEN:"What this means: launching three agents does not prove that every role completed its intended review. This remains an orchestration improvement area."
    },
    verifier:{
      pl:"Weryfikator potwierdził przejście 79 testów oraz niezależne przeliczenie źródła i kwot regionalnych przez parser CSV/Decimal. Wskazał też brak atomowych zapisów i niezweryfikowane założenia biznesowe.",
      en:"The verifier confirmed 79 passing tests and an independent CSV/Decimal recomputation of the source and regional totals. It also flagged non-atomic output publication and unresolved business assumptions.",
      decisionPL:"Co z tego wynika: wynik arytmetyczny jest powtarzalny w ramach przyjętych reguł, ale testy nie dowodzą biznesowego znaczenia każdej transakcji.",
      decisionEN:"What this means: arithmetic is reproducible under the documented rules, but tests cannot establish the business meaning of each transaction."
    }
  };
  const qualityItems=[
    ["extraHeader","Powtórzony nagłówek","Repeated header",q=>q.repeatedHeaders],
    ["total","Wiersz kontrolny TOTAL","TOTAL control row",q=>q.summaryRows],
    ["duplicate","Dokładne duplikaty usunięte","Exact duplicates removed",q=>q.exactDuplicates],
    ["normalized","Nazwy regionów znormalizowane","Region variants normalized",q=>q.normalizedRegions],
    ["prices","Ceny z przecinkiem dziesiętnym","Decimal-comma prices parsed",q=>q.commaPrices],
    ["quantities","Ilości z separatorem tysięcy","Grouped quantities parsed",q=>q.spacedQuantities],
    ["recovered","Brakujące ceny odtworzone","Missing prices recovered",q=>q.recoveredPrices],
    ["discounts","Puste rabaty przyjęte jako zero","Blank discounts set to zero",q=>q.blankDiscountsZeroed],
    ["returns","Ujemne ilości zachowane","Negative quantities retained",q=>q.negativeQuantities]
  ];
  const fixes=[
    {pr:1,pl:"Deduplikacja po normalizacji mogła łączyć różne rekordy.",en:"Deduplicating after normalization could collapse different source records.",
      detailPL:"Zmiana: porównywanie wartości źródłowych przed czyszczeniem i nowe testy na identyczność rekordów.",detailEN:"Fix: compare raw source values before cleaning and add record-identity regressions."},
    {pr:2,pl:"Globalne .strip() po cichu zmieniało inne pola niż region.",en:"Global .strip() silently changed fields beyond the permitted region label.",
      detailPL:"Zmiana: normalizacja ograniczona do właściwego pola i testy odrzucające niezatwierdzone korekty.",detailEN:"Fix: field-scoped normalization and fail-closed tests for unauthorized coercion."},
    {pr:3,pl:"Ścieżka pliku wynikowego mogła nadpisać dane źródłowe.",en:"An output path could overwrite the original evidence file.",
      detailPL:"Zmiana: kontrola kolizji ścieżek jeszcze przed zapisem oraz testy zachowania bajtów źródła.",detailEN:"Fix: reject artifact-path collisions before writes and test source-byte preservation."}
  ];
  const implemented=[
    ["3 agenty Microsoft Agent Framework + Foundry","3 Microsoft Agent Framework agents in Foundry"],
    ["Orkiestracja SequentialBuilder","SequentialBuilder orchestration"],
    ["Ograniczone narzędzia tylko do odczytu","Restricted read-only reviewer tools"],
    ["Pydantic + wersjonowany kontrakt danych","Pydantic + versioned data contract"],
    ["ETL pandas/Decimal + niezależny oracle","pandas/Decimal ETL + independent oracle"],
    ["GitHub Actions + Azure Entra OIDC","GitHub Actions + Azure Entra OIDC"],
    ["79 testów CI / Windows + Ubuntu","79 CI tests / Windows + Ubuntu"],
    ["16 zmierzonych wywołań narzędzi","16 measured tool calls"],
    ["Kontrolowany Fault-Injection Lab","Controlled deterministic fault-injection lab"]
  ];
  const pending=[
    ["Autonomiczne pisanie kodu przez Engineer Agent","Autonomous code authoring by Engineer Agent"],
    ["GitHub MCP jako narzędzia agentów","GitHub MCP integrated into agent workflows"],
    ["Trwały DataDecision / decision ledger agentów","Persistent DataDecision records produced by agents"],
    ["Pandera jako warstwa walidacji DataFrame","Pandera DataFrame validation layer"],
    ["Aktywny Application Insights z pełnym trace ID","Connected Application Insights with real trace IDs"],
    ["Pomiar tokenów/kosztu i czasu każdego agenta","Measured tokens/cost and per-agent timings"],
    ["Osobna ewaluacja skuteczności agentów","Independent agent accuracy evaluation"]
  ];
  function renderReports(){
    const tabs=$("#agent-tabs"),body=$("#agent-detail");
    tabs.replaceChildren();
    reviews.roles.forEach((report,i)=>{
      const isActive=report.id===activeAgent;
      const button=elt("button","",null);
      button.type="button";button.role="tab";button.setAttribute("aria-selected",String(isActive));
      button.setAttribute("tabindex",isActive?"0":"-1");
      button.append(elt("span","",String(i+1).padStart(2,"0")+" / FOUNDRY"),elt("strong","",["Data Architect","Data Engineer","Verification Engineer"][i]));
      button.addEventListener("click",()=>{activeAgent=report.id;renderReports();});
      tabs.append(button);
    });
    const report=reviews.roles.find(item=>item.id===activeAgent);
    const agent=data.agents.find(item=>item.id===activeAgent);
    const editorial=summaries[report.id];
    body.replaceChildren();
    const top=elt("div","agent-detail-top");
    const column=elt("div","");
    column.append(elt("span","label",pl("RZECZYWISTY RAPORT MODELU","ACTUAL MODEL REPORT")));
    column.append(elt("h4","",agent.name));
    column.append(elt("p","",language==="pl"?editorial.pl:editorial.en));
    const count=elt("div","agent-detail-finding-count");
    count.append(elt("strong","",report.findingCount),elt("small","",pl("ustaleń w JSON","findings in JSON")));
    top.append(column,count);body.append(top);
    const grid=elt("div","finding-grid");
    const interpretation=elt("div","finding-col");
    interpretation.append(elt("span","",pl("WYNIK I ZNACZENIE","FINDING AND IMPLICATION")),
      elt("p","",language==="pl"?editorial.decisionPL:editorial.decisionEN));
    const tools=elt("div","finding-col");
    tools.append(elt("span","",pl("DOZWOLONE NARZĘDZIA TEJ ROLI","TOOLS ALLOWED FOR THIS ROLE")));
    const list=elt("ul","");
    agent.tools.forEach(item=>list.append(elt("li","",item+"()")));
    tools.append(list);
    grid.append(interpretation,tools);body.append(grid);
    const details=elt("details","original-report");
    const summary=elt("summary","",pl("Otwórz oryginalny tekst modelu (EN) i konkretne ustalenia","Show original model output (EN) and selected findings"));
    details.append(summary);
    const quote=elt("blockquote","",report.originalSummary);
    details.append(quote);
    const subtitle=elt("h5","",pl("Wybrane faktyczne ustalenia z JSON:","Selected actual statements from the JSON:"));
    details.append(subtitle);
    const ul=elt("ul","");
    report.selectedFindings.forEach(item=>ul.append(elt("li","",item)));
    details.append(ul);
    details.append(elt("h5","",pl("Oryginalne zalecenie agenta:","Original agent's recommended next action:")));
    details.append(elt("p","original-next-step",report.originalRecommendedNextAction));
    const link=elt("a","report-link",pl("Pełny raport i oryginalny artefakt GitHub Actions ↗","Full report / original GitHub Actions artifact ↗"));
    link.href=safeUrl(reviews.runUrl);link.target="_blank";link.rel="noopener noreferrer";
    details.append(link);
    body.append(details);
  }
  function renderTools(){
    const summary=$("#tool-counts");summary.replaceChildren();
    const keys=Object.entries(trace.toolCounts).sort((a,b)=>b[1]-a[1]);
    keys.forEach(([name,count])=>{
      const card=elt("div","tool-count");
      card.append(elt("code","",name+"()"),elt("strong","",count));
      summary.append(card);
    });
    const events=$("#tool-events");events.replaceChildren();
    trace.events.forEach((event,i)=>{
      const row=elt("div","event-row");
      row.append(elt("span","",String(i+1).padStart(2,"0")),
        elt("code","",event.name+"()"),
        elt("span","",event.durationMs.toFixed(2)+" ms"),
        elt("span","",event.status==="ok"?pl("OK","OK"):pl("BŁĄD","ERROR")));
      events.append(row);
    });
  }
  function renderResults(){
    const regions=$("#region-data");regions.replaceChildren();
    const ordered=[...data.quality.regions].sort((a,b)=>b.value-a.value);
    const top=ordered[0].value;
    for(const item of ordered){
      const row=elt("div","region-row");
      row.append(elt("span","region-label",item.name));
      const bar=elt("div","region-track");const fill=elt("span","region-fill");
      fill.style.width=(item.value/top*100).toFixed(2)+"%";bar.append(fill);row.append(bar);
      row.append(elt("span","region-value",formatMoney(item.value)));
      regions.append(row);
    }
    $("#data .result-total strong").textContent=formatMoney(data.quality.netRevenue);
    $("#intro .proof-revenue strong").textContent=formatMoney(data.quality.netRevenue);
    const items=$("#quality-data");items.replaceChildren();
    for(const [,plLabel,enLabel,getValue] of qualityItems){
      const row=elt("div","quality-row");
      row.append(elt("span","",pl(plLabel,enLabel)),elt("strong","",formatCount(getValue(data.quality))));
      items.append(row);
    }
    $(".control-pair div:first-child strong").textContent=formatCount(data.quality.controlQuantity);
    $(".control-pair div:last-child strong").textContent=formatMoney(data.quality.controlDiscount);
  }
  function renderFixes(){
    const list=$("#pr-list");list.replaceChildren();
    fixes.forEach(item=>{
      const row=elt("article","pr-row");
      row.append(elt("span","pr-index","PR #"+item.pr));
      const body=elt("div","");
      body.append(elt("h3","",language==="pl"?item.pl:item.en));
      body.append(elt("p","",language==="pl"?item.detailPL:item.detailEN));
      const url="https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/pull/"+item.pr;
      const link=elt("a","",pl("Zobacz zmianę ↗","Inspect diff ↗"));
      link.href=safeUrl(url);link.target="_blank";link.rel="noopener noreferrer";
      row.append(body,link);list.append(row);
    });
  }
  function renderStatus(){
    for(const [id,items] of [["implemented",implemented],["pending",pending]]){
      const list=$("#"+id);list.replaceChildren();
      for(const [polish,english] of items) list.append(elt("li","",pl(polish,english)));
    }
  }
  function renderDynamic(){renderReports();renderTools();renderResults();renderFixes();renderStatus();}
  function showError(message){
    for(const id of ["agent-detail","tool-counts","region-data"]){
      const node=$("#"+id);if(node)node.textContent=message;
    }
  }
  async function init(){
    for(const button of document.querySelectorAll("[data-lang]")){
      button.addEventListener("click",()=>setLanguage(button.dataset.lang));
    }
    $("#copy-hash").addEventListener("click",async()=>{
      const hash="811573152aa287b14d5006ce6901ebd0ca17586149e16a5b79de5ae69684c1d4";
      try{await navigator.clipboard.writeText(hash);const toast=$("#toast");toast.textContent=pl("Skopiowano SHA-256","SHA-256 copied");toast.classList.add("show");setTimeout(()=>toast.classList.remove("show"),2200);}catch{ /* Link and visible hash remain available. */ }
    });
    setLanguage(language);
    try{
      const paths=["./data/evidence.json","./data/agent_trace.json","./data/foundry_reports.json"];
      const responses=await Promise.all(paths.map(x=>fetch(x,{cache:"no-store"})));
      if(responses.some(x=>!x.ok))throw Error("Missing public evidence file");
      [data,trace,reviews]=await Promise.all(responses.map(x=>x.json()));
      if(!validEvidence(data,trace,reviews))throw Error("Evidence integrity mismatch");
      renderDynamic();
    }catch(error){
      console.error("Unable to verify recorded implementation evidence",error);
      showError(pl("Dowody nie przeszły kontroli spójności. Otwórz oryginalny przebieg GitHub Actions.","Evidence integrity validation failed. Please inspect the original GitHub Actions run."));
    }
  }
  init();
})();

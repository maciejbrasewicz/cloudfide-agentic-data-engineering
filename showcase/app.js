/* CloudFide / documented Foundry case study.
   No synthetic agent conversations, invented tool timings or live-data claims. */
(() => {
  "use strict";
  const en = {
    entryEyebrow:"LIVE EXECUTION / MICROSOFT FOUNDRY",
    progressEyebrow:"LIVE RUN · GITHUB ACTIONS",
    progressDetails:"Actual GitHub Actions jobs and execution steps",
    entryTitle:"Launch the agents on the actual assignment",
    entryIntro:"This is not a playback or simulation. Entering your reviewer code starts real Microsoft Foundry agents through GitHub Actions. They build a fresh Python virtual-column solution and a sales ETL pipeline, generate tests and independently verify the results. New code, evidence and outcomes are produced during this run.",
    entryArchitect:"Reads the requirements, profiles the source and defines the implementation contract.",
    entryEngineer:"Writes Python and tests. Docker executes the result and sends real failures back for corrections (up to 3 attempts).",
    entryVerifier:"Creates an independent test and challenges the candidate. When P4 passes, GitHub automatically creates a draft PR; a human decides whether to merge.",
    heroStackLabel:"01 / TECHNOLOGY STACK",
    heroStackDesc:"Orchestration, implementation and independent verification.",
    heroFlowLabel:"02 / CODE DELIVERY WORKFLOW",
    heroFlowDesc:"Three purpose-specific agent roles with deterministic gates in between.",
    flowInputTitle:"Assignment & policy",
    flowInputDesc:"Private specification and human-approved data rules.",
    flowArchitectDesc:"Source profiling and implementation contract.",
    flowEngineerDesc:"New code, tests and failure-driven repairs.",
    flowSandboxTitle:"Sandbox & controller",
    flowSandboxDesc:"Isolated tests, reconciliation and up to 3 attempts.",
    flowVerifierDesc:"Independent pytest and a deliberate negative control.",
    flowReviewDesc:"SHA-bound CI and human review; never auto-merge.",
    flowGovernanceNote:"GitHub Actions controls transitions. The Architect designs the solution — it does not create the other agents. Business policy changes require separate human authorization.",
    skip:"Skip to content",
    navLab:"System",
    verifiedDeliveryLabel:"LATEST VERIFIED RUN / 19 NOV 2026",
    verifiedDeliveryDesc:"Three actual iterations, an independently executed third-agent test, and 18/18 passing candidate tests. Published as a draft PR without replacing the trusted production pipeline.",
    verifiedDeliveryRun:"Execution evidence #44485096373 ↗",
    verifiedDeliveryPR:"Independently verified draft PR #35 ↗",
    verifiedDeliveryCI:"Isolated CI / exact candidate SHA ↗",
    heroLab:"Launch a fresh delivery",
    technicalEyebrow:"IMPLEMENTATION & OPERATIONS",
    technicalHeading:"Technical implementation",
    technicalLead:"Data contracts, change control, agent permissions, event logging and execution procedures. Specifications linked directly to source and artifacts.",
    governanceTitle:"Specification and policy approval",
    governanceDesc:"Task requirements, data-quality policy, business decisions and human approval control. Agents cannot approve their own rules.",
    engineeringTitle:"Implementation and change control",
    engineeringDesc:"Versioned Python code, regression tests, Pandera validation and pull-request review.",
    orchestrationTitle:"Three actual code-delivery roles",
    orchestrationDesc:"Data Architect defines the contract, Data Engineer writes actual code, and Verification Engineer authors independently executed tests. Host-side gates control progression.",
    assuranceTitle:"Independent assurance and provenance",
    assuranceDesc:"Original employer tests, no-network sandbox, independent Decimal oracle, SHA-256, bounded rework and draft PR approval gates.",
    launchHeading:"Launch the complete three-agent Foundry workflow",
    launchLead:"An authorized reviewer can dispatch the complete real Architect → Engineer → Verifier pipeline, with bounded repairs, isolated tests, a draft PR and exact-SHA CI. The server never shares workflow credentials.",
    recordedLink:"Open full delivery workflow in GitHub ↗",
    execStatusLabel:"EXECUTION READINESS",
    execChecking:"Checking connection",
    accessLabel:"Private reviewer access code",
    startRun:"Start full delivery",
    executionLimits:"Launching starts Architect → Engineer → isolated Docker tests and corrections (up to 3 attempts) → Verification Engineer → P4 → automatically created draft PR and separate CI. It normally takes several minutes, often 10–30; with retries or a GitHub queue it can take longer. The current step and source run are shown live. Limit: 5 starts / 24 h, one active.",
    openJob:"Open execution in GitHub Actions ↗",
    implementationDetails:"Runtime modules, permissions and contracts",
    technicalFootnote:"Every transition is controlled by independent source, code or test evidence. A draft PR requires successful gates and a later human decision; agents cannot merge changes automatically.",
    topDate:"GitHub Actions · current runs and archival evidence",
    navTask:"Assignment",navArchitecture:"Architecture",navAgents:"Execution",navData:"Results",navProof:"Evidence",originalRun:"Original run",
    kicker:"DATA ENGINEERING / VERIFIED EXECUTION",
    heroTitle:"An agentic system that builds and verifies Data Engineering code.",
    heroLead:"Three real Microsoft Foundry roles work on the recruitment assignment: Data Architect analyzes requirements, Data Engineer writes code and Verification Engineer independently challenges it. Each stage has test and execution evidence.",
    heroAction:"See what the agents did",heroResult:"Explore the data output",
    resultCard:"ARCHIVED EVIDENCE · P3 / P4 / CI",revenueTag:"Net revenue / 5 regions",
    revenueExplanation:"Computed deterministically — not by AI",
    agentCount:"agent roles",toolCount:"actual code versions",testsCount:"candidate tests",durationCount:"detected mutation",
    sourceEvidence:"Open the original real agent execution",
    taskEyebrow:"THE ASSIGNMENT",taskHeading:"Deliverables and acceptance scope",
    taskLead:"A virtual-column function and sales ETL pipeline. The current workflow uses Data Architect for contracts, Data Engineer for real code changes and Verification Engineer for independent tests.",
    virtualTitle:"Virtual column function",
    virtualDesc:"add_virtual_column(df, role, new_column) computes a new column from a restricted arithmetic expression. An AST allowlist rejects invalid names and operations without evaluating arbitrary code.",
    virtualFooter:"Delivered: function, supplied tests and regression tests.",
    etlTitle:"Net revenue from a messy sales CSV",
    etlDesc:"The export contained duplicates, a repeated header, a TOTAL control row, inconsistent number formats, inconsistent region labels and missing prices. The pipeline validates controls, applies the approved policy and produces revenue_by_region.csv.",
    etlFooter:"Delivered: regional revenue CSV and a data quality report.",
    rawSource:"SOURCE DATA",rawExplain:"rows including repeated header and TOTAL",
    cleanSource:"AFTER CLEANING",cleanExplain:"actual transaction rows",
    finalSource:"RESULT",regionWord:"regions",finalExplain:"totals exact to two decimal places",
    architectureEyebrow:"ARCHITECTURE",architectureHeading:"Data processing and code-delivery architecture",
    architectureLead:"Deterministic financial calculations alongside a controlled process for code design, generation, testing and corrective iterations.",
    laneA:"Computation / no AI",sourceStep:"INPUT",sourceStepDesc:"Unmodified source and versioned cleaning rules.",
    processingStep:"PROCESSING",processingStepDesc:"Source controls, cleaning, deduplication and revenue.",
    resultStep:"OUTPUT",resultStepDesc:"Five regions, quality report, SHA-256 provenance.",
    laneB:"Code delivery / Microsoft Foundry",roleArchitect:"Source profiling, anomalies and assumptions",roleEngineer:"Real code authoring and feedback-driven repairs",roleVerifier:"Independent pytest and controlled mutation test",
    reviewStep:"DELIVERED RESULT",reviewStepDesc:"Real Python source, three attempts, isolated tests, mutation detection and exact-SHA draft PR CI.",
    trustBoundary:"Important trust boundary",
    trustDesc:"The pipeline calculates revenue independently. Agent output remains untrusted until schema-validated, bound to artifact provenance, and checked by deterministic tests. GitHub MCP repository access is read-only.",
    executionEyebrow:"RECORDED EXECUTION",executionHeading:"Actual agent work and three candidate iterations",
    executionLead:"Source-backed execution: contract design, three actual code versions, two rejected candidates, independent Verifier tests and published draft PR.",
    runDate:"DATE",walltime:"WALL TIME",openEvidence:"Open recorded execution ↗",
    whatRan:"WHAT RAN",
    whatRanText:"GitHub Actions executed the pipeline and tests, authenticated to Azure with OIDC, then invoked SequentialBuilder with three reviewers. Each agent had a specific prompt and bounded tools. Pydantic parsed the returned reports and a manifest checked the evidence files against their hashes.",
    reportsHeading:"Archived Microsoft Foundry audit reports",reportsSubheading:"Historically recorded findings and tool boundaries. Current delivery states are shown in the live section above.",
    measureLabel:"RECORDED TELEMETRY",toolHeading:"Recorded tool-call events",
    toolLead:"Sixteen real tool calls were measured with timings. Without per-agent span attribution we do not assign individual calls to specific reviewers.",
    expandEvents:"Expand all 16 measured calls",
    traceLimit:"This is a real tool-call record, not a full distributed trace. Model tokens, costs and individual agent durations were not captured in this run.",
    resultsEyebrow:"DATA OUTPUT",resultsHeading:"ETL output and reconciliation",
    resultsLead:"Regional totals from the committed CSV, source quality measurements and control reconciliations, calculated using Decimal arithmetic.",
    regionsHeading:"Net revenue by region",totalLabel:"TOTAL",cleanHeading:"Data anomalies handled",
    controlHeading:"Control totals reconciled before deduplication",
    controlDesc:"The TOTAL record matched the 1,505 original transactions before five exact duplicates were removed. An independent CSV/Decimal parser then verified the final result.",
    controlQty:"SOURCE QUANTITY",controlDiscount:"SOURCE DISCOUNT",
    improvementsEyebrow:"AUDIT OUTCOMES",improvementsHeading:"Review findings and implemented corrections",
    improvementsLead:"Documented source changes, regression checks and links to pull-request diffs and CI history.",
    testLabel:"tests passed",testProof:"Windows and Ubuntu CI. Separately, a fault-injection lab caught 4/4 seeded code defects and rejected 1/1 corrupted source. That tests the deterministic quality gates, not the LLM agents.",
    ciLink:"Open CI result ↗",faultLink:"Open fault-injection run ↗",
    statusEyebrow:"IMPLEMENTATION STATUS",statusHeading:"Implementation status and operational dependencies",
    statusLead:"Verified evidence is distinguished from features whose cloud configuration or operational validation remains outstanding.",
    doneHeading:"IMPLEMENTED / VERIFIABLE",pendingHeading:"CONFIGURATION OR VALIDATION REQUIRED",
    evidenceEyebrow:"EVIDENCE",evidenceHeading:"Artifacts and provenance",
    evidenceLead:"The audit trail comprises GitHub Actions executions, Foundry reports, source hashes, ETL output and change history.",
    eFoundry:"Actual three-agent Foundry review",eFoundryNote:"Azure OIDC · Foundry · JSON reports · 16 tool calls",
    eTests:"CI and test results",eTestsNote:"79 tests · Windows and Ubuntu · reconciliation",
    eWorkflow:"Autonomous data-engineering workflow implementation",
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
    for(const node of document.querySelectorAll("[data-lang]")){
      node.setAttribute("aria-pressed",String(node.dataset.lang===language));
    }
    const url=new URL(location.href);
    url.searchParams.set("lang",language);
    history.replaceState(null,"",url.pathname+url.search+url.hash);
    document.title=language==="pl"?"CloudFide | Data Engineering i Microsoft Foundry":"CloudFide | Data Engineering & Microsoft Foundry";
    if(data&&trace&&reviews) renderDynamic();
    window.dispatchEvent(new CustomEvent("cloudfide:language",{detail:{language}}));
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
    ["Deterministyczny ETL · pandas / Decimal","Deterministic ETL · pandas / Decimal"],
    ["Kontrole jakości i niezależny oracle CSV","Data-quality checks and independent CSV oracle"],
    ["3 recenzenci Microsoft Agent Framework","3 Microsoft Agent Framework reviewers"],
    ["SequentialBuilder + GitHub Actions OIDC","SequentialBuilder + GitHub Actions OIDC"],
    ["Pydantic · raporty i walidacja manifestu","Pydantic · reports and manifest validation"],
    ["Pandera · kontrakt DataFrame bez konwersji","Pandera · non-coercive DataFrame schema"],
    ["DataDecision · propozycje z dowodami i akceptacją","DataDecision · evidence-linked human-gated proposals"],
    ["124 testy CI na Windows i Ubuntu (najnowszy zestaw)","124 CI tests across Windows and Ubuntu (updated suite)"],
    ["Historyczny przebieg: 16 zmierzonych wywołań","Recorded run: 16 measured tool calls"]
  ];
  const pending=[
    ["Nowe wykonania: prywatny kod; brak automatycznego scalenia PR","Fresh execution requires a private code; PR never auto-merges"],
    ["GitHub MCP: integracja kodu; walidacja przebiegu live","GitHub MCP: integrated; live runtime verification pending"],
    ["Wynik każdego nowego przebiegu jest osobno weryfikowany w P3/P4 i dokładnym SHA CI","Each new run is independently validated by P3/P4 and exact-SHA CI"],
    ["Application Insights: brak potwierdzonego eksportu trace","Application Insights: exporter not verified"],
    ["Koszt modelu: brak potwierdzonych stawek rozliczeniowych","Model cost: deployment billing rates not verified"],
    ["Ewaluacja skuteczności agentów: bez benchmarku","Agent effectiveness evaluation: no independent benchmark"]
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

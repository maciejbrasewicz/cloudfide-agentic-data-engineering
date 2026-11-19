/* Technical execution controls for the unified results-and-system portal.
   Every displayed live event is received through the authenticated server gateway.
   Recorded evidence remains in the main execution section; never simulate events. */
(() => {
  "use strict";
  const root=document.getElementById("reviewer-execution");
  if(!root)return;
  const $=id=>document.getElementById(id);
  const el=(tag,cls,text)=>{
    const node=document.createElement(tag);
    if(cls)node.className=cls;
    if(text!==undefined)node.textContent=String(text);
    return node;
  };
  const isEN=()=>document.documentElement.lang==="en";
  const local=(pl,en)=>isEN()?en:pl;
  const project="https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering";
  const modules=[
    {path:"agentic/spec_loader.py",name:"Specification & provenance",pl:"Oryginalne wymagania przekazywane prywatnie, kontrola integralności i hashy danych.",en:"Private original task input, immutable source fingerprints and provenance checks."},
    {path:"agentic/architect.py",name:"01 / Data Architect",pl:"Rzeczywiste profilowanie źródła, kontrakt wymagań i decyzje sprawdzane niezależną bramką.",en:"Actual source profiling, requirements contract and independently verified policy proposals."},
    {path:"agentic/engineer.py",name:"02 / Data Engineer",pl:"Zapisywanie rzeczywistego kodu, testów i README w izolowanym workspace.",en:"Real code, regression tests and README written inside a restricted candidate workspace."},
    {path:"agentic/workspace.py",name:"Candidate workspace",pl:"Granice zapisu, ochrona oryginalnych plików, SHA-256 i brak uruchamiania kodu z Azure.",en:"Write allowlist, original fixture protection, SHA-256 and deferred code execution."},
    {path:"agentic/p3_oracle.py",name:"03 / Independent sandbox",pl:"Testy oryginalne i wygenerowane, osobny Docker i przeliczenie CSV/Decimal.",en:"Original and generated tests, isolated Docker and independent raw CSV/Decimal oracle."},
    {path:"agentic/rework.py",name:"Bounded remediation",pl:"Poprawka przez tego samego Engineera na podstawie rzeczywistego błędu i poprzednich plików.",en:"Feedback-driven code correction from real failing tests and previous candidate source."},
    {path:"agentic/delivery_status.py",name:"Execution control",pl:"Maksymalnie trzy próby, niezależne decyzje PASS/REJECTED i pełny ślad iteracji.",en:"Three-attempt maximum, independent acceptance gates and full iteration provenance."},
    {path:"agentic/verifier.py",name:"04 / Verification Engineer",pl:"Niezależny test pytest napisany przez trzeciego agenta i walidacja falsyfikacyjna.",en:"A third agent authors original pytest falsification tests that run independently."},
    {path:"agentic/verifier_verdict.py",name:"Adversarial assurance",pl:"Test musi przejść na właściwym kodzie i wykryć kontrolowaną mutację błędnej implementacji.",en:"The test must pass on real code and reject a deliberately corrupted implementation."},
    {path:"agentic/publisher_prepare.py",name:"Human-reviewed delivery",pl:"Publikacja tylko zweryfikowanych plików, draft PR i oddzielny CI na konkretnym SHA.",en:"SHA-bound source publication, a human-reviewed draft PR and separate exact-commit CI."},
    {path:".github/workflows/engineer-e2e.yml",name:"GitHub Actions / Foundry",pl:"Jedno uruchomienie całego procesu, federacja OIDC tylko dla zaufanych etapów.",en:"One canonical delivery workflow; Azure OIDC only in trusted agent jobs."},
    {path:"showcase/delivery_gateway.mjs",name:"Public execution evidence",pl:"Bieżące joby pobierane z publicznego GitHub API; bez symulowanych stanów.",en:"Current jobs obtained from public GitHub API, without synthetic execution states."}
  ];
  const state={enabled:false,id:null,timer:null,polling:false,lastRun:null,submittedAt:null,workflowUrl:null};
  const storageKey="cloudfide.reviewer.run.v1";
  const store=()=>{try{if(state.id)sessionStorage.setItem(storageKey,JSON.stringify({id:state.id,submittedAt:state.submittedAt,workflowUrl:state.workflowUrl}));else sessionStorage.removeItem(storageKey);}catch{/* private code is never stored */}};
  const restore=()=>{try{const x=JSON.parse(sessionStorage.getItem(storageKey)||"null");if(x&&typeof x.id==="string"&&x.id.length===36){state.id=x.id;state.submittedAt=x.submittedAt;state.workflowUrl=x.workflowUrl;}}catch{/* optional */}};
  function renderModules(){
    const node=$("technical-modules");node.replaceChildren();
    for(const item of modules){
      const article=el("article","technical-module");
      const head=el("div","");
      head.append(el("strong","",item.name),el("p","",local(item.pl,item.en)));
      const anchor=el("a","technical-module-link",local("Źródło ↗","Source ↗"));
      anchor.href=project+"/blob/main/"+item.path;
      anchor.target="_blank";anchor.rel="noopener noreferrer";
      anchor.setAttribute("aria-label",item.path);
      article.append(head,anchor);node.append(article);
    }
  }
  const milestones=[
    ["architect","Data Architect · analiza wymagań","Data Architect · requirements","architect"],
    ["engineer","Data Engineer · napisanie kodu","Data Engineer · code authoring","engineer"],
    ["sandbox","P3 · niezależne testy w Dockerze","P3 · independent Docker tests","Verify P2 code inside no-network, no-secret Docker sandbox"],
    ["repair2","Poprawka · druga próba","Correction · attempt two","Data Engineer repairs actual P3 failing tests (iteration 2)"],
    ["sandbox2","Docker · test drugiej próby","Docker · validate attempt two","Verify corrected P5 round-2 code in independent sandbox"],
    ["repair3","Poprawka · trzecia próba","Correction · attempt three","Data Engineer third and final evidence-driven correction (iteration 3)"],
    ["sandbox3","Docker · test trzeciej próby","Docker · validate attempt three","Verify final P5 round-3 candidate in independent sandbox"],
    ["p5","P5 · kontrola wyników i wybór wersji","P5 · evidence-based selection","Deterministic 3-round delivery state and strict evidence verification"],
    ["verifier","Verification Engineer · własny test","Verification Engineer · new test","Independent Foundry Verification Engineer proposes real falsification test"],
    ["p4","P4 · niezależny test i kontrprzykład","P4 · independent test and mutation","Execute Verifier test independently and prove mutation sensitivity"],
    ["pr","P6 · automatyczny draft PR","P6 · automatic draft PR","Publish verified P4 candidate as human-reviewed draft PR (no Azure)"],
    ["accept","Końcowa kontrola dostarczenia","Final delivery acceptance","Final fail-closed P5/P4/P6 acceptance (never infer from green jobs alone)"]
  ];
  function cleanUrl(value){
    try{const url=new URL(value);return url.protocol==="https:"&&url.hostname==="github.com"&&
      url.pathname.startsWith("/maciejbrasewicz/cloudfide-agentic-data-engineering/")?url.href:null;}catch{return null;}
  }
  function statusText(job){
    if(!job)return local("Oczekuje na wcześniejsze etapy","Awaiting previous stages");
    if(job.conclusion==="success")return local("Zakończono","Completed");
    if(job.conclusion==="failure"||job.conclusion==="timed_out")return local("BŁĄD","FAILED");
    if(job.conclusion==="skipped")return local("Pominięto","Skipped");
    if(job.conclusion==="cancelled")return local("Anulowano","Cancelled");
    if(job.status==="in_progress")return local("W TRAKCIE","RUNNING");
    return local("W kolejce","Queued");
  }
  function minutes(value){
    const delta=Date.now()-Date.parse(value||"");
    if(!Number.isFinite(delta)||delta<0)return "";
    return delta<60_000?local("poniżej minuty","under a minute"):Math.round(delta/60_000)+" min";
  }
  function renderRun(run){
    state.lastRun=run;
    const jobs=Array.isArray(run.jobs)?run.jobs:[];
    const stages=$("technical-job-steps"),extra=$("technical-live-events");
    const outcome=$("technical-run-outcome"),meta=$("technical-run-meta");
    const explain=$("technical-run-explainer"),title=$("technical-run-title");
    stages.replaceChildren();extra.replaceChildren();outcome.replaceChildren();meta.replaceChildren();
    const link=$("technical-run-link");
    const target=cleanUrl(run.githubRunUrl||run.workflowUrl||state.workflowUrl);
    if(target){link.href=target;link.hidden=false;}else link.hidden=true;
    title.textContent=run.githubRunId?"GitHub Actions #"+run.githubRunId:
      local("Zlecenie przekazane do GitHub Actions","Request submitted to GitHub Actions");
    const duration=minutes(run.createdAt||state.submittedAt);
    if(duration)meta.append(el("span","",local("Od startu: ","Elapsed: ")+duration));
    meta.append(el("span","",local("Aktualizacja co 6 sekund","Updated every 6 seconds")));
    const awaiting=run.status==="awaiting_github_run"||run.status==="dispatching";
    const finished=run.status==="completed";
    const active=jobs.find(j=>j.status==="in_progress");
    const failure=jobs.find(j=>j.conclusion==="failure");
    if(awaiting){
      const longWait=Date.now()-Date.parse(state.submittedAt||"")>150_000;
      explain.textContent=longWait?
        local("GitHub nie potwierdził numeru wykonania. Sprawdź link GitHub — nie deklarujemy pracy agentów bez dowodu.",
              "GitHub has not confirmed the run ID. Check the GitHub link; agent execution is unverified."):
        local("GitHub przyjął zlecenie. Oczekujemy na identyfikator i pierwsze joby. Nie oznacza to jeszcze uruchomienia modeli.",
              "GitHub accepted the dispatch. Awaiting the real run ID and first jobs; the models are not yet confirmed running.");
      const li=el("li","technical-milestone pending");
      li.append(el("strong","",local("Oczekiwanie na GitHub Actions","Awaiting GitHub Actions")),
                el("small","",local("Brak potwierdzonego joba","No confirmed job yet")));
      stages.append(li);
    }else{
      if(finished){
        explain.textContent=run.conclusion==="success"?
          local("Workflow zakończony. Sprawdź poniżej potwierdzony PR i osobne CI; samo zakończenie nie wystarcza do akceptacji.",
                "Workflow finished. Check the draft PR and exact-SHA CI; completion alone does not verify delivery."):
          local("Wykonanie zakończyło się niepowodzeniem. Zobacz etap i przyczynę w GitHub Actions. Bez P4 nie tworzymy PR.",
                "Execution failed. Review the failed stage in GitHub Actions. No draft PR is created without P4.");
      }else if(active){
        const m=milestones.find(p=>p[3]===active.name);
        const step=active.steps?.find(s=>s.status==="in_progress");
        explain.textContent=local("Teraz: ","Now: ")+(m?local(m[1],m[2]):active.name)+(step?" · "+step.name:"");
      }else explain.textContent=local("GitHub czeka na uruchomienie kolejnego joba.","GitHub is preparing the next job.");
      for(const phase of milestones){
        const job=jobs.find(j=>j.name===phase[3]);
        if(phase[0].startsWith("repair")||phase[0].startsWith("sandbox2")||phase[0]==="sandbox3"){
          if(!job||job.conclusion==="skipped")continue;
        }
        const cls=job?.conclusion==="success"?"passed":
          job?.conclusion==="failure"?"failed":
          job?.status==="in_progress"?"running":
          job?.conclusion==="skipped"?"skipped":"pending";
        const item=el("li","technical-milestone "+cls);
        item.append(el("strong","",local(phase[1],phase[2])),el("small","",statusText(job)));
        const current=job?.steps?.find(s=>s.status==="in_progress"||s.conclusion==="failure");
        if(current)item.append(el("p","",current.name));
        stages.append(item);
      }
    }
    const pub=run.publication;
    if(pub?.pullRequest?.draft===true&&cleanUrl(pub.pullRequest.url)){
      const card=el("div","technical-publication");
      card.append(el("strong","",local("Automatycznie utworzony draft PR #","Auto-created draft PR #")+pub.pullRequest.number));
      card.append(el("p","",local("Do utworzenia PR nie jest potrzebna zgoda rekrutera. Dopiero scalenie kodu wymaga przeglądu człowieka.",
        "No reviewer approval is needed to CREATE the draft PR; only merging requires human review.")));
      const a=el("a","technical-pr-link",local("Otwórz wygenerowany kod / PR ↗","Open generated code / PR ↗"));
      a.href=cleanUrl(pub.pullRequest.url);a.target="_blank";a.rel="noopener noreferrer";card.append(a);
      if(pub.exactCi)card.append(el("small","",local("Oddzielne CI na SHA: ","Separate exact-SHA CI: ")+pub.exactCi.state));
      outcome.append(card);
    }else{
      outcome.append(el("p",finished?"technical-run-failure":"technical-awaiting-publication",
        finished?local("Nie potwierdzono nowego draft PR. Weryfikacja mogła odrzucić kod; sprawdź szczegóły GitHub.",
          "No new draft PR is confirmed. The candidate may have failed verification; inspect GitHub evidence."):
        local("Po pozytywnej weryfikacji P4 GitHub automatycznie utworzy draft PR. Link pojawi się tutaj.",
          "After successful P4, GitHub automatically creates a draft PR and its link appears here.")));
    }
    if(failure){
      const failedStep=failure.steps?.find(s=>s.conclusion==="failure");
      outcome.append(el("p","technical-run-failure",local("Niepowodzenie: ","Failed: ")+failure.name+(failedStep?" · "+failedStep.name:"")));
    }
    for(const job of jobs){
      const d=el("div","technical-raw-job");
      d.append(el("strong","",job.name+" · "+statusText(job)));
      const href=cleanUrl(job.url);
      if(href){const a=el("a","",local("Otwórz job ↗","Open job ↗"));a.href=href;a.target="_blank";a.rel="noopener noreferrer";d.append(a);}
      for(const step of job.steps||[]){
        if(step.status==="in_progress"||step.conclusion==="failure"||step.conclusion==="success")
          d.append(el("p","",statusText(step)+" · "+step.name));
      }
      extra.append(d);
    }
    if(jobs.length===0)extra.append(el("p","",local("Brak jobów potwierdzonych przez GitHub.","No jobs confirmed by GitHub yet.")));
  }
  const errors={
    invalid_access_code:["Nieprawidłowy kod dostępu.","Invalid access code."],
    daily_limit_or_active_run:["Limit uruchomień lub aktywny przebieg.","Run limit exceeded or execution already active."],
    github_dispatch_failed:["Zlecenie do GitHub Actions zostało odrzucone.","GitHub Actions rejected the execution request."],
    too_many_attempts:["Przekroczony limit prób uwierzytelnienia.","Too many authentication attempts."],
    full_delivery_not_provisioned:["Uruchomienie pełnych agentów wymaga tokenu Actions i kodu recenzenta na serwerze.","Launching full agents requires a scoped Actions token and reviewer code on the server."],
    daily_quota_or_active_execution:["Dzienny limit uruchomień lub inny aktywny przebieg.","Daily quota reached or another execution active."],
    session_not_found_or_expired:["Przebieg jest niedostępny po wygaśnięciu sesji.","Run unavailable after the session expired."],
    origin_not_allowed:["Żądanie nie pochodzi z tego serwisu.","Request origin is not permitted."]
  };
  const err=(key)=>local(...(errors[key]||["Nie udało się zrealizować żądania.","Request could not be completed."]));
  async function capabilities(){
    try{
      const response=await fetch("/api/delivery/launch/capabilities",{cache:"no-store"});
      if(!response.ok)throw Error("gateway_unavailable");
      const info=await response.json();
      state.enabled=info.liveReady===true;
      $("technical-availability").textContent=state.enabled?
        local("Gotowe do uruchomienia agentów","Ready to launch agents"):
        local("Uruchomienia nowych agentów niedostępne","New agent execution unavailable");
      $("technical-availability-note").textContent=state.enabled?
        local("Kod uruchamia nowe wykonanie: Architect przygotuje kontrakt, Engineer napisze kod, Docker go przetestuje, a Verifier niezależnie zweryfikuje wynik. Po P4 powstanie automatyczny draft PR.",
              "The code starts a fresh run: Architect designs the contract, Engineer writes code, Docker tests it, and Verifier challenges it independently. A successful P4 automatically creates a draft PR."):
        local("Start wymaga prywatnej konfiguracji serwera. Archiwalne wykonanie pozostaje dostępne.",
              "Starting new agents requires private server configuration. Historical evidence remains available.");
      $("technical-indicator").classList.toggle("available",state.enabled);
      $("technical-start").disabled=!state.enabled||Boolean(state.id);
    }catch{
      state.enabled=false;
      $("technical-availability").textContent=local("Brak połączenia z usługą","Execution service unavailable");
      $("technical-availability-note").textContent=local("Dane historyczne są nadal dostępne.","Historical evidence remains available.");
      $("technical-start").disabled=true;
    }
  }
  async function poll(){
    if(!state.id||state.polling)return;
    state.polling=true;
    try{
      const response=await fetch("/api/delivery/launch/session/"+encodeURIComponent(state.id),{cache:"no-store"});
      const run=await response.json();
      if(!response.ok)throw Error(run.error||"gateway_error");
      renderRun(run);
      $("technical-error").textContent="";
      if(run.status==="completed"){
        const publisher=(run.jobs||[]).find(j=>j.name==="Publish verified P4 candidate as human-reviewed draft PR (no Azure)");
        const ci=run.publication?.exactCi?.state;
        const finalized=["success","failure","error"].includes(ci);
        const referenceTime=Date.parse(run.updatedAt||state.submittedAt||"");
        const stillChecking=publisher?.conclusion==="success"&&!finalized&&
          Number.isFinite(referenceTime)&&Date.now()-referenceTime<600_000;
        if(stillChecking){
          // The source workflow can finish before separate exact-SHA CI.
          // Keep polling its immutable PR SHA until CI finishes or times out.
          $("technical-start").disabled=true;
        }else{
          clearInterval(state.timer);state.timer=null;
          state.id=null;store();
          $("technical-start").disabled=!state.enabled;
          void capabilities();
        }
      }
    }catch(e){$("technical-error").textContent=err(e.message);}
    finally{state.polling=false;}
  }
  async function start(event){
    event.preventDefault();
    if(!state.enabled||state.id)return;
    const field=$("technical-access"),accessCode=field.value;
    if(accessCode.length<24){$("technical-error").textContent=err("invalid_access_code");return;}
    $("technical-start").disabled=true;
    $("technical-error").textContent="";
    try{
      const response=await fetch("/api/delivery/launch",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({accessCode})
      });
      const result=await response.json();
      if(!response.ok)throw Error(result.error||"github_delivery_dispatch_failed");
      field.value="";
      state.id=result.id;state.submittedAt=result.submittedAt||new Date().toISOString();
      state.workflowUrl=result.workflowUrl||null;store();
      $("technical-run").hidden=false;
      renderRun({id:state.id,status:"awaiting_github_run",jobs:[],publication:{status:"not_yet_available"},workflowUrl:state.workflowUrl});
      await poll();
      if(state.id&&!state.timer)state.timer=setInterval(poll,6000);
    }catch(e){
      $("technical-error").textContent=err(e.message);
      $("technical-start").disabled=false;
    }
  }
  window.addEventListener("cloudfide:language",()=>{
    renderModules();
    if(state.lastRun)renderRun(state.lastRun);
    if(!state.id)void capabilities();
  });
  $("technical-start-form").addEventListener("submit",start);
  renderModules();restore();void capabilities();
  if(state.id){
    $("technical-run").hidden=false;
    renderRun({status:"awaiting_github_run",jobs:[],publication:{status:"not_yet_available"},workflowUrl:state.workflowUrl});
    void poll();
    if(!state.timer)state.timer=setInterval(poll,6000);
  }
})();

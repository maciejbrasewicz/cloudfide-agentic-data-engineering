/* Technical execution controls for the unified results-and-system portal.
   Every displayed live event is received through the authenticated server gateway.
   Recorded evidence remains in the main execution section; never simulate events. */
(() => {
  "use strict";
  const root=document.getElementById("technical");
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
  const state={enabled:false,id:null,timer:null,polling:false};
  const sessionKey="cloudfide-active-review-request";
  const uuidPattern=/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  try{
    const saved=sessionStorage.getItem(sessionKey);
    if(uuidPattern.test(saved||""))state.id=saved;
  }catch{/* Restricted browser storage must not break the portal. */}
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
      if(!response.ok)throw Error("bad_gateway");
      const info=await response.json();
      state.enabled=info.liveReady===true;
      $("technical-availability").textContent=state.enabled?
        local("Dostępne po autoryzacji","Available with authorization"):
        local("Uruchomienia na żądanie — nieaktywne","On-demand execution — not configured");
      $("technical-availability-note").textContent=state.enabled?
        local("Kod autoryzuje rzeczywiste wykonanie Architect → Engineer → Verifier, do trzech prób z niezależnymi testami.","The code authorizes real Architect → Engineer → Verifier execution, up to three attempts with independent tests."):
        local("Pełny start agentów wymaga konfiguracji serwera. Rekruter może już oglądać ich rzeczywistą pracę i uruchomić niezależne przeliczenie CSV powyżej.","Server configuration is required for paid full-agent launch. The reviewer can already inspect real agent work and rerun independent CSV verification above.");
      $("technical-indicator").classList.toggle("available",state.enabled);
      $("technical-start").disabled=!state.enabled||Boolean(state.id);
    }catch{
      state.enabled=false;
      $("technical-availability").textContent=local("Bramka wykonawcza niedostępna","Execution gateway unavailable");
      $("technical-availability-note").textContent=local("Historyczne wykonanie jest nadal dostępne.","The recorded execution remains accessible.");
      $("technical-start").disabled=true;
    }
  }
  function appendEvent(record){
    const line=el("div","execution-event");
    const seq=el("small","event-seq",String(record.seq).padStart(3,"0"));
    const body=el("div","");
    const p=record.payload||{};
    const type=record.type==="agent.completed"?local("Raport agenta","Agent report"):
      record.type==="tool.completed"?local("Narzędzie","Tool"):
      record.type==="agent.timing"?local("Czas agenta","Agent timing"):record.type;
    body.append(el("strong","",type+(p.role?" · "+p.role:"")+(p.tool?" · "+p.tool+"()":"")));
    if(typeof p.summary==="string")body.append(el("p","",p.summary));
    else if(Number.isFinite(p.duration_ms))body.append(el("p","",String(p.duration_ms)+" ms · "+(p.status||"")));
    else if(Number.isFinite(p.total_ms))body.append(el("p","",String(p.total_ms)+" ms"));
    body.append(el("small","",record.classification+" · "+record.at_utc));
    line.append(seq,body);return line;
  }
  async function poll(){
    if(!state.id||state.polling)return;
    state.polling=true;
    try{
      const response=await fetch("/api/delivery/launch/session/"+encodeURIComponent(state.id),{cache:"no-store"});
      const run=await response.json();
      if(!response.ok)throw Error(run.error||"gateway_error");
      $("technical-run-title").textContent=local("Wykonanie","Execution")+" "+state.id.slice(0,8)+" · "+run.status+(run.conclusion?" / "+run.conclusion:"");
      const anchor=$("technical-run-link");
      if(run.githubRunUrl){
        const url=new URL(run.githubRunUrl);
        if(url.protocol==="https:"&&url.hostname==="github.com"){anchor.href=url.href;anchor.hidden=false;}
      }
      const steps=$("technical-job-steps");steps.replaceChildren();
      for(const job of run.jobs||[]){
        const duration=Number.isFinite(job.jobDurationMs)?
          " · "+(job.jobDurationMs/1000).toFixed(1)+" s "+local("czas joba","job elapsed"):"";
        const header=el("strong","execution-job-name",job.name+" · "+job.status+duration);
        steps.append(header);
        for(const stage of job.steps||[]){
          const cls=stage.conclusion==="success"?"passed":stage.conclusion==="failure"?"failed":stage.status==="in_progress"?"running":"";
          const row=el("div","execution-step "+cls);
          row.append(el("span","",stage.name),el("small","",stage.conclusion||stage.status||"pending"));
          steps.append(row);
        }
      }
      const events=$("technical-live-events");events.replaceChildren();
      for(const e of run.events||[])events.append(appendEvent(e));
      if(run.status==="completed"){
        clearInterval(state.timer);state.timer=null;
        $("technical-start").disabled=true;
      }
      $("technical-error").textContent="";
    }catch(e){$("technical-error").textContent=err(e.message);}
    finally{state.polling=false;}
  }
  async function start(event){
    event.preventDefault();
    if(!state.enabled||state.id)return;
    const input=$("technical-access");const accessCode=input.value;
    if(accessCode.length<20){$("technical-error").textContent=err("invalid_access_code");return;}
    $("technical-start").disabled=true;
    $("technical-error").textContent="";
    try{
      const response=await fetch("/api/delivery/launch",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({accessCode})
      });
      const body=await response.json();
      if(!response.ok)throw Error(body.error||"gateway_error");
      input.value="";
      if(!uuidPattern.test(body.id||""))throw Error("invalid_session_id");
      state.id=body.id;
      try{sessionStorage.setItem(sessionKey,state.id);}catch{}
      $("technical-run").hidden=false;
      await poll();
      state.timer=setInterval(poll,6000);
    }catch(e){
      $("technical-error").textContent=err(e.message);
      $("technical-start").disabled=false;
    }
  }
  function resetSessionView(){
    if(state.timer){clearInterval(state.timer);state.timer=null;}
    state.id=null;
    try{sessionStorage.removeItem(sessionKey);}catch{}
    $("technical-run").hidden=true;
    $("technical-run-link").hidden=true;
    $("technical-job-steps").replaceChildren();
    $("technical-live-events").replaceChildren();
    $("technical-error").textContent="";
    capabilities();
  }
  function translateView(){
    renderModules();
    $("technical-clear-session").textContent=local(
      "Otwórz formularz nowego wykonania (poprzedni proces trwa dalej)",
      "Open new execution form (previous run continues)"
    );
    if(!state.id)capabilities();
  }
  $("technical-clear-session").addEventListener("click",resetSessionView);
  window.addEventListener("cloudfide:language",translateView);
  $("technical-start-form").addEventListener("submit",start);
  renderModules();capabilities();
  if(state.id){
    $("technical-run").hidden=false;
    poll();
    state.timer=setInterval(poll,6000);
  }
})();

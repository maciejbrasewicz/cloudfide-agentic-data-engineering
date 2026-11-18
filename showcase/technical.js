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
    {path:"contracts/data_policy.json",name:"DataPolicy",pl:"Wersjonowane reguły czyszczenia i zatwierdzony zakres automatycznych korekt.",en:"Versioned cleaning rules and an approved scope of automated corrections."},
    {path:"solution.py",name:"Virtual column / AST",pl:"Dozwolona gramatyka wyrażeń; odrzucenie niedozwolonych operacji.",en:"Allowlisted expression grammar; invalid operations fail closed."},
    {path:"dataframe_contracts.py",name:"Pandera · DataFrame contract",pl:"Niezależna walidacja typów, wartości Decimal i arytmetyki bez konwersji.",en:"Independent validation of Decimal types and arithmetic without coercion."},
    {path:"agentic/run.py",name:"Microsoft Agent Framework",pl:"SequentialBuilder, trzy role, kontrolowany zestaw narzędzi i manifest wykonania.",en:"SequentialBuilder, three roles, scoped tools and execution manifest."},
    {path:"agentic/github_mcp.py",name:"GitHub MCP · read-only",pl:"Ograniczony token GitHub Actions; brak uprawnień do zapisu w repozytorium.",en:"Scoped GitHub Actions token; no repository write permissions."},
    {path:"agentic/decision_ledger.py",name:"DataDecision / approval control",pl:"Propozycje z dowodami i hashami raportów; brak automatycznego zatwierdzenia.",en:"Evidence-linked proposals and report hashes; no autonomous approval."},
    {path:"agentic/review_metrics.py",name:"Run-level metrics",pl:"Pomiar czasu każdego agenta, tokeny wyłącznie z danych SDK, bez szacowanych kosztów.",en:"Per-agent timings, SDK-reported token counters only, no invented costs."},
    {path:"agentic/coding_proposal.py",name:"Regression author",pl:"Wygenerowany test przechodzi izolowane CI, następnie powstaje draft PR.",en:"Generated test runs in isolated CI; only then may a draft PR be opened."},
    {path:".github/workflows/agent-review.yml",name:"CI / OIDC / provenance",pl:"Wykonanie w GitHub Actions, federacja Azure, dowody i walidacja raportów.",en:"GitHub Actions execution, Azure federation, evidence and report validation."},
    {path:"showcase/live_gateway.mjs",name:"Execution API",pl:"Autoryzacja, limit uruchomień i kryptograficzna weryfikacja zdarzeń runnera.",en:"Authentication, run limits and cryptographic runner event verification."}
  ];
  const state={enabled:false,id:null,timer:null,polling:false};
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
    live_not_provisioned:["Usługa nie ma skonfigurowanego dostępu do GitHub Actions.","GitHub Actions dispatch access has not been configured."],
    session_not_found_or_expired:["Przebieg jest niedostępny po wygaśnięciu sesji.","Run unavailable after the session expired."],
    origin_not_allowed:["Żądanie nie pochodzi z tego serwisu.","Request origin is not permitted."]
  };
  const err=(key)=>local(...(errors[key]||["Nie udało się zrealizować żądania.","Request could not be completed."]));
  async function capabilities(){
    try{
      const response=await fetch("/api/live/capabilities",{cache:"no-store"});
      if(!response.ok)throw Error("bad_gateway");
      const info=await response.json();
      state.enabled=info.liveReady===true;
      $("technical-availability").textContent=state.enabled?
        local("Dostępne po autoryzacji","Available with authorization"):
        local("Uruchomienia na żądanie — nieaktywne","On-demand execution — not configured");
      $("technical-availability-note").textContent=state.enabled?
        local("Po podaniu kodu uruchomimy istniejący workflow w GitHub Actions.","The access code authorizes dispatch of the existing GitHub Actions workflow."):
        local("Wymagany jest ograniczony token GitHub Actions i kod dostępu skonfigurowany na serwerze. Historyczny przebieg Foundry i raporty są dostępne powyżej.","A scoped GitHub Actions token and reviewer access code must be configured server-side. The recorded Foundry run remains available above.");
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
      const response=await fetch("/api/live/session/"+encodeURIComponent(state.id),{cache:"no-store"});
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
        const header=el("strong","execution-job-name",job.name+" · "+job.status);
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
      const response=await fetch("/api/live/start",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({accessCode})
      });
      const body=await response.json();
      if(!response.ok)throw Error(body.error||"gateway_error");
      input.value="";
      state.id=body.id;
      $("technical-run").hidden=false;
      await poll();
      state.timer=setInterval(poll,6000);
    }catch(e){
      $("technical-error").textContent=err(e.message);
      $("technical-start").disabled=false;
    }
  }
  window.addEventListener("cloudfide:language",()=>{renderModules();if(!state.id)capabilities();});
  $("technical-start-form").addEventListener("submit",start);
  renderModules();capabilities();
})();

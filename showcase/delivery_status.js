/* Unified portal: current public GitHub Actions states, never synthetic traces. */
(() => {
  "use strict";
  const root=document.getElementById("delivery-evidence");
  if(!root)return;
  const statusNode=document.getElementById("delivery-live-state");
  const jobsNode=document.getElementById("delivery-jobs");
  const heading=document.getElementById("delivery-status-title");
  const lead=document.getElementById("delivery-status-lead");
  const note=document.getElementById("delivery-proof-note");
  const published=document.getElementById("delivery-publication");
  const isEN=()=>document.documentElement.lang==="en";
  const choose=(pl,en)=>isEN()?en:pl;
  const core=new Set([
    "architect","engineer","sandbox-validate","p5-state",
    "verifier","adversarial","publish-draft-pr"
  ]);
  const names={
    architect:["Data Architect","Data Architect"],
    engineer:["Data Engineer","Data Engineer"],
    "sandbox-validate":["Niezależne testy P3","P3 independent sandbox"],
    "rework-r2":["Data Engineer · poprawka 2","Data Engineer · correction 2"],
    "sandbox-rework-r2":["Sandbox · poprawka 2","Sandbox · correction 2"],
    "rework-r3":["Data Engineer · poprawka 3","Data Engineer · correction 3"],
    "sandbox-rework-r3":["Sandbox · poprawka 3","Sandbox · correction 3"],
    "p5-state":["Kontroler prób i dowodów","Deterministic state controller"],
    verifier:["Verification Engineer","Verification Engineer"],
    adversarial:["Weryfikacja i kontrprzykład P4","P4 independent falsification"],
    "publish-draft-pr":["Draft PR do przeglądu","Human-reviewed draft PR"]
  };
  const statuses={
    success:["Job zakończony pomyślnie","Job completed successfully"],
    failure:["Job zakończony błędem","Job failed"],
    skipped:["Pominięty","Skipped"],
    cancelled:["Anulowany","Cancelled"],
    in_progress:["Wykonywany","In progress"],
    queued:["W kolejce","Queued"],
    pending:["Oczekuje","Pending"],
    waiting:["Oczekuje","Waiting"],
    not_started:["Nie rozpoczęto","Not started"],
    unknown:["Brak danych","Unknown"]
  };
  let latest=null;

  function el(tag,className,value){
    const node=document.createElement(tag);
    if(className)node.className=className;
    if(value!==undefined)node.textContent=String(value);
    return node;
  }
  function label(key){
    const pair=statuses[key]||statuses.unknown;
    return pair[isEN()?1:0];
  }
  function render(){
    heading.textContent=choose("Autonomiczny proces Data Engineering","Autonomous Data Engineering delivery");
    lead.textContent=choose(
      "Rzeczywiste role, testy i bramki dostarczenia kodu. Dane pobierane z publicznego GitHub Actions.",
      "Actual agent roles, tests, and delivery gates, retrieved from public GitHub Actions."
    );
    note.textContent=choose(
      "Zielony status joba nie jest decyzją o akceptacji kodu. Potwierdzeniem są artefakty bramek P3–P6 i niezależne testy dostępne przy wykonaniu.",
      "A green job status alone does not accept the code. The P3–P6 gate artifacts and independent test results are authoritative."
    );
    jobsNode.replaceChildren();
    published.replaceChildren();
    if(!latest){
      statusNode.textContent=choose("Odczytywanie aktualnego przebiegu…","Loading current execution…");
      return;
    }
    if(!latest.available||!latest.run){
      statusNode.textContent=choose(
        "Nie udało się potwierdzić aktualnego wykonania. GitHub Actions pozostaje dostępne przez link obok.",
        "Current run could not be verified. Use the GitHub Actions link to view the source."
      );
      return;
    }
    const run=latest.run;
    const text=el("div","delivery-run-label");
    const headingText=choose("Ostatni przebieg","Latest run")+" #"+run.id;
    const state=label(run.conclusion||run.status);
    text.append(el("strong","",headingText),el("span","",state));
    if(latest.stale){
      text.append(el("small","delivery-stale",choose(
        "Ostatni potwierdzony odczyt; GitHub API jest chwilowo niedostępne.",
        "Last verified snapshot; GitHub API is temporarily unavailable."
      )));
    }
    const link=el("a","delivery-run-source",choose(
      "Otwórz oryginalny przebieg i artefakty ↗",
      "Open source run and original artifacts ↗"
    ));
    try{
      const url=new URL(run.url);
      if(url.protocol==="https:"&&url.hostname==="github.com"&&
          /^\/maciejbrasewicz\/cloudfide-agentic-data-engineering\/actions\/runs\/\d+$/.test(url.pathname)){
        link.href=url.href;link.target="_blank";link.rel="noopener noreferrer";
      }else throw Error("Untrusted URL");
    }catch{link.removeAttribute("href");}
    statusNode.replaceChildren(text,link);

    const rows=(latest.phases||[]).filter(item=>
      core.has(item.id)||(
        names[item.id]&&item.status!=="not_started"&&item.conclusion!=="skipped"
      )
    );
    for(const item of rows){
      const article=el("div","delivery-job","");article.setAttribute("role","listitem");
      const name=names[item.id]||[item.label,item.label];
      article.append(
        el("strong","",name[isEN()?1:0]),
        el("small", "delivery-job-status "+(
          item.conclusion==="success"?"passed":
          item.conclusion==="failure"?"failed":
          item.status==="in_progress"?"running":""
        ),label(item.conclusion||item.status))
      );
      jobsNode.append(article);
    }
    const result=latest.publication;
    if(result?.status==="verified_draft_awaiting_human"&&result.pullRequest?.draft===true){
      const row=el("div","delivery-published");
      row.append(el("strong","",choose("Kod opublikowany i zweryfikowany przez osobne CI","Published source independently verified by CI")));
      row.append(el("small","",choose("Draft PR · wymagany przegląd człowieka · exact-SHA CI: SUCCESS","Draft PR · human review required · exact-SHA CI: SUCCESS")));
      const link=el("a","delivery-run-source","PR #"+result.pullRequest.number+" ↗");
      const href=result.pullRequest.url;
      if(typeof href==="string"&&/^https:\/\/github\.com\/maciejbrasewicz\/cloudfide-agentic-data-engineering\/pull\/\d+$/.test(href)){
        link.href=href;link.target="_blank";link.rel="noopener noreferrer";row.append(link);
      }
      published.append(row);
    }else if(result?.status==="draft_ci_not_confirmed"){
      published.append(el("p","delivery-pending-ci",choose("Draft PR utworzony; dokładny commit czeka na potwierdzenie niezależnego CI.","Draft PR created; exact commit is still awaiting independent CI confirmation.")));
    }
  }
  async function refresh(){
    try{
      const response=await fetch("/api/delivery/latest",{cache:"no-store"});
      const body=await response.json();
      if(!response.ok||!body||typeof body!=="object")throw Error("Unavailable");
      latest=body;
    }catch{
      latest={available:false};
    }
    render();
  }
  window.addEventListener("cloudfide:language",render);
  render();
  refresh();
  setInterval(refresh,90_000);
})();

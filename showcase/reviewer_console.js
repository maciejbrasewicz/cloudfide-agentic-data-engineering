/* Real-world CloudFide agent execution inspector: no simulated progress or test claims. */
(() => {
  "use strict";
  const root=document.getElementById("reviewer-workspace");
  if(!root)return;
  const $=id=>document.getElementById(id);
  const isEN=()=>document.documentElement.lang==="en";
  const loc=(pl,en)=>isEN()?en:pl;
  const node=(tag,cls,text)=>{
    const n=document.createElement(tag);
    if(cls)n.className=cls;
    if(text!==undefined)n.textContent=String(text);
    return n;
  };
  const URL_PREFIX="https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/";
  const safeLink=(url)=>{
    try{
      const parsed=new URL(url);
      return parsed.protocol==="https:"&&parsed.href.startsWith(URL_PREFIX)?parsed.href:null;
    }catch{return null;}
  };
  let data=null,active=0,lastRecalculation=null,checking=false;
  const statusNames={
    PASSED:["Zaliczone","Passed"],
    FAILED:["Odrzucone przez testy","Failed by tests"]
  };
  const detail=$("reviewer-stage-detail"),tabs=$("reviewer-stage-tabs");
  function addLink(to,title,cls="reviewer-link"){
    const href=safeLink(to);
    if(!href)return node("span","",title);
    const link=node("a",cls,title);
    link.href=href;link.target="_blank";link.rel="noopener noreferrer";
    return link;
  }
  function renderButtons(){
    tabs.replaceChildren();
    if(!data)return;
    for(const [i,stage] of data.stages.entries()){
      const b=node("button","reviewer-stage-tab",stage.role);
      b.type="button";b.setAttribute("role","tab");
      b.setAttribute("aria-selected",i===active?"true":"false");
      b.setAttribute("tabindex",i===active?"0":"-1");
      if(stage.status==="FAILED")b.classList.add("is-failed");
      if(i===active)b.classList.add("is-selected");
      b.append(node("small","",stage.status==="PASSED"?loc("Zaliczone","Passed"):loc("Błąd wykryty","Failure detected")));
      b.addEventListener("click",()=>{active=i;renderButtons();renderDetail();});
      b.addEventListener("keydown",event=>{
        if(!["ArrowLeft","ArrowRight"].includes(event.key))return;
        event.preventDefault();
        active=(active+(event.key==="ArrowRight"?1:-1)+data.stages.length)%data.stages.length;
        renderButtons();renderDetail();tabs.children[active]?.focus();
      });
      tabs.append(b);
    }
  }
  function renderDetail(){
    detail.replaceChildren();
    if(!data)return;
    const stage=data.stages[active];
    detail.append(node("p","reviewer-stage-overline",
      loc("FAKTYCZNY ETAP","RECORDED STAGE")+" / "+String(active+1).padStart(2,"0")+" — "+stage.role));
    const head=node("div","reviewer-stage-title");
    head.append(
      node("h4","",isEN()?stage.headlineEn:stage.headlinePl),
      node("span","reviewer-stage-verdict "+(stage.status==="PASSED"?"passed":"failed"),
        (statusNames[stage.status]||[stage.status,stage.status])[isEN()?1:0])
    );
    detail.append(head);
    detail.append(node("p","reviewer-stage-explanation",isEN()?stage.explanationEn:stage.explanationPl));
    const facts=node("div","reviewer-facts");
    for(const fact of stage.facts||[]){
      const item=node("div","reviewer-fact");
      item.append(node("small","",fact.label),node("strong","",fact.value));
      facts.append(item);
    }
    detail.append(facts);
    if(stage.tools?.length){
      const tools=node("div","reviewer-detail-block");
      tools.append(node("h5","",loc("Udokumentowane wywołania narzędzi","Recorded tool calls")));
      const list=node("div","reviewer-tools");
      for(const tool of stage.tools)list.append(node("code","",tool));
      tools.append(list);detail.append(tools);
    }
    if(stage.files?.length){
      const files=node("div","reviewer-detail-block");
      files.append(node("h5","",loc("Rzeczywiście zapisane pliki","Actually authored files")));
      const list=node("div","reviewer-files");
      for(const file of stage.files){
        const row=node("div","reviewer-file-row");
        row.append(file.url?addLink(file.url,file.name):node("strong","",file.name));
        row.append(node("code","",file.sha256.slice(0,12)+"…"));
        list.append(row);
      }
      files.append(list);detail.append(files);
    }
    if(stage.codeExcerpt){
      const excerpt=node("div","reviewer-detail-block");
      excerpt.append(node("h5","",loc("Fragment rzeczywiście zapisanego kodu","Excerpt from actual authored source")+
        " · "+stage.codeExcerpt.path+" · "+stage.codeExcerpt.lines));
      const pre=node("pre","reviewer-code-excerpt");
      pre.append(node("code","",stage.codeExcerpt.source));
      excerpt.append(pre);
      detail.append(excerpt);
    }
    const note=isEN()?stage.riskEn:stage.riskPl;
    if(note)detail.append(node("p","reviewer-risk",note));
    const footer=node("div","reviewer-stage-footer");
    footer.append(
      node("small","",loc("Źródło: artefakty GitHub, nie symulacja","Source: GitHub artifacts, not a simulation")),
      addLink(stage.sourceUrl,loc("Zobacz oryginalne dowody ↗","Open original evidence ↗"))
    );
    detail.append(footer);
  }
  function renderRecalculation(){
    const label=$("reviewer-recalculation-result");
    const btn=$("reviewer-recalculate");
    btn.textContent=checking?loc("Przeliczanie…","Recalculating…"):
      loc("Przelicz dane i sprawdź wynik","Recalculate and verify");
    btn.disabled=checking;
    label.replaceChildren();
    if(!lastRecalculation)return;
    if(lastRecalculation.status!=="PASSED"){
      label.append(node("strong","reviewer-check-failed",loc(
        "Weryfikacja niedostępna — nie przedstawiamy wyniku jako zaliczonego.",
        "Recalculation unavailable — no successful result is claimed."
      )));
      return;
    }
    const d=lastRecalculation;
    const success=node("div","reviewer-check-success");
    success.append(node("strong","",loc("Niezależne przeliczenie: ZALICZONE","Independent recalculation: PASSED")));
    success.append(node("span","",loc("Przychód netto: ","Net revenue: ")+d.netRevenue));
    success.append(node("small","",loc(
      "Odczytano "+d.sourceCounts.rawRows+" wierszy, po deduplikacji "+d.sourceCounts.uniqueTransactions+
      "; porównano wszystkie pięć regionów. SHA-256 źródła i wyniku zgodne.",
      "Read "+d.sourceCounts.rawRows+" source rows, "+d.sourceCounts.uniqueTransactions+
      " unique transactions; reconciled all five regions. Source and output SHA-256 verified."
    )));
    label.append(success);
    const table=node("div","reviewer-region-values");
    for(const [name,value] of Object.entries(d.regions||{})){
      const row=node("div","reviewer-region-value");
      row.append(node("span","",name),node("strong","",value));table.append(row);
    }
    label.append(table);
    label.append(node("p","reviewer-method-note",loc(
      "Ponownie przeliczono dane na serwerze za pomocą niezależnego algorytmu BigInt. To NIE jest nowe uruchomienie agentów ani ponowne wykonanie Python/pytest.",
      "A separate server-side BigInt oracle has recomputed the source data. This is NOT a new agent run or a rerun of Python/pytest."
    )));
  }
  async function recalculate(){
    if(checking)return;
    checking=true;renderRecalculation();
    try{
      const res=await fetch("/api/review/recalculate",{
        method:"POST",headers:{"Content-Type":"application/json"},body:"{}"
      });
      const result=await res.json();
      if(!res.ok||result.status!=="PASSED")throw Error("Verification not completed");
      lastRecalculation=result;
    }catch{lastRecalculation={status:"UNAVAILABLE"};}
    checking=false;renderRecalculation();
  }
  function language(){
    $("reviewer-headline").textContent=loc(
      "Rzeczywisty przebieg: projekt → kod → naprawy → weryfikacja",
      "Real execution: design → code → corrections → verification"
    );
    $("reviewer-intro").textContent=loc(
      "Wybierz etap, żeby zobaczyć faktyczne pliki, wykonane narzędzia i wyniki. Starszy audyt odczytowy jest osobno poniżej.",
      "Select a stage to inspect actual files, tool calls and results. An earlier read-only audit appears separately below."
    );
    $("historic-audit-label").textContent=loc(
      "Starszy, archiwalny audyt odczytowy (nie generował tego kodu)",
      "Earlier read-only audit (did not generate this code)"
    );
    $("reviewer-result-title").textContent=loc(
      "Sprawdź wynik na oryginalnym CSV — teraz",
      "Verify the result against the original CSV — now"
    );
    $("reviewer-result-explainer").textContent=loc(
      "Uruchom ponownie niezależne obliczenie danych i porównanie z rzeczywistym wynikiem. Bez uruchamiania płatnych agentów.",
      "Recompute the original data independently and compare against the actual generated result. No paid agents are launched."
    );
    renderButtons();renderDetail();renderRecalculation();
  }
  $("reviewer-recalculate").addEventListener("click",recalculate);
  window.addEventListener("cloudfide:language",language);
  fetch("/data/latest_autonomous_run.json",{cache:"no-store"}).then(r=>{
    if(!r.ok)throw Error("No recorded evidence");return r.json();
  }).then(payload=>{
    if(payload.schemaVersion!==1||payload.runId!==44485096373||!Array.isArray(payload.stages))throw Error("Unexpected evidence schema");
    data=payload;language();
  }).catch(()=>{
    detail.replaceChildren(node("p","",loc(
      "Zweryfikowane artefakty są niedostępne. Można je przejrzeć bezpośrednio w GitHub Actions.",
      "Verified artifacts unavailable. View the original evidence in GitHub Actions."
    )));
  });
  language();
})();

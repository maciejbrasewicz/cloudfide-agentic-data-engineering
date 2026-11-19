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
  const state={enabled:false,id:null,timer:null,polling:false,submittedAt:null,workflowUrl:null,lastRun:null};
  const savedKey="cloudfide.review.execution.v1";
  function restore(){
    try{
      const saved=JSON.parse(sessionStorage.getItem(savedKey)||"null");
      if(saved&&/^[0-9a-f-]{36}$/i.test(saved.id||"")){
        state.id=saved.id;
        state.submittedAt=saved.submittedAt||null;
        state.workflowUrl=saved.workflowUrl||null;
      }
    }catch{/* Session storage is optional; never store the access code. */}
  }
  function preserve(){
    try{
      if(state.id)sessionStorage.setItem(savedKey,JSON.stringify({
        id:state.id,submittedAt:state.submittedAt,workflowUrl:state.workflowUrl
      }));
      else sessionStorage.removeItem(savedKey);
    }catch{/* The same live run can still be tracked without browser storage. */}
  }
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
  // REPLACED

/* Evaluated quality gates — controlled source mutations, never LLM scores. */
(() => {
  "use strict";
  const list=document.getElementById("fault-cases");
  const count=document.getElementById("fault-counts");
  if(!list||!count)return;
  const create=(tag,cls,value)=>{
    const element=document.createElement(tag);
    if(cls)element.className=cls;
    if(value!==undefined)element.textContent=String(value);
    return element;
  };
  async function render(){
    try{
      const [snapshot,evidence]=await Promise.all([
        fetch("./data/fault_evaluation.json",{cache:"no-store"}).then(x=>{if(!x.ok)throw Error("Missing evaluation");return x.json();}),
        fetch("./data/evidence.json",{cache:"no-store"}).then(x=>{if(!x.ok)throw Error("Missing audit");return x.json();}),
      ]);
      if(snapshot.schemaVersion!==1||snapshot.source!=="recorded_ci_artifact"||
         snapshot.sourceSha256!==evidence.provenance.sourceSha256||
         snapshot.scope!=="deterministic_gate_sensitivity_only"||
         !snapshot.originalDataIntact||
         snapshot.cases?.length!==(snapshot.mutantTotal+snapshot.sourceAnomaliesTotal)||
         snapshot.mutantTotal!==4||snapshot.sourceAnomaliesTotal!==1||
         snapshot.cases.some(x=>!x.detected)){
        throw Error("Fault-evaluation provenance or detection status mismatch");
      }
      count.replaceChildren();
      const score=create("strong","",snapshot.mutantCaught+"/"+snapshot.mutantTotal);
      const caption=create("span","","CODE MUTANTS DETECTED");
      const source=create("small","","+"+snapshot.sourceAnomaliesRejected+" / "+snapshot.sourceAnomaliesTotal+" SOURCE ANOMALY REJECTED");
      count.append(score,caption,source);
      list.replaceChildren();
      snapshot.cases.forEach((item,index)=>{
        const row=create("article","fault-card");
        row.append(create("span","fault-index",item.id));
        const body=create("div","fault-content");
        body.append(create("span","fault-category",item.category.toUpperCase()),
          create("h3","",item.title),create("p","",item.fault),
          create("div","fault-gate","CHECK · "+item.gate));
        row.append(body,create("div","fault-result","DETECTED ✓"));
        list.append(row);
      });
    }catch(error){
      console.error("Fault lab evidence failed verification",error);
      list.textContent="Recorded fault-injection results could not be independently verified.";
      count.textContent="EVIDENCE UNAVAILABLE";
    }
  }
  render();
})();

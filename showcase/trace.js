/* Recorded tool timeline. This is not a live Azure Monitor feed. */
(() => {
  "use strict";
  const view = document.getElementById("tool-timeline");
  const metrics = document.getElementById("trace-metrics");
  const selection = document.getElementById("trace-selected");
  const explanation = document.getElementById("observability-description");
  const zoomButtons = [...document.querySelectorAll("[data-zoom]")];
  const state = {zoom:"full",selected:0,data:null};
  const fmt = (value) => Number(value).toFixed(2);
  const create = (tag,className,text) => {
    const node=document.createElement(tag);
    if(className)node.className=className;
    if(text!==undefined)node.textContent=String(text);
    return node;
  };
  const repoHost = "github.com";
  function safeGithubLink(url){
    try{
      const parsed=new URL(url);
      return parsed.protocol==="https:"&&parsed.hostname===repoHost?parsed.href:"#";
    }catch{return "#";}
  }
  function render(){
    const t=state.data;
    if(!t)return;
    const seconds=t.wallDurationMs/1000;
    const families=Object.keys(t.toolCounts).length;
    explanation.textContent="Verified run: "+t.toolCallCount+" measured tool calls over "+
      seconds.toFixed(1)+" seconds. Model token usage and individual agent durations were not captured; OTel export is not yet connected.";
    metrics.replaceChildren();
    [
      ["TOTAL RUNTIME",seconds.toFixed(1)+"s",false],
      ["MEASURED TOOL CALLS",t.toolCallCount,false],
      ["TOOL FAMILIES",families,false],
      ["OTEL EXPORT",t.otelExporterConfigured?"CONNECTED":"NOT CONFIGURED",!t.otelExporterConfigured]
    ].forEach(([name,value,unavailable])=>{
      const box=create("div","trace-metric");
      box.append(create("small","",name),create("strong",unavailable?"not-recorded":"",value));
      metrics.append(box);
    });
    zoomButtons.forEach(button=>button.setAttribute("aria-pressed",String(button.dataset.zoom===state.zoom)));
    const observedEnd=Math.max(...t.events.map(e=>e.startSeconds+e.durationMs/1000));
    const bound=state.zoom==="tools"?observedEnd+1:seconds;
    const axis=create("div","trace-axis");
    axis.append(create("span","trace-axis-label","RECORDED FUNCTION"));
    const ticks=create("div","trace-axis-ticks");
    [0,bound/2,bound].forEach(value=>ticks.append(create("span","",value.toFixed(1)+"s")));
    axis.append(ticks,create("span","trace-axis-label","DURATION"));
    view.replaceChildren(axis);
    t.events.forEach((event,index)=>{
      const row=create("button","trace-row"+(index===state.selected?" selected":""));
      row.type="button";
      row.setAttribute("aria-pressed",String(index===state.selected));
      row.setAttribute("aria-label",event.name+" at +"+event.startSeconds+" seconds, duration "+event.durationMs+" milliseconds");
      const name=create("span","trace-name",event.name+"()");
      const rail=create("span","trace-rail");
      const bar=create("span","trace-bar");
      const pct=Math.min(98.5,event.startSeconds/bound*100);
      const width=Math.min(100-pct,Math.max(.6,event.durationMs/1000/bound*100));
      bar.style.left=pct.toFixed(3)+"%";
      bar.style.width=width.toFixed(3)+"%";
      rail.append(bar);
      const duration=create("span","trace-duration");
      duration.append(create("strong","",fmt(event.durationMs)),document.createTextNode(" ms"));
      row.append(name,rail,duration);
      row.addEventListener("click",()=>{state.selected=index;render();});
      view.append(row);
    });
    const selected=t.events[state.selected]||t.events[0];
    selection.replaceChildren();
    selection.append(
      create("strong","","EVENT #"+String(selected.seq).padStart(2,"0")+" / "+selected.name+"()"),
      create("span","",
        "START +"+selected.startSeconds.toFixed(3)+"s · "+selected.durationMs.toFixed(3)+"ms · "+
        selected.status.toUpperCase()+" · MEASURED")
    );
    const source=create("a","case-link","ORIGINAL RUN ↗");
    source.href=safeGithubLink(t.githubRunUrl);
    source.target="_blank";
    source.rel="noopener noreferrer";
    selection.append(source);
  }
  zoomButtons.forEach(button=>button.addEventListener("click",()=>{state.zoom=button.dataset.zoom;render();}));
  async function load(){
    try{
      const [traceResponse,evidenceResponse]=await Promise.all([
        fetch("./data/agent_trace.json",{cache:"no-store"}),
        fetch("./data/evidence.json",{cache:"no-store"})
      ]);
      if(!traceResponse.ok||!evidenceResponse.ok)throw Error("Missing verified snapshot");
      const trace=await traceResponse.json();
      const evidence=await evidenceResponse.json();
      if(trace.schemaVersion!==1||trace.kind!=="recorded_tool_activity"||
        trace.measurementSource!=="real_foundry_run"||
        trace.reviewedCommit!==evidence.provenance.reviewedCommit||
        trace.sourceSha256!==evidence.provenance.sourceSha256||
        trace.toolCallCount!==trace.events?.length||
        trace.toolCallCount!==evidence.observability.toolSpanCount||
        !trace.events?.length){
        throw Error("Execution evidence provenance mismatch");
      }
      state.data=trace;
      render();
    }catch(error){
      console.error("Recorded tool timeline unavailable:",error);
      view.textContent="Recorded telemetry cannot be verified against this release.";
      metrics.textContent="SOURCE CHECK FAILED";
    }
  }
  load();
})();

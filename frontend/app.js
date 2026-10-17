import {all,put,remove,partition,retryable,send} from "./queue.js";
const $ = id => document.getElementById(id);
let user = null, token = "", busy = false;
const owner = () => [user.tenant_id,user.factory_id,user.id].join(":");
function message(text) {$("message").textContent=text;}
function error(e) {$("error").textContent=e.message || String(e);}
async function api(path,options={}) {
  const r = await fetch("/api"+path,{...options,headers:{"Authorization":"Bearer "+token,"Content-Type":"application/json"},cache:"no-store"});
  if(!r.ok) {const e=new Error((await r.text()).slice(0,400));e.status=r.status;throw e;}
  return r.json();
}
async function queueView() {
  $("queue").replaceChildren();
  for(const item of partition(await all(),owner())) {
    const li=document.createElement("li");li.textContent=(item.error?"확인 필요: ":"전송 대기: ")+item.incident.notes+" "+(item.error||"");
    $("queue").append(li);
  }
}
async function records() {
  const rows=await api("/incidents");
  $("incidents").replaceChildren();
  for(const row of rows) {
    const article=document.createElement("article"), text=document.createElement("p");
    text.textContent=(row.approved?"승인 완료":"검토 대기")+" · "+new Date(row.started_at).toLocaleString()+" · "+row.notes;
    article.append(text);
    if(!row.approved && ["supervisor","admin"].includes(user.role)) {
      const button=document.createElement("button");button.textContent="조치 확인 및 승인";
      button.onclick=async()=>{
        try {
          const detail=await api("/incidents/"+row.id);
          const summary=detail.actions.map(a=>a.action+" → "+a.outcome).join("\n");
          if(!summary) throw new Error("등록된 조치가 없습니다.");
          const evidence=prompt(summary+"\n해결을 확인한 증빙을 입력하세요.");
          if(!evidence) return;
          const end=prompt("실제 정지 종료 시각 (시간대 포함 ISO 형식)",new Date().toISOString());
          if(!end) return;
          await api("/incidents/"+row.id+"/approve",{method:"POST",body:JSON.stringify({resolved:true,evidence,ended_at:end})});
          await records();
        }catch(e){error(e);}
      };article.append(button);
    }
    $("incidents").append(article);
  }
}
async function sync() {
  if(busy||!user) return;
  busy=true;$("sync").disabled=true;
  const activeOwner=owner();
  try {
    for(const item of partition(await all(),activeOwner)) {
      if(item.error) continue;
      try {await send(item,api);await remove(item.id);}
      catch(e) {
        if(!retryable(e.status||0) && e.status!==401) {item.error=e.message;await put(item);}
        else {message(e.status===401?"재로그인이 필요합니다. 기록은 보존됩니다.":"연결 대기 중입니다. 기록은 보존됩니다.");break;}
      }
    }
    await queueView();
    if(navigator.onLine) await records();
  }catch(e){error(e);}finally{busy=false;$("sync").disabled=false;}
}
async function enter() {
  $("login").hidden=true;$("workspace").hidden=false;
  $("identity").textContent="공장 "+user.factory_id+" · "+user.role;
  let equipment;
  if(navigator.onLine) {
    equipment=await api("/equipment");
    sessionStorage.setItem("equipment:"+owner(),JSON.stringify(equipment));
  }else equipment=JSON.parse(sessionStorage.getItem("equipment:"+owner())||"[]");
  $("equipment").replaceChildren(...equipment.map(e=>new Option(e.name,e.id)));
  $("report-panel").hidden=!["supervisor","admin"].includes(user.role);
  if(!$("report-panel").hidden && navigator.onLine) {
    const sensors=await api("/sensors");
    $("report-sensor").replaceChildren(new Option("정지 기록만 집계",""),...sensors.map(s=>new Option(s.name,s.id)));
  }
  const local=new Date(Date.now()-new Date().getTimezoneOffset()*60000);
  $("started").value=local.toISOString().slice(0,16);
  await queueView();await sync();
}
$("login-form").onsubmit=async e=>{
  e.preventDefault();$("error").textContent="";token=$("token").value;
  try {user=await api("/me");sessionStorage.setItem("login",JSON.stringify({user,token}));$("token").value="";await enter();}
  catch(e){user=null;token="";error(e);}
};
$("logout").onclick=()=>{
  if(busy) return message("전송이 끝난 후 로그아웃하세요.");
  sessionStorage.clear();user=null;token="";
  $("incidents").replaceChildren();$("queue").replaceChildren();$("incident-form").reset();
  $("knowledge-results").replaceChildren();$("report-result").replaceChildren();
  $("workspace").hidden=true;$("login").hidden=false;
};
$("incident-form").onsubmit=async e=>{
  e.preventDefault();
  try {
    const id=crypto.randomUUID();
    await put({id,owner:owner(),created:Date.now(),
      incident:{id,equipment_id:$("equipment").value,reason:$("reason").value,notes:$("notes").value,
                started_at:new Date($("started").value).toISOString()},
      action:{id:crypto.randomUUID(),action:$("action").value,outcome:$("outcome").value}});
    ["notes","action","outcome"].forEach(id=>$(id).value="");
    message("기기에 저장했습니다.");await queueView();await sync();
  }catch(e){error(e);}
};
$("sync").onclick=sync;
$("knowledge-form").onsubmit=async e=>{
  e.preventDefault();
  try {
    const data=await api("/knowledge?q="+encodeURIComponent($("query").value));
    const target=$("knowledge-results");target.replaceChildren();
    const answer=document.createElement("p");answer.textContent=data.answer;target.append(answer);
    for(const source of data.sources) {
      const article=document.createElement("article");
      article.textContent=source.notes+" · "+source.actions+" · 승인 근거: "+source.evidence+" · 출처 기록 "+source.id;
      target.append(article);
    }
    const note=document.createElement("p");note.textContent=data.limitations.join(" ");target.append(note);
  }catch(e){error(e);}
};
$("report-form").onsubmit=async e=>{
  e.preventDefault();
  try {
    const report=await api("/reports",{method:"POST",body:JSON.stringify({
      period:$("period").value,day:$("report-day").value,sensor_id:$("report-sensor").value||null})});
    const target=$("report-result");target.replaceChildren();
    const summary=document.createElement("p"),d=report.document;
    summary.textContent="정지 기록 "+d.incident_count+"건 · 승인 "+d.approved_count+"건 · 설비 정지 "+d.equipment_downtime_minutes.toFixed(1)+"분";
    target.append(summary);
    if(d.energy) {
      const energy=document.createElement("p");
      energy.textContent="실측 "+d.energy.measured_kwh.toFixed(2)+" kWh · 추정 "+d.energy.estimated_kwh.toFixed(2)+" kWh · 실측 시간 비율 "+(d.energy.measured_coverage_ratio*100).toFixed(1)+"%";
      target.append(energy);
    }
    const note=document.createElement("p");note.textContent="생성 시점의 확정 스냅샷입니다. 지연 수집 자료는 미포함하며, 검증된 절감 실적을 뜻하지 않습니다.";target.append(note);
    for(const format of ["xlsx","pdf"]) {
      const button=document.createElement("button");button.textContent=format.toUpperCase()+" 다운로드";
      button.onclick=async()=>{
        try {
          const r=await fetch("/api/reports/"+report.id+"/export?format="+format,{headers:{Authorization:"Bearer "+token}});
          if(!r.ok)throw new Error("보고서 다운로드 실패");
          const url=URL.createObjectURL(await r.blob()),a=document.createElement("a");
          a.href=url;a.download="factory-"+d.day+"."+format;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
        }catch(e){error(e);}
      };target.append(button);
    }
  }catch(e){error(e);}
};
function connectivity() {$("connection").textContent=navigator.onLine?"온라인":"오프라인 · 기기 저장";}
window.addEventListener("online",()=>{connectivity();sync();});window.addEventListener("offline",connectivity);connectivity();
try {const saved=JSON.parse(sessionStorage.getItem("login")||"null");if(saved){user=saved.user;token=saved.token;await enter();}}catch(e){error(e);}
if("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(error);

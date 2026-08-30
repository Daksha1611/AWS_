import{a as e,c as t,d as n,f as r,i,l as a,m as o,n as s,o as c,p as l,r as u,s as d,t as ee,u as te}from"./gateway-CtT9b1Hm.js";var f=e=>e==null?`—`:`₹`+Math.round(e/100).toLocaleString(`en-IN`);function p(e){return String(e??``).replace(/[&<>"']/g,e=>({"&":`&amp;`,"<":`&lt;`,">":`&gt;`,'"':`&quot;`,"'":`&#39;`})[e])}var m={settled:`done`,decomposed:`open`,granted:`open`,pending:`open`,searching:`open`,paying:`open`,escalated:`held`,refused:`stop`},ne={pending:`queued`,granted:`granted`,decomposed:`split`,searching:`reading`,paying:`paying`,settled:`paid`,escalated:`held`,refused:`stopped`};function h(e){let t=new Map,n=(e,n,r)=>{t.has(e)||t.set(e,{id:e,parentId:n??null,depth:r??0,task:``,budget:null,tools:[],sourcing:`catalogue`,supplier:null,state:`pending`,note:``,helper:!1,fault:!1,broker:!1,blocks:null,tokenBytes:null,expires:null,children:[],order:t.size});let i=t.get(e);return n&&!i.parentId&&(i.parentId=n),i};for(let t of e){let e=n(t.node_id,t.parent_id,t.depth),r=t.detail||{};switch(t.kind){case`spawned`:e.task=r.description||e.task,e.sourcing=r.sourcing||e.sourcing,e.supplier=r.supplier??e.supplier,r.helper&&(e.helper=!0),r.sources_for&&(e.sourcesFor=r.sources_for),e.budget===null&&r.budget_paise!==void 0&&(e.budget=r.budget_paise);break;case`granted`:e.budget=r.budget_paise??e.budget,e.tools=r.tools||e.tools,e.broker=!!r.broker,e.blocks=r.blocks||e.blocks,e.tokenBytes=r.token_bytes??e.tokenBytes,e.expires=r.expires||e.expires,e.state=`granted`;break;case`decomposed`:e.state=`decomposed`,e.note=`split ${r.children} ways · ${f(r.allocated)} allocated`;break;case`searching`:e.state=`searching`,e.note=`reading supplier pages it did not write`;break;case`paying`:e.state=`paying`;break;case`settled`:e.state=`settled`,e.note=typeof r.result==`string`?r.result:e.note;break;case`escalated`:e.state=`escalated`,e.note=r.reason||`waiting on a person; the money is still held`;break;case`denied`:e.state=`refused`,e.note=r.reason||`refused`;break;case`bound_hit`:r.fault&&(e.state=`refused`,e.fault=!0),e.note=r.critique?`a second model refused this plan: ${r.critique}`:r.reason||e.note}}let r=[];for(let e of t.values()){let n=e.parentId?t.get(e.parentId):null;n?n.children.push(e):r.push(e)}for(let e of t.values())e.children.sort((e,t)=>e.order-t.order);let i=[],a=e=>{i.push(e),e.children.forEach(a)};return r.sort((e,t)=>e.order-t.order).forEach(a),{nodes:t,ordered:i,roots:r}}function re(e){let t=e.ordered,n=t.filter(e=>!e.helper),r=n.filter(e=>e.state===`settled`);return{nodes:t.length,lookers:t.length-n.length,depth:t.reduce((e,t)=>Math.max(e,t.depth),0),widest:t.reduce((e,t)=>Math.max(e,t.children.length),0),paid:r.length,held:t.filter(e=>e.state===`escalated`).length,stopped:t.filter(e=>e.state===`refused`).length,faults:t.filter(e=>e.fault).map(e=>e.note),committed:r.reduce((e,t)=>e+(t.budget||0),0),settled:t.length>0&&t.every(e=>[`settled`,`refused`,`escalated`,`decomposed`].includes(e.state))}}function ie(e){return e.tools.length?e.broker?`<span class="tool t-broker">confers · cannot spend</span>`:e.tools.map(e=>`<span class="tool t-${p(e)}">${p(e)}</span>`).join(``):e.depth===0?`<span class="tool t-mandate">mandate</span>`:``}function ae(e,t){let n=m[e.state]||`open`,r=e.helper&&e.state===`settled`?`read`:ne[e.state]||e.state,i=e.sourcesFor?`<span class="web-tag">sources for ${p(e.sourcesFor)}</span>`:``,a=e.sourcing===`best`?`<span class="web-tag">open web</span>`:e.supplier?`<span class="web-tag">pays ${p(e.supplier)}</span>`:``;return`
    <div class="row is-${n}${e.helper?` is-helper`:``}" data-node="${p(e.id)}" role="button" tabindex="0">
      <span class="row-seq">${String(t).padStart(2,`0`)}</span>
      <div class="row-body">
        <div class="row-task">${p(e.task||`—`)}${a}${i}</div>
        <div class="row-id">${p(e.id)}</div>
        ${e.note?`<div class="row-note">${p(e.note)}</div>`:``}
      </div>
      <span class="tools">${ie(e)}</span>
      <span class="row-amt">${f(e.budget)}</span>
      <span class="row-state">${r}</span>
    </div>`}function oe(e){let t=new Map;for(let n of e)t.has(n.depth)||t.set(n.depth,[]),t.get(n.depth).push(n);let n=0;return[...t.entries()].sort((e,t)=>e[0]-t[0]).map(([e,t])=>{let r=t.reduce((e,t)=>e+(t.budget||0),0);return`
        <section class="layer">
          <div class="layer-head">
            <b>${e===0?`Mandate`:`Layer ${e}`}</b>
            <span>${t.length} node${t.length===1?``:`s`} · ${f(r)}</span>
            <hr>
          </div>
          ${t.map(e=>ae(e,++n)).join(``)}
        </section>`}).join(``)}var g=e=>document.getElementById(e),_={text:``,answers:{},reading:null,busy:!1},v=e=>`₹`+Number(e).toLocaleString(`en-IN`);function y(e){return String(e??``).replace(/[&<>"']/g,e=>({"&":`&amp;`,"<":`&lt;`,">":`&gt;`,'"':`&quot;`,"'":`&#39;`})[e])}function b(){_.text=``,_.answers={},_.reading=null,_.busy=!1;let e=g(`intake`);e.hidden=!0,e.innerHTML=``}var se={errand:`a bounded purchase — one obvious cart`,target:`a goal, not a list — it has to work out what to buy`,standing:`recurring — this would keep spending, so it needs approving first`};function ce(e){let t=[];e.task_kind&&t.push(`<span class="in-tag" data-tip="${y(se[e.task_kind]||``)}"
      >${y(e.task_kind)}</span>`);for(let n of(e.items||[]).slice(0,6)){let e=n.quantity?` ${y(n.quantity)}`:``;t.push(`<span class="in-tag is-item">${y(n.name)}${e}</span>`)}e.supplier&&t.push(`<span class="in-tag is-item">from ${y(e.supplier)}</span>`);let n=e.extracted_by===`model`?`read by the intake model`:`no model reachable — asking everything`;return`
    <div class="in-card in-read">
      <p class="in-label" data-tip-title="What it understood"
         data-tip="Extracted from your sentence by a model that holds no authority. It can be wrong; that is why anything it changes about the money is asked rather than applied.">Here is what I understood</p>
      <p class="in-goal">${y(e.goal||``)}</p>
      ${t.length?`<div class="in-tags">${t.join(``)}</div>`:``}
      <p class="in-foot">${y(n)}</p>
    </div>`}function le(e){if(e.kind===`money`){let t=e.suggestion?y(e.suggestion):``;return`
      <div class="in-money">
        <label class="in-rupee">₹<input class="in-input" inputmode="numeric"
          data-answer="${e.id}" value="${t}"
          aria-label="Ceiling in rupees" placeholder="0" /></label>
        <button class="in-go" data-submit="${e.id}">
          ${e.confirming?`Use this ceiling`:`Set ceiling`}
        </button>
      </div>`}return e.kind===`choice`?`<div class="in-choices">${e.options.map(t=>`
      <button class="in-choice" data-pick="${e.id}" data-value="${y(t.value)}"
              ${t.note?`data-tip="${y(t.note)}"`:``}>
        <b>${y(t.label)}</b>
        ${t.note?`<span>${y(t.note)}</span>`:``}
      </button>`).join(``)}</div>`:`
    <div class="in-money">
      <input class="in-input is-wide" data-answer="${e.id}"
             placeholder="Type it here" aria-label="${y(e.ask)}" />
      <button class="in-go" data-submit="${e.id}">Use this</button>
    </div>`}function ue(e){return`
    <div class="in-card in-q${e.confirming?` is-confirming`:``}" data-q="${e.id}">
      <p class="in-ask">${y(e.ask)}</p>
      <p class="in-why">${y(e.why)}</p>
      ${le(e)}
    </div>`}function de(e){let t=e.proposal,n=e.understood,r=e.expected_model_calls,i={catalogue:`our own catalogue, no web search`,specific:`only ${n.supplier}`,best:`the open web, searched by a zero-budget agent`}[n.sourcing];return`
    <div class="in-card in-ready">
      <p class="in-label">Ready. Nothing is signed until you press this.</p>
      <dl class="in-summary">
        <div><dt>Task</dt><dd>${y(t.task)}</dd></div>
        <div><dt data-tip="Signed into the root token. No agent below can raise it, and every sub-agent gets a strict share of it.">Ceiling</dt>
             <dd class="num">${v(t.budget_paise/100)}</dd></div>
        <div><dt data-tip="Below this a task stops splitting and simply buys. It is what ends the recursion — without it the tree would never reach a leaf.">Smallest purchase</dt>
             <dd class="num">${v(t.floor_paise/100)}</dd></div>
        <div><dt data-tip="Where the goods come from. This is the risk axis, not a preference — reading the open web means reading seller-controlled text.">Sourcing</dt>
             <dd>${y(i||`—`)}</dd></div>
        ${Number.isFinite(r)?`<div><dt data-tip="One call per branch to split it, one per leaf to judge the payment. ${e.model_calls_exact?`The tree shape is fixed in advance, so this figure is exact.`:`A model chooses how deep each branch goes, so this is a floor — a real tree usually runs larger.`}">Model calls</dt>
             <dd class="num">${e.model_calls_exact?``:`≥ `}${r}</dd></div>`:``}
      </dl>
      <div class="in-actions">
        <button class="in-start" id="in-start">Mint the mandate &amp; run</button>
        <button class="in-edit" id="in-edit">Start over</button>
      </div>
    </div>`}var x=e=>`<div class="in-thread">${e}</div>`;function S(){let e=g(`intake`),t=_.reading;e.hidden=!1;let n=g(`empty`);n&&(n.hidden=!0);let r=`<div class="in-said">${y(_.text)}</div>`;if(!t){e.innerHTML=x(r+`<div class="in-card in-wait">Reading that…</div>`);return}let i=(t.notes||[]).length?`<p class="in-note">${t.notes.map(y).join(` `)}</p>`:``;e.innerHTML=x(r+ce(t.understood)+i+(t.ready?de(t):t.questions.map(ue).join(``))),e.querySelector(`.in-input, .in-choice, #in-start`)?.focus()}async function C(e){_.busy=!0,S();try{_.reading=await t(_.text,_.answers,e)}catch(e){_.reading=null,g(`intake`).innerHTML=x(`
      <div class="in-said">${y(_.text)}</div>
      <div class="in-card in-error">
        Could not read that: ${y(String(e.detail?.denied??e.message))}
      </div>`);return}finally{_.busy=!1}S()}function w(e,t){return _.text=e,_.answers={},_.reading=null,C(t)}function T(e,t,n){if(t!==``&&t!=null)return _.answers={..._.answers,[e]:t},C(n)}function E({options:e,onRun:t}){let n=g(`intake`);n.addEventListener(`click`,r=>{if(_.busy)return;let i=r.target.closest(`[data-pick]`);if(i){T(i.dataset.pick,i.dataset.value,e());return}let a=r.target.closest(`[data-submit]`);if(a){let t=a.dataset.submit,r=n.querySelector(`[data-answer="${t}"]`),i=r?.value??``,o=t.endsWith(`_rupees`)?i.replace(/\D/g,``):i.trim();if(!o){r?.focus();return}T(t,o,e());return}if(r.target.closest(`#in-edit`)){b();let e=g(`empty`);e&&(e.hidden=!1);return}r.target.closest(`#in-start`)&&_.reading?.proposal&&t(_.reading.proposal,_.reading.understood)}),n.addEventListener(`keydown`,e=>{if(e.key!==`Enter`)return;let t=e.target.closest(`[data-answer]`);t&&(e.preventDefault(),n.querySelector(`[data-submit="${t.dataset.answer}"]`)?.click())})}var D=document.getElementById(`tip`),O=null,k=null,A=10;function j(e){let t=e.getBoundingClientRect();D.hidden=!1,D.classList.remove(`is-on`);let n=D.getBoundingClientRect(),r=t.top-n.height-A,i=t.bottom+A,a=r<8,o=a?i:r,s=t.left+t.width/2-n.width/2;s=Math.max(8,Math.min(s,window.innerWidth-n.width-8)),D.style.top=`${Math.round(o)}px`,D.style.left=`${Math.round(s)}px`,D.style.setProperty(`--arrow`,`${Math.round(t.left+t.width/2-s)}px`),D.classList.toggle(`is-below`,a),requestAnimationFrame(()=>D.classList.add(`is-on`))}function M(e){let t=e.dataset.tip;if(!t)return;let n=e.dataset.tipTitle;if(D.innerHTML=``,n){let e=document.createElement(`b`);e.className=`tip-title`,e.textContent=n,D.append(e)}let r=document.createElement(`span`);r.textContent=t,D.append(r),O=e,j(e)}function N(){O=null,clearTimeout(k),D.classList.remove(`is-on`),k=setTimeout(()=>{O||(D.hidden=!0)},120)}function P(e){return e.target.closest?.(`[data-tip]`)??null}document.addEventListener(`pointerover`,e=>{let t=P(e);!t||t===O||(clearTimeout(k),k=setTimeout(()=>M(t),160))}),document.addEventListener(`pointerout`,e=>{let t=P(e);t&&t===O&&!t.contains(e.relatedTarget)?N():t&&t!==O&&clearTimeout(k)});var fe=e=>e.matches?.(`input, textarea, [contenteditable]`)||!!e.querySelector?.(`input, textarea`);document.addEventListener(`focusin`,e=>{let t=P(e);t&&!fe(e.target)&&M(t)}),document.addEventListener(`input`,()=>{O&&N()}),document.addEventListener(`focusout`,()=>{O&&N()}),document.addEventListener(`keydown`,e=>{e.key===`Escape`&&O&&N()}),window.addEventListener(`scroll`,()=>{O&&N()},!0),window.addEventListener(`resize`,()=>{O&&N()});var F=e=>document.getElementById(e),pe=[{key:`depth`,name:`Depth`,limit:8,fault:!1,note:`derived from the token chain, never claimed`},{key:`floor`,name:`Budget floor`,limit:`₹5,000`,fault:!1,note:`below this a task acts instead of splitting — this is what ends the recursion`},{key:`widest`,name:`Fan-out`,limit:6,fault:!0,note:`children per node`},{key:`nodes`,name:`Node budget`,limit:128,fault:!0,note:`per run; exhaustion refuses`},{key:`cycles`,name:`Cycles`,limit:0,fault:!0,note:`a sub-task restating an ancestor`},{key:`conservation`,name:`Conservation`,limit:`100%`,fault:!0,note:`children may not be allocated more than their parent holds`},{key:`railcap`,name:`Rail cap`,limit:`₹5,00,000`,fault:!0,note:`the mirror of the floor — the most one order may be`},{key:`critic`,name:`Critic`,limit:`advisory`,fault:!0,judged:!0,note:`a second model reads each plan before any token is minted. It can refuse; it can never authorise`}],I=new Map,L={live:!1,running:!1,filter:`all`,mandateId:null,task:``,floor:null,mandate:null,approvals:[],stop:null,audit:[],chain:null,inspecting:null,replays:{},parties:[],fleet:null,policies:[],tab:`run`,auditFilter:`all`,criticOn:null,can:null},R=e=>I.set(`${e.run_id??`-`}|${e.node_id}|${e.kind}|${e.at}`,e),z=()=>{let e=[...I.values()];return L.mandateId?e.filter(e=>!e.run_id||e.run_id===L.mandateId):e};function B(e,t){let n=F(`conn`);n.className=`sb-conn ${e}`,n.textContent=t}async function me(){try{L.can=(await c()).capabilities||null,Ae()}catch{L.live=!1,B(`is-off`,`no gateway`),F(`note`).innerHTML=`No gateway at <b>${p(l())}</b>. Start one with <b>pocketchange serve</b> — this console shows real runs only.`,F(`send`).disabled=!0;return}L.live=!0,B(`is-live`,L.can?.degraded?`live · degraded`:`live`),he(),await V(),X()}function he(){L.stop?.(),L.stop=r({onEvent:e=>{R(e),!(L.mandateId&&e.run_id&&e.run_id!==L.mandateId)&&(H(),[`settled`,`denied`,`escalated`,`bound_hit`].includes(e.kind)&&V())},onOpen:()=>B(`is-live`,`live`),onError:()=>B(``,`reconnecting`)})}async function V(){let[e,t,n,r,a]=await Promise.all([s().catch(()=>({pending:[]})),u().catch(()=>({entries:[]})),i().catch(()=>({counterparties:[]})),ee().catch(()=>null),te().catch(()=>({orders:[]}))]);if(L.parties=n.counterparties??[],L.fleet=r,L.policies=a.orders??[],L.approvals=e.pending??[],L.audit=t.entries??[],!L.mandateId){let e=(t.entries??[]).find(e=>e.tool===`mandate`);e&&(L.mandateId=e.mandate_id,L.task=e.context||``)}L.mandateId&&(L.mandate=await d(L.mandateId).catch(()=>L.mandate)),H()}function H(){let e=h(z()),t=re(e);ge(t),_e(e),ve(t,e),be(),W(),K(),G(),Ce(),we(),ye(),Oe(e,t)}function ge(e){let t=L.mandate;F(`cap`).textContent=t?f(t.cap_paise):`—`,F(`task-line`).textContent=L.task||`No run yet`,F(`mandate-id`).textContent=L.mandateId?L.mandateId.slice(0,20)+`…`:``,F(`committed`).textContent=f(t?t.committed_paise:e.committed),F(`held`).textContent=t?f(t.reserved_paise):`—`,F(`available`).textContent=t?f(t.available_paise):`—`;let n=t&&t.cap_paise?t.committed_paise/t.cap_paise:0,r=F(`meter`);r.style.width=`${Math.min(100,n*100).toFixed(1)}%`,r.dataset.level=n>.9?`high`:n>.7?`mid`:`low`}function _e(e){let t=new Map;for(let n of e.ordered){let e=m[n.state]||`open`,r=t.get(n.depth)||{done:0,held:0,stop:0,open:0,n:0};r[e]+=1,r.n+=1,t.set(n.depth,r)}if(!t.size){F(`profile`).innerHTML=`<p class="sb-empty">Nothing running.</p>`;return}let n=Math.max(...[...t.values()].map(e=>e.n));F(`profile`).innerHTML=[...t.entries()].sort((e,t)=>e[0]-t[0]).map(([e,t])=>{let r=(e,n)=>t[e]?`<span class="${n}" style="flex:${t[e]}"></span>`:``;return`
        <div class="profile-row">
          <span>d${e}</span>
          <span class="profile-bar" style="width:${Math.max(12,t.n/n*100)}%">
            ${r(`done`,`p-done`)}${r(`held`,`p-held`)}${r(`stop`,`p-stop`)}${r(`open`,`p-open`)}
          </span>
          <span class="profile-n">${t.n}</span>
        </div>`}).join(``)}function ve(e,t){let n=t.ordered.filter(e=>/second model refused/i.test(e.note||``)).length,r={depth:e.depth,floor:`—`,widest:e.widest,nodes:e.nodes,cycles:e.faults.filter(e=>/cycle/i.test(e)).length,conservation:e.faults.some(e=>/conservation/i.test(e))?`over`:`ok`,railcap:`ok`,critic:n?`${n} refused`:L.can?.critic===`unconfigured`?`none`:L.criticOn===null?`—`:L.criticOn?`watching`:`off`};F(`bounds`).innerHTML=pe.map(t=>{let n=e.faults.some(e=>new RegExp(t.name.split(` `)[0],`i`).test(e));return`
      <div class="bound${t.fault?` bound-fault`:``}${t.judged?` bound-judged`:``}${n?` is-hit`:``}">
        <span class="bound-name">${t.name}</span>
        <span class="bound-val">${r[t.key]} <em>/ ${t.limit}</em></span>
        <span class="bound-note">${t.note}</span>
      </div>`}).join(``)}function ye(){let e=F(`approvals-block`);if(!L.approvals.length){e.hidden=!0;return}e.hidden=!1,F(`approvals`).innerHTML=L.approvals.map(e=>`
    <article class="approval">
      <p class="approval-amt num">${f(e.amount_paise)}<span class="approval-kind">${e.kind===`policy`?`per period, recurring`:`one payment, held`}</span></p>
      <p class="approval-why">${p(e.reason)}</p>
      <p class="approval-claim">
        <span>${e.kind===`policy`?`your instruction`:`the agent says`}</span>
        ${p(e.agent_claim||`—`)}
      </p>
      <div class="approval-btns">
        <button class="yes" data-yes="${p(e.approval_id)}">Release</button>
        <button class="no"  data-no="${p(e.approval_id)}">Refuse</button>
      </div>
    </article>`).join(``)}function U(e){if(!e.length)return null;let t=[...e].sort((e,t)=>e-t),n=Math.floor(t.length/2);return t.length%2?t[n]:(t[n-1]+t[n])/2}function be(){let e=L.audit.filter(e=>e.tool===`pay`&&e.detail),t=e.map(e=>e.detail.enforcement_ms).filter(e=>typeof e==`number`),n=e.map(e=>e.detail.monitor_ms).filter((t,n)=>typeof t==`number`&&e[n].detail.monitor_ran!==!1);if(!t.length){F(`latency`).innerHTML=`<p class="sb-empty">No payments yet.</p>`;return}let r=U(t),i=U(n),a=Math.max(r||0,i||0)||1,o=e=>e===null?`—`:(e<10?e.toFixed(3):Math.round(e).toLocaleString())+` ms`,s=(e,t,n)=>`
    <div class="lat-row${t!==null&&t>50?` is-slow`:``}">
      <span class="lat-name">${e}</span>
      <span class="lat-val">${o(t)}</span>
      <span class="lat-bar"><span style="width:${t===null?0:t/a*100}%"></span></span>
      ${n?`<span class="lat-note">${n}</span>`:``}
    </div>`,c=r!==null&&r>50;F(`latency`).innerHTML=s(`Enforcement`,r,c?`includes a Firestore round trip; 0.164 ms with the in-memory ledger`:`signature, expiry, depth, scope, cumulative spend, idempotency`)+s(`Judgement`,i,n.length?`${n.length} model call${n.length===1?``:`s`}`:`monitor not run`)+`<p class="lat-note">median of ${t.length} payment${t.length===1?``:`s`}</p>`}function xe(e){let t=[];return e.vetoed&&t.push(`${e.vetoed} refused by a person`),e.injections&&t.push(`${e.injections} injected page${e.injections===1?``:`s`}`),e.escalated&&t.push(`${e.escalated} held for review`),e.refused&&t.push(`${e.refused} refused by the gateway`),t}function W(){let e=[...L.parties].sort((e,t)=>(t.trouble||0)-(e.trouble||0)||t.orders-e.orders),t=F(`parties-table`);if(!e.length){t.innerHTML=`<tbody><tr><td class="wrap">Nobody has been paid yet.</td></tr></tbody>`;return}t.innerHTML=`
    <thead><tr>
      <th>counterparty</th><th>orders</th><th>settled</th>
      <th>mandates</th><th>first paid</th><th>on the record</th>
    </tr></thead>
    <tbody>${e.map(e=>{let t=xe(e);return`
        <tr class="${t.length?`row-trouble`:``}">
          <td class="m">${p(e.id)}</td>
          <td class="n">${e.orders||`—`}</td>
          <td class="n">${e.orders?f(e.total_paise):`—`}</td>
          <td class="n">${e.mandates||`—`}</td>
          <td class="m">${e.orders?String(e.first_paid).slice(0,10):`—`}</td>
          <td class="wrap">${t.length?`<span class="verdict bad">concerns</span> ${p(t.join(` · `))}`:`nothing against them`}</td>
        </tr>`}).join(``)}</tbody>`}var Se={allowed:`ok`,escalated:`held`,denied:`bad`};function G(){let e=L.audit.filter(e=>L.auditFilter===`all`||e.decision===L.auditFilter).slice().reverse(),t=F(`audit-table`);if(!e.length){t.innerHTML=`<tbody><tr><td class="wrap">Nothing recorded under this filter.</td></tr></tbody>`;return}t.innerHTML=`
    <thead><tr>
      <th>#</th><th>time</th><th>tool</th><th>decision</th>
      <th>amount</th><th>enforce</th><th>judge</th><th>reason</th>
    </tr></thead>
    <tbody>${e.map(e=>{let t=e.detail||{},n=Se[e.decision]||`ok`,r=t.monitor_ran===!1?`<span class="unjudged">not judged</span>`:``,i=e=>typeof e==`number`?e<10?e.toFixed(2):Math.round(e).toLocaleString():`—`;return`
        <tr class="${n===`bad`?`row-trouble`:n===`held`?`row-held`:``}">
          <td class="n">${e.seq}</td>
          <td class="m">${String(e.at||``).slice(11,19)}</td>
          <td class="m">${p(e.tool)}</td>
          <td><span class="verdict ${n}">${p(e.decision)}</span>${r}</td>
          <td class="n">${e.amount_paise?f(e.amount_paise):`—`}</td>
          <td class="n">${i(t.enforcement_ms)}</td>
          <td class="n">${t.monitor_ran===!1?`—`:i(t.monitor_ms)}</td>
          <td class="wrap">${p(e.reason)}</td>
        </tr>`}).join(``)}</tbody>`}function Ce(){let e=F(`fleet-table`),t=L.fleet;if(!t||!(t.agents||[]).length){e.innerHTML=`<tbody><tr><td class="wrap">No agents published.</td></tr></tbody>`;return}e.innerHTML=`
    <thead><tr>
      <th>agent</th><th>department</th><th>owner</th>
      <th>may ever hold</th><th>ceiling</th><th>approved</th>
    </tr></thead>
    <tbody>${t.agents.map(e=>`
      <tr class="${e.approved?``:`row-trouble`}">
        <td class="m">${p(e.ref)}</td>
        <td>${p(e.department)}</td>
        <td>${p(e.owner)}</td>
        <td>${(e.capabilities||[]).map(e=>`<span class="cap-chip">${p(e)}</span>`).join(``)}</td>
        <td class="n">${f(e.max_budget_paise)}</td>
        <td>${e.approved?`<span class="verdict ok">yes</span>`:`<span class="verdict bad">no</span>`}</td>
      </tr>`).join(``)}</tbody>`}function we(){let e=F(`policies`);if(!L.policies.length){e.innerHTML=`<p class="sb-empty">No standing policies yet. A recurring
      instruction lives here once one is written, and does nothing until a
      person approves it.</p>`;return}e.innerHTML=`<div class="table-wrap"><table class="grid">
    <thead><tr>
      <th>instruction</th><th>dept</th><th>per period</th>
      <th>spent</th><th>reorder rules</th><th>state</th>
    </tr></thead>
    <tbody>${[...L.policies].sort((e,t)=>+!!e.approved-!!t.approved).map(e=>`
      <tr class="${e.approved?``:`row-held`}">
        <td class="wrap">${p(e.instruction||e.id||``)}</td>
        <td>${p(e.department||`—`)}</td>
        <td class="n">${f(e.period_budget_paise)} / ${p(e.period||``)}</td>
        <td class="n">${f(e.spent_this_period_paise)}</td>
        <td class="m">${(e.rules||[]).map(e=>`<span class="cap-chip">${p(e.sku)} &lt;${e.reorder_point} &rarr; ${e.target_level}</span>`).join(``)}</td>
        <td>${e.approved?`<span class="verdict ok">running</span>`:`<span class="verdict held">inert until approved</span>`}</td>
      </tr>`).join(``)}</tbody></table></div>`}function K(){let e=L.chain;if(!e){F(`chain`).innerHTML=`<p class="sb-empty">Not checked yet.</p>`;return}F(`chain`).innerHTML=`
    <p class="chain-state ${e.ok?`ok`:`bad`}">
      ${e.ok?`Intact`:`BROKEN`} · ${e.entries} entr${e.entries===1?`y`:`ies`}
    </p>
    <p class="chain-head">${p(e.head)}</p>
    <p class="chain-proves">${p(e.proves)}</p>`}function Te(e){switch(L.filter){case`paid`:return e.state===`settled`&&!e.helper;case`web`:return e.sourcing===`best`||e.helper;case`trouble`:return e.state===`refused`||e.state===`escalated`;default:return!0}}function Ee(e,t){if(t===0)return`the authority you signed`;let n=/delegate\("([^"]+)"\)/.exec(e);return n?n[1].includes(`/broker/`)?`delegation to a branch`:`delegation to a leaf`:`delegation`}function De(e){return p(e).split(`
`).map(e=>/^\s*check if/.test(e)?`<span class="chk">${e}</span>`:e).join(`
`)}function q(e){let t=h(z()).nodes.get(e);if(!t)return;L.inspecting=e,F(`drawer`).hidden=!1,F(`drawer-title`).textContent=t.task||e,F(`drawer-sub`).textContent=`${e} · depth ${t.depth} · ${t.tokenBytes??`?`} chars`+(t.expires?` · expires ${String(t.expires).slice(11,19)}`:``);let n=t.blocks||[];F(`drawer-body`).innerHTML=n.length?n.map((e,t)=>`
        <div class="blk">
          <div class="blk-head">
            <span class="blk-n">block ${t}</span>
            <span class="blk-kind">${p(Ee(e,t))}</span>
          </div>
          <pre class="blk-src">${De(e)}</pre>
        </div>`).join(``)+`<p class="chain-proves">Verification requires every check in every block to
        pass, so each block can only narrow the one above it. ${n.length}
        block${n.length===1?``:`s`} means ${n.length-1}
        delegation${n.length===2?``:`s`} from the mandate.</p>`:`<p class="sb-empty">The root mandate is minted, not attenuated, so it
        carries no delegation block yet.</p>`}function J(){L.inspecting=null,F(`drawer`).hidden=!0}function Oe(e,t){if(!e.ordered.length)return;F(`empty`)?.remove();let n=e.ordered.filter(Te),r=t.settled;r&&(L.running=!1);let i=r?`${t.paid} paid · ${t.held} held · ${t.stopped} stopped`+(t.faults.length?` · a bound refused this run`:` · every bound respected`):`running…`;F(`pane-run`).innerHTML=`
    <div class="run-head">
      <p class="run-task">${p(L.task||`Run`)}</p>
      <p class="run-meta">
        <span>${t.nodes} nodes</span>
        <span>depth ${t.depth}</span>
        <span>${t.lookers} zero-budget looker${t.lookers===1?``:`s`}</span>
        <span>${f(t.committed)} committed</span>
        ${L.floor?`<span>splits above ₹${L.floor.toLocaleString(`en-IN`)}</span>`:``}
      </p>
    </div>
    ${oe(n)}
    <p class="tail${r?` is-done`:``}">${p(i)}</p>`,ke(),r||(F(`pane-run`).scrollTop=F(`pane-run`).scrollHeight)}function ke(){let e=new Map;for(let t of L.audit)t.tool===`pay`&&t.decision===`allowed`&&t.detail&&t.detail.order_id&&e.set(String(t.context||``).replace(`leaf of the funnel: `,``),t.seq);for(let t of document.querySelectorAll(`.row.is-done`)){if(t.querySelector(`.row-actions`))continue;t.dataset.node;let n=t.querySelector(`.row-task`)?.textContent||``,r=e.get(n.replace(/open web|sources for.*$/g,``).trim());if(r===void 0)continue;let i=L.replays[r];t.insertAdjacentHTML(`beforeend`,`
      <div class="row-actions">
        <button class="mini-btn" data-replay="${r}">Replay this payment</button>
        ${i?`<span class="replay-out ${i.charged_twice?`bad`:``}">${p(i.text)}</span>`:``}
      </div>`)}}var Y=F(`task`);function X(){F(`send`).disabled=!L.live||L.running||!Y.value.trim()}Y.addEventListener(`input`,()=>{Y.style.height=`auto`,Y.style.height=Math.min(Y.scrollHeight,128)+`px`,X()}),F(`opt-monitor`).addEventListener(`change`,()=>{_.reading?.ready&&w(_.text,Z())}),Y.addEventListener(`keydown`,e=>{e.key===`Enter`&&!e.shiftKey&&(e.preventDefault(),Q())});var Z=()=>({monitor:F(`opt-monitor`).checked});function Ae(){let e=L.can,t=F(`degraded`),n=F(`opt-monitor`);if(!e){t.hidden=!0;return}let r=e.monitor===`gemini`;n.disabled=!r,n.checked=n.checked&&r;let i=n.closest(`.opt`);i.classList.toggle(`is-unavailable`,!r),i.querySelector(`span`).textContent=r?`Semantic monitor`:`Semantic monitor — no model configured`,i.dataset.tip=r?i.dataset.tipFull:`There is no model this gateway can reach, so nothing can judge a payment. Enforcement still runs in full and refuses on its own — that is the point of the two layers being separable — but no second opinion is being formed, and the audit trail records every payment as “not judged” rather than approved.`,t.hidden=!e.degraded,e.degraded&&(t.innerHTML=`<b>Running degraded.</b> ${p(e.degraded)} Enforcement is unaffected — bounds, attenuation and the audit chain are deterministic and need no model.`)}async function Q(){if(F(`send`).disabled)return;let e=Y.value.trim();$(`run`),F(`head-note`).textContent=`Reading your request. Nothing is signed yet.`,Y.value=``,Y.style.height=`auto`,X(),await w(e,Z())}async function je(e){e.budget_paise/100,L.running=!0,I.clear(),L.mandateId=null,L.mandate=null,L.task=e.task,L.floor=e.floor_paise/100,b(),$(`run`),X(),F(`head-note`).textContent=`The tree is drawing itself as the gateway builds it.`;try{let t=await n(e);L.mandateId=t.mandate_id,L.criticOn=t.critic===`gemini`||t.critic===`unconfigured`&&null;let r=(e,t)=>t===`gemini`?`${e} on`:t===`off`?`${e} off`:`no ${e} configured`;F(`head-note`).textContent=`${t.decomposer} · ${r(`critic`,t.critic)} · ${r(`monitor`,t.monitor)} · ${t.model_calls_exact?`~`:`at least `}${t.expected_model_calls} model call${t.expected_model_calls===1?``:`s`} for this run`,F(`opt-cost`).textContent=`ceiling ${f(e.budget_paise)} · floor ${f(e.floor_paise)}`}catch(e){L.running=!1,F(`head-note`).textContent=e.status===401?`This deployment gates runs behind a demo token. Everything else on this page is live and readable — the ledger, the audit trail, the tree from the last run.`:`The gateway refused the run: ${p(String(e.detail??e.message))}`}X(),await V()}E({options:Z,onRun:e=>je(e)}),document.addEventListener(`keydown`,e=>{if(e.key===`Escape`&&L.inspecting){J();return}let t=e.target.closest?.(`.row`);t&&(e.key===`Enter`||e.key===` `)&&(e.preventDefault(),q(t.dataset.node))}),F(`send`).addEventListener(`click`,Q);var Me=[`run`,`ledger`,`parties`,`fleet`,`policies`];function $(e){L.tab=e;for(let t of Me)F(`pane-${t}`).hidden=t!==e;document.querySelectorAll(`.tab`).forEach(t=>t.classList.toggle(`is-on`,t.dataset.tab===e)),document.querySelector(`.composer`).hidden=e!==`run`,F(`run-filters`).hidden=e!==`run`}document.addEventListener(`click`,async t=>{let n=t.target.closest(`[data-tab]`);if(n){$(n.dataset.tab);return}let r=t.target.closest(`[data-audit]`);if(r){L.auditFilter=r.dataset.audit,r.parentElement.querySelectorAll(`.chip`).forEach(e=>e.classList.toggle(`is-on`,e===r)),G();return}let i=t.target.closest(`[data-filter]`);if(i){L.filter=i.dataset.filter,i.parentElement.querySelectorAll(`.chip`).forEach(e=>e.classList.toggle(`is-on`,e===i)),H();return}let s=t.target.closest(`[data-task]`);if(s){Y.value=`${s.dataset.task}, budget around ₹${s.dataset.budget}`,X(),Y.focus(),Y.dispatchEvent(new Event(`input`));return}if(t.target.closest(`#drawer-close`)){J();return}let c=t.target.closest(`[data-replay]`);if(c){let e=Number(c.dataset.replay);c.disabled=!0,c.textContent=`Replaying…`;try{let t=await a(e);L.replays[e]={charged_twice:t.charged_twice,text:t.charged_twice?`CHARGED TWICE`:`same order ${t.second.order_id} · ledger unmoved`}}catch{L.replays[e]={charged_twice:!0,text:`replay failed`}}await V();return}let l=t.target.closest(`#verify-chain`);if(l){l.disabled=!0,l.textContent=`Verifying…`;try{L.chain=await o()}catch{L.chain=null}l.disabled=!1,l.textContent=`Verify chain`,K();return}let u=t.target.closest(`.row`);if(u&&!t.target.closest(`button`)){q(u.dataset.node);return}let d=t.target.closest(`[data-yes], [data-no]`);if(d){let t=d.hasAttribute(`data-yes`);d.disabled=!0,d.textContent=t?`Releasing…`:`Refusing…`;try{await e(t?d.dataset.yes:d.dataset.no,t)}finally{await V()}}}),$(`run`),me();
// theme handling (persist)
const themeSelect = document.getElementById('themeSelect');
const body = document.body;
const savedTheme = localStorage.getItem('studyTheme') || 'purple';
if(themeSelect) themeSelect.value = savedTheme;
applyTheme(savedTheme);
if(themeSelect) themeSelect.addEventListener('change', (e)=>{ applyTheme(e.target.value); localStorage.setItem('studyTheme', e.target.value); });

function applyTheme(t){
  body.classList.remove('theme-purple','theme-midnight','theme-soft');
  if(t==='purple'){ body.classList.add('theme-purple'); setCSSForPurple(); }
  if(t==='midnight'){ body.classList.add('theme-midnight'); setCSSForMidnight(); }
  if(t==='soft'){ body.classList.add('theme-soft'); setCSSForSoft(); }
}
function setCSSForPurple(){}
function setCSSForMidnight(){}
function setCSSForSoft(){}

// AI bot behavior
const aiBot = document.getElementById('aiBot');
const chatBubble = document.getElementById('chatBubble');
const chatContent = document.getElementById('chatContent');
const chatName = document.getElementById('chatName');
const chatInput = document.getElementById('chatInput');
const chatSend = document.getElementById('chatSend');
const closeChat = document.getElementById('closeChat');

async function loadProfileName(){
  try{
    const res = await fetch('/profile');
    const txt = await res.text();
    // crude parse: search for the name in HTML (we render the profile page). Better: create API
    const match = txt.match(/name\" value=\"([^\"]+)\"/);
    const name = match ? match[1] : "Student";
    chatName.textContent = `Hi ${name} — StudyMate`;
    // greeting message
    appendChat(`👋 Hi ${name}! I'm StudyMate — ask me anything about your studies or tasks.`);
  }catch(e){
    chatName.textContent = "StudyMate";
    appendChat("👋 Hi! I'm StudyMate — ask me anything.");
  }
}

aiBot?.addEventListener('click', async ()=>{
  if(chatBubble.classList.contains('hidden')){ chatBubble.classList.remove('hidden'); await loadProfileName(); }
  else { chatBubble.classList.add('hidden'); }
});

closeChat?.addEventListener('click', ()=> chatBubble.classList.add('hidden'));

function appendChat(text, who='ai'){
  const p = document.createElement('div');
  p.className = 'chat-line ' + (who==='user'?'user':'ai');
  p.textContent = text;
  chatContent.appendChild(p);
  chatContent.scrollTop = chatContent.scrollHeight;
}

chatSend?.addEventListener('click', async ()=>{
  const q = chatInput.value.trim();
  if(!q) return;
  appendChat(`You: ${q}`, 'user');
  chatInput.value = '';
  appendChat('Thinking...', 'ai');
  try{
    const res = await fetch('/ai_query', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({question:q}) });
    const j = await res.json();
    // remove 'Thinking...' last ai line
    const ais = Array.from(chatContent.querySelectorAll('.chat-line.ai'));
    if(ais.length) ais[ais.length-1].remove();
    appendChat(j.answer || "Sorry, no answer.");
  }catch(e){
    appendChat("AI error: couldn't reach server.");
  }
});

// Search: post to /search and update pending/completed lists
const globalSearch = document.getElementById('globalSearch');
if(globalSearch){
  globalSearch.addEventListener('keydown', async (e)=>{
    if(e.key==='Enter'){
      const q = globalSearch.value.trim();
      if(!q) return;
      try{
        const res = await fetch('/search', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({q}) });
        const j = await res.json();
        // show results by replacing pendingList content
        const pendingEl = document.getElementById('pendingList');
        pendingEl.innerHTML = '';
        (j.results || []).forEach(t=>{
          const div = document.createElement('div');
          div.className='task-card';
          div.innerHTML = `<div class="task-left"><div class="task-title">${t.title}</div><div class="task-meta">${t.priority} • ${t.date}</div></div>
                           <div class="task-right"><a class="btn small" href="/toggle/${t.id}">Complete</a> <a class="btn ghost" href="/delete/${t.id}">Delete</a></div>`;
          pendingEl.appendChild(div);
        });
      }catch(err){ console.error(err) }
    }
  });
}

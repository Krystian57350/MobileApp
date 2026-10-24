// Menadżer subskrypcji — Połączenie z bazą danych przez PHP API
const DEFAULT_CATEGORIES = ['Wideo','Muzyka','Aplikacje'];
const STATIC_MODE = !window.location.pathname.toLowerCase().endsWith('.php');
const POLISH_FLATPICKR_LOCALE = {
    weekdays: {
        shorthand: ['Nd', 'Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'So'],
        longhand: ['Niedziela', 'Poniedziałek', 'Wtorek', 'Środa', 'Czwartek', 'Piątek', 'Sobota']
    },
    months: {
        shorthand: ['Sty', 'Lut', 'Mar', 'Kwi', 'Maj', 'Cze', 'Lip', 'Sie', 'Wrz', 'Paź', 'Lis', 'Gru'],
        longhand: ['Styczeń', 'Luty', 'Marzec', 'Kwiecień', 'Maj', 'Czerwiec', 'Lipiec', 'Sierpień', 'Wrzesień', 'Październik', 'Listopad', 'Grudzień']
    },
    rangeSeparator: ' do ',
    weekAbbreviation: 'tydz.',
    scrollTitle: 'Przewiń, aby zwiększyć',
    toggleTitle: 'Kliknij, aby przełączyć',
    firstDayOfWeek: 1,
    time_24hr: true,
    ordinal: () => '.'
};
let subs = [];
let categories = [];
let isLoggedIn = false;
let isRegisterMode = false;
let currentUser = null;

// DOM Helpers
const el = id => document.getElementById(id);
const tbody = document.querySelector('#subsTable tbody');
const form = el('subForm');
const totalEl = el('total');

const STORAGE_KEYS = {
    accounts: 'mobileapp.accounts',
    session: 'mobileapp.session',
    data: username => `mobileapp.data.${encodeURIComponent(username.toLowerCase())}`
};

function getLocalAccounts() {
    return JSON.parse(localStorage.getItem(STORAGE_KEYS.accounts) || '[]');
}

function getLocalUsername() {
    return localStorage.getItem(STORAGE_KEYS.session);
}

function getLocalData(username) {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEYS.data(username)) || '{}');
    return {
        subs: Array.isArray(saved.subs) ? saved.subs : [],
        categories: [...new Set([...DEFAULT_CATEGORIES, ...(Array.isArray(saved.categories) ? saved.categories : [])])]
    };
}

function saveLocalData(username, data) {
    localStorage.setItem(STORAGE_KEYS.data(username), JSON.stringify(data));
}

async function hashPassword(password) {
    if (!window.crypto || !window.crypto.subtle) {
        throw new Error('Logowanie wymaga bezpiecznego połączenia HTTPS.');
    }
    const bytes = new TextEncoder().encode(password);
    const digest = await window.crypto.subtle.digest('SHA-256', bytes);
    return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
}

async function handleLocalAPI(data) {
    const username = getLocalUsername();

    switch (data.action) {
        case 'check_session':
            return username
                ? { success: true, username }
                : { success: false };
        case 'register': {
            const name = String(data.username || '').trim();
            if (!name || String(data.password || '').length < 3) {
                return { success: false, message: 'Podaj login i hasło o długości co najmniej 3 znaków.' };
            }
            const accounts = getLocalAccounts();
            if (accounts.some(account => account.username.toLowerCase() === name.toLowerCase())) {
                return { success: false, code: 'exists', message: 'Użytkownik już istnieje w tej przeglądarce.' };
            }
            accounts.push({ username: name, passwordHash: await hashPassword(data.password) });
            localStorage.setItem(STORAGE_KEYS.accounts, JSON.stringify(accounts));
            saveLocalData(name, { subs: [], categories: DEFAULT_CATEGORIES });
            return { success: true };
        }
        case 'login': {
            const name = String(data.username || '').trim();
            const account = getLocalAccounts().find(item => item.username.toLowerCase() === name.toLowerCase());
            if (!account || account.passwordHash !== await hashPassword(String(data.password || ''))) {
                return { success: false, message: 'Błędny login lub hasło.' };
            }
            localStorage.setItem(STORAGE_KEYS.session, account.username);
            return { success: true, username: account.username };
        }
        case 'logout':
            localStorage.removeItem(STORAGE_KEYS.session);
            return { success: true };
        case 'get_data': {
            if (!username) return { success: false, message: 'Zaloguj się ponownie.' };
            return { success: true, ...getLocalData(username) };
        }
        case 'save_subscription': {
            if (!username) return { success: false, message: 'Zaloguj się ponownie.' };
            const saved = getLocalData(username);
            const index = saved.subs.findIndex(item => item.id === data.id);
            const item = {
                id: data.id,
                name: String(data.name || ''),
                cost: Number(data.cost),
                period: data.period === 'yearly' ? 'yearly' : 'monthly',
                nextDate: data.nextDate || null,
                category: String(data.category || ''),
                note: String(data.note || ''),
                active: Boolean(data.active),
                added: Number(data.added) || Date.now()
            };
            if (!item.name || !Number.isFinite(item.cost) || item.cost < 0) {
                return { success: false, message: 'Nieprawidłowa nazwa lub koszt.' };
            }
            if (index < 0) saved.subs.push(item);
            else saved.subs[index] = { ...saved.subs[index], ...item };
            saveLocalData(username, saved);
            return { success: true };
        }
        case 'delete_subscription': {
            if (!username) return { success: false, message: 'Zaloguj się ponownie.' };
            const saved = getLocalData(username);
            saved.subs = saved.subs.filter(item => item.id !== data.id);
            saveLocalData(username, saved);
            return { success: true };
        }
        case 'add_category': {
            if (!username) return { success: false, message: 'Zaloguj się ponownie.' };
            const name = String(data.name || '').trim();
            const saved = getLocalData(username);
            if (!name || saved.categories.some(category => category.toLowerCase() === name.toLowerCase())) {
                return { success: false, message: 'Nazwa kategorii jest pusta lub kategoria już istnieje.' };
            }
            saved.categories.push(name);
            saveLocalData(username, saved);
            return { success: true };
        }
        case 'clear_all': {
            if (!username) return { success: false, message: 'Zaloguj się ponownie.' };
            const saved = getLocalData(username);
            saved.subs = [];
            saveLocalData(username, saved);
            return { success: true };
        }
        default:
            return { success: false, message: 'Ta funkcja nie jest dostępna w wersji GitHub Pages.' };
    }
}

// Uniwersalna funkcja do komunikacji z API albo lokalną pamięcią przeglądarki
async function requestAPI(data) {
    if (STATIC_MODE) return handleLocalAPI(data);
    try {
        const response = await fetch('api.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return await response.json();
    } catch (e) {
        console.error("Błąd sieci/API:", e);
        return { success: false, message: "Błąd połączenia z serwerem." };
    }
}

// Inicjalizacja Autoryzacji oparta na Sesji PHP
async function initAuth(){
    const res = await requestAPI({ action: 'check_session' });
    if(res.success){
        currentUser = res.username;
        isLoggedIn = true;
        showMainContent();
    } else {
        isLoggedIn = false;
        showLoginForm();
    }
}

function showLoginForm(){
    el('loginSection').classList.remove('hidden');
    el('mainContent').classList.add('hidden');
    el('logoutBtn').classList.add('hidden');
}

async function showMainContent(){
    el('loginSection').classList.add('hidden');
    el('mainContent').classList.remove('hidden');
    el('logoutBtn').classList.remove('hidden');
    
    // Ładowanie danych z bazy danych
    await loadDataFromServer();
}

async function loadDataFromServer() {
    const res = await requestAPI({ action: 'get_data' });
    if(res.success) {
        subs = Array.isArray(res.subs) ? res.subs : [];
        const serverCategories = Array.isArray(res.categories) ? res.categories.filter(Boolean) : [];
        categories = [...new Set([...DEFAULT_CATEGORIES, ...serverCategories])];
        populateCategoryOptions();
        render();
    }
}

async function handleLogin(e){
    e.preventDefault();
    const username = el('loginUsername').value.trim();
    const password = el('loginPassword').value;
    
    const res = await requestAPI({ action: 'login', username, password });
    
    if(res.success){
        currentUser = res.username;
        isLoggedIn = true;
        el('loginForm').reset();
        showMainContent();
    } else {
        alert(res.message || 'Nieprawidłowy login lub hasło!');
    }
}

function toggleAuthMode(){
    isRegisterMode = !isRegisterMode;
    const loginForm = el('loginForm');
    const registerForm = el('registerForm');
    const toggleMsg = el('toggleMsg');
    const toggleBtn = el('toggleAuthBtn');
    const authTitle = el('authTitle');
    
    if(isRegisterMode){
        loginForm.classList.add('hidden');
        registerForm.classList.remove('hidden');
        authTitle.textContent = 'Zarejestruj się';
        toggleMsg.textContent = 'Masz już konto?';
        toggleBtn.textContent = 'Zaloguj się';
    } else {
        loginForm.classList.remove('hidden');
        registerForm.classList.add('hidden');
        authTitle.textContent = 'Zaloguj się';
        toggleMsg.textContent = 'Nie masz konta?';
        toggleBtn.textContent = 'Zarejestruj się';
        clearRegisterMessages();
    }
}

function clearRegisterMessages(){
    el('userExistsMsg').classList.add('hidden');
    el('pwdLengthMsg').classList.add('hidden');
    el('pwdMatchMsg').classList.add('hidden');
}

async function handleRegister(e){
    e.preventDefault();
    clearRegisterMessages();
    
    const username = el('registerUsername').value.trim();
    const password = el('registerPassword').value;
    const passwordConfirm = el('registerPasswordConfirm').value;
    
    if(password.length < 3){
        el('pwdLengthMsg').classList.remove('hidden');
        return;
    }
    if(password !== passwordConfirm){
        el('pwdMatchMsg').classList.remove('hidden');
        return;
    }
    
    const res = await requestAPI({ action: 'register', username, password });
    
    if(res.success) {
        alert('Konto zostało utworzone! Możesz się teraz zalogować.');
        el('registerForm').reset();
        toggleAuthMode();
    } else {
        if(res.code === 'exists') {
            el('userExistsMsg').classList.remove('hidden');
        } else {
            alert(res.message);
        }
    }
}

async function handleLogout(){
    await requestAPI({ action: 'logout' });
    isLoggedIn = false;
    currentUser = null;
    subs = [];
    showLoginForm();
}

function uid(){return Date.now().toString(36)+Math.random().toString(36).slice(2,8)}
function formatCurrency(n){return new Intl.NumberFormat('pl-PL',{style:'currency',currency:'PLN'}).format(n)}
function toMonthly(cost, period){return period==='yearly'?cost/12:cost}

function populateCategoryOptions(){
    const select = el('category');
    if(!select) return;
    select.innerHTML = `<option value="">Brak</option>${categories.map(c=>`<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('')}`;
}

function openCategoryModal(){
    const modal = el('categoryModal');
    const input = el('newCategoryName');
    modal.classList.remove('hidden');
    input.value = '';
    setTimeout(()=>input.focus(), 0);
}
function closeCategoryModal(){
    el('categoryModal').classList.add('hidden');
}

async function saveNewCategory(){
    const name = el('newCategoryName').value.trim();
    if(!name){alert('Nazwa kategorii nie może być pusta.'); return}
    if(categories.includes(name)){alert('Ta kategoria już istnieje.'); return}
    
    const res = await requestAPI({ action: 'add_category', name });
    if(res.success) {
        categories.push(name);
        populateCategoryOptions();
        el('category').value = name;
        closeCategoryModal();
    } else {
        alert(res.message);
    }
}

function initDatepicker(){
    if(typeof flatpickr === 'undefined') return;
    if(typeof flatpickr.localize === 'function') {
        flatpickr.localize(POLISH_FLATPICKR_LOCALE);
    }
    if(typeof flatpickr.setDefaults === 'function') {
        flatpickr.setDefaults({ locale: POLISH_FLATPICKR_LOCALE });
    }
    flatpickr(el('nextDate'), {
        dateFormat: 'Y-m-d',
        locale: POLISH_FLATPICKR_LOCALE,
        allowInput: true,
        disableMobile: true
    });
}

function render(){
    const search = el('search').value.toLowerCase();
    const filter = el('filter').value;
    const sort = el('sort').value;

    let list = subs.slice();
    if(filter==='active') list = list.filter(s=>s.active);
    if(filter==='inactive') list = list.filter(s=>!s.active);
    if(search) list = list.filter(s=> (s.name+s.category+s.note).toLowerCase().includes(search));

    if(sort==='costDesc') list.sort((a,b)=>b.cost-a.cost);
    else if(sort==='costAsc') list.sort((a,b)=>a.cost-b.cost);
    else if(sort==='dateAsc') list.sort((a,b)=> (a.nextDate||'').localeCompare(b.nextDate||''));
    else if(sort==='dateDesc') list.sort((a,b)=> (b.nextDate||'').localeCompare(a.nextDate||''));
    else list.sort((a,b)=>b.added-a.added);

    tbody.innerHTML='';
    list.forEach(s=>{
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${escapeHtml(s.name)}</td>
            <td>${formatCurrency(s.cost)}</td>
            <td>${s.period==='monthly'?'Miesięczny':'Roczny'}</td>
            <td>${s.nextDate||'-'}</td>
            <td>${escapeHtml(s.category||'-')}</td>
            <td>${escapeHtml(s.note||'-')}</td>
            <td>${s.active? 'Tak' : 'Nie'}</td>
            <td>
                <button class="btn edit" data-id="${s.id}">Edytuj</button>
                <button class="btn delete" data-id="${s.id}">Usuń</button>
                <button class="btn toggle" data-id="${s.id}">${s.active? 'Dezaktywuj' : 'Aktywuj'}</button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    const total = subs.reduce((acc,s)=> acc + (s.active? toMonthly(s.cost,s.period):0), 0);
    totalEl.textContent = formatCurrency(total);
}

function escapeHtml(str){return String(str||'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[c])}

async function addOrUpdateFromForm(e){
    e.preventDefault();
    const id = el('subId').value || uid();
    const name = el('name').value.trim();
    const cost = parseFloat(el('cost').value);
    const period = el('period').value;
    const nextDate = el('nextDate').value || null;
    const category = el('category').value.trim();
    const note = el('note').value.trim();
    const active = el('active').checked;
    const added = Date.now();

    if(!name || isNaN(cost) || cost<0){alert('Proszę podać poprawną nazwę i koszt.');return}

    const payload = { action: 'save_subscription', id, name, cost, period, nextDate, category, note, active, added };
    
    const res = await requestAPI(payload);
    if(res.success) {
        const idx = subs.findIndex(s=>s.id===id);
        const itemData = {id, name, cost, period, nextDate, category, note, active, added};
        if(idx>-1){
            subs[idx] = itemData;
        }else{
            subs.push(itemData);
        }
        render(); form.reset(); el('subId').value='';
    } else {
        alert('Nie udało się zapisać w bazie danych: ' + res.message);
    }
}

async function handleTableClick(e){
    const id = e.target.dataset.id;
    if(!id) return;
    const s = subs.find(x=>x.id===id); 
    if(!s) return;

    if(e.target.classList.contains('edit')){
        el('subId').value = s.id;
        el('name').value = s.name;
        el('cost').value = s.cost;
        el('period').value = s.period;
        el('nextDate').value = s.nextDate || '';
        el('category').value = s.category || '';
        el('note').value = s.note || '';
        el('active').checked = !!s.active;
        window.scrollTo({top:0,behavior:'smooth'});
    }else if(e.target.classList.contains('delete')){
        if(confirm('Usuń tę subskrypcję?')){
            const res = await requestAPI({ action: 'delete_subscription', id });
            if(res.success) {
                subs = subs.filter(x=>x.id!==id); 
                render();
            }
        }
    }else if(e.target.classList.contains('toggle')){
        const updatedActive = !s.active;
        const payload = { ...s, action: 'save_subscription', active: updatedActive };
        const res = await requestAPI(payload);
        if(res.success) {
            s.active = updatedActive;
            render();
        }
    }
}

// Zostawiamy funkcję lokalną dla wygody użytkownika (pobiera plik z pamięci RAM przeglądarki)
function exportJSON(){
    const data = JSON.stringify(subs, null, 2);
    const blob = new Blob([data],{type:'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'subscriptions.json'; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
}

// Import również wysyła dane do bazy pętli po odczytaniu pliku
function importJSON(file){
    const reader = new FileReader();
    reader.onload = async ()=>{
        try{
            const imported = JSON.parse(reader.result);
            if(!Array.isArray(imported)) throw 0;
            
            for(let item of imported) {
                item.id = item.id || uid();
                item.added = item.added || Date.now();
                await requestAPI({ action: 'save_subscription', ...item });
            }
            alert('Import do bazy zakończony sukcesem.');
            await loadDataFromServer();
        }catch(e){alert('Błąd importu: niepoprawny plik JSON.')}
    }
    reader.readAsText(file);
}

// Events
form.addEventListener('submit', addOrUpdateFromForm);
el('clearBtn').addEventListener('click', ()=>{form.reset(); el('subId').value='';});
tbody.addEventListener('click', handleTableClick);
el('search').addEventListener('input', render);
el('filter').addEventListener('change', render);
el('sort').addEventListener('change', render);
el('exportBtn').addEventListener('click', exportJSON);
el('importFile').addEventListener('change', e=>{ if(e.target.files[0]) importJSON(e.target.files[0]); e.target.value='' });
el('clearAllBtn').addEventListener('click', async ()=>{ 
    if(confirm('Usunąć wszystkie subskrypcje z bazy danych?')){ 
        const res = await requestAPI({ action: 'clear_all' });
        if(res.success) { subs=[]; render(); }
    } 
});
el('addCategoryBtn').addEventListener('click', openCategoryModal);
el('saveCategoryBtn').addEventListener('click', saveNewCategory);
el('cancelCategoryBtn').addEventListener('click', closeCategoryModal);

document.addEventListener('keydown', e=>{
    if(e.key==='Escape' && !el('categoryModal').classList.contains('hidden')) closeCategoryModal();
});
el('categoryModal').addEventListener('click', e=>{
    if(e.target.id==='categoryModal') closeCategoryModal();
});

// Auth events
el('loginForm').addEventListener('submit', handleLogin);
el('registerForm').addEventListener('submit', handleRegister);
el('logoutBtn').addEventListener('click', handleLogout);
el('toggleAuthBtn').addEventListener('click', toggleAuthMode);

// Init
initAuth();
initDatepicker();
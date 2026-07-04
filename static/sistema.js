// ==========================================
// AI Popularity Predictor - Frontend Logic
// ==========================================

// --- XSS Protection ---
function escapeHtml(str) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}

const COLORS = {
    'ALTA': '#10b981', 'ALTO': '#10b981', 'Alta': '#10b981',
    'MÉDIA': '#f59e0b', 'MEDIA': '#f59e0b', 'Média': '#f59e0b',
    'BAIXA': '#f43f5e', 'Baixa': '#f43f5e'
};

// --- Populate date/time selects ---
function popularSelectsDataHora() {
    const now = new Date();
    const anoAtual = now.getFullYear();

    popularSelect('data_dia', 1, 31, true);
    popularSelect('data_mes', 1, 12, true);
    popularSelectRange('data_ano', anoAtual - 5, anoAtual + 1, false);
    popularSelect('hora_h', 0, 23, true);
    popularSelect('hora_m', 0, 59, true);

    // Default: current date/time (just set <select> value, custom UI not ready yet)
    setSelectRaw('data_dia', String(now.getDate()));
    setSelectRaw('data_mes', String(now.getMonth() + 1));
    setSelectRaw('data_ano', String(anoAtual));
    setSelectRaw('hora_h', String(now.getHours()));
    setSelectRaw('hora_m', String(now.getMinutes()));
}

function popularSelect(id, start, end, padZero) {
    const sel = document.getElementById(id);
    if (!sel) return;
    const placeholder = sel.options[0];
    sel.innerHTML = '';
    sel.appendChild(placeholder);
    for (let i = start; i <= end; i++) {
        const opt = document.createElement('option');
        const val = padZero ? String(i).padStart(2, '0') : String(i);
        opt.value = String(i);
        opt.textContent = val;
        sel.appendChild(opt);
    }
}

function popularSelectRange(id, start, end, padZero) {
    const sel = document.getElementById(id);
    if (!sel) return;
    const placeholder = sel.options[0];
    sel.innerHTML = '';
    sel.appendChild(placeholder);
    for (let i = start; i <= end; i++) {
        const opt = document.createElement('option');
        opt.value = String(i);
        opt.textContent = padZero ? String(i).padStart(2, '0') : String(i);
        sel.appendChild(opt);
    }
}

// Set value on raw <select> (before custom UI is built)
function setSelectRaw(id, value) {
    const sel = document.getElementById(id);
    if (sel) sel.value = value;
}

// --- Custom Select Dropdown ---
function initCustomSelects() {
    document.querySelectorAll('select[data-custom]').forEach(initCustomSelect);
}

function initCustomSelect(select) {
    const wrapper = document.createElement('div');
    wrapper.className = 'custom-select-wrapper';
    
    const trigger = document.createElement('div');
    trigger.className = 'custom-select-trigger';
    
    const options = document.createElement('div');
    options.className = 'custom-select-options';
    
    // Set initial trigger text
    const updateTrigger = () => {
        const selected = select.options[select.selectedIndex];
        trigger.textContent = selected ? selected.text : 'Selecionar...';
    };
    updateTrigger();
    
    Array.from(select.options).forEach((opt) => {
        const option = document.createElement('div');
        option.className = 'custom-select-option';
        option.textContent = opt.text;
        option.dataset.value = opt.value;
        if (opt.selected) option.classList.add('selected');
        
        option.addEventListener('click', (e) => {
            e.stopPropagation();
            select.value = opt.value;
            updateTrigger();
            options.querySelectorAll('.custom-select-option').forEach(o => o.classList.remove('selected'));
            option.classList.add('selected');
            options.classList.remove('open');
            // Trigger change event on original select
            select.dispatchEvent(new Event('change', { bubbles: true }));
        });
        options.appendChild(option);
    });
    
    trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        // Close other open selects
        document.querySelectorAll('.custom-select-options.open').forEach(o => {
            o.classList.remove('open');
            o.closest('.custom-select-wrapper').classList.remove('open');
        });
        const isOpen = options.classList.toggle('open');
        wrapper.classList.toggle('open', isOpen);
    });
    
    wrapper.appendChild(trigger);
    wrapper.appendChild(options);
    select.parentNode.insertBefore(wrapper, select);
    select.style.display = 'none';
    
    // Store reference for external updates
    select._customUpdate = updateTrigger;
}

document.addEventListener('click', () => {
    document.querySelectorAll('.custom-select-options.open').forEach(o => {
        o.classList.remove('open');
        o.closest('.custom-select-wrapper').classList.remove('open');
    });
});

// --- UI State ---
function mudarModo() {
    const select = document.getElementById('plataforma_destino');
    const plat = select.value;
    const isWebsite = plat === 'website';
    document.getElementById('form_website').style.display = isWebsite ? 'block' : 'none';
    document.getElementById('form_social').style.display = isWebsite ? 'none' : 'block';
    
    document.getElementById('resultadoArea').style.display = 'none';
    document.getElementById('resultadoShell').classList.remove('active');
    document.getElementById('emptyState').style.display = 'block';
    
    // Update custom select trigger if exists
    if (select._customUpdate) select._customUpdate();
}

function mostrarErro(elemento, mensagem) {
    elemento.innerHTML = `<p style="color: #f43f5e; text-align:center; font-size: 13px; padding: 20px 0;">${mensagem}</p>`;
}

function mostrarLoading(elemento, texto = "A carregar...") {
    elemento.innerHTML = `<p style="text-align:center; color: rgba(255,255,255,0.4); font-size: 13px; padding: 20px 0;">${texto}</p>`;
}

// --- Auth Check ---
function getToken() {
    return localStorage.getItem("jwt_token");
}

function requireAuth() {
    const token = getToken();
    if (!token) {
        alert("Por favor, inicie sessão para continuar.");
        window.location.href = '/login-page';
        return null;
    }
    return token;
}

// --- Prediction ---
async function fazerPrevisao() {
    const btn = document.querySelector('.btn-prever');
    const plat = document.getElementById('plataforma_destino').value;
    
    const token = requireAuth();
    if (!token) return;

    // Validate required fields
    if (plat === 'website') {
        const titulo = document.getElementById('titulo').value.trim();
        const descricao = document.getElementById('descricao').value.trim();
        if (!titulo) {
            alert("Preencha o título da notícia.");
            document.getElementById('titulo').focus();
            return;
        }
        if (!descricao) {
            alert("Preencha a descrição da notícia.");
            document.getElementById('descricao').focus();
            return;
        }
    } else {
        const texto = document.getElementById('texto_social').value.trim();
        const seguidores = document.getElementById('seguidores_social').value;
        const likes = document.getElementById('likes_social').value;
        const comentarios = document.getElementById('comentarios_social').value;
        if (!texto) {
            alert("Preencha o texto da publicação.");
            document.getElementById('texto_social').focus();
            return;
        }
        if (!seguidores || parseInt(seguidores) <= 0) {
            alert("Indique o número de seguidores.");
            document.getElementById('seguidores_social').focus();
            return;
        }
        if (likes === '' || parseInt(likes) < 0) {
            alert("Indique o número de likes.");
            document.getElementById('likes_social').focus();
            return;
        }
        if (comentarios === '' || parseInt(comentarios) < 0) {
            alert("Indique o número de comentários.");
            document.getElementById('comentarios_social').focus();
            return;
        }
    }

    btn.innerText = "A processar...";
    btn.disabled = true;

    const formData = new FormData();
    if (plat === 'website') {
        formData.append('titulo', document.getElementById('titulo').value.trim());
        formData.append('descricao', document.getElementById('descricao').value.trim());
        formData.append('categoria', document.getElementById('categoria').value);
        formData.append('data_dia', document.getElementById('data_dia').value);
        formData.append('data_mes', document.getElementById('data_mes').value);
        formData.append('data_ano', document.getElementById('data_ano').value);
        formData.append('hora_h', document.getElementById('hora_h').value);
        formData.append('hora_m', document.getElementById('hora_m').value);
    } else {
        formData.append('texto_social', document.getElementById('texto_social').value.trim());
        formData.append('seguidores', document.getElementById('seguidores_social').value);
        formData.append('likes', document.getElementById('likes_social').value);
        formData.append('comentarios', document.getElementById('comentarios_social').value);
        const foto = document.getElementById('imagem_social').files[0];
        if (foto) formData.append('imagem_post', foto);
    }

    try {
        const res = await fetch(plat === 'website' ? '/prever' : '/prever_social', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + token },
            body: formData
        });
        
        const data = await res.json();
        btn.innerText = "Analisar com IA";
        btn.disabled = false;

        if (!data.sucesso) {
            alert("Erro: " + data.erro);
            return;
        }

        document.getElementById('emptyState').style.display = 'none';
        document.getElementById('resultadoArea').style.display = 'block';
        document.getElementById('resultadoShell').classList.add('active');

        const previsao = data.previsao.toUpperCase();
        const scoreEl = document.getElementById('textoResultado');
        scoreEl.innerText = previsao;
        scoreEl.style.color = COLORS[previsao] || COLORS[data.previsao] || '#ffffff';

        const caixaSugestoes = document.getElementById('caixaSugestoes');
        const listaSugestoes = document.getElementById('listaSugestoes');
        
        if (plat === 'website') {
            document.getElementById('detalhesIA').innerText = "Análise efetuada com base no contexto editorial e processamento de linguagem natural.";
            caixaSugestoes.style.display = 'none';
            listaSugestoes.innerHTML = '';
        } else {
            document.getElementById('detalhesIA').innerText = data.contexto_ia;
            
            if (data.sugestoes && data.sugestoes.length > 0) {
                caixaSugestoes.style.display = 'block';
                listaSugestoes.innerHTML = data.sugestoes.map(d => `<li>${escapeHtml(d)}</li>`).join('');
            } else {
                caixaSugestoes.style.display = 'none';
            }
        }
    } catch (err) {
        btn.innerText = "Analisar com IA";
        btn.disabled = false;
        alert("Erro de comunicação com o servidor.");
    }
}

// --- Feedback ---
async function enviarFeedback() {
    const plat = document.getElementById('plataforma_destino').value;
    const popularidade = document.getElementById('popularidade_real_user').value;
    const textoIA = document.getElementById('textoResultado').innerText;
    const previsaoIA = textoIA.replace('Previsão:', '').trim();

    const token = requireAuth();
    if (!token) return;

    let dadosJSON = {};
    if (plat === 'website') {
        dadosJSON = { 
            titulo: document.getElementById('titulo').value, 
            descricao: document.getElementById('descricao').value, 
            categoria: document.getElementById('categoria').value, 
            popularidade_real: popularidade,
            previsao_ia: previsaoIA
        };
    } else {
        dadosJSON = { 
            plataforma: plat, 
            popularidade_real: popularidade, 
            texto_post: document.getElementById('texto_social').value, 
            seguidores: document.getElementById('seguidores_social').value,
            likes: document.getElementById('likes_social').value,
            comentarios: document.getElementById('comentarios_social').value,
            previsao_ia: previsaoIA
        };
    }

    const btnSubmit = document.getElementById('btnSubmitFeedback');
    btnSubmit.innerText = "A enviar...";
    btnSubmit.disabled = true;

    try {
        const res = await fetch('/feedback', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify(dadosJSON) 
        });
        
        const result = await res.json();
        btnSubmit.innerText = "Submeter";
        btnSubmit.disabled = false;
        const aviso = document.getElementById('mensagemAviso');
        
        if (result.sucesso) {
            aviso.innerText = "Feedback guardado com sucesso!";
            aviso.style.color = "#10b981";
            carregarHistorico();
        } else {
            aviso.innerText = result.erro || "Erro ao submeter feedback.";
            aviso.style.color = "#f43f5e";
        }
    } catch (err) {
        btnSubmit.innerText = "Submeter";
        btnSubmit.disabled = false;
        document.getElementById('mensagemAviso').innerText = "Erro de conexão.";
        document.getElementById('mensagemAviso').style.color = "#f43f5e";
    }
}

// --- Authentication ---
document.addEventListener("DOMContentLoaded", () => {
    mudarModo();
    verificarLoginStatus();
    // Populate date/time options BEFORE custom select init
    popularSelectsDataHora();
    // Now init custom selects — they'll read the populated options
    initCustomSelects();
});

function fazerLogout() {
    localStorage.removeItem("jwt_token");
    localStorage.removeItem("user_nome");
    window.location.href = '/';
}

function verificarLoginStatus() {
    const token = getToken();
    const nome = localStorage.getItem("user_nome");
    const zonaUser = document.getElementById("zona-utilizador");
    const historicoContainer = document.getElementById("historico-container");
    const feedbackArea = document.getElementById("feedbackArea");

    if (token && nome) {
        zonaUser.innerHTML = `
            <span style="color: rgba(255,255,255,0.7);">Olá, <b style="color: #fff;">${escapeHtml(nome)}</b></span> 
            <button class="btn-logout" onclick="fazerLogout()">Sair</button>
        `;
        if (historicoContainer) historicoContainer.style.display = "block";
        if (feedbackArea) feedbackArea.style.display = "block";
        carregarHistorico();
    } else {
        zonaUser.innerHTML = `<button class="btn-auth" onclick="window.location.href='/login-page'">Iniciar Sessão</button>`;
        if (historicoContainer) historicoContainer.style.display = "none";
        if (feedbackArea) feedbackArea.style.display = "none";
    }
}

// --- History ---
async function carregarHistorico() {
    const lista = document.getElementById('lista-historico');
    if (!lista) return;
    
    const token = getToken();
    if (!token) {
        lista.innerHTML = '<p style="text-align:center; color: rgba(255,255,255,0.4); font-size: 13px; padding: 20px 0;">Faça login para ver o histórico.</p>';
        return;
    }

    mostrarLoading(lista, "A carregar histórico...");

    try {
        const res = await fetch('/api/historico', {
            method: 'GET',
            headers: { 'Authorization': 'Bearer ' + token }
        });

        if (res.status === 401) {
            mostrarErro(lista, "Sessão expirou. Faça login novamente.");
            setTimeout(fazerLogout, 2000);
            return;
        }

        const data = await res.json();

        if (!data.sucesso) {
            mostrarErro(lista, data.erro || "Erro ao carregar histórico.");
            return;
        }

        if (!data.historico || data.historico.length === 0) {
            lista.innerHTML = '<p style="text-align:center; color: rgba(255,255,255,0.4); font-size: 13px; padding: 20px 0;">Ainda não submeteu nenhum feedback.</p>';
            return;
        }
        
        let html = '';
        data.historico.forEach(item => {
            const isNoticia = item.tipo === 'noticia';
            const icone = isNoticia ? '📰' : '📱';
            
            const corBadge = item.feedback === 'Alta' ? 'badge-alta' : 
                             (item.feedback === 'Baixa' ? 'badge-baixa' : 'badge-media');
            
            const iaBadge = (item.previsao_ia || '').toUpperCase() === 'ALTA' ? 'badge-alta' : 
                           ((item.previsao_ia || '').toUpperCase() === 'BAIXA' ? 'badge-baixa' : 'badge-media');
            
            html += `
            <div class="historico-item">
                <div class="historico-header-row">
                    <span class="historico-tipo">${icone} ${isNoticia ? 'Notícia' : 'Rede Social'}</span>
                    <span class="historico-data">${escapeHtml(item.data)}</span>
                </div>
                <div class="historico-titulo">"${escapeHtml(item.titulo)}"</div>
                <div class="historico-detalhe">${escapeHtml(item.detalhe)}</div>
                <div class="historico-badges">
                    <div class="badge-group">
                        <span class="badge-label">IA:</span>
                        <span class="badge ${iaBadge}">${escapeHtml(item.previsao_ia || 'N/A')}</span>
                    </div>
                    <div class="badge-group">
                        <span class="badge-label">Tu:</span>
                        <span class="badge ${corBadge}">${escapeHtml(item.feedback || 'N/A')}</span>
                    </div>
                </div>
            </div>`;
        });
        lista.innerHTML = html;
    } catch (e) {
        mostrarErro(lista, "Falha de conexão com o servidor.");
    }
}

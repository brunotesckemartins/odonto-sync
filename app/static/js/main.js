// OdontoSync - Main JavaScript

// Theme Toggle
document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const root = document.documentElement;
    
    // Carregar tema salvo
    const savedTheme = localStorage.getItem('theme') || 'light';
    root.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
    
    if (!themeToggle) {
        return;
    }

    // Toggle de tema
    themeToggle.addEventListener('click', () => {
        const currentTheme = root.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        
        root.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateThemeIcon(newTheme);
    });
    
    function updateThemeIcon(theme) {
        const darkModeIcon = document.querySelector('.theme-icon.dark-mode');
        const lightModeIcon = document.querySelector('.theme-icon.light-mode');
        if (!darkModeIcon || !lightModeIcon) {
            return;
        }

        if (theme === 'light') {
            darkModeIcon.style.display = 'inline';
            lightModeIcon.style.display = 'none';
        } else {
            darkModeIcon.style.display = 'none';
            lightModeIcon.style.display = 'inline';
        }
    }
});

// ── Funções compartilhadas para a página de agenda (reagendamento inline) ──

function removerConsultaDaTela(consultaId) {
    const row = document.getElementById(`consulta-row-${consultaId}`);
    if (row) row.remove();
    const panel = document.getElementById(`consulta-panel-${consultaId}`);
    if (panel) panel.remove();
    const card = document.getElementById(`consulta-card-${consultaId}`);
    if (card) card.remove();
}

// Buscar opções de reagendamento inteligente (agenda inline)
function buscarReagendamento(consultaId) {
    const container = document.getElementById(`reagendamento-${consultaId}`);
    const panelRow = document.getElementById(`consulta-panel-${consultaId}`);
    if (!container) return;

    container.innerHTML = '<p class="loading">Calculando melhores opções de reagendamento…</p>';
    container.style.display = 'block';
    if (panelRow) panelRow.style.display = 'table-row';

    fetch(`/reorganizacao/reagendamento/${consultaId}`)
        .then(response => response.json())
        .then(data => {
            if (!data.sucesso || !data.opcoes || data.opcoes.length === 0) {
                container.innerHTML = '<p>Nenhuma opção de reagendamento encontrada.</p>';
                return;
            }

            let html = '<div class="substitutos-list"><h4>Melhores horários para reagendar:</h4>';
            data.opcoes.forEach((opcao) => {
                html += `
                    <div class="substituto-card" style="padding:1rem;border-radius:10px;margin-bottom:0.75rem;border:1px solid var(--border-color);background:var(--bg-secondary);">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
                            <strong>${opcao.data} às ${opcao.horario}</strong>
                            <span class="badge badge-success">Score ${opcao.score}</span>
                        </div>
                        <p style="font-size:0.82rem;color:var(--text-secondary);margin-bottom:0.4rem;">
                            Prob. falta: <strong>${opcao.probabilidade_falta}%</strong> ·
                            Redução: <strong style="color:var(--success)">-${opcao.reducao_risco_pp} p.p.</strong> ·
                            Confiança: ${opcao.confianca}%
                        </p>
                        <div class="progress-bar" style="margin-bottom:0.5rem;">
                            <div class="progress-fill info" style="width:${opcao.confianca}%"></div>
                        </div>
                        <p style="font-size:0.8rem;color:var(--text-secondary);font-style:italic;margin-bottom:0.5rem;">${opcao.justificativa}</p>
                        <button onclick="confirmarReagendamento(${consultaId}, '${opcao.data}', '${opcao.horario}')"
                                style="width:100%;padding:0.5rem;font-size:0.85rem;border-radius:8px;">
                            Confirmar Reagendamento
                        </button>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;
        })
        .catch(error => {
            container.innerHTML = `<p class="alert alert-danger">Erro: ${error.message}</p>`;
        });
}

// Confirmar reagendamento (agenda inline)
function confirmarReagendamento(consultaId, data, horario) {
    if (!confirm(`Confirmar reagendamento para ${data} às ${horario}?`)) return;

    const formData = new FormData();
    formData.append('consulta_id', consultaId);
    formData.append('data', data);
    formData.append('horario', horario);

    fetch('/reorganizacao/confirmar-reagendamento', { method: 'POST', body: formData })
        .then(response => response.json())
        .then(data => {
            if (data.sucesso) {
                removerConsultaDaTela(consultaId);
            } else {
                alert('Erro: ' + data.mensagem);
            }
        })
        .catch(error => alert('Erro: ' + error.message));
}

// Auto-update para agenda (a cada 5 min)
function autoUpdateAgenda() {
    const isAgendaPage = window.location.pathname === '/' || window.location.pathname.startsWith('/?');
    if (isAgendaPage) {
        setInterval(() => location.reload(), 5 * 60 * 1000);
    }
}

autoUpdateAgenda();

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

// Buscar Substitutos (Reorganização)
function buscarSubstitutos(consultaId) {
    const container = document.getElementById(`substitutos-${consultaId}`);
    
    // Mostrar loading
    container.innerHTML = '<p class="loading">Buscando substitutos...</p>';
    container.style.display = 'block';
    
    fetch(`/reorganizacao/substitutos/${consultaId}`)
        .then(response => response.json())
        .then(data => {
            if (data.sucesso && data.substitutos.length > 0) {
                let html = '<div class="substitutos-list">';
                html += '<h4>Substitutos Recomendados:</h4>';
                
                data.substitutos.forEach((sub, index) => {
                    html += `
                        <div class="substituto-card">
                            <div class="substituto-header">
                                <strong>${sub.nome}</strong>
                                <span class="badge badge-info">${sub.tipo_pagamento}</span>
                            </div>
                            <div class="substituto-body">
                                <p><strong>Probabilidade de Falta:</strong> ${sub.probabilidade_falta}%</p>
                                <div class="progress-bar">
                                    <div class="progress-fill success" style="width: ${100 - sub.probabilidade_falta}%"></div>
                                </div>
                                <p class="justificativa">${sub.justificativa}</p>
                                <p><strong>Score:</strong> ${sub.score}/100</p>
                            </div>
                            <button onclick="confirmarSubstituicao(${consultaId}, '${sub.paciente_id}', '${data.consulta.data}', '${data.consulta.horario}')">
                                Confirmar Substituição
                            </button>
                        </div>
                    `;
                });
                
                html += '</div>';
                container.innerHTML = html;
            } else {
                container.innerHTML = '<p>Nenhum substituto disponível no momento.</p>';
            }
        })
        .catch(error => {
            container.innerHTML = `<p class="alert alert-danger">Erro ao buscar substitutos: ${error.message}</p>`;
        });
}

function removerConsultaDaTela(consultaId) {
    const row = document.getElementById(`consulta-row-${consultaId}`);
    if (row) {
        row.remove();
    }

    const card = document.getElementById(`consulta-card-${consultaId}`);
    if (card) {
        card.remove();
    }
}

function mostrarMensagemContainer(consultaId, tipo, mensagem) {
    const containers = [
        document.getElementById(`substitutos-${consultaId}`),
        document.getElementById(`reagendamento-${consultaId}`)
    ].filter(Boolean);

    containers.forEach((container) => {
        container.style.display = 'block';
        container.innerHTML = `<p class="alert alert-${tipo}">${mensagem}</p>`;
    });
}

// Confirmar Substituição
function confirmarSubstituicao(consultaId, pacienteId, dataConsulta, horario) {
    if (!confirm('Deseja confirmar esta substituição?')) {
        return;
    }
    
    const formData = new FormData();
    formData.append('consulta_id', consultaId);
    formData.append('paciente_id', pacienteId);
    formData.append('data', dataConsulta);
    formData.append('horario', horario);
    
    fetch('/reorganizacao/confirmar', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            mostrarMensagemContainer(consultaId, 'success', data.mensagem);
            removerConsultaDaTela(consultaId);
        } else {
            alert('Erro: ' + data.mensagem);
        }
    })
    .catch(error => {
        alert('Erro ao confirmar substituição: ' + error.message);
    });
}

// Buscar opções de reagendamento inteligente
function buscarReagendamento(consultaId) {
    const container = document.getElementById(`reagendamento-${consultaId}`);
    container.innerHTML = '<p class="loading">Calculando melhores opções de reagendamento...</p>';
    container.style.display = 'block';

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
                    <div class="substituto-card">
                        <div class="substituto-header">
                            <strong>${opcao.data} às ${opcao.horario}</strong>
                            <span class="badge badge-success">Score ${opcao.score}</span>
                        </div>
                        <div class="substituto-body">
                            <p><strong>Probabilidade de falta:</strong> ${opcao.probabilidade_falta}%</p>
                            <p><strong>Redução de risco:</strong> ${opcao.reducao_risco_pp} p.p.</p>
                            <p class="justificativa">${opcao.justificativa}</p>
                        </div>
                        <button onclick="confirmarReagendamento(${consultaId}, '${opcao.data}', '${opcao.horario}')">
                            Confirmar Reagendamento
                        </button>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;
        })
        .catch(error => {
            container.innerHTML = `<p class="alert alert-danger">Erro ao sugerir reagendamento: ${error.message}</p>`;
        });
}

// Confirmar reagendamento
function confirmarReagendamento(consultaId, data, horario) {
    if (!confirm(`Confirmar reagendamento para ${data} às ${horario}?`)) {
        return;
    }

    const formData = new FormData();
    formData.append('consulta_id', consultaId);
    formData.append('data', data);
    formData.append('horario', horario);

    fetch('/reorganizacao/confirmar-reagendamento', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            mostrarMensagemContainer(consultaId, 'success', data.mensagem);
            removerConsultaDaTela(consultaId);
        } else {
            alert('Erro: ' + data.mensagem);
        }
    })
    .catch(error => {
        alert('Erro ao confirmar reagendamento: ' + error.message);
    });
}

// Auto-update para agenda (opcional)
function autoUpdateAgenda() {
    const isAgendaPage = window.location.pathname === '/';
    
    if (isAgendaPage) {
        setInterval(() => {
            // Recarregar a página a cada 5 minutos
            location.reload();
        }, 5 * 60 * 1000);
    }
}

// Inicializar
autoUpdateAgenda();

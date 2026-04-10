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
                            <button onclick="confirmarSubstituicao(${consultaId}, '${sub.paciente_id}', '${data.consulta.horario}')">
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

// Confirmar Substituição
function confirmarSubstituicao(consultaId, pacienteId, horario) {
    if (!confirm('Deseja confirmar esta substituição?')) {
        return;
    }
    
    const formData = new FormData();
    formData.append('consulta_id', consultaId);
    formData.append('paciente_id', pacienteId);
    formData.append('data', new Date().toISOString().split('T')[0]);
    formData.append('horario', horario);
    
    fetch('/reorganizacao/confirmar', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            alert('Sucesso: ' + data.mensagem);
            location.reload();
        } else {
            alert('Erro: ' + data.mensagem);
        }
    })
    .catch(error => {
        alert('Erro ao confirmar substituição: ' + error.message);
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

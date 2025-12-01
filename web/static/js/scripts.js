// --- 1. LÓGICA DE APARICIÓN DEL CHATBOT ---
document.addEventListener('DOMContentLoaded', function() {
    // Leemos la variable global definida en el HTML
    // Si no existe, asumimos falso por seguridad
    const isLoggedIn = window.isUserLoggedIn || false; 
    
    if (isLoggedIn) {
        setTimeout(() => {
            const widget = document.getElementById('chatbot-widget');
            if(widget) widget.style.display = 'block';
        }, 1500); 
    }
});

// --- 2. LÓGICA VISUAL DEL CHAT ---
let isChatOpen = false;

function toggleChat() {
    const body = document.getElementById('chat-body');
    const input = document.getElementById('chat-input-area');
    const icon = document.getElementById('chat-icon');
    
    isChatOpen = !isChatOpen;
    
    if (isChatOpen) {
        body.style.display = 'block';
        input.style.display = 'block';
        icon.classList.remove('fa-chevron-up');
        icon.classList.add('fa-chevron-down');
    } else {
        body.style.display = 'none';
        input.style.display = 'none';
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-up');
    }
}

function handleEnter(e) {
    if (e.key === 'Enter') sendMessage();
}

// --- 3. CONEXIÓN CON EL CEREBRO DEL BOT (AJAX) ---
function sendMessage() {
    const input = document.getElementById('user-input');
    const text = input.value.trim();
    if (!text) return;

    addMessage(text, 'user-msg');
    input.value = '';
    showTypingIndicator();

    fetch('/api/chat/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: text })
    })
    .then(response => response.json())
    .then(data => {
        removeTypingIndicator();
        addMessage(data.reply, 'bot-msg');
    })
    .catch(error => {
        console.error('Error:', error);
        removeTypingIndicator();
        addMessage("Ups, tuve un problema de conexión 🔌", 'bot-msg');
    });
}

function addMessage(text, className) {
    const div = document.createElement('div');
    div.className = `message ${className}`;
    div.innerHTML = text; 
    const body = document.getElementById('chat-body');
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
}

function showTypingIndicator() {
    const div = document.createElement('div');
    div.id = 'typing-indicator';
    div.className = 'message bot-msg text-muted';
    div.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Procesando...';
    document.getElementById('chat-body').appendChild(div);
    document.getElementById('chat-body').scrollTop = document.getElementById('chat-body').scrollHeight;
}

function removeTypingIndicator() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
}
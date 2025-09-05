let isWatching = false;

// ページ読み込み時に状態を取得
document.addEventListener('DOMContentLoaded', function() {
    updateWatchStatus();
    // 5秒ごとに状態を更新
    setInterval(updateWatchStatus, 5000);
});

function updateWatchStatus() {
    fetch('/api/watch-status/')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                isWatching = data.is_watching;
                updateUI();
            }
        })
        .catch(error => {
            console.error('状態取得エラー:', error);
        });
}

function updateUI() {
    const statusIndicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    
    if (isWatching) {
        statusIndicator.className = 'status-indicator status-watching';
        statusText.textContent = '監視中';
        startBtn.disabled = true;
        stopBtn.disabled = false;
    } else {
        statusIndicator.className = 'status-indicator status-stopped';
        statusText.textContent = '停止中';
        startBtn.disabled = false;
        stopBtn.disabled = true;
    }
}

function toggleWatch(action) {
    const messageDiv = document.getElementById('message');
    
    fetch('/api/toggle-watch/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ action: action })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            isWatching = data.is_watching;
            updateUI();
            showMessage(data.message, 'success');
        } else {
            showMessage(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('エラー:', error);
        showMessage('通信エラーが発生しました', 'error');
    });
}

function showMessage(text, type) {
    const messageDiv = document.getElementById('message');
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = 'block';
    
    // 3秒後にメッセージを非表示
    setTimeout(() => {
        messageDiv.style.display = 'none';
    }, 3000);
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

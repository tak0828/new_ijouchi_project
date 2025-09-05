// サイドバーの初期化
document.addEventListener('DOMContentLoaded', function() {
    initSidebar();
});

// サイドバーの初期化
function initSidebar() {
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const sidebarClose = document.getElementById('sidebarClose');
    
    // サイドバー開く
    sidebarToggle.addEventListener('click', function() {
        openSidebar();
    });
    
    // サイドバー閉じる
    sidebarClose.addEventListener('click', function() {
        closeSidebar();
    });
    
    // オーバーレイクリックで閉じる
    sidebarOverlay.addEventListener('click', function() {
        closeSidebar();
    });
    
    // ESCキーで閉じる
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && sidebar.classList.contains('open')) {
            closeSidebar();
        }
    });
}

// サイドバーを開く
function openSidebar() {
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const body = document.body;
    
    sidebar.classList.add('open');
    sidebarOverlay.classList.add('active');
    body.classList.add('sidebar-open');
}

// サイドバーを閉じる
function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const body = document.body;
    
    sidebar.classList.remove('open');
    sidebarOverlay.classList.remove('active');
    body.classList.remove('sidebar-open');
}

// 未実装ページ用の関数
function showComingSoon(pageName) {
    alert(`${pageName}ページは準備中です。`);
}

// تحديث عدد الإشعارات غير المقروءة
function updateNotificationCount() {
    $.ajax({
        url: '/api/notifications/unread_count/',
        method: 'GET',
        success: function(response) {
            const badge = $('.notification-badge');
            if (response.count > 0) {
                badge.text(response.count).show();
            } else {
                badge.hide();
            }
        }
    });
}

// تحديث الإشعارات كل دقيقة
setInterval(updateNotificationCount, 60000);

// تعليم الإشعار كمقروء عند النقر عليه
$(document).on('click', '.notification-item', function() {
    const notificationId = $(this).data('id');
    $.ajax({
        url: `/api/notifications/${notificationId}/mark_as_read/`,
        method: 'POST',
        headers: {
            "X-CSRFToken": getCookie('csrftoken')
        }
    });
});

// دالة مساعدة للحصول على قيمة الكوكي
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
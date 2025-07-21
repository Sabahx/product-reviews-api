// ✅ دالة جلب CSRF من الميتا
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// ✅ تحديث عدد الإشعارات غير المقروءة
function updateNotificationCount() {
    $.ajax({
        url: '/api/notifications/unread_count/',
        method: 'GET',
        headers: {
            'X-CSRFToken': getCSRFToken()
        },
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

// ✅ تعليم الإشعار كمقروء عند النقر عليه
$(document).on('click', '.notification-item', function() {
    const notificationId = $(this).data('id');
    $.ajax({
        url: `/api/notifications/${notificationId}/mark_as_read/`,
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken()
        }
    });
});

// ✅ تحديث الإشعارات كل دقيقة
setInterval(updateNotificationCount, 60000);

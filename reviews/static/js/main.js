// ✅ دالة جلب CSRF من <meta>
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// ✅ تهيئة الصفحة عند التحميل
$(document).ready(function() {
    // تفعيل عناصر Bootstrap التي تحتاج JS
    $('[data-toggle="tooltip"]').tooltip();
    $('[data-toggle="popover"]').popover();
    
    // إدارة التنبيهات
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);
    
    // إدارة القائمة المنسدلة في الهاتف
    $('.navbar-toggler').click(function() {
        $('.navbar-collapse').toggleClass('show');
    });
    
    // إدارة النماذج
    $('form').submit(function(e) {
        $(this).find('button[type="submit"]').prop('disabled', true);
    });
});

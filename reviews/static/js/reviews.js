(function ($) {

  // ✅ دالة جلب CSRF من الـ <meta>
function getCSRFToken() {
  return window.CSRF_TOKEN;
}



  // ✅ التفاعل (مفيد / غير مفيد)
  $(document).on('click', '.review-interaction', function () {
    const btn = $(this);
    const reviewId = btn.data('review-id');
    const isHelpful = btn.data('helpful');

    $.ajax({
      url: `/api/reviews/${reviewId}/interact/`,
      method: 'POST',
      data: { helpful: isHelpful },
      headers: { "X-CSRFToken": getCSRFToken() },
      success: function () {
        location.reload(); // نحدّث الصفحة لعرض الأرقام المحدثة
      },
      error: function () {
        alert('⚠️ فشل في إرسال التفاعل.');
      }
    });
  });

  // ✅ التبليغ عن مراجعة (🚩)
  $(document).on('submit', 'form[action^="/report/"]', function (e) {
    e.preventDefault();
    const form = $(this);

    $.ajax({
      url: form.attr('action'),
      method: 'POST',
      data: form.serialize(),
      headers: { "X-CSRFToken": getCSRFToken() },
      success: function () {
        alert('✅ تم الإبلاغ عن المراجعة.');
        location.reload();
      },
      error: function () {
        alert('⚠️ فشل في إرسال البلاغ.');
      }
    });
  });

})(jQuery);

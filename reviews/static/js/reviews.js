(function ($) {

  // ✅ جلب الـ JWT Access Token من LocalStorage
  function getJWTToken() {
    return localStorage.getItem("access_token");
  }

  // ✅ التفاعل (مفيد / غير مفيد) باستخدام JWT
  $(document).on('click', '.review-interaction', function () {
    const btn = $(this);
    const reviewId = btn.data('review-id');
    const isHelpful = btn.data('helpful');

    $.ajax({
      url: `/api/reviews/${reviewId}/interact/`,
      method: 'POST',
      contentType: 'application/json',
      data: JSON.stringify({ helpful: isHelpful }),
      headers: {
        "Authorization": `Bearer ${getJWTToken()}`
      },
      success: function () {
        location.reload();
      },
      error: function (xhr) {
        if (xhr.status === 401) {
          alert('⚠️ يجب تسجيل الدخول باستخدام JWT.');
        } else {
          alert('⚠️ فشل في إرسال التفاعل.');
        }
      }
    });
  });

  // ✅ التبليغ عن مراجعة باستخدام JWT
  $(document).on('submit', 'form[action^="/report/"]', function (e) {
    e.preventDefault();
    const form = $(this);

    $.ajax({
      url: form.attr('action'),
      method: 'POST',
      data: form.serialize(),
      headers: {
        "Authorization": `Bearer ${getJWTToken()}`
      },
      success: function () {
        alert('✅ تم الإبلاغ عن المراجعة.');
        location.reload();
      },
      error: function (xhr) {
        if (xhr.status === 401) {
          alert('⚠️ يجب تسجيل الدخول باستخدام JWT.');
        } else {
          alert('⚠️ فشل في إرسال البلاغ.');
        }
      }
    });
  });

})(jQuery);

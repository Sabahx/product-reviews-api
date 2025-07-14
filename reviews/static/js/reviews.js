// إرسال تقييم جديد
$('#review-form').submit(function(e) {
    e.preventDefault();
    const form = $(this);
    const submitBtn = form.find('button[type="submit"]');
    
    submitBtn.prop('disabled', true);
    submitBtn.html('<i class="fas fa-spinner fa-spin"></i> جاري الإرسال...');
    
    $.ajax({
        url: form.attr('action'),
        method: 'POST',
        data: form.serialize(),
        headers: {
            "X-CSRFToken": getCookie('csrftoken')
        },
        success: function(response) {
            location.reload();
        },
        error: function(xhr) {
            alert('حدث خطأ: ' + xhr.responseJSON.error);
            submitBtn.prop('disabled', false);
            submitBtn.text('إرسال التقييم');
        }
    });
});

// التفاعل مع المراجعات (إعجاب/عدم إعجاب)
$(document).on('click', '.review-interaction', function() {
    const btn = $(this);
    const reviewId = btn.data('review-id');
    const isHelpful = btn.data('helpful');
    
    $.ajax({
        url: `/api/reviews/${reviewId}/interact/`,
        method: 'POST',
        data: {
            helpful: isHelpful
        },
        headers: {
            "X-CSRFToken": getCookie('csrftoken')
        },
        success: function(response) {
            btn.toggleClass('active');
            btn.find('.count').text(response.new_count);
        }
    });
});
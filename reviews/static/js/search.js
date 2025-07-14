
$('#search-input').on('input', function() {
    const query = $(this).val();
    if (query.length > 2) {
        $.ajax({
            url: '/api/search/',
            data: { q: query },
            success: function(results) {
                const resultsContainer = $('#search-results');
                resultsContainer.empty();
                
                if (results.length > 0) {
                    results.forEach(function(item) {
                        resultsContainer.append(`
                            <div class="search-result-item">
                                <a href="${item.url}">${item.name}</a>
                            </div>
                        `);
                    });
                    resultsContainer.show();
                } else {
                    resultsContainer.hide();
                }
            }
        });
    }
});

// إخفاء نتائج البحث عند النقر خارجها
$(document).click(function(e) {
    if (!$(e.target).closest('#search-container').length) {
        $('#search-results').hide();
    }
});
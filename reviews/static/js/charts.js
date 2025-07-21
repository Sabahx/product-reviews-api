// ✅ دالة جلب CSRF من <meta>
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// ✅ تهيئة الرسوم البيانية
function initCharts() {
    // مخطط توزيع المشاعر
    const sentimentCtx = document.getElementById('sentimentChart');
    if (sentimentCtx) {
        new Chart(sentimentCtx, {
            type: 'pie',
            data: {
                labels: ['إيجابي', 'سلبي', 'محايد'],
                datasets: [{
                    data: [
                        sentimentCtx.dataset.positive,
                        sentimentCtx.dataset.negative,
                        sentimentCtx.dataset.neutral
                    ],
                    backgroundColor: ['#28a745', '#dc3545', '#ffc107']
                }]
            }
        });
    }

    // مخطط أفضل المنتجات
    const productsCtx = document.getElementById('topProductsChart');
    if (productsCtx) {
        new Chart(productsCtx, {
            type: 'bar',
            data: {
                labels: JSON.parse(productsCtx.dataset.labels),
                datasets: [{
                    label: 'متوسط التقييم',
                    data: JSON.parse(productsCtx.dataset.data),
                    backgroundColor: '#007bff'
                }]
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 5
                    }
                }
            }
        });
    }
}

// ✅ استدعاء التهيئة بعد التحميل
$(document).ready(initCharts);

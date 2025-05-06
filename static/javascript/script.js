document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const amtField = form.querySelector('input[name="amount"]');
            if (amtField && parseFloat(amtField.value) <= 0) {
                alert('请输入正数金额');
                event.preventDefault();
            }
        });
    });
});
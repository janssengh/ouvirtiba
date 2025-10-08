document.addEventListener("DOMContentLoaded", function() {
    document.querySelectorAll('.dropdown-menu').forEach(function(element) {
        element.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    })

    if (window.innerWidth < 992) {

        document.querySelectorAll('.dropdown-menu a').forEach(function(element) {
            element.addEventListener('click', function(e) {

                let nextEl = this.nextElementSibling;
                if (nextEl && nextEl.classList.contains('submenu')) {
                    e.preventDefault();
                    if (nextEl.style.display == 'block') {
                        nextEl.style.display = 'none';
                    } else {
                        nextEl.style.display = 'block';
                    }

                }
            });
        })
    }

});

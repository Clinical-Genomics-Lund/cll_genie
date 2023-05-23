document.addEventListener('DOMContentLoaded', function () {
    const tooltips = document.querySelectorAll('.df-table-class td.tooltip');
    tooltips.forEach(function (tooltip) {
        tooltip.addEventListener('mouseenter', function () {
            tooltip.setAttribute('data-title', tooltip.innerText);
        });
        tooltip.addEventListener('mouseleave', function () {
            tooltip.removeAttribute('data-title');
        });
    });
});
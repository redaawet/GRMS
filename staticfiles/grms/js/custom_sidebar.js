
document.addEventListener('DOMContentLoaded', () => {
    // TOP LEVEL ACCORDION
    document.querySelectorAll('.group-header').forEach(header => {
        header.dataset.accordionBound = 'true';
        header.addEventListener('click', () => {
            const key = header.dataset.group;
            const panel = document.getElementById(`group-${key}`);

            document.querySelectorAll('.group-items').forEach(g => {
                if (g !== panel) {
                    g.classList.remove('show');
                    g.previousElementSibling?.classList?.remove('active');
                }
            });

            const isOpen = panel.classList.toggle('show');
            header.classList.toggle('active', isOpen);
        });
    });

    // SUBGROUP ACCORDION (STYLE B)
    document.querySelectorAll('.subgroup-header').forEach(header => {
        header.dataset.accordionBound = 'true';
        header.addEventListener('click', () => {
            const key = header.dataset.subgroup;
            const panel = document.getElementById(`subgroup-${key}`);
            const parent = header.closest('.group-items');

            parent.querySelectorAll('.subgroup-items').forEach(s => {
                if (s !== panel) {
                    s.classList.remove('show');
                    s.previousElementSibling?.classList?.remove('active');
                }
            });

            const isOpen = panel.classList.toggle('show');
            header.classList.toggle('active', isOpen);
        });
    });
});



// TOP LEVEL ACCORDION
document.querySelectorAll('.group-header').forEach(header => {
    header.addEventListener('click', () => {
        const key = header.dataset.group;
        const panel = document.getElementById(`group-${key}`);

        document.querySelectorAll('.group-items').forEach(g => {
            if (g !== panel) g.classList.remove('show');
        });

        panel.classList.toggle('show');
    });
});

// SUBGROUP ACCORDION (STYLE B)
document.querySelectorAll('.subgroup-header').forEach(header => {
    header.addEventListener('click', () => {
        const key = header.dataset.subgroup;
        const panel = document.getElementById(`subgroup-${key}`);
        const parent = header.closest('.group-items');

        parent.querySelectorAll('.subgroup-items').forEach(s => {
            if (s !== panel) s.classList.remove('show');
        });

        panel.classList.toggle('show');
    });
});


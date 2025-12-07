// Hybrid accordion behavior for GRMS sidebar

// Top-level accordion (only one open at a time)
document.querySelectorAll('.group-header').forEach(header => {
    header.addEventListener('click', () => {
        const key = header.dataset.group;
        const list = document.getElementById(`group-${key}`);

        document.querySelectorAll('.group-items').forEach(other => {
            if (other !== list) other.classList.remove('show');
        });

        list.classList.toggle('show');
    });
});

// Subgroup accordion (within Reference & Lookups only)
document.querySelectorAll('.subgroup-header').forEach(header => {
    header.addEventListener('click', () => {
        const key = header.dataset.subgroup;
        const list = document.getElementById(`subgroup-${key}`);

        const parent = header.closest('.group-items');
        parent.querySelectorAll('.subgroup-items').forEach(other => {
            if (other !== list) other.classList.remove('show');
        });

        list.classList.toggle('show');
    });
});

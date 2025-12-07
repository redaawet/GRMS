// ---------------------------
// TOP LEVEL ACCORDION
// ---------------------------
function initTopLevelAccordion() {
    document.querySelectorAll('.group-header').forEach(header => {
        header.addEventListener('click', () => {
            const key = header.dataset.group;
            const list = document.getElementById(`group-${key}`);

            // Collapse other top groups
            document.querySelectorAll('.group-items').forEach(other => {
                if (other !== list) {
                    other.classList.remove('show');
                    localStorage.setItem(`sidebar-${other.id}`, 'collapsed');
                }
            });

            // Toggle current
            list.classList.toggle('show');
            const isCollapsed = !list.classList.contains('show');
            localStorage.setItem(`sidebar-${key}`, isCollapsed ? 'collapsed' : 'expanded');
        });
    });
}

// ---------------------------
// SUBGROUP ACCORDION
// ---------------------------
function initSubgroupAccordion() {
    document.querySelectorAll('.subgroup-header').forEach(header => {
        header.addEventListener('click', () => {
            const key = header.dataset.subgroup;
            const list = document.getElementById(`subgroup-${key}`);

            // Collapse siblings inside same top group
            const parent = header.closest('.group-items');
            parent.querySelectorAll('.subgroup-items').forEach(other => {
                if (other !== list) {
                    other.classList.remove('show');
                    localStorage.setItem(`subgroup-${other.id}`, 'collapsed');
                }
            });

            // Toggle current subgroup
            list.classList.toggle('show');
            const isCollapsed = !list.classList.contains('show');
            localStorage.setItem(`subgroup-${key}`, isCollapsed ? 'collapsed' : 'expanded');
        });
    });
}

document.addEventListener('DOMContentLoaded', () => {
    initTopLevelAccordion();
    initSubgroupAccordion();
});

(function () {
    "use strict";

    const $ = window.django && window.django.jQuery ? window.django.jQuery : window.jQuery;
    if (!$) {
        return;
    }

    function setDisabled(selectors, disabled) {
        selectors.forEach(function (selector) {
            const input = $(selector);
            if (!input.length) {
                return;
            }
            input.prop("disabled", disabled);
            if (disabled) {
                input.val("");
                input.closest(".form-row").addClass("is-disabled");
            } else {
                input.closest(".form-row").removeClass("is-disabled");
            }
        });
    }

    function toggleFields() {
        const culvertType = $("#id_culvert_type").val();
        const slabFields = ["#id_width_m", "#id_span_m", "#id_clear_height_m"];
        const pipeFields = ["#id_num_pipes", "#id_pipe_diameter_m"];

        if (culvertType === "Pipe Culvert") {
            setDisabled(slabFields, true);
            setDisabled(pipeFields, false);
        } else if (culvertType === "Slab Culvert" || culvertType === "Box Culvert") {
            setDisabled(pipeFields, true);
            setDisabled(slabFields, false);
        } else {
            setDisabled(pipeFields, false);
            setDisabled(slabFields, false);
        }
    }

    $(document).ready(function () {
        const typeSelect = $("#id_culvert_type");
        if (!typeSelect.length) {
            return;
        }
        typeSelect.on("change", toggleFields);
        toggleFields();
    });
})();

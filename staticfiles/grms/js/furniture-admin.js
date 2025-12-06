(function () {
  const POINT_TYPES = new Set(["KM Post", "Road Sign"]);
  const LINEAR_TYPES = new Set(["Guard Post", "Guard Rail"]);

  function $(id) {
    return document.getElementById(id);
  }

  function clearValue(input) {
    if (!input) return;
    if (input.type === "checkbox") {
      input.checked = false;
    } else {
      input.value = "";
    }
  }

  function setDisabled(input, disabled) {
    if (!input) return;
    input.disabled = disabled;
    if (disabled) {
      clearValue(input);
    }
  }

  function syncFurnitureFields() {
    const typeField = $("id_furniture_type");
    if (!typeField) return;

    const furnitureType = typeField.value;
    const isPoint = POINT_TYPES.has(furnitureType);
    const isLinear = LINEAR_TYPES.has(furnitureType);

    setDisabled($("id_chainage_km"), !isPoint);
    setDisabled($("id_chainage_from_km"), !isLinear);
    setDisabled($("id_chainage_to_km"), !isLinear);
    setDisabled($("id_left_present"), !isLinear);
    setDisabled($("id_right_present"), !isLinear);
  }

  document.addEventListener("DOMContentLoaded", function () {
    const typeField = $("id_furniture_type");
    if (!typeField) return;

    typeField.addEventListener("change", syncFurnitureFields);
    syncFurnitureFields();
  });
})();

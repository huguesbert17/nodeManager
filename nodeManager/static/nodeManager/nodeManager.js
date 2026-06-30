document.addEventListener("submit", function (event) {
  var form = event.target;
  var message = form.getAttribute("data-confirm");
  if (message && !window.confirm(message)) {
    event.preventDefault();
  }
});

document.addEventListener("change", function (event) {
  var input = event.target;
  if (!input || input.name !== "env_file" || !input.files || !input.files.length) {
    return;
  }
  var form = input.closest("form");
  var textarea = form ? form.querySelector("textarea[name='environment']") : null;
  if (!textarea) {
    return;
  }
  var reader = new FileReader();
  reader.onload = function () {
    textarea.value = reader.result || "";
  };
  reader.readAsText(input.files[0]);
});

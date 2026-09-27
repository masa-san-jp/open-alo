(function () {
  "use strict";

  var source = document.getElementById("source");
  var messages = document.getElementById("messages");
  var exampleSelect = document.getElementById("example-select");
  var graphPanel = document.getElementById("graph-panel");
  var promptPanel = document.getElementById("prompt-panel");
  var runPanel = document.getElementById("run-panel");

  function showErrors(errors) {
    messages.textContent = "";
    var list = document.createElement("ul");
    (errors || []).forEach(function (error) {
      var item = document.createElement("li");
      item.textContent = error;
      list.appendChild(item);
    });
    if (!list.children.length) {
      var success = document.createElement("p");
      success.textContent = "No errors.";
      messages.appendChild(success);
    } else {
      messages.appendChild(list);
    }
  }

  function post(path, payload) {
    return fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(function (response) {
      return response.json().then(function (body) {
        if (!response.ok) {
          throw new Error((body.errors || ["Request failed"]).join("; "));
        }
        return body;
      });
    });
  }

  document.getElementById("validate-button").addEventListener("click", function () {
    post("/api/validate", { source: source.value })
      .then(function (result) { showErrors(result.errors); })
      .catch(function (error) { showErrors([error.message]); });
  });

  document.getElementById("prompt-button").addEventListener("click", function () {
    post("/api/prompt", { source: source.value })
      .then(function (result) {
        if (result.errors) {
          showErrors(result.errors);
          promptPanel.hidden = true;
          return;
        }
        showErrors([]);
        document.getElementById("prompt-output").textContent = result.prompt;
        promptPanel.hidden = false;
      })
      .catch(function (error) { showErrors([error.message]); });
  });

  document.getElementById("graph-button").addEventListener("click", function () {
    post("/api/graph", { source: source.value, direction: "TD" })
      .then(function (result) {
        if (result.errors) {
          showErrors(result.errors);
          graphPanel.hidden = true;
          return;
        }
        showErrors([]);
        document.getElementById("graph-viewer").innerHTML = result.svg;
        document.getElementById("mermaid-output").textContent = result.mermaid;
        graphPanel.hidden = false;
      })
      .catch(function (error) { showErrors([error.message]); });
  });

  document.getElementById("run-button").addEventListener("click", function () {
    var input;
    var responses;
    try {
      input = JSON.parse(document.getElementById("input-data").value || "{}");
      responses = JSON.parse(document.getElementById("responses").value || "{}");
    } catch (error) {
      showErrors(["Run input and responses must be valid JSON."]);
      return;
    }
    post("/api/run", { source: source.value, input: input, responses: responses })
      .then(function (result) {
        if (result.errors) {
          showErrors(result.errors);
          runPanel.hidden = true;
          return;
        }
        showErrors([]);
        document.getElementById("run-output").textContent = JSON.stringify(result, null, 2);
        runPanel.hidden = false;
      })
      .catch(function (error) { showErrors([error.message]); });
  });

  exampleSelect.addEventListener("change", function () {
    var selected = exampleSelect.options[exampleSelect.selectedIndex];
    if (selected && selected.dataset.source) {
      source.value = selected.dataset.source;
    }
  });

  document.getElementById("file-input").addEventListener("change", function (event) {
    var file = event.target.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function () { source.value = reader.result; };
    reader.onerror = function () { showErrors(["Could not read the selected file."]); };
    reader.readAsText(file);
  });

  document.getElementById("download-button").addEventListener("click", function () {
    var blob = new Blob([source.value], { type: "text/plain;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = "alo.yaml";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  });

  fetch("/api/examples")
    .then(function (response) { return response.json(); })
    .then(function (examples) {
      examples.forEach(function (example) {
        var option = document.createElement("option");
        option.value = example.id;
        option.textContent = example.id + " (" + example.path + ")";
        option.dataset.source = example.source;
        exampleSelect.appendChild(option);
      });
    })
    .catch(function (error) { showErrors(["Could not load examples: " + error.message]); });
}());

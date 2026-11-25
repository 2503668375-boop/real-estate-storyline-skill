"use strict";

const notebook = document.querySelector("[data-example]");
const tabList = notebook.querySelector(".example-tabs");
const tabs = Array.from(tabList.querySelectorAll("button"));
const panels = tabs.map((tab) => document.getElementById(tab.getAttribute("aria-controls")));

function selectCase(index, moveFocus) {
  tabs.forEach((tab, position) => {
    const selected = position === index;
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
    panels[position].hidden = !selected;
  });

  if (moveFocus) tabs[index].focus();
}

tabList.setAttribute("role", "tablist");
tabList.setAttribute("aria-label", "案例推导步骤");
tabs.forEach((tab, index) => {
  tab.setAttribute("role", "tab");
  panels[index].setAttribute("role", "tabpanel");
  panels[index].setAttribute("aria-labelledby", tab.id);
  panels[index].tabIndex = 0;
  tab.addEventListener("click", () => selectCase(index, false));

  tab.addEventListener("keydown", (event) => {
    const destinations = {
      ArrowLeft: (index + tabs.length - 1) % tabs.length,
      ArrowRight: (index + 1) % tabs.length,
      Home: 0,
      End: tabs.length - 1,
    };

    if (!Object.hasOwn(destinations, event.key)) return;
    event.preventDefault();
    selectCase(destinations[event.key], true);
  });
});
selectCase(0, false);
tabList.hidden = false;

const copyStatus = document.querySelector(".copy-status");
document.querySelectorAll("[data-copy]").forEach((button) => {
  const source = document.getElementById(button.dataset.copy);
  let restoreLabel;
  button.hidden = false;

  button.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(source.textContent.trim());
      const originalLabel = button.dataset.label || button.textContent;
      button.dataset.label = originalLabel;
      button.textContent = "已复制";
      copyStatus.textContent = "已复制，可以粘贴到 Codex。";
      clearTimeout(restoreLabel);
      restoreLabel = setTimeout(() => {
        button.textContent = originalLabel;
        copyStatus.textContent = "";
      }, 2400);
    } catch {
      const range = document.createRange();
      range.selectNodeContents(source);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      copyStatus.textContent = "已选中指令，请使用系统复制。";
    }
  });
});
